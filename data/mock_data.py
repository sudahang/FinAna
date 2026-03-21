"""Simulated market data for demo purposes."""

from data.schemas import MacroContext, IndustryContext, CompanyData, NewsItem, CompanyAnalysis
from datetime import datetime, timedelta
import random


def get_mock_macro_context() -> MacroContext:
    """Generate simulated macroeconomic data."""
    return MacroContext(
        gdp_growth=2.5,
        inflation_rate=3.2,
        interest_rate=5.25,
        unemployment_rate=3.8,
        market_sentiment="neutral",
        summary=(
            "The current macroeconomic environment shows moderate growth with GDP expanding at 2.5%. "
            "Inflation has eased to 3.2% but remains above the Federal Reserve's 2% target. "
            "The central bank maintains a restrictive stance with interest rates at 5.25%. "
            "Labor markets remain resilient with unemployment at 3.8%. "
            "Overall market sentiment is neutral as investors balance growth concerns against inflation progress."
        )
    )


def get_mock_industry_context(sector: str = "Technology") -> IndustryContext:
    """Generate simulated industry data for a given sector."""
    industry_data = {
        "Technology": {
            "growth": 8.5,
            "competitive_landscape": (
                "Highly competitive with dominant players in AI, cloud computing, and semiconductors. "
                "Barriers to entry remain high due to R&D requirements and network effects."
            ),
            "regulatory_environment": (
                "Increased antitrust scrutiny globally. AI regulation frameworks under development. "
                "Data privacy regulations continue to evolve."
            ),
            "trends": [
                "Generative AI adoption accelerating across enterprises",
                "Cloud migration continuing at steady pace",
                "Edge computing gaining traction",
                "Cybersecurity investments increasing"
            ],
            "outlook": "positive"
        },
        "Automotive": {
            "growth": 4.2,
            "competitive_landscape": (
                "Traditional automakers competing with EV-focused newcomers. "
                "Chinese manufacturers expanding globally. Margin pressure from price competition."
            ),
            "regulatory_environment": (
                "Stricter emissions standards driving EV transition. "
                "Government incentives for electric vehicles in major markets."
            ),
            "trends": [
                "Electric vehicle adoption accelerating",
                "Autonomous driving technology maturing",
                "Software-defined vehicles becoming standard",
                "Battery technology improvements"
            ],
            "outlook": "neutral"
        },
        "Healthcare": {
            "growth": 5.8,
            "competitive_landscape": (
                "Fragmented market with large pharma, biotech, and device manufacturers. "
                "M&A activity remains elevated."
            ),
            "regulatory_environment": (
                "FDA approval pathways evolving for digital health. "
                "Drug pricing reforms under consideration."
            ),
            "trends": [
                "GLP-1 drugs transforming obesity treatment",
                "AI in drug discovery gaining momentum",
                "Personalized medicine advancing",
                "Telehealth stabilization post-pandemic"
            ],
            "outlook": "positive"
        }
    }

    data = industry_data.get(sector, industry_data["Technology"])

    return IndustryContext(
        sector_name=sector,
        sector_growth=data["growth"],
        competitive_landscape=data["competitive_landscape"],
        regulatory_environment=data["regulatory_environment"],
        trends=data["trends"],
        outlook=data["outlook"],
        summary=(
            f"The {sector} sector shows {data['growth']}% growth with a {data['outlook']} outlook. "
            f"{data['competitive_landscape']} {data['regulatory_environment']}"
        )
    )


