import logging
from types import SimpleNamespace

import pytest

from finana.harness_adapter import (
    AnalysisOutcome,
    FakeHarness,
    HarnessAdapter,
    HarnessUnavailable,
    write_npm_wrapper,
)


class _ScriptDriver:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []
        self.closed = False

    def run(self, prompt, *, session_id):
        self.calls.append((prompt, session_id))
        if len(self.results) > 1:
            return self.results.pop(0)
        return self.results[0]

    def close(self):
        self.closed = True


class _BoomDriver:
    def __init__(self):
        self.closed = False

    def run(self, prompt, *, session_id):
        raise RuntimeError("boom")

    def close(self):
        self.closed = True


def _adapter(monkeypatch, builders):
    built = []
    state = {"i": 0}

    def _build(self):
        driver = builders[min(state["i"], len(builders) - 1)]()
        state["i"] += 1
        built.append(driver)
        return driver

    monkeypatch.setattr(HarnessAdapter, "_build_driver", _build)
    return HarnessAdapter(), built


def _sdk_result(final_response="结论", finish_reason="stop", events=None):
    if events is None:
        events = [
            {"type": "assistant/message", "data": {"usage": {"inputTokens": 10, "outputTokens": 4}}},
            {"type": "assistant/message", "data": {"usage": {"inputTokens": 5}}},
            {"type": "tool", "data": {"usage": {"inputTokens": 999}}},
            {"type": "assistant/message"},
        ]
    return SimpleNamespace(final_response=final_response, finish_reason=finish_reason, events=events)


def test_run_success_passthrough_and_usage_summed(monkeypatch):
    driver = SimpleNamespace(run=lambda prompt, session_id: _sdk_result(), close=lambda: None)
    monkeypatch.setattr(HarnessAdapter, "_build_driver", lambda self: driver)
    adapter = HarnessAdapter()

    outcome = adapter.run("分析特斯拉", "sess-1")

    assert outcome.final_response == "结论"
    assert outcome.finish_reason == "stop"
    assert outcome.usage == {"inputTokens": 15, "outputTokens": 4}
    assert outcome.session_id == "sess-1"


def test_missing_usage_yields_empty_dict(monkeypatch):
    driver = SimpleNamespace(
        run=lambda prompt, session_id: _sdk_result(events=[{"type": "assistant/message"}]),
        close=lambda: None,
    )
    monkeypatch.setattr(HarnessAdapter, "_build_driver", lambda self: driver)

    outcome = HarnessAdapter().run("q", "s")

    assert outcome.usage == {}


def test_error_finish_reason_rebuilds_and_retries(monkeypatch):
    err = AnalysisOutcome(final_response="", finish_reason="error")
    ok = AnalysisOutcome(final_response="恢复后成功", finish_reason="complete")
    adapter, built = _adapter(monkeypatch, [lambda: FakeHarness([err]), lambda: FakeHarness([ok])])

    outcome = adapter.run("q", "sess-9")

    assert outcome.final_response == "恢复后成功"
    assert outcome.session_id == "sess-9"
    assert len(built) == 2
    assert built[0].closed is True


def test_two_failures_raise_harness_unavailable(monkeypatch, caplog):
    import finana.harness_adapter as ha

    recorded = []

    class _FakeMetrics:
        def record(self, name, value=1, **tags):
            recorded.append((name, value, tags))

    monkeypatch.setattr(ha, "get_metrics", lambda: _FakeMetrics())
    bad = AnalysisOutcome(finish_reason="error")
    adapter, built = _adapter(monkeypatch, [lambda: FakeHarness([bad])])

    with caplog.at_level(logging.WARNING, logger="finana.harness"):
        with pytest.raises(HarnessUnavailable) as excinfo:
            adapter.run("q", "s")

    assert "finish_reason=error" in str(excinfo.value)
    assert len([r for r in caplog.records if r.name == "finana.harness"]) == 2
    assert recorded == [("harness.run", 1, {"finish_reason": "error"})] * 2
    assert len(built) == 2


def test_none_finish_reason_triggers_retry(monkeypatch):
    none_outcome = AnalysisOutcome(final_response="部分输出")
    ok = AnalysisOutcome(final_response="完成", finish_reason="complete")
    adapter, built = _adapter(
        monkeypatch, [lambda: FakeHarness([none_outcome]), lambda: FakeHarness([ok])]
    )

    outcome = adapter.run("q", "s")

    assert outcome.final_response == "完成"
    assert len(built) == 2


