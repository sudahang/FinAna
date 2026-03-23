"""Analysis API router."""

import uuid
from fastapi import APIRouter, HTTPException
from api.models import AnalysisRequest, AnalysisResponse, AnalysisResult
from workflows.langgraph_workflow import AIResearchWorkflow

router = APIRouter(prefix="/analysis", tags=["analysis"])

# In-memory task storage for demo purposes
# In production, use Redis or a database
task_store: dict[str, dict] = {}


@router.post("/analyze", response_model=AnalysisResponse)
async def start_analysis(request: AnalysisRequest) -> AnalysisResponse:
    """
    Start a new investment research analysis.

    This endpoint accepts a user query and initiates the multi-agent
    research workflow. Returns a task ID for tracking progress.

    Args:
        request: AnalysisRequest containing the user's query.

    Returns:
        AnalysisResponse with task ID and initial status.
    """
    task_id = str(uuid.uuid4())

    # Store task as pending
    task_store[task_id] = {
        "query": request.query,
        "status": "pending",
        "report": None,
        "error": None
    }

    # Execute workflow in background (simplified for demo)
    # In production, use Celery or similar for background tasks
    try:
        workflow = ResearchWorkflow()
        report = workflow.execute(request.query)

        task_store[task_id].update({
            "status": "completed",
            "report": report.full_report,
            "recommendation": report.recommendation,
            "target_price": report.target_price
        })
    except Exception as e:
        task_store[task_id].update({
            "status": "failed",
            "error": str(e)
        })

    return AnalysisResponse(
        task_id=task_id,
        status=task_store[task_id]["status"],
        report=task_store[task_id]["report"]
    )


@router.get("/status/{task_id}", response_model=AnalysisResponse)
async def get_task_status(task_id: str) -> AnalysisResponse:
    """
    Get the status of an analysis task.

    Args:
        task_id: The unique identifier of the analysis task.

    Returns:
        AnalysisResponse with current task status.

    Raises:
        HTTPException: If task not found.
    """
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_store[task_id]
    return AnalysisResponse(
        task_id=task_id,
        status=task["status"],
        report=task.get("report"),
        error=task.get("error")
    )


@router.get("/result/{task_id}", response_model=AnalysisResult)
async def get_analysis_result(task_id: str) -> AnalysisResult:
    """
    Get the complete result of a completed analysis task.

    Args:
        task_id: The unique identifier of the analysis task.

    Returns:
        AnalysisResult with full report details.

    Raises:
        HTTPException: If task not found or not completed.
    """
    if task_id not in task_store:
        raise HTTPException(status_code=404, detail="Task not found")

    task = task_store[task_id]

    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task not completed. Current status: {task['status']}"
        )

    return AnalysisResult(
        query=task["query"],
        recommendation=task.get("recommendation", "hold"),
        target_price=task.get("target_price"),
        full_report=task["report"] or ""
    )
