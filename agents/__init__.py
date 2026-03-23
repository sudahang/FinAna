"""Agents module for FinAna multi-agent system."""

# AI-powered agents using Qwen LLM with real-time data
from agents.macro_analyst_ai import MacroAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent
from agents.equity_analyst_ai import EquityAnalystAgent
from agents.report_synthesizer_ai import ReportSynthesizerAgent
from agents.input_router_ai import InputRouterAgent, get_router_agent

__all__ = [
    "MacroAnalystAgent",
    "IndustryAnalystAgent",
    "EquityAnalystAgent",
    "ReportSynthesizerAgent",
    "InputRouterAgent",
    "get_router_agent"
]
