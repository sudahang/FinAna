"""Test AI Agent functionality."""

import sys
sys.path.insert(0, '.')

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

from llm.client import LLMClient, get_llm_client
from data.finance_data import FinancialDataFetcher, get_data_fetcher
from agents.macro_analyst_ai import MacroAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent
from agents.equity_analyst_ai import EquityAnalystAgent
from agents.report_synthesizer_ai import ReportSynthesizerAgent
from workflows.ai_research_workflow import AIResearchWorkflow


def test_llm_client():
    """Test LLM client connection."""
    print("\n=== 测试 LLM 客户端 ===")
    try:
        client = get_llm_client()
        response = client.chat(
            messages=[{"role": "user", "content": "你好，请用一句话介绍你自己"}]
        )
        print(f"✅ LLM 连接成功：{response[:50]}...")
        return True
    except Exception as e:
        print(f"❌ LLM 连接失败：{e}")
        return False


def test_data_fetcher():
    """Test financial data fetcher."""
    print("\n=== 测试财经数据获取 ===")
    fetcher = get_data_fetcher()

    # Test US stock quote
    print("\n测试美股行情 (TSLA)...")
    quote = fetcher.get_us_stock_quote("TSLA")
    if quote:
        print(f"✅ TSLA 价格：${quote.get('current_price', 'N/A')}")
    else:
        print("⚠️  TSLA 行情获取失败（可能 API 限流）")

    # Test macro data
    print("\n测试宏观数据...")
    macro = fetcher.get_macro_data("china")
    if macro:
        print(f"✅ 中国 GDP 增长：{macro.get('gdp_growth', 'N/A')}%")
    else:
        print("❌ 宏观数据获取失败")

    # Test industry data
    print("\n测试行业数据...")
    industry = fetcher.get_industry_data("科技")
    if industry:
        print(f"✅ 科技行业增长：{industry.get('sector_growth', 'N/A')}%")
    else:
        print("❌ 行业数据获取失败")

    return True


def test_macro_agent():
    """Test Macro Analyst AI Agent."""
    print("\n=== 测试宏观经济分析师 AI ===")
    try:
        agent = MacroAnalystAgent()
        result = agent.analyze("china")
        print(f"✅ 市场情绪：{result.market_sentiment}")
        print(f"📝 分析摘要：{result.summary[:100]}...")
        return True
    except Exception as e:
        print(f"❌ 宏观分析失败：{e}")
        return False


def test_industry_agent():
    """Test Industry Analyst AI Agent."""
    print("\n=== 测试行业分析师 AI ===")
    try:
        agent = IndustryAnalystAgent()
        result = agent.analyze("科技")
        print(f"✅ 行业前景：{result.outlook}")
        print(f"📝 分析摘要：{result.summary[:100]}...")
        return True
    except Exception as e:
        print(f"❌ 行业分析失败：{e}")
        return False


def test_equity_agent():
    """Test Equity Analyst AI Agent."""
    print("\n=== 测试个股分析师 AI ===")
    try:
        agent = EquityAnalystAgent()
        result = agent.analyze("TSLA")
        print(f"✅ 技术信号：{result.technical_indicator}")
        print(f"📝 分析摘要：{result.summary[:100]}...")
        return True
    except Exception as e:
        print(f"❌ 个股分析失败：{e}")
        return False


def test_full_workflow():
    """Test full AI research workflow."""
    print("\n=== 测试完整 AI 投研工作流 ===")
    try:
        workflow = AIResearchWorkflow()
        print("开始分析：特斯拉股票未来走势...")
        report = workflow.execute("分析特斯拉股票的未来走势")

        print(f"\n✅ 报告生成成功!")
        print(f"📊 投资建议：{report.recommendation}")
        print(f"💰 目标价格：${report.target_price}")
        print(f"📄 报告长度：{len(report.full_report)} 字符")
        print(f"\n--- 报告预览 ---")
        print(report.full_report[:1000] + "...")
        return True
    except Exception as e:
        print(f"❌ 工作流执行失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("FinAna AI Agent 功能测试")
    print("=" * 60)

    results = {
        "LLM 客户端": test_llm_client(),
        "财经数据获取": test_data_fetcher(),
        "宏观分析师 AI": test_macro_agent(),
        "行业分析师 AI": test_industry_agent(),
        "个股分析师 AI": test_equity_agent(),
        "完整工作流": test_full_workflow()
    }

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for test, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test}: {status}")

    total = sum(results.values())
    print(f"\n总计：{total}/{len(results)} 测试通过")

    return total == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
