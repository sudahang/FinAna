"""AI-powered Input Router Agent for parsing user queries."""

from typing import TypedDict, Optional
from data.schemas import ResearchReport
from llm.client import LLMClient, get_llm_client
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

    Then routes to appropriate analyst agents.
    """

    SYSTEM_PROMPT = """你是一个投资研究助手，负责分析用户的查询意图。

请从用户输入中提取以下信息：
1. 国家/市场：中国（A 股）、香港（港股）、美国（美股）
2. 行业/板块：科技、金融、消费、医疗、汽车、能源等
3. 股票代码：如果有具体股票
4. 查询类型：个股分析、行业分析、宏观经济分析

请根据以下规则判断：
- A 股代码：6 位数字，或以 sh/sz 开头
- 港股代码：5 位数字，或以 HK 开头
- 美股代码：3-4 个字母

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
        'china': ['中国', 'a 股', '沪深', '上海', '深圳', '人民币', 'cn'],
        'hk': ['香港', '港股', 'hk', '港交所', '恒生'],
        'us': ['美国', '美股', 'nasdaq', 'nyse', 'dow', 'us', '美元']
    }

    # 行业关键词映射
    SECTOR_KEYWORDS = {
        '科技': ['科技', '软件', 'ai', '人工智能', '半导体', '芯片', '互联网', '云计算', '大数据', 'nvidia', '英伟达', '苹果', '微软', '谷歌', 'meta', '腾讯', '阿里', '百度'],
        '汽车': ['汽车', '新能源', 'ev', '电动车', 'tesla', '特斯拉', '比亚迪', '造车', '蔚来', '小鹏', '理想'],
        '金融': ['金融', '银行', '保险', '券商', '证券', 'fintech', '支付', '招行', '平安', '工行'],
        '消费': ['消费', '零售', '食品', '饮料', '家电', '服装', '电商', '茅台', '五粮液', '京东', '拼多多', '美团'],
        '医疗': ['医疗', '健康', '医药', '生物', 'biotech', '制药', '医疗器械', '疫苗'],
        '能源': ['能源', '石油', '天然气', '光伏', '风电', '电池', '宁德时代', '太阳能'],
        '房地产': ['房地产', '地产', '物业', '万科', '碧桂园'],
        '通信': ['通信', '5g', '电信', '移动', '联通', '华为', '中兴']
    }

    # 股票名称到代码的映射
    STOCK_MAPPINGS = {
        # 美股
        '特斯拉': 'TSLA', 'tsla': 'TSLA',
        '英伟达': 'NVDA', 'nvidia': 'NVDA',
        '苹果': 'AAPL', 'apple': 'AAPL',
        '微软': 'MSFT', 'microsoft': 'MSFT',
        '谷歌': 'GOOGL', 'google': 'GOOGL',
        '亚马逊': 'AMZN', 'amazon': 'AMZN',
        'meta': 'META', 'facebook': 'META',
        '耐克': 'NKE', 'nike': 'NKE',
        '星巴克': 'SBUX', 'starbucks': 'SBUX',
        '可口可乐': 'KO', '百事': 'PEP',
        # 中概股
        '阿里巴巴': 'BABA', 'ali': 'BABA', 'ali 巴巴': 'BABA',
        '拼多多': 'PDD', 'pdd': 'PDD',
        '京东': 'JD', 'jd': 'JD',
        '百度': 'BIDU', 'baidu': 'BIDU',
        '网易': 'NTES', 'netease': 'NTES',
        '小鹏': 'XPEV', 'xpeng': 'XPEV',
        '理想': 'LI', 'li auto': 'LI',
        '蔚来': 'NIO', 'nio': 'NIO',
        '携程': 'TCOM', 'trip': 'TCOM',
        # A 股
        '贵州茅台': 'sh600519', '茅台': 'sh600519',
        '宁德时代': 'sz300750', '宁德': 'sz300750', 'catl': 'sz300750',
        '中国平安': 'sh601318', '平安': 'sh601318',
        '招商银行': 'sh600036', '招行': 'sh600036',
        '五粮液': 'sz000858',
        '比亚迪': 'sz002594',
        '美的集团': 'sz000333',
        '格力电器': 'sz000651',
        '海尔智家': 'sh600690',
        '万科': 'sz000002',
        '恒瑞医药': 'sh600276',
        '药明康德': 'sh603259',
        '中信证券': 'sh600030',
        '东方财富': 'sz300059',
        '立讯精密': 'sz002475',
        '海康威视': 'sz002415',
        '中芯国际': 'sh688981',
        '北方华创': 'sz002371',
        '隆基绿能': 'sh601012',
        '通威股份': 'sh600438',
        # 港股
        '腾讯': 'HK00700', '腾讯控股': 'HK00700',
        '阿里巴巴港股': 'HK09988', '阿里健康': 'HK00241',
        '美团': 'HK03690', '美团点评': 'HK03690',
        '小米': 'HK01810', '小米集团': 'HK01810',
        '京东健康': 'HK06618', '京东物流': 'HK02618',
        '网易港股': 'HK09999',
        '百度港股': 'HK09888',
        '小鹏港股': 'HK09868',
        '理想港股': 'HK02015',
        '蔚来港股': 'HK09866',
        '快手': 'HK01024',
        '哔哩哔哩': 'HK09626', 'b 站': 'HK09626',
        '吉利汽车': 'HK00175',
        '理想汽车': 'HK02015',
        '安踏体育': 'HK02020',
        '李宁': 'HK02331',
        '海底捞': 'HK06862',
        '华润啤酒': 'HK00291',
        '中国神华': 'HK01088',
        '建设银行': 'HK00939',
        '工商银行': 'HK01398',
        '中国平安港股': 'HK02318',
        '中国人寿': 'HK02628',
        '友邦保险': 'HK01299',
        '港交所': 'HK00388', '香港交易所': 'HK00388',
        '中国移动': 'HK00941',
        '中国电信': 'HK00728',
        '中国联通': 'HK00762',
        '中芯国际港股': 'HK00981',
        '联想集团': 'HK00992',
        'hsbc': 'HK00005', '汇丰控股': 'HK00005'
    }

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the Input Router Agent.

        Args:
            llm_client: Optional LLM client. If None, uses default.
        """
        self.llm = llm_client or get_llm_client()
        self.role = "Input Router"
        self.goal = "Parse user queries and route to appropriate agents"

    def parse_query(self, query: str) -> DetectedParams:
        """
        Parse user query to extract parameters.

        Args:
            query: User's input query

        Returns:
            DetectedParams with extracted information
        """
        query_lower = query.lower()

        # Step 1: Detect country
        country = self._detect_country(query, query_lower)

        # Step 2: Detect stock symbol
        symbol = self._detect_symbol(query, query_lower)

        # Step 3: Detect sector
        sector = self._detect_sector(query_lower)

        # Step 4: Determine query type
        query_type = self._detect_query_type(query, symbol, sector)

        # Step 5: Calculate confidence
        confidence = self._calculate_confidence(query, symbol, country, sector)

        return DetectedParams(
            country=country,
            sector=sector,
            symbol=symbol,
            query_type=query_type,
            confidence=confidence
        )

    def _detect_country(self, query: str, query_lower: str) -> str:
        """Detect country/market from query."""
        # Check for explicit country keywords
        for country, keywords in self.COUNTRY_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower or kw in query:
                    return country

        # Check stock symbol patterns
        # A-share pattern: sh/sz + 6 digits or 6 digits alone
        if re.search(r'(sh|sz)\d{6}', query_lower) or re.search(r'\b[06]\d{5}\b', query):
            return 'china'

        # HK stock pattern: HK + 5 digits
        if re.search(r'hk\d{5}', query_lower):
            return 'hk'

        # Check if query contains Chinese stock names
        for name in self.STOCK_MAPPINGS:
            if name in query:
                symbol = self.STOCK_MAPPINGS[name]
                if symbol.startswith('sh') or symbol.startswith('sz'):
                    return 'china'
                elif symbol.startswith('HK'):
                    return 'hk'

        # Default to US for ticker symbols
        if re.search(r'\b[A-Z]{3,4}\b', query):
            return 'us'

        return 'us'  # Default

    def _detect_symbol(self, query: str, query_lower: str) -> str:
        """Detect stock symbol from query."""
        # Priority 1: Check for A-share codes (6 digits)
        cn_pattern = re.findall(r'\b([06]\d{5})\b', query)
        if cn_pattern:
            code = cn_pattern[0]
            if code.startswith(('6', '9')):
                return f"sh{code}"
            elif code.startswith(('0', '3')):
                return f"sz{code}"

        # Priority 2: Check for HK codes (HK + 5 digits)
        hk_pattern = re.findall(r'\b(hk\d{5})\b', query_lower)
        if hk_pattern:
            return hk_pattern[0].upper()

        # Priority 3: Check for sh/sz prefix codes
        prefix_pattern = re.findall(r'\b((?:sh|sz)\d{6})\b', query_lower)
        if prefix_pattern:
            return prefix_pattern[0]

        # Priority 4: Match Chinese/English stock names
        for name, symbol in self.STOCK_MAPPINGS.items():
            if name in query or name.lower() in query_lower:
                return symbol

        # Priority 5: Check for US ticker (3-4 uppercase letters)
        tickers = re.findall(r'\b([A-Z]{3,4})\b', query)
        if tickers:
            return tickers[0]

        return ''  # No symbol detected

    def _detect_sector(self, query_lower: str) -> str:
        """Detect sector/industry from query."""
        # Count keyword matches for each sector
        sector_scores = {}
        for sector, keywords in self.SECTOR_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                sector_scores[sector] = score

        # Return sector with highest score
        if sector_scores:
            return max(sector_scores, key=sector_scores.get)

        return ''  # No sector detected

    def _detect_query_type(self, query: str, symbol: str, sector: str) -> str:
        """Determine the type of query."""
        query_lower = query.lower()

        # Check for explicit query type indicators
        if any(kw in query_lower for kw in ['大盘', '经济', '宏观', 'gdp', '通胀', '利率']):
            return 'macro_analysis'

        if any(kw in query_lower for kw in ['行业', '板块', '赛道', '领域']) and not symbol:
            return 'industry_analysis'

        if symbol or any(kw in query_lower for kw in ['股票', '股价', '分析', '走势', '估值', '基本面']):
            return 'stock_analysis'

        # Default based on detected params
        if symbol:
            return 'stock_analysis'
        elif sector:
            return 'industry_analysis'
        else:
            return 'stock_analysis'  # Default

    def _calculate_confidence(self, query: str, symbol: str, country: str, sector: str) -> float:
        """Calculate confidence score for the detection."""
        confidence = 0.5  # Base confidence

        # Higher confidence if symbol detected
        if symbol:
            confidence += 0.3

        # Higher confidence if country explicitly mentioned
        if country in ['china', 'hk', 'us']:
            # Check if country keywords are in query
            for kw in self.COUNTRY_KEYWORDS.get(country, []):
                if kw in query.lower() or kw in query:
                    confidence += 0.1
                    break

        # Higher confidence if sector detected
        if sector:
            confidence += 0.1

        # Cap at 0.99
        return min(confidence, 0.99)

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

            # Try to parse JSON from response
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

        # Fallback to rule-based parsing
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
            # For stock analysis, run all agents
            routing['run_macro'] = True
            routing['run_industry'] = True
            routing['run_equity'] = True

        return routing


def get_router_agent() -> InputRouterAgent:
    """Get singleton instance of InputRouterAgent."""
    return InputRouterAgent()
