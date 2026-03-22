"""AI-powered investment research workflow using LangGraph."""

from typing import TypedDict, Annotated, Literal
from data.schemas import ResearchReport, MacroContext, IndustryContext, CompanyAnalysis
from agents.macro_analyst_ai import MacroAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent
from agents.equity_analyst_ai import EquityAnalystAgent
from agents.report_synthesizer_ai import ReportSynthesizerAgent
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages


class WorkflowState(TypedDict):
    """State type for LangGraph workflow orchestration."""
    query: str
    country: str
    sector: str
    symbol: str
    macro_context: MacroContext | None
    industry_context: IndustryContext | None
    company_analysis: CompanyAnalysis | None
    report: ResearchReport | None
    error: str | None
    messages: Annotated[list[str], add_messages]


class AIResearchWorkflow:
    """
    AI-powered research workflow using LangGraph.

    Coordinates AI agents with real data fetching:
    1. Macro Analyst (AI + real macro data)
    2. Industry Analyst (AI + real industry data)
    3. Equity Analyst (AI + real stock data)
    4. Report Synthesizer (AI-generated report)
    """

    def __init__(self, llm_config=None):
        """
        Initialize the AI research workflow with LangGraph.

        Args:
            llm_config: Optional LLM configuration.
        """
        self.macro_analyst = MacroAnalystAgent()
        self.industry_analyst = IndustryAnalystAgent()
        self.equity_analyst = EquityAnalystAgent()
        self.report_synthesizer = ReportSynthesizerAgent()

        # Build the LangGraph workflow
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        # Initialize the graph
        builder = StateGraph(WorkflowState)

        # Add nodes for each agent
        builder.add_node("detect_params", self._detect_params)
        builder.add_node("macro_analysis", self._run_macro_analysis)
        builder.add_node("industry_analysis", self._run_industry_analysis)
        builder.add_node("equity_analysis", self._run_equity_analysis)
        builder.add_node("synthesize_report", self._run_report_synthesis)

        # Define edges (execution flow)
        # Entry point: detect parameters
        builder.add_edge("detect_params", "macro_analysis")

        # Sequential execution: Macro -> Industry -> Equity -> Synthesize
        builder.add_edge("macro_analysis", "industry_analysis")
        builder.add_edge("industry_analysis", "equity_analysis")
        builder.add_edge("equity_analysis", "synthesize_report")

        # Final node ends the workflow
        builder.add_edge("synthesize_report", END)

        # Set entry point
        builder.set_entry_point("detect_params")

        return builder.compile()

    def _detect_params(self, state: WorkflowState) -> dict:
        """Detect country and symbol from query."""
        query = state["query"]
        query_lower = query.lower()
        query_upper = query.upper()

        # Detect country
        if any(kw in query_lower for kw in ["中国", "a 股", "港股", "沪深"]):
            country = "china"
        elif any(kw in query_lower for kw in ["美股", "美国", "nasdaq", "nyse"]):
            country = "us"
        else:
            country = "us"  # Default to US for known stocks

        # Detect symbol
        symbol = self._detect_symbol(query_upper)

        # Detect sector
        sector = self._detect_sector(query_lower)

        return {
            "country": country,
            "symbol": symbol,
            "sector": sector,
            "messages": state.get("messages", []) + [f"分析参数：国家={country}, 股票={symbol}, 行业={sector}"]
        }

    def _detect_symbol(self, query_upper: str) -> str:
        """Detect stock symbol from query."""
        # Common mappings (including Chinese names)
        mappings = {
            "特斯拉": "TSLA", "TSLA": "TSLA",
            "英伟达": "NVDA", "NVIDIA": "NVDA", "NVDA": "NVDA",
            "苹果": "AAPL", "APPLE": "AAPL", "AAPL": "AAPL",
            "微软": "MSFT", "MICROSOFT": "MSFT", "MSFT": "MSFT",
            "谷歌": "GOOGL", "GOOGLE": "GOOGL", "GOOGL": "GOOGL",
            "亚马逊": "AMZN", "AMAZON": "AMZN", "AMZN": "AMZN",
            "META": "META", "FACEBOOK": "META",
            # Chinese concept stocks
            "阿里巴巴": "BABA", "ALIBABA": "BABA", "BABA": "BABA", "阿里": "BABA",
            "拼多多": "PDD", "PDD": "PDD",
            "京东": "JD", "JD": "JD",
            "百度": "BIDU", "BAIDU": "BIDU", "BIDU": "BIDU",
            "网易": "NTES", "NETEASE": "NTES", "NTES": "NTES",
            "小鹏": "XPEV", "XPENG": "XPEV", "XPEV": "XPEV",
            "理想": "LI", "LI AUTO": "LI",
            "蔚来": "NIO", "NIO": "NIO"
        }

        for name, symbol in mappings.items():
            if name in query_upper:
                return symbol

        # Check for ticker pattern
        import re
        tickers = re.findall(r'\b[A-Z]{3,4}\b', query_upper)
        if tickers:
            return tickers[0]

        return "TSLA"  # Default

    def _detect_sector(self, query_lower: str) -> str:
        """Detect sector from query."""
        sector_keywords = {
            "科技": ["科技", "软件", "ai", "半导体", "芯片", "互联网", "nvidia", "苹果", "微软"],
            "汽车": ["汽车", "新能源", "ev", "tesla", "特斯拉", "比亚迪", "造车"],
            "医疗": ["医疗", "健康", "医药", "biotech", "生物科技", "器械"],
            "金融": ["金融", "银行", "保险", "券商", "fintech"],
            "消费": ["消费", "零售", "食品", "饮料", "家电", "服装"],
            "能源": ["能源", "石油", "天然气", "光伏", "风电", "电池"]
        }

        for sector, keywords in sector_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return sector

        return "科技"  # Default to technology

    def _run_macro_analysis(self, state: WorkflowState) -> dict:
        """Run macro economic analysis."""
        country = state.get("country", "us")
        try:
            print(f"🔍 正在分析宏观经济 ({country})...")
            macro_context = self.macro_analyst.analyze(country)
            print(f"✅ 宏观经济分析完成")
            return {
                "macro_context": macro_context,
                "messages": state.get("messages", []) + [
                    f"### 📈 步骤 1/4: 宏观经济分析完成\n\n- **国家**: {country}\n- **GDP 增长**: {macro_context.gdp_growth}%\n- **通胀率**: {macro_context.inflation_rate}%\n- **市场情绪**: {macro_context.market_sentiment}"
                ]
            }
        except Exception as e:
            print(f"❌ 宏观分析失败：{e}")
            return {
                "error": f"宏观分析失败：{str(e)}",
                "messages": state.get("messages", []) + [f"❌ 宏观分析失败：{str(e)}"]
            }

    def _run_industry_analysis(self, state: WorkflowState) -> dict:
        """Run industry analysis."""
        sector = state.get("sector", "科技")
        query = state.get("query", "")
        try:
            print(f"🔍 正在分析行业 ({sector})...")
            industry_context = self.industry_analyst.analyze_with_context(query)
            print(f"✅ 行业分析完成")
            return {
                "industry_context": industry_context,
                "messages": state.get("messages", []) + [
                    f"### 🏭 步骤 2/4: 行业分析完成\n\n- **行业**: {sector}\n- **行业增长**: {industry_context.sector_growth}%\n- **行业前景**: {industry_context.outlook}"
                ]
            }
        except Exception as e:
            print(f"❌ 行业分析失败：{e}")
            return {
                "error": f"行业分析失败：{str(e)}",
                "messages": state.get("messages", []) + [f"❌ 行业分析失败：{str(e)}"]
            }

    def _run_equity_analysis(self, state: WorkflowState) -> dict:
        """Run equity analysis."""
        symbol = state.get("symbol", "TSLA")
        try:
            print(f"🔍 正在分析公司 ({symbol})...")
            company_analysis = self.equity_analyst.analyze(symbol)
            print(f"✅ 公司分析完成")
            return {
                "company_analysis": company_analysis,
                "messages": state.get("messages", []) + [
                    f"### 🏢 步骤 3/4: 公司分析完成\n\n- **公司**: {company_analysis.company.name}\n- **股票代码**: {symbol}\n- **当前股价**: ${company_analysis.company.current_price:.2f}\n- **技术信号**: {company_analysis.technical_indicator}"
                ]
            }
        except Exception as e:
            print(f"❌ 公司分析失败：{e}")
            return {
                "error": f"公司分析失败：{str(e)}",
                "messages": state.get("messages", []) + [f"❌ 公司分析失败：{str(e)}"]
            }

    def _run_report_synthesis(self, state: WorkflowState) -> dict:
        """Run report synthesis."""
        query = state.get("query", "")
        macro_context = state.get("macro_context")
        industry_context = state.get("industry_context")
        company_analysis = state.get("company_analysis")

        if not all([macro_context, industry_context, company_analysis]):
            return {
                "error": "缺少必要的分析结果，无法生成报告",
                "messages": state.get("messages", []) + ["❌ 缺少分析结果，无法生成报告"]
            }

        try:
            print("📝 正在合成最终报告...")
            report = self.report_synthesizer.synthesize(
                query=query,
                macro_context=macro_context,
                industry_context=industry_context,
                company_analysis=company_analysis
            )
            print(f"✅ 报告生成完成，长度：{len(report.full_report)} 字符")
            return {
                "report": report,
                "messages": state.get("messages", []) + [
                    f"### 📄 步骤 4/4: 报告合成完成\n\n- **投资建议**: {report.recommendation}\n- **目标价格**: ${report.target_price}\n- **报告长度**: {len(report.full_report)} 字符"
                ]
            }
        except Exception as e:
            print(f"❌ 报告合成失败：{e}")
            return {
                "error": f"报告合成失败：{str(e)}",
                "messages": state.get("messages", []) + [f"❌ 报告合成失败：{str(e)}"]
            }

    def execute(self, query: str) -> ResearchReport:
        """
        Execute the full AI research workflow using LangGraph.

        Args:
            query: User's investment research query.

        Returns:
            Complete ResearchReport with AI analysis.
        """
        # Initialize state
        initial_state: WorkflowState = {
            "query": query,
            "country": "",
            "sector": "",
            "symbol": "",
            "macro_context": None,
            "industry_context": None,
            "company_analysis": None,
            "report": None,
            "error": None,
            "messages": []
        }

        # Run the workflow
        final_state = self.graph.invoke(initial_state)

        # Log execution trace
        print("执行轨迹:")
        for msg in final_state.get("messages", []):
            print(f"  {msg}")

        # Check for errors
        if final_state.get("error"):
            raise RuntimeError(final_state["error"])

        # Return the final report
        report = final_state.get("report")
        if not report:
            raise RuntimeError("工作流执行成功但未生成报告")

        return report


async def execute_ai_research_workflow(query: str) -> ResearchReport:
    """
    Async convenience function to execute AI research workflow.

    Args:
        query: User's investment research query.

    Returns:
        Complete ResearchReport with AI analysis.
    """
    workflow = AIResearchWorkflow()
    return workflow.execute(query)
