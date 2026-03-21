"""Investment research workflow orchestration."""

from typing import TypedDict
from data.schemas import ResearchReport, MacroContext, IndustryContext, CompanyAnalysis
from agents.macro_analyst import MacroAnalystAgent
from agents.industry_analyst import IndustryAnalystAgent
from agents.equity_analyst import EquityAnalystAgent
from agents.report_synthesizer import ReportSynthesizerAgent


class WorkflowState(TypedDict):
    """State type for workflow orchestration."""

    query: str
    macro_context: MacroContext | None
    industry_context: IndustryContext | None
    company_analysis: CompanyAnalysis | None
    report: ResearchReport | None
    error: str | None


class ResearchWorkflow:
    """
    Orchestrates the investment research workflow.

    Coordinates multiple specialist agents in sequence:
    1. Macro Analyst -> 2. Industry Analyst -> 3. Equity Analyst -> 4. Report Synthesizer
    """

    def __init__(self, llm_config: dict | None = None):
        """
        Initialize the research workflow.

        Args:
            llm_config: Optional LLM configuration passed to agents.
        """
        self.macro_analyst = MacroAnalystAgent(llm_config)
        self.industry_analyst = IndustryAnalystAgent(llm_config)
        self.equity_analyst = EquityAnalystAgent(llm_config)
        self.report_synthesizer = ReportSynthesizerAgent(llm_config)
        self.llm_config = llm_config

    def execute(self, query: str) -> ResearchReport:
        """
        Execute the full research workflow.

        Args:
            query: User's investment research query.

        Returns:
            Complete ResearchReport with all analysis.

        Raises:
            Exception: If any step in the workflow fails.
        """
        state: WorkflowState = {
            "query": query,
            "macro_context": None,
            "industry_context": None,
            "company_analysis": None,
            "report": None,
            "error": None
        }

        try:
            # Step 1: Macro economic analysis
            state = self._analyze_macro(state)

            # Step 2: Industry analysis
            state = self._analyze_industry(state)

            # Step 3: Company/equity analysis
            state = self._analyze_equity(state)

            # Step 4: Synthesize final report
            state = self._synthesize_report(state)

            if state["report"] is None:
                raise RuntimeError("Failed to generate report")

            return state["report"]

        except Exception as e:
            state["error"] = str(e)
            raise

    def _analyze_macro(self, state: WorkflowState) -> WorkflowState:
        """Run macro analyst agent."""
        state["macro_context"] = self.macro_analyst.analyze_with_context(state["query"])
        return state

    def _analyze_industry(self, state: WorkflowState) -> WorkflowState:
        """Run industry analyst agent."""
        state["industry_context"] = self.industry_analyst.analyze_with_context(
            state["query"],
            state["macro_context"]
        )
        return state

    def _analyze_equity(self, state: WorkflowState) -> WorkflowState:
        """Run equity analyst agent."""
        state["company_analysis"] = self.equity_analyst.analyze_with_context(
            state["query"],
            state["macro_context"],
            state["industry_context"]
        )
        return state

    def _synthesize_report(self, state: WorkflowState) -> WorkflowState:
        """Run report synthesizer agent."""
        if state["macro_context"] is None or state["industry_context"] is None:
            raise RuntimeError("Missing required analysis context")

        state["report"] = self.report_synthesizer.synthesize(
            query=state["query"],
            macro_context=state["macro_context"],
            industry_context=state["industry_context"],
            company_analysis=state["company_analysis"]
        )
        return state


async def execute_research_workflow(query: str) -> ResearchReport:
    """
    Async convenience function to execute research workflow.

    Args:
        query: User's investment research query.

    Returns:
        Complete ResearchReport with all analysis.
    """
    workflow = ResearchWorkflow()
    return workflow.execute(query)
