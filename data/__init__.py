"""Data layer for FinAna."""

from data.schemas import (
    MacroContext,
    IndustryContext,
    CompanyData,
    NewsItem,
    CompanyAnalysis,
    ResearchReport
)
from data.mock_data import (
    get_mock_macro_context,
    get_mock_industry_context,
    get_mock_company_data,
    get_mock_news,
    get_mock_company_analysis
)
from data.finance_data import FinancialDataFetcher, get_data_fetcher

__all__ = [
    "MacroContext",
    "IndustryContext",
    "CompanyData",
    "NewsItem",
    "CompanyAnalysis",
    "ResearchReport",
    "get_mock_macro_context",
    "get_mock_industry_context",
    "get_mock_company_data",
    "get_mock_news",
    "get_mock_company_analysis",
    "FinancialDataFetcher",
    "get_data_fetcher"
]
