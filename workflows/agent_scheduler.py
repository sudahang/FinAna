"""Agent scheduling boundary for the research workflow."""

from datetime import datetime
from typing import Any

from agents.contracts import AgentResult, AgentRunMetadata, AgentTask, Evidence
from agents.equity_analyst_ai import EquityAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent
from agents.macro_analyst_ai import MacroAnalystAgent
from data.schemas import CompanyAnalysis, IndustryContext, MacroContext


class AgentScheduler:
    """Create validated tasks and wrap specialist outputs as agent results."""

    def __init__(
        self,
        macro_analyst: MacroAnalystAgent,
        industry_analyst: IndustryAnalystAgent,
        equity_analyst: EquityAnalystAgent,
    ):
        self.macro_analyst = macro_analyst
        self.industry_analyst = industry_analyst
        self.equity_analyst = equity_analyst

    def run_macro(self, query: str, country: str, trace_id: str | None = None) -> tuple[MacroContext, AgentResult]:
        task = AgentTask(role="macro_analyst", query=query, country=country)
        context = self.macro_analyst.analyze(country)
        return context, self._result(
            task=task,
            payload=context.model_dump(),
            evidence=[
                Evidence(
                    source=context.data_source,
                    as_of=context.as_of or datetime.now(),
                    content=context.summary,
                    is_fallback=context.is_fallback,
                )
            ],
            prompt_version=getattr(getattr(self.macro_analyst, "prompt", None), "identifier", None),
            trace_id=trace_id,
            is_fallback=context.is_fallback,
        )

    def run_industry(self, query: str, sector: str, trace_id: str | None = None) -> tuple[IndustryContext, AgentResult]:
        task = AgentTask(role="industry_analyst", query=query, sector=sector)
        context = self.industry_analyst.analyze(sector)
        return context, self._result(
            task=task,
            payload=context.model_dump(),
            evidence=[
                Evidence(
                    source=context.data_source,
                    as_of=context.as_of or datetime.now(),
                    content=context.summary,
                    is_fallback=context.is_fallback,
                )
            ],
            prompt_version=getattr(getattr(self.industry_analyst, "prompt", None), "identifier", None),
            trace_id=trace_id,
            is_fallback=context.is_fallback,
        )

    def run_equity(self, query: str, symbol: str, trace_id: str | None = None) -> tuple[CompanyAnalysis, AgentResult]:
        task = AgentTask(role="equity_analyst", query=query, symbol=symbol)
        analysis = self.equity_analyst.analyze(symbol)
        return analysis, self._result(
            task=task,
            payload=analysis.model_dump(),
            evidence=[
                Evidence(
                    source=analysis.company.data_source,
                    as_of=analysis.company.as_of or datetime.now(),
                    content=analysis.summary,
                    is_fallback=analysis.company.is_fallback,
                )
            ],
            prompt_version=getattr(getattr(self.equity_analyst, "prompt", None), "identifier", None),
            trace_id=trace_id,
            is_fallback=analysis.company.is_fallback,
        )

    def _result(
        self,
        task: AgentTask,
        payload: dict[str, Any],
        evidence: list[Evidence],
        prompt_version: str | None,
        trace_id: str | None,
        is_fallback: bool,
    ) -> AgentResult:
        metadata = AgentRunMetadata(
            agent_role=task.role,
            completed_at=datetime.now(),
            prompt_version=prompt_version,
            trace_id=trace_id,
        )
        return AgentResult(
            task_id=task.id,
            role=task.role,
            payload=payload,
            confidence=0.5 if is_fallback else 0.8,
            evidence=evidence,
            metadata=metadata,
            is_fallback=is_fallback,
        )
