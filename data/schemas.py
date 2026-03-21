"""Data schemas for inter-agent communication."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MacroContext(BaseModel):
    """Macro economy analysis context."""

    gdp_growth: float = Field(description="GDP growth rate percentage")
    inflation_rate: float = Field(description="Inflation rate percentage")
    interest_rate: float = Field(description="Central bank interest rate")
    unemployment_rate: float = Field(description="Unemployment rate percentage")
    market_sentiment: str = Field(description="Overall market sentiment: bullish/neutral/bearish")
    summary: str = Field(description="Summary of macroeconomic conditions")


class IndustryContext(BaseModel):
    """Industry sector analysis context."""

    sector_name: str = Field(description="Name of the industry sector")
    sector_growth: float = Field(description="Sector growth rate percentage")
    competitive_landscape: str = Field(description="Description of competitive dynamics")
    regulatory_environment: str = Field(description="Current regulatory climate")
    trends: list[str] = Field(description="Key industry trends")
    outlook: str = Field(description="Industry outlook: positive/neutral/negative")
    summary: str = Field(description="Summary of industry analysis")


class CompanyData(BaseModel):
    """Basic company data."""

    symbol: str = Field(description="Stock ticker symbol")
    name: str = Field(description="Company name")
    sector: str = Field(description="Industry sector")
    market_cap: float = Field(description="Market capitalization in billions")
    pe_ratio: float = Field(description="Price-to-earnings ratio")
    current_price: float = Field(description="Current stock price")


class NewsItem(BaseModel):
    """News article item."""

    title: str = Field(description="News article title")
    source: str = Field(description="News source")
    published_at: datetime = Field(description="Publication timestamp")
    sentiment: str = Field(description="Article sentiment: positive/neutral/negative")
    summary: str = Field(description="Brief summary of the news")


class CompanyAnalysis(BaseModel):
    """Individual company analysis result."""

    company: CompanyData = Field(description="Basic company information")
    financial_health: str = Field(description="Assessment of financial health")
    recent_news: list[NewsItem] = Field(description="Recent news items")
    technical_indicator: str = Field(description="Technical analysis: buy/hold/sell")
    risks: list[str] = Field(description="Identified risk factors")
    summary: str = Field(description="Summary of company analysis")


class ResearchReport(BaseModel):
    """Final synthesized research report."""

    query: str = Field(description="Original user query")
    macro_analysis: MacroContext = Field(description="Macroeconomic analysis")
    industry_analysis: IndustryContext = Field(description="Industry analysis")
    company_analysis: CompanyAnalysis = Field(description="Company-specific analysis")
    investment_thesis: str = Field(description="Core investment thesis")
    recommendation: str = Field(description="Investment recommendation: buy/hold/sell")
    target_price: Optional[float] = Field(description="Target price if applicable")
    time_horizon: str = Field(description="Recommended investment time horizon")
    full_report: str = Field(description="Complete markdown-formatted report")
