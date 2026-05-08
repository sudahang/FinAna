"""
Enhanced Stock Data Fetcher - 使用多种数据源

数据源:
- A 股: 新浪财经 HTTP (快速，单只股票)
- 港股: 新浪财经 HTTP (快速，单只股票)
- 美股: yfinance (Yahoo Finance) + Finnhub + Alpha Vantage (备用)

优势:
- 实时行情使用 HTTP 直接请求，避免全市场数据加载
- 历史数据使用 AKShare (已经很快)
- 美股使用 yfinance + Finnhub + Alpha Vantage 三数据源
- 更好的错误处理
- 自动重试机制
"""

import logging
import requests
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
from config import get_data_source_config

logger = logging.getLogger(__name__)


class EnhancedStockDataFetcher:
    """使用多种数据源的股票数据获取器"""

    def __init__(self):
        """初始化数据获取器"""
        self._akshare = None
        self._yfinance = None
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://finance.sina.com.cn/"
        })
        self._alpha_vantage_api_key = ""
        self._alpha_vantage_base_url = ""
        self._finnhub_api_key = ""
        self._finnhub_base_url = ""
        self._init_libraries()
        self._init_data_sources()

    def _init_libraries(self):
        """延迟导入库，避免未安装时的错误"""
        try:
            import akshare as ak
            self._akshare = ak
            logger.info("AKShare 加载成功")
        except ImportError:
            logger.warning("AKShare 未安装，请运行: pip install akshare")

        try:
            import yfinance as yf
            self._yfinance = yf
            logger.info("yfinance 加载成功")
        except ImportError:
            logger.warning("yfinance 未安装，请运行: pip install yfinance")

    def _init_data_sources(self):
        """初始化所有备用数据源"""
        config = get_data_source_config()
        
        # Alpha Vantage
        self._alpha_vantage_api_key = config.alpha_vantage_api_key
        self._alpha_vantage_base_url = config.alpha_vantage_base_url
        if self._alpha_vantage_api_key:
            logger.info("Alpha Vantage API Key 已配置")
        else:
            logger.warning("Alpha Vantage API Key 未配置")

        # Finnhub
        self._finnhub_api_key = config.finnhub_api_key
        self._finnhub_base_url = config.finnhub_base_url
        if self._finnhub_api_key:
            logger.info("Finnhub API Key 已配置 (60次/分钟)")
        else:
            logger.warning("Finnhub API Key 未配置")

    def _normalize_symbol(self, symbol: str) -> tuple[str, str]:
        """
        标准化股票代码

        Returns:
            (normalized_symbol, market_type) 元组
            market_type: 'a_share', 'hk', 'us'
        """
        symbol = symbol.strip().upper()

        if not symbol:
            return "", "unknown"

        # A 股：sh600519 或 sz000001
        if symbol.startswith("SH"):
            return symbol[2:], "a_share"
        if symbol.startswith("SZ"):
            return symbol[2:], "a_share"

        # 港股：HK00700
        if symbol.startswith("HK"):
            return symbol, "hk"

        # 纯数字：判断是 A 股还是港股
        if symbol.isdigit():
            if len(symbol) == 6:
                # A 股代码
                return symbol, "a_share"
            elif len(symbol) == 5:
                # 港股代码
                return f"HK{symbol.zfill(5)}", "hk"

        # 字母：美股代码
        if symbol.isalpha() and len(symbol) <= 5:
            return symbol, "us"

        # 默认当作美股
        return symbol, "us"

    def get_quote(self, symbol: str) -> Optional[dict]:
        """
        获取实时行情

        Args:
            symbol: 股票代码

        Returns:
            行情数据字典
        """
        normalized, market = self._normalize_symbol(symbol)

        if not normalized:
            logger.warning("无效的股票代码: %s", symbol)
            return None

        try:
            if market == "a_share":
                return self._get_a_share_quote(normalized)
            elif market == "hk":
                return self._get_hk_quote(normalized)
            elif market == "us":
                return self._get_us_quote(normalized)
            else:
                logger.warning("未知市场类型: %s", symbol)
                return None
        except Exception as e:
            logger.error("获取行情失败 %s: %s", symbol, e)
            return None

    def _get_a_share_quote(self, symbol: str) -> Optional[dict]:
        """获取 A 股行情 (使用新浪财经 HTTP，快速)"""
        try:
            # 新浪财经接口：http://hq.sinajs.cn/list=sh600519
            if symbol.startswith(('6', '9')):
                sina_symbol = f"sh{symbol}"
            else:
                sina_symbol = f"sz{symbol}"

            response = self._session.get(
                f"http://hq.sinajs.cn/list={sina_symbol}",
                timeout=5
            )

            if response.status_code == 200:
                text = response.text.strip()
                if "=" in text:
                    data_str = text.split('="')[1].strip('";')
                    fields = data_str.split(",")

                    if len(fields) >= 32:
                        # A 股格式：0=名称，1=开盘，2=昨收，3=当前价，4=最高，5=最低...
                        name = fields[0]
                        current_price = float(fields[3]) if fields[3] else 0
                        prev_close = float(fields[2]) if fields[2] else 0
                        open_price = float(fields[1]) if fields[1] else 0
                        high = float(fields[4]) if fields[4] else 0
                        low = float(fields[5]) if fields[5] else 0
                        volume = float(fields[8]) if fields[8] else 0
                        amount = float(fields[9]) if fields[9] else 0

                        return {
                            "symbol": symbol,
                            "name": name,
                            "current_price": current_price,
                            "open": open_price,
                            "high": high,
                            "low": low,
                            "prev_close": prev_close,
                            "change": current_price - prev_close,
                            "change_pct": ((current_price - prev_close) / prev_close * 100) if prev_close else 0,
                            "volume": volume,
                            "amount": amount,
                            "market_cap": 0.0,  # 新浪不提供
                            "pe_ratio": 0.0,
                            "pb_ratio": 0.0,
                            "turnover_rate": 0.0,
                            "market": "sh" if symbol.startswith(('6', '9')) else "sz",
                            "timestamp": datetime.now()
                        }

            # 如果新浪失败，尝试腾讯
            return self._get_tencent_quote(symbol)

        except Exception as e:
            logger.error("获取 A 股行情失败 %s: %s", symbol, e)
            # 尝试腾讯作为 fallback
            return self._get_tencent_quote(symbol)

        return None

    def _get_tencent_quote(self, symbol: str) -> Optional[dict]:
        """获取 A 股行情 (使用腾讯财经 HTTP，备用)"""
        try:
            if symbol.startswith(('6', '9')):
                tencent_symbol = f"sh{symbol}"
            else:
                tencent_symbol = f"sz{symbol}"

            response = self._session.get(
                f"https://qt.gtimg.cn/q={tencent_symbol}",
                timeout=5
            )

            if response.status_code == 200:
                text = response.text.strip()
                if "=" in text:
                    data_str = text.split('="')[1].strip('";')
                    fields = data_str.split("~")

                    if len(fields) >= 45:
                        # 腾讯格式：1=名称，3=当前价，4=昨收，5=开盘，6=成交量...
                        name = fields[1]
                        current_price = float(fields[3]) if fields[3] else 0
                        prev_close = float(fields[4]) if fields[4] else 0

                        return {
                            "symbol": symbol,
                            "name": name,
                            "current_price": current_price,
                            "open": float(fields[5]) if fields[5] else 0,
                            "high": float(fields[33]) if len(fields) > 33 and fields[33] else 0,
                            "low": float(fields[34]) if len(fields) > 34 and fields[34] else 0,
                            "prev_close": prev_close,
                            "change": current_price - prev_close,
                            "change_pct": float(fields[32]) if len(fields) > 32 and fields[32] else 0,
                            "volume": float(fields[6]) if fields[6] else 0,
                            "amount": float(fields[37]) if len(fields) > 37 and fields[37] else 0,
                            "market_cap": float(fields[45]) if len(fields) > 45 and fields[45] else 0,
                            "pe_ratio": float(fields[39]) if len(fields) > 39 and fields[39] else 0,
                            "pb_ratio": 0.0,
                            "turnover_rate": 0.0,
                            "market": "sh" if symbol.startswith(('6', '9')) else "sz",
                            "timestamp": datetime.now()
                        }

        except Exception as e:
            logger.error("腾讯财经获取行情失败 %s: %s", symbol, e)

        return None

    def _get_hk_quote(self, symbol: str) -> Optional[dict]:
        """获取港股行情 (使用新浪财经 HTTP，快速)"""
        try:
            # 提取纯数字代码 (去掉 HK 前缀)
            hk_code = symbol[2:] if symbol.startswith("HK") else symbol

            # 新浪财经港股接口：http://hq.sinajs.cn/list=hk00700
            sina_symbol = f"hk{hk_code.lower().zfill(5)}"

            response = self._session.get(
                f"http://hq.sinajs.cn/list={sina_symbol}",
                timeout=5
            )

            if response.status_code == 200:
                text = response.text.strip()
                if "=" in text:
                    data_str = text.split('="')[1].strip('";')
                    fields = data_str.split(",")

                    if len(fields) >= 19:
                        # 港股格式：0=英文名，1=中文名，2=昨收，3=开盘，4=当前价，5=最高，6=最低...
                        name = fields[1] if fields[1] else fields[0]
                        prev_close = float(fields[2]) if fields[2] else 0
                        current_price = float(fields[4]) if fields[4] else 0
                        open_price = float(fields[3]) if fields[3] else 0
                        high = float(fields[5]) if fields[5] else 0
                        low = float(fields[6]) if fields[6] else 0
                        change = float(fields[7]) if fields[7] else 0
                        change_pct = float(fields[8]) if fields[8] else 0
                        volume = float(fields[11]) if fields[11] else 0
                        amount = float(fields[12]) if fields[12] else 0

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
                            "market_cap": 0.0,
                            "pe_ratio": 0.0,
                            "pb_ratio": 0.0,
                            "turnover_rate": 0.0,
                            "market": "hk",
                            "timestamp": datetime.now()
                        }

            # 如果新浪失败，尝试腾讯
            return self._get_tencent_hk_quote(symbol)

        except Exception as e:
            logger.error("获取港股行情失败 %s: %s", symbol, e)
            return self._get_tencent_hk_quote(symbol)

        return None

    def _get_tencent_hk_quote(self, symbol: str) -> Optional[dict]:
        """获取港股行情 (使用腾讯财经 HTTP，备用)"""
        try:
            hk_code = symbol[2:] if symbol.startswith("HK") else symbol
            tencent_symbol = f"HK{hk_code.zfill(5)}"

            response = self._session.get(
                f"https://qt.gtimg.cn/q={tencent_symbol}",
                timeout=5
            )

            if response.status_code == 200:
                text = response.text.strip()
                if "=" in text:
                    data_str = text.split('="')[1].strip('";')
                    fields = data_str.split("~")

                    if len(fields) >= 45:
                        name = fields[1]
                        current_price = float(fields[3]) if fields[3] else 0
                        prev_close = float(fields[4]) if fields[4] else 0

                        return {
                            "symbol": symbol,
                            "name": name,
                            "current_price": current_price,
                            "open": float(fields[5]) if fields[5] else 0,
                            "high": float(fields[33]) if len(fields) > 33 and fields[33] else 0,
                            "low": float(fields[34]) if len(fields) > 34 and fields[34] else 0,
                            "prev_close": prev_close,
                            "change": current_price - prev_close,
                            "change_pct": float(fields[32]) if len(fields) > 32 and fields[32] else 0,
                            "volume": float(fields[6]) if fields[6] else 0,
                            "amount": float(fields[37]) if len(fields) > 37 and fields[37] else 0,
                            "market_cap": float(fields[45]) if len(fields) > 45 and fields[45] else 0,
                            "pe_ratio": float(fields[39]) if len(fields) > 39 and fields[39] else 0,
                            "pb_ratio": 0.0,
                            "turnover_rate": 0.0,
                            "market": "hk",
                            "timestamp": datetime.now()
                        }

        except Exception as e:
            logger.error("腾讯财经获取港股行情失败 %s: %s", symbol, e)

        return None

    def _get_us_quote(self, symbol: str) -> Optional[dict]:
        """获取美股行情 (使用 yfinance + Finnhub + Alpha Vantage 备用)"""
        # 先尝试 yfinance
        try:
            if self._yfinance:
                quote = self._get_us_quote_yfinance(symbol)
                if quote:
                    return quote
        except Exception as e:
            logger.warning("yfinance 获取美股行情失败 %s: %s", symbol, e)

        # yfinance 失败后尝试 Finnhub (60次/分钟，更稳定)
        try:
            if self._finnhub_api_key:
                quote = self._get_us_quote_finnhub(symbol)
                if quote:
                    return quote
        except Exception as e:
            logger.warning("Finnhub 获取美股行情失败 %s: %s", symbol, e)

        # Finnhub 失败后尝试 Alpha Vantage
        return self._get_us_quote_alpha_vantage(symbol)

    def _get_us_quote_yfinance(self, symbol: str) -> Optional[dict]:
        """获取美股行情 (使用 yfinance)"""
        if not self._yfinance:
            return None

        # 使用 yfinance 获取美股数据
        ticker = self._yfinance.Ticker(symbol)

        # 获取实时行情
        info = ticker.info

        if not info:
            logger.warning("未找到美股数据: %s", symbol)
            return None

        # 获取当前价格 (优先使用 regularMarketPrice)
        current_price = info.get('regularMarketPrice', 0)
        prev_close = info.get('regularMarketPreviousClose', 0)
        change = current_price - prev_close if prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0

        return {
            "symbol": symbol,
            "name": info.get('shortName', info.get('longName', '')),
            "current_price": float(current_price),
            "open": float(info.get('regularMarketOpen', 0)),
            "high": float(info.get('regularMarketDayHigh', 0)),
            "low": float(info.get('regularMarketDayLow', 0)),
            "prev_close": float(prev_close),
            "change": float(change),
            "change_pct": float(change_pct),
            "volume": float(info.get('regularMarketVolume', 0)),
            "amount": 0.0,  # yfinance 不提供成交额
            "market_cap": float(info.get('marketCap', 0)),
            "pe_ratio": float(info.get('trailingPE', 0)),
            "pb_ratio": float(info.get('priceToBook', 0)),
            "turnover_rate": 0.0,  # yfinance 不提供换手率
            "market": "us",
            "timestamp": datetime.now()
        }

    def _get_us_quote_finnhub(self, symbol: str) -> Optional[dict]:
        """获取美股行情 (使用 Finnhub)"""
        if not self._finnhub_api_key:
            logger.warning("Finnhub API Key 未配置")
            return None

        try:
            # Finnhub Quote API: https://finnhub.io/api/v1/quote?symbol=AAPL&token=YOUR_API_KEY
            params = {
                "symbol": symbol,
                "token": self._finnhub_api_key
            }

            response = self._session.get(
                f"{self._finnhub_base_url}/quote",
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                # 检查限流
                if response.status_code == 429:
                    logger.warning("Finnhub 限流: 超过 60 次/分钟")
                    return None

                # Finnhub 返回字段：
                # c: current price, h: high, l: low, o: open, pc: previous close, t: timestamp
                current_price = data.get('c', 0)
                prev_close = data.get('pc', 0)
                
                if current_price == 0:
                    logger.warning("Finnhub 返回价格为 0: %s", symbol)
                    return None

                change = current_price - prev_close if prev_close else 0
                change_pct = (change / prev_close * 100) if prev_close else 0

                return {
                    "symbol": symbol,
                    "name": symbol,  # Finnhub quote 不提供公司名称
                    "current_price": float(current_price),
                    "open": float(data.get('o', 0)),
                    "high": float(data.get('h', 0)),
                    "low": float(data.get('l', 0)),
                    "prev_close": float(prev_close),
                    "change": float(change),
                    "change_pct": float(change_pct),
                    "volume": 0.0,  # Finnhub quote 不提供成交量
                    "amount": 0.0,
                    "market_cap": 0.0,
                    "pe_ratio": 0.0,
                    "pb_ratio": 0.0,
                    "turnover_rate": 0.0,
                    "market": "us",
                    "timestamp": datetime.now()
                }

        except Exception as e:
            logger.error("Finnhub 获取美股行情失败 %s: %s", symbol, e)

        return None

    def _get_us_quote_alpha_vantage(self, symbol: str) -> Optional[dict]:
        """获取美股行情 (使用 Alpha Vantage 备用)"""
        if not self._alpha_vantage_api_key:
            logger.warning("Alpha Vantage API Key 未配置")
            return None

        try:
            # Alpha Vantage GLOBAL_QUOTE 接口
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self._alpha_vantage_api_key
            }

            response = self._session.get(
                self._alpha_vantage_base_url,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                # 检查是否有限流信息
                if "Note" in data:
                    logger.warning("Alpha Vantage 限流: %s", data["Note"])
                    return None

                # 检查是否有错误信息
                if "Error Message" in data:
                    logger.error("Alpha Vantage 错误: %s", data["Error Message"])
                    return None

                # 解析行情数据
                quote = data.get("Global Quote", {})

                if not quote:
                    logger.warning("未找到 Alpha Vantage 数据: %s", symbol)
                    return None

                # Alpha Vantage 字段：
                # 01: symbol, 02: open, 03: high, 04: low, 05: price, 06: volume
                # 07: latest trading day, 08: previous close, 09: change, 10: change percent

                current_price = float(quote.get("05", 0))
                prev_close = float(quote.get("08", 0))
                change_str = quote.get("09", "0")
                change_pct_str = quote.get("10", "0%")

                # 解析涨跌幅 (去掉 % 符号)
                change_pct = float(change_pct_str.replace("%", "")) if change_pct_str else 0
                change = float(change_str) if change_str else 0

                return {
                    "symbol": symbol,
                    "name": symbol,  # Alpha Vantage 不提供公司名称
                    "current_price": current_price,
                    "open": float(quote.get("02", 0)),
                    "high": float(quote.get("03", 0)),
                    "low": float(quote.get("04", 0)),
                    "prev_close": prev_close,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": float(quote.get("06", 0)),
                    "amount": 0.0,
                    "market_cap": 0.0,
                    "pe_ratio": 0.0,
                    "pb_ratio": 0.0,
                    "turnover_rate": 0.0,
                    "market": "us",
                    "timestamp": datetime.now()
                }

        except Exception as e:
            logger.error("Alpha Vantage 获取美股行情失败 %s: %s", symbol, e)

        return None

    def get_company_info(self, symbol: str) -> Optional[dict]:
        """
        获取公司基本信息

        Args:
            symbol: 股票代码

        Returns:
            公司信息字典
        """
        normalized, market = self._normalize_symbol(symbol)

        if not normalized:
            return None

        try:
            if market == "a_share":
                return self._get_a_share_company_info(normalized)
            elif market == "hk":
                return self._get_hk_company_info(normalized)
            elif market == "us":
                return self._get_us_company_info(normalized)
            else:
                return None
        except Exception as e:
            logger.error("获取公司信息失败 %s: %s", symbol, e)
            return None

    def _get_a_share_company_info(self, symbol: str) -> Optional[dict]:
        """获取 A 股公司信息"""
        if not self._akshare:
            return None

        try:
            # 使用 AKShare 获取公司信息
            # 注意：AKShare 的公司信息接口可能需要特定的股票代码格式
            df = self._akshare.stock_individual_info_em(symbol=symbol)

            if df is None or df.empty:
                return None

            # 转换为字典格式
            info_dict = {}
            for _, row in df.iterrows():
                key = row.get('item', '')
                value = row.get('value', '')
                info_dict[key] = value

            return {
                "symbol": symbol,
                "name": info_dict.get('股票简称', ''),
                "industry": info_dict.get('行业', ''),
                "area": info_dict.get('地域', ''),
                "listing_date": info_dict.get('上市时间', ''),
                "pe_ratio": float(info_dict.get('市盈率', 0)),
                "pb_ratio": float(info_dict.get('市净率', 0)),
                "total_revenue": 0.0,  # AKShare 可能不直接提供
                "net_profit": 0.0,
                "gross_margin": 0.0,
                "roe": 0.0,
                "market_cap": 0.0,
                "timestamp": datetime.now()
            }

        except Exception as e:
            logger.error("获取 A 股公司信息失败 %s: %s", symbol, e)
            return None

    def _get_hk_company_info(self, symbol: str) -> Optional[dict]:
        """获取港股公司信息"""
        # 港股公司信息获取较为复杂，暂时返回基础信息
        return {
            "symbol": symbol,
            "name": "",
            "industry": "",
            "area": "HK",
            "listing_date": "",
            "pe_ratio": 0.0,
            "pb_ratio": 0.0,
            "total_revenue": 0.0,
            "net_profit": 0.0,
            "gross_margin": 0.0,
            "roe": 0.0,
            "market_cap": 0.0,
            "timestamp": datetime.now()
        }

    def _get_us_company_info(self, symbol: str) -> Optional[dict]:
        """获取美股公司信息"""
        if not self._yfinance:
            return None

        try:
            ticker = self._yfinance.Ticker(symbol)
            info = ticker.info

            if not info:
                return None

            return {
                "symbol": symbol,
                "name": info.get('longName', info.get('shortName', '')),
                "industry": info.get('industry', ''),
                "area": info.get('country', ''),
                "listing_date": "",
                "pe_ratio": float(info.get('trailingPE', 0)),
                "pb_ratio": float(info.get('priceToBook', 0)),
                "total_revenue": float(info.get('totalRevenue', 0)),
                "net_profit": float(info.get('netIncomeToCommon', 0)),
                "gross_margin": float(info.get('grossMargins', 0)) * 100,
                "roe": float(info.get('returnOnEquity', 0)) * 100,
                "market_cap": float(info.get('marketCap', 0)),
                "timestamp": datetime.now()
            }

        except Exception as e:
            logger.error("获取美股公司信息失败 %s: %s", symbol, e)
            return None

    def get_stock_news(self, symbol: str, limit: int = 10) -> list:
        """
        获取股票相关新闻

        Args:
            symbol: 股票代码
            limit: 返回数量

        Returns:
            新闻列表
        """
        normalized, market = self._normalize_symbol(symbol)
        news_list = []

        try:
            # 转换为东方财富 secid 格式
            if normalized.startswith(("sh", "sz", "bj")):
                if normalized.startswith("sh"):
                    secid = f"1.{normalized[2:]}"
                elif normalized.startswith("sz"):
                    secid = f"0.{normalized[2:]}"
                else:
                    secid = f"2.{normalized[2:]}"
            elif normalized.startswith("HK"):
                hk_code = normalized[2:].lstrip('0') or '0'
                secid = f"116.{hk_code}"
            elif normalized.isalpha():
                secid = f"162.{normalized}"
            else:
                return news_list

            params = {
                "secid": secid,
                "ps": limit,
                "p": 1
            }

            # 东方财富新闻 API
            response = self._session.get(
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

    def get_macro_data(self, country: str = "china") -> Optional[dict]:
        """
        获取宏观经济数据

        Args:
            country: 国家名称 ('china' 或 'us')

        Returns:
            宏观数据字典
        """
        macro_data = {
            "country": country,
            "timestamp": datetime.now(),
            "as_of": datetime.now(),
            "data_source": "AKShare macro data",
            "is_fallback": False,
        }

        try:
            if country.lower() == "china":
                if not self._akshare:
                    logger.warning("AKShare 未安装，使用默认宏观数据")
                    return self._get_china_macro_defaults()

                gdp_growth = None
                cpi_latest = None
                pmi_latest = None

                try:
                    gdp_df = self._akshare.macro_china_gdp()
                    if gdp_df is not None and not gdp_df.empty:
                        gdp_df = gdp_df.sort_index(ascending=False)
                        gdp_growth = float(gdp_df.iloc[0].get('国内生产总值同比增长', 0))
                except Exception as e:
                    logger.warning("AKShare GDP data fetch failed: %s", e)

                try:
                    cpi_df = self._akshare.macro_china_cpi()
                    if cpi_df is not None and not cpi_df.empty:
                        cpi_df = cpi_df.sort_index(ascending=False)
                        cpi_latest = float(cpi_df.iloc[0].get('CPI同比', 0))
                except Exception as e:
                    logger.warning("AKShare CPI data fetch failed: %s", e)

                try:
                    pmi_df = self._akshare.macro_china_pmi()
                    if pmi_df is not None and not pmi_df.empty:
                        pmi_df = pmi_df.sort_index(ascending=False)
                        pmi_latest = float(pmi_df.iloc[0].get('制造业PMI', 0))
                except Exception as e:
                    logger.warning("AKShare PMI data fetch failed: %s", e)

                defaults = self._get_china_macro_defaults()
                macro_data.update({
                    "gdp_growth": gdp_growth if gdp_growth else defaults.get('gdp_growth', 5.0),
                    "inflation_rate": cpi_latest if cpi_latest else defaults.get('inflation_rate', 0.2),
                    "interest_rate": defaults.get('interest_rate', 3.45),
                    "unemployment_rate": defaults.get('unemployment_rate', 5.1),
                    "pmi": pmi_latest if pmi_latest else defaults.get('pmi', 50.0),
                    "data_source": "AKShare macro data",
                    "is_fallback": False,
                })

            else:
                macro_data.update(self._get_us_macro_defaults())
                macro_data.update({
                    "data_source": "US macro defaults",
                    "is_fallback": True,
                })

        except Exception as e:
            logger.warning("Error fetching macro data, using fallback: %s", e)
            if country.lower() == "china":
                macro_data.update({
                    "gdp_growth": 5.0,
                    "inflation_rate": 0.2,
                    "interest_rate": 3.45,
                    "unemployment_rate": 5.1,
                    "pmi": 50.0,
                    "data_source": "China macro fallback",
                    "is_fallback": True,
                })
            else:
                macro_data.update({
                    "gdp_growth": 2.5,
                    "inflation_rate": 3.2,
                    "interest_rate": 5.25,
                    "unemployment_rate": 3.8,
                    "data_source": "US macro fallback",
                    "is_fallback": True,
                })

        return macro_data

    def _get_china_macro_defaults(self) -> dict:
        """获取中国宏观默认数据"""
        return {
            "gdp_growth": 5.0,
            "inflation_rate": 0.2,
            "interest_rate": 3.45,
            "unemployment_rate": 5.1,
            "pmi": 50.0,
        }

    def _get_us_macro_defaults(self) -> dict:
        """获取美国宏观默认数据"""
        return {
            "gdp_growth": 2.5,
            "inflation_rate": 3.2,
            "interest_rate": 5.25,
            "unemployment_rate": 3.8,
        }

    def get_industry_data(self, sector: str) -> Optional[dict]:
        """
        获取行业/板块分析数据

        Args:
            sector: 行业名称

        Returns:
            行业数据字典
        """
        try:
            if not self._akshare:
                logger.warning("AKShare 未安装，使用默认行业数据")
                return self._get_industry_defaults(sector)

            sector_lower = sector.lower()

            try:
                board_df = self._akshare.stock_board_industry_name_em()
                if board_df is not None and not board_df.empty:
                    matching_rows = board_df[board_df['板块名称'].str.contains(sector, case=False, na=False)]
                    if not matching_rows.empty:
                        row = matching_rows.iloc[0]
                        change_pct = float(row.get('涨跌幅', 0))
                        return {
                            "sector": sector,
                            "sector_growth": change_pct,
                            "avg_pe_ratio": float(row.get('市盈率', 0)) if row.get('市盈率') else 0,
                            "market_sentiment": "bullish" if change_pct > 0 else "bearish",
                            "turnover_rate": float(row.get('换手率', 0)) if row.get('换手率') else 0,
                            "as_of": datetime.now(),
                            "data_source": "AKShare industry board data",
                            "is_fallback": False,
                        }
            except Exception as e:
                logger.warning("AKShare industry board data fetch failed: %s", e)

            return self._get_industry_defaults(sector)

        except Exception as e:
            logger.warning("Error fetching industry data: %s", e)
            return self._get_industry_defaults(sector, is_error=True)

    def _get_industry_defaults(self, sector: str, is_error: bool = False) -> dict:
        """获取行业默认数据"""
        industry_defaults = {
            "technology": {
                "sector_growth": 12.5,
                "avg_pe_ratio": 30.0,
                "market_sentiment": "bullish",
                "turnover_rate": 2.5,
            },
            "finance": {
                "sector_growth": 5.0,
                "avg_pe_ratio": 8.0,
                "market_sentiment": "neutral",
                "turnover_rate": 1.0,
            },
            "healthcare": {
                "sector_growth": 10.0,
                "avg_pe_ratio": 25.0,
                "market_sentiment": "bullish",
                "turnover_rate": 2.0,
            },
            "consumer": {
                "sector_growth": 8.0,
                "avg_pe_ratio": 20.0,
                "market_sentiment": "neutral",
                "turnover_rate": 1.5,
            },
        }

        sector_lower = sector.lower()
        for key, value in industry_defaults.items():
            if key in sector_lower:
                return {
                    "sector": sector,
                    **value,
                    "as_of": datetime.now(),
                    "data_source": "Industry defaults",
                    "is_fallback": True,
                }

        return {
            "sector": sector,
            **industry_defaults.get("technology", {}),
            "as_of": datetime.now(),
            "data_source": "Industry defaults fallback",
            "is_fallback": True,
        }

    def get_history(self, symbol: str, start_date: str = "",
                    end_date: str = "", period: str = "d") -> Optional[list[dict]]:
        """
        获取历史 K 线数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD 或 YYYYMMDD)
            end_date: 结束日期
            period: K 线周期 (d=日, w=周, m=月)

        Returns:
            K 线数据列表
        """
        normalized, market = self._normalize_symbol(symbol)

        if not normalized:
            return None

        try:
            if market == "a_share":
                return self._get_a_share_history(normalized, start_date, end_date, period)
            elif market == "hk":
                return self._get_hk_history(normalized, start_date, end_date, period)
            elif market == "us":
                return self._get_us_history(normalized, start_date, end_date, period)
            else:
                return None
        except Exception as e:
            logger.error("获取历史数据失败 %s: %s", symbol, e)
            return None

    def _get_a_share_history(self, symbol: str, start_date: str,
                             end_date: str, period: str) -> Optional[list[dict]]:
        """获取 A 股历史 K 线"""
        if not self._akshare:
            return None

        try:
            # 设置默认日期
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            # 转换日期格式
            start_date = start_date.replace('-', '')
            end_date = end_date.replace('-', '')

            # 使用 AKShare 获取历史数据
            df = self._akshare.stock_zh_a_hist(
                symbol=symbol,
                period="daily" if period == "d" else "weekly" if period == "w" else "monthly",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )

            if df is None or df.empty:
                return None

            # 转换为列表格式
            result = []
            for _, row in df.iterrows():
                result.append({
                    "date": str(row.get('日期', '')),
                    "open": float(row.get('开盘', 0)),
                    "high": float(row.get('最高', 0)),
                    "low": float(row.get('最低', 0)),
                    "close": float(row.get('收盘', 0)),
                    "volume": float(row.get('成交量', 0)),
                    "amount": float(row.get('成交额', 0))
                })

            return result

        except Exception as e:
            logger.error("获取 A 股历史数据失败 %s: %s", symbol, e)
            return None

    def _get_hk_history(self, symbol: str, start_date: str,
                        end_date: str, period: str) -> Optional[list[dict]]:
        """获取港股历史 K 线"""
        if not self._akshare:
            return None

        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')

            start_date = start_date.replace('-', '')
            end_date = end_date.replace('-', '')

            # 提取纯数字代码
            hk_code = symbol[2:] if symbol.startswith("HK") else symbol

            df = self._akshare.stock_hk_hist(
                symbol=hk_code,
                period="daily" if period == "d" else "weekly" if period == "w" else "monthly",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )

            if df is None or df.empty:
                return None

            result = []
            for _, row in df.iterrows():
                result.append({
                    "date": str(row.get('日期', '')),
                    "open": float(row.get('开盘', 0)),
                    "high": float(row.get('最高', 0)),
                    "low": float(row.get('最低', 0)),
                    "close": float(row.get('收盘', 0)),
                    "volume": float(row.get('成交量', 0)),
                    "amount": float(row.get('成交额', 0))
                })

            return result

        except Exception as e:
            logger.error("获取港股历史数据失败 %s: %s", symbol, e)
            return None

    def _get_us_history(self, symbol: str, start_date: str,
                        end_date: str, period: str) -> Optional[list[dict]]:
        """获取美股历史 K 线"""
        if not self._yfinance:
            return None

        try:
            # 设置默认日期
            if not start_date:
                start = datetime.now() - timedelta(days=365)
            else:
                start = datetime.strptime(start_date.replace('-', ''), '%Y%m%d')

            if not end_date:
                end = datetime.now()
            else:
                end = datetime.strptime(end_date.replace('-', ''), '%Y%m%d')

            # 转换周期
            interval = "1d" if period == "d" else "1wk" if period == "w" else "1mo"

            # 使用 yfinance 获取历史数据
            ticker = self._yfinance.Ticker(symbol)
            df = ticker.history(start=start, end=end, interval=interval)

            if df is None or df.empty:
                return None

            # 转换为列表格式
            result = []
            for date, row in df.iterrows():
                result.append({
                    "date": date.strftime('%Y-%m-%d'),
                    "open": float(row.get('Open', 0)),
                    "high": float(row.get('High', 0)),
                    "low": float(row.get('Low', 0)),
                    "close": float(row.get('Close', 0)),
                    "volume": float(row.get('Volume', 0)),
                    "amount": 0.0  # yfinance 不提供成交额
                })

            return result

        except Exception as e:
            logger.error("获取美股历史数据失败 %s: %s", symbol, e)
            return None


# 单例模式
_fetcher: Optional[EnhancedStockDataFetcher] = None


def get_fetcher() -> EnhancedStockDataFetcher:
    """获取单例数据获取器"""
    global _fetcher
    if _fetcher is None:
        _fetcher = EnhancedStockDataFetcher()
    return _fetcher


def get_stock_quote(symbol: str) -> Optional[dict]:
    """获取股票行情 (便捷函数)"""
    return get_fetcher().get_quote(symbol)


def get_company_info(symbol: str) -> Optional[dict]:
    """获取公司信息 (便捷函数)"""
    return get_fetcher().get_company_info(symbol)


def get_history(symbol: str, start_date: str = "",
                  end_date: str = "", period: str = "d") -> Optional[list[dict]]:
    """获取历史 K 线 (便捷函数)"""
    return get_fetcher().get_history(symbol, start_date, end_date, period)


def get_stock_news(symbol: str, limit: int = 10) -> list:
    """获取股票新闻 (便捷函数)"""
    return get_fetcher().get_stock_news(symbol, limit)


def get_macro_data(country: str = "china") -> Optional[dict]:
    """获取宏观经济数据 (便捷函数)"""
    return get_fetcher().get_macro_data(country)


def get_industry_data(sector: str) -> Optional[dict]:
    """获取行业数据 (便捷函数)"""
    return get_fetcher().get_industry_data(sector)
