"""AI-powered Report Synthesizer Agent using Qwen LLM."""

from llm.client import LLMClient, get_llm_client
from data.schemas import ResearchReport, MacroContext, IndustryContext, CompanyAnalysis
import json


class ReportSynthesizerAgent:
    """
    AI-powered Report Synthesizer Agent.

    Uses Qwen LLM to synthesize multi-agent analysis into
    coherent, professional investment research reports.
    """

    SYSTEM_PROMPT = """你是一位资深投资策略师，负责整合宏观、行业和个股分析，
生成专业的投资研究报告。

你的报告应该：
1. 结构清晰，包含Executive Summary、宏观分析、行业分析、公司分析、投资结论
2. 语言专业但不晦涩，适合个人投资者阅读
3. 给出明确的投资建议（买入/持有/卖出）
4. 包含目标价格和时间 horizon
5. 充分揭示风险

请用 Markdown 格式输出完整报告。"""

    def __init__(self, llm_client: LLMClient | None = None):
        """
        Initialize the Report Synthesizer Agent.

        Args:
            llm_client: Optional LLM client. If None, uses default.
        """
        self.llm = llm_client or get_llm_client()
        self.role = "Report Synthesizer"
        self.goal = "Synthesize multi-agent analysis into professional reports"

    def synthesize(
        self,
        query: str,
        macro_context: MacroContext,
        industry_context: IndustryContext,
        company_analysis: CompanyAnalysis
    ) -> ResearchReport:
        """
        Synthesize analysis from all agents into final report.

        Args:
            query: Original user query.
            macro_context: Macroeconomic analysis.
            industry_context: Industry analysis.
            company_analysis: Company analysis.

        Returns:
            ResearchReport containing complete investment report.
        """
        return self.synthesize_partial(
            query=query,
            macro_context=macro_context,
            industry_context=industry_context,
            company_analysis=company_analysis,
            query_type="stock_analysis",
        )

    def synthesize_partial(
        self,
        query: str,
        macro_context: MacroContext | None = None,
        industry_context: IndustryContext | None = None,
        company_analysis: CompanyAnalysis | None = None,
        query_type: str = "stock_analysis",
    ) -> ResearchReport:
        """
        Synthesize analysis with partial contexts for flexible report types.

        Args:
            query: Original user query.
            macro_context: Optional macroeconomic analysis.
            industry_context: Optional industry analysis.
            company_analysis: Optional company analysis.
            query_type: Type of analysis requested.

        Returns:
            ResearchReport containing the investment report.
        """
        user_prompt = self._build_partial_synthesis_prompt(
            query, macro_context, industry_context, company_analysis, query_type
        )

        try:
            response = self.llm.chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=self.SYSTEM_PROMPT
            )

            recommendation, target_price = self._extract_partial_recommendation(
                response, company_analysis
            )

            return ResearchReport(
                query=query,
                macro_analysis=macro_context,
                industry_analysis=industry_context,
                company_analysis=company_analysis,
                investment_thesis=self._extract_thesis(response),
                recommendation=recommendation,
                target_price=target_price,
                time_horizon="3-6 个月",
                full_report=response
            )

        except Exception as e:
            print(f"AI synthesis failed, using fallback: {e}")
            return self._fallback_partial_synthesize(
                query, macro_context, industry_context, company_analysis, query_type
            )

    def _build_synthesis_prompt(
        self,
        query: str,
        macro: MacroContext,
        industry: IndustryContext,
        company: CompanyAnalysis
    ) -> str:
        """Build prompt for AI synthesis."""
        return self._build_partial_synthesis_prompt(query, macro, industry, company, "stock_analysis")

    def _build_partial_synthesis_prompt(
        self,
        query: str,
        macro: MacroContext | None,
        industry: IndustryContext | None,
        company: CompanyAnalysis | None,
        query_type: str = "stock_analysis",
    ) -> str:
        """Build prompt for AI synthesis with partial contexts."""
        sections = [f"【用户查询】\n{query}\n"]

        if macro:
            sections.append(f"""【宏观经济分析】
- GDP 增长：{macro.gdp_growth}%
- 通胀率：{macro.inflation_rate}%
- 利率：{macro.interest_rate}%
- 失业率：{macro.unemployment_rate}%
- 市场情绪：{macro.market_sentiment}
- 分析总结：{macro.summary}
""")

        if industry:
            trends_str = ", ".join(industry.trends[:3]) if industry.trends else "无"
            sections.append(f"""【行业分析 - {industry.sector_name}】
- 行业增长：{industry.sector_growth}%
- 行业前景：{industry.outlook}
- 主要趋势：{trends_str}
- 竞争格局：{industry.competitive_landscape}
- 监管环境：{industry.regulatory_environment}
""")

        if company:
            risks_str = ", ".join(company.risks[:3]) if company.risks else "无"
            sections.append(f"""【公司分析 - {company.company.name} ({company.company.symbol})】
- 当前股价：${company.company.current_price:.2f}
- 财务健康：{company.financial_health}
- 技术信号：{company.technical_indicator}
- 主要风险：{risks_str}
- 分析总结：{company.summary}
""")

        report_requirements = {
            "macro_analysis": "1. 执行摘要\n2. 宏观经济分析\n3. 投资结论与风险提示",
            "industry_analysis": "1. 执行摘要\n2. 宏观经济概况（如适用）\n3. 行业分析\n4. 投资结论与风险提示",
            "stock_analysis": "1. 执行摘要（含投资建议和目标价）\n2. 宏观经济分析\n3. 行业分析\n4. 公司分析\n5. 投资结论与风险提示",
        }

        requirements = report_requirements.get(query_type, report_requirements["stock_analysis"])

        return "\n".join(sections) + f"""
请生成一份完整的 Markdown 格式投资研究报告，包含：
{requirements}

报告应当专业、全面，适合个人投资者参考。"""

    def _extract_recommendation(
        self,
        response: str,
        company: CompanyAnalysis
    ) -> tuple[str, float | None]:
        """Extract recommendation and target price from AI response."""
        return self._extract_partial_recommendation(response, company)

    def _extract_partial_recommendation(
        self,
        response: str,
        company: CompanyAnalysis | None
    ) -> tuple[str, float | None]:
        """Extract recommendation and target price from AI response with optional company."""
        # Try to extract using patterns
        response_lower = response.lower()

        # Determine recommendation
        if "买入" in response or "buy" in response_lower or "推荐买入" in response:
            recommendation = "buy"
        elif "卖出" in response or "sell" in response_lower or "推荐卖出" in response:
            recommendation = "sell"
        else:
            recommendation = "hold"

        # Try to extract target price
        import re
        price_match = re.search(r'目标价 [格]？[:：]?\s*\$?(\d+\.?\d*)', response)
        if price_match:
            target_price = float(price_match.group(1))
        elif company and company.company.current_price > 0:
            current = company.company.current_price
            if recommendation == "buy":
                target_price = current * 1.15
            elif recommendation == "sell":
                target_price = current * 0.85
            else:
                target_price = current * 1.02
        else:
            target_price = None

        return recommendation, target_price

    def _extract_thesis(self, response: str) -> str:
        """Extract investment thesis from AI response."""
        # Look for key thesis sections
        keywords = ["投资论点", "投资逻辑", "核心观点", "thesis", "summary"]
        for keyword in keywords:
            if keyword in response.lower():
                # Extract paragraph around keyword
                idx = response.lower().find(keyword)
                start = max(0, idx - 50)
                end = min(len(response), idx + 200)
                return response[start:end].strip()

        # Fallback: return first substantial paragraph
        paragraphs = response.split('\n\n')
        for p in paragraphs:
            if len(p) > 50:
                return p.strip()

        return "基于综合分析，生成投资建议。"

    def _fallback_synthesize(
        self,
        query: str,
        macro: MacroContext,
        industry: IndustryContext,
        company: CompanyAnalysis
    ) -> ResearchReport:
        """Generate fallback report without AI."""
        return self._fallback_partial_synthesize(query, macro, industry, company, "stock_analysis")

    def _fallback_partial_synthesize(
        self,
        query: str,
        macro: MacroContext | None,
        industry: IndustryContext | None,
        company: CompanyAnalysis | None,
        query_type: str = "stock_analysis",
    ) -> ResearchReport:
        """Generate fallback report without AI, supporting partial contexts."""
        # Determine recommendation based on available signals
        signals = []
        if macro:
            if macro.market_sentiment == "bullish":
                signals.append(1)
            elif macro.market_sentiment == "bearish":
                signals.append(-1)

        if industry:
            if industry.outlook == "positive":
                signals.append(1)
            elif industry.outlook == "negative":
                signals.append(-1)

        if company:
            if company.technical_indicator == "buy":
                signals.append(1)
            elif company.technical_indicator == "sell":
                signals.append(-1)

        avg_signal = sum(signals) / len(signals) if signals else 0

        if avg_signal > 0.5:
            recommendation = "buy"
        elif avg_signal < -0.5:
            recommendation = "sell"
        else:
            recommendation = "hold"

        # Calculate target price
        if company and company.company.current_price > 0:
            current = company.company.current_price
            if recommendation == "buy":
                target_price = current * 1.15
            elif recommendation == "sell":
                target_price = current * 0.85
            else:
                target_price = current * 1.02
        else:
            target_price = None

        # Generate template report
        full_report = self._generate_partial_template_report(
            query, macro, industry, company, recommendation, target_price, query_type
        )

        # Build investment thesis from available analyses
        thesis_parts = []
        if macro:
            thesis_parts.append(f"宏观{macro.market_sentiment}")
        if industry:
            thesis_parts.append(f"行业{industry.outlook}")
        if company:
            thesis_parts.append(f"公司{company.technical_indicator}")
        investment_thesis = "、".join(thesis_parts) + "的综合判断" if thesis_parts else "基于现有分析，生成投资建议"

        return ResearchReport(
            query=query,
            macro_analysis=macro,
            industry_analysis=industry,
            company_analysis=company,
            investment_thesis=investment_thesis,
            recommendation=recommendation,
            target_price=round(target_price, 2) if target_price else None,
            time_horizon="3-6 个月",
            full_report=full_report
        )

    def _generate_template_report(
        self,
        query: str,
        macro: MacroContext,
        industry: IndustryContext,
        company: CompanyAnalysis,
        recommendation: str,
        target_price: float
    ) -> str:
        """Generate a template-based report."""
        return self._generate_partial_template_report(
            query, macro, industry, company, recommendation, target_price, "stock_analysis"
        )

    def _generate_partial_template_report(
        self,
        query: str,
        macro: MacroContext | None,
        industry: IndustryContext | None,
        company: CompanyAnalysis | None,
        recommendation: str,
        target_price: float | None,
        query_type: str = "stock_analysis",
    ) -> str:
        """Generate a template-based report with partial contexts."""
        rec_text = {"buy": "买入", "hold": "持有", "sell": "卖出"}[recommendation]
        target_price_str = f"${target_price:.2f}" if target_price else "N/A"

        sections = [f"""# 投资研究报告

**查询**: {query}

---

## 执行摘要

**投资建议**: {rec_text}
**目标价格**: {target_price_str}
**时间 horizon**: 3-6 个月
"""]

        if macro:
            sections.append(f"""
---

## 宏观经济分析

| 指标 | 数值 |
|------|------|
| GDP 增长 | {macro.gdp_growth}% |
| 通胀率 | {macro.inflation_rate}% |
| 利率 | {macro.interest_rate}% |
| 失业率 | {macro.unemployment_rate}% |
| 市场情绪 | {macro.market_sentiment} |

{macro.summary}
""")

        if industry:
            trends_lines = "\n".join([f"- {t}" for t in industry.trends]) if industry.trends else "无"
            sections.append(f"""
---

## 行业分析：{industry.sector_name}

| 指标 | 数值 |
|------|------|
| 行业增长 | {industry.sector_growth}% |
| 行业前景 | {industry.outlook} |

### 主要趋势
{trends_lines}

### 竞争格局
{industry.competitive_landscape}

### 监管环境
{industry.regulatory_environment}
""")

        if company:
            risks_lines = "\n".join([f"- {r}" for r in company.risks]) if company.risks else "无"
            sections.append(f"""
---

## 公司分析：{company.company.name} ({company.company.symbol})

| 指标 | 数值 |
|------|------|
| 当前股价 | ${company.company.current_price:.2f} |
| 技术信号 | {company.technical_indicator} |

### 财务健康
{company.financial_health}

### 风险因素
{risks_lines}
""")

        # Investment conclusion
        conclusion_parts = []
        if macro:
            conclusion_parts.append(f"宏观环境：{macro.market_sentiment}")
        if industry:
            conclusion_parts.append(f"行业前景：{industry.outlook}")
        if company:
            conclusion_parts.append(f"公司信号：{company.technical_indicator}")
            conclusion_text = f"基于以上分析，我们对{company.company.name}给出**{rec_text}**评级。"
        else:
            conclusion_text = f"基于以上分析，给出**{rec_text}**评级。"

        conclusion_factors = "\n".join([f"{i+1}. {f}" for i, f in enumerate(conclusion_parts)])

        sections.append(f"""
---

## 投资结论

{conclusion_text}

**主要考虑因素**：
{conclusion_factors}

---

*免责声明：本报告仅供参考，不构成投资建议。投资有风险，决策需谨慎。*
""")

        return "\n".join(sections)
