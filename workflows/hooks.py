"""Deterministic lifecycle hooks for analysis requests."""

import logging
from datetime import datetime

from agents.contracts import AgentResult
from data.schemas import ResearchReport

logger = logging.getLogger(__name__)


class AnalysisLifecycleHooks:
    """Validation and audit hooks around workflow execution."""

    def validate_input(self, query: str) -> None:
        """Reject empty or obviously invalid requests before LLM work starts."""
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        if len(query) > 4000:
            raise ValueError("query is too long")

    def validate_agent_result(self, result: AgentResult) -> AgentResult:
        """Validate required evidence metadata after each specialist run."""
        if not result.evidence:
            result.add_warning("agent returned no evidence")
        for evidence in result.evidence:
            if not evidence.source:
                result.add_warning(f"evidence {evidence.id} has no source")
        return result

    def validate_report_provenance(
        self,
        report: ResearchReport,
        agent_results: list[AgentResult],
    ) -> ResearchReport:
        """Ensure report metadata discloses sources and fallback warnings."""
        sources = list(report.data_sources or [])
        fallback_sources = []
        for result in agent_results:
            for evidence in result.evidence:
                if evidence.source and evidence.source not in sources:
                    sources.append(evidence.source)
                if evidence.is_fallback:
                    fallback_sources.append(evidence.source)

        report.data_sources = sources
        if fallback_sources and "fallback" not in report.full_report.lower():
            report.full_report += (
                "\n\n## 数据质量提示\n\n"
                f"以下来源包含 fallback 或默认数据：{', '.join(sorted(set(fallback_sources)))}。"
            )
        return report

    def emit_audit_log(self, event: str, trace_id: str | None = None, **fields: object) -> None:
        """Emit a structured lifecycle audit log."""
        logger.info(
            "analysis_lifecycle event=%s trace_id=%s at=%s fields=%s",
            event,
            trace_id,
            datetime.now().isoformat(),
            fields,
        )
