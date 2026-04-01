"""AI-powered Macro Analyst Agent using Qwen LLM."""

from llm.client import LLMClient, get_llm_client
from data.finance_data import FinancialDataFetcher, get_data_fetcher
from data.schemas import MacroContext
from skills.stock_info.stock_info import get_macro_data
import json


class MacroAnalystAgent:
    """
    AI-powered Macro Economy Analyst Agent.

    Uses Qwen LLM to analyze real macroeconomic data and provide
    intelligent investment context.
    """

    SYSTEM_PROMPT = """你是一位专业的宏观经济分析师，拥有多年华尔街投行研究经验。
你的任务是分析宏观经济数据，为投资决策提供背景分析。

请基于提供的数据，分析：
1. 经济增长态势（GDP、PMI 等）
2. 通胀与货币政策（CPI、利率等）
3. 就业市场状况
4. 整体市场情绪

请用专业但易懂的语言输出分析结果。"""

    def __init__(self, llm_client: LLMClient | None = None):
        """
        Initialize the Macro Analyst Agent.

        Args:
            llm_client: Optional LLM client. If None, uses default.
        """
        self.llm = llm_client or get_llm_client()
        self.data_fetcher = get_data_fetcher()
        self.role = "Macro Economy Analyst"
        self.goal = "Analyze macroeconomic conditions using real data and AI"

    def analyze(self, country: str = "china") -> MacroContext:
        """
        Perform macroeconomic analysis using AI and real data.

        Args:
            country: Country to analyze ('china' or 'us')

        Returns:
            MacroContext with AI-generated analysis.
        """
        # Fetch real macro data using stock_info skill (more reliable)
        try:
            macro_data = get_macro_data(country)
        except Exception as e:
            print(f"Macro data fetch failed, using fallback: {e}")
            macro_data = self.data_fetcher.get_macro_data(country)

        # Build prompt for AI analysis
        user_prompt = self._build_analysis_prompt(macro_data, country)

        # Get AI analysis
        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=self.SYSTEM_PROMPT
            )

            # Parse AI response to extract structured data
            return self._parse_ai_response(response, macro_data)

        except Exception as e:
            print(f"AI analysis failed, using fallback: {e}")
            return self._fallback_analysis(macro_data)

    def _build_analysis_prompt(self, macro_data: dict, country: str) -> str:
        """Build prompt for AI analysis."""
        country_name = "中国" if country.lower() == "china" else "美国"

        return f"""请分析{country_name}当前宏观经济状况：

【宏观经济数据】
- GDP 增长率：{macro_data.get('gdp_growth', 'N/A')}%
- 通胀率（CPI）：{macro_data.get('inflation_rate', 'N/A')}%
- 基准利率：{macro_data.get('interest_rate', 'N/A')}%
- 失业率：{macro_data.get('unemployment_rate', 'N/A')}%
- 制造业 PMI: {macro_data.get('manufacturing_pmi', 'N/A')}
- 消费者信心：{macro_data.get('consumer_confidence', 'N/A')}

请提供：
1. 一段简洁的宏观经济总结（100-200 字）
2. 判断市场情绪（bullish/neutral/bearish）
3. 对投资者的一条关键建议

请以 JSON 格式输出：
{{
    "summary": "你的分析总结",
    "market_sentiment": "bullish/neutral/bearish",
    "recommendation": "关键建议"
}}"""

    def _parse_ai_response(self, response: str, macro_data: dict) -> MacroContext:
        """Parse AI response into structured MacroContext."""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
            else:
                parsed = {}

            return MacroContext(
                gdp_growth=macro_data.get('gdp_growth', 5.0),
                inflation_rate=macro_data.get('inflation_rate', 2.0),
                interest_rate=macro_data.get('interest_rate', 3.5),
                unemployment_rate=macro_data.get('unemployment_rate', 5.0),
                market_sentiment=parsed.get('market_sentiment', 'neutral'),
                summary=parsed.get('summary', self._generate_fallback_summary(macro_data))
            )

        except json.JSONDecodeError:
            return self._fallback_analysis(macro_data)

    def _fallback_analysis(self, macro_data: dict) -> MacroContext:
        """Generate fallback analysis without AI."""
        gdp = macro_data.get('gdp_growth', 5.0)
        inflation = macro_data.get('inflation_rate', 2.0)

        # Simple rule-based sentiment
        if gdp > 4 and inflation < 3:
            sentiment = "bullish"
        elif gdp < 2 or inflation > 5:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        return MacroContext(
            gdp_growth=gdp,
            inflation_rate=inflation,
            interest_rate=macro_data.get('interest_rate', 3.5),
            unemployment_rate=macro_data.get('unemployment_rate', 5.0),
            market_sentiment=sentiment,
            summary=self._generate_fallback_summary(macro_data)
        )

    def _generate_fallback_summary(self, macro_data: dict) -> str:
        """Generate a simple fallback summary."""
        gdp = macro_data.get('gdp_growth', 5.0)
        inflation = macro_data.get('inflation_rate', 2.0)
        rate = macro_data.get('interest_rate', 3.5)

        return (
            f"当前宏观经济数据显示 GDP 增长{gdp}%，通胀率{inflation}%，"
            f"利率水平{rate}%。整体经济环境保持稳定，建议投资者保持适度乐观，"
            f"关注结构性投资机会。"
        )

    def analyze_with_context(self, query: str, country: str = "china") -> MacroContext:
        """
        Analyze macro conditions with query context.

        Args:
            query: User's investment query
            country: Country to analyze

        Returns:
            MacroContext with analysis.
        """
        # Detect country from query if not specified
        if "中国" in query or "A 股" in query or "港股" in query:
            country = "china"
        elif "美股" in query or "美国" in query:
            country = "us"

        return self.analyze(country)
