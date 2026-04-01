#!/usr/bin/env python3
"""
Stock Info Skill - 命令行使用示例

使用方法:
    python run_stock_skill.py search 贵州茅台
    python run_stock_skill.py quote sh600519
    python run_stock_skill.py company TSLA
    python run_stock_skill.py history sh600519
    python run_stock_skill.py news sh600519
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.stock_info.stock_info import (
    search_stock_info,
    get_stock_quote,
    get_company_info,
    get_stock_history,
    get_stock_news
)


def cmd_search(keyword):
    """搜索股票"""
    print(f"搜索：{keyword}")
    results = search_stock_info(keyword)
    if results:
        for r in results[:10]:
            print(f"  {r.get('code', '')} {r.get('name', '')} ({r.get('market', '')})")
            print(f"    全名：{r.get('full_name', '')}")
    else:
        print("  未找到匹配的股票")


def cmd_quote(symbol):
    """获取行情"""
    print(f"获取行情：{symbol}")
    quote = get_stock_quote(symbol)
    if quote:
        print(f"  名称：{quote.get('name', '')}")
        print(f"  当前价：{quote.get('current_price', 0)}")
        print(f"  涨跌幅：{quote.get('change_pct', 0):.2f}%")
        print(f"  涨跌额：{quote.get('change', 0)}")
        print(f"  成交量：{quote.get('volume', 0)}")
        print(f"  成交额：{quote.get('amount', 0)}")
        print(f"  市盈率：{quote.get('pe_ratio', 0)}")
        print(f"  总市值：{quote.get('market_cap', 0)}")
    else:
        print("  获取行情失败")


def cmd_company(symbol):
    """获取公司信息"""
    print(f"获取公司信息：{symbol}")
    info = get_company_info(symbol)
    if info:
        print(f"  名称：{info.get('name', '')}")
        print(f"  行业：{info.get('industry', '')}")
        print(f"  地区：{info.get('area', '')}")
        print(f"  市盈率 (PE): {info.get('pe_ratio', 0)}")
        print(f"  市净率 (PB): {info.get('pb_ratio', 0)}")
        print(f"  毛利率：{info.get('gross_margin', 0)}%")
        print(f"  ROE: {info.get('roe', 0)}%")
        print(f"  资产负债率：{info.get('debt_ratio', 0)}%")
    else:
        print("  获取公司信息失败")


def cmd_history(symbol, period="d"):
    """获取历史 K 线"""
    print(f"获取历史 K 线：{symbol} (周期：{period})")
    klines = get_stock_history(symbol, period=period)
    if klines:
        print(f"  最近 {len(klines[:10])} 条数据:")
        for k in klines[:10]:
            print(f"    {k.get('date')}: 开{ k.get('open')} 收{ k.get('close')} 高{ k.get('high')} 低{ k.get('low')} 涨跌:{ k.get('change_pct', 0):.2f}%")
    else:
        print("  获取历史数据失败")


def cmd_news(symbol, limit=10):
    """获取新闻"""
    print(f"获取新闻：{symbol}")
    news_list = get_stock_news(symbol, limit)
    if news_list:
        for i, news in enumerate(news_list[:limit], 1):
            print(f"  {i}. {news.get('title', '')}")
            print(f"     来源：{news.get('source', '')} 时间：{news.get('published_at', '')}")
    else:
        print("  获取新闻失败")


def print_usage():
    """打印使用说明"""
    print("""
Stock Info Skill - 上市公司信息查询

用法:
    python run_stock_skill.py <command> <symbol> [options]

命令:
    search <keyword>     搜索股票 (支持名称/代码/拼音)
    quote <symbol>       获取实时行情
    company <symbol>     获取公司信息
    history <symbol>     获取历史 K 线 (可选：period=d/w/m)
    news <symbol>        获取股票新闻 (可选：limit=10)

股票代码格式:
    A 股：sh600519 (茅台), sz000001 (平安银行)
    港股：HK00700 (腾讯), HK09988 (阿里)
    美股：TSLA (特斯拉), AAPL (苹果)

示例:
    python run_stock_skill.py search 贵州茅台
    python run_stock_skill.py quote sh600519
    python run_stock_skill.py company TSLA
    python run_stock_skill.py history sh600519 period=w
    python run_stock_skill.py news 00700 limit=5
""")


def main():
    if len(sys.argv) < 2:
        print_usage()
        return

    cmd = sys.argv[1].lower()

    # 解析参数
    args = {}
    for arg in sys.argv[3:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            args[key] = value

    if cmd == "search":
        if len(sys.argv) < 3:
            print("错误：缺少搜索关键词")
            return
        cmd_search(sys.argv[2])

    elif cmd == "quote":
        if len(sys.argv) < 3:
            print("错误：缺少股票代码")
            return
        cmd_quote(sys.argv[2])

    elif cmd == "company":
        if len(sys.argv) < 3:
            print("错误：缺少股票代码")
            return
        cmd_company(sys.argv[2])

    elif cmd == "history":
        if len(sys.argv) < 3:
            print("错误：缺少股票代码")
            return
        period = args.get('period', 'd')
        cmd_history(sys.argv[2], period)

    elif cmd == "news":
        if len(sys.argv) < 3:
            print("错误：缺少股票代码")
            return
        limit = int(args.get('limit', 10))
        cmd_news(sys.argv[2], limit)

    else:
        print(f"未知命令：{cmd}")
        print_usage()


if __name__ == "__main__":
    main()
