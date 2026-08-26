from __future__ import annotations

import builtins
import re

import pytest

from finana.cli import main, parse_profile_args, render_result
from finana.harness_adapter import HarnessUnavailable
from finana.memory.service import MemoryService
from finana.orchestrator import AnalysisResult
from finana.prediction.parser import PredictionDraft
from finana.storage.db import connect


class FakeOrchestrator:
    def __init__(self, memory=None):
        self.memory = memory
        self.calls = []
        self._outcomes = []

    def queue(self, outcome):
        self._outcomes.append(outcome)

    def analyze(self, query, session_id=None):
        self.calls.append((query, session_id))
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return AnalysisResult(
            response_md=outcome["response_md"],
            prediction=outcome.get("prediction"),
            prediction_id=outcome.get("prediction_id"),
            trace_id=outcome.get("trace_id", "trace-1"),
            session_id=session_id or "sid-1",
        )


_PRED = PredictionDraft(
    direction="up",
    confidence=0.62,
    target_low=1680.0,
    target_high=1850.0,
    horizon_days=30,
    invalidation=["跌破均线", "放量滞涨"],
)


def test_once_happy_path_prints_response_and_prediction_card(capsys):
    fake = FakeOrchestrator()
    fake.queue({"response_md": "特斯拉基本面稳健", "prediction": _PRED, "prediction_id": 12})
    with pytest.raises(SystemExit) as excinfo:
        main(["--once", "分析特斯拉"], factory=lambda: fake)
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "特斯拉基本面稳健" in out
    assert "方向: up" in out
    assert "置信度: 0.62" in out
    assert "1680.0 – 1850.0" in out
    assert "期限: 30 天" in out
    assert "ID: pred #12" in out
    assert "失效条件: 跌破均线; 放量滞涨" in out


def test_once_harness_unavailable_stderr_trace_exit_2(capsys):
    fake = FakeOrchestrator()
    fake.queue(HarnessUnavailable("harness 连续两次运行失败；最后错误：boom"))
    with pytest.raises(SystemExit) as excinfo:
        main(["--once", "分析特斯拉"], factory=lambda: fake)
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "分析失败(HarnessUnavailable): harness 连续两次运行失败；最后错误：boom" in err
    assert re.search(r"trace=[0-9a-f]+", err)


def test_repl_profile_set_persists_via_real_memory_service(tmp_path, capsys, monkeypatch):
    svc = MemoryService(connect(tmp_path / "m.db"))
    fake = FakeOrchestrator(memory=svc)
    lines = iter(["/profile set risk=保守", "/session", "/quit"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(lines))
    with pytest.raises(SystemExit) as excinfo:
        main([], factory=lambda: fake)
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert svc.get_profile()["risk_preference"] == "保守"
    assert "画像已更新: risk_preference=保守" in out
    assert "当前会话: " in out
    assert len(re.findall(r"\b[0-9a-f]{32}\b", out)) >= 2


def test_repl_profile_show_without_args(tmp_path, capsys, monkeypatch):
    svc = MemoryService(connect(tmp_path / "m.db"))
    fake = FakeOrchestrator(memory=svc)
    lines = iter(["/profile", "/quit"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(lines))
    with pytest.raises(SystemExit):
        main([], factory=lambda: fake)
    out = capsys.readouterr().out
    assert "用户画像:" in out
    assert "watchlist=-" in out


def test_repl_harness_unavailable_keeps_loop_alive(capsys, monkeypatch):
    fake = FakeOrchestrator()
    fake.queue(HarnessUnavailable("harness 连续两次运行失败"))
    fake.queue({"response_md": "恢复后的结论"})
    lines = iter(["问题一", "问题二", "/quit"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(lines))
    with pytest.raises(SystemExit) as excinfo:
        main([], factory=lambda: fake)
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "分析失败(HarnessUnavailable)" in captured.err
    assert "恢复后的结论" in captured.out
    assert len(fake.calls) == 2


def test_parse_profile_args_valid_mapping():
    assert parse_profile_args("risk=保守 style=趋势") == {
        "risk_preference": "保守",
        "style": "趋势",
    }
    assert parse_profile_args("") == {}


@pytest.mark.parametrize("raw", ["foo=1", "risk", "risk="])
def test_parse_profile_args_invalid_raises_value_error(raw):
    with pytest.raises(ValueError):
        parse_profile_args(raw)


def test_new_reuses_single_factory_instance_and_rotates_session(monkeypatch, capsys):
    fake = FakeOrchestrator()
    fake.queue({"response_md": "结论一"})
    fake.queue({"response_md": "结论二"})
    created = []

    def factory():
        created.append(fake)
        return fake

    lines = iter(["", "/new", "问题一", "问题二", "/quit"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(lines))
    with pytest.raises(SystemExit) as excinfo:
        main([], factory=factory)
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "新会话: " in out
    assert len(created) == 1
    assert len(fake.calls) == 2
    assert fake.calls[0][0] == "问题一"
    assert fake.calls[1][0] == "问题二"
    match = re.search(r"新会话: ([0-9a-f]{32})", out)
    assert match is not None
    assert fake.calls[0][1] == match.group(1)
    assert fake.calls[1][1] == match.group(1)


def test_render_result_passthrough_without_prediction():
    res = AnalysisResult(
        response_md="只有正文",
        prediction=None,
        prediction_id=None,
        trace_id="t",
        session_id="s",
    )
    assert render_result(res) == "只有正文"


def test_render_result_prediction_card_marks_new_without_id():
    res = AnalysisResult(
        response_md="正文",
        prediction=_PRED,
        prediction_id=None,
        trace_id="t",
        session_id="s",
    )
    text = render_result(res)
    assert text.startswith("正文")
    assert "ID: new" in text
    assert text.count("│") >= 8