def get_mock_company_data(symbol: str) -> CompanyData:
    """Generate simulated company data for a given stock symbol."""
    company_data = {
        "TSLA": {
            "name": "Tesla, Inc.",
            "sector": "Automotive",
            "market_cap": 580.5,
            "pe_ratio": 45.2,
            "current_price": 185.50
        },
        "NVDA": {
            "name": "NVIDIA Corporation",
            "sector": "Technology",
            "market_cap": 1750.0,
            "pe_ratio": 65.8,
            "current_price": 722.48
        },
        "AAPL": {
            "name": "Apple Inc.",
            "sector": "Technology",
            "market_cap": 2650.0,
            "pe_ratio": 28.5,
            "current_price": 172.75
        },
        "MSFT": {
            "name": "Microsoft Corporation",
            "sector": "Technology",
            "market_cap": 2890.0,
            "pe_ratio": 35.2,
            "current_price": 390.25
        },
        "GOOGL": {
            "name": "Alphabet Inc.",
            "sector": "Technology",
            "market_cap": 1720.0,
            "pe_ratio": 24.8,
            "current_price": 138.20
        },
        "BABA": {
            "name": "Alibaba Group Holding Limited",
            "sector": "Consumer Discretionary",
            "market_cap": 210.5,
            "pe_ratio": 12.8,
            "current_price": 78.50
        },
        "PDD": {
            "name": "PDD Holdings Inc.",
            "sector": "Consumer Discretionary",
            "market_cap": 185.0,
            "pe_ratio": 15.2,
            "current_price": 125.30
        },
        "JD": {
            "name": "JD.com, Inc.",
            "sector": "Consumer Discretionary",
            "market_cap": 52.5,
            "pe_ratio": 10.5,
            "current_price": 28.75
        },
        "BIDU": {
            "name": "Baidu, Inc.",
            "sector": "Technology",
            "market_cap": 35.8,
            "pe_ratio": 11.2,
            "current_price": 98.40
        },
        "NIO": {
            "name": "NIO Inc.",
            "sector": "Automotive",
            "market_cap": 15.2,
            "pe_ratio": -5.8,
            "current_price": 8.25
        },
        "XPEV": {
            "name": "XPeng Inc.",
            "sector": "Automotive",
            "market_cap": 12.8,
            "pe_ratio": -3.2,
            "current_price": 14.60
        },
        "LI": {
            "name": "Li Auto Inc.",
            "sector": "Automotive",
            "market_cap": 28.5,
            "pe_ratio": 18.5,
            "current_price": 28.90
        }
    }

    data = company_data.get(symbol.upper(), None)

    if data is None:
        # Generic fallback for unknown symbols
        return CompanyData(
            symbol=symbol.upper(),
            name=symbol.upper(),
            sector="Unknown",
            market_cap=0,
            pe_ratio=0,
            current_price=0
        )

    return CompanyData(
        symbol=symbol.upper(),
        name=data["name"],
        sector=data["sector"],
        market_cap=data["market_cap"],
        pe_ratio=data["pe_ratio"],
        current_price=data["current_price"]
    )


