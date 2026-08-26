import os
import time

from fastapi.testclient import TestClient

from finana.api import create_app
from finana.config import get_settings
from finana.datacore.models import Quote
from finana.harness_adapter import AnalysisOutcome, FakeHarness
from finana.memory.service import MemoryService
from finana.prediction.parser import PredictionDraft
from finana.storage.db import connect


def _prediction_outcome():
    md = (
        "## 分析\n看好。\n\n```json\n"
        '{"direction": "up", "confidence": 0.8, "target_low": 210.0, '
        '"target_high": 260.0, "horizon_days": 30, "invalidation": ["跌破200"]}\n```'
    )
    return AnalysisOutcome(final_response=md, finish_reason="stop")


def _app(tmp_path, outcomes, prices):
    os.environ["FINANA_HOME"] = str(tmp_path / "home")
    get_settings.cache_clear()
    conn = connect(tmp_path / "finana.db")
    memory = MemoryService(conn)
    seed = outcomes if outcomes else [_prediction_outcome()]
    adapter = FakeHarness(seed)

    class _FakeDataCore:
        def get_realtime_quote(self, symbol):
            return Quote(symbol=symbol, name=symbol, price=prices.get(symbol, 0.0),
                         change_pct=0.0, open_=0.0, high=0.0, low=0.0,
                         prev_close=0.0, volume=0.0, amount=0.0, timestamp=0.0)

    return create_app(memory=memory, adapter=adapter, datacore=_FakeDataCore())


def test_analyze_endpoint_returns_prediction(tmp_path):
    from finana.api import create_app

    client = TestClient(_app(tmp_path, [_prediction_outcome()], {}))
    resp = client.post("/api/analyze", json={"query": "分析600519走势"})
    assert resp.status_code == 200
    body = resp.json()
    assert "response_md" in body
    assert body["prediction"]["direction"] == "up"
    assert body["prediction_id"] is not None


def test_goals_crud(tmp_path):
    from finana.api import create_app

    client = TestClient(_app(tmp_path, [], {}))
    created = client.post("/api/goals", json={"query": "每月跟踪贵州茅台表现"})
    assert created.status_code == 200
    goal_id = created.json()["goal_id"]

    listed = client.get("/api/goals")
    assert any(g["goal_id"] == goal_id for g in listed.json())

    set_st = client.post(f"/api/goals/{goal_id}/status", json={"status": "paused"})
    assert set_st.json()["status"] == "paused"


def test_verify_run_endpoint(tmp_path):
    from finana.api import create_app

    conn = connect(tmp_path / "finana.db")
    memory = MemoryService(conn)
    memory.save_prediction(
        PredictionDraft(direction="up", confidence=0.7, target_low=200.0, target_high=260.0,
                        horizon_days=30, invalidation=[]),
        "TSLA",
    )

    class _FakeDataCore:
        def get_realtime_quote(self, symbol):
            return Quote(symbol=symbol, name=symbol, price=230.0, change_pct=0.0,
                         open_=0.0, high=0.0, low=0.0, prev_close=0.0,
                         volume=0.0, amount=0.0, timestamp=0.0)

    os.environ["FINANA_HOME"] = str(tmp_path / "home")
    get_settings.cache_clear()
    app = create_app(memory=memory, datacore=_FakeDataCore())
    client = TestClient(app)
    resp = client.post("/api/verify/run", json={}, params={"now": time.time() + 31 * 86400})
    assert resp.status_code == 200
    assert resp.json()["verified"] == 1
    assert resp.json()["results"][0]["direction_hit"] is True
