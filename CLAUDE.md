# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FinAna is a personal investment research assistant demo that uses multi-agent collaboration to provide automated investment analysis. Users input natural language queries (e.g., "Analyze Tesla's outlook for the next month") and receive structured research reports.

## Quick Start

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start API server
uvicorn api.main:app --reload

# Start web UI
python -m web_ui.app
```

## Tech Stack

- **Agent Framework**: LangGraph or CrewAI for multi-agent orchestration
- **Backend**: FastAPI for RESTful API services
- **Frontend**: Gradio for interactive web UI
- **Data Models**: Pydantic for type-safe data structures

## Project Structure

```
FinAna/
├── agents/                  # Multi-agent implementations
│   ├── macro_analyst.py     # Macro economy analyst
│   ├── industry_analyst.py  # Industry sector analyst
│   ├── equity_analyst.py    # Individual stock analyst
│   └── report_synthesizer.py # Report compilation agent
├── workflows/               # Agent orchestration
│   └── research_workflow.py # Investment research workflow
├── data/                    # Data layer
│   ├── mock_data.py         # Simulated market data
│   └── schemas.py           # Pydantic data models
├── api/                     # Backend services
│   ├── main.py              # FastAPI application
│   └── routers/analysis.py  # Analysis endpoints
├── web_ui/                  # Frontend
│   └── app.py               # Gradio application
├── tests/                   # Unit tests
└── requirements.txt         # Python dependencies
```

## Core Workflow

1. User submits query via Gradio UI
2. FastAPI receives request and triggers research workflow
3. Agents execute in sequence: Macro → Industry → Equity Analysis → Report Synthesis
4. Structured Markdown report returned to user

## Key Design Principles

- **Modular agents**: Each agent is independent with specific role, goal, and tools
- **Simulated data**: Demo uses mock stock/news/economic data for stability
- **Type safety**: Pydantic models (`MacroContext`, `IndustryContext`, `CompanyAnalysis`) define inter-agent communication
- **PEP 8 compliance**: Follow Python style guidelines with docstrings and type hints

## Supported Stocks

The demo includes simulated data for: TSLA, NVDA, AAPL, MSFT, GOOGL. Other symbols return default data.
