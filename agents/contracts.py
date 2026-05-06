"""Typed contracts for agent boundary inputs and outputs."""

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


AgentRole = Literal[
    "input_router",
    "macro_analyst",
    "industry_analyst",
    "equity_analyst",
    "risk_compliance",
    "report_synthesizer",
]


class Evidence(BaseModel):
    """Source-backed fact or artifact used by an agent."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    as_of: datetime = Field(default_factory=datetime.now)
    content: str
    url: str | None = None
    is_fallback: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRunMetadata(BaseModel):
    """Execution metadata attached to every agent result."""

    agent_role: AgentRole
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    prompt_version: str | None = None
    model: str | None = None
    trace_id: str | None = None
    warnings: list[str] = Field(default_factory=list)


class AgentTask(BaseModel):
    """Validated task payload sent from the coordinator to a specialist agent."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    role: AgentRole
    query: str
    country: str | None = None
    sector: str | None = None
    symbol: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)


class AgentResult(BaseModel):
    """Validated result returned from a specialist agent."""

    task_id: str
    role: AgentRole
    payload: dict[str, Any]
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    metadata: AgentRunMetadata
    warnings: list[str] = Field(default_factory=list)
    is_fallback: bool = False

    def add_warning(self, warning: str) -> None:
        """Record a warning on both result and run metadata."""
        self.warnings.append(warning)
        self.metadata.warnings.append(warning)
