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
from logging_config import get_trace_id, set_trace_id
import logging

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """State type for LangGraph workflow orchestration."""
    query: str
    session_id: str | None  # Session ID for multi-turn conversation
    conversation_history: list[dict] | None  # Previous conversation history
    country: str
    sector: str
    symbol: str
    query_type: str  # 'stock_analysis', 'industry_analysis', 'macro_analysis'
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

        # Conditional routing based on query_type
        builder.add_conditional_edges(
            "detect_params",
            self._route_after_detection,
            {
                "macro_analysis": "macro_analysis",
                "industry_analysis": "industry_analysis",
                "equity_analysis": "equity_analysis",
                "synthesize_report": "synthesize_report",
            }
        )
        builder.add_conditional_edges(
            "macro_analysis",
            self._route_after_macro,
            {
                "industry_analysis": "industry_analysis",
                "synthesize_report": "synthesize_report",
            }
        )
        builder.add_conditional_edges(
            "industry_analysis",
            self._route_after_industry,
            {
                "equity_analysis": "equity_analysis",
                "synthesize_report": "synthesize_report",
            }
        )
        builder.add_conditional_edges(
            "equity_analysis",
            self._route_after_equity,
            {
                "synthesize_report": "synthesize_report",
            }
        )

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

        # Get trace ID from context
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Detecting parameters from query")

        # Use Input Router Agent to parse the query
        params = self.input_router.parse_query(query)

        country = params.get('country', 'us')
        symbol = params.get('symbol', 'TSLA')
        sector = params.get('sector', '科技')
        query_type = params.get('query_type', 'stock_analysis')

        # Log detection info
        detection_info = f"识别结果：国家={country}, 股票={symbol}, 行业={sector}, 类型={query_type}, 置信度={params.get('confidence', 0):.0%}"
        logger.info(f"[TRACE={trace_id}] {detection_info}")

        # Store context in conversation memory if session exists
        if session_id:
            self.memory.update_context(session_id, {
                "country": country,
                "symbol": symbol,
                "sector": sector,
                "query_type": query_type,
                "last_query": query
            })

        # Check if this is a follow-up question
        context_note = ""
        if conversation_history and len(conversation_history) > 0:
            context_note = "\n\n**注意**: 这是一个多轮对话，之前的分析上下文已保留。"

        # Determine analysis scope based on query_type
        scope_map = {
            'macro_analysis': ['macro'],
            'industry_analysis': ['macro', 'industry'],
            'stock_analysis': ['macro', 'industry', 'equity'],
        }
        analysis_scope = scope_map.get(query_type, ['macro', 'industry', 'equity'])

        step_count = len(analysis_scope)
        step_label = f"步骤 0/{step_count}"

        return {
            "country": country,
            "symbol": symbol,
            "sector": sector,
            "query_type": query_type,
            "messages": state.get("messages", []) + [
                f"### 🎯 {step_label}: 查询分析完成\n\n- {detection_info}{context_note}"
            ]
        }

    def _route_after_detection(self, state: WorkflowState) -> str:
        """Route to the first analysis node based on query_type."""
        query_type = state.get("query_type", "stock_analysis")
        if query_type == "macro_analysis":
            return "macro_analysis"
        elif query_type == "industry_analysis":
            return "industry_analysis"
        elif query_type == "stock_analysis":
            return "macro_analysis"
        return "synthesize_report"

    def _route_after_macro(self, state: WorkflowState) -> str:
        """Route after macro analysis."""
        query_type = state.get("query_type", "stock_analysis")
        if query_type == "macro_analysis":
            return "synthesize_report"
        return "industry_analysis"

    def _route_after_industry(self, state: WorkflowState) -> str:
        """Route after industry analysis."""
        query_type = state.get("query_type", "stock_analysis")
        if query_type in ("macro_analysis", "industry_analysis"):
            return "synthesize_report"
        return "equity_analysis"

    def _route_after_equity(self, state: WorkflowState) -> str:
        """Route after equity analysis."""
        return "synthesize_report"

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
        query_type = state.get("query_type", "stock_analysis")
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Running macro analysis for country: {country}")

        total_steps = {'macro_analysis': 1, 'industry_analysis': 2, 'stock_analysis': 4}.get(query_type, 4)

        try:
            macro_context = self.macro_analyst.analyze(country)
            logger.info(f"[TRACE={trace_id}] Macro analysis completed: GDP={macro_context.gdp_growth}%, Inflation={macro_context.inflation_rate}%")
            return {
                "macro_context": macro_context,
                "messages": state.get("messages", []) + [
                    f"### 📈 步骤 1/{total_steps}: 宏观经济分析完成\n\n- **国家**: {country}\n- **GDP 增长**: {macro_context.gdp_growth}%\n- **通胀率**: {macro_context.inflation_rate}%\n- **市场情绪**: {macro_context.market_sentiment}"
                ]
            }
        except Exception as e:
            logger.error(f"[TRACE={trace_id}] Macro analysis failed: {e}")
            return {
                "error": f"宏观分析失败：{str(e)}",
                "messages": state.get("messages", []) + [f"❌ 宏观分析失败：{str(e)}"]
            }

    def _run_industry_analysis(self, state: WorkflowState) -> dict:
        """Run industry analysis."""
        sector = state.get("sector", "科技")
        query = state.get("query", "")
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Running industry analysis for sector: {sector}")

        try:
            industry_context = self.industry_analyst.analyze_with_context(query)
            logger.info(f"[TRACE={trace_id}] Industry analysis completed: growth={industry_context.sector_growth}%, outlook={industry_context.outlook}")
            return {
                "industry_context": industry_context,
                "messages": state.get("messages", []) + [
                    f"### 🏭 步骤 2/4: 行业分析完成\n\n- **行业**: {sector}\n- **行业增长**: {industry_context.sector_growth}%\n- **行业前景**: {industry_context.outlook}"
                ]
            }
        except Exception as e:
            logger.error(f"[TRACE={trace_id}] Industry analysis failed: {e}")
            return {
                "error": f"行业分析失败：{str(e)}",
                "messages": state.get("messages", []) + [f"❌ 行业分析失败：{str(e)}"]
            }

    def _run_equity_analysis(self, state: WorkflowState) -> dict:
        """Run equity analysis."""
        symbol = state.get("symbol", "TSLA")
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Running equity analysis for symbol: {symbol}")

        try:
            company_analysis = self.equity_analyst.analyze(symbol)
            logger.info(f"[TRACE={trace_id}] Equity analysis completed: company={company_analysis.company.name}, current_price=${company_analysis.company.current_price:.2f}")
            return {
                "company_analysis": company_analysis,
                "messages": state.get("messages", []) + [
                    f"### 🏢 步骤 3/4: 公司分析完成\n\n- **公司**: {company_analysis.company.name}\n- **股票代码**: {symbol}\n- **当前股价**: ${company_analysis.company.current_price:.2f}\n- **技术信号**: {company_analysis.technical_indicator}"
                ]
            }
        except Exception as e:
            logger.error(f"[TRACE={trace_id}] Equity analysis failed: {e}")
            return {
                "error": f"公司分析失败：{str(e)}",
                "messages": state.get("messages", []) + [f"❌ 公司分析失败：{str(e)}"]
            }

    def _run_report_synthesis(self, state: WorkflowState) -> dict:
        """Run report synthesis, handling partial contexts."""
        query = state.get("query", "")
        session_id = state.get("session_id")
        macro_context = state.get("macro_context")
        industry_context = state.get("industry_context")
        company_analysis = state.get("company_analysis")
        query_type = state.get("query_type", "stock_analysis")
        trace_id = get_trace_id()

        # At least one analysis must be present
        if not any([macro_context, industry_context, company_analysis]):
            logger.error(f"[TRACE={trace_id}] No analysis results available for report synthesis")
            return {
                "error": "缺少必要的分析结果，无法生成报告",
                "messages": state.get("messages", []) + ["❌ 缺少分析结果，无法生成报告"]
            }

        try:
            logger.info(f"[TRACE={trace_id}] Synthesizing final report (type={query_type})")
            report = self.report_synthesizer.synthesize_partial(
                query=query,
                macro_context=macro_context,
                industry_context=industry_context,
                company_analysis=company_analysis,
                query_type=query_type,
            )
            logger.info(f"[TRACE={trace_id}] Report synthesized successfully, length: {len(report.full_report)} chars, recommendation: {report.recommendation}")

            # Store analysis results in conversation memory for future reference
            if session_id:
                self.memory.update_context(session_id, {
                    "last_report": report.full_report,
                    "last_recommendation": report.recommendation,
                    "last_target_price": report.target_price,
                    "macro_context": macro_context.model_dump() if macro_context else None,
                    "industry_context": industry_context.model_dump() if industry_context else None,
                    "company_analysis": company_analysis.model_dump() if company_analysis else None,
                })

            # Determine total steps based on query_type
            step_map = {
                'macro_analysis': 1,
                'industry_analysis': 2,
                'stock_analysis': 4,
            }
            total_steps = step_map.get(query_type, 4)
            current_step = total_steps

            return {
                "report": report,
                "messages": state.get("messages", []) + [
                    f"### 📄 步骤 {current_step}/{total_steps}: 报告合成完成\n\n- **投资建议**: {report.recommendation}\n- **目标价格**: ${report.target_price}\n- **报告长度**: {len(report.full_report)} 字符"
                ]
            }
        except Exception as e:
            logger.error(f"[TRACE={trace_id}] Report synthesis failed: {e}")
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
        # Generate trace ID for this request
        import uuid
        trace_id = str(uuid.uuid4())[:8]

        # Set trace ID in context for propagation to storage layer
        set_trace_id(trace_id)

        logger.info(f"[TRACE={trace_id}] Starting AI research workflow: query='{query[:50]}...'")

        # Step 1: Try to get cached report first (if cache is enabled)
        if self.enable_cache and self.report_cache:
            logger.info(f"[TRACE={trace_id}] Checking cache for similar reports")
            cached_report = self.report_cache.find_cached_report(query)
            if cached_report:
                logger.info(f"[TRACE={trace_id}] CACHE HIT: Found cached report, returning directly")
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
                logger.info(f"[TRACE={trace_id}] Workflow completed (from cache)")
                return cached_report
            else:
                logger.info(f"[TRACE={trace_id}] CACHE MISS: No similar report found, will generate new one")

        # Get or create session if session_id provided
        if session_id:
            session = self.memory.get_or_create_session(session_id)
            # Add user query to conversation history
            self.memory.add_message(session_id, "user", query)
            logger.debug(f"[TRACE={trace_id}] Session initialized: {session_id}")

        # Initialize state
        initial_state: WorkflowState = {
            "query": query,
            "session_id": session_id,
            "conversation_history": conversation_history or [],
            "country": "",
            "sector": "",
            "symbol": "",
            "query_type": "stock_analysis",
            "macro_context": None,
            "industry_context": None,
            "company_analysis": None,
            "report": None,
            "error": None,
            "messages": []
        }

        # Run the workflow
        logger.info(f"[TRACE={trace_id}] Invoking LangGraph workflow")
        final_state = self.graph.invoke(initial_state)

        # Log execution trace
        logger.info(f"[TRACE={trace_id}] Workflow completed, messages: {len(final_state.get('messages', []))} steps")

        # Check for errors
        if final_state.get("error"):
            logger.error(f"[TRACE={trace_id}] Workflow error: {final_state['error']}")
            if session_id:
                self.memory.add_message(session_id, "assistant", f"分析失败：{final_state['error']}")
            raise RuntimeError(final_state["error"])

        # Return the final report
        report = final_state.get("report")
        if not report:
            logger.error(f"[TRACE={trace_id}] Workflow completed but no report generated")
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

                logger.info(f"[TRACE={trace_id}] Caching newly generated report: symbol={symbol}, country={country}")
                report_id, success = self.report_cache.cache_report(
                    report=report,
                    query=query,
                    symbol=symbol,
                    country=country,
                    sector=sector,
                )

                if success:
                    logger.info(f"[TRACE={trace_id}] Report cached successfully: report_id={report_id}")

                    # Store report ID in session context
                    if session_id:
                        self.memory.set_context(session_id, f"report_{report_id}", {
                            "query": query,
                            "symbol": symbol,
                            "cached_at": datetime.now().isoformat(),
                        })
                else:
                    logger.warning(f"[TRACE={trace_id}] Failed to cache report")

            except Exception as e:
                logger.warning(f"[TRACE={trace_id}] Error while caching report: {e}")

        logger.info(f"[TRACE={trace_id}] Workflow execution completed successfully")
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
