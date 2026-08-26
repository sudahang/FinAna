from pathlib import Path

import pytest

from finana.prompts.loader import PROMPTS_DIR, load_skill, load_system_prompt


def test_prompts_dir_points_to_package():
    assert PROMPTS_DIR == Path(__file__).parents[2] / "finana" / "prompts"


def test_system_prompt_nonempty_with_anchors():
    prompt = load_system_prompt(include_prediction_format=False)
    assert prompt.strip()
    assert "prediction" in prompt
    assert "不构成投资建议" in prompt


def test_system_prompt_at_most_60_lines():
    prompt = load_system_prompt(include_prediction_format=False)
    assert len(prompt.split("\n")) <= 60


def test_system_prompt_includes_prediction_format():
    combined = load_system_prompt()
    base = load_system_prompt(include_prediction_format=False)
    assert combined.startswith(base)
    assert '"direction"' in combined
    assert combined.index("不构成投资建议") < combined.index('"direction"')


def test_load_stock_research_skill():
    skill = load_skill("stock-research")
    assert skill.strip()
    assert ("龙虎榜" in skill) or ("get_lhb" in skill)
    assert "降级" in skill


def test_load_missing_skill_raises():
    with pytest.raises(FileNotFoundError):
        load_skill("nope")
