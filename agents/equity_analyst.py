"""Equity Analyst Agent."""

from data.schemas import CompanyAnalysis, MacroContext, IndustryContext
from data.mock_data import get_mock_company_analysis


class EquityAnalystAgent:
    """
    Analyst agent responsible for individual company/stock analysis.

    This agent performs deep dives on specific companies including
    financial health, recent news, technical indicators, and risk factors.
    """

    def __init__(self, llm_config: dict | None = None):
        """
        Initialize the Equity Analyst Agent.

        Args:
            llm_config: Optional LLM configuration for future enhancement.
                       Currently uses simulated data for demo purposes.
        """
        self.role = "Equity Analyst"
        self.goal = "Analyze individual companies and provide investment recommendations"
        self.llm_config = llm_config

    def analyze(self, symbol: str) -> CompanyAnalysis:
        """
        Perform company analysis for a given stock symbol.

        Args:
            symbol: Stock ticker symbol to analyze.

        Returns:
            CompanyAnalysis containing detailed company assessment.
        """
        return get_mock_company_analysis(symbol)

    def analyze_with_context(
        self,
        query: str,
        macro_context: MacroContext | None = None,
        industry_context: IndustryContext | None = None
    ) -> CompanyAnalysis:
        """
        Perform company analysis with context from previous agents.

        Args:
            query: The user's investment research query.
            macro_context: Macroeconomic context from macro analyst.
            industry_context: Industry context from industry analyst.

        Returns:
            CompanyAnalysis containing detailed company assessment.
        """
        # Extract symbol from query (simplified for demo)
        symbol = self._extract_symbol(query)
        return self.analyze(symbol)

    def _extract_symbol(self, query: str) -> str:
        """
        Extract stock symbol from user query.

        Args:
            query: The user's investment research query.

        Returns:
            Stock ticker symbol extracted from query.
        """
        # Common company name to symbol mapping
        company_mapping = {
            "tesla": "TSLA",
            "nvidia": "NVDA",
            "apple": "AAPL",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "amazon": "AMZN",
            "meta": "META",
            "facebook": "META"
        }

        query_lower = query.lower()

        # Check for company names
        for name, symbol in company_mapping.items():
            if name in query_lower:
                return symbol

        # Check for uppercase ticker symbols (3-4 letters)
        import re
        tickers = re.findall(r'\b[A-Z]{3,4}\b', query)
        if tickers:
            return tickers[0]

        # Default to Tesla for demo
        return "TSLA"
