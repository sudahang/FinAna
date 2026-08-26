from __future__ import annotations

import threading
import time

from finana.goals import GoalService
from finana.harness_adapter import HarnessAdapter
from finana.memory.service import MemoryService
from finana.observability import get_logger
from finana.orchestrator import Orchestrator
from finana.storage.db import get_db
from finana.verifier import Verifier

log = get_logger("scheduler")


class Scheduler:
    """惰性调度器：处理到期目标（回访分析）与到期预测（验证）。

    设计为可被 CLI/API/cron 周期调用，也可 start() 常驻后台线程；
    不依赖 dsh runtime 做常驻调度。
    """

    def __init__(self, memory: MemoryService | None = None, adapter=None, datacore=None):
        self.memory = memory if memory is not None else MemoryService(get_db())
        self.adapter = adapter if adapter is not None else HarnessAdapter()
        self.datacore = datacore
        self._orchestrator = Orchestrator(memory=self.memory, adapter=self.adapter)
        self._goals = GoalService(self.memory._conn)
        self._verifier = Verifier()
        self._thread = None
        self._stop = False

    def _datacore(self):
        if self.datacore is not None:
            return self.datacore
        from finana.datacore.core import get_datacore

        return get_datacore()

    def process_due(self, now: float | None = None) -> dict:
        """处理所有到期目标与到期预测，返回处理计数。"""
        now = now if now is not None else time.time()
        goals = self._goals.due_goals(now=now)
        goal_runs = 0
        for goal in goals:
            try:
                self._orchestrator.analyze(goal.title, session_id=goal.goal_id)
            except Exception as exc:
                log.warning("goal %s 回访失败: %s", goal.goal_id, exc)
            self._goals.touch(goal.goal_id, now=now)
            goal_runs += 1
        verdicts = self._verifier.run_due(self._datacore(), self.memory, now=now)
        return {"goals_processed": goal_runs, "predictions_verified": len(verdicts)}

    def start(self, interval_seconds: int = 3600) -> None:
        """启动后台线程，按间隔周期调用 process_due。"""

        def loop() -> None:
            while not self._stop:
                try:
                    self.process_due()
                except Exception as exc:
                    log.warning("scheduler loop error: %s", exc)
                time.sleep(interval_seconds)

        self._stop = False
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止后台线程。"""
        self._stop = True


def _scheduler_process_once() -> dict:
    return Scheduler().process_due()
