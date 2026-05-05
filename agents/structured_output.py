"""Helpers for extracting structured LLM output safely."""

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    """
    Extract a JSON object from an LLM response.

    Handles raw JSON, fenced code blocks, and prose around the object. Returns an
    empty dict when no valid object can be recovered.
    """
    if not text:
        return {}

    candidates = []
    fence_matches = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(fence_matches)

    start_idx = text.find("{")
    end_idx = text.rfind("}") + 1
    if start_idx >= 0 and end_idx > start_idx:
        candidates.append(text[start_idx:end_idx])

    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        candidates.append(stripped)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    return {}


def repair_json_response(llm: Any, response: str, schema_hint: str) -> str:
    """
    Ask the LLM once to repair malformed structured output.

    Returns the repaired response only if it contains a valid JSON object;
    otherwise returns the original response so callers can use fallbacks.
    """
    if extract_json_object(response):
        return response

    try:
        repaired = llm.chat(
            messages=[
                {
                    "role": "user",
                    "content": (
                        "请把下面内容修复为严格合法的 JSON 对象，只返回 JSON，不要解释。\n\n"
                        f"目标结构：\n{schema_hint}\n\n"
                        f"原始内容：\n{response}"
                    ),
                }
            ],
            system_prompt="你是 JSON 修复器，只输出严格合法的 JSON 对象。",
        )
    except Exception:
        return response

    return repaired if extract_json_object(repaired) else response


def normalize_choice(value: Any, allowed: set[str], default: str) -> str:
    """Normalize an LLM enum-like value against an allowed set."""
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in allowed:
            return normalized
    return default


def normalize_string_list(value: Any, default: list[str]) -> list[str]:
    """Normalize an LLM list field into a non-empty string list."""
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        if items:
            return items
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return default
