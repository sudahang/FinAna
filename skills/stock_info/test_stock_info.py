#!/usr/bin/env python3
"""
Stock Info Skill 测试脚本
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.stock_info.stock_info import (
    get_stock_info_fetcher,
    search_stock_info,
    get_stock_quote,
    get_company_info,
    get_stock_history,
    get_stock_news
)


def test_search():
    """测试股票搜索"""
    print("\n=== 测试股票搜索 ===")

    # 测试 A 股
    results = search_stock_info("贵州茅台")
    print(f"搜索 '贵州茅台': {len(results)} 条结果")
    for r in results[:3]:
        print(f"  - {r.get('code')} {r.get('name')} ({r.get('market')})")

    # 测试港股
    results = search_stock_info("腾讯")
    print(f"\n搜索 '腾讯': {len(results)} 条结果")
    for r in results[:3]:
        print(f"  - {r.get('code')} {r.get('name')}")

    # 测试美股
    results = search_stock_info("特斯拉")
    print(f"\n搜索 '特斯拉': {len(results)} 条结果")
    for r in results[:3]:
        print(f"  - {r.get('code')} {r.get('name')}")


def test_quote():
    """测试实时行情"""
    print("\n=== 测试实时行情 ===")

    # A 股
    quote = get_stock_quote("sh600519")
    if quote:
        print(f"\n贵州茅台 (sh600519):")
        print(f"  当前价：{quote.get('current_price')}")
        print(f"  涨跌幅：{quote.get('change_pct'):.2f}%")
        print(f"  成交量：{quote.get('volume')}")

    # 港股
    quote = get_stock_quote("HK00700")
    if quote:
        print(f"\n腾讯控股 (HK00700):")
        print(f"  当前价：{quote.get('current_price')}")
        print(f"  涨跌幅：{quote.get('change_pct'):.2f}%")

    # 美股
    quote = get_stock_quote("TSLA")
    if quote:
        print(f"\n特斯拉 (TSLA):")
        print(f"  当前价：{quote.get('current_price')}")
        print(f"  涨跌幅：{quote.get('change_pct'):.2f}%")


def test_company_info():
    """测试公司信息"""
    print("\n=== 测试公司信息 ===")

    info = get_company_info("sh600519")
    if info:
        print(f"\n贵州茅台:")
        print(f"  行业：{info.get('industry')}")
        print(f"  地区：{info.get('area')}")
        print(f"  市盈率：{info.get('pe_ratio')}")
        print(f"  市净率：{info.get('pb_ratio')}")
        print(f"  总市值：{info.get('market_cap')}")

    info = get_company_info("TSLA")
    if info:
        print(f"\n特斯拉:")
        print(f"  行业：{info.get('industry')}")
        print(f"  市盈率：{info.get('pe_ratio')}")
        print(f"  总市值：{info.get('market_cap')}")


def test_history():
    """测试历史 K 线"""
    print("\n=== 测试历史 K 线 ===")

    klines = get_stock_history("sh600519", period="d")
    if klines:
        print(f"\n贵州茅台 - 最近 5 个交易日:")
        for k in klines[:5]:
            print(f"  {k.get('date')}: 开{ k.get('open')} 收{ k.get('close')} 高{ k.get('high')} 低{ k.get('low')}")


def test_news():
    """测试股票新闻"""
    print("\n=== 测试股票新闻 ===")

    news_list = get_stock_news("sh600519", limit=5)
    if news_list:
        print(f"\n贵州茅台 - 最近 5 条新闻:")
        for news in news_list:
            print(f"  - {news.get('title')}")
            print(f"    来源：{news.get('source')} 时间：{news.get('published_at')}")


def main():
    """运行所有测试"""
    print("=" * 50)
    print("Stock Info Skill 测试")
    print("=" * 50)

    fetcher = get_stock_info_fetcher()
    print(f"\nFetcher 初始化成功：{fetcher}")

    test_search()
    test_quote()
    test_company_info()
    test_history()
    test_news()

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
