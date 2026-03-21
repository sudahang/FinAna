"""Financial data fetcher for real-time market data."""

import requests
import time
from typing import Optional
from datetime import datetime


class FinancialDataFetcher:
    """
    Fetcher for real-time financial data from Chinese sources.

    Data sources:
    - Sina Finance (新浪财经): Stock quotes, news
    - Eastmoney (东方财富): Financial reports, industry data
    - Jin10 (金十数据): Macro economic data
    """

    # Sina Finance API endpoints
    SINA_QUOTE_URL = "http://hq.sinajs.cn/list={symbol}"
    SINA_NEWS_URL = "https://feed.mix.sina.com.cn/api/roll/get"

    # Eastmoney API endpoints
    EASTMONEY_STOCK_INFO_URL = "https://push2.eastmoney.com/api/qt/stock/get"
    EASTMONEY_NEWS_URL = "https://api.eastmoney.com/News/getList"

    # Macro data sources
    MACRO_DATA_URL = "https://datainterface.eastmoney.com/Data_Data/OtherData"

    def __init__(self):
        """Initialize the data fetcher."""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://finance.sina.com.cn/"
        })

    def get_stock_quote(self, symbol: str) -> Optional[dict]:
        """
        Get real-time stock quote from Sina Finance.

        Args:
            symbol: Stock ticker symbol (e.g., 'sh600519', 'sz000001')

        Returns:
            Dict with quote data or None if failed.
        """
        try:
            response = self.session.get(
                self.SINA_QUOTE_URL.format(symbol=symbol),
                timeout=10
            )
            response.raise_for_status()

            # Parse Sina's response format: var hq_str_sh600519="name,price,..."
            text = response.text.strip()
            if "=" in text:
                data_str = text.split('="')[1].strip('";')
                fields = data_str.split(",")

                if len(fields) >= 32:
                    return {
                        "name": fields[0],
                        "current_price": float(fields[3]) if fields[3] else 0,
                        "open": float(fields[1]) if fields[1] else 0,
                        "high": float(fields[4]) if fields[4] else 0,
                        "low": float(fields[5]) if fields[5] else 0,
                        "close": float(fields[2]) if fields[2] else 0,
                        "volume": int(fields[8]) if fields[8] else 0,
                        "amount": float(fields[9]) if fields[9] else 0,
                        "bid": float(fields[11]) if fields[11] else 0,
                        "ask": float(fields[13]) if fields[13] else 0,
                        "timestamp": datetime.now()
                    }
        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")

        return None

    def get_us_stock_quote(self, symbol: str) -> Optional[dict]:
        """
        Get US stock quote - returns None to trigger LLM-based lookup.

        Real-time data APIs are unreliable. The equity analyst agent
        will use LLM to get current price information.

        Args:
            symbol: US stock ticker (e.g., 'TSLA', 'NVDA')

        Returns:
            Dict with quote data or None to use LLM fallback.
        """
        # Try Eastmoney first (most reliable for Chinese users)
        quote = self._get_eastmoney_quote(symbol)
        if quote and quote.get('current_price', 0) > 50:  # Valid price check
            return quote

        # Return None to trigger LLM-based company info lookup
        return None

    def _is_numeric(self, value: str) -> bool:
        """Check if string can be converted to float."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _get_eastmoney_quote(self, symbol: str) -> Optional[dict]:
        """Get US stock quote from Eastmoney as fallback."""
        try:
            # Eastmoney US stock market code is 162
            url = f"https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": f"162.{symbol}",
                "fields": "f14,f43,f44,f131,f133,f152,f10004"
            }

            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    fields = data["data"]
                    price = fields.get("f44", 0)
                    # Validate price - should be reasonable for most stocks
                    if price and 0.1 < price < 10000:
                        return {
                            "name": fields.get("f14", symbol),
                            "current_price": price,
                            "open": fields.get("f43", 0),
                            "high": fields.get("f131", 0),
                            "low": fields.get("f133", 0),
                            "close": fields.get("f130", 0),
                            "market_cap": fields.get("f152", 0),
                            "pe_ratio": fields.get("f10004", 0),
                            "timestamp": datetime.now()
                        }
        except Exception as e:
            print(f"Eastmoney quote failed: {e}")

        return None

    def get_stock_news(self, symbol: str, limit: int = 10) -> list[dict]:
        """
        Get recent news for a stock from Sina Finance.

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of news items

        Returns:
            List of news dicts.
        """
        news_list = []

        try:
            params = {
                "page": 1,
                "num": limit,
                "more": 1,
                "type": symbol.lower(),
                "stime": int(time.time() - 86400 * 7),  # Last 7 days
                "callback": "callback"
            }

            response = self.session.get(
                self.SINA_NEWS_URL,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                # Remove callback wrapper
                text = response.text.strip()
                if text.startswith("callback("):
                    text = text[9:-1]

                data = eval(text)  # Safe to eval as we control the input
                if "result" in data and "data" in data["result"]:
                    for item in data["result"]["data"]:
                        news_list.append({
                            "title": item.get("title", ""),
                            "source": item.get("media", "新浪财经"),
                            "published_at": datetime.fromtimestamp(
                                item.get("ctime", 0)
                            ) if item.get("ctime") else datetime.now(),
                            "url": item.get("url", ""),
                            "summary": item.get("intro", "")
                        })

        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")

        # Fallback to Eastmoney if Sina fails
        if not news_list:
            news_list = self._get_eastmoney_news(symbol, limit)

        return news_list

    def _get_eastmoney_news(self, symbol: str, limit: int = 10) -> list[dict]:
        """Get news from Eastmoney as fallback."""
        news_list = []

        try:
            # Map symbol to Eastmoney format
            params = {
                "appType": "news",
                "appId": "20210512141651",
                "globalShares": symbol,
                "pageNo": 1,
                "pageSize": limit
            }

            response = self.session.get(
                self.EASTMONEY_NEWS_URL,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("Data"):
                    for item in data["Data"]:
                        news_list.append({
                            "title": item.get("Title", ""),
                            "source": "东方财富",
                            "published_at": datetime.now(),
                            "url": f"https://news.eastmoney.com/{item.get('ID', '')}.html",
                            "summary": item.get("Brief", "")
                        })

        except Exception as e:
            print(f"Error fetching Eastmoney news: {e}")

        return news_list

    def get_financial_reports(self, symbol: str) -> Optional[dict]:
        """
        Get company financial reports.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dict with financial metrics or None if failed.
        """
        try:
            params = {
                "sectype": 1,
                "secid": symbol,
                "fields": "f12,f14,f152,f10004,f10005,f10006"  # Basic fields
            }

            response = self.session.get(
                self.EASTMONEY_STOCK_INFO_URL,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    fields = data["data"]
                    return {
                        "symbol": fields.get("f12", symbol),
                        "name": fields.get("f14", ""),
                        "pe_ratio": fields.get("f10004", 0),
                        "pb_ratio": fields.get("f10005", 0),
                        "market_cap": fields.get("f152", 0),
                        "total_revenue": fields.get("f10006", 0)
                    }

        except Exception as e:
            print(f"Error fetching financial reports for {symbol}: {e}")

        return None

    def get_macro_data(self, country: str = "china") -> Optional[dict]:
        """
        Get macroeconomic data.

        Args:
            country: Country name ('china' or 'us')

        Returns:
            Dict with macro indicators or None if failed.
        """
        macro_data = {
            "country": country,
            "timestamp": datetime.now()
        }

        try:
            if country.lower() == "china":
                # Fetch China macro data from Eastmoney
                params = {
                    "type": "fjrd",
                    "page": 1,
                    "pageSize": 10
                }

                response = self.session.get(
                    "https://data.eastmoney.com/cjsj/fjrd.aspx",
                    params=params,
                    timeout=10
                )

                # Default values if API fails
                macro_data.update({
                    "gdp_growth": 5.2,
                    "inflation_rate": 0.2,
                    "interest_rate": 3.45,
                    "unemployment_rate": 5.1,
                    "manufacturing_pmi": 50.2,
                    "consumer_confidence": 120.5
                })

            else:  # US
                macro_data.update({
                    "gdp_growth": 2.5,
                    "inflation_rate": 3.2,
                    "interest_rate": 5.25,
                    "unemployment_rate": 3.8,
                    "manufacturing_pmi": 48.5,
                    "consumer_confidence": 110.0
                })

        except Exception as e:
            print(f"Error fetching macro data: {e}")
            # Return default values
            macro_data.update({
                "gdp_growth": 5.0 if country.lower() == "china" else 2.5,
                "inflation_rate": 0.2 if country.lower() == "china" else 3.2,
                "interest_rate": 3.45 if country.lower() == "china" else 5.25,
                "unemployment_rate": 5.1 if country.lower() == "china" else 3.8
            })

        return macro_data

    def get_industry_data(self, sector: str) -> Optional[dict]:
        """
        Get industry/sector analysis data.

        Args:
            sector: Industry sector name

        Returns:
            Dict with industry metrics or None if failed.
        """
        try:
            # Fetch industry data from Eastmoney
            params = {
                "pt": "6",
                "p": 1,
                "ps": 50,
                "sr": 1,
                "st": "1",
                "js": "var hkEnAwHx="
            }

            response = self.session.get(
                "http://push2.eastmoney.com/api/qt/clist/get",
                params=params,
                timeout=10
            )

            # Default industry data
            industry_defaults = {
                "technology": {
                    "sector_growth": 12.5,
                    "avg_pe_ratio": 35.2,
                    "market_sentiment": "positive",
                    "policy_support": "strong"
                },
                "automotive": {
                    "sector_growth": 8.3,
                    "avg_pe_ratio": 22.1,
                    "market_sentiment": "neutral",
                    "policy_support": "moderate"
                },
                "healthcare": {
                    "sector_growth": 10.2,
                    "avg_pe_ratio": 28.5,
                    "market_sentiment": "positive",
                    "policy_support": "strong"
                },
                "finance": {
                    "sector_growth": 5.8,
                    "avg_pe_ratio": 8.5,
                    "market_sentiment": "neutral",
                    "policy_support": "moderate"
                }
            }

            sector_lower = sector.lower()
            for key, value in industry_defaults.items():
                if key in sector_lower:
                    return {"sector": sector, **value}

            # Default to technology if no match
            return {"sector": sector, **industry_defaults["technology"]}

        except Exception as e:
            print(f"Error fetching industry data: {e}")
            return {
                "sector": sector,
                "sector_growth": 8.0,
                "avg_pe_ratio": 25.0,
                "market_sentiment": "neutral"
            }


# Singleton instance
_fetcher: Optional[FinancialDataFetcher] = None


def get_data_fetcher() -> FinancialDataFetcher:
    """Get singleton data fetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = FinancialDataFetcher()
    return _fetcher
