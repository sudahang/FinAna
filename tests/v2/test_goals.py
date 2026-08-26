import time

from finana.goals import GoalService, Planner
from finana.memory.service import MemoryService
from finana.storage.db import connect


def _memory(tmp_path):
    conn = connect(tmp_path / "finana.db")
    return MemoryService(conn)


def test_goal_create_and_due_cadence(tmp_path):
    conn = connect(tmp_path / "finana.db")
    svc = GoalService(conn)
    now = 1_000_000.0
    goal = svc.create("跟踪茅台", "600519.SH", cadence_days=30, now=now)

    assert goal.symbol == "600519.SH"
    assert goal.next_run_at == now + 30 * 86400
    assert svc.due_goals(now=now) == []
    assert len(svc.due_goals(now=now + 31 * 86400)) == 1


def test_goal_touch_reschedules(tmp_path):
    conn = connect(tmp_path / "finana.db")
    svc = GoalService(conn)
    goal = svc.create("x", "TSLA", cadence_days=7, now=100.0)
    svc.touch(goal.goal_id, now=200.0)
    refreshed = svc.get(goal.goal_id)
    assert refreshed.last_run_at == 200.0
    assert refreshed.next_run_at == 200.0 + 7 * 86400


def test_goal_status_filter_and_delete(tmp_path):
    conn = connect(tmp_path / "finana.db")
    svc = GoalService(conn)
    g = svc.create("active goal", "TSLA")
    svc.create("paused goal", "NVDA")
    svc.update_status(g.goal_id, "paused")
    assert len(svc.list(status="active")) == 1
    assert len(svc.list(status="paused")) == 1
    svc.delete(g.goal_id)
    assert svc.get(g.goal_id) is None


def test_planner_parses_cadence_and_symbol(tmp_path):
    mem = _memory(tmp_path)
    mem.upsert_instrument("600519.SH", name="贵州茅台")
    mem.upsert_instrument("TSLA", name="特斯拉")
    planner = Planner()

    goal = planner.plan_from_query("每月跟踪贵州茅台的季度表现", mem)
    assert goal.symbol == "600519.SH"
    assert goal.cadence_days == 30

    goal2 = planner.plan_from_query("每7天跟踪特斯拉", mem)
    assert goal2.symbol == "TSLA"
    assert goal2.cadence_days == 7

    goal3 = planner.plan_from_query("跟踪一下市场情绪", mem)
    assert goal3.symbol is None
    assert goal3.cadence_days == 30
