"""Industry Analyst Agent."""

import re
from data.schemas import IndustryContext
from data.mock_data import get_mock_industry_context


class IndustryAnalystAgent:
    """
    Analyst agent responsible for industry/sector analysis.

    This agent evaluates specific industry sectors including growth rates,
    competitive dynamics, regulatory environment, and key trends.
    """

    def __init__(self, llm_config: dict | None = None):
        """
        Initialize the Industry Analyst Agent.

        Args:
            llm_config: Optional LLM configuration for future enhancement.
                       Currently uses simulated data for demo purposes.
        """
        self.role = "Industry Analyst"
        self.goal = "Analyze industry sectors and provide investment context"
        self.llm_config = llm_config

    def analyze(self, sector: str = "Technology") -> IndustryContext:
        """
        Perform industry analysis for a given sector.

        Args:
            sector: The industry sector to analyze.

        Returns:
            IndustryContext containing sector analysis and outlook.
        """
        return get_mock_industry_context(sector)

    def analyze_with_context(
        self,
        query: str,
        macro_context: IndustryContext | None = None
    ) -> IndustryContext:
        """
        Perform industry analysis with context from previous agents.

        Args:
            query: The user's investment research query.
            macro_context: Optional macro context for integrated analysis.

        Returns:
            IndustryContext containing sector analysis and outlook.
        """
        # Extract sector from query (simplified for demo)
        sector = self._extract_sector(query)
        return self.analyze(sector)

    def _extract_sector(self, query: str) -> str:
        """
        Extract sector/industry from user query.

        Args:
            query: The user's investment research query.

        Returns:
            Sector name extracted from query.
        """
        query_lower = query.lower()

        # Check for exact sector names first (highest priority)
        if "healthcare" in query_lower or "health " in query_lower or query_lower.endswith(" health"):
            return "Healthcare"
        if "automotive" in query_lower or "auto " in query_lower or " ev " in query_lower or query_lower.endswith(" ev"):
            return "Automotive"
        if "technology" in query_lower or "tech " in query_lower or query_lower.endswith(" tech"):
            return "Technology"

        # Check for specific company/sector keywords
        sector_keywords = {
            "automotive": ["tesla", "car", "auto", "ev", "electric vehicle"],
            "healthcare": ["pharma", "biotech", "medical", "drug"],
            "technology": ["software", "ai", "semiconductor", "chip", "nvidia", "apple", "microsoft"]
        }

        for sector, keywords in sector_keywords.items():
            for keyword in keywords:
                if re.search(rf'\b{keyword}\b', query_lower):
                    if sector == "automotive":
                        return "Automotive"
                    elif sector == "healthcare":
                        return "Healthcare"
                    else:
                        return "Technology"

        # Default to Technology if no sector identified
        return "Technology"
