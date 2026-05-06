"""Focused contract tests for the production workflow path."""

from api.routers import analysis
from agents.contracts import AgentResult, AgentRunMetadata, AgentTask, Evidence
from agents.prompt_loader import load_prompt
from agents.structured_output import (
    extract_json_object,
    normalize_choice,
    normalize_string_list,
    repair_json_response,
)
from agents.report_synthesizer_ai import ReportSynthesizerAgent
from data.schemas import CompanyAnalysis, CompanyData, MacroContext, ResearchReport
from fastapi.testclient import TestClient
from api.main import app
from memory.stores import compact_conversation_history
from storage.redis_client import RedisClient
from workflows import AIResearchWorkflow
from workflows.langgraph_workflow import AIResearchWorkflow as LangGraphWorkflow
from workflows.hooks import AnalysisLifecycleHooks


def test_workflows_default_export_is_langgraph():
    """The package-level workflow should point to the production LangGraph path."""
    assert AIResearchWorkflow is LangGraphWorkflow


def test_industry_analysis_uses_resolved_sector():
    """Downstream analysis should consume router state instead of re-guessing from query."""
    workflow = object.__new__(LangGraphWorkflow)

    class FakeIndustryAnalyst:
        def __init__(self):
            self.sector = None

        def analyze(self, sector):
            self.sector = sector
            from data.schemas import IndustryContext

            return IndustryContext(
                sector_name=sector,
                sector_growth=9.0,
                competitive_landscape="竞争格局",
                regulatory_environment="监管环境",
                trends=["趋势"],
                outlook="positive",
                summary="行业总结",
            )

    fake = FakeIndustryAnalyst()
    workflow.industry_analyst = fake

    class FakeScheduler:
        def run_industry(self, query, sector, trace_id=None):
            context = fake.analyze(sector)
            result = AgentResult(
                task_id="task-1",
                role="industry_analyst",
                payload=context.model_dump(),
                evidence=[Evidence(source="test-source", content=context.summary)],
                metadata=AgentRunMetadata(agent_role="industry_analyst"),
            )
            return context, result

    workflow.agent_scheduler = FakeScheduler()
    workflow.hooks = AnalysisLifecycleHooks()

    result = workflow._run_industry_analysis(
        {
            "query": "它的行业怎么看",
            "sector": "汽车",
            "messages": [],
        }
    )

    assert fake.sector == "汽车"
    assert result["industry_context"].sector_name == "汽车"
    assert result["agent_results"][0].role == "industry_analyst"


def test_agent_contracts_validate_evidence_and_metadata():
    """Agent boundary contracts should enforce role, confidence, and evidence shape."""
    task = AgentTask(role="macro_analyst", query="Analyze macro", country="us")
    evidence = Evidence(source="macro-source", content="GDP and inflation summary")
    result = AgentResult(
        task_id=task.id,
        role=task.role,
        payload={"market_sentiment": "neutral"},
        confidence=0.75,
        evidence=[evidence],
        metadata=AgentRunMetadata(agent_role=task.role, prompt_version="agents.macro@v1"),
    )

    assert result.task_id == task.id
    assert result.confidence == 0.75
    assert result.evidence[0].source == "macro-source"
    assert result.metadata.prompt_version == "agents.macro@v1"


def test_prompt_loader_reads_versioned_prompt():
    """Prompt loader should expose role prompt metadata for reports and evals."""
    prompt = load_prompt("agents/macro.md")

    assert prompt.version == "v1"
    assert prompt.identifier == "agents.macro@v1"
    assert "宏观经济分析师" in prompt.content


def test_memory_compaction_bounds_large_history():
    """Conversation memory should be compacted before prompt injection."""
    history = [{"role": "assistant", "content": "x" * 1200} for _ in range(5)]

    compacted = compact_conversation_history(history, max_messages=5, max_chars=1000)

    assert "[对话历史压缩]" in compacted
    assert len(compacted) < 1200


