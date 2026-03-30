"""AI-powered Input Router Agent for parsing user queries."""

from typing import TypedDict, Optional
from data.schemas import ResearchReport
from llm.client import LLMClient, get_llm_client
from skills.web_search.web_search import WebSearcher, get_web_searcher
import json
import re


class DetectedParams(TypedDict, total=False):
    """Detected parameters from user query."""
    country: str  # 'china', 'us', 'hk'
    sector: str   # industry/sector
    symbol: str   # stock symbol
    query_type: str  # 'stock_analysis', 'industry_analysis', 'macro_analysis'
    confidence: float  # confidence score 0-1


class InputRouterAgent:
    """
    AI-powered Input Router Agent.

    Analyzes user queries to extract:
    1. Country/Market (US, China A-shares, HK stocks)
    2. Sector/Industry
    3. Stock Symbol
    4. Query Type (stock/industry/macro analysis)

    Uses web search and pattern matching to intelligently identify stocks.
    """

    SYSTEM_PROMPT = """你是一个投资研究助手，负责分析用户的查询意图。

请从用户输入中提取以下信息：
1. 国家/市场：中国（A 股）、香港（港股）、美国（美股）
2. 行业/板块：科技、金融、消费、医疗、汽车、能源等
3. 股票代码：如果有具体股票
4. 查询类型：个股分析、行业分析、宏观经济分析

请以 JSON 格式输出：
{
    "country": "china/us/hk",
    "sector": "行业名称",
    "symbol": "股票代码",
    "query_type": "stock_analysis/industry_analysis/macro_analysis",
    "confidence": 0.9,
    "reasoning": "简要说明判断依据"
}

如果某些信息无法确定，可以留空或设为 null。"""

    # 国家/市场关键词
    COUNTRY_KEYWORDS = {
        'china': ['中国', 'a 股', '沪深', '上海', '深圳', '人民币'],
        'hk': ['香港', '港股', 'hk', '港交所', '恒生'],
        'us': ['美国', '美股', 'nasdaq', 'nyse', 'dow', '美元']
    }

    # 行业关键词映射（不包含具体公司名）
    SECTOR_KEYWORDS = {
        '科技': ['科技', '软件', 'ai', '人工智能', '半导体', '芯片', '互联网', '云计算', '大数据'],
        '汽车': ['汽车', '新能源', 'ev', '电动车', '造车'],
        '金融': ['金融', '银行', '保险', '券商', '证券', '支付'],
        '消费': ['消费', '零售', '食品', '饮料', '家电', '服装', '电商', '白酒'],
        '医疗': ['医疗', '健康', '医药', '生物', '制药', '医疗器械', '疫苗'],
        '能源': ['能源', '石油', '天然气', '光伏', '风电', '电池', '太阳能'],
        '房地产': ['房地产', '地产', '物业', '建筑'],
        '通信': ['通信', '5g', '电信', '网络']
    }

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the Input Router Agent.

        Args:
            llm_client: Optional LLM client. If None, uses default.
        """
        self.llm = llm_client or get_llm_client()
        self.web_searcher = get_web_searcher()
        self.role = "Input Router"
        self.goal = "Parse user queries using web search"

    def parse_query(self, query: str) -> DetectedParams:
        """
        Parse user query to extract parameters using web search.

        Args:
            query: User's input query

        Returns:
            DetectedParams with extracted information
        """
        # Use web search to find stock information
        web_result = self.web_searcher.search_stock_info(query)

        # Get symbol and basic info from web search
        symbol = web_result.get('symbol', '')
        country = web_result.get('country', '')
        sector = web_result.get('sector', '')

        # Fallback to pattern matching if web search didn't find symbol
        if not symbol:
            symbol = self._extract_symbol_from_query(query)

        # Fallback country detection
        if not country:
            country = self._detect_country(query)

        # Fallback sector detection
        if not sector:
            sector = self._detect_sector(query)

        # Determine query type
        query_type = self._detect_query_type(query, symbol)

        # Calculate confidence
        confidence = self._calculate_confidence(symbol, country, sector, web_result.get('source', ''))

        return DetectedParams(
            country=country,
            sector=sector,
            symbol=symbol,
            query_type=query_type,
            confidence=confidence
        )

    def _extract_symbol_from_query(self, query: str) -> str:
        """Extract stock symbol from query using patterns."""
        query_lower = query.lower()

        # A-share: 6 digits
        cn_match = re.search(r'\b([06]\d{5})\b', query)
        if cn_match:
            code = cn_match.group(1)
            if code.startswith(('6', '9')):
                return f'sh{code}'
            elif code.startswith(('0', '3')):
                return f'sz{code}'

        # A-share with prefix
        prefix_match = re.search(r'\b((?:sh|sz)\d{6})\b', query_lower)
        if prefix_match:
            return prefix_match.group(1)

        # HK stock: HK + 5 digits
        hk_match = re.search(r'\b(hk\d{5})\b', query_lower)
        if hk_match:
            return hk_match.group(1).upper()

        # US ticker: 3-4 uppercase letters
        # Exclude common English words
        excluded = ['THE', 'AND', 'FOR', 'WITH', 'THIS', 'THAT', 'FROM', 'HAVE', 'BUT', 'NOT', 'YOU', 'WAS', 'ARE', 'HAS']
        tickers = re.findall(r'\b([A-Z]{3,4})\b', query.upper())
        for ticker in tickers:
            if ticker not in excluded:
                return ticker

        return ''

    def _detect_country(self, query: str) -> str:
        """Detect country/market from query."""
        query_lower = query.lower()

        # Check explicit keywords
        for country, keywords in self.COUNTRY_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower or kw in query:
                    return country

        # Check symbol patterns
        if re.search(r'(sh|sz)\d{6}', query_lower) or re.search(r'\b[06]\d{5}\b', query):
            return 'china'

        if re.search(r'hk\d{5}', query_lower):
            return 'hk'

        return 'us'  # Default

    def _detect_sector(self, query: str) -> str:
        """Detect sector from query using keyword matching."""
        query_lower = query.lower()
        sector_scores = {}

        for sector, keywords in self.SECTOR_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                sector_scores[sector] = score

        if sector_scores:
            return max(sector_scores, key=sector_scores.get)
        return ''

    def _detect_query_type(self, query: str, symbol: str) -> str:
        """Determine the type of query."""
        query_lower = query.lower()

        # Macro indicators
        if any(kw in query_lower for kw in ['大盘', '经济', '宏观', 'gdp', '通胀', '利率', 'pmi']):
            return 'macro_analysis'

        # Industry indicators
        if any(kw in query_lower for kw in ['行业', '板块', '赛道', '领域']) and not symbol:
            return 'industry_analysis'

        # Stock analysis (default if symbol detected)
        if symbol or any(kw in query_lower for kw in ['股票', '股价', '分析', '走势', '估值', '基本面']):
            return 'stock_analysis'

        return 'stock_analysis'

    def _calculate_confidence(self, symbol: str, country: str, sector: str, source: str) -> float:
        """Calculate confidence score."""
        confidence = 0.5

        if symbol:
            confidence += 0.3
        if country:
            confidence += 0.1
        if sector:
            confidence += 0.1

        return min(confidence, 0.95)

    def parse_with_llm(self, query: str) -> DetectedParams:
        """
        Use LLM to parse complex queries.

        Args:
            query: User's input query

        Returns:
            DetectedParams with LLM-enhanced extraction
        """
        try:
            user_prompt = f"""请分析以下用户查询：

