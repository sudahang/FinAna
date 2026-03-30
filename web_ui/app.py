"""Gradio web UI for FinAna - Modern Design with Multi-turn Chat Support."""

import gradio as gr
from workflows.langgraph_workflow import AIResearchWorkflow
from memory.conversation_memory import get_conversation_memory
from dotenv import load_dotenv
import os
import uuid

# Load environment variables
load_dotenv()

# Get conversation memory singleton
conversation_memory = get_conversation_memory()

# Custom CSS for modern design
CUSTOM_CSS = """
/* Global styles */
:root {
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --success-gradient: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    --card-bg: #ffffff;
    --bg-gradient: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.gradio-container {
    background: var(--bg-gradient);
    min-height: 100vh;
}

/* Header styling */
.header-section {
    background: var(--primary-gradient);
    padding: 40px 20px;
    border-radius: 20px;
    margin-bottom: 30px;
    box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
    text-align: center;
}

.header-section h1 {
    color: white;
    font-size: 2.5em;
    margin: 0;
    font-weight: 700;
    text-shadow: 0 2px 10px rgba(0,0,0,0.2);
}

.header-section p {
    color: rgba(255,255,255,0.9);
    margin-top: 10px;
    font-size: 1.1em;
}

/* Card styling */
.card {
    background: var(--card-bg);
    border-radius: 16px;
    padding: 30px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}

/* Input styling */
#query_input textarea {
    background: #f8f9fa;
    border: 2px solid #e9ecef;
    border-radius: 12px;
    padding: 15px;
    font-size: 16px;
    transition: all 0.3s ease;
}

#query_input textarea:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
}

/* Button styling */
#analyze_btn {
    background: var(--primary-gradient);
    border: none;
    border-radius: 12px;
    padding: 15px 40px;
    font-size: 16px;
    font-weight: 600;
    color: white;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

#analyze_btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 25px rgba(102, 126, 234, 0.5);
}

/* Output styling */
#report_output {
    background: white;
    border-radius: 16px;
    padding: 30px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

/* Example buttons */
.example-btn {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border: 2px solid #dee2e6;
    border-radius: 10px;
    padding: 12px 20px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s ease;
    margin: 5px;
}

.example-btn:hover {
    background: var(--primary-gradient);
    border-color: #667eea;
    color: white;
    transform: translateY(-2px);
}

/* Steps section */
.steps-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-top: 20px;
}

.step-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 25px;
    border-radius: 12px;
    text-align: center;
    transition: transform 0.3s ease;
}

.step-card:hover {
    transform: translateY(-5px);
}

.step-number {
    background: rgba(255,255,255,0.2);
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 15px;
    font-size: 18px;
    font-weight: bold;
    color: white;
}

.step-title {
    color: white;
    font-weight: 600;
    margin-bottom: 8px;
}

.step-desc {
    color: rgba(255,255,255,0.8);
    font-size: 13px;
}

/* Stock tickers section */
.stock-tickers {
    display: flex;
    justify-content: center;
    gap: 15px;
    flex-wrap: wrap;
    margin: 20px 0;
}

.ticker-badge {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    padding: 8px 16px;
    border-radius: 20px;
    color: white;
    font-weight: 600;
    font-size: 14px;
}

/* Loading animation */
.loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
}

.loading-dot {
    width: 10px;
    height: 10px;
    background: #667eea;
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dot:nth-child(1) { animation-delay: -0.32s; }
.loading-dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1); }
}
"""


