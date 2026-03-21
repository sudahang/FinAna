"""API request/response models."""

from pydantic import BaseModel, Field
from typing import Optional


class AnalysisRequest(BaseModel):
    """Request model for analysis endpoint."""

    query: str = Field(description="User's investment research query")


class AnalysisResponse(BaseModel):
    """Response model for analysis endpoint."""

    task_id: str = Field(description="Unique task identifier")
    status: str = Field(description="Task status: pending/running/completed/failed")
    report: Optional[str] = Field(default=None, description="Markdown report if completed")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class AnalysisResult(BaseModel):
    """Complete analysis result model."""

    query: str = Field(description="Original user query")
    recommendation: str = Field(description="Investment recommendation")
    target_price: Optional[float] = Field(default=None, description="Target price")
    full_report: str = Field(description="Complete markdown report")
