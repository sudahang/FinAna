#!/usr/bin/env python3
"""
测试更新后的 Agent 数据获取功能（不使用 LLM）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.equity_analyst_ai import EquityAnalystAgent
from agents.macro_analyst_ai import MacroAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent

# 直接导入 stock_info skill
from skills.stock_info.stock_info import (
    get_stock_quote,
    get_company_info,
    get_stock_news,
    get_stock_history,
    get_macro_data
)


def test_stock_info_integration():
    """测试 stock_info skill 集成"""
    print("\n" + "=" * 60)
    print("测试 stock_info skill 数据获取")
    print("=" * 60)

    # A 股
    print("\n1. A 股 - 贵州茅台 (sh600519)")
    quote = get_stock_quote("sh600519")
    if quote:
        print(f"   名称：{quote.get('name')}")
        print(f"   当前价：{quote.get('current_price')}元")
        print(f"   涨跌幅：{quote.get('change_pct'):.2f}%")
        print(f"   市盈率：{quote.get('pe_ratio')}")
    else:
        print("   数据获取失败")

    # 港股
    print("\n2. 港股 - 腾讯控股 (HK00700)")
    quote = get_stock_quote("HK00700")
    if quote:
        print(f"   名称：{quote.get('name')}")
        print(f"   当前价：{quote.get('current_price')}港元")
        print(f"   涨跌幅：{quote.get('change_pct'):.2f}%")
    else:
        print("   数据获取失败")

    # 公司新闻
    print("\n3. 新闻获取 - 贵州茅台")
    news = get_stock_news("sh600519", limit=3)
    if news:
        for n in news[:3]:
            print(f"   - {n.get('title', 'N/A')}")
    else:
        print("   新闻获取失败")

    # 历史数据
    print("\n4. 历史 K 线 - 贵州茅台")
    history = get_stock_history("sh600519", period="d")
    if history:
        print(f"   获取到 {len(history)} 条数据")
        print(f"   最新数据：{history[0]}")
    else:
        print("   历史数据获取失败")


def test_equity_agent_data_fetch():
    """测试 EquityAnalystAgent 数据获取"""
    print("\n" + "=" * 60)
    print("测试 EquityAnalystAgent 数据获取")
    print("=" * 60)

    agent = EquityAnalystAgent()

    # 测试代码转换
    print("\n1. 股票代码标准化")
    test_symbols = ['600519', '000001', '00700', 'TSLA']
    for s in test_symbols:
        std = agent._get_symbol_format(s)
        print(f"   {s} -> {std}")

    # 测试名称识别
    print("\n2. 股票名称识别")
    test_names = ['贵州茅台', '茅台', '腾讯', '特斯拉', '宁德时代']
    for name in test_names:
        symbol = agent._extract_symbol(name)
        print(f"   '{name}' -> {symbol}")

    # 测试技术指标分析
    print("\n3. 技术指标分析")
    history = get_stock_history("sh600519", period="d")
    tech_analysis = agent._analyze_technical_indicators(history)
    print(f"   {tech_analysis}")


def test_macro_agent():
    """测试 MacroAnalystAgent"""
    print("\n" + "=" * 60)
    print("测试 MacroAnalystAgent 宏观数据")
    print("=" * 60)

    # 测试宏观数据获取
    print("\n1. 中国宏观数据")
    macro = get_macro_data("china")
    print(f"   GDP 增长：{macro.get('gdp_growth')}%")
    print(f"   通胀率：{macro.get('inflation_rate')}%")
    print(f"   利率：{macro.get('interest_rate')}%")
    print(f"   PMI: {macro.get('manufacturing_pmi')}")

    print("\n2. 美国宏观数据")
    macro = get_macro_data("us")
    print(f"   GDP 增长：{macro.get('gdp_growth')}%")
    print(f"   通胀率：{macro.get('inflation_rate')}%")
    print(f"   利率：{macro.get('interest_rate')}%")
    print(f"   PMI: {macro.get('manufacturing_pmi')}")


def test_industry_agent():
    """测试 IndustryAnalystAgent"""
    print("\n" + "=" * 60)
    print("测试 IndustryAnalystAgent 行业数据")
    print("=" * 60)

    agent = IndustryAnalystAgent()

    # 测试行业数据获取
    print("\n1. 科技行业数据")
    industry = agent.data_fetcher.get_industry_data("科技")
    print(f"   行业增长：{industry.get('sector_growth')}%")
    print(f"   平均 PE: {industry.get('avg_pe_ratio')}")
    print(f"   市场情绪：{industry.get('market_sentiment')}")

    print("\n2. 汽车行业数据")
    industry = agent.data_fetcher.get_industry_data("汽车")
    print(f"   行业增长：{industry.get('sector_growth')}%")
    print(f"   平均 PE: {industry.get('avg_pe_ratio')}")
    print(f"   市场情绪：{industry.get('market_sentiment')}")


def test_symbol_extraction():
    """测试股票符号提取"""
    print("\n" + "=" * 60)
    print("测试股票符号提取功能")
    print("=" * 60)

    agent = EquityAnalystAgent()

    test_queries = [
        "我想分析贵州茅台",
        "腾讯控股怎么样",
        "特斯拉的股价",
        "600519 基本面分析",
        "00700 港股分析",
        "分析一下宁德时代",
        "AAPL 财报分析",
    ]

    print("\n查询 -> 识别的股票代码")
    print("-" * 40)
    for query in test_queries:
        symbol = agent._extract_symbol(query)
        print(f"'{query[:15]}...' -> {symbol}")


def main():
    """运行所有测试"""
    print("\n" + "#" * 60)
    print("#  更新后的 AI Agent 数据获取测试")
    print("#  集成 stock_info skill - 不依赖 LLM")
    print("#" * 60)

    try:
        test_stock_info_integration()
        test_equity_agent_data_fetch()
        test_macro_agent()
        test_industry_agent()
        test_symbol_extraction()

        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