def run_analysis(query: str) -> str:
    """
    Run investment research analysis and return report.

    Args:
        query: User's investment research query.

    Returns:
        Markdown-formatted research report.
    """
    if not query or not query.strip():
        return """
<div style="background: #fff3cd; padding: 20px; border-radius: 12px; border-left: 4px solid #ffc107;">
    <strong>⚠️ 请输入查询内容</strong>
    <p style="margin: 10px 0 0 0; color: #856404;">请在上方输入框中输入股票名称或公司，例如："分析特斯拉股票"</p>
</div>
"""

    try:
        # Check if API key is configured
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            return """
<div style="background: #fff3cd; padding: 20px; border-radius: 12px; border-left: 4px solid #ffc107;">
    <strong>⚠️ 配置提示</strong>
    <p style="margin: 10px 0 0 0; color: #856404;">
        请先配置 DASHSCOPE_API_KEY 环境变量以使用 AI 分析功能。
        <br><br>
        1. 访问 <a href="https://dashscope.console.aliyun.com/" target="_blank">DashScope 控制台</a> 获取 API Key
        <br>
        2. 将 .env.example 复制为 .env 并填入 API Key
        <br>
        3. 重启服务
    </p>
</div>
"""

        workflow = AIResearchWorkflow()
        report = workflow.execute(query)
        return report.full_report

    except Exception as e:
        # Return a more user-friendly error message
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            return """
<div style="background: #f8d7da; padding: 20px; border-radius: 12px; border-left: 4px solid #dc3545;">
    <strong>❌ 请求超时</strong>
    <p style="margin: 10px 0 0 0; color: #721c24;">
        AI 分析请求超时，请稍后重试。
    </p>
    <p style="margin: 10px 0 0 0; font-size: 13px; color: #721c24;">
        建议：<br>
        1. 检查网络连接<br>
        2. 确认 API Key 有效且有足够额度<br>
        3. 稍后重试
    </p>
</div>
"""
        return f"""
<div style="background: #f8d7da; padding: 20px; border-radius: 12px; border-left: 4px solid #dc3545;">
    <strong>❌ 生成报告时出错</strong>
    <p style="margin: 10px 0 0 0; color: #721c24;">{error_msg}</p>
</div>
"""


def run_analysis_streaming(query: str):
    """
    Run investment research analysis with streaming output.

    Args:
        query: User's investment research query.

    Yields:
        Intermediate status updates and final report.
    """
    if not query or not query.strip():
        yield """
<div style="background: #fff3cd; padding: 20px; border-radius: 12px; border-left: 4px solid #ffc107;">
    <strong>⚠️ 请输入查询内容</strong>
</div>
"""
        return

    try:
        # Check if API key is configured
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            yield """
<div style="background: #fff3cd; padding: 20px; border-radius: 12px; border-left: 4px solid #ffc107;">
    <strong>⚠️ 配置提示</strong>
    <p style="margin: 10px 0 0 0; color: #856404;">请先配置 DASHSCOPE_API_KEY 环境变量</p>
</div>
"""
            return

        # Initialize workflow
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

        # Stream execution steps using LangGraph stream
        graph = workflow.graph

        # Stream the workflow execution
        for step in graph.stream(initial_state, stream_mode="values"):
            messages = step.get("messages", [])
            if messages and len(messages) > 0:
                # Get the latest message
                latest_msg = messages[-1]
                # Format as markdown
                if hasattr(latest_msg, 'content'):
                    yield f"# 📊 实时分析进度\n\n{latest_msg.content}"
                else:
                    yield f"# 📊 实时分析进度\n\n{str(latest_msg)}"

        # Get final state
        final_state = graph.invoke(initial_state)

        if final_state.get("error"):
            yield f"""
<div style="background: #f8d7da; padding: 20px; border-radius: 12px; border-left: 4px solid #dc3545;">
    <strong>❌ 分析失败</strong>
    <p style="margin: 10px 0 0 0; color: #721c24;">{final_state['error']}</p>
</div>
"""
            return

        report = final_state.get("report")
        if report:
            yield f"# ✅ 分析完成\n\n{report.full_report}"
        else:
            yield "❌ 未生成报告"

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        yield f"""
<div style="background: #f8d7da; padding: 20px; border-radius: 12px; border-left: 4px solid #dc3545;">
    <strong>❌ 生成报告时出错</strong>
    <p style="margin: 10px 0 0 0; color: #721c24;">{str(e)}</p>
    <details>
        <summary>查看详细错误</summary>
        <pre>{error_trace}</pre>
    </details>
</div>
"""


def chat_with_memory(
    message: str,
    history: list[list[str]]
) -> str:
    """
    Chat function with conversation memory support.

    Args:
        message: User's message.
        history: Conversation history as [[user_msg, assistant_msg], ...].

    Returns:
        Assistant response.
    """
    if not message or not message.strip():
        return "请输入消息内容。"

    try:
        # Check if API key is configured
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            return """⚠️ **配置提示**

请先配置 DASHSCOPE_API_KEY 环境变量以使用 AI 分析功能。

1. 访问 [DashScope 控制台](https://dashscope.console.aliyun.com/) 获取 API Key
2. 将 .env.example 复制为 .env 并填入 API Key
3. 重启服务"""

        # Generate or get session ID from history length (simple session tracking)
        # In a real implementation, you'd use a proper session management
        session_id = f"webui_session_{len(history)}"

        # Get conversation history from Gradio format
        conv_history = []
        for user_msg, assistant_msg in history:
            conv_history.append({"role": "user", "content": user_msg})
            conv_history.append({"role": "assistant", "content": assistant_msg})

        # Execute workflow with conversation memory
        workflow = AIResearchWorkflow()
        report = workflow.execute(
            query=message,
            session_id=session_id,
            conversation_history=conv_history
        )

        return report.full_report

    except Exception as e:
        return f"""❌ **生成回复时出错**

{str(e)}

请检查配置后重试。"""


