"""Tests for agent modules."""

import pytest
from agents.macro_analyst import MacroAnalystAgent
from agents.industry_analyst import IndustryAnalystAgent
from agents.equity_analyst import EquityAnalystAgent
from agents.report_synthesizer import ReportSynthesizerAgent
from data.schemas import MacroContext, IndustryContext, CompanyAnalysis, CompanyData, NewsItem


class TestMacroAnalystAgent:
    """Tests for MacroAnalystAgent."""

    def test_create_agent(self):
        """Test creating a MacroAnalystAgent."""
        agent = MacroAnalystAgent()
        assert agent.role == "Macro Economy Analyst"
        assert agent.goal == "Analyze macroeconomic conditions and provide investment context"

    def test_analyze_returns_macro_context(self):
        """Test that analyze returns a MacroContext."""
        agent = MacroAnalystAgent()
        result = agent.analyze()
        assert isinstance(result, MacroContext)

    def test_analyze_with_context(self):
        """Test analyze_with_context method."""
        agent = MacroAnalystAgent()
        result = agent.analyze_with_context("Analyze Tesla")
        assert isinstance(result, MacroContext)
        assert result.gdp_growth > 0


class TestIndustryAnalystAgent:
    """Tests for IndustryAnalystAgent."""

    def test_create_agent(self):
        """Test creating an IndustryAnalystAgent."""
        agent = IndustryAnalystAgent()
        assert agent.role == "Industry Analyst"

    def test_analyze_technology(self):
        """Test analyzing Technology sector."""
        agent = IndustryAnalystAgent()
        result = agent.analyze("Technology")
        assert result.sector_name == "Technology"

    def test_analyze_automotive(self):
        """Test analyzing Automotive sector."""
        agent = IndustryAnalystAgent()
        result = agent.analyze("Automotive")
        assert result.sector_name == "Automotive"

    def test_extract_sector_automotive(self):
        """Test sector extraction for automotive keywords."""
        agent = IndustryAnalystAgent()
        assert agent._extract_sector("Analyze Tesla stock") == "Automotive"
        assert agent._extract_sector("EV market analysis") == "Automotive"

    def test_extract_sector_healthcare(self):
        """Test sector extraction for healthcare keywords."""
        agent = IndustryAnalystAgent()
        assert agent._extract_sector("Healthcare sector outlook") == "Healthcare"
        assert agent._extract_sector("Health industry analysis") == "Healthcare"

    def test_extract_sector_technology(self):
        """Test sector extraction for technology keywords."""
        agent = IndustryAnalystAgent()
        assert agent._extract_sector("Technology stocks") == "Technology"
        assert agent._extract_sector("AI companies") == "Technology"

    def test_extract_sector_default(self):
        """Test default sector extraction."""
        agent = IndustryAnalystAgent()
        assert agent._extract_sector("Unknown sector") == "Technology"


class TestEquityAnalystAgent:
    """Tests for EquityAnalystAgent."""

    def test_create_agent(self):
        """Test creating an EquityAnalystAgent."""
        agent = EquityAnalystAgent()
        assert agent.role == "Equity Analyst"

    def test_analyze_tesla(self):
        """Test analyzing Tesla stock."""
        agent = EquityAnalystAgent()
        result = agent.analyze("TSLA")
        assert result.company.symbol == "TSLA"

    def test_analyze_nvidia(self):
        """Test analyzing NVIDIA stock."""
        agent = EquityAnalystAgent()
        result = agent.analyze("NVDA")
        assert result.company.symbol == "NVDA"

    def test_extract_symbol_tesla(self):
        """Test symbol extraction for Tesla."""
        agent = EquityAnalystAgent()
        assert agent._extract_symbol("Analyze Tesla stock") == "TSLA"

    def test_extract_symbol_nvidia(self):
        """Test symbol extraction for NVIDIA."""
        agent = EquityAnalystAgent()
        assert agent._extract_symbol("Buy NVIDIA") == "NVDA"

    def test_extract_symbol_apple(self):
        """Test symbol extraction for Apple."""
        agent = EquityAnalystAgent()
        assert agent._extract_symbol("Apple Inc analysis") == "AAPL"

    def test_extract_symbol_direct_ticker(self):
        """Test direct ticker symbol extraction."""
        agent = EquityAnalystAgent()
        assert agent._extract_symbol("Analyze MSFT stock") == "MSFT"

    def test_extract_symbol_default(self):
        """Test default symbol extraction."""
        agent = EquityAnalystAgent()
        assert agent._extract_symbol("Unknown company") == "TSLA"


