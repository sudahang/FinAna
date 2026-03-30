"""Analysis API router."""

import uuid
from fastapi import APIRouter, HTTPException
from api.models import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisResult,
    ChatRequest,
    ChatResponse,
    CachedReportResponse,
    CacheStatsResponse,
)
from workflows.langgraph_workflow import AIResearchWorkflow
from memory.conversation_memory import get_conversation_memory
from storage.report_cache import get_report_cache_service
from storage.redis_client import get_redis_client
from storage.seaweed_client import get_seaweed_client

router = APIRouter(prefix="/analysis", tags=["analysis"])

# In-memory task storage for demo purposes
# In production, use Redis or a database
task_store: dict[str, dict] = {}

# Conversation memory singleton
conversation_memory = get_conversation_memory()


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

    # Use session_id from request or generate new one
    session_id = request.session_id or str(uuid.uuid4())

    # Store task as pending
    task_store[task_id] = {
        "query": request.query,
        "session_id": session_id,
        "status": "pending",
        "report": None,
        "error": None
    }

    # Execute workflow in background (simplified for demo)
    # In production, use Celery or similar for background tasks
    try:
        workflow = AIResearchWorkflow()
        report = workflow.execute(request.query, session_id=session_id)

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
        report=task_store[task_id]["report"],
        session_id=session_id
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint for multi-turn conversation with analysis.

    This endpoint supports conversation history and maintains context
    across multiple turns using session_id.

    Args:
        request: ChatRequest with query, optional session_id and history.

    Returns:
        ChatResponse with analysis and session ID.
    """
    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())

    # Get conversation history from memory if available
    history = conversation_memory.get_history(session_id)

    # Execute workflow with session and history
    try:
        # Create workflow with cache enabled/disabled
        workflow = AIResearchWorkflow(enable_cache=request.use_cache)
        report = workflow.execute(
            query=request.query,
            session_id=session_id,
            conversation_history=history
        )

        # Get updated history
        updated_history = conversation_memory.get_history(session_id)

        # Check if report was served from cache
        # (If the same query was cached, it would be returned immediately)
        from_cache = False
        if request.use_cache:
            cache_service = _get_cache_service()
            if cache_service:
                similar = cache_service.redis.find_similar_reports(
                    query=request.query,
                    symbol=None,
                    limit=1,
                )
                if similar and similar[0].get("similarity", 0) == 1.0:
                    from_cache = True

        return ChatResponse(
            query=request.query,
            response=report.full_report,
            session_id=session_id,
            recommendation=report.recommendation,
            target_price=report.target_price,
            has_history=len(updated_history) > 2,
            from_cache=from_cache,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/session/{session_id}")
async def get_session_info(session_id: str) -> dict:
    """
    Get conversation session information.

    Args:
        session_id: The session ID.

    Returns:
        Session information including message count and context keys.
    """
    session = conversation_memory.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return conversation_memory.get_session_info(session_id)


@router.get("/session/{session_id}/history")
async def get_session_history(
    session_id: str,
    max_messages: int = 20
) -> dict:
    """
    Get conversation session history.

    Args:
        session_id: The session ID.
        max_messages: Maximum number of messages to return.

    Returns:
        List of messages in the conversation.
    """
    session = conversation_memory.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "messages": conversation_memory.get_history(session_id, max_messages)
    }


@router.delete("/session/{session_id}")
async def clear_session(session_id: str) -> dict:
    """
    Clear a conversation session's history.

    Args:
        session_id: The session ID.

    Returns:
        Success message.
    """
    session = conversation_memory.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    conversation_memory.clear_session(session_id)
    return {"message": "Session cleared successfully", "session_id": session_id}


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


# ============================================
# Cache-related endpoints
# ============================================

# Initialize cache service
_report_cache_service = None


def _get_cache_service():
    """Get or create cache service singleton."""
    global _report_cache_service
    if _report_cache_service is None:
        _report_cache_service = get_report_cache_service()
    return _report_cache_service


@router.get("/cache/search", response_model=list[CachedReportResponse])
async def search_cached_reports(
    query: str,
    symbol: str = None,
    limit: int = 5
) -> list[CachedReportResponse]:
    """
    Search for similar cached reports.

    Args:
        query: User query to find similar reports for
        symbol: Optional stock symbol to filter
        limit: Maximum number of results

    Returns:
        List of similar cached reports
    """
    cache_service = _get_cache_service()

    if not cache_service or not cache_service.enable_cache:
        raise HTTPException(status_code=503, detail="Cache service not available")

    # Find similar reports
    similar_reports = cache_service.redis.find_similar_reports(
        query=query,
        symbol=symbol,
        limit=limit,
    )

    return [
        CachedReportResponse(
            report_id=report.get("report_id", ""),
            query=report.get("query", ""),
            summary=report.get("summary", ""),
            similarity=report.get("similarity", 0),
            created_at=report.get("created_at", ""),
        )
        for report in similar_reports
    ]


@router.get("/cache/report/{report_id}", response_model=CachedReportResponse)
async def get_cached_report(
    report_id: str,
    include_full: bool = False
) -> CachedReportResponse:
    """
    Get a cached report by ID.

    Args:
        report_id: Report identifier
        include_full: Whether to include full report content

    Returns:
        Cached report information
    """
    cache_service = _get_cache_service()

    if not cache_service or not cache_service.enable_cache:
        raise HTTPException(status_code=503, detail="Cache service not available")

    # Get summary from Redis
    summary_data = cache_service.redis.get_report_summary(report_id)

    if not summary_data:
        raise HTTPException(status_code=404, detail="Report not found in cache")

    # Get full report if requested
    full_report = None
    if include_full:
        full_report = cache_service._download_cached_report(report_id)
        if not full_report:
            raise HTTPException(status_code=404, detail="Report content not found")

    return CachedReportResponse(
        report_id=report_id,
        query=summary_data["metadata"].get("query", ""),
        summary=summary_data["summary"],
        similarity=1.0,
        created_at=summary_data.get("created_at", ""),
        full_report=full_report,
    )


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats() -> CacheStatsResponse:
    """
    Get cache service statistics.

    Returns:
        Cache statistics including Redis and SeaweedFS info
    """
    cache_service = _get_cache_service()

    if not cache_service:
        raise HTTPException(status_code=503, detail="Cache service not available")

    stats = cache_service.get_cache_stats()

    return CacheStatsResponse(
        redis=stats.get("redis", {}),
        seaweed=stats.get("seaweed", {}),
        cache_enabled=stats.get("cache_enabled", False),
        cache_ttl=stats.get("cache_ttl", 0),
    )


@router.post("/cache/clear")
async def clear_cache() -> dict:
    """
    Clear all cached report summaries (Redis only).

    Note: This does not delete reports from SeaweedFS.

    Returns:
        Success message
    """
    cache_service = _get_cache_service()

    if not cache_service:
        raise HTTPException(status_code=503, detail="Cache service not available")

    success = cache_service.clear_cache()

    if success:
        return {"message": "Cache cleared successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.get("/cache/health")
async def check_cache_health() -> dict:
    """
    Check cache service health status.

    Returns:
        Health status for Redis and SeaweedFS
    """
    cache_service = _get_cache_service()

    if not cache_service:
        return {
            "status": "unavailable",
            "redis": {"connected": False},
            "seaweed": {"connected": False},
        }

    redis_ok = cache_service.redis.test_connection()
    seaweed_ok = cache_service.seaweed.test_connection()

    status = "healthy" if (redis_ok and seaweed_ok) else "degraded"

    return {
        "status": status,
        "redis": {"connected": redis_ok},
        "seaweed": {"connected": seaweed_ok},
        "cache_enabled": cache_service.enable_cache,
    }
