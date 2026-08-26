from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass

from finana.orchestrator import resolve_symbol_local
from finana.memory.service import MemoryService

_CADENCE_RE = re.compile(r"(\d+)\s*(天|日|周|月|季|年)")
_UNIT_DAYS = {"天": 1, "日": 1, "周": 7, "月": 30, "季": 90, "年": 365}


@dataclass
class Goal:
    """用户长期研究目标：标的、周期、调度状态。"""

    goal_id: str
    user_id: str
    title: str
    symbol: str | None
    cadence_days: int
    last_run_at: float | None
    next_run_at: float | None
    status: str
    created_at: float
    notes: str = ""


class GoalService:
    """基于 SQLite 的目标持久化服务。"""

    def __init__(self, conn):
        self._conn = conn

    def create(self, title: str, symbol: str | None, cadence_days: int = 30,
               user_id: str = "default", now: float | None = None) -> Goal:
        """创建目标并计算首次到期时间。"""
        now = now if now is not None else time.time()
        goal_id = uuid.uuid4().hex
        next_run = now + cadence_days * 86400
        self._conn.execute(
            """INSERT INTO user_goals
               (goal_id, user_id, title, symbol, cadence_days, last_run_at, next_run_at, status)
               VALUES (?, ?, ?, ?, ?, NULL, ?, 'active')""",
            (goal_id, user_id, title, symbol, cadence_days, next_run),
        )
        self._conn.commit()
        return self.get(goal_id)

    def get(self, goal_id: str) -> Goal | None:
        row = self._conn.execute(
            "SELECT * FROM user_goals WHERE goal_id=?", (goal_id,)
        ).fetchone()
        return self._row_to_goal(row) if row is not None else None

    def list(self, user_id: str = "default", status: str | None = None) -> list[Goal]:
        if status is None:
            rows = self._conn.execute(
                "SELECT * FROM user_goals WHERE user_id=? ORDER BY created_at DESC", (user_id,)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM user_goals WHERE user_id=? AND status=? ORDER BY created_at DESC",
                (user_id, status),
            ).fetchall()
        return [self._row_to_goal(r) for r in rows]

    def update_status(self, goal_id: str, status: str) -> None:
        self._conn.execute(
            "UPDATE user_goals SET status=? WHERE goal_id=?", (status, goal_id)
        )
        self._conn.commit()

    def touch(self, goal_id: str, now: float | None = None) -> None:
        """记录一次运行并顺延下一到期时间。"""
        now = now if now is not None else time.time()
        goal = self.get(goal_id)
        if goal is None:
            return
        next_run = now + goal.cadence_days * 86400
        self._conn.execute(
            "UPDATE user_goals SET last_run_at=?, next_run_at=? WHERE goal_id=?",
            (now, next_run, goal_id),
        )
        self._conn.commit()

    def due_goals(self, now: float | None = None, user_id: str = "default") -> list[Goal]:
        now = now if now is not None else time.time()
        rows = self._conn.execute(
            "SELECT * FROM user_goals WHERE user_id=? AND status='active' AND next_run_at<=? "
            "ORDER BY next_run_at",
            (user_id, now),
        ).fetchall()
        return [self._row_to_goal(r) for r in rows]

    def delete(self, goal_id: str) -> None:
        self._conn.execute("DELETE FROM user_goals WHERE goal_id=?", (goal_id,))
        self._conn.commit()

    def _row_to_goal(self, row) -> Goal:
        return Goal(
            goal_id=row["goal_id"],
            user_id=row["user_id"],
            title=row["title"],
            symbol=row["symbol"],
            cadence_days=row["cadence_days"],
            last_run_at=row["last_run_at"],
            next_run_at=row["next_run_at"],
            status=row["status"],
            created_at=row["created_at"],
            notes=row["notes"] or "",
        )


class Planner:
    """从自然语言查询启发式生成目标（不调用 LLM）。"""

    def plan_from_query(self, query: str, memory: MemoryService) -> Goal | None:
        symbol = resolve_symbol_local(query, memory)
        cadence = self._parse_cadence(query)
        title = query.strip()[:120] or "未命名目标"
        return Goal(
            goal_id="",
            user_id="default",
            title=title,
            symbol=symbol,
            cadence_days=cadence,
            last_run_at=None,
            next_run_at=None,
            status="active",
            created_at=0.0,
        )

    def _parse_cadence(self, query: str) -> int:
        m = _CADENCE_RE.search(query or "")
        if not m:
            return 30
        num = int(m.group(1))
        return num * _UNIT_DAYS[m.group(2)]