class TestReportSynthesizerAgent:
    """Tests for ReportSynthesizerAgent."""

    def test_create_agent(self):
        """Test creating a ReportSynthesizerAgent."""
        agent = ReportSynthesizerAgent()
        assert agent.role == "Report Synthesizer"

    def test_synthesize_report(self):
        """Test synthesizing a complete report."""
        macro = MacroContext(
            gdp_growth=2.5,
            inflation_rate=3.2,
            interest_rate=5.25,
            unemployment_rate=3.8,
            market_sentiment="neutral",
            summary="Test macro"
        )
        industry = IndustryContext(
            sector_name="Technology",
            sector_growth=8.5,
            competitive_landscape="Test",
            regulatory_environment="Test",
            trends=["AI"],
            outlook="positive",
            summary="Test industry"
        )
        company_data = CompanyData(
            symbol="NVDA",
            name="NVIDIA",
            sector="Technology",
            market_cap=1750.0,
            pe_ratio=65.8,
            current_price=722.48
        )
        company = CompanyAnalysis(
            company=company_data,
            financial_health="Strong",
            recent_news=[],
            technical_indicator="buy",
            risks=["Risk 1"],
            summary="Test company"
        )

        agent = ReportSynthesizerAgent()
        result = agent.synthesize(
            query="Analyze NVDA",
            macro_context=macro,
            industry_context=industry,
            company_analysis=company
        )

        assert result.query == "Analyze NVDA"
        assert result.recommendation in ["buy", "hold", "sell"]
        assert "# Investment Research Report" in result.full_report

    def test_generate_recommendation_buy_positive(self):
        """Test recommendation generation for buy + positive."""
        agent = ReportSynthesizerAgent()

        company_data = CompanyData(
            symbol="NVDA",
            name="NVIDIA",
            sector="Technology",
            market_cap=1750.0,
            pe_ratio=30.0,
            current_price=100.0
        )
        company = CompanyAnalysis(
            company=company_data,
            financial_health="Strong",
            recent_news=[],
            technical_indicator="buy",
            risks=[],
            summary="Test"
        )
        industry = IndustryContext(
            sector_name="Technology",
            sector_growth=10.0,
            competitive_landscape="Test",
            regulatory_environment="Test",
            trends=[],
            outlook="positive",
            summary="Test"
        )

        rec, price = agent._generate_recommendation(company, industry)
        assert rec == "buy"
        assert price > 100.0  # Target price higher than current

    def test_generate_report_contains_sections(self):
        """Test that generated report contains all sections."""
        agent = ReportSynthesizerAgent()

        macro = MacroContext(
            gdp_growth=2.5,
            inflation_rate=3.2,
            interest_rate=5.25,
            unemployment_rate=3.8,
            market_sentiment="neutral",
            summary="Test"
        )
        industry = IndustryContext(
            sector_name="Technology",
            sector_growth=8.5,
            competitive_landscape="Test",
            regulatory_environment="Test",
            trends=["Trend 1"],
            outlook="positive",
            summary="Test"
        )
        company_data = CompanyData(
            symbol="AAPL",
            name="Apple",
            sector="Technology",
            market_cap=2650.0,
            pe_ratio=28.5,
            current_price=172.75
        )
        company = CompanyAnalysis(
            company=company_data,
            financial_health="Strong",
            recent_news=[],
            technical_indicator="hold",
            risks=["Risk 1"],
            summary="Test"
        )

        report = agent.synthesize("Analyze AAPL", macro, industry, company)

        assert "## Macroeconomic Analysis" in report.full_report
        assert "## Industry Analysis" in report.full_report
        assert "## Company Analysis" in report.full_report
