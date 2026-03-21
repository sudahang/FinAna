"""AI-powered investment research workflow."""

from typing import TypedDict
from data.schemas import ResearchReport
from agents.macro_analyst_ai import MacroAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent
from agents.equity_analyst_ai import EquityAnalystAgent
from agents.report_synthesizer_ai import ReportSynthesizerAgent


class WorkflowState(TypedDict):
    """State type for workflow orchestration."""

    query: str
    country: str
    sector: str
    symbol: str
    macro_context: ResearchReport | None
    industry_context: ResearchReport | None
    company_analysis: ResearchReport | None
    report: ResearchReport | None
    error: str | None


class AIResearchWorkflow:
    """
    AI-powered research workflow using Qwen LLM.

    Coordinates AI agents with real data fetching:
    1. Macro Analyst (AI + real macro data)
    2. Industry Analyst (AI + real industry data)
    3. Equity Analyst (AI + real stock data)
    4. Report Synthesizer (AI-generated report)
    """

    def __init__(self, llm_config=None):
        """
        Initialize the AI research workflow.

        Args:
            llm_config: Optional LLM configuration.
        """
        self.macro_analyst = MacroAnalystAgent()
        self.industry_analyst = IndustryAnalystAgent()
        self.equity_analyst = EquityAnalystAgent()
        self.report_synthesizer = ReportSynthesizerAgent()

    def execute(self, query: str) -> ResearchReport:
        """
        Execute the full AI research workflow.

        Args:
            query: User's investment research query.

        Returns:
            Complete ResearchReport with AI analysis.
        """
        # Detect analysis parameters from query
        country = self._detect_country(query)
        symbol = self._detect_symbol(query)

        # Step 1: Macro economic analysis (AI-powered)
        macro_context = self.macro_analyst.analyze(country)

        # Step 2: Industry analysis (AI-powered)
        industry_context = self.industry_analyst.analyze_with_context(query)

        # Step 3: Company analysis (AI-powered)
        company_analysis = self.equity_analyst.analyze(symbol)

        # Step 4: Synthesize final report (AI-powered)
        report = self.report_synthesizer.synthesize(
            query=query,
            macro_context=macro_context,
            industry_context=industry_context,
            company_analysis=company_analysis
        )

        return report

    def _detect_country(self, query: str) -> str:
        """Detect country from query."""
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["中国", "a 股", "港股", "沪深"]):
            return "china"
        elif any(kw in query_lower for kw in ["美股", "美国", "nasdaq", "nyse"]):
            return "us"

        # Detect based on stock symbol
        if self._detect_symbol(query):
            return "us"  # US stocks by default

        return "china"  # Default to China

    def _detect_symbol(self, query: str) -> str:
        """Detect stock symbol from query."""
        query_upper = query.upper()

        # Common mappings
        mappings = {
            "特斯拉": "TSLA", "TSLA": "TSLA",
            "英伟达": "NVDA", "NVIDIA": "NVDA", "NVDA": "NVDA",
            "苹果": "AAPL", "APPLE": "AAPL", "AAPL": "AAPL",
            "微软": "MSFT", "MICROSOFT": "MSFT", "MSFT": "MSFT",
            "谷歌": "GOOGL", "GOOGLE": "GOOGL", "GOOGL": "GOOGL",
            "亚马逊": "AMZN", "AMAZON": "AMZN", "AMZN": "AMZN",
            "META": "META", "FACEBOOK": "META"
        }

        for name, symbol in mappings.items():
            if name in query_upper:
                return symbol

        # Check for ticker pattern
        import re
        tickers = re.findall(r'\b[A-Z]{3,4}\b', query_upper)
        if tickers:
            return tickers[0]

        return "TSLA"  # Default


async def execute_ai_research_workflow(query: str) -> ResearchReport:
    """
    Async convenience function to execute AI research workflow.

    Args:
        query: User's investment research query.

    Returns:
        Complete ResearchReport with AI analysis.
    """
    workflow = AIResearchWorkflow()
    return workflow.execute(query)
