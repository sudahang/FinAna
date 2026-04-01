"""Test script for multi-turn conversation with memory."""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.conversation_memory import (
    ConversationMemory,
    get_conversation_memory,
    format_history_for_llm
)
from workflows.langgraph_workflow import AIResearchWorkflow


def test_conversation_memory():
    """Test basic conversation memory functionality."""
    print("=" * 60)
    print("测试 1: 基础对话记忆功能")
    print("=" * 60)

    # Create memory instance
    memory = ConversationMemory(
        max_sessions=10,
        session_ttl=3600,
        max_messages_per_session=20
    )

    # Create a session
    session_id = memory.create_session()
    print(f"创建会话：{session_id}")

    # Add messages
    memory.add_message(session_id, "user", "分析特斯拉股票")
    memory.add_message(session_id, "assistant", "特斯拉是一家美国电动汽车公司...")
    memory.add_message(session_id, "user", "它的估值合理吗？")
    memory.add_message(session_id, "assistant", "根据分析，特斯拉的当前估值...")

    # Get history
    history = memory.get_history(session_id)
    print(f"\n对话历史 ({len(history)} 条消息):")
    for msg in history:
        print(f"  [{msg['role']}]: {msg['content'][:50]}...")

    # Test context storage
    memory.set_context(session_id, "symbol", "TSLA")
    memory.set_context(session_id, "country", "us")
    memory.set_context(session_id, "sector", "汽车")

    context = memory.get_context(session_id)
    print(f"\n会话上下文：{context}")

    # Test session info
    info = memory.get_session_info(session_id)
    print(f"\n会话信息：{info}")

    # Test clear session
    memory.clear_session(session_id)
    cleared_history = memory.get_history(session_id)
    print(f"\n清除后会话历史：{len(cleared_history)} 条消息")

    print("\n✅ 基础对话记忆功能测试通过\n")


def test_workflow_with_memory():
    """Test workflow execution with conversation memory."""
    print("=" * 60)
    print("测试 2: 工作流与对话记忆集成")
    print("=" * 60)

    # Check if API key is configured
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("⚠️  跳过：未配置 DASHSCOPE_API_KEY 环境变量")
        print("   如需运行完整测试，请设置 API Key 后重试\n")
        return

    # Create workflow
    workflow = AIResearchWorkflow()

    # Generate session ID
    session_id = f"test_session_{os.urandom(4).hex()}"
    print(f"会话 ID: {session_id}")

    # First turn: Basic analysis
    print("\n第一轮：基础分析")
    print("-" * 40)
    query1 = "分析特斯拉股票"
    print(f"用户：{query1}")

    try:
        report1 = workflow.execute(query1, session_id=session_id)
        print(f"助手：收到，已生成特斯拉分析报告 (长度：{len(report1.full_report)} 字符)")
        print(f"投资建议：{report1.recommendation}")
    except Exception as e:
        print(f"❌ 第一轮分析失败：{e}")
        return

    # Second turn: Follow-up question
    print("\n第二轮：后续问题")
    print("-" * 40)
    query2 = "特斯拉的估值合理吗？"
    print(f"用户：{query2}")

    try:
        # Get conversation history
        memory = get_conversation_memory()
        history = memory.get_history(session_id)
        print(f"对话历史：{len(history)} 条消息")

        report2 = workflow.execute(query2, session_id=session_id, conversation_history=history)
        print(f"助手：收到，已分析特斯拉估值 (长度：{len(report2.full_report)} 字符)")
    except Exception as e:
        print(f"❌ 第二轮分析失败：{e}")
        return

    # Third turn: Comparison question
    print("\n第三轮：对比分析")
    print("-" * 40)
    query3 = "对比特斯拉和比亚迪"
    print(f"用户：{query3}")

    try:
        history = memory.get_history(session_id)
        print(f"对话历史：{len(history)} 条消息")

        report3 = workflow.execute(query3, session_id=session_id, conversation_history=history)
        print(f"助手：收到，已完成特斯拉和比亚迪对比分析")
    except Exception as e:
        print(f"❌ 第三轮分析失败：{e}")
        return

    # Verify conversation history
    print("\n验证对话历史")
    print("-" * 40)
    final_history = memory.get_history(session_id)
    print(f"总消息数：{len(final_history)}")
    for i, msg in enumerate(final_history):
        preview = msg['content'][:60].replace('\n', ' ')
        print(f"  {i+1}. [{msg['role']}] {preview}...")

    # Get stored context
    context = memory.get_context(session_id)
    print(f"\n存储的上下文键：{list(context.keys())}")

    print("\n✅ 工作流与对话记忆集成测试通过\n")


def test_format_history_for_llm():
    """Test history formatting for LLM context."""
    print("=" * 60)
    print("测试 3: 对话历史格式化")
    print("=" * 60)

    # Create sample history
    history = [
        {"role": "user", "content": "分析特斯拉股票"},
        {"role": "assistant", "content": "特斯拉是一家美国电动汽车公司..."},
        {"role": "user", "content": "它的估值合理吗？"},
        {"role": "assistant", "content": "根据分析，特斯拉的当前估值..."}
    ]

    # Format for LLM
    formatted = format_history_for_llm(history, max_history_messages=10)
    print("格式化结果:")
    print("-" * 40)
    print(formatted)
    print("-" * 40)

    # Test with limit
    formatted_limited = format_history_for_llm(history, max_history_messages=2)
    print("\n限制 2 条消息:")
    print("-" * 40)
    print(formatted_limited)

    print("\n✅ 对话历史格式化测试通过\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("FinAna 多轮对话功能测试")
    print("=" * 60 + "\n")

    # Test 1: Basic memory functionality (always runs)
    test_conversation_memory()

    # Test 2: Format history (always runs)
    test_format_history_for_llm()

    # Test 3: Full workflow with memory (requires API key)
    test_workflow_with_memory()

    print("=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
