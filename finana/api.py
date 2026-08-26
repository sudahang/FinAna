from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from finana.config import get_settings
from finana.goals import GoalService, Planner
from finana.harness_adapter import FakeHarness, HarnessAdapter
from finana.memory.service import MemoryService
from finana.orchestrator import AnalysisResult, Orchestrator
from finana.storage.db import get_db
from finana.verifier import Verifier


class AnalyzeRequest(BaseModel):
    query: str
    session_id: str | None = None


class GoalRequest(BaseModel):
    query: str


class GoalStatusRequest(BaseModel):
    status: str


class VerifyResponse(BaseModel):
    verified: int
    results: list[dict]


def _result_to_dict(res: AnalysisResult) -> dict:
    pred = res.prediction
    return {
        "response_md": res.response_md,
        "prediction": {
            "direction": pred.direction,
            "confidence": pred.confidence,
            "target_low": pred.target_low,
            "target_high": pred.target_high,
            "horizon_days": pred.horizon_days,
        } if pred else None,
        "prediction_id": res.prediction_id,
        "trace_id": res.trace_id,
        "session_id": res.session_id,
    }


def create_app(memory: MemoryService | None = None, adapter=None,
               datacore=None) -> FastAPI:
    """构建 FastAPI 应用；测试可注入 FakeHarness / FakeDataCore。"""
    settings = get_settings()
    memory = memory if memory is not None else MemoryService(get_db())
    adapter = adapter if adapter is not None else HarnessAdapter()
    orchestrator = Orchestrator(memory=memory, adapter=adapter)
    goal_service = GoalService(memory._conn)
    planner = Planner()

    app = FastAPI(title="FinAna v2")

    def _datacore():
        if datacore is not None:
            return datacore
        from finana.datacore import DataCore

        return DataCore()

    @app.post("/api/analyze")
    def analyze(req: AnalyzeRequest):
        try:
            result = orchestrator.analyze(req.query, session_id=req.session_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        return _result_to_dict(result)

    @app.get("/api/goals")
    def list_goals(status: str | None = None):
        return [vars(g) for g in goal_service.list(status=status)]

    @app.post("/api/goals")
    def create_goal(req: GoalRequest):
        goal = planner.plan_from_query(req.query, memory)
        if goal is None:
            raise HTTPException(status_code=400, detail="无法从查询解析目标")
        created = goal_service.create(goal.title, goal.symbol, cadence_days=goal.cadence_days)
        return vars(created)

    @app.post("/api/goals/{goal_id}/status")
    def set_goal_status(goal_id: str, req: GoalStatusRequest):
        if goal_service.get(goal_id) is None:
            raise HTTPException(status_code=404, detail="goal not found")
        goal_service.update_status(goal_id, req.status)
        return {"goal_id": goal_id, "status": req.status}

    @app.post("/api/verify/run", response_model=VerifyResponse)
    def verify_run(now: float | None = None):
        verdicts = Verifier().run_due(_datacore(), memory, now=now)
        return VerifyResponse(verified=len(verdicts), results=[vars(v) for v in verdicts])

    @app.get("/api/reports")
    def list_reports(symbol: str | None = None):
        reports_dir = settings.finana_home.expanduser() / "reports"
        if not reports_dir.exists():
            return []
        out = []
        for f in sorted(reports_dir.iterdir(), key=lambda p: p.name):
            if not f.is_file():
                continue
            if symbol and symbol not in f.name:
                continue
            out.append({"file": f.name, "mtime": f.stat().st_mtime})
        return out

    @app.get("/api/reports/{name}")
    def get_report(name: str):
        reports_dir = settings.finana_home.expanduser() / "reports"
        path = reports_dir / name
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="report not found")
        return {"file": name, "content": path.read_text(encoding="utf-8")}

    return app


app = create_app()
