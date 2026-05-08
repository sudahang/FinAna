"""
测试 Enhanced Stock Data Skill

测试 AKShare 和 yfinance 数据源
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from skills.stock_data_enhanced.stock_data import (
    get_stock_quote,
    get_company_info,
    get_history,
    get_fetcher
)


def test_a_share_quote():
    """测试 A 股行情"""
    print("\n" + "="*60)
    print("测试 A 股行情 (使用 AKShare)")
    print("="*60)

    test_symbols = ["600519", "000001", "sh600519"]

    for symbol in test_symbols:
        print(f"\n获取 {symbol} 行情...")
        quote = get_stock_quote(symbol)

        if quote:
            print(f"✅ 成功")
            print(f"  名称: {quote.get('name', 'N/A')}")
            print(f"  当前价: {quote.get('current_price', 'N/A')}")
            print(f"  涨跌幅: {quote.get('change_pct', 'N/A')}%")
            print(f"  成交量: {quote.get('volume', 'N/A')}")
            print(f"  市盈率: {quote.get('pe_ratio', 'N/A')}")
        else:
            print(f"❌ 失败")


def test_hk_quote():
    """测试港股行情"""
    print("\n" + "="*60)
    print("测试港股行情 (使用 AKShare)")
    print("="*60)

    test_symbols = ["HK00700", "00700", "HK09988"]

    for symbol in test_symbols:
        print(f"\n获取 {symbol} 行情...")
        quote = get_stock_quote(symbol)

        if quote:
            print(f"✅ 成功")
            print(f"  名称: {quote.get('name', 'N/A')}")
            print(f"  当前价: {quote.get('current_price', 'N/A')}")
            print(f"  涨跌幅: {quote.get('change_pct', 'N/A')}%")
            print(f"  成交量: {quote.get('volume', 'N/A')}")
        else:
            print(f"❌ 失败")


def test_us_quote():
    """测试美股行情"""
    print("\n" + "="*60)
    print("测试美股行情 (使用 yfinance)")
    print("="*60)

    test_symbols = ["AAPL", "TSLA", "NVDA"]

    for symbol in test_symbols:
        print(f"\n获取 {symbol} 行情...")
        quote = get_stock_quote(symbol)

        if quote:
            print(f"✅ 成功")
            print(f"  名称: {quote.get('name', 'N/A')}")
            print(f"  当前价: ${quote.get('current_price', 'N/A')}")
            print(f"  涨跌幅: {quote.get('change_pct', 'N/A')}%")
            print(f"  成交量: {quote.get('volume', 'N/A')}")
            print(f"  市盈率: {quote.get('pe_ratio', 'N/A')}")
        else:
            print(f"❌ 失败")


def test_company_info():
    """测试公司信息"""
    print("\n" + "="*60)
    print("测试公司信息")
    print("="*60)

    test_symbols = ["600519", "AAPL"]

    for symbol in test_symbols:
        print(f"\n获取 {symbol} 公司信息...")
        info = get_company_info(symbol)

        if info:
            print(f"✅ 成功")
            print(f"  名称: {info.get('name', 'N/A')}")
            print(f"  行业: {info.get('industry', 'N/A')}")
            print(f"  市盈率: {info.get('pe_ratio', 'N/A')}")
            print(f"  市净率: {info.get('pb_ratio', 'N/A')}")
        else:
            print(f"❌ 失败")


def test_history():
    """测试历史 K 线"""
    print("\n" + "="*60)
    print("测试历史 K 线数据")
    print("="*60)

    # 测试 A 股历史
    print("\n获取 600519 (贵州茅台) 日 K 线...")
    history = get_history("600519", period="d")

    if history and len(history) > 0:
        print(f"✅ 成功，获取 {len(history)} 条数据")
        print(f"  最新日期: {history[-1].get('date', 'N/A')}")
        print(f"  收盘价: {history[-1].get('close', 'N/A')}")
    else:
        print(f"❌ 失败")

    # 测试美股历史
    print("\n获取 AAPL (苹果) 日 K 线...")
    history = get_history("AAPL", period="d")

    if history and len(history) > 0:
        print(f"✅ 成功，获取 {len(history)} 条数据")
        print(f"  最新日期: {history[-1].get('date', 'N/A')}")
        print(f"  收盘价: ${history[-1].get('close', 'N/A')}")
    else:
        print(f"❌ 失败")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Enhanced Stock Data Skill 测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 检查依赖
    try:
        import akshare
        print("✅ AKShare 已安装")
    except ImportError:
        print("❌ AKShare 未安装，请运行: pip install akshare")

    try:
        import yfinance
        print("✅ yfinance 已安装")
    except ImportError:
        print("❌ yfinance 未安装，请运行: pip install yfinance")

    # 运行测试
    test_a_share_quote()
    test_hk_quote()
    test_us_quote()
    test_company_info()
    test_history()

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    main()
