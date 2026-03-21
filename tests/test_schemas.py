"""Tests for data schemas."""

import pytest
from data.schemas import (
    MacroContext,
    IndustryContext,
    CompanyData,
    NewsItem,
    CompanyAnalysis,
    ResearchReport
)
from datetime import datetime


class TestMacroContext:
    """Tests for MacroContext schema."""

    def test_create_macro_context(self):
        """Test creating a valid MacroContext."""
        context = MacroContext(
            gdp_growth=2.5,
            inflation_rate=3.2,
            interest_rate=5.25,
            unemployment_rate=3.8,
            market_sentiment="neutral",
            summary="Test summary"
        )
        assert context.gdp_growth == 2.5
        assert context.market_sentiment == "neutral"

    def test_macro_context_validates_types(self):
        """Test that MacroContext validates field types."""
        context = MacroContext(
            gdp_growth="2.5",  # Should be converted to float
            inflation_rate=3.2,
            interest_rate=5.25,
            unemployment_rate=3.8,
            market_sentiment="bullish",
            summary="Test"
        )
        assert context.gdp_growth == 2.5


class TestIndustryContext:
    """Tests for IndustryContext schema."""

    def test_create_industry_context(self):
        """Test creating a valid IndustryContext."""
        context = IndustryContext(
            sector_name="Technology",
            sector_growth=8.5,
            competitive_landscape="Competitive",
            regulatory_environment="Stable",
            trends=["AI adoption", "Cloud growth"],
            outlook="positive",
            summary="Test summary"
        )
        assert context.sector_name == "Technology"
        assert len(context.trends) == 2
        assert context.outlook == "positive"


class TestCompanyData:
    """Tests for CompanyData schema."""

    def test_create_company_data(self):
        """Test creating a valid CompanyData."""
        data = CompanyData(
            symbol="AAPL",
            name="Apple Inc.",
            sector="Technology",
            market_cap=2650.0,
            pe_ratio=28.5,
            current_price=172.75
        )
        assert data.symbol == "AAPL"
        assert data.market_cap == 2650.0


class TestNewsItem:
    """Tests for NewsItem schema."""

    def test_create_news_item(self):
        """Test creating a valid NewsItem."""
        news = NewsItem(
            title="Test Headline",
            source="Test Source",
            published_at=datetime.now(),
            sentiment="positive",
            summary="Test summary"
        )
        assert news.sentiment == "positive"
        assert news.title == "Test Headline"


class TestCompanyAnalysis:
    """Tests for CompanyAnalysis schema."""

    def test_create_company_analysis(self):
        """Test creating a valid CompanyAnalysis."""
        company = CompanyData(
            symbol="TSLA",
            name="Tesla, Inc.",
            sector="Automotive",
            market_cap=580.5,
            pe_ratio=45.2,
            current_price=185.50
        )
        analysis = CompanyAnalysis(
            company=company,
            financial_health="Strong",
            recent_news=[],
            technical_indicator="buy",
            risks=["Risk 1"],
            summary="Test summary"
        )
        assert analysis.company.symbol == "TSLA"
        assert analysis.technical_indicator == "buy"
        assert len(analysis.risks) == 1


class TestResearchReport:
    """Tests for ResearchReport schema."""

    def test_create_research_report(self):
        """Test creating a valid ResearchReport."""
        macro = MacroContext(
            gdp_growth=2.5,
            inflation_rate=3.2,
            interest_rate=5.25,
            unemployment_rate=3.8,
            market_sentiment="neutral",
            summary="Macro summary"
        )
        industry = IndustryContext(
            sector_name="Technology",
            sector_growth=8.5,
            competitive_landscape="Competitive",
            regulatory_environment="Stable",
            trends=["AI"],
            outlook="positive",
            summary="Industry summary"
        )
        company = CompanyData(
            symbol="NVDA",
            name="NVIDIA Corporation",
            sector="Technology",
            market_cap=1750.0,
            pe_ratio=65.8,
            current_price=722.48
        )
        company_analysis = CompanyAnalysis(
            company=company,
            financial_health="Strong",
            recent_news=[],
            technical_indicator="buy",
            risks=["Risk 1"],
            summary="Company summary"
        )
        report = ResearchReport(
            query="Analyze NVDA",
            macro_analysis=macro,
            industry_analysis=industry,
            company_analysis=company_analysis,
            investment_thesis="AI growth driver",
            recommendation="buy",
            target_price=800.0,
            time_horizon="3-6 months",
            full_report="# Report"
        )
        assert report.query == "Analyze NVDA"
        assert report.recommendation == "buy"
        assert report.target_price == 800.0