def get_mock_news(symbol: str) -> list[NewsItem]:
    """Generate simulated news items for a given stock symbol."""
    news_templates = {
        "TSLA": [
            {
                "title": "Tesla Expands Supercharger Network to New Regions",
                "source": "EV News Daily",
                "sentiment": "positive",
                "summary": "Tesla announces major expansion of its Supercharger network, adding 500 new stations globally."
            },
            {
                "title": "Competition Intensifies in EV Market as Legacy Automakers Ramp Up",
                "source": "Auto Weekly",
                "sentiment": "neutral",
                "summary": "Traditional automakers are accelerating EV production, increasing competitive pressure on Tesla."
            },
            {
                "title": "Tesla Q4 Deliveries Beat Analyst Expectations",
                "source": "Financial Times",
                "sentiment": "positive",
                "summary": "Tesla reported stronger-than-expected vehicle deliveries for Q4, signaling robust demand."
            }
        ],
        "NVDA": [
            {
                "title": "NVIDIA Unveils Next-Generation AI Chips",
                "source": "Tech Crunch",
                "sentiment": "positive",
                "summary": "NVIDIA announces breakthrough AI accelerator with 2x performance improvement."
            },
            {
                "title": "Data Center Demand Drives NVIDIA Revenue Growth",
                "source": "Reuters",
                "sentiment": "positive",
                "summary": "Enterprise AI adoption continues to fuel strong demand for NVIDIA's data center products."
            },
            {
                "title": "Export Restrictions May Impact NVIDIA China Sales",
                "source": "Bloomberg",
                "sentiment": "negative",
                "summary": "New semiconductor export controls could affect NVIDIA's revenue from Chinese market."
            }
        ],
        "BABA": [
            {
                "title": "阿里巴巴云智能集团宣布 AI 大模型新进展",
                "source": "科技日报",
                "sentiment": "positive",
                "summary": "阿里云发布通义千问新模型，企业应用能力显著提升。"
            },
            {
                "title": "阿里电商业务面临拼多多激烈竞争",
                "source": "财经网",
                "sentiment": "neutral",
                "summary": "拼多多 GMV 持续增长，阿里巴巴市场份额受到挑战。"
            },
            {
                "title": "阿里巴巴回购计划提振投资者信心",
                "source": "华尔街见闻",
                "sentiment": "positive",
                "summary": "公司宣布追加 250 亿美元股票回购计划，显示管理层对公司前景信心。"
            }
        ],
        "PDD": [
            {
                "title": "拼多多 Temu 海外扩张加速",
                "source": "晚点 LatePost",
                "sentiment": "positive",
                "summary": "Temu 进入多个欧洲市场，用户增长超预期。"
            },
            {
                "title": "拼多多财报超预期，营收增长显著",
                "source": "财新",
                "sentiment": "positive",
                "summary": "季度营收同比增长 58%，盈利能力持续提升。"
            }
        ],
        "NIO": [
            {
                "title": "蔚来推出新品牌乐道，进军主流市场",
                "source": "汽车之家",
                "sentiment": "positive",
                "summary": "乐道 L60 正式亮相，价格更具竞争力。"
            },
            {
                "title": "蔚来换电站数量突破 2000 座",
                "source": "第一电动",
                "sentiment": "positive",
                "summary": "充电基础设施持续完善，用户体验提升。"
            }
        ],
        "DEFAULT": [
            {
                "title": "Company Reports Strong Quarterly Earnings",
                "source": "Market Watch",
                "sentiment": "positive",
                "summary": "Better-than-expected earnings drive investor optimism."
            },
            {
                "title": "Industry Analysts Upgrade Stock Rating",
                "source": "CNBC",
                "sentiment": "positive",
                "summary": "Multiple analysts raise price targets citing improved fundamentals."
            },
            {
                "title": "Market Volatility Affects Sector Performance",
                "source": "Wall Street Journal",
                "sentiment": "neutral",
                "summary": "Broader market headwinds create near-term uncertainty for the sector."
            }
        ]
    }

    news_list = news_templates.get(symbol.upper(), news_templates["DEFAULT"])

    now = datetime.now()
    return [
        NewsItem(
            title=item["title"],
            source=item["source"],
            published_at=now - timedelta(days=i),
            sentiment=item["sentiment"],
            summary=item["summary"]
        )
        for i, item in enumerate(news_list)
    ]


def get_mock_company_analysis(symbol: str) -> CompanyAnalysis:
    """Generate simulated company analysis."""
    company = get_mock_company_data(symbol)
    news = get_mock_news(symbol)

    # Generate analysis based on company data
    pe_assessment = "reasonable" if company.pe_ratio < 30 else "elevated"
    financial_health = (
        f"Strong balance sheet with solid cash flows. "
        f"Valuation appears {pe_assessment} given current growth prospects."
    )

    technical = "buy" if company.pe_ratio < 40 else "hold"

    risks = [
        "Market volatility and macroeconomic uncertainty",
        "Sector-specific competitive pressures",
        "Regulatory changes impacting operations",
        "Supply chain disruption risks"
    ]

    return CompanyAnalysis(
        company=company,
        financial_health=financial_health,
        recent_news=news,
        technical_indicator=technical,
        risks=risks,
        summary=(
            f"{company.name} ({company.symbol}) shows {technical} signals with current price at "
            f"${company.current_price}. Market cap of ${company.market_cap}B reflects {pe_assessment} "
            f"valuation at {company.pe_ratio}x P/E. Recent news flow is mixed with positive earnings "
            f"momentum offset by broader market concerns."
        )
    )
