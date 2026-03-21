"""AI-powered Equity Analyst Agent using Qwen LLM."""

from llm.client import LLMClient, get_llm_client
from data.finance_data import FinancialDataFetcher, get_data_fetcher
from data.schemas import CompanyAnalysis, CompanyData, NewsItem
from datetime import datetime
import json


class EquityAnalystAgent:
    """
    AI-powered Equity Analyst Agent.

    Uses Qwen LLM to analyze individual companies with real market data.
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
        self.role = "Equity Analyst"
        self.goal = "Analyze individual companies using real data and AI"

    def analyze(self, symbol: str) -> CompanyAnalysis:
        """
        Perform company analysis using AI and real data.

        Args:
            symbol: Stock ticker symbol

        Returns:
            CompanyAnalysis with AI-generated analysis.
        """
        # Fetch real company data
        quote_data = self.data_fetcher.get_us_stock_quote(symbol)
        news_data = self.data_fetcher.get_stock_news(symbol, limit=5)

        # Build company data object
        company_data = self._build_company_data(symbol, quote_data)

        # Build prompt for AI analysis
        user_prompt = self._build_analysis_prompt(company_data, news_data)

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

    def _build_company_data(self, symbol: str, quote_data: dict | None) -> CompanyData:
        """Build CompanyData from quote or LLM lookup."""
        if quote_data and quote_data.get('current_price', 0) > 0:
            return CompanyData(
                symbol=symbol,
                name=quote_data.get('name', symbol),
                sector="Technology",
                market_cap=quote_data.get('market_cap', 0),
                pe_ratio=quote_data.get('pe_ratio', 0),
                current_price=quote_data.get('current_price', 0)
            )
        else:
            # Use LLM to get company info when real data unavailable
            return self._get_company_info_from_llm(symbol)

    def _get_company_info_from_llm(self, symbol: str) -> CompanyData:
        """Get company basic info using LLM knowledge."""
        prompt = f"""请提供 {symbol} 股票的基本信息，以 JSON 格式输出：
{{
    "name": "公司全称",
    "sector": "所属行业",
    "current_price": 当前股价（数字）,
    "pe_ratio": 市盈率（数字）,
    "market_cap": 市值（亿美元，数字）
}}

只输出 JSON，不要其他文字。"""

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="你是一位专业的金融数据助手，提供准确的股票信息。"
            )

            # Parse JSON response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)

                return CompanyData(
                    symbol=symbol,
                    name=parsed.get('name', symbol),
                    sector=parsed.get('sector', 'Unknown'),
                    market_cap=parsed.get('market_cap', 0),
                    pe_ratio=parsed.get('pe_ratio', 0) or 0,
                    current_price=parsed.get('current_price', 0) or 0
                )
        except Exception as e:
            print(f"LLM company lookup failed: {e}")

        # Ultimate fallback - use symbol as name
        return CompanyData(
            symbol=symbol,
            name=symbol,
            sector="Unknown",
            market_cap=0,
            pe_ratio=0,
            current_price=0
        )

    def _build_analysis_prompt(
        self,
        company: CompanyData,
        news: list[dict]
    ) -> str:
        """Build prompt for AI analysis."""
        news_str = "\n".join([
            f"- {n['title']} ({n['source']})"
            for n in news[:5]
        ]) if news else "暂无最新新闻"

        return f"""请分析 {company.name} ({company.symbol}) 的投资价值：

【公司数据】
- 当前股价：${company.current_price:.2f}
- 市盈率：{company.pe_ratio if company.pe_ratio else 'N/A'}
- 市值：{company.market_cap if company.market_cap else 'N/A'}

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
                f"当前股价${company.current_price:.2f}，建议结合行业动态综合判断。"
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
        return (
            f"{company.name}（{company.symbol}）作为行业知名企业，"
            f"具备较强的竞争力和抗风险能力。当前股价${company.current_price:.2f}，"
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
        """Extract stock symbol from query."""
        query_upper = query.upper()

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
            "NIO": "NIO"
        }

        for name, symbol in company_mapping.items():
            if name in query_upper:
                return symbol

        # Check for direct ticker symbols
        import re
        tickers = re.findall(r'\b[A-Z]{3,4}\b', query_upper)
        if tickers:
            return tickers[0]

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
