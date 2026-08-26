from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


@dataclass
class PredictionDraft:
    """模型预测结果的结构化草稿。"""

    direction: str
    confidence: float
    target_low: float | None = None
    target_high: float | None = None
    horizon_days: int = 30
    invalidation: list[str] = field(default_factory=list)
    rationale: str = ""


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_DIRECTIONS = {"up", "down", "sideways"}


def parse_prediction(text: str) -> PredictionDraft | None:
    """从模型输出文本解析最后一个预测 JSON 块，无法解析时返回 None。"""
    raw = _extract_raw(text)
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return _build_draft(payload)


def _extract_raw(text: str) -> str | None:
    matches = _FENCE_RE.findall(text)
    if matches:
        return matches[-1]
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                candidate = text[start : i + 1]
                if '"direction"' in candidate:
                    return candidate
                start = -1
    return None


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _build_draft(payload: dict) -> PredictionDraft | None:
    direction = payload.get("direction")
    if not isinstance(direction, str) or direction not in _DIRECTIONS:
        return None
    confidence = payload.get("confidence")
    if not _is_number(confidence) or not 0.0 <= confidence <= 1.0:
        return None
    horizon_days = payload.get("horizon_days", 30)
    if (
        not isinstance(horizon_days, int)
        or isinstance(horizon_days, bool)
        or horizon_days <= 0
    ):
        return None
    target_low = payload.get("target_low")
    if target_low is not None and not _is_number(target_low):
        return None
    target_high = payload.get("target_high")
    if target_high is not None and not _is_number(target_high):
        return None
    invalidation = payload.get("invalidation", [])
    if not isinstance(invalidation, list) or not all(
        isinstance(item, str) for item in invalidation
    ):
        return None
    rationale = payload.get("rationale", "")
    if not isinstance(rationale, str):
        return None
    return PredictionDraft(
        direction=direction,
        confidence=float(confidence),
        target_low=None if target_low is None else float(target_low),
        target_high=None if target_high is None else float(target_high),
        horizon_days=horizon_days,
        invalidation=invalidation,
        rationale=rationale,
    )