def test_driver_exception_follows_same_retry_path(monkeypatch):
    boom = _BoomDriver()
    adapter, built = _adapter(monkeypatch, [lambda: boom, lambda: FakeHarness([AnalysisOutcome(final_response="ok", finish_reason="complete")])])

    outcome = adapter.run("q", "s")

    assert outcome.final_response == "ok"
    assert boom.closed is True
    assert len(built) == 2


def test_fake_harness_records_calls_and_repeats_last():
    harness = FakeHarness([AnalysisOutcome(final_response="a", finish_reason="complete")])

    first = harness.run("p1", "s1")
    second = harness.run("p2", "s2")

    assert first.final_response == "a"
    assert second.final_response == "a"
    assert harness.calls == [("p1", "s1"), ("p2", "s2")]
    harness.close()
    assert harness.closed is True


def test_write_npm_wrapper_content_mode_and_idempotent(tmp_path):
    npm_bin = tmp_path / "dsh.js"
    npm_bin.write_text("console.log(1)\n", encoding="utf-8")
    home = tmp_path / "finana-home"

    wrapper = write_npm_wrapper(home, npm_bin)

    expected = f'#!/bin/sh\nexec node "{npm_bin}" "$@"\n'
    assert wrapper == home / "bin" / "dsh-jsonrpc"
    assert wrapper.read_text(encoding="utf-8") == expected
    assert wrapper.stat().st_mode & 0o755 == 0o755

    mtime = wrapper.stat().st_mtime_ns
    assert write_npm_wrapper(home, npm_bin) == wrapper
    assert wrapper.stat().st_mtime_ns == mtime


def test_build_driver_npm_without_bin_raises(tmp_path):
    from finana.config import Settings

    settings = Settings(finana_home=tmp_path, dsh_runtime="npm", dsh_npm_bin=None)
    adapter = HarnessAdapter(settings=settings)

    with pytest.raises(HarnessUnavailable) as excinfo:
        adapter._build_driver()

    assert "DSH_NPM_BIN" in str(excinfo.value)


def test_build_driver_injects_research_env_and_key(tmp_path, monkeypatch):
    import deepseek_harness

    from finana.config import Settings

    captured = {}

    class _FakeHarness:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run(self, prompt, *, session_id):
            return SimpleNamespace(final_response="x", finish_reason="stop", events=[])

        def close(self):
            pass

    monkeypatch.setattr(deepseek_harness, "DeepSeekHarness", _FakeHarness)
    settings = Settings(
        finana_home=tmp_path,
        dsh_runtime="wheel",
        deepseek_api_key="sk-test",
        deepseek_base_url="https://example",
    )
    adapter = HarnessAdapter(settings=settings)

    driver = adapter._build_driver()

    assert isinstance(driver, _FakeHarness)
    env = captured["env"]
    assert "DSH_SYSTEM_PROMPT" in env and env["DSH_SYSTEM_PROMPT"]
    assert env["FINANA_PYTHON"]
    assert env["FINANA_SKILLS_DIR"].endswith("finana/prompts/skills")
    assert captured["api_key"] == "sk-test"
    assert captured["base_url"] == "https://example"


def test_harness_unavailable_carries_trace_id():
    exc = HarnessUnavailable("boom", trace_id="trace-1")
    assert exc.trace_id == "trace-1"


def test_auto_falls_back_to_npm_on_runtime_error(monkeypatch):
    class _RT:
        def __init__(self, fail):
            self.fail = fail
            self.closed = False

        def run(self, prompt, *, session_id):
            if self.fail:
                raise FileNotFoundError(
                    "Unable to locate the bundled DeepSeek Harness SDK runtime."
                )
            return SimpleNamespace(final_response="ok", finish_reason="stop", events=[])

        def close(self):
            self.closed = True

    state = {"i": 0}

    def _build(self):
        if state["i"] == 0:
            state["i"] = 1
            return _RT(fail=True)
        return _RT(fail=False)

    monkeypatch.setattr(HarnessAdapter, "_build_driver", _build)
    adapter = HarnessAdapter()
    adapter.settings.dsh_runtime = "auto"

    outcome = adapter.run("分析600519", "s1")

    assert outcome.final_response == "ok"
    assert adapter._force_npm is True