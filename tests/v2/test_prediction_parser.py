import json

from finana.prediction.parser import PredictionDraft, parse_prediction


def _fenced(payload, tag="json"):
    opener = f"```{tag}" if tag else "```"
    return f"{opener}\n{json.dumps(payload, ensure_ascii=False)}\n```"


def test_valid_fenced_block_parses_fully():
    text = (
        "分析如下。\n"
        + _fenced(
            {
                "direction": "up",
                "confidence": 0.8,
                "target_low": 210.0,
                "target_high": 260.5,
                "horizon_days": 90,
                "invalidation": ["跌破200日均线", "放量跌破支撑"],
                "rationale": "基本面强劲",
            }
        )
        + "\n以上供参考。"
    )
    draft = parse_prediction(text)
    assert draft == PredictionDraft(
        direction="up",
        confidence=0.8,
        target_low=210.0,
        target_high=260.5,
        horizon_days=90,
        invalidation=["跌破200日均线", "放量跌破支撑"],
        rationale="基本面强劲",
    )


def test_fenced_block_without_json_tag_parses():
    draft = parse_prediction(_fenced({"direction": "down", "confidence": 0.6}, tag=""))
    assert draft is not None
    assert draft.direction == "down"
    assert draft.confidence == 0.6


def test_two_blocks_last_wins():
    text = _fenced({"direction": "up", "confidence": 0.9})
    text += "\n中间补充说明。\n"
    text += _fenced({"direction": "down", "confidence": 0.2})
    draft = parse_prediction(text)
    assert draft is not None
    assert draft.direction == "down"
    assert draft.confidence == 0.2


def test_bare_json_object_fallback_parses():
    text = '结论： {"direction": "sideways", "confidence": 0.5} 请注意风险。'
    draft = parse_prediction(text)
    assert draft is not None
    assert draft.direction == "sideways"
    assert draft.horizon_days == 30


def test_missing_direction_returns_none():
    assert parse_prediction(_fenced({"confidence": 0.7})) is None


def test_bad_direction_value_returns_none():
    assert parse_prediction(_fenced({"direction": "bullish", "confidence": 0.7})) is None


def test_confidence_above_one_returns_none():
    assert parse_prediction(_fenced({"direction": "up", "confidence": 1.5})) is None


def test_horizon_days_string_returns_none():
    text = _fenced({"direction": "up", "confidence": 0.7, "horizon_days": "30"})
    assert parse_prediction(text) is None


def test_garbage_inside_fence_returns_none():
    assert parse_prediction("```json\n这不是JSON\n```\n") is None


def test_malformed_json_inside_fence_returns_none():
    assert parse_prediction("```json\n{oops,, \"direction\": \"up\"\n```") is None


def test_no_block_returns_none():
    assert parse_prediction("没有任何预测块的普通文本。") is None


def test_empty_text_returns_none():
    assert parse_prediction("") is None


def test_minimal_valid_parses_with_defaults():
    text = _fenced({"direction": "up", "confidence": 0.55, "horizon_days": 14})
    draft = parse_prediction(text)
    assert draft == PredictionDraft(
        direction="up",
        confidence=0.55,
        target_low=None,
        target_high=None,
        horizon_days=14,
        invalidation=[],
        rationale="",
    )
