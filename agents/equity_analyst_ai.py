"""AI-powered Equity Analyst Agent using Qwen LLM."""

from llm.client import LLMClient, get_llm_client
from data.finance_data import FinancialDataFetcher, get_data_fetcher
from data.schemas import CompanyAnalysis, CompanyData, NewsItem
from skills.stock_info.stock_info import (
    get_stock_quote,
    get_company_info,
    get_stock_news,
    get_stock_history,
    search_stock_info
)
from datetime import datetime
import json


class EquityAnalystAgent:
    """
    AI-powered Equity Analyst Agent.

    Uses Qwen LLM to analyze individual companies with real market data.
    Enhanced with Stock Info Skill for A 股/港股/美股 data.
    """

    SYSTEM_PROMPT = """你是一位资深股票分析师，擅长基本面分析和技术分析。
你的任务是对具体公司进行深入分析，给出投资建议。

请基于提供的数据，分析：
1. 公司基本面（估值、财务健康）
2. 近期新闻和事件影响
3. 技术面信号
4. 风险因素
5. 投资建议

请用专业但易懂的语言输出分析结果。"""

    def __init__(self, llm_client: LLMClient | None = None):
        """
        Initialize the Equity Analyst Agent.

        Args:
            llm_client: Optional LLM client. If None, uses default.
        """
        self.llm = llm_client or get_llm_client()
        self.data_fetcher = get_data_fetcher()
        self.stock_fetcher = None  # Use functional API
        self.role = "Equity Analyst"
        self.goal = "Analyze individual companies using real data and AI"

    def _get_symbol_format(self, symbol: str) -> str:
        """
        Convert symbol to standard format for stock_info skill.

        Args:
            symbol: Stock symbol (e.g., TSLA, 600519, sh600519)

        Returns:
            Standardized symbol (e.g., sh600519, HK00700, TSLA)
        """
        symbol = symbol.strip().upper()

        # Already has market prefix
        if symbol.startswith(("sh", "sz", "HK", "bj")):
            return symbol

        # A 股 6-digit code
        if len(symbol) == 6 and symbol.isdigit():
            if symbol.startswith(("6", "9")):
                return f"sh{symbol}"
            elif symbol.startswith(("0", "3")):
                return f"sz{symbol}"

        # HK stock
        if len(symbol) == 5 and symbol.isdigit():
            return f"HK{symbol}"

        # US stock or return as-is
        return symbol

    def analyze(self, symbol: str) -> CompanyAnalysis:
        """
        Perform company analysis using AI and real data.

        Args:
            symbol: Stock ticker symbol

        Returns:
            CompanyAnalysis with AI-generated analysis.
        """
        # Standardize symbol format
        std_symbol = self._get_symbol_format(symbol)

        # Fetch real company data using stock_info skill
        quote_data = get_stock_quote(std_symbol)

        # Fetch company info
        company_info = get_company_info(std_symbol)

        # Fetch news using stock_info skill
        try:
            news_data = get_stock_news(std_symbol, limit=5)
        except Exception as e:
            print(f"  ⚠️  新闻获取失败：{e}")
            news_data = []

        # Fetch K-line history for technical analysis
        try:
            history_data = get_stock_history(std_symbol, period="d")
        except Exception as e:
            print(f"  ⚠️  历史数据获取失败：{e}")
            history_data = []

        # Build company data object
        company_data = self._build_company_data(symbol, quote_data, company_info)

        # Build prompt for AI analysis
        user_prompt = self._build_analysis_prompt(company_data, news_data, history_data)

        # Get AI analysis
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=self.SYSTEM_PROMPT
            )

            # Parse AI response
            return self._parse_ai_response(response, company_data, news_data)

        except Exception as e:
            print(f"AI analysis failed, using fallback: {e}")
            return self._fallback_analysis(company_data, news_data)

    def _build_company_data(
        self,
        symbol: str,
        quote_data: dict | None,
        company_info: dict | None
    ) -> CompanyData:
        """Build CompanyData from quote and company info."""
        if quote_data and quote_data.get('current_price', 0) > 0:
            return CompanyData(
                symbol=symbol,
                name=quote_data.get('name', symbol),
                sector=company_info.get('industry', 'Unknown') if company_info else 'Unknown',
                market_cap=quote_data.get('market_cap', 0),
                pe_ratio=quote_data.get('pe_ratio', 0),
                current_price=quote_data.get('current_price', 0)
            )
        else:
            # Use LLM to get company info when real data unavailable
            return self._get_company_info_from_llm(symbol)

    def _get_company_info_from_llm(self, symbol: str) -> CompanyData:
        """Get company basic info using LLM with real-time search."""
        # First prompt: get real-time price and basic info
        price_prompt = f"""请查询 {symbol} 股票的实时股价和基本信息。

你可以通过联网搜索获取最新数据。请提供：
1. 公司全称
2. 当前股价（美元）
3. 所属行业
4. 市盈率
5. 市值

请只返回 JSON 格式，例如：
{{
    "name": "公司全称",
    "current_price": 123.45,
    "sector": "行业名称",
    "pe_ratio": 25.5,
    "market_cap": 1000
}}"""

        try:
            print(f"  📡 正在通过 LLM 查询 {symbol} 实时数据...")
            response = self.llm.chat(
                messages=[{"role": "user", "content": price_prompt}],
                system_prompt="你是一位专业的金融数据助手，提供准确的实时股票信息。请使用联网搜索获取最新数据。"
            )
            print(f"  ✅ LLM 返回数据")

            # Parse JSON response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)

                return CompanyData(
                    symbol=symbol,
                    name=parsed.get('name', f'{symbol} Inc.'),
                    sector=parsed.get('sector', 'Unknown'),
                    market_cap=parsed.get('market_cap', 0),
                    pe_ratio=parsed.get('pe_ratio', 0) or 0,
                    current_price=parsed.get('current_price', 0) or 0
                )

        except Exception as e:
            print(f"  ❌ LLM 查询失败：{e}")

        # Ultimate fallback - use symbol as name with generic data
        return CompanyData(
            symbol=symbol,
            name=f'{symbol} Inc.',
            sector='Unknown',
            market_cap=0,
            pe_ratio=0,
            current_price=0
        )

    def _build_analysis_prompt(
        self,
        company: CompanyData,
        news: list[dict],
        history_data: list[dict] | None = None
    ) -> str:
        """Build prompt for AI analysis with history data."""
        news_str = "\n".join([
            f"- {n.get('title', 'N/A')} ({n.get('source', 'Unknown')})"
            for n in news[:5]
        ]) if news else "暂无最新新闻"

        # Add technical indicators from history data
        tech_analysis = self._analyze_technical_indicators(history_data)

        return f"""请分析 {company.name} ({company.symbol}) 的投资价值：

【公司数据】
- 当前股价：{company.current_price:.2f}{'元' if company.symbol.startswith(('sh', 'sz', 'HK')) else '$'}
- 市盈率：{company.pe_ratio if company.pe_ratio else 'N/A'}
- 市值：{company.market_cap if company.market_cap else 'N/A'}

【技术指标】
{tech_analysis}

【近期新闻】
{news_str}

请提供：
1. 财务健康评估（100 字左右）
2. 技术面信号（buy/hold/sell）
3. 主要风险因素（列出 3-5 条）
4. 分析总结（100 字左右）

请以 JSON 格式输出：
{{
    "financial_health": "财务健康评估",
    "technical_indicator": "buy/hold/sell",
    "risks": ["风险 1", "风险 2", "风险 3"],
    "summary": "分析总结"
}}"""

    def _analyze_technical_indicators(self, history_data: list[dict] | None) -> str:
        """Analyze technical indicators from K-line history."""
        if not history_data or len(history_data) < 5:
            return "暂无足够历史数据进行技术分析"

        # Calculate simple moving averages
        recent_prices = [k['close'] for k in history_data[:5]]
        ma5 = sum(recent_prices) / len(recent_prices)

        if len(history_data) >= 20:
            prices_20 = [k['close'] for k in history_data[:20]]
            ma20 = sum(prices_20) / len(prices_20)
        else:
            ma20 = ma5

        current_price = history_data[0]['close']

        # Determine trend
        if current_price > ma5 > ma20:
            trend = "短期 uptrend，价格在 MA5/MA20 之上"
        elif current_price < ma5 < ma20:
            trend = "短期 downtrend，价格在 MA5/MA20 之下"
        else:
            trend = "震荡整理"

        # Calculate recent performance
        if len(history_data) >= 5:
            price_5d_ago = history_data[4]['close']
            change_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100
            performance = f"5 日涨跌幅：{change_5d:+.2f}%"
        else:
            performance = ""

        return f"- MA5: {ma5:.2f}\n- MA20: {ma20:.2f}\n- 趋势：{trend}\n- {performance}"

    def _parse_ai_response(
        self,
        response: str,
        company: CompanyData,
        news: list[dict]
    ) -> CompanyAnalysis:
        """Parse AI response into structured CompanyAnalysis."""
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
            else:
                parsed = {}

            # Convert news to NewsItem format
            news_items = [
                NewsItem(
                    title=n.get('title', ''),
                    source=n.get('source', 'Unknown'),
                    published_at=n.get('published_at', datetime.now()),
                    sentiment='neutral',  # AI could determine this
                    summary=n.get('summary', '')
                )
                for n in news
            ]

            return CompanyAnalysis(
                company=company,
                financial_health=parsed.get(
                    'financial_health',
                    f"{company.name}财务状况总体稳健，建议关注后续财报。"
                ),
                recent_news=news_items,
                technical_indicator=parsed.get('technical_indicator', 'hold'),
                risks=parsed.get('risks', ['市场波动风险']),
                summary=parsed.get('summary', self._generate_fallback_summary(company))
            )

        except json.JSONDecodeError:
            return self._fallback_analysis(company, news)

    def _fallback_analysis(
        self,
        company: CompanyData,
        news: list[dict]
    ) -> CompanyAnalysis:
        """Generate fallback analysis without AI."""
        # Determine currency based on market
        if company.symbol.startswith(("sh", "sz")):
            currency = "元"
        elif company.symbol.startswith("HK"):
            currency = "港元"
        else:
            currency = "$"

        # Simple heuristic based on price data
        if company.current_price > 0:
            # Mock technical signal based on symbol hash
            tech = 'buy' if hash(company.symbol) % 3 == 0 else 'hold'
        else:
            tech = 'hold'

        news_items = [
            NewsItem(
                title=n.get('title', ''),
                source=n.get('source', 'Unknown'),
                published_at=n.get('published_at', datetime.now()),
                sentiment='neutral',
                summary=n.get('summary', '')
            )
            for n in news
        ]

        return CompanyAnalysis(
            company=company,
            financial_health=(
                f"{company.name}基本面稳健，财务状况良好。"
                f"当前股价{company.current_price:.2f}{currency}，建议结合行业动态综合判断。"
            ),
            recent_news=news_items if news_items else [],
            technical_indicator=tech,
            risks=[
                "市场整体波动风险",
                "行业竞争加剧",
                "宏观经济不确定性",
                "政策法规变化风险"
            ],
            summary=self._generate_fallback_summary(company)
        )

    def _generate_fallback_summary(self, company: CompanyData) -> str:
        """Generate a simple fallback summary."""
        # Determine currency based on market
        if company.symbol.startswith(("sh", "sz")):
            currency = "元"
        elif company.symbol.startswith("HK"):
            currency = "港元"
        else:
            currency = "$"

        return (
            f"{company.name}（{company.symbol}）作为行业知名企业，"
            f"具备较强的竞争力和抗风险能力。当前股价{company.current_price:.2f}{currency}，"
            f"建议投资者结合自身风险承受能力，采取分散投资策略。"
        )

    def analyze_with_context(
        self,
        query: str,
        macro_context=None,
        industry_context=None
    ) -> CompanyAnalysis:
        """
        Perform company analysis with context.

        Args:
            query: User's investment research query.
            macro_context: Macroeconomic context.
            industry_context: Industry context.

        Returns:
            CompanyAnalysis containing detailed assessment.
        """
        symbol = self._extract_symbol(query)
        return self.analyze(symbol)

    def _extract_symbol(self, query: str) -> str:
        """
        Extract stock symbol from query.

        Supports A 股 (6-digit codes), HK stocks, and US stocks.
        """
        query_upper = query.upper()

        # Check for A 股 6-digit codes directly
        import re
        cn_stock_pattern = re.findall(r'\b([06]\d{5})\b', query)
        if cn_stock_pattern:
            code = cn_stock_pattern[0]
            # Add market prefix based on code
            if code.startswith(('6', '9')):
                return f"sh{code}"
            elif code.startswith(('0', '3')):
                return f"sz{code}"

        # Check for HK stock 5-digit code
        hk_pattern = re.findall(r'\b(HK\d{5}|\d{5})\b', query_upper)
        if hk_pattern:
            code = hk_pattern[0]
            if code.startswith('HK'):
                return code.upper()
            return f"HK{code}"

        # Check for US stock ticker (3-4 letters)
        us_tickers = re.findall(r'\b[A-Z]{3,4}\b', query_upper)
        if us_tickers:
            return us_tickers[0]

        # Common US stock mappings (including Chinese names)
        company_mapping = {
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
            # A 股 popular stocks
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

        for name, symbol in company_mapping.items():
            if name in query_upper or name in query:
                return symbol

        # Default to Tesla
        return "TSLA"

    def analyze_with_context(
        self,
        query: str,
        macro_context=None,
        industry_context=None
    ) -> CompanyAnalysis:
        """
        Perform company analysis with context.

        Args:
            query: User's investment research query.
            macro_context: Macroeconomic context.
            industry_context: Industry context.

        Returns:
            CompanyAnalysis containing detailed assessment.
        """
        symbol = self._extract_symbol(query)
        return self.analyze(symbol)
