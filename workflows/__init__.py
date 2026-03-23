"""Workflows module for FinAna."""

from workflows.ai_research_workflow import AIResearchWorkflow, execute_ai_research_workflow
from workflows.langgraph_workflow import AIResearchWorkflow as LangGraphAIResearchWorkflow

__all__ = [
    "AIResearchWorkflow",
    "execute_ai_research_workflow",
    "LangGraphAIResearchWorkflow"
]