def test_report_synthesizer_includes_context_and_market_metadata():
    """Report prompts should carry follow-up context and resolved currency/source metadata."""
    captured = {}

    class FakeLLM:
        def chat(self, messages, system_prompt=None):
            captured["prompt"] = messages[0]["content"]
            return "# 报告\n\n建议持有\n\n## 数据来源与局限性\n\n仅供参考。"

    agent = ReportSynthesizerAgent(llm_client=FakeLLM())
    company = CompanyAnalysis(
        company=CompanyData(
            symbol="HK00700",
            name="腾讯控股",
            sector="科技",
            market_cap=0.0,
            pe_ratio=0.0,
            current_price=300.0,
        ),
        financial_health="稳健",
        recent_news=[],
        technical_indicator="hold",
        risks=["估值风险"],
        summary="公司总结",
    )

    report = agent.synthesize_partial(
        query="它的估值合理吗？",
        company_analysis=company,
        conversation_context="用户: 分析腾讯控股",
        market_metadata={
            "market": "港股",
            "currency": "HKD",
            "price_prefix": "HK$",
            "data_source": "新浪财经 / 东方财富",
        },
    )

    assert report.recommendation == "hold"
    assert "多轮对话上下文" in captured["prompt"]
    assert "用户: 分析腾讯控股" in captured["prompt"]
    assert "HK$300.00 HKD" in captured["prompt"]
    assert "新浪财经 / 东方财富" in captured["prompt"]
    assert report.market == "港股"
    assert report.currency == "HKD"
    assert "新浪财经 / 东方财富" in report.data_sources


def test_structured_output_handles_fenced_json_and_invalid_enums():
    """LLM JSON parsing should handle fenced output and normalize risky values."""
    parsed = extract_json_object(
        """这里是结果：
```json
{"technical_indicator": "STRONG BUY", "risks": "市场波动"}
```
"""
    )

    assert parsed["technical_indicator"] == "STRONG BUY"
    assert normalize_choice(parsed["technical_indicator"], {"buy", "hold", "sell"}, "hold") == "hold"
    assert normalize_string_list(parsed["risks"], ["默认风险"]) == ["市场波动"]


def test_structured_output_repairs_malformed_json_once():
    """Malformed model output should get one repair attempt."""
    class FakeLLM:
        def __init__(self):
            self.calls = 0

        def chat(self, messages, system_prompt=None):
            self.calls += 1
            return '{"summary": "修复后", "market_sentiment": "neutral"}'

    llm = FakeLLM()
    repaired = repair_json_response(llm, "summary: 修复前", '{"summary": "string"}')

    assert llm.calls == 1
    assert extract_json_object(repaired)["summary"] == "修复后"


def test_schema_provenance_fields_have_defaults_and_accept_values():
    """Research schemas should carry provenance without breaking old constructors."""
    macro = MacroContext(
        gdp_growth=2.5,
        inflation_rate=3.2,
        interest_rate=5.25,
        unemployment_rate=3.8,
        market_sentiment="neutral",
        summary="Macro summary",
        data_source="macro-source",
        is_fallback=True,
    )
    company = CompanyData(
        symbol="TSLA",
        name="Tesla",
        sector="汽车",
        market_cap=0.0,
        pe_ratio=0.0,
        current_price=200.0,
        market="美股",
        currency="USD",
        data_source="quote-source",
    )

    assert macro.data_source == "macro-source"
    assert macro.is_fallback is True
    assert company.market == "美股"
    assert company.currency == "USD"


def test_analyze_endpoint_passes_use_cache(monkeypatch):
    """The analyze endpoint should honor AnalysisRequest.use_cache."""
    seen = {}

    class FakeWorkflow:
        def __init__(self, enable_cache=True):
            seen["enable_cache"] = enable_cache
            self.last_from_cache = False

        def execute(self, query, session_id=None):
            return ResearchReport(
                query=query,
                investment_thesis="测试",
                recommendation="hold",
                target_price=None,
                time_horizon="3-6 个月",
                full_report="# Investment Research Report\n\n测试",
            )

    monkeypatch.setattr(analysis, "AIResearchWorkflow", FakeWorkflow)
    analysis.task_store.clear()

    client = TestClient(app)
    response = client.post(
        "/analysis/analyze",
        json={"query": "Analyze TSLA", "use_cache": False},
    )

    assert response.status_code == 200
    assert seen["enable_cache"] is False
    assert response.json()["from_cache"] is False


def test_redis_keyword_search_uses_metadata_query():
    """Keyword cache lookup should read query from metadata JSON, not a missing top-level field."""
    redis_client = object.__new__(RedisClient)

    class FakeRedis:
        def __init__(self):
            self.calls = 0

        def scan(self, cursor, match=None, count=None):
            self.calls += 1
            return 0, ["report:summary:report-1"]

        def hgetall(self, key):
            return {
                "summary": "缓存摘要",
                "metadata": '{"query": "分析特斯拉股票", "symbol": "TSLA"}',
                "created_at": "2026-05-03T00:00:00",
            }

    redis_client.client = FakeRedis()

    results = redis_client._search_by_keywords(["特"], limit=5)

    assert len(results) == 1
    assert results[0]["report_id"] == "report-1"
    assert results[0]["query"] == "分析特斯拉股票"
    assert results[0]["metadata"]["symbol"] == "TSLA"
