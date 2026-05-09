"""Gradio web UI for FinAna - Minimalist Single Input Design."""

import gradio as gr
from workflows.langgraph_workflow import AIResearchWorkflow
from memory.conversation_memory import get_conversation_memory
from dotenv import load_dotenv
import os
import uuid
import logging

from config import get_webui_config

webui_config = get_webui_config()

setup_logging = __import__('logging_config', fromlist=['setup_logging', 'get_logger']).setup_logging
get_logger = __import__('logging_config', fromlist=['setup_logging', 'get_logger']).get_logger

setup_logging(level=logging.INFO)
logger = get_logger(__name__)
logger.info("FinAna Web UI starting...")

load_dotenv()

conversation_memory = get_conversation_memory()

CUSTOM_CSS = """
.gradio-container {
    background: #fff !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif !important;
}

#logo {
    font-size: 1.5rem;
    font-weight: 400;
    color: #202124;
    margin-bottom: 32px;
    letter-spacing: -0.5px;
    text-align: center;
}

#logo span {
    color: #4285f4;
}

#input-box {
    max-width: 680px;
    margin: 0 auto 24px;
}

#input-box textarea {
    border: 1px solid #dfe1e5 !important;
    border-radius: 8px !important;
    padding: 14px 16px !important;
    font-size: 15px !important;
    color: #202124 !important;
    background: #fff !important;
    box-shadow: none !important;
    line-height: 1.5 !important;
}

#input-box textarea:focus {
    border-color: #4285f4 !important;
    box-shadow: 0 0 0 2px rgba(66,133,244,0.15) !important;
}

#result {
    max-width: 680px;
    margin: 0 auto;
    border-top: 1px solid #e8eaed;
    padding-top: 24px;
}

#result h1, #result h2, #result h3 {
    color: #202124;
    font-size: 16px;
    font-weight: 500;
    margin: 0 0 12px 0;
}

#result p, #result li {
    color: #4d5156;
    font-size: 14px;
    line-height: 1.6;
}

#empty {
    color: #9aa0a6;
    font-size: 14px;
    text-align: center;
    padding: 40px 0;
}
"""


def run_analysis(query: str):
    if not query or not query.strip():
        yield '<div id="empty">Enter a stock or question to get started</div>'
        return

    try:
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            yield '<div id="empty">Please configure DASHSCOPE_API_KEY</div>'
            return

        workflow = AIResearchWorkflow()
        initial_state = {
            "query": query,
            "country": "",
            "sector": "",
            "symbol": "",
            "macro_context": None,
            "industry_context": None,
            "company_analysis": None,
            "report": None,
            "error": None,
            "messages": []
        }

        graph = workflow.graph
        for step in graph.stream(initial_state, stream_mode="values"):
            messages = step.get("messages", [])
            if messages and len(messages) > 0:
                latest_msg = messages[-1]
                if hasattr(latest_msg, 'content'):
                    yield latest_msg.content
                else:
                    yield str(latest_msg)

        final_state = graph.invoke(initial_state)
        if final_state.get("error"):
            yield f"Error: {final_state['error']}"
            return

        report = final_state.get("report")
        if report:
            yield report.full_report
        else:
            yield "No report generated."

    except Exception as e:
        yield f"Error: {str(e)}"


def create_demo() -> gr.Blocks:
    with gr.Blocks(title="FinAna") as demo:

        gr.HTML('<div id="logo">Fin<span>Ana</span></div>')

        query_input = gr.Textbox(
            elem_id="input-box",
            placeholder="Ask about any stock or market...",
            label="",
            lines=1,
            max_lines=4
        )

        report_output = gr.Markdown(
            elem_id="result",
            label="",
            value='<div id="empty">Enter a stock or question to get started</div>'
        )

        query_input.submit(
            fn=run_analysis,
            inputs=query_input,
            outputs=report_output,
            show_progress="full"
        )

    return demo


def launch():
    demo = create_demo()
    demo.queue(max_size=webui_config.queue_max_size)
    demo.launch(
        server_name=webui_config.server_name,
        server_port=webui_config.server_port,
        show_error=True,
        css=CUSTOM_CSS
    )


if __name__ == "__main__":
    launch()
