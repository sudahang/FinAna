# finana/prompts/loader.py
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_system_prompt(include_prediction_format: bool = True) -> str:
    """读取系统提示词，include 为 True 时追加预测格式全文。"""
    text = (PROMPTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
    if include_prediction_format:
        text += "\n\n" + (PROMPTS_DIR / "prediction_format.md").read_text(encoding="utf-8")
    return text


def load_skill(name: str) -> str:
    """读取 skills/<name>/SKILL.md，缺失时抛 FileNotFoundError。"""
    path = PROMPTS_DIR / "skills" / name / "SKILL.md"
    if not path.is_file():
        raise FileNotFoundError(f"skill not found: {name}")
    return path.read_text(encoding="utf-8")
