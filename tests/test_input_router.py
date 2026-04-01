#!/usr/bin/env python3
"""
测试 Input Router Agent - 用户查询意图识别
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.input_router_ai import InputRouterAgent, get_router_agent


def test_query_parsing():
    """测试查询解析功能"""
    print("\n" + "=" * 60)
    print("测试查询解析功能")
    print("=" * 60)

    agent = InputRouterAgent()

    test_queries = [
        # A 股
        "分析贵州茅台",
        "茅台股票怎么样",
        "600519 基本面分析",
        "sh600519 走势",
        "宁德时代值得投资吗",
        "分析一下招商银行",

        # 港股
        "分析腾讯",
        "腾讯控股股票",
        "HK00700 走势分析",
        "美团港股怎么样",
        "小米集团基本面",

        # 美股
        "分析特斯拉",
        "TSLA 股票分析",
        "英伟达值得买入吗",
        "苹果公司估值",
        "微软和谷歌哪个更好",

        # 中概股
        "阿里巴巴股票",
        "拼多多走势",
        "蔚来汽车分析",

        # 行业分析
        "科技行业前景",
        "新能源汽车板块",
        "医药行业分析",

        # 宏观分析
        "中国经济形势",
        "美国 GDP 增长",
        "通胀对投资的影响"
    ]

    print(f"\n{'查询':<30} {'国家':<8} {'股票':<12} {'行业':<8} {'类型':<18} {'置信度':<8}")
    print("-" * 90)

    for query in test_queries:
        params = agent.parse_query(query)
        country = params.get('country', '')
        symbol = params.get('symbol', '')
        sector = params.get('sector', '')
        query_type = params.get('query_type', '')
        confidence = params.get('confidence', 0)

        # Truncate for display
        display_query = query[:28] + "..." if len(query) > 30 else query

        print(f"{display_query:<30} {country:<8} {symbol:<12} {sector:<8} {query_type:<18} {confidence:.0%}")


def test_stock_symbol_detection():
    """测试股票代码识别"""
    print("\n" + "=" * 60)
    print("测试股票代码识别")
    print("=" * 60)

    agent = InputRouterAgent()

    test_cases = [
        # (查询，预期代码)
        ("贵州茅台", "sh600519"),
        ("茅台", "sh600519"),
        ("腾讯", "HK00700"),
        ("腾讯控股", "HK00700"),
        ("特斯拉", "TSLA"),
        ("TSLA", "TSLA"),
        ("宁德时代", "sz300750"),
        ("600519", "sh600519"),
        ("sh600519", "sh600519"),
        ("HK00700", "HK00700"),
        ("阿里巴巴", "BABA"),
        ("拼多多", "PDD"),
    ]

    print()
    passed = 0
    failed = 0

    for query, expected in test_cases:
        params = agent.parse_query(query)
        symbol = params.get('symbol', '')
        status = "✓" if symbol == expected else "✗"

        if symbol == expected:
            passed += 1
        else:
            failed += 1

        print(f"  {status} '{query}' -> {symbol} (预期：{expected})")

    print(f"\n通过：{passed}, 失败：{failed}")


def test_country_detection():
    """测试国家/市场识别"""
    print("\n" + "=" * 60)
    print("测试国家/市场识别")
    print("=" * 60)

    agent = InputRouterAgent()

    test_cases = [
        # (查询，预期市场)
        ("A 股分析", "china"),
        ("港股行情", "hk"),
        ("美股走势", "us"),
        ("贵州茅台", "china"),
        ("腾讯控股", "hk"),
        ("特斯拉", "us"),
        ("纳斯达克", "us"),
        ("沪深股市", "china"),
        ("恒生指数", "hk"),
    ]

    print()
    passed = 0
    failed = 0

    for query, expected in test_cases:
        params = agent.parse_query(query)
        country = params.get('country', '')
        status = "✓" if country == expected else "✗"

        if country == expected:
            passed += 1
        else:
            failed += 1

        print(f"  {status} '{query}' -> {country} (预期：{expected})")

    print(f"\n通过：{passed}, 失败：{failed}")


def test_sector_detection():
    """测试行业识别"""
    print("\n" + "=" * 60)
    print("测试行业识别")
    print("=" * 60)

    agent = InputRouterAgent()

    test_cases = [
        # (查询，预期行业)
        ("科技股票", "科技"),
        ("新能源汽车", "汽车"),
        ("医药生物", "医疗"),
        ("银行保险", "金融"),
        ("食品饮料", "消费"),
        ("光伏能源", "能源"),
        ("腾讯", "科技"),
        ("特斯拉", "汽车"),
        ("宁德时代", "能源"),  # 电池属于能源
    ]

    print()
    passed = 0
    failed = 0

    for query, expected in test_cases:
        params = agent.parse_query(query)
        sector = params.get('sector', '')
        status = "✓" if sector == expected else "~"  # ~ means partial match

        if sector == expected:
            passed += 1
        else:
            failed += 1

        print(f"  {status} '{query}' -> {sector} (预期：{expected})")

    print(f"\n通过：{passed}, 失败：{failed}")


def test_query_type_detection():
    """测试查询类型识别"""
    print("\n" + "=" * 60)
    print("测试查询类型识别")
    print("=" * 60)

    agent = InputRouterAgent()

    test_cases = [
        # (查询，预期类型)
        ("分析特斯拉股票", "stock_analysis"),
        ("科技行业前景", "industry_analysis"),
        ("中国经济形势", "macro_analysis"),
        ("TSLA 走势", "stock_analysis"),
        ("GDP 增长", "macro_analysis"),
        ("医药板块分析", "industry_analysis"),
    ]

    print()
    passed = 0
    failed = 0

    for query, expected in test_cases:
        params = agent.parse_query(query)
        query_type = params.get('query_type', '')
        status = "✓" if query_type == expected else "✗"

        if query_type == expected:
            passed += 1
        else:
            failed += 1

        print(f"  {status} '{query}' -> {query_type} (预期：{expected})")

    print(f"\n通过：{passed}, 失败：{failed}")


def main():
    """运行所有测试"""
    print("\n" + "#" * 60)
    print("#  Input Router Agent 测试")
    print("#  用户查询意图识别")
    print("#" * 60)

    try:
        test_query_parsing()
        test_stock_symbol_detection()
        test_country_detection()
        test_sector_detection()
        test_query_type_detection()

        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
