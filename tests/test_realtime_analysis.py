#!/usr/bin/env python3
"""实时测试脚本 - 展示大模型在整个分析过程中的执行过程和实时输出。"""

import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from workflows.langgraph_workflow import AIResearchWorkflow
from agents.macro_analyst_ai import MacroAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent
from agents.equity_analyst_ai import EquityAnalystAgent
from agents.report_synthesizer_ai import ReportSynthesizerAgent
from data.finance_data import FinancialDataFetcher

# 彩色输出
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_step(step, text):
    print(f"\n{Colors.CYAN}>>> 步骤 {step}: {text}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")

def print_data(title, data):
    print(f"{Colors.YELLOW}[{title}]{Colors.ENDC}")
    for key, value in data.items():
        print(f"  • {key}: {value}")

def test_data_fetcher():
    """测试数据获取器"""
    print_header("1️⃣  测试实时数据获取")

    fetcher = FinancialDataFetcher()

    # 测试宏观数据
    print_step("1.1", "获取宏观经济数据")
    macro_data = fetcher.get_macro_data("china")
    print_data("中国宏观数据", {
        "GDP 增长": f"{macro_data.get('gdp_growth', 'N/A')}%",
        "通胀率": f"{macro_data.get('inflation_rate', 'N/A')}%",
        "利率": f"{macro_data.get('interest_rate', 'N/A')}%",
        "失业率": f"{macro_data.get('unemployment_rate', 'N/A')}%"
    })

    # 测试行业数据
    print_step("1.2", "获取行业数据")
    industry_data = fetcher.get_industry_data("科技")
    print_data("科技行业数据", {
        "行业增长": f"{industry_data.get('sector_growth', 'N/A')}%",
        "市场情绪": f"{industry_data.get('market_sentiment', 'N/A')}"
    })

    print_success("数据获取测试完成")

def test_macro_analyst():
    """测试宏观分析师 Agent"""
    print_header("2️⃣  测试宏观分析师 Agent")

    agent = MacroAnalystAgent()

    print_step("2.1", "分析美国宏观经济")
    print_info("调用 LLM 进行宏观经济分析...")

    result = agent.analyze("us")

    print_success("宏观分析完成")
    print_data("分析结果", {
        "GDP 增长": f"{result.gdp_growth}%",
        "通胀率": f"{result.inflation_rate}%",
        "利率": f"{result.interest_rate}%",
        "市场情绪": result.market_sentiment
    })
    print(f"\n{Colors.YELLOW}[分析摘要]{Colors.ENDC}")
    print(f"  {result.summary[:200]}...")

def test_industry_analyst():
    """测试行业分析师 Agent"""
    print_header("3️⃣  测试行业分析师 Agent")

    from agents.industry_analyst_ai import IndustryAnalystAgent

    agent = IndustryAnalystAgent()

    print_step("3.1", "分析科技行业")
    print_info("调用 LLM 进行行业分析...")

    result = agent.analyze("科技")

    print_success("行业分析完成")
    print_data("分析结果", {
        "行业": result.sector_name,
        "行业增长": f"{result.sector_growth}%",
        "行业前景": result.outlook
    })
    print(f"\n{Colors.YELLOW}[分析摘要]{Colors.ENDC}")
    print(f"  {result.summary[:200]}...")

def test_equity_analyst():
    """测试个股分析师 Agent"""
    print_header("4️⃣  测试个股分析师 Agent")

    agent = EquityAnalystAgent()

    print_step("4.1", "分析A股中国平安")
    print_info("获取实时股价和新闻...")
    print_info("调用 LLM 进行公司分析...")

    result = agent.analyze("中国平安")

    print_success("公司分析完成")
    print_data("分析结果", {
        "公司名称": result.company.name,
        "股票代码": result.company.symbol,
        "当前股价": f"${result.company.current_price:.2f}",
        "技术信号": result.technical_indicator
    })
    print(f"\n{Colors.YELLOW}[分析摘要]{Colors.ENDC}")
    print(f"  {result.summary[:200]}...")

def test_full_workflow_streaming():
    """测试完整工作流 - 流式输出"""
    print_header("5️⃣  测试完整工作流（流式输出）")

    query = "分析中国平安股票的投资价值"
    print(f"{Colors.BOLD}用户查询：{Colors.ENDC}{query}\n")

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

    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.CYAN}开始执行工作流...{Colors.ENDC}\n")

    # 流式输出每个步骤
    for step in graph.stream(initial_state, stream_mode="values"):
        messages = step.get("messages", [])
        if messages:
            latest_msg = messages[-1]
            if hasattr(latest_msg, 'content'):
                content = latest_msg.content
            else:
                content = str(latest_msg)

            # 打印实时进度
            print(f"{Colors.CYAN}[实时进度]{Colors.ENDC}")
            print(f"  {content}\n")
            print(f"{Colors.CYAN}{'-'*60}{Colors.ENDC}")

    # 获取最终状态
    final_state = graph.invoke(initial_state)

    if final_state.get("error"):
        print_error(f"工作流执行失败：{final_state['error']}")
        return

    report = final_state.get("report")
    if report:
        print_success("报告生成完成!")
        print(f"\n{Colors.BOLD}投资建议：{Colors.ENDC}{report.recommendation}")
        print(f"{Colors.BOLD}目标价格：{Colors.ENDC}${report.target_price}")
        print(f"{Colors.BOLD}报告长度：{Colors.ENDC}{len(report.full_report)} 字符\n")

        print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.CYAN}报告预览（前 1000 字符）:{Colors.ENDC}\n")
        print(report.full_report[:1000])
        print("...")

def main():
    """运行所有测试"""
    print_header("🤖 FinAna 实时分析测试脚本")
    print(f"{Colors.BOLD}测试目标：{Colors.ENDC}展示大模型在分析过程中的实时输出")
    print(f"{Colors.BOLD}数据来源：{Colors.ENDC}真实财经数据 + Qwen3.5-plus 大模型")

    # 选择测试项目
    print("\n" + "="*60)
    print("请选择测试模式:")
    print("  1. 完整测试（所有组件 + 工作流）")
    print("  2. 仅测试数据获取")
    print("  3. 仅测试工作流（流式输出）")
    print("="*60)

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\n请输入选择 (1/2/3，默认 1): ").strip() or "1"

    if choice == "1":
        test_data_fetcher()
        test_macro_analyst()
        test_industry_analyst()
        test_equity_analyst()
        test_full_workflow_streaming()
    elif choice == "2":
        test_data_fetcher()
    elif choice == "3":
        test_full_workflow_streaming()
    else:
        print_error("无效选择")
        return

    print_header("✅ 测试完成")

if __name__ == "__main__":
    main()
