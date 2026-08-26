import json
import time

import pytest

from finana.config import get_settings
from finana.harness_adapter import AnalysisOutcome, FakeHarness, HarnessUnavailable
from finana.memory.service import MemoryService
from finana.observability import MetricsService
from finana.orchestrator import AnalysisResult, Orchestrator, resolve_symbol_local
from finana.storage.db import connect

_PREDICTION = {
    "direction": "up",
    "confidence": 0.8,
    "target_low": 210.0,
    "target_high": 260.0,
    "horizon_days": 30,
    "invalidation": ["跌破200日均线"],
    "rationale": "需求强劲",
}


def _memory(tmp_path):
    return MemoryService(connect(tmp_path / "mem.db"))


def _metrics(tmp_path):
    return MetricsService(connect(tmp_path / "metrics.db"))


def _outcome(text, finish="stop"):
    return AnalysisOutcome(final_response=text, finish_reason=finish, usage={}, session_id="")


def _prediction_text():
    return (
        "## 分析\n基本面看好。\n\n```json\n"
        + json.dumps(_PREDICTION, ensure_ascii=False)
        + "\n```"
    )


def test_end_to_end_with_valid_prediction_block(tmp_path):
    mem = _memory(tmp_path)
    metrics = _metrics(tmp_path)
    orch = Orchestrator(
        memory=mem,
        adapter=FakeHarness([_outcome(_prediction_text())]),
        metrics=metrics,
    )
    result = orch.analyze("分析600519未来走势", session_id="s-fix")

    assert isinstance(result, AnalysisResult)
    assert result.from_memory_only is False
    assert result.session_id == "s-fix"
    assert result.trace_id
    assert result.prediction is not None
    assert result.prediction.direction == "up"
    assert isinstance(result.prediction_id, int)

    due = mem.due_predictions(time.time() + 31 * 86400)
    saved = [p for p in due if p["symbol"] == "600519.SH"]
    assert len(saved) == 1
    assert saved[0]["trace_id"] == result.trace_id
    assert saved[0]["confidence"] == 0.8

    info = mem.get_instrument("600519.SH")
    assert info is not None and len(info["conclusions"]) == 1

    assert mem.symbol_for_session("s-fix") == "600519.SH"

    reports = list((get_settings().finana_home.expanduser() / "reports").glob("*.md"))
    assert len(reports) == 1
    content = reports[0].read_text(encoding="utf-8")
    assert result.trace_id in content
    assert "s-fix" in content

    summary = metrics.summary("analysis.latency_ms", 0)
    assert summary["count"] == 1


def test_no_prediction_block_skips_writeback(tmp_path):
    mem = _memory(tmp_path)
    orch = Orchestrator(
        memory=mem,
        adapter=FakeHarness([_outcome("## 普通分析\n没有结构化结论。")]),
        metrics=_metrics(tmp_path),
    )
    result = orch.analyze("看看000001.SZ", session_id="s-np")

    assert result.prediction is None
    assert result.prediction_id is None
    assert "普通分析" in result.response_md
    assert result.trace_id

    assert mem.get_instrument("000001.SZ") is None
    assert mem.symbol_for_session("s-np") == "000001.SZ"

    reports = list((get_settings().finana_home.expanduser() / "reports").glob("*.md"))
    assert len(reports) == 1


def test_query_without_symbol_skips_persistence_and_binding(tmp_path):
    mem = _memory(tmp_path)
    orch = Orchestrator(
        memory=mem,
        adapter=FakeHarness([_outcome(_prediction_text())]),
        metrics=_metrics(tmp_path),
    )
    result = orch.analyze("最近市场怎么样？", session_id="s-general")

    assert result.prediction is not None
    assert result.prediction_id is None
    assert result.session_id == "s-general"

    assert mem.due_predictions(time.time() + 31 * 86400) == []
    assert mem.symbol_for_session("s-general") is None

    reports = list((get_settings().finana_home.expanduser() / "reports").glob("*.md"))
    assert len(reports) == 1
    assert reports[0].name.endswith("-general.md")


class _RaisingHarness(FakeHarness):
    def run(self, prompt, session_id):
        raise HarnessUnavailable("harness down")


def test_harness_unavailable_propagates(tmp_path):
    orch = Orchestrator(
        memory=_memory(tmp_path),
        adapter=_RaisingHarness([_outcome("x")]),
        metrics=_metrics(tmp_path),
    )
    with pytest.raises(HarnessUnavailable):
        orch.analyze("分析600519")


def test_abnormal_finish_uses_fallback_text(tmp_path):
    mem = _memory(tmp_path)
    orch = Orchestrator(
        memory=mem,
        adapter=FakeHarness([_outcome(_prediction_text(), finish="error")]),
        metrics=_metrics(tmp_path),
    )
    result = orch.analyze("分析600519")
    assert result.response_md == "分析未能完成，请稍后重试"
    assert result.prediction is None
    assert result.prediction_id is None


def test_resolve_symbol_local_codes_and_none(tmp_path):
    mem = _memory(tmp_path)
    assert resolve_symbol_local("600519", mem) == "600519.SH"
    assert resolve_symbol_local("贵州茅台", mem) is None
    assert resolve_symbol_local("000001.SZ", mem) == "000001.SZ"


def test_prompt_includes_context_block_and_user_question(tmp_path):
    mem = _memory(tmp_path)
    mem.remember_semantic("特斯拉供应链本土化率持续提升", tags="行业")
    fake = FakeHarness([_outcome("好的，已结合记忆。")])
    orch = Orchestrator(memory=mem, adapter=fake, metrics=_metrics(tmp_path))
    query = "特斯拉 前景如何"
    result = orch.analyze(query, session_id="s-ctx")

    prompt, sid = fake.calls[0]
    assert prompt.endswith(f"用户问题: {query}")
    assert "[L3] 相关记忆" in prompt
    assert "特斯拉供应链本土化率持续提升" in prompt
    assert sid == "s-ctx"
    assert result.session_id == "s-ctx"
