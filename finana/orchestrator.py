from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass

from finana.config import get_settings
from finana.datacore.symbols import normalize_symbol
from finana.harness_adapter import HarnessAdapter
from finana.memory.service import MemoryService
from finana.observability import get_metrics, run_trace
from finana.prediction.parser import PredictionDraft, parse_prediction
from finana.storage.db import get_db

_MD_SYMBOLS_RE = re.compile(r"[#*`_~|\[\]()>-]+")
_CODE_SUFFIXED_RE = re.compile(r"(?<![\dA-Za-z.])(\d{6})\.(SH|SZ|BJ)", re.IGNORECASE)
_CODE_PLAIN_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")

_FALLBACK_TEXT = "分析未能完成，请稍后重试"


@dataclass
class AnalysisResult:
    response_md: str
    prediction: PredictionDraft | None
    prediction_id: int | None
    trace_id: str
    session_id: str
    from_memory_only: bool = False


def resolve_symbol_local(query: str, memory: MemoryService) -> str | None:
    m = _CODE_SUFFIXED_RE.search(query or "")
    if m is not None:
        raw = f"{m.group(1)}.{m.group(2).upper()}"
    else:
        plain = _CODE_PLAIN_RE.search(query or "")
        raw = plain.group(1) if plain else None
    if raw is None:
        return None
    try:
        return normalize_symbol(raw)
    except ValueError:
        return None


class Orchestrator:
    def __init__(self, memory=None, adapter=None, metrics=None):
        self.memory = memory if memory is not None else MemoryService(get_db())
        self.adapter = adapter if adapter is not None else HarnessAdapter()
        self.metrics = metrics if metrics is not None else get_metrics()

    def analyze(self, query: str, session_id: str | None = None) -> AnalysisResult:
        started = time.perf_counter()
        with run_trace() as tid:
            symbol = resolve_symbol_local(query, self.memory)
            ctx = self.memory.build_context_block(symbol or "", query)
            sid = session_id or uuid.uuid4().hex
            prompt = (ctx + "\n\n" if ctx else "") + f"用户问题: {query}"
            outcome = self.adapter.run(prompt, session_id=sid)

            response = outcome.final_response
            ok = response is not None and outcome.finish_reason not in ("error", None)
            response_md = response if ok else _FALLBACK_TEXT
            pred = parse_prediction(response_md) if ok else None

            prediction_id: int | None = None
            if pred is not None and symbol:
                prediction_id = self.memory.save_prediction(pred, symbol, tid)
                conclusion = _MD_SYMBOLS_RE.sub("", response_md[:200]).strip()
                self.memory.upsert_instrument(symbol, conclusion=conclusion)
            if symbol:
                self.memory.bind_session(sid, symbol)

            reports_dir = get_settings().finana_home.expanduser() / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            meta = (
                f"trace: {tid}\nsession: {sid} | "
                f"prediction: {prediction_id if prediction_id is not None else '-'}"
            )
            report_path = reports_dir / f"{int(time.time())}-{symbol or 'general'}.md"
            report_path.write_text(meta + "\n\n" + response_md, encoding="utf-8")

            elapsed_ms = (time.perf_counter() - started) * 1000
            self.metrics.record("analysis.latency_ms", elapsed_ms, stage="total")
            return AnalysisResult(
                response_md=response_md,
                prediction=pred,
                prediction_id=prediction_id,
                trace_id=tid,
                session_id=sid,
                from_memory_only=False,
            )
