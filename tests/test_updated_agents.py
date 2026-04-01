#!/usr/bin/env python3
"""
测试更新后的 AI Agent - 集成 stock_info skill

测试内容:
1. EquityAnalystAgent - A 股/港股/美股分析
2. MacroAnalystAgent - 宏观经济分析
3. IndustryAnalystAgent - 行业分析
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.equity_analyst_ai import EquityAnalystAgent
from agents.macro_analyst_ai import MacroAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent


def test_equity_agent_a_share():
    """测试 A 股分析"""
    print("\n" + "=" * 60)
    print("测试 A 股分析 - 贵州茅台 (sh600519)")
    print("=" * 60)

    agent = EquityAnalystAgent()
    result = agent.analyze("sh600519")

    print(f"公司名称：{result.company.name}")
    print(f"当前股价：{result.company.current_price:.2f}元")
    print(f"市盈率：{result.company.pe_ratio}")
    print(f"市值：{result.company.market_cap}")
    print(f"财务健康：{result.financial_health[:50]}...")
    print(f"技术信号：{result.technical_indicator}")
    print(f"风险因素：{len(result.risks)} 项")
    print(f"分析总结：{result.summary[:80]}...")


def test_equity_agent_hk_share():
    """测试港股分析"""
    print("\n" + "=" * 60)
    print("测试港股分析 - 腾讯控股 (HK00700)")
    print("=" * 60)

    agent = EquityAnalystAgent()
    result = agent.analyze("HK00700")

    print(f"公司名称：{result.company.name}")
    print(f"当前股价：{result.company.current_price:.2f}港元")
    print(f"市盈率：{result.company.pe_ratio}")
    print(f"市值：{result.company.market_cap}")
    print(f"财务健康：{result.financial_health[:50]}...")
    print(f"技术信号：{result.technical_indicator}")
    print(f"分析总结：{result.summary[:80]}...")


def test_equity_agent_us_share():
    """测试美股分析"""
    print("\n" + "=" * 60)
    print("测试美股分析 - 特斯拉 (TSLA)")
    print("=" * 60)

    agent = EquityAnalystAgent()
    result = agent.analyze("TSLA")

    print(f"公司名称：{result.company.name}")
    print(f"当前股价：{result.company.current_price:.2f}美元")
    print(f"市盈率：{result.company.pe_ratio}")
    print(f"市值：{result.company.market_cap}")
    print(f"财务健康：{result.financial_health[:50]}...")
    print(f"技术信号：{result.technical_indicator}")
    print(f"分析总结：{result.summary[:80]}...")


def test_equity_agent_chinese_name():
    """测试中文名称识别"""
    print("\n" + "=" * 60)
    print("测试中文名称识别 - '茅台'")
    print("=" * 60)

    agent = EquityAnalystAgent()

    # 测试从查询中提取股票代码
    symbol = agent._extract_symbol("我想分析贵州茅台的股票")
    print(f"识别的股票代码：{symbol}")

    result = agent.analyze(symbol)
    print(f"公司名称：{result.company.name}")
    print(f"当前股价：{result.company.current_price:.2f}元")


def test_macro_agent():
    """测试宏观分析师"""
    print("\n" + "=" * 60)
    print("测试宏观经济分析 - 中国")
    print("=" * 60)

    agent = MacroAnalystAgent()
    result = agent.analyze("china")

    print(f"GDP 增长率：{result.gdp_growth}%")
    print(f"通胀率：{result.inflation_rate}%")
    print(f"利率：{result.interest_rate}%")
    print(f"失业率：{result.unemployment_rate}%")
    print(f"市场情绪：{result.market_sentiment}")
    print(f"经济总结：{result.summary[:80]}...")


def test_industry_agent():
    """测试行业分析师"""
    print("\n" + "=" * 60)
    print("测试行业分析 - 科技行业")
    print("=" * 60)

    agent = IndustryAnalystAgent()
    result = agent.analyze("科技")

    print(f"行业名称：{result.sector_name}")
    print(f"行业增长：{result.sector_growth}%")
    print(f"市场情绪：{result.outlook}")
    print(f"行业趋势：{result.trends}")
    print(f"竞争格局：{result.competitive_landscape[:50]}...")
    print(f"行业总结：{result.summary[:80]}...")


def test_full_workflow():
    """测试完整工作流"""
    print("\n" + "=" * 60)
    print("测试完整工作流 - 分析腾讯控股")
    print("=" * 60)

    # 1. 宏观分析
    print("\n[1/3] 宏观经济分析...")
    macro_agent = MacroAnalystAgent()
    macro_result = macro_agent.analyze("china")
    print(f"  中国市场情绪：{macro_result.market_sentiment}")

    # 2. 行业分析
    print("\n[2/3] 行业分析...")
    industry_agent = IndustryAnalystAgent()
    industry_result = industry_agent.analyze("科技")
    print(f"  科技行业前景：{industry_result.outlook}")

    # 3. 公司分析
    print("\n[3/3] 公司分析...")
    equity_agent = EquityAnalystAgent()
    equity_result = equity_agent.analyze("HK00700")
    print(f"  腾讯控股股价：{equity_result.company.current_price}港元")
    print(f"  技术信号：{equity_result.technical_indicator}")

    print("\n[综合评估]")
    print(f"  宏观：{macro_result.market_sentiment}")
    print(f"  行业：{industry_result.outlook}")
    print(f"  公司：{equity_result.technical_indicator}")


def main():
    """运行所有测试"""
    print("\n" + "#" * 60)
    print("#  更新后的 AI Agent 测试")
    print("#  集成 stock_info skill - 支持 A 股/港股/美股")
    print("#" * 60)

    try:
        # 测试各个 Agent
        test_equity_agent_a_share()
        test_equity_agent_hk_share()
        test_equity_agent_us_share()
        test_equity_agent_chinese_name()
        test_macro_agent()
        test_industry_agent()
        test_full_workflow()

        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
