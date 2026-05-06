"""Versioned prompt loading utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from string import Template


PROMPT_ROOT = Path(__file__).resolve().parents[1] / "prompts"


@dataclass(frozen=True)
class PromptSpec:
    """Loaded prompt text plus lightweight metadata."""

    name: str
    version: str
    content: str

    @property
    def identifier(self) -> str:
        return f"{self.name}@{self.version}"

    def render(self, **variables: object) -> str:
        """Render prompt text with `$variable` interpolation."""
        return Template(self.content).safe_substitute(
            {key: str(value) for key, value in variables.items()}
        )


def load_prompt(relative_path: str, default: str = "") -> PromptSpec:
    """Load a prompt file from `prompts/`, falling back to `default`."""
    path = PROMPT_ROOT / relative_path
    name = relative_path.removesuffix(".md").replace("/", ".")
    if not path.exists():
        return PromptSpec(name=name, version="inline", content=default)

    content = path.read_text(encoding="utf-8")
    version = "v1"
    match = re.search(r"^version:\s*([^\s]+)\s*$", content, flags=re.MULTILINE)
    if match:
        version = match.group(1).strip()

    body = re.sub(r"^---\n.*?\n---\n?", "", content, count=1, flags=re.DOTALL)
    return PromptSpec(name=name, version=version, content=body.strip())
