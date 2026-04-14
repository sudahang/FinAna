"""Central configuration for FinAna application.

All hardcoded constants should be defined here and imported from here.
"""

import os
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class APIConfig(BaseModel):
    """API-related configuration."""

    title: str = "FinAna API"
    description: str = "Investment Research Assistant API"
    version: str = "0.1.0"


class LLMConfig(BaseModel):
    """LLM (DashScope) configuration."""

    api_key: str = ""
    base_url: str = "https://coding.dashscope.aliyuncs.com/v1"
    model: str = "qwen3.5-plus"
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 90


class DataSourceConfig(BaseModel):
    """External data source URLs and settings."""

    # Sina Finance
    sina_quote_url: str = "http://hq.sinajs.cn/list={symbol}"
    sina_news_url: str = "https://feed.mix.sina.com.cn/api/roll/get"

    # Tencent Finance
    tencent_quote_url: str = "https://qt.gtimg.cn/q={symbol}"

    # Eastmoney
    eastmoney_stock_search_url: str = "https://searchapi.eastmoney.com/api/suggest/get"
    eastmoney_stock_detail_url: str = "https://push2.eastmoney.com/api/qt/stock/get"
    eastmoney_stock_history_url: str = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    eastmoney_news_url: str = "https://api.eastmoney.com/News/getList"
    eastmoney_stock_info_url: str = "https://push2.eastmoney.com/api/qt/stock/get"
    eastmoney_news_api: str = "https://push2.eastmoney.com/api/qt/stocknews/get"
    eastmoney_macro_url: str = "https://datainterface.eastmoney.com/Data_Data/OtherData"
    eastmoney_industry_url: str = "http://push2.eastmoney.com/api/qt/clist/get"

    # Market code mapping
    market_codes: dict = {
        "sh": "1",
        "sz": "0",
        "hk": "116",
        "us": "162",
        "bj": "2"
    }


class WebUIConfig(BaseModel):
    """Web UI configuration."""

    server_name: str = "0.0.0.0"
    server_port: int = 7860
    queue_max_size: int = 10


class FinanceConfig(BaseModel):
    """Finance-related default values."""

    # Default macro data for China
    china_macro_defaults: dict = {
        "gdp_growth": 5.2,
        "inflation_rate": 0.2,
        "interest_rate": 3.45,
        "unemployment_rate": 5.1,
        "manufacturing_pmi": 50.2,
        "consumer_confidence": 120.5
    }

    # Default macro data for US
    us_macro_defaults: dict = {
        "gdp_growth": 2.5,
        "inflation_rate": 3.2,
        "interest_rate": 5.25,
        "unemployment_rate": 3.8,
        "manufacturing_pmi": 48.5,
        "consumer_confidence": 110.0
    }

    # Default industry data
    industry_defaults: dict = {
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

    # Currency symbols
    currency_symbols: dict = {
        "sh": "元",
        "sz": "元",
        "hk": "港元",
        "bj": "元",
        "default": "$"
    }

    # Default stock when no match
    default_stock: str = "TSLA"


class CompanyMappingConfig(BaseModel):
    """Company name to stock symbol mapping."""

    mappings: dict = {
        # Common US stocks (Chinese names)
        "特斯拉": "TSLA",
        "TSLA": "TSLA",
        "英伟达": "NVDA",
        "NVIDIA": "NVDA",
        "NVDA": "NVDA",
        "苹果": "AAPL",
        "APPLE": "AAPL",
        "AAPL": "AAPL",
        "微软": "MSFT",
        "MICROSOFT": "MSFT",
        "MSFT": "MSFT",
        "谷歌": "GOOGL",
        "GOOGLE": "GOOGL",
        "GOOGL": "GOOGL",
        "亚马逊": "AMZN",
        "AMAZON": "AMZN",
        "AMZN": "AMZN",
        "META": "META",
        "FACEBOOK": "META",
        # Chinese concept stocks
        "阿里巴巴": "BABA",
        "ALIBABA": "BABA",
        "BABA": "BABA",
        "阿里": "BABA",
        "拼多多": "PDD",
        "PDD": "PDD",
        "京东": "JD",
        "JD": "JD",
        "百度": "BIDU",
        "BAIDU": "BIDU",
        "BIDU": "BIDU",
        "网易": "NTES",
        "NETEASE": "NTES",
        "NTES": "NTES",
        "小鹏": "XPEV",
        "XPENG": "XPEV",
        "XPEV": "XPEV",
        "理想": "LI",
        "LI AUTO": "LI",
        "蔚来": "NIO",
        "NIO": "NIO",
        # A-share popular stocks
        "贵州茅台": "sh600519",
        "茅台": "sh600519",
        "600519": "sh600519",
        "宁德时代": "sz300750",
        "宁德": "sz300750",
        "300750": "sz300750",
        "中国平安": "sh601318",
        "平安": "sh601318",
        "601318": "sh601318",
        "招商银行": "sh600036",
        "招行": "sh600036",
        "600036": "sh600036",
        "腾讯": "HK00700",
        "腾讯控股": "HK00700",
        "00700": "HK00700",
        "阿里巴巴港股": "HK09988",
        "9988": "HK09988"
    }

    # Sector keywords for sector extraction
    sector_keywords: dict = {
        "科技": ["科技", "软件", "ai", "半导体", "芯片", "互联网", "nvidia", "苹果", "微软"],
        "汽车": ["汽车", "新能源", "ev", "tesla", "特斯拉", "比亚迪", "造车"],
        "医疗": ["医疗", "健康", "医药", "biotech", "生物科技", "器械"],
        "金融": ["金融", "银行", "保险", "券商", " fintech"],
        "消费": ["消费", "零售", "食品", "饮料", "家电", "服装"],
        "能源": ["能源", "石油", "天然气", "光伏", "风电", "电池"]
    }

    default_sector: str = "科技"


def get_api_config() -> APIConfig:
    """Get API configuration."""
    return APIConfig()


def get_llm_config() -> LLMConfig:
    """Get LLM configuration from environment."""
    return LLMConfig(
        api_key=os.getenv("DASHSCOPE_API_KEY", ""),
        base_url=os.getenv("DASHSCOPE_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1"),
        model=os.getenv("DASHSCOPE_MODEL", "qwen3.5-plus"),
        max_tokens=int(os.getenv("DASHSCOPE_MAX_TOKENS", 2048)),
        temperature=float(os.getenv("DASHSCOPE_TEMPERATURE", 0.7)),
        timeout=int(os.getenv("DASHSCOPE_TIMEOUT", 90))
    )


def get_data_source_config() -> DataSourceConfig:
    """Get data source configuration."""
    return DataSourceConfig()


def get_webui_config() -> WebUIConfig:
    """Get Web UI configuration."""
    return WebUIConfig(
        server_name=os.getenv("WEBUI_HOST", "0.0.0.0"),
        server_port=int(os.getenv("WEBUI_PORT", 7860)),
        queue_max_size=int(os.getenv("WEBUI_QUEUE_MAX_SIZE", 10))
    )


def get_finance_config() -> FinanceConfig:
    """Get finance configuration."""
    return FinanceConfig()


def get_company_mapping_config() -> CompanyMappingConfig:
    """Get company mapping configuration."""
    return CompanyMappingConfig()
