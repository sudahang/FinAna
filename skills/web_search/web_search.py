"""
网络搜索技能 - 用于查找公司股票信息

功能:
- 搜索股票代码和公司名称
- 查找公司所属国家和市场
- 识别公司所属行业/板块
- 获取公司基本信息

使用 LLM 智能识别公司名称到股票代码的映射
"""

import requests
import json
import re
from typing import Optional, List, Dict
from datetime import datetime

from llm.client import get_llm_client


class WebSearcher:
    """网络搜索工具 - 查找公司股票信息"""

    # 股票 symbol 模式
    SYMBOL_PATTERNS = {
        'a_share_sh': r'\b(sh[0-9]{6}|[0-9]{6}\.SH)\b',
        'a_share_sz': r'\b(sz[0-9]{6}|[0-9]{6}\.SZ)\b',
        'hk_stock': r'\b(HK[0-9]{5}|[0-9]{5}\.HK|0[0-9]{4}\.HK)\b',
        'us_stock': r'\b([A-Z]{3,4})\b',
    }

    # 国家/市场关键词
    MARKET_KEYWORDS = {
        'china': ['a 股', '沪深', '上海', '深圳', '人民币'],
        'hk': ['港股', '香港', 'hk', '恒生', '港交所'],
        'us': ['美股', '美国', 'nasdaq', 'nyse', 'dow', '美元'],
    }

    # 行业关键词
    SECTOR_KEYWORDS = {
        '科技': ['科技', '软件', 'ai', '人工智能', '半导体', '芯片', '互联网', '云计算'],
        '汽车': ['汽车', '新能源', 'ev', '电动车', '自动驾驶'],
        '金融': ['金融', '银行', '保险', '证券', '支付'],
        '消费': ['消费', '零售', '食品', '饮料', '家电', '服装', '电商', '白酒'],
        '医疗': ['医疗', '健康', '医药', '生物', '制药', '医疗器械'],
        '能源': ['能源', '石油', '天然气', '光伏', '风电', '电池', '太阳能'],
        '通信': ['通信', '5g', '电信', '网络'],
        '房地产': ['房地产', '地产', '物业', '建筑'],
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化网络搜索工具

        Args:
            api_key: 可选的 API 密钥
        """
        self.api_key = api_key
        self.llm = get_llm_client()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*',
        })

    def search_stock_info(self, query: str) -> Dict:
        """
        搜索股票信息

        Args:
            query: 搜索查询（公司名称、代码等）

        Returns:
            包含股票信息的字典
        """
        result = {
            'symbol': None,
            'name': None,
            'country': None,
            'sector': None,
            'exchange': None,
            'confidence': 0.0,
            'source': 'web_search'
        }

        query_stripped = query.strip()

        # 1. 检测股票代码模式
        symbol = self._extract_symbol(query_stripped)
        if symbol:
            result['symbol'] = symbol
            result['country'] = self._infer_country_from_symbol(symbol)
            result['confidence'] = 0.85
            result['source'] = 'pattern_match'
            return result

        # 2. 检测国家/市场
        result['country'] = self._detect_market(query_stripped)

        # 3. 检测行业
        result['sector'] = self._detect_sector(query_stripped)

        # 4. 使用 LLM 识别公司名称到股票代码
        llm_result = self._lookup_symbol_with_llm(query_stripped)
        if llm_result.get('symbol'):
            result['symbol'] = llm_result['symbol']
            result['name'] = llm_result.get('name')
            result['country'] = llm_result.get('country', result['country'])
            result['confidence'] = llm_result.get('confidence', 0.8)
            result['source'] = 'llm_lookup'

        return result

    def _extract_symbol(self, text: str) -> Optional[str]:
        """从文本中提取股票代码"""
        text_lower = text.lower()

        # A 股：6 位数字
        cn_match = re.search(r'\b([06]\d{5})\b', text)
        if cn_match:
            code = cn_match.group(1)
            if code.startswith(('6', '9')):
                return f'sh{code}'
            elif code.startswith(('0', '3')):
                return f'sz{code}'

        # A 股：带市场前缀
        prefix_match = re.search(r'\b((?:sh|sz)\d{6})\b', text_lower)
        if prefix_match:
            return prefix_match.group(1)

        # 港股：HK + 5 位数字
        hk_match = re.search(r'\b(hk\d{5})\b', text_lower)
        if hk_match:
            return hk_match.group(1).upper()

        # 美股：3-4 个字母（排除常见英文单词）
        excluded = ['THE', 'AND', 'FOR', 'WITH', 'THIS', 'THAT', 'FROM', 'HAVE', 'BUT', 'NOT', 'YOU', 'WAS', 'ARE', 'HAS', 'WILL', 'WOULD', 'THERE', 'THEIR', 'WHAT', 'WHICH', 'MORE', 'SOME', 'TIME', 'YEAR', 'PEOPLE', 'WAY', 'DAY', 'MAN', 'WOMAN', 'LIFE', 'WORLD', 'HAND', 'PART', 'PLACE', 'CASE', 'WEEK', 'COMPANY', 'SYSTEM', 'PROGRAM', 'QUESTION', 'NUMBER', 'GROUP', 'PROBLEM', 'FACT']
        us_match = re.search(r'\b([A-Z]{3,4})\b', text.upper())
        if us_match and us_match.group(1) not in excluded:
            return us_match.group(1)

        return None

    def _infer_country_from_symbol(self, symbol: str) -> str:
        """从股票代码推断国家/市场"""
        if symbol.startswith('sh') or symbol.startswith('sz'):
            return 'china'
        elif symbol.upper().startswith('HK'):
            return 'hk'
        elif len(symbol) <= 4 and symbol.isalpha():
            return 'us'
        return 'us'

    def _infer_sector_from_name(self, name: str) -> Optional[str]:
        """从公司名称推断行业"""
        name_lower = name.lower()
        for sector, keywords in self.SECTOR_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in name_lower or kw in name_lower:
                    return sector
        return None

    def _detect_market(self, text: str) -> str:
        """检测文本中提到的市场"""
        text_lower = text.lower()
        for market, keywords in self.MARKET_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return market
        return 'us'

    def _detect_sector(self, text: str) -> Optional[str]:
        """检测文本中提到的行业"""
        text_lower = text.lower()
        sector_scores = {}
        for sector, keywords in self.SECTOR_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                sector_scores[sector] = score
        if sector_scores:
            return max(sector_scores, key=sector_scores.get)
        return None

    def _lookup_symbol_with_llm(self, query: str) -> Dict:
        """
        使用 LLM 将公司名称映射到股票代码

        Args:
            query: 公司名称或关键词

        Returns:
            包含 symbol, country, name, confidence 的字典
        """
        system_prompt = """你是一个专业的股票分析师助手，熟悉全球主要股票市场的上市公司。

你的任务是将用户输入的公司名称或关键词转换为正确的股票代码。

请根据以下规则判断：
1. A 股（中国）：代码格式为 shXXXXXX（上交所，6 开头）或 szXXXXXXXX（深交所，0 或 3 开头）
2. 港股（香港）：代码格式为 HKXXXXX（5 位数字）
3. 美股（美国）：代码格式为 3-4 个大写字母（如 TSLA, AAPL）

常见公司示例：
- 贵州茅台 → sh600519
- 宁德时代 → sz300750
- 格力电器 → sz000651
- 美的集团 → sz000333
- 腾讯控股 → HK00700
- 阿里巴巴 → HK09988（港股）或 BABA（美股）
- 美团 → HK03690
- 小米集团 → HK01810
- 特斯拉 → TSLA
- 英伟达 → NVDA
- 苹果 → AAPL

如果无法确定具体公司，返回 null。"""

        user_prompt = f"""请将以下公司或关键词转换为股票代码：

输入："{query}"

请只返回 JSON 格式：
{{
    "symbol": "股票代码",
    "name": "公司标准名称",
    "country": "china/hk/us",
    "confidence": 0.9
}}"""

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt
            )

            # 解析 JSON
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
                return {
                    'symbol': parsed.get('symbol'),
                    'name': parsed.get('name'),
                    'country': parsed.get('country'),
                    'confidence': parsed.get('confidence', 0.8)
                }
        except Exception as e:
            print(f"LLM lookup failed: {e}")

        return {}

    def search_with_engine(self, query: str, engine: str = 'yahoo') -> Dict:
        """
        使用搜索引擎查找股票信息

        Args:
            query: 搜索查询
            engine: 搜索引擎 ('yahoo', 'google')

        Returns:
            搜索结果
        """
        if engine == 'yahoo':
            return self._search_yahoo(query)
        return self.search_stock_info(query)

    def _search_yahoo(self, query: str) -> Dict:
        """使用 Yahoo Finance 搜索"""
        try:
            params = {
                'q': query,
                'quotesCount': 5,
                'newsCount': 0,
            }

            response = self.session.get(
                'https://query1.finance.yahoo.com/v1/finance/search',
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                quotes = data.get('quotes', [])

                if quotes:
                    first_quote = quotes[0]
                    symbol = first_quote.get('symbol', '')
                    name = first_quote.get('shortname', '')
                    exchange = first_quote.get('exchange', '')

                    return {
                        'symbol': symbol,
                        'name': name,
                        'exchange': exchange,
                        'country': self._exchange_to_country(exchange),
                        'sector': first_quote.get('sector'),
                        'confidence': 0.9,
                        'source': 'yahoo_finance'
                    }

        except Exception as e:
            print(f"Yahoo Finance search failed: {e}")

        return self.search_stock_info(query)

    def _exchange_to_country(self, exchange: str) -> str:
        """将交易所代码转换为国家/市场"""
        exchange_upper = exchange.upper()
        if exchange_upper in ['SHG', 'SS', 'SZ']:
            return 'china'
        elif exchange_upper in ['HKG', 'HK']:
            return 'hk'
        elif exchange_upper in ['NMS', 'NGS', 'NYQ', 'NYSE', 'NASDAQ']:
            return 'us'
        return 'us'


def get_web_searcher(api_key: Optional[str] = None) -> WebSearcher:
    """获取 WebSearcher 单例"""
    return WebSearcher(api_key)


# 便捷函数
def search_company_info(query: str) -> Dict:
    """
    搜索公司信息

    Args:
        query: 公司名称或代码

    Returns:
        包含公司信息的字典
    """
    searcher = get_web_searcher()
    return searcher.search_stock_info(query)


if __name__ == '__main__':
    # 测试
    test_queries = [
        '腾讯',
        'Tesla',
        '贵州茅台',
        'sh600519',
        'HK00700',
        'TSLA',
        '阿里巴巴',
        '宁德时代',
        '格力电器',
        '美的集团',
    ]

    print("测试 WebSearcher:")
    print("=" * 60)

    for query in test_queries:
        result = search_company_info(query)
        print(f"\n查询：{query}")
        print(f"  股票代码：{result.get('symbol', 'N/A')}")
        print(f"  市场：{result.get('country', 'N/A')}")
        print(f"  行业：{result.get('sector', 'N/A')}")
        print(f"  来源：{result.get('source', 'N/A')}")
        print(f"  置信度：{result.get('confidence', 0):.0%}")
