"""Tests for mock data generators."""

import pytest
from data.mock_data import (
    get_mock_macro_context,
    get_mock_industry_context,
    get_mock_company_data,
    get_mock_news,
    get_mock_company_analysis
)
from data.schemas import MacroContext, IndustryContext, CompanyData, CompanyAnalysis


class TestGetMockMacroContext:
    """Tests for get_mock_macro_context function."""

    def test_returns_macro_context(self):
        """Test that function returns a MacroContext instance."""
        result = get_mock_macro_context()
        assert isinstance(result, MacroContext)

    def test_macro_context_has_valid_values(self):
        """Test that returned context has reasonable values."""
        result = get_mock_macro_context()
        assert result.gdp_growth > 0
        assert result.inflation_rate > 0
        assert result.market_sentiment in ["bullish", "neutral", "bearish"]


class TestGetMockIndustryContext:
    """Tests for get_mock_industry_context function."""

    def test_returns_industry_context(self):
        """Test that function returns an IndustryContext instance."""
        result = get_mock_industry_context("Technology")
        assert isinstance(result, IndustryContext)

    def test_industry_context_for_technology(self):
        """Test industry context for Technology sector."""
        result = get_mock_industry_context("Technology")
        assert result.sector_name == "Technology"
        assert len(result.trends) > 0

    def test_industry_context_for_automotive(self):
        """Test industry context for Automotive sector."""
        result = get_mock_industry_context("Automotive")
        assert result.sector_name == "Automotive"

    def test_industry_context_for_healthcare(self):
        """Test industry context for Healthcare sector."""
        result = get_mock_industry_context("Healthcare")
        assert result.sector_name == "Healthcare"

    def test_default_industry_context(self):
        """Test default industry context for unknown sector."""
        result = get_mock_industry_context("Unknown")
        assert result.sector_name == "Unknown"


class TestGetMockCompanyData:
    """Tests for get_mock_company_data function."""

    def test_returns_company_data(self):
        """Test that function returns a CompanyData instance."""
        result = get_mock_company_data("TSLA")
        assert isinstance(result, CompanyData)

    def test_tesla_company_data(self):
        """Test company data for Tesla."""
        result = get_mock_company_data("TSLA")
        assert result.symbol == "TSLA"
        assert result.name == "Tesla, Inc."

    def test_nvidia_company_data(self):
        """Test company data for NVIDIA."""
        result = get_mock_company_data("NVDA")
        assert result.symbol == "NVDA"
        assert result.name == "NVIDIA Corporation"

    def test_apple_company_data(self):
        """Test company data for Apple."""
        result = get_mock_company_data("AAPL")
        assert result.symbol == "AAPL"

    def test_case_insensitive_symbol(self):
        """Test that symbol lookup is case insensitive."""
        result_lower = get_mock_company_data("tsla")
        result_upper = get_mock_company_data("TSLA")
        assert result_lower.symbol == result_upper.symbol

    def test_default_company_data(self):
        """Test default company data for unknown symbol."""
        result = get_mock_company_data("UNKNOWN")
        assert isinstance(result, CompanyData)


class TestGetMockNews:
    """Tests for get_mock_news function."""

    def test_returns_news_list(self):
        """Test that function returns a list of news items."""
        result = get_mock_news("TSLA")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_tesla_news(self):
        """Test news for Tesla."""
        result = get_mock_news("TSLA")
        assert len(result) == 3
        assert "Tesla" in result[0].title or "EV" in result[0].title

    def test_nvidia_news(self):
        """Test news for NVIDIA."""
        result = get_mock_news("NVDA")
        assert len(result) == 3
        assert "NVIDIA" in result[0].title or "AI" in result[0].title

    def test_default_news(self):
        """Test default news for unknown symbol."""
        result = get_mock_news("UNKNOWN")
        assert len(result) == 3


class TestGetMockCompanyAnalysis:
    """Tests for get_mock_company_analysis function."""

    def test_returns_company_analysis(self):
        """Test that function returns a CompanyAnalysis instance."""
        result = get_mock_company_analysis("TSLA")
        assert isinstance(result, CompanyAnalysis)

    def test_analysis_includes_company(self):
        """Test that analysis includes company data."""
        result = get_mock_company_analysis("AAPL")
        assert result.company.symbol == "AAPL"

    def test_analysis_includes_news(self):
        """Test that analysis includes news items."""
        result = get_mock_company_analysis("TSLA")
        assert len(result.recent_news) > 0

    def test_analysis_includes_risks(self):
        """Test that analysis includes risk factors."""
        result = get_mock_company_analysis("NVDA")
        assert len(result.risks) > 0

    def test_analysis_has_technical_indicator(self):
        """Test that analysis has technical indicator."""
        result = get_mock_company_analysis("TSLA")
        assert result.technical_indicator in ["buy", "hold", "sell"]
