#!/usr/bin/env python3
"""
FinAna 命令行客户端 - 流式输出股票分析结果

用法:
    python cli_analyzer.py "分析腾讯股票"
    python cli_analyzer.py "茅台值得投资吗"
    python cli_analyzer.py "TSLA 走势分析"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.input_router_ai import InputRouterAgent
from agents.macro_analyst_ai import MacroAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent
from agents.equity_analyst_ai import EquityAnalystAgent
from agents.report_synthesizer_ai import ReportSynthesizerAgent
from llm.client import get_llm_client

# ANSI 颜色代码
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


def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_step(step: int, total: int, text: str):
    """打印步骤"""
    print(f"{Colors.CYAN}[{step}/{total}] {text}{Colors.ENDC}")


def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")


def analyze_stock(query: str):
    """
    分析股票查询

    Args:
        query: 用户查询
    """
    print_header(f"FinAna 智能投研分析")
    print_info(f"查询：{query}\n")

    # 初始化 Agent
    print_step(0, 5, "初始化 Agent...")
    router = InputRouterAgent()
    macro_agent = MacroAnalystAgent()
    industry_agent = IndustryAnalystAgent()
    equity_agent = EquityAnalystAgent()
    synthesizer = ReportSynthesizerAgent()
    print_success("Agent 初始化完成\n")

    # Step 1: 解析查询
    print_step(1, 5, "解析用户查询...")
    params = router.parse_query(query)

    country = params.get('country', 'us')
    symbol = params.get('symbol', '')
    sector = params.get('sector', '')
    query_type = params.get('query_type', 'stock_analysis')
    confidence = params.get('confidence', 0)

    # 显示解析结果
    country_name = {'china': '中国 (A 股)', 'hk': '香港 (港股)', 'us': '美国 (美股)'}
    print(f"  市场：{country_name.get(country, country)}")
    print(f"  股票：{symbol or '未检测到具体股票'}")
    print(f"  行业：{sector or '未检测到具体行业'}")
    print(f"  类型：{query_type}")
    print(f"  置信度：{confidence:.0%}")
    print_success("查询解析完成\n")

    # Step 2: 宏观经济分析
    print_step(2, 5, f"宏观经济分析 ({country_name.get(country, country)})...")
    try:
        macro_context = macro_agent.analyze(country)
        print(f"  GDP 增长：{macro_context.gdp_growth}%")
        print(f"  通胀率：{macro_context.inflation_rate}%")
        print(f"  利率：{macro_context.interest_rate}%")
        print(f"  市场情绪：{macro_context.market_sentiment}")
        print_success("宏观经济分析完成\n")
    except Exception as e:
        print_error(f"宏观分析失败：{e}")
        macro_context = None

    # Step 3: 行业分析
    print_step(3, 5, f"行业分析 ({sector})...")
    try:
        industry_context = industry_agent.analyze_with_context(query)
        print(f"  行业增长：{industry_context.sector_growth}%")
        print(f"  行业前景：{industry_context.outlook}")
        print(f"  竞争格局：{industry_context.competitive_landscape[:50]}...")
        print_success("行业分析完成\n")
    except Exception as e:
        print_error(f"行业分析失败：{e}")
        industry_context = None

    # Step 4: 公司分析
    print_step(4, 5, f"公司分析 ({symbol})...")
    try:
        if symbol:
            company_analysis = equity_agent.analyze(symbol)
            print(f"  公司：{company_analysis.company.name}")
            print(f"  当前股价：{company_analysis.company.current_price}")
            print(f"  市盈率：{company_analysis.company.pe_ratio}")
            print(f"  市值：{company_analysis.company.market_cap}")
            print(f"  技术信号：{company_analysis.technical_indicator}")
            print(f"  财务健康：{company_analysis.financial_health[:30]}...")
            print_success("公司分析完成\n")
        else:
            print_info("未检测到具体股票，跳过公司分析")
            company_analysis = None
    except Exception as e:
        print_error(f"公司分析失败：{e}")
        company_analysis = None

    # Step 5: 合成报告
    print_step(5, 5, "合成最终报告...")
    try:
        if company_analysis and macro_context and industry_context:
            report = synthesizer.synthesize(
                query=query,
                macro_context=macro_context,
                industry_context=industry_context,
                company_analysis=company_analysis
            )

            print(f"\n{Colors.GREEN}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
            print(f"{Colors.GREEN}{Colors.BOLD}投资建议报告{Colors.ENDC}")
            print(f"{Colors.GREEN}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

            print(f"{Colors.BOLD}投资建议:{Colors.ENDC} {report.recommendation}")
            print(f"{Colors.BOLD}目标价格:{Colors.ENDC} ${report.target_price}")
            print(f"{Colors.BOLD}报告长度:{Colors.ENDC} {len(report.full_report)} 字符\n")

            # 输出完整报告
            print(f"{Colors.YELLOW}【完整分析报告】{Colors.ENDC}")
            print("-" * 60)
            print(report.full_report)
            print("-" * 60)

            print_success("报告生成完成")
        else:
            print_error("缺少必要的分析结果，无法生成完整报告")
    except Exception as e:
        print_error(f"报告合成失败：{e}")

    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}分析完成{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def main():
    """主函数"""
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h', 'help']:
        print(f"""
{Colors.BOLD}FinAna 智能投研分析系统{Colors.ENDC}

{Colors.YELLOW}用法:{Colors.ENDC}
    python cli_analyzer.py "查询内容"
    ./cli.sh "查询内容"

{Colors.YELLOW}示例:{Colors.ENDC}
    python cli_analyzer.py "分析腾讯股票"
    python cli_analyzer.py "茅台值得投资吗"
    python cli_analyzer.py "TSLA 走势分析"
    python cli_analyzer.py "分析贵州茅台"
    python cli_analyzer.py "港股美团怎么样"

{Colors.YELLOW}支持的市场:{Colors.ENDC}
    - A 股：贵州茅台 (sh600519)、宁德时代 (sz300750)
    - 港股：腾讯控股 (HK00700)、美团 (HK03690)、小米集团 (HK01810)
    - 美股：特斯拉 (TSLA)、英伟达 (NVDA)、苹果 (AAPL)
    - 中概股：阿里巴巴 (BABA)、拼多多 (PDD)、京东 (JD)

{Colors.YELLOW}选项:{Colors.ENDC}
    --help, -h, help    显示帮助信息
""")
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    # 组合查询参数
    query = " ".join(sys.argv[1:])
    analyze_stock(query)


if __name__ == "__main__":
    main()
