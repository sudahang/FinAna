import time

from finana.datacore.models import Quote
from finana.memory.service import MemoryService
from finana.prediction.parser import PredictionDraft
from finana.storage.db import connect
from finana.verifier import Verifier


def _quote(symbol, price):
    return Quote(
        symbol=symbol, name=symbol, price=price, change_pct=0.0,
        open_=price, high=price, low=price, prev_close=price,
        volume=0.0, amount=0.0, timestamp=0.0,
    )


class _FakeDataCore:
    def __init__(self, prices):
        self._prices = prices

    def get_realtime_quote(self, symbol):
        return _quote(symbol, self._prices[symbol])


def _svc(tmp_path):
    return MemoryService(connect(tmp_path / "finana.db"))


def test_verify_two_sided_target():
    v = Verifier()
    pred = {"prediction_id": 1, "symbol": "TSLA", "direction": "up",
            "target_low": 200.0, "target_high": 260.0}
    assert v.verify_prediction(pred, _quote("TSLA", 230.0)).range_hit is True
    assert v.verify_prediction(pred, _quote("TSLA", 230.0)).direction_hit is True
    assert v.verify_prediction(pred, _quote("TSLA", 190.0)).direction_hit is False
    assert v.verify_prediction(pred, _quote("TSLA", 270.0)).range_hit is False


def test_verify_one_sided_target():
    v = Verifier()
    pred = {"prediction_id": 2, "symbol": "TSLA", "direction": "up", "target_low": 200.0, "target_high": None}
    assert v.verify_prediction(pred, _quote("TSLA", 210.0)).direction_hit is True
    assert v.verify_prediction(pred, _quote("TSLA", 190.0)).direction_hit is False


def test_run_due_writes_verdict_and_lesson(tmp_path):
    svc = _svc(tmp_path)
    svc.save_prediction(
        PredictionDraft(direction="up", confidence=0.7, target_low=200.0, target_high=260.0,
                        horizon_days=30, invalidation=[]),
        "TSLA", trace_id="t1",
    )
    now = time.time() + 31 * 86400
    verdicts = Verifier().run_due(_FakeDataCore({"TSLA": 230.0}), svc, now=now)

    assert len(verdicts) == 1
    assert verdicts[0].direction_hit is True
    updated = svc._conn.execute(
        "SELECT verdict, status FROM predictions WHERE prediction_id=1"
    ).fetchone()
    assert updated["status"] == "verified"
    assert '"direction_hit": true' in updated["verdict"]
    lessons = svc.search_semantic("预测验证", k=5)
    assert any("命中" in l["content"] for l in lessons)


def test_run_due_handles_quote_failure(tmp_path):
    svc = _svc(tmp_path)
    svc.save_prediction(
        PredictionDraft(direction="up", confidence=0.7, target_low=200.0, target_high=260.0,
                        horizon_days=30, invalidation=[]),
        "TSLA",
    )

    class _Boom:
        def get_realtime_quote(self, symbol):
            raise RuntimeError("network down")

    verdicts = Verifier().run_due(_Boom(), svc, now=time.time() + 31 * 86400)
    assert verdicts[0].note.startswith("行情获取失败")
    assert verdicts[0].current_price == 0.0
