"""Agents module for FinAna multi-agent system."""

from agents.macro_analyst import MacroAnalystAgent
from agents.industry_analyst import IndustryAnalystAgent
from agents.equity_analyst import EquityAnalystAgent
from agents.report_synthesizer import ReportSynthesizerAgent

# AI-powered agents using Qwen LLM
from agents.macro_analyst_ai import MacroAnalystAgent as MacroAnalystAI
from agents.industry_analyst_ai import IndustryAnalystAgent as IndustryAnalystAI
from agents.equity_analyst_ai import EquityAnalystAgent as EquityAnalystAI
from agents.report_synthesizer_ai import ReportSynthesizerAgent as ReportSynthesizerAI

__all__ = [
    "MacroAnalystAgent",
    "IndustryAnalystAgent",
    "EquityAnalystAgent",
    "ReportSynthesizerAgent",
    "MacroAnalystAI",
    "IndustryAnalystAI",
    "EquityAnalystAI",
    "ReportSynthesizerAI"
]
