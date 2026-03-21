"""Macro Economy Analyst Agent."""

from data.schemas import MacroContext
from data.mock_data import get_mock_macro_context


class MacroAnalystAgent:
    """
    Analyst agent responsible for macroeconomic analysis.

    This agent evaluates overall economic conditions including GDP growth,
    inflation, interest rates, and market sentiment to provide context
    for investment decisions.
    """

    def __init__(self, llm_config: dict | None = None):
        """
        Initialize the Macro Analyst Agent.

        Args:
            llm_config: Optional LLM configuration for future enhancement.
                       Currently uses simulated data for demo purposes.
        """
        self.role = "Macro Economy Analyst"
        self.goal = "Analyze macroeconomic conditions and provide investment context"
        self.llm_config = llm_config

    def analyze(self) -> MacroContext:
        """
        Perform macroeconomic analysis.

        Returns:
            MacroContext containing economic indicators and analysis summary.
        """
        # In demo mode, return simulated data
        # In production, this would call LLM with real economic data
        return get_mock_macro_context()

    def analyze_with_context(self, query: str) -> MacroContext:
        """
        Perform macroeconomic analysis with user query context.

        Args:
            query: The user's investment research query.

        Returns:
            MacroContext containing economic indicators and analysis summary.
        """
        # For now, same analysis regardless of query
        # Future enhancement: tailor analysis based on query specifics
        return self.analyze()
