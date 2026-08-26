import time

from finana.datacore.models import Quote
from finana.goals import GoalService
from finana.harness_adapter import AnalysisOutcome, FakeHarness
from finana.memory.service import MemoryService
from finana.prediction.parser import PredictionDraft
from finana.scheduler import Scheduler
from finana.storage.db import connect


def _quote(symbol, price):
    return Quote(symbol=symbol, name=symbol, price=price, change_pct=0.0,
                 open_=price, high=price, low=price, prev_close=price,
                 volume=0.0, amount=0.0, timestamp=0.0)


class _FakeDataCore:
    def __init__(self, prices):
        self._prices = prices

    def get_realtime_quote(self, symbol):
        return _quote(symbol, self._prices[symbol])


def _outcome():
    return AnalysisOutcome(final_response="## 回访\n趋势延续。", finish_reason="stop")


def test_process_due_handles_goals_and_predictions(tmp_path):
    conn = connect(tmp_path / "finana.db")
    memory = MemoryService(conn)
    goals = GoalService(conn)
    g = goals.create("每月跟踪600519", "600519.SH", cadence_days=30,
                     now=time.time() - 31 * 86400)
    memory.save_prediction(
        PredictionDraft(direction="up", confidence=0.7, target_low=200.0, target_high=260.0,
                        horizon_days=30, invalidation=[]), "600519.SH")
    dc = _FakeDataCore({"600519.SH": 230.0})

    scheduler = Scheduler(memory=memory, adapter=FakeHarness([_outcome()]), datacore=dc)
    summary = scheduler.process_due(now=time.time() + 31 * 86400)

    assert summary["goals_processed"] == 1
    assert summary["predictions_verified"] == 1
    assert goals.get(g.goal_id).status == "active"
    assert goals.get(g.goal_id).last_run_at is not None
    verified = conn.execute(
        "SELECT status FROM predictions WHERE prediction_id=1"
    ).fetchone()
    assert verified["status"] == "verified"


def test_process_due_no_due_items(tmp_path):
    memory = MemoryService(connect(tmp_path / "finana.db"))
    scheduler = Scheduler(memory=memory, adapter=FakeHarness([_outcome()]), datacore=_FakeDataCore({}))
    summary = scheduler.process_due(now=time.time())
    assert summary == {"goals_processed": 0, "predictions_verified": 0}
