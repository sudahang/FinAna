"""Report Synthesizer Agent."""

from data.schemas import ResearchReport, MacroContext, IndustryContext, CompanyAnalysis


class ReportSynthesizerAgent:
    """
    Agent responsible for synthesizing analysis into a final research report.

    This agent combines inputs from macro, industry, and equity analysts
    into a coherent, structured investment research report.
    """

    def __init__(self, llm_config: dict | None = None):
        """
        Initialize the Report Synthesizer Agent.

        Args:
            llm_config: Optional LLM configuration for future enhancement.
                       Currently uses template-based synthesis for demo purposes.
        """
        self.role = "Report Synthesizer"
        self.goal = "Synthesize multi-agent analysis into coherent investment research report"
        self.llm_config = llm_config

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
            macro_context: Macroeconomic analysis from macro analyst.
            industry_context: Industry analysis from industry analyst.
            company_analysis: Company analysis from equity analyst.

        Returns:
            ResearchReport containing complete investment research report.
        """
        # Generate investment thesis
        investment_thesis = self._generate_thesis(
            macro_context, industry_context, company_analysis
        )

        # Generate recommendation
        recommendation, target_price = self._generate_recommendation(
            company_analysis, industry_context
        )

        # Generate full markdown report
        full_report = self._generate_report(
            query=query,
            macro_context=macro_context,
            industry_context=industry_context,
            company_analysis=company_analysis,
            investment_thesis=investment_thesis,
            recommendation=recommendation,
            target_price=target_price
        )

        return ResearchReport(
            query=query,
            macro_analysis=macro_context,
            industry_analysis=industry_context,
            company_analysis=company_analysis,
            investment_thesis=investment_thesis,
            recommendation=recommendation,
            target_price=target_price,
            time_horizon="3-6 months",
            full_report=full_report
        )

    def _generate_thesis(
        self,
        macro: MacroContext,
        industry: IndustryContext,
        company: CompanyAnalysis
    ) -> str:
        """Generate core investment thesis."""
        thesis_parts = []

        # Macro perspective
        if macro.market_sentiment == "bullish":
            thesis_parts.append(
                f"Favorable macroeconomic conditions with {macro.gdp_growth}% GDP growth "
                f"support risk asset appreciation."
            )
        elif macro.market_sentiment == "bearish":
            thesis_parts.append(
                f"Challenging macroeconomic backdrop with {macro.inflation_rate}% inflation "
                f"and {macro.interest_rate}% interest rates warrant caution."
            )
        else:
            thesis_parts.append(
                "Neutral macroeconomic environment provides stable backdrop for stock selection."
            )

        # Industry perspective
        thesis_parts.append(
            f"The {industry.sector_name} sector shows {industry.outlook} outlook with "
            f"{industry.sector_growth}% growth rate."
        )

        # Company perspective
        thesis_parts.append(
            f"{company.company.name} demonstrates {company.technical_indicator} signals "
            f"with {company.company.pe_ratio}x P/E ratio."
        )

        return " ".join(thesis_parts)

    def _generate_recommendation(
        self,
        company: CompanyAnalysis,
        industry: IndustryContext
    ) -> tuple[str, float | None]:
        """Generate investment recommendation and target price."""
        # Simple logic based on technical indicator and industry outlook
        technical = company.technical_indicator

        if technical == "buy" and industry.outlook == "positive":
            recommendation = "buy"
            # Calculate target price with 15% upside
            target_price = company.company.current_price * 1.15
        elif technical == "buy" or industry.outlook == "positive":
            recommendation = "buy"
            target_price = company.company.current_price * 1.08
        elif technical == "sell" or industry.outlook == "negative":
            recommendation = "sell"
            target_price = company.company.current_price * 0.85
        else:
            recommendation = "hold"
            target_price = company.company.current_price * 1.02

        return recommendation, round(target_price, 2)

    def _generate_report(
        self,
        query: str,
        macro_context: MacroContext,
        industry_context: IndustryContext,
        company_analysis: CompanyAnalysis,
        investment_thesis: str,
        recommendation: str,
        target_price: float | None
    ) -> str:
        """Generate full markdown-formatted research report."""
        report = f"""# Investment Research Report

**Query:** {query}

---

## Executive Summary

**Recommendation:** {recommendation.upper()}
**Target Price:** ${target_price:.2f} (if applicable)
**Time Horizon:** 3-6 months

{investment_thesis}

---

## Macroeconomic Analysis

| Indicator | Value |
|-----------|-------|
| GDP Growth | {macro_context.gdp_growth}% |
| Inflation Rate | {macro_context.inflation_rate}% |
| Interest Rate | {macro_context.interest_rate}% |
| Unemployment Rate | {macro_context.unemployment_rate}% |
| Market Sentiment | {macro_context.market_sentiment} |

{macro_context.summary}

---

## Industry Analysis: {industry_context.sector_name}

| Metric | Value |
|--------|-------|
| Sector Growth | {industry_context.sector_growth}% |
| Outlook | {industry_context.outlook} |

### Key Industry Trends
"""
        for trend in industry_context.trends:
            report += f"\n- {trend}"

        report += f"""

### Competitive Landscape
{industry_context.competitive_landscape}

### Regulatory Environment
{industry_context.regulatory_environment}

---

## Company Analysis: {company_analysis.company.name} ({company_analysis.company.symbol})

| Metric | Value |
|--------|-------|
| Market Cap | ${company_analysis.company.market_cap:.1f}B |
| P/E Ratio | {company_analysis.company.pe_ratio}x |
| Current Price | ${company_analysis.company.current_price:.2f} |
| Technical Signal | {company_analysis.technical_indicator} |

### Financial Health
{company_analysis.financial_health}

### Recent News
"""
        for news in company_analysis.recent_news:
            sentiment_emoji = {"positive": "📈", "neutral": "➖", "negative": "📉"}.get(
                news.sentiment, "•"
            )
            report += f"\n{sentiment_emoji} **{news.title}** ({news.source})\n"
            report += f"\n   {news.summary}\n"

        report += "\n### Risk Factors\n"
        for risk in company_analysis.risks:
            report += f"\n- {risk}"

        report += f"""

---

## Investment Conclusion

Based on our multi-factor analysis combining macroeconomic conditions, industry dynamics,
and company-specific fundamentals, we issue a **{recommendation.upper()}** recommendation
for {company_analysis.company.symbol}.

**Key Considerations:**
1. Macroeconomic environment: {macro_context.market_sentiment}
2. Industry outlook: {industry_context.outlook}
3. Company technical signal: {company_analysis.technical_indicator}

---

*This report is generated for demonstration purposes only and should not be considered
as financial advice. Please consult with a qualified financial advisor before making
investment decisions.*
"""

        return report
