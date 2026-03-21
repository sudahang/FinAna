"""AI-powered Industry Analyst Agent using Qwen LLM."""

from llm.client import LLMClient, get_llm_client
from data.finance_data import FinancialDataFetcher, get_data_fetcher
from data.schemas import IndustryContext
import json


class IndustryAnalystAgent:
    """
    AI-powered Industry Analyst Agent.

    Uses Qwen LLM to analyze industry sectors with real market data.
    """

    SYSTEM_PROMPT = """你是一位资深行业分析师，专注于 TMT、消费、医疗、高端制造等领域。
你的任务是分析特定行业的投资价值和风险。

请基于提供的数据，分析：
1. 行业增长动力和趋势
2. 竞争格局和进入壁垒
3. 政策环境和监管风险
4. 行业景气度判断

请用专业但易懂的语言输出分析结果。"""

    def __init__(self, llm_client: LLMClient | None = None):
        """
        Initialize the Industry Analyst Agent.

        Args:
            llm_client: Optional LLM client. If None, uses default.
        """
        self.llm = llm_client or get_llm_client()
        self.data_fetcher = get_data_fetcher()
        self.role = "Industry Analyst"
        self.goal = "Analyze industry sectors using real data and AI"

    def analyze(self, sector: str = "科技") -> IndustryContext:
        """
        Perform industry analysis using AI and real data.

        Args:
            sector: Industry sector name

        Returns:
            IndustryContext with AI-generated analysis.
        """
        # Fetch real industry data
        industry_data = self.data_fetcher.get_industry_data(sector)

        # Build prompt for AI analysis
        user_prompt = self._build_analysis_prompt(sector, industry_data)

        # Get AI analysis
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=self.SYSTEM_PROMPT
            )

            # Parse AI response to extract structured data
            return self._parse_ai_response(response, sector, industry_data)

        except Exception as e:
            print(f"AI analysis failed, using fallback: {e}")
            return self._fallback_analysis(sector, industry_data)

    def _build_analysis_prompt(self, sector: str, industry_data: dict) -> str:
        """Build prompt for AI analysis."""
        return f"""请分析{sector}行业的投资价值：

【行业数据】
- 行业增长率：{industry_data.get('sector_growth', 'N/A')}%
- 平均市盈率：{industry_data.get('avg_pe_ratio', 'N/A')}x
- 市场情绪：{industry_data.get('market_sentiment', 'N/A')}
- 政策支持：{industry_data.get('policy_support', 'N/A')}

请提供：
1. 一段行业分析总结（100-200 字）
2. 行业前景判断（positive/neutral/negative）
3. 该行业的主要趋势（列出 3-5 条）
4. 竞争格局描述
5. 监管环境描述

请以 JSON 格式输出：
{{
    "summary": "你的分析总结",
    "outlook": "positive/neutral/negative",
    "trends": ["趋势 1", "趋势 2", "趋势 3"],
    "competitive_landscape": "竞争格局描述",
    "regulatory_environment": "监管环境描述"
}}"""

    def _parse_ai_response(
        self,
        response: str,
        sector: str,
        industry_data: dict
    ) -> IndustryContext:
        """Parse AI response into structured IndustryContext."""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
            else:
                parsed = {}

            return IndustryContext(
                sector_name=sector,
                sector_growth=industry_data.get('sector_growth', 8.0),
                competitive_landscape=parsed.get(
                    'competitive_landscape',
                    f"{sector}行业竞争格局持续演变，龙头企业优势明显。"
                ),
                regulatory_environment=parsed.get(
                    'regulatory_environment',
                    f"当前{sector}行业监管环境总体稳定。"
                ),
                trends=parsed.get('trends', ["行业数字化转型加速"]),
                outlook=parsed.get('outlook', 'neutral'),
                summary=parsed.get('summary', self._generate_fallback_summary(sector, industry_data))
            )

        except json.JSONDecodeError:
            return self._fallback_analysis(sector, industry_data)

    def _fallback_analysis(self, sector: str, industry_data: dict) -> IndustryContext:
        """Generate fallback analysis without AI."""
        growth = industry_data.get('sector_growth', 8.0)
        sentiment = industry_data.get('market_sentiment', 'neutral')

        # Rule-based outlook
        if growth > 10 and sentiment == 'positive':
            outlook = 'positive'
        elif growth < 5 or sentiment == 'negative':
            outlook = 'negative'
        else:
            outlook = 'neutral'

        return IndustryContext(
            sector_name=sector,
            sector_growth=growth,
            competitive_landscape=(
                f"{sector}行业竞争激烈，头部企业凭借规模和技术优势占据主导地位，"
                "新进入者面临较高壁垒。"
            ),
            regulatory_environment=(
                "行业监管框架逐步完善，政策环境总体稳定，"
                "建议关注相关政策变化。"
            ),
            trends=[
                f"{sector}行业数字化转型加速",
                "龙头企业集中度提升",
                "创新和研发投入持续增加"
            ],
            outlook=outlook,
            summary=self._generate_fallback_summary(sector, industry_data)
        )

    def _generate_fallback_summary(self, sector: str, industry_data: dict) -> str:
        """Generate a simple fallback summary."""
        growth = industry_data.get('sector_growth', 8.0)
        sentiment = industry_data.get('market_sentiment', 'neutral')

        return (
            f"{sector}行业当前增长率为{growth}%，市场情绪{sentiment}。"
            f"整体来看，该行业具备长期投资价值，建议关注行业龙头企业的机会。"
        )

    def analyze_with_context(
        self,
        query: str,
        macro_context=None
    ) -> IndustryContext:
        """
        Perform industry analysis with query context.

        Args:
            query: User's investment research query.
            macro_context: Optional macro context.

        Returns:
            IndustryContext containing sector analysis.
        """
        sector = self._extract_sector(query)
        return self.analyze(sector)

    def _extract_sector(self, query: str) -> str:
        """
        Extract sector/industry from user query.

        Uses keyword matching and AI if needed.
        """
        query_lower = query.lower()

        sector_keywords = {
            "科技": ["科技", "软件", "ai", "半导体", "芯片", "互联网", "nvidia", "苹果", "微软"],
            "汽车": ["汽车", "新能源", "ev", "tesla", "特斯拉", "比亚迪", "造车"],
            "医疗": ["医疗", "健康", "医药", "biotech", "生物科技", "器械"],
            "金融": ["金融", "银行", "保险", "券商", " fintech"],
            "消费": ["消费", "零售", "食品", "饮料", "家电", "服装"],
            "能源": ["能源", "石油", "天然气", "光伏", "风电", "电池"]
        }

        for sector, keywords in sector_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return sector

        # Default to technology
        return "科技"
