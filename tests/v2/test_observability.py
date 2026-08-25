# tests/v2/test_observability.py
import json
import logging
import time


def test_trace_context(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    from finana import observability as obs
    from finana.config import Settings

    obs.init_logging(Settings())
    with obs.run_trace() as tid:
        assert len(tid) == 32
        assert obs.current_trace_id() == tid
        rec = {"tid": obs.current_trace_id()}
    assert rec["tid"] == tid


def test_logger_writes_json_with_trace(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    from finana import observability as obs
    from finana.config import Settings

    s = Settings()
    s.ensure_dirs()
    obs.init_logging(s, force=True)
    with obs.run_trace():
        logging.getLogger("finana.test").info("hello %s", "world")
    log_file = s.logs_dir / "finana.log"
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    entry = json.loads(lines[-1])
    assert entry["message"] == "hello world"
    assert len(entry["trace_id"]) == 32
    assert entry["level"] == "INFO"


def test_metrics_record_and_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    from finana import observability as obs
    from finana.storage.db import connect

    m = obs.MetricsService(connect(tmp_path / "m.db"))
    for i, v in enumerate([10, 20, 30, 40]):
        m.record("analysis.latency_ms", v, stage="harness")
        time.sleep(0.001)
    s = m.summary("analysis.latency_ms", since=time.time() - 60)
    assert s["count"] == 4
    assert s["avg"] == 25
    assert s["p50"] == 20
    assert s["max"] == 40
