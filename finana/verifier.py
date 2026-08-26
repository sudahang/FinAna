from __future__ import annotations

import time
from dataclasses import dataclass

from finana.datacore.models import Quote
from finana.memory.service import MemoryService


@dataclass
class Verdict:
    """单条预测的验证结果。"""

    prediction_id: int
    symbol: str
    direction_hit: bool | None
    range_hit: bool | None
    current_price: float
    note: str


class Verifier:
    """到期预测验证器：拉实时价，判定方向与区间命中，写回结论并沉淀教训。"""

    def verify_prediction(self, pred: dict, quote: Quote) -> Verdict:
        price = quote.price
        low, high = pred.get("target_low"), pred.get("target_high")
        direction = pred.get("direction")

        range_hit = self._range_hit(price, low, high)
        direction_hit = self._direction_hit(price, direction, low, high)

        parts = []
        if direction_hit is not None:
            parts.append("方向命中" if direction_hit else "方向未命中")
        if range_hit is not None:
            parts.append("区间命中" if range_hit else "区间未命中")
        if not parts:
            parts.append("无锚定目标，仅记录现价")
        note = "；".join(parts) + f"（现价 {price:.2f}）"

        return Verdict(
            prediction_id=pred["prediction_id"],
            symbol=pred["symbol"],
            direction_hit=direction_hit,
            range_hit=range_hit,
            current_price=price,
            note=note,
        )

    def _range_hit(self, price: float, low, high) -> bool | None:
        if low is not None and high is not None:
            return low <= price <= high
        if low is not None:
            return price >= low
        if high is not None:
            return price <= high
        return None

    def _direction_hit(self, price: float, direction: str | None, low, high) -> bool | None:
        if direction == "up":
            if low is not None:
                return price >= low
            if high is not None:
                return price <= high
        if direction == "down":
            if high is not None:
                return price <= high
            if low is not None:
                return price >= low
        return None

    def run_due(self, datacore, memory: MemoryService, now: float | None = None) -> list[Verdict]:
        now = now if now is not None else time.time()
        verdicts: list[Verdict] = []
        for pred in memory.due_predictions(now):
            try:
                quote = datacore.get_realtime_quote(pred["symbol"])
            except Exception as exc:
                verdicts.append(Verdict(
                    prediction_id=pred["prediction_id"],
                    symbol=pred["symbol"],
                    direction_hit=None,
                    range_hit=None,
                    current_price=0.0,
                    note=f"行情获取失败：{type(exc).__name__}: {exc}",
                ))
                continue
            verdict = self.verify_prediction(pred, quote)
            memory.record_verdict(verdict.prediction_id, self._verdict_json(verdict))
            if verdict.direction_hit is not None:
                lesson = (
                    f"预测验证[{pred['symbol']}]：方向{'命中' if verdict.direction_hit else '未命中'}，"
                    f"现价 {verdict.current_price:.2f}，区间 {pred.get('target_low')}–{pred.get('target_high')}"
                )
                memory.remember_semantic(lesson, tags="verdict", trace=pred.get("trace_id", ""))
            verdicts.append(verdict)
        return verdicts

    def _verdict_json(self, verdict: Verdict) -> dict:
        return {
            "direction_hit": verdict.direction_hit,
            "range_hit": verdict.range_hit,
            "current_price": verdict.current_price,
            "note": verdict.note,
        }
