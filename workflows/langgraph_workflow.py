"""AI-powered investment research workflow using LangGraph."""

from typing import TypedDict, Annotated, Literal
from datetime import datetime
from data.schemas import ResearchReport, MacroContext, IndustryContext, CompanyAnalysis
from agents.macro_analyst_ai import MacroAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent
from agents.equity_analyst_ai import EquityAnalystAgent
from agents.report_synthesizer_ai import ReportSynthesizerAgent
from agents.input_router_ai import InputRouterAgent, get_router_agent
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from memory.conversation_memory import ConversationMemory, get_conversation_memory, format_history_for_llm
from storage.report_cache import ReportCacheService, get_report_cache_service


class WorkflowState(TypedDict):
    """State type for LangGraph workflow orchestration."""
    query: str
    session_id: str | None  # Session ID for multi-turn conversation
    conversation_history: list[dict] | None  # Previous conversation history
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
    1. Input Router (parses user query)
    2. Macro Analyst (AI + real macro data)
    3. Industry Analyst (AI + real industry data)
    4. Equity Analyst (AI + real stock data)
    5. Report Synthesizer (AI-generated report)
    """

    def __init__(
        self,
        llm_config=None,
        conversation_memory: ConversationMemory = None,
        report_cache: ReportCacheService = None,
        enable_cache: bool = True,
    ):
        """
        Initialize the AI research workflow with LangGraph.

        Args:
            llm_config: Optional LLM configuration.
            conversation_memory: Optional conversation memory instance.
            report_cache: Optional report cache service instance.
            enable_cache: Enable report caching (default True).
        """
        # Initialize the Input Router Agent
        self.input_router = InputRouterAgent()

        # Initialize analyst agents
        self.macro_analyst = MacroAnalystAgent()
        self.industry_analyst = IndustryAnalystAgent()
        self.equity_analyst = EquityAnalystAgent()
        self.report_synthesizer = ReportSynthesizerAgent()

        # Conversation memory for multi-turn chat
        self.memory = conversation_memory or get_conversation_memory()

        # Report cache for fast retrieval of similar reports
        self.report_cache = report_cache or get_report_cache_service() if enable_cache else None
        self.enable_cache = enable_cache

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
        """Detect country, symbol, and sector from query using Input Router Agent."""
        query = state["query"]
        session_id = state.get("session_id")
        conversation_history = state.get("conversation_history", [])

        # Use Input Router Agent to parse the query
        params = self.input_router.parse_query(query)

        country = params.get('country', 'us')
        symbol = params.get('symbol', 'TSLA')
        sector = params.get('sector', '科技')

        # Log detection info
        detection_info = f"识别结果：国家={country}, 股票={symbol}, 行业={sector}, 置信度={params.get('confidence', 0):.0%}"

        # Store context in conversation memory if session exists
        if session_id:
            self.memory.update_context(session_id, {
                "country": country,
                "symbol": symbol,
                "sector": sector,
                "last_query": query
            })

        # Check if this is a follow-up question
        context_note = ""
        if conversation_history and len(conversation_history) > 0:
            context_note = "\n\n**注意**: 这是一个多轮对话，之前的分析上下文已保留。"

        return {
            "country": country,
            "symbol": symbol,
            "sector": sector,
            "messages": state.get("messages", []) + [
                f"### 🎯 步骤 0/4: 查询分析完成\n\n- {detection_info}{context_note}"
            ]
        }

    def _detect_symbol(self, query: str, query_upper: str) -> str:
        """Detect stock symbol from query."""
        # 首先检查是否包含 A 股 6 位代码
        import re
        cn_stock_pattern = re.findall(r'\b([06]\d{5})\b', query_upper)
        if cn_stock_pattern:
            code = cn_stock_pattern[0]
            # 添加市场前缀
            if code.startswith(('6', '9')):
                return f"sh{code}"
            elif code.startswith(('0', '3')):
                return f"sz{code}"

        # 检查港股 5 位代码
        hk_pattern = re.findall(r'\b(HK\d{5}|\d{5})\b', query_upper)
        if hk_pattern:
            code = hk_pattern[0]
            if code.startswith('HK'):
                return code.upper()
            return f"HK{code}"

        # Common mappings (including Chinese names) - 包含 A 股和港股
        mappings = {
            # 美股
            "特斯拉": "TSLA", "TSLA": "TSLA",
            "英伟达": "NVDA", "NVIDIA": "NVDA", "NVDA": "NVDA",
            "苹果": "AAPL", "APPLE": "AAPL", "AAPL": "AAPL",
            "微软": "MSFT", "MICROSOFT": "MSFT", "MSFT": "MSFT",
            "谷歌": "GOOGL", "GOOGLE": "GOOGL", "GOOGL": "GOOGL",
            "亚马逊": "AMZN", "AMAZON": "AMZN", "AMZN": "AMZN",
            "META": "META", "FACEBOOK": "META",
            # 中概股
            "阿里巴巴": "BABA", "ALIBABA": "BABA", "BABA": "BABA", "阿里": "BABA",
            "拼多多": "PDD", "PDD": "PDD",
            "京东": "JD", "JD": "JD",
            "百度": "BIDU", "BAIDU": "BIDU", "BIDU": "BIDU",
            "网易": "NTES", "NETEASE": "NTES", "NTES": "NTES",
            "小鹏": "XPEV", "XPENG": "XPEV", "XPEV": "XPEV",
            "理想": "LI", "LI AUTO": "LI",
            "蔚来": "NIO", "NIO": "NIO",
            # A 股
            "贵州茅台": "sh600519", "茅台": "sh600519",
            "宁德时代": "sz300750", "宁德": "sz300750",
            "中国平安": "sh601318", "平安": "sh601318",
            "招商银行": "sh600036", "招行": "sh600036",
            "五粮液": "sz000858",
            "比亚迪": "sz002594",
            # 港股
            "腾讯": "HK00700", "腾讯控股": "HK00700",
            "阿里巴巴港股": "HK09988",
            "美团": "HK03690",
            "小米": "HK01810", "小米集团": "HK01810"
        }

        # 使用原始查询匹配中文名称
        for name, symbol in mappings.items():
            if name in query:
                return symbol

        # 检查ticker pattern (3-4位大写字母)
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
        session_id = state.get("session_id")
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

            # Store analysis results in conversation memory for future reference
            if session_id:
                self.memory.update_context(session_id, {
                    "last_report": report.full_report,
                    "last_recommendation": report.recommendation,
                    "last_target_price": report.target_price,
                    "macro_context": macro_context.to_dict() if hasattr(macro_context, 'to_dict') else str(macro_context),
                    "industry_context": industry_context.to_dict() if hasattr(industry_context, 'to_dict') else str(industry_context),
                    "company_analysis": company_analysis.to_dict() if hasattr(company_analysis, 'to_dict') else str(company_analysis)
                })

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

    def execute(
        self,
        query: str,
        session_id: str = None,
        conversation_history: list[dict] = None
    ) -> ResearchReport:
        """
        Execute the full AI research workflow using LangGraph.

        Args:
            query: User's investment research query.
            session_id: Optional session ID for multi-turn conversation.
            conversation_history: Optional conversation history for context.

        Returns:
            Complete ResearchReport with AI analysis.
        """
        # Step 1: Try to get cached report first (if cache is enabled)
        if self.enable_cache and self.report_cache:
            print("🔍 正在检查缓存的报告...")
            cached_report = self.report_cache.find_cached_report(query)
            if cached_report:
                print("✅ 找到缓存的报告，直接返回")
                # Still add to conversation history
                if session_id:
                    self.memory.add_message(session_id, "user", query)
                    self.memory.add_message(
                        session_id,
                        "assistant",
                        cached_report.full_report,
                        metadata={
                            "recommendation": cached_report.recommendation,
                            "target_price": cached_report.target_price,
                            "from_cache": True,
                        }
                    )
                return cached_report

        # Get or create session if session_id provided
        if session_id:
            session = self.memory.get_or_create_session(session_id)
            # Add user query to conversation history
            self.memory.add_message(session_id, "user", query)

        # Initialize state
        initial_state: WorkflowState = {
            "query": query,
            "session_id": session_id,
            "conversation_history": conversation_history or [],
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
            if session_id:
                self.memory.add_message(session_id, "assistant", f"分析失败：{final_state['error']}")
            raise RuntimeError(final_state["error"])

        # Return the final report
        report = final_state.get("report")
        if not report:
            raise RuntimeError("工作流执行成功但未生成报告")

        # Add assistant response to conversation history
        if session_id:
            self.memory.add_message(
                session_id,
                "assistant",
                report.full_report,
                metadata={
                    "recommendation": report.recommendation,
                    "target_price": report.target_price,
                    "symbol": final_state.get("symbol", "")
                }
            )

        # Step 2: Cache the newly generated report
        if self.enable_cache and self.report_cache:
            try:
                country = final_state.get("country", "")
                sector = final_state.get("sector", "")
                symbol = final_state.get("symbol", "")

                report_id, success = self.report_cache.cache_report(
                    report=report,
                    query=query,
                    symbol=symbol,
                    country=country,
                    sector=sector,
                )

                if success:
                    print(f"✅ 报告已缓存，ID: {report_id}")

                    # Store report ID in session context
                    if session_id:
                        self.memory.set_context(session_id, f"report_{report_id}", {
                            "query": query,
                            "symbol": symbol,
                            "cached_at": datetime.now().isoformat(),
                        })
            except Exception as e:
                print(f"⚠️ 缓存报告失败：{e}")

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