def clear_conversation() -> tuple[str, list]:
    """
    Clear conversation history.

    Returns:
        Success message and empty history.
    """
    # Clear all sessions (in production, you'd want to target specific session)
    global conversation_memory
    conversation_memory = get_conversation_memory()

    return "✅ 对话历史已清除，开始新的对话吧！", []


def create_demo() -> gr.Blocks:
    """Create the Gradio demo application with modern design and multi-turn chat."""

    with gr.Blocks(
        title="FinAna | 智能投研助手",
        css=CUSTOM_CSS,
        fill_height=True
    ) as demo:

        # Header
        gr.HTML("""
        <div class="header-section">
            <h1>📊 FinAna 智能投研助手</h1>
            <p>基于多智能体协作的自动化投资研究分析系统 - 支持多轮对话</p>
        </div>
        """)

        # Create tabs for different modes
        with gr.Tabs(elem_classes="modern-tabs") as tabs:

            # Tab 1: Chat Mode (Multi-turn)
            with gr.TabItem("💬 多轮对话", id=0) as chat_tab:
                with gr.Row(equal_height=True):
                    # Left column - Chat input and controls
                    with gr.Column(scale=1, min_width=400):
                        gr.HTML('<div class="card">')
                        gr.Markdown("### 🗨️ 开始对话")
                        gr.Markdown("""
                        **多轮对话功能**让您能够:
                        - 基于之前的分析结果进行深入提问
                        - 对比多只股票的投资价值
                        - 获取更详细的数据解释

                        **示例**:
                        1. 先问："分析特斯拉股票"
                        2. 再问："它的估值合理吗？"
                        3. 再问："和比亚迪比哪个更值得投资？"
                        """)

                        with gr.Row():
                            clear_btn = gr.Button(
                                "🗑️ 清除对话",
                                variant="secondary",
                                size="lg"
                            )

                        gr.HTML('</div>')

                        # Example Queries Card
                        gr.HTML('<div class="card">')
                        gr.Markdown("### 📝 示例问题")

                        examples = [
                            "📈 分析特斯拉股票的未来走势",
                            "💡 特斯拉的估值合理吗？",
                            "🔍 对比特斯拉和比亚迪",
                            "📊 特斯拉的财务健康状况如何？",
                            "🎯 现在适合买入特斯拉吗？"
                        ]

                        for example in examples:
                            gr.Button(example, elem_classes="example-btn")

                        gr.HTML('</div>')

                    # Right column - Chat output
                    with gr.Column(scale=2, min_width=600):
                        gr.HTML('<div class="card">')
                        gr.Markdown("### 💬 对话记录")

                        # Chat interface
                        chat_interface = gr.ChatInterface(
                            fn=chat_with_memory,
                            title="",
                            description="输入您的问题，获取智能投资分析",
                            examples=[
                                ["分析特斯拉股票"],
                                ["特斯拉的竞争优势是什么？"],
                                ["对比苹果和微软"],
                                ["现在适合买入 NVIDIA 吗？"]
                            ],
                            textbox=gr.Textbox(
                                placeholder="输入您的问题，例如：分析特斯拉股票...",
                                container=False,
                                scale=7
                            ),
                            retry_btn=None,
                            undo_btn="↩️ 撤回",
                            clear_btn="🗑️ 清除",
                            theme="soft"
                        )

                        gr.HTML('</div>')

            # Tab 2: Single Analysis Mode (Original)
            with gr.TabItem("📊 单次分析", id=1) as analysis_tab:
                with gr.Row(equal_height=True):
                    # Left column - Input and Examples
                    with gr.Column(scale=1, min_width=400):
                        # Query Input Card
                        gr.HTML('<div class="card">')
                        gr.Markdown("### 💬 输入您的查询")
                        query_input = gr.Textbox(
                            elem_id="query_input",
                            label="",
                            placeholder="例如：分析特斯拉股票的未来走势...",
                            lines=4,
                            container=False
                        )
                        analyze_btn = gr.Button(
                            "🚀 开始分析",
                            elem_id="analyze_btn",
                            variant="primary",
                            size="lg"
                        )
                        gr.HTML('</div>')

                        # Example Queries Card
                        gr.HTML('<div class="card">')
                        gr.Markdown("### 📝 示例查询")

                        def use_example(example: str) -> str:
                            return example

                        examples = [
                            "📈 分析特斯拉股票的未来走势",
                            "💡 应该投资 NVIDIA 吗？",
                            "🍎 苹果公司长期投资分析",
                            "🔍 微软股票值得买入吗",
                            "📊 谷歌投资价值分析"
                        ]

                        for example in examples:
                            btn = gr.Button(example, elem_classes="example-btn")
                            btn.click(fn=use_example, inputs=btn, outputs=query_input)

                        gr.HTML('</div>')

                        # Supported Stocks Card
                        gr.HTML('<div class="card">')
                        gr.Markdown("### 💹 支持的投资标的")
                        gr.HTML("""
                        <div class="stock-tickers">
                            <span class="ticker-badge">🚗 TSLA 特斯拉</span>
                            <span class="ticker-badge">🎮 NVDA 英伟达</span>
                            <span class="ticker-badge">🍎 AAPL 苹果</span>
                            <span class="ticker-badge">💻 MSFT 微软</span>
                            <span class="ticker-badge">🔍 GOOGL 谷歌</span>
                        </div>
                        """)
                        gr.HTML('</div>')

                    # Right column - How it works and Output
                    with gr.Column(scale=1, min_width=400):
                        # How it works Card
                        gr.HTML('<div class="card">')
                        gr.Markdown("### ⚙️ 工作原理")
                        gr.HTML("""
                        <div class="steps-container">
                            <div class="step-card">
                                <div class="step-number">1</div>
                                <div class="step-title">宏观经济分析</div>
                                <div class="step-desc">GDP、通胀、利率等指标</div>
                            </div>
                            <div class="step-card">
                                <div class="step-number">2</div>
                                <div class="step-title">行业分析</div>
                                <div class="step-desc">行业趋势、竞争格局</div>
                            </div>
                            <div class="step-card">
                                <div class="step-number">3</div>
                                <div class="step-title">公司分析</div>
                                <div class="step-desc">财务健康、技术指标</div>
                            </div>
                            <div class="step-card">
                                <div class="step-number">4</div>
                                <div class="step-title">报告合成</div>
                                <div class="step-desc">生成完整投资建议</div>
                            </div>
                        </div>
                        """)
                        gr.HTML('</div>')

                        # Output Card
                        gr.HTML('<div class="card" id="report_output">')
                        gr.Markdown("### 📄 分析报告")
                        report_output = gr.Markdown(
                            label="",
                            elem_id="report_output",
                            value="""
<div style="text-align: center; padding: 40px; color: #6c757d;">
    <div style="font-size: 48px; margin-bottom: 20px;">📊</div>
    <h3 style="margin-bottom: 10px;">准备生成报告</h3>
    <p>在左侧输入股票或公司名称，点击"开始分析"获取详细的投资研究报告</p>
</div>
"""
                        )
                        gr.HTML('</div>')

        # Footer
        gr.HTML("""
        <div style="text-align: center; margin-top: 30px; padding: 20px; color: #6c757d;">
            <p style="margin: 0; font-size: 14px;">
                ⚠️ <strong>免责声明</strong>：本报告仅供演示和教育用途，不构成投资建议。
            </p>
            <p style="margin: 5px 0 0 0; font-size: 13px;">
                投资有风险，决策需谨慎。请咨询持牌金融顾问获取专业建议。
            </p>
        </div>
        """)

        # Set up event handlers for single analysis mode
        analyze_btn.click(
            fn=run_analysis_streaming,
            inputs=query_input,
            outputs=report_output,
            show_progress="full"
        )

        # Handle enter key with streaming
        query_input.submit(
            fn=run_analysis_streaming,
            inputs=query_input,
            outputs=report_output,
            show_progress="full"
        )

    return demo


def launch():
    """Launch the Gradio application."""
    demo = create_demo()
    demo.queue(max_size=10)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )


if __name__ == "__main__":
    launch()