用户输入："{query}"

请提取：国家/市场、行业板块、股票代码、查询类型"""

            response = self.llm.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=self.SYSTEM_PROMPT
            )

            # Parse JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
                return DetectedParams(
                    country=parsed.get('country', 'us'),
                    sector=parsed.get('sector', ''),
                    symbol=parsed.get('symbol', ''),
                    query_type=parsed.get('query_type', 'stock_analysis'),
                    confidence=parsed.get('confidence', 0.8),
                    reasoning=parsed.get('reasoning', '')
                )
        except Exception as e:
            print(f"LLM parsing failed: {e}, using rule-based parsing")

        return self.parse_query(query)

    def route_to_agents(self, params: DetectedParams) -> dict:
        """
        Determine which agents to invoke based on parsed params.

        Args:
            params: DetectedParams from query parsing

        Returns:
            Dictionary with routing information
        """
        routing = {
            'run_macro': False,
            'run_industry': False,
            'run_equity': False,
            'params': params
        }

        query_type = params.get('query_type', 'stock_analysis')

        if query_type == 'macro_analysis':
            routing['run_macro'] = True
        elif query_type == 'industry_analysis':
            routing['run_industry'] = True
        elif query_type == 'stock_analysis':
            routing['run_macro'] = True
            routing['run_industry'] = True
            routing['run_equity'] = True

        return routing


def get_router_agent() -> InputRouterAgent:
    """Get singleton instance of InputRouterAgent."""
    return InputRouterAgent()
