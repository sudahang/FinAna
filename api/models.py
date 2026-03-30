"""API request/response models."""

from pydantic import BaseModel, Field
from typing import Optional


class AnalysisRequest(BaseModel):
    """Request model for analysis endpoint."""

    query: str = Field(description="User's investment research query")
    session_id: Optional[str] = Field(default=None, description="Session ID for multi-turn conversation")
    use_cache: Optional[bool] = Field(default=True, description="Use cached reports if available")


class ChatMessage(BaseModel):
    """A single message in conversation history."""
    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content")


class ChatRequest(BaseModel):
    """Request model for chat endpoint with conversation history."""

    query: str = Field(description="User's investment research query")
    session_id: Optional[str] = Field(default=None, description="Session ID for multi-turn conversation")
    history: Optional[list[ChatMessage]] = Field(default=None, description="Conversation history")
    use_cache: Optional[bool] = Field(default=True, description="Use cached reports if available")


class AnalysisResponse(BaseModel):
    """Response model for analysis endpoint."""

    task_id: str = Field(description="Unique task identifier")
    status: str = Field(description="Task status: pending/running/completed/failed")
    report: Optional[str] = Field(default=None, description="Markdown report if completed")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    session_id: Optional[str] = Field(default=None, description="Session ID for multi-turn conversation")
    from_cache: Optional[bool] = Field(default=False, description="Whether report was from cache")


class AnalysisResult(BaseModel):
    """Complete analysis result model."""

    query: str = Field(description="Original user query")
    recommendation: str = Field(description="Investment recommendation")
    target_price: Optional[float] = Field(default=None, description="Target price")
    full_report: str = Field(description="Complete markdown report")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    query: str = Field(description="Original user query")
    response: str = Field(description="Assistant response with analysis")
    session_id: str = Field(description="Session ID for the conversation")
    recommendation: Optional[str] = Field(default=None, description="Investment recommendation")
    target_price: Optional[float] = Field(default=None, description="Target price")
    has_history: bool = Field(default=False, description="Whether conversation has history")
    from_cache: Optional[bool] = Field(default=False, description="Whether report was from cache")


class CachedReportResponse(BaseModel):
    """Response model for cached report."""
    report_id: str = Field(description="Report identifier")
    query: str = Field(description="Original query")
    summary: str = Field(description="Report summary")
    similarity: float = Field(description="Similarity score")
    created_at: str = Field(description="Creation timestamp")
    full_report: Optional[str] = Field(default=None, description="Full report content if requested")


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""
    redis: dict = Field(description="Redis statistics")
    seaweed: dict = Field(description="SeaweedFS statistics")
    cache_enabled: bool = Field(description="Whether cache is enabled")
    cache_ttl: int = Field(description="Cache TTL in seconds")
