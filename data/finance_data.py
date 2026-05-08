"""Financial data fetcher for real-time market data."""

import requests
import time
import json
import re
import logging
from typing import Optional
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import get_data_source_config, get_finance_config
from skills.stock_data_enhanced.stock_data import (
    get_stock_quote as enhanced_get_stock_quote,
    get_stock_news as enhanced_get_stock_news,
    get_macro_data as enhanced_get_macro_data,
    get_industry_data as enhanced_get_industry_data
)


class FinancialDataFetcher:
    """
    Fetcher for real-time financial data from Chinese sources.

    Data sources:
    - Sina Finance (新浪财经): Stock quotes, news
    - Eastmoney (东方财富): Financial reports, industry data
    - Jin10 (金十数据): Macro economic data
    """

    def __init__(self):
        """Initialize the data fetcher."""
        config = get_data_source_config()
        finance_config = get_finance_config()

        self.sina_quote_url = config.sina_quote_url
        self.sina_news_url = config.sina_news_url
        self.eastmoney_stock_info_url = config.eastmoney_stock_info_url
        self.eastmoney_news_url = config.eastmoney_news_url
        self.macro_data_url = config.eastmoney_macro_url
        self.eastmoney_industry_url = config.eastmoney_industry_url
        self.china_macro_defaults = finance_config.china_macro_defaults
        self.us_macro_defaults = finance_config.us_macro_defaults
        self.industry_defaults = finance_config.industry_defaults

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://finance.sina.com.cn/"
        })
        # Configure retries for transient network errors
        retries = Retry(total=3, backoff_factor=0.5,
                        status_forcelist=[429, 500, 502, 503, 504],
                        allowed_methods=["HEAD", "GET", "POST"])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Logger
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO)

    def get_stock_quote(self, symbol: str) -> Optional[dict]:
        """
        Get real-time stock quote using enhanced stock data skill.

        Args:
            symbol: Stock ticker symbol (e.g., 'sh600519', 'sz000001')

        Returns:
            Dict with quote data or None if failed.
        """
        return enhanced_get_stock_quote(symbol)

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
            response.raise_for_status()
            try:
                data = response.json()
            except Exception:
                self.logger.warning("Eastmoney quote: failed to parse JSON for %s; text truncated: %s", symbol, response.text[:200])
                data = None

            if data and data.get("data"):
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
        except requests.exceptions.RequestException as e:
            self.logger.warning("Eastmoney quote failed for %s: %s", symbol, e)
        except Exception as e:
            self.logger.exception("Unexpected Eastmoney quote error for %s: %s", symbol, e)

        return None

    def get_stock_news(self, symbol: str, limit: int = 10) -> list[dict]:
        """
        Get recent news for a stock using enhanced stock data skill.

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of news items

        Returns:
            List of news dicts.
        """
        return enhanced_get_stock_news(symbol, limit)

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
                self.eastmoney_news_url,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            text = response.text.strip()
            if text:
                try:
                    data = response.json()
                except Exception:
                    try:
                        data = json.loads(text)
                    except Exception as e:
                        self.logger.warning("Error parsing Eastmoney news JSON for %s: %s; text truncated: %s", symbol, e, text[:200])
                        data = None

                if data and data.get("Data"):
                    for item in data["Data"]:
                        news_list.append({
                            "title": item.get("Title", ""),
                            "source": "东方财富",
                            "published_at": datetime.now(),
                            "url": f"https://news.eastmoney.com/{item.get('ID', '')}.html",
                            "summary": item.get("Brief", "")
                        })

        except requests.exceptions.RequestException as e:
            self.logger.warning("Network error fetching Eastmoney news for %s: %s", symbol, e)
        except Exception as e:
            self.logger.exception("Unexpected error fetching Eastmoney news for %s: %s", symbol, e)

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
                self.eastmoney_stock_info_url,
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

        except requests.exceptions.RequestException as e:
            self.logger.warning("Network error fetching financial reports for %s: %s", symbol, e)
        except Exception as e:
            self.logger.exception("Unexpected error fetching financial reports for %s: %s", symbol, e)

        return None

    def get_macro_data(self, country: str = "china") -> Optional[dict]:
        """
        Get macroeconomic data using enhanced stock data skill.

        Args:
            country: Country name ('china' or 'us')

        Returns:
            Dict with macro indicators or None if failed.
        """
        return enhanced_get_macro_data(country)

    def get_industry_data(self, sector: str) -> Optional[dict]:
        """
        Get industry/sector analysis data using enhanced stock data skill.

        Args:
            sector: Industry sector name

        Returns:
            Dict with industry metrics or None if failed.
        """
        return enhanced_get_industry_data(sector)


# Singleton instance
_fetcher: Optional[FinancialDataFetcher] = None


def get_data_fetcher() -> FinancialDataFetcher:
    """Get singleton data fetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = FinancialDataFetcher()
    return _fetcher
