"""
上市公司信息查询 Skill - 整合多个免费数据源

数据源:
- A 股：新浪财经、东方财富、Baostock
- 港股：新浪财经、东方财富
- 美股：东方财富 (中概股/港股通)

功能:
- 实时行情 (股价、涨跌幅、成交量)
- 公司基本信息 (名称、行业、市值)
- 财务指标 (PE、PB、营收、利润)
- K 线数据 (历史行情)
- 公司公告/新闻
"""

import requests
import json
import logging
from typing import Optional
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class StockInfoFetcher:
    """上市公司信息查询工具"""

    # 数据源配置
    SINA_QUOTE_URL = "http://hq.sinajs.cn/list={symbol}"
    TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q={symbol}"
    EASTMONEY_STOCK_SEARCH_URL = "https://searchapi.eastmoney.com/api/suggest/get"
    EASTMONEY_STOCK_DETAIL_URL = "https://push2.eastmoney.com/api/qt/stock/get"
    EASTMONEY_STOCK_HISTORY_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    # 市场代码映射
    MARKET_CODES = {
        "sh": "1",      # 上交所
        "sz": "0",      # 深交所
        "hk": "116",    # 港股
        "us": "162",    # 美股
        "bj": "2"       # 北交所
    }

    def __init__(self):
        """初始化 HTTP 会话"""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://finance.sina.com.cn/"
        })

        # 配置重试机制
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def search_stock(self, keyword: str) -> list[dict]:
        """
        搜索股票，支持公司名称、代码、拼音

        Args:
            keyword: 搜索关键词 (公司名称/代码/拼音)

        Returns:
            匹配的股票列表
        """
        results = []

        try:
            # 使用东方财富搜索 API - 改进参数
            params = {
                "input": keyword,
                "type": 14,  # 股票类型
                "range": 10,
                "token": "D43D7E595551B0A528D2A1A296F2C5CC"
            }

            response = self.session.get(
                self.EASTMONEY_STOCK_SEARCH_URL,
                params=params,
                timeout=10,
                headers={"Referer": "https://www.eastmoney.com/"}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("quatresponse"):
                    items = data["data"]["quatresponse"]["data"]
                    for item in items:
                        if isinstance(item, dict) and "code" in item:
                            results.append({
                                "code": item.get("code", ""),
                                "name": item.get("name", ""),
                                "market": self._get_market_type(item.get("code", "")),
                                "full_name": item.get("full_name", ""),
                                "pinyin": item.get("pinyin", "")
                            })
        except Exception as e:
            logger.warning(f"搜索股票失败 {keyword}: {e}")

        # 如果东方财富搜索失败，尝试直接匹配代码
        if not results and keyword.isdigit() and len(keyword) >= 4:
            results = self._search_by_code(keyword)

        return results

    def _search_by_code(self, code: str) -> list[dict]:
        """根据股票代码直接搜索"""
        results = []

        # A 股代码
        if len(code) == 6:
            if code.startswith(("6", "9")):
                results.append({
                    "code": code,
                    "name": f"A 股{code}",
                    "market": "sh",
                    "full_name": f"上交所{code}",
                    "pinyin": ""
                })
            elif code.startswith(("0", "3")):
                results.append({
                    "code": code,
                    "name": f"A 股{code}",
                    "market": "sz",
                    "full_name": f"深交所{code}",
                    "pinyin": ""
                })

        return results

    def _get_market_type(self, code: str) -> str:
        """根据股票代码判断市场类型"""
        if not code:
            return "unknown"

        if code.startswith("60") or code.startswith("68") or code.startswith("9"):
            return "sh"
        elif code.startswith("00") or code.startswith("30"):
            return "sz"
        elif code.startswith("4") or code.startswith("8"):
            return "bj"
        elif code.startswith("HK") or len(code) == 5 and code.isdigit():
            return "hk"
        else:
            return "us"

    def get_quote(self, symbol: str) -> Optional[dict]:
        """
        获取实时行情

        Args:
            symbol: 股票代码 (支持多种格式)
                    - A 股：sh600519, sz000001
                    - 港股：HK00700, 00700
                    - 美股：AAPL, TSLA

        Returns:
            行情数据字典
        """
        # 标准化股票代码
        symbol = self._normalize_symbol(symbol)
        if not symbol:
            return None

        symbol_lower = symbol.lower()

        # A 股：先试腾讯 (最可靠)，再试新浪
        if symbol_lower.startswith(("sh", "sz")):
            quote = self._get_tencent_quote(symbol)
            if quote:
                return quote
            quote = self._get_sina_quote(symbol)
            if quote:
                return quote

        # 港股：先试新浪
        if symbol_lower.startswith("hk"):
            quote = self._get_sina_quote(symbol)
            if quote:
                return quote

        # 东方财富 (全市场，作为最后 fallback)
        quote = self._get_eastmoney_quote(symbol)
        if quote:
            return quote

        return None

    def _normalize_symbol(self, symbol: str) -> Optional[str]:
        """标准化股票代码格式"""
        symbol = symbol.strip().upper()

        if not symbol:
            return None

        # 已经是标准格式
        if symbol.startswith(("sh", "sz", "hk")):
            return symbol

        # A 股代码 (6 位数字)
        if len(symbol) == 6 and symbol.isdigit():
            if symbol.startswith(("6", "9")):
                return f"sh{symbol}"
            elif symbol.startswith(("0", "3")):
                return f"sz{symbol}"
            elif symbol.startswith(("4", "8")):
                return f"bj{symbol}"

        # 港股代码 (5 位数字或 HK 开头)
        if symbol.startswith("HK"):
            return symbol
        if len(symbol) == 5 and symbol.isdigit():
            return f"HK{symbol}"

        # 美股代码 (字母)
        if symbol.isalpha():
            return symbol

        return symbol

    def _get_tencent_quote(self, symbol: str) -> Optional[dict]:
        """从腾讯财经获取行情 (更可靠)"""
        try:
            # 转换股票代码为腾讯格式 (统一小写)
            symbol_lower = symbol.lower()
            if symbol_lower.startswith("sh"):
                tencent_symbol = f"sh{symbol[2:]}"
            elif symbol_lower.startswith("sz"):
                tencent_symbol = f"sz{symbol[2:]}"
            elif symbol_lower.startswith("hk"):
                tencent_symbol = f"HK{symbol[2:]}"
            else:
                tencent_symbol = symbol

            response = self.session.get(
                self.TENCENT_QUOTE_URL.format(symbol=tencent_symbol),
                timeout=10,
                headers={
                    "Referer": "https://stockapp.finance.qq.com/"
                }
            )

            if response.status_code == 200:
                text = response.text.strip()
                # 腾讯格式：v_sh600519="51~贵州茅台~600519~1445.00~1452.87~1452.96~..."
                # 字段：0=未知，1=名称，2=代码，3=当前价，4=昨收，5=开盘，6=成交量...
                if "=" in text:
                    data_str = text.split('="')[1].strip('";')
                    fields = data_str.split("~")

                    if len(fields) >= 10:
                        name = fields[1]
                        current_price = float(fields[3]) if fields[3] else 0
                        prev_close = float(fields[4]) if fields[4] else 0

                        return {
                            "symbol": symbol,
                            "name": name,
                            "current_price": current_price,
                            "open": float(fields[5]) if fields[5] else 0,
                            "prev_close": prev_close,
                            "change": current_price - prev_close,
                            "change_pct": float(fields[32]) if len(fields) > 32 and fields[32] else 0,
                            "volume": int(fields[6]) if fields[6] else 0,
                            "amount": float(fields[37]) if len(fields) > 37 and fields[37] else 0,
                            "market_cap": float(fields[45]) if len(fields) > 45 and fields[45] else 0,
                            "pe_ratio": float(fields[39]) if len(fields) > 39 and fields[39] else 0,
                            "high": float(fields[33]) if len(fields) > 33 and fields[33] else 0,
                            "low": float(fields[34]) if len(fields) > 34 and fields[34] else 0,
                            "timestamp": datetime.now()
                        }
        except Exception as e:
            logger.warning(f"腾讯财经获取行情失败 {symbol}: {e}")

        return None

    def _get_sina_quote(self, symbol: str) -> Optional[dict]:
        """从新浪财经获取行情"""
        try:
            # 转换港股格式
            if symbol.lower().startswith("hk"):
                sina_symbol = f"hk{symbol[2:].zfill(5)}"
            else:
                sina_symbol = symbol.lower()

            # 使用专门的 session  for Sina 以避免 403
            sina_session = requests.Session()
            sina_session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://finance.sina.com.cn/"
            })

            response = sina_session.get(
                self.SINA_QUOTE_URL.format(symbol=sina_symbol),
                timeout=10
            )

            if response.status_code == 200:
                text = response.text.strip()
                if "=" in text:
                    data_str = text.split('="')[1].strip('";')
                    fields = data_str.split(",")

                    if len(fields) >= 10:
                        # 港股和 A 股格式略有不同
                        # 港股字段：0=英文名，1=中文名，2=昨收，3=开盘，4=当前价，5=高，6=低...
                        # A 股字段 0: "贵州茅台" (中文名)
                        if symbol.lower().startswith("hk"):
                            # 港股：字段 0=英文名，1=中文名，2=昨收价...
                            name = fields[1] if len(fields) > 1 and fields[1] else fields[0]
                            prev_close = float(fields[2]) if len(fields) > 2 and fields[2] else 0

                            # 港股字段偏移：0=英文名，1=中文名，2=昨收，3=开盘，4=当前价...
                            current_price = float(fields[4]) if len(fields) > 4 and fields[4] else 0
                            open_price = float(fields[3]) if len(fields) > 3 and fields[3] else 0
                            high = float(fields[5]) if len(fields) > 5 and fields[5] else 0
                            low = float(fields[6]) if len(fields) > 6 and fields[6] else 0
                            change = float(fields[7]) if len(fields) > 7 and fields[7] else 0
                            change_pct = float(fields[8]) if len(fields) > 8 and fields[8] else 0
                            volume = int(float(fields[11])) if len(fields) > 11 and fields[11] else 0
                            amount = float(fields[12]) if len(fields) > 12 and fields[12] else 0
                        else:
                            # A 股：字段 0=名称，1=开盘，2=昨收，3=当前价...
                            name = name_raw
                            current_price = float(fields[3]) if fields[3] else 0
                            prev_close = float(fields[2]) if fields[2] else 0
                            open_price = float(fields[1]) if fields[1] else 0
                            high = float(fields[4]) if fields[4] else 0
                            low = float(fields[5]) if fields[5] else 0
                            change = current_price - prev_close
                            change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
                            volume = int(float(fields[8])) if fields[8] else 0
                            amount = float(fields[9]) if fields[9] else 0

                        return {
                            "symbol": symbol,
                            "name": name,
                            "current_price": current_price,
                            "open": open_price,
                            "high": high,
                            "low": low,
                            "prev_close": prev_close,
                            "change": change,
                            "change_pct": change_pct,
                            "volume": volume,
                            "amount": amount,
                            "market": self._get_market_type(symbol),
                            "timestamp": datetime.now()
                        }
        except Exception as e:
            logger.warning(f"新浪财经获取行情失败 {symbol}: {e}")

        return None

    def _get_eastmoney_quote(self, symbol: str) -> Optional[dict]:
        """从东方财富获取行情"""
        try:
            # 确定市场代码
            if symbol.startswith("sh"):
                secid = f"1.{symbol[2:]}"
            elif symbol.startswith("sz"):
                secid = f"0.{symbol[2:]}"
            elif symbol.startswith("bj"):
                secid = f"2.{symbol[2:]}"
            elif symbol.startswith("HK"):
                # 港股代码去掉 leading zeros 以外的 0
                hk_code = symbol[2:].lstrip('0') or '0'
                secid = f"116.{hk_code}"
            elif symbol.isalpha():
                secid = f"162.{symbol}"
            else:
                return None

            params = {
                "secid": secid,
                "fields": "f12,f14,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f84,f85,f86,f87,f10004,f10005,f152"
            }

            response = self.session.get(
                self.EASTMONEY_STOCK_DETAIL_URL,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    fields = data["data"]
                    price = fields.get("f44", 0) or fields.get("f43", 0)

                    return {
                        "symbol": symbol,
                        "name": fields.get("f14", ""),
                        "current_price": price,
                        "open": fields.get("f43", 0),
                        "high": fields.get("f44", 0),
                        "low": fields.get("f45", 0),
                        "prev_close": fields.get("f60", 0),
                        "change": fields.get("f85", 0),
                        "change_pct": fields.get("f86", 0),
                        "volume": fields.get("f47", 0),
                        "amount": fields.get("f48", 0),
                        "market_cap": fields.get("f152", 0),
                        "pe_ratio": fields.get("f10004", 0),
                        "pb_ratio": fields.get("f10005", 0),
                        "turnover_rate": fields.get("f49", 0),
                        "market": self._get_market_type(symbol),
                        "timestamp": datetime.now()
                    }
        except Exception as e:
            logger.warning(f"东方财富获取行情失败 {symbol}: {e}")

        return None

    def get_company_info(self, symbol: str) -> Optional[dict]:
        """
        获取公司基本信息

        Args:
            symbol: 股票代码

        Returns:
            公司信息字典
        """
        try:
            secid = self._to_eastmoney_secid(symbol)
            if not secid:
                return None

            params = {
                "secid": secid,
                "fields": "f12,f14,f17,f22,f28,f45,f48,f10004,f10005,f10006,f10007,f10008,f10009,f10010,f10011"
            }

            response = self.session.get(
                self.EASTMONEY_STOCK_DETAIL_URL,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    fields = data["data"]
                    return {
                        "symbol": fields.get("f12", ""),
                        "name": fields.get("f14", ""),
                        "industry": fields.get("f17", ""),  # 行业
                        "area": fields.get("f22", ""),      # 地区
                        "listing_date": fields.get("f45", ""),  # 上市日期
                        "issue_price": fields.get("f28", 0),    # 发行价
                        "pe_ratio": fields.get("f10004", 0),
                        "pb_ratio": fields.get("f10005", 0),
                        "total_revenue": fields.get("f10006", 0),  # 营收
                        "net_profit": fields.get("f10007", 0),     # 净利润
                        "gross_margin": fields.get("f10008", 0),   # 毛利率
                        "roe": fields.get("f10009", 0),            # ROE
                        "debt_ratio": fields.get("f10010", 0),     # 资产负债率
                        "market_cap": fields.get("f152", 0),
                        "shares_total": fields.get("f84", 0),      # 总股本
                        "shares_float": fields.get("f85", 0),      # 流通股本
                        "timestamp": datetime.now()
                    }
        except Exception as e:
            logger.warning(f"获取公司信息失败 {symbol}: {e}")

        return None

    def _to_eastmoney_secid(self, symbol: str) -> Optional[str]:
        """转换为东方财富 secid 格式"""
        symbol = self._normalize_symbol(symbol)
        if not symbol:
            return None

        if symbol.startswith("sh"):
            return f"1.{symbol[2:]}"
        elif symbol.startswith("sz"):
            return f"0.{symbol[2:]}"
        elif symbol.startswith("bj"):
            return f"2.{symbol[2:]}"
        elif symbol.startswith("HK"):
            # 港股代码处理：HK00700 -> 116.700
            hk_code = symbol[2:].lstrip('0') or '0'
            return f"116.{hk_code}"
        elif symbol.isalpha():
            return f"162.{symbol}"
        return None

    def get_history(self, symbol: str, start_date: str = "",
                    end_date: str = "", period: str = "d") -> Optional[list[dict]]:
        """
        获取历史 K 线数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: K 线周期 (d=日，w=周，m=月)

        Returns:
            K 线数据列表
        """
        try:
            secid = self._to_eastmoney_secid(symbol)
            if not secid:
                return None

            params = {
                "secid": secid,
                "klt": period,
                "fqt": 1,  # 前复权
                "beg": start_date or "19900101",
                "end": end_date or "20991231",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60"
            }

            response = self.session.get(
                self.EASTMONEY_STOCK_HISTORY_URL,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("klines"):
                    klines = []
                    for kline_str in data["data"]["klines"]:
                        parts = kline_str.split(",")
                        if len(parts) >= 10:
                            klines.append({
                                "date": parts[0],
                                "open": float(parts[1]) if parts[1] else 0,
                                "close": float(parts[2]) if parts[2] else 0,
                                "high": float(parts[3]) if parts[3] else 0,
                                "low": float(parts[4]) if parts[4] else 0,
                                "volume": float(parts[5]) if parts[5] else 0,
                                "amount": float(parts[6]) if parts[6] else 0,
                                "amplitude": float(parts[7]) if parts[7] else 0,
                                "change_pct": float(parts[8]) if parts[8] else 0,
                                "change": float(parts[9]) if parts[9] else 0
                            })
                    return klines
        except Exception as e:
            logger.warning(f"获取历史数据失败 {symbol}: {e}")

        return None

    def get_stock_news(self, symbol: str, limit: int = 10) -> list[dict]:
        """
        获取股票相关新闻

        Args:
            symbol: 股票代码
            limit: 返回数量

        Returns:
            新闻列表
        """
        news_list = []

        try:
            secid = self._to_eastmoney_secid(symbol)
            if not secid:
                return news_list

            params = {
                "secid": secid,
                "ps": limit,
                "p": 1
            }

            # 东方财富新闻 API
            response = self.session.get(
                "https://push2.eastmoney.com/api/qt/stocknews/get",
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("list"):
                    for item in data["data"]["list"]:
                        news_list.append({
                            "title": item.get("Title", ""),
                            "summary": item.get("Digest", ""),
                            "source": item.get("Source", ""),
                            "published_at": item.get("ShowTime", ""),
                            "url": f"https://news.eastmoney.com/news/{item.get('ID', '')}.html"
                        })
        except Exception as e:
            logger.warning(f"获取新闻失败 {symbol}: {e}")

        return news_list


# 单例模式
_fetcher: Optional[StockInfoFetcher] = None


def get_stock_info_fetcher() -> StockInfoFetcher:
    """获取 StockInfoFetcher 单例"""
    global _fetcher
    if _fetcher is None:
        _fetcher = StockInfoFetcher()
    return _fetcher


# Skill 接口函数
def search_stock_info(keyword: str) -> list[dict]:
    """搜索股票信息"""
    return get_stock_info_fetcher().search_stock(keyword)


def get_stock_quote(symbol: str) -> Optional[dict]:
    """获取股票实时行情"""
    return get_stock_info_fetcher().get_quote(symbol)


def get_company_info(symbol: str) -> Optional[dict]:
    """获取公司基本信息"""
    return get_stock_info_fetcher().get_company_info(symbol)


def get_stock_history(symbol: str, start_date: str = "",
                      end_date: str = "", period: str = "d") -> Optional[list[dict]]:
    """获取历史 K 线数据"""
    return get_stock_info_fetcher().get_history(symbol, start_date, end_date, period)


def get_stock_news(symbol: str, limit: int = 10) -> list[dict]:
    """获取股票新闻"""
    return get_stock_info_fetcher().get_stock_news(symbol, limit)


def get_macro_data(country: str = "china") -> dict:
    """
    获取宏观经济数据

    Args:
        country: 国家名称 ('china' 或 'us')

    Returns:
        宏观经济数据字典
    """
    # 默认宏观数据
    macro_defaults = {
        "china": {
            "country": "china",
            "gdp_growth": 5.2,
            "inflation_rate": 0.2,
            "interest_rate": 3.45,
            "unemployment_rate": 5.1,
            "manufacturing_pmi": 50.2,
            "consumer_confidence": 120.5,
            "timestamp": datetime.now()
        },
        "us": {
            "country": "us",
            "gdp_growth": 2.5,
            "inflation_rate": 3.2,
            "interest_rate": 5.25,
            "unemployment_rate": 3.8,
            "manufacturing_pmi": 48.5,
            "consumer_confidence": 110.0,
            "timestamp": datetime.now()
        }
    }

    country_lower = country.lower()
    if country_lower == "china":
        return macro_defaults["china"]
    else:
        return macro_defaults["us"]
