#!/usr/bin/env python3
"""
Enhanced Stock Data Skill 命令行工具

用法:
    python run_stock_data.py quote 600519        # 获取 A 股行情
    python run_stock_data.py quote HK00700       # 获取港股行情
    python run_stock_data.py quote AAPL          # 获取美股行情
    python run_stock_data.py info 600519         # 获取公司信息
    python run_stock_data.py history 600519      # 获取历史 K 线
"""

import sys
import os
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from skills.stock_data_enhanced.stock_data import (
    get_stock_quote,
    get_company_info,
    get_history
)


def format_number(num, decimals=2):
    """格式化数字显示"""
    if num is None or num == 0:
        return "N/A"

    if abs(num) >= 1e12:
        return f"{num/1e12:.{decimals}f}万亿"
    elif abs(num) >= 1e8:
        return f"{num/1e8:.{decimals}f}亿"
    elif abs(num) >= 1e4:
        return f"{num/1e4:.{decimals}f}万"
    else:
        return f"{num:.{decimals}f}"


def print_quote(symbol):
    """打印行情数据"""
    print(f"\n获取 {symbol} 行情...")
    quote = get_stock_quote(symbol)

    if not quote:
        print("❌ 获取失败")
        return

    print(f"\n{'='*60}")
    print(f"{quote.get('name', 'N/A')} ({quote.get('symbol', 'N/A')})")
    print(f"{'='*60}")
    print(f"当前价:    {quote.get('current_price', 'N/A')}")
    print(f"涨跌幅:    {quote.get('change_pct', 'N/A')}%")
    print(f"涨跌额:    {quote.get('change', 'N/A')}")
    print(f"今开:      {quote.get('open', 'N/A')}")
    print(f"最高:      {quote.get('high', 'N/A')}")
    print(f"最低:      {quote.get('low', 'N/A')}")
    print(f"昨收:      {quote.get('prev_close', 'N/A')}")
    print(f"成交量:    {format_number(quote.get('volume', 0))}")
    print(f"成交额:    {format_number(quote.get('amount', 0))}")
    print(f"总市值:    {format_number(quote.get('market_cap', 0))}")
    print(f"市盈率:    {quote.get('pe_ratio', 'N/A')}")
    print(f"市净率:    {quote.get('pb_ratio', 'N/A')}")
    print(f"换手率:    {quote.get('turnover_rate', 'N/A')}%")
    print(f"时间:      {quote.get('timestamp', 'N/A')}")
    print(f"{'='*60}")


def print_company_info(symbol):
    """打印公司信息"""
    print(f"\n获取 {symbol} 公司信息...")
    info = get_company_info(symbol)

    if not info:
        print("❌ 获取失败")
        return

    print(f"\n{'='*60}")
    print(f"{info.get('name', 'N/A')} ({info.get('symbol', 'N/A')})")
    print(f"{'='*60}")
    print(f"行业:      {info.get('industry', 'N/A')}")
    print(f"地区:      {info.get('area', 'N/A')}")
    print(f"上市日期:  {info.get('listing_date', 'N/A')}")
    print(f"市盈率:    {info.get('pe_ratio', 'N/A')}")
    print(f"市净率:    {info.get('pb_ratio', 'N/A')}")
    print(f"总市值:    {format_number(info.get('market_cap', 0))}")
    print(f"营收:      {format_number(info.get('total_revenue', 0))}")
    print(f"净利润:    {format_number(info.get('net_profit', 0))}")
    print(f"毛利率:    {info.get('gross_margin', 'N/A')}%")
    print(f"ROE:       {info.get('roe', 'N/A')}%")
    print(f"{'='*60}")


def print_history(symbol, period="d"):
    """打印历史 K 线"""
    print(f"\n获取 {symbol} 历史 K 线 ({period})...")
    history = get_history(symbol, period=period)

    if not history or len(history) == 0:
        print("❌ 获取失败")
        return

    print(f"\n{'='*60}")
    print(f"共 {len(history)} 条数据")
    print(f"{'='*60}")

    # 显示最近 10 条
    recent = history[-10:] if len(history) > 10 else history

    print(f"{'日期':<12} {'开盘':>10} {'最高':>10} {'最低':>10} {'收盘':>10} {'成交量':>15}")
    print("-" * 60)

    for item in recent:
        print(f"{item.get('date', 'N/A'):<12} "
              f"{item.get('open', 0):>10.2f} "
              f"{item.get('high', 0):>10.2f} "
              f"{item.get('low', 0):>10.2f} "
              f"{item.get('close', 0):>10.2f} "
              f"{format_number(item.get('volume', 0)):>15}")

    print(f"{'='*60}")


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法:")
        print("  python run_stock_data.py quote <symbol>     # 获取行情")
        print("  python run_stock_data.py info <symbol>      # 获取公司信息")
        print("  python run_stock_data.py history <symbol>   # 获取历史 K 线")
        print("\n示例:")
        print("  python run_stock_data.py quote 600519")
        print("  python run_stock_data.py quote HK00700")
        print("  python run_stock_data.py quote AAPL")
        print("  python run_stock_data.py info 600519")
        print("  python run_stock_data.py history 600519")
        return

    command = sys.argv[1].lower()
    symbol = sys.argv[2]

    if command == "quote":
        print_quote(symbol)
    elif command == "info":
        print_company_info(symbol)
    elif command == "history":
        period = sys.argv[3] if len(sys.argv) > 3 else "d"
        print_history(symbol, period)
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    main()
