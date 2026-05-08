"""Tests for current AI agent modules without external network calls."""

from agents.equity_analyst_ai import EquityAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent
from agents.macro_analyst_ai import MacroAnalystAgent
from agents.report_synthesizer_ai import ReportSynthesizerAgent
from data.schemas import CompanyAnalysis, CompanyData, IndustryContext, MacroContext


class FakeLLM:
    """Minimal LLM stub for tests that do not call the network."""

    def chat(self, messages, system_prompt=None):
        return "{}"


class TestMacroAnalystAgent:
    """Tests for MacroAnalystAgent."""

    def test_create_agent(self):
        agent = MacroAnalystAgent(llm_client=FakeLLM())
        assert agent.role == "Macro Economy Analyst"
        assert agent.goal == "Analyze macroeconomic conditions using real data and AI"

    def test_parse_ai_response_accepts_fenced_json(self):
        agent = MacroAnalystAgent(llm_client=FakeLLM())
        result = agent._parse_ai_response(
            """```json
{"summary": "宏观稳定", "market_sentiment": "bullish"}
```""",
            {
                "gdp_growth": 2.5,
                "inflation_rate": 3.2,
                "interest_rate": 5.25,
                "unemployment_rate": 3.8,
                "data_source": "test-source",
                "is_fallback": False,
            },
        )

        assert isinstance(result, MacroContext)
        assert result.market_sentiment == "bullish"
        assert result.data_source == "test-source"


class TestIndustryAnalystAgent:
    """Tests for IndustryAnalystAgent."""

    def test_create_agent(self):
        agent = IndustryAnalystAgent(llm_client=FakeLLM())
        assert agent.role == "Industry Analyst"

    def test_extract_sector_uses_configured_labels(self):
        agent = IndustryAnalystAgent(llm_client=FakeLLM())
        assert agent._extract_sector("分析比亚迪股票") == "汽车"
        assert agent._extract_sector("EV market analysis") == "汽车"
        assert agent._extract_sector("医疗 sector outlook") == "医疗"
        assert agent._extract_sector("Technology stocks") == "科技"
        assert agent._extract_sector("Unknown sector") == "科技"

    def test_parse_ai_response_normalizes_invalid_outlook(self):
        agent = IndustryAnalystAgent(llm_client=FakeLLM())
        result = agent._parse_ai_response(
            '{"summary": "行业稳健", "outlook": "very positive", "trends": "集中度提升"}',
            "科技",
            {
                "sector_growth": 8.5,
                "data_source": "industry-source",
                "is_fallback": True,
            },
        )

        assert isinstance(result, IndustryContext)
        assert result.outlook == "neutral"
        assert result.trends == ["集中度提升"]
        assert result.is_fallback is True


class TestEquityAnalystAgent:
    """Tests for EquityAnalystAgent."""

    def test_create_agent(self):
        agent = EquityAnalystAgent(llm_client=FakeLLM())
        assert agent.role == "Equity Analyst"

    def test_symbol_format_and_market_metadata(self):
        agent = EquityAnalystAgent(llm_client=FakeLLM())
        assert agent._get_symbol_format("600519") == "sh600519"
        assert agent._get_symbol_format("00700") == "HK00700"
        assert agent._get_market_metadata("HK00700")["currency"] == "HKD"

    def test_extract_symbol_uses_company_mapping(self):
        agent = EquityAnalystAgent(llm_client=FakeLLM())
        assert agent._extract_symbol("分析贵州茅台股票") == "sh600519"
        assert agent._extract_symbol("腾讯控股分析") == "HK00700"
        assert agent._extract_symbol("分析阿里巴巴") == "BABA"
        assert agent._extract_symbol("Unknown company") == "sh600519"

    def test_parse_ai_response_normalizes_signal_and_risks(self):
        agent = EquityAnalystAgent(llm_client=FakeLLM())
        company = CompanyData(
            symbol="sh600519",
            name="贵州茅台",
            sector="白酒",
            market_cap=0.0,
            pe_ratio=0.0,
            current_price=1800.0,
            market="A股",
            currency="CNY",
            data_source="quote-source",
        )

        result = agent._parse_ai_response(
            '{"financial_health": "稳健", "technical_indicator": "strong buy", "risks": "估值风险", "summary": "总结"}',
            company,
            [],
        )

        assert isinstance(result, CompanyAnalysis)
        assert result.technical_indicator == "hold"
        assert result.risks == ["估值风险"]
        assert result.company.data_source == "quote-source"


class TestReportSynthesizerAgent:
    """Tests for ReportSynthesizerAgent."""

    def test_create_agent(self):
        agent = ReportSynthesizerAgent(llm_client=FakeLLM())
        assert agent.role == "Report Synthesizer"

    def test_fallback_report_contains_source_limitations(self):
        agent = ReportSynthesizerAgent(llm_client=FakeLLM())
        macro = MacroContext(
            gdp_growth=2.5,
            inflation_rate=3.2,
            interest_rate=5.25,
            unemployment_rate=3.8,
            market_sentiment="neutral",
            summary="Macro summary",
            data_source="macro-source",
        )
        industry = IndustryContext(
            sector_name="科技",
            sector_growth=8.5,
            competitive_landscape="Competitive",
            regulatory_environment="Stable",
            trends=["AI"],
            outlook="positive",
            summary="Industry summary",
            data_source="industry-source",
        )
        company = CompanyAnalysis(
            company=CompanyData(
                symbol="sh600519",
                name="贵州茅台",
                sector="白酒",
                market_cap=1750.0,
                pe_ratio=65.8,
                current_price=1800.0,
                market="A股",
                currency="CNY",
                data_source="quote-source",
            ),
            financial_health="Strong",
            recent_news=[],
            technical_indicator="buy",
            risks=["估值风险"],
            summary="公司总结",
        )

        report = agent._fallback_partial_synthesize(
            "分析贵州茅台",
            macro,
            industry,
            company,
            market_metadata={
                "market": "A股",
                "currency": "CNY",
                "price_prefix": "¥",
                "data_source": "market-source",
            },
        )

        assert report.recommendation in ["buy", "hold", "sell"]
        assert "# 投资研究报告" in report.full_report
        assert "## 宏观经济分析" in report.full_report
        assert "## 行业分析" in report.full_report
        assert "## 公司分析" in report.full_report
        assert "数据来源与局限性" in report.full_report
        assert report.market == "A股"
        assert "quote-source" in report.data_sources
