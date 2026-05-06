"""AI-powered investment research workflow using LangGraph."""

from typing import TypedDict, Annotated
from datetime import datetime
from data.schemas import ResearchReport, MacroContext, IndustryContext, CompanyAnalysis
from agents.macro_analyst_ai import MacroAnalystAgent
from agents.industry_analyst_ai import IndustryAnalystAgent
from agents.equity_analyst_ai import EquityAnalystAgent
from agents.report_synthesizer_ai import ReportSynthesizerAgent
from agents.input_router_ai import InputRouterAgent, get_router_agent
from agents.contracts import AgentResult
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from memory.conversation_memory import ConversationMemory, get_conversation_memory, format_history_for_llm
from memory.stores import InstrumentMemoryStore, ResearchMemoryLayer, SessionMemoryStore
from storage.report_cache import ReportCacheService, get_report_cache_service
from workflows.agent_scheduler import AgentScheduler
from workflows.hooks import AnalysisLifecycleHooks
from logging_config import get_trace_id, set_trace_id
import logging

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """State type for LangGraph workflow orchestration."""
    query: str
    session_id: str | None  # Session ID for multi-turn conversation
    conversation_history: list[dict] | None  # Previous conversation history
    conversation_context: str
    session_context: dict | None
    country: str
    sector: str
    symbol: str
    query_type: str  # 'stock_analysis', 'industry_analysis', 'macro_analysis'
    market_metadata: dict | None
    macro_context: MacroContext | None
    industry_context: IndustryContext | None
    company_analysis: CompanyAnalysis | None
    agent_results: list[AgentResult]
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
        self.agent_scheduler = AgentScheduler(
            self.macro_analyst,
            self.industry_analyst,
            self.equity_analyst,
        )
        self.hooks = AnalysisLifecycleHooks()

        # Conversation memory for multi-turn chat
        self.memory = conversation_memory or get_conversation_memory()

        # Report cache for fast retrieval of similar reports
        self.report_cache = report_cache or get_report_cache_service() if enable_cache else None
        self.enable_cache = enable_cache
        self.last_from_cache = False
        self.memory_layer = ResearchMemoryLayer(
            session_store=SessionMemoryStore(self.memory),
            instrument_store=InstrumentMemoryStore(self.report_cache),
        )

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
        builder.add_node("compliance_check", self._run_compliance_check)

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

        builder.add_edge("synthesize_report", "compliance_check")
        builder.add_edge("compliance_check", END)

        # Set entry point
        builder.set_entry_point("detect_params")

        return builder.compile()

    def _build_conversation_context(
        self,
        history: list[dict] | None,
        session_context: dict | None,
    ) -> str:
        """Build a concise context block for follow-up questions."""
        context_parts = []
        if history:
            context_parts.append(format_history_for_llm(history, max_history_messages=6))

        if session_context:
            useful_keys = [
                "symbol",
                "country",
                "sector",
                "query_type",
                "last_recommendation",
                "last_target_price",
                "user_preferences",
                "instrument_memory",
            ]
            retained = {
                key: session_context.get(key)
                for key in useful_keys
                if session_context.get(key) not in (None, "")
            }
            if retained:
                context_parts.append(f"已保留的会话上下文：{retained}")

        return "\n\n".join(context_parts)

    def _get_market_metadata(self, country: str, symbol: str = "") -> dict:
        """Return lightweight market metadata for display and report prompts."""
        country = (country or "us").lower()
        if country == "china" or symbol.lower().startswith(("sh", "sz")):
            return {
                "market": "A股",
                "currency": "CNY",
                "price_prefix": "¥",
                "data_source": "新浪财经 / 东方财富",
            }
        if country == "hk" or symbol.upper().startswith("HK"):
            return {
                "market": "港股",
                "currency": "HKD",
                "price_prefix": "HK$",
                "data_source": "新浪财经 / 东方财富",
            }
        return {
            "market": "美股",
            "currency": "USD",
            "price_prefix": "$",
            "data_source": "东方财富 / 公开市场数据",
        }

    def _format_price(self, price: float | None, market_metadata: dict | None) -> str:
        """Format a price using the resolved market currency."""
        if price is None:
            return "N/A"
        prefix = (market_metadata or {}).get("price_prefix", "")
        currency = (market_metadata or {}).get("currency", "")
        return f"{prefix}{price:.2f} {currency}".strip()

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
        session_context = self.memory.get_context(session_id) if session_id else {}

        country = params.get('country') or session_context.get("country") or 'us'
        symbol = params.get('symbol') or session_context.get("symbol") or 'TSLA'
        sector = params.get('sector') or session_context.get("sector") or '科技'
        query_type = params.get('query_type') or session_context.get("query_type") or 'stock_analysis'
        market_metadata = self._get_market_metadata(country, symbol)

        # Log detection info
        detection_info = f"识别结果：国家={country}, 股票={symbol}, 行业={sector}, 类型={query_type}, 置信度={params.get('confidence', 0):.0%}"
        logger.info(f"[TRACE={trace_id}] {detection_info}")

        # Store context in conversation memory if session exists
        if session_id:
            self.memory.get_or_create_session(session_id)
            self.memory.update_context(session_id, {
                "country": country,
                "symbol": symbol,
                "sector": sector,
                "query_type": query_type,
                "market": market_metadata["market"],
                "currency": market_metadata["currency"],
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
            "market_metadata": market_metadata,
            "session_context": session_context,
            "messages": state.get("messages", []) + [
                f"### 🎯 {step_label}: 查询分析完成\n\n- {detection_info}\n- 市场={market_metadata['market']}, 币种={market_metadata['currency']}\n- 数据源提示：{market_metadata['data_source']}{context_note}"
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
        if state.get("error"):
            return "synthesize_report"
        query_type = state.get("query_type", "stock_analysis")
        if query_type == "macro_analysis":
            return "synthesize_report"
        return "industry_analysis"

    def _route_after_industry(self, state: WorkflowState) -> str:
        """Route after industry analysis."""
        if state.get("error"):
            return "synthesize_report"
        query_type = state.get("query_type", "stock_analysis")
        if query_type in ("macro_analysis", "industry_analysis"):
            return "synthesize_report"
        return "equity_analysis"

    def _route_after_equity(self, state: WorkflowState) -> str:
        """Route after equity analysis."""
        return "synthesize_report"

    def _run_macro_analysis(self, state: WorkflowState) -> dict:
        """Run macro economic analysis."""
        country = state.get("country", "us")
        query_type = state.get("query_type", "stock_analysis")
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Running macro analysis for country: {country}")

        total_steps = {'macro_analysis': 1, 'industry_analysis': 2, 'stock_analysis': 4}.get(query_type, 4)

        try:
            macro_context, agent_result = self.agent_scheduler.run_macro(
                query=state.get("query", ""),
                country=country,
                trace_id=trace_id,
            )
            agent_result = self.hooks.validate_agent_result(agent_result)
            logger.info(f"[TRACE={trace_id}] Macro analysis completed: GDP={macro_context.gdp_growth}%, Inflation={macro_context.inflation_rate}%")
            return {
                "macro_context": macro_context,
                "agent_results": state.get("agent_results", []) + [agent_result],
                "messages": state.get("messages", []) + [
                    f"### 📈 步骤 1/{total_steps}: 宏观经济分析完成\n\n- **国家**: {country}\n- **GDP 增长**: {macro_context.gdp_growth}%\n- **通胀率**: {macro_context.inflation_rate}%\n- **市场情绪**: {macro_context.market_sentiment}\n- **数据来源**: {macro_context.data_source}"
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
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Running industry analysis for sector: {sector}")

        try:
            industry_context, agent_result = self.agent_scheduler.run_industry(
                query=state.get("query", ""),
                sector=sector,
                trace_id=trace_id,
            )
            agent_result = self.hooks.validate_agent_result(agent_result)
            logger.info(f"[TRACE={trace_id}] Industry analysis completed: growth={industry_context.sector_growth}%, outlook={industry_context.outlook}")
            return {
                "industry_context": industry_context,
                "agent_results": state.get("agent_results", []) + [agent_result],
                "messages": state.get("messages", []) + [
                    f"### 🏭 步骤 2/4: 行业分析完成\n\n- **行业**: {sector}\n- **行业增长**: {industry_context.sector_growth}%\n- **行业前景**: {industry_context.outlook}\n- **数据来源**: {industry_context.data_source}"
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
        market_metadata = state.get("market_metadata") or self._get_market_metadata(state.get("country", "us"), symbol)
        trace_id = get_trace_id()
        logger.info(f"[TRACE={trace_id}] Running equity analysis for symbol: {symbol}")

        try:
            company_analysis, agent_result = self.agent_scheduler.run_equity(
                query=state.get("query", ""),
                symbol=symbol,
                trace_id=trace_id,
            )
            agent_result = self.hooks.validate_agent_result(agent_result)
            price_text = self._format_price(company_analysis.company.current_price, market_metadata)
            logger.info(f"[TRACE={trace_id}] Equity analysis completed: company={company_analysis.company.name}, current_price={price_text}")
            return {
                "company_analysis": company_analysis,
                "agent_results": state.get("agent_results", []) + [agent_result],
                "messages": state.get("messages", []) + [
                    f"### 🏢 步骤 3/4: 公司分析完成\n\n- **公司**: {company_analysis.company.name}\n- **股票代码**: {symbol}\n- **当前股价**: {price_text}\n- **技术信号**: {company_analysis.technical_indicator}\n- **数据来源**: {company_analysis.company.data_source}"
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
        conversation_context = state.get("conversation_context", "")
        market_metadata = state.get("market_metadata") or self._get_market_metadata(state.get("country", "us"), state.get("symbol", ""))
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
                conversation_context=conversation_context,
                market_metadata=market_metadata,
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
                    f"### 📄 步骤 {current_step}/{total_steps}: 报告合成完成\n\n- **投资建议**: {report.recommendation}\n- **目标价格**: {self._format_price(report.target_price, market_metadata)}\n- **报告长度**: {len(report.full_report)} 字符"
                ]
            }
        except Exception as e:
            logger.error(f"[TRACE={trace_id}] Report synthesis failed: {e}")
            return {
                "error": f"报告合成失败：{str(e)}",
                "messages": state.get("messages", []) + [f"❌ 报告合成失败：{str(e)}"]
            }

    def _run_compliance_check(self, state: WorkflowState) -> dict:
        """Run deterministic report provenance and compliance checks."""
        report = state.get("report")
        if not report:
            return {}

        trace_id = get_trace_id()
        agent_results = state.get("agent_results", [])
        checked_report = self.hooks.validate_report_provenance(report, agent_results)
        self.hooks.emit_audit_log(
            "report_compliance_checked",
            trace_id=trace_id,
            sources=len(checked_report.data_sources or []),
            fallback_agents=sum(1 for result in agent_results if result.is_fallback),
        )
        return {"report": checked_report}

    def execute(
        self,
        query: str,
        session_id: str = None,
        conversation_history: list[dict] = None,
        user_id: str = None,
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
        self.last_from_cache = False
        self.hooks.validate_input(query)

        # Set trace ID in context for propagation to storage layer
        set_trace_id(trace_id)

        logger.info(f"[TRACE={trace_id}] Starting AI research workflow: query='{query[:50]}...'")

        # Step 1: Try to get cached report first (if cache is enabled)
        if self.enable_cache and self.report_cache:
            logger.info(f"[TRACE={trace_id}] Checking cache for similar reports")
            cached_report = self.report_cache.find_cached_report(query)
            if cached_report:
                self.last_from_cache = True
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

        session_context = self.memory.get_context(session_id) if session_id else {}
        prior_history = conversation_history or []
        if session_id and conversation_history is None:
            prior_history = self.memory.get_history(session_id)

        memory_snapshot = self.memory_layer.snapshot(
            session_id=session_id,
            history=prior_history,
            user_id=user_id,
            symbol=session_context.get("symbol"),
            query=query,
        )
        session_context = memory_snapshot.session_context
        conversation_context = self._build_conversation_context(
            [{"role": "system", "content": memory_snapshot.conversation_summary}]
            if memory_snapshot.conversation_summary else [],
            {
                **session_context,
                "user_preferences": memory_snapshot.user_preferences,
                "instrument_memory": memory_snapshot.instrument_memory,
            },
        )

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
            "conversation_history": prior_history,
            "conversation_context": conversation_context,
            "session_context": session_context,
            "country": "",
            "sector": "",
            "symbol": "",
            "query_type": "stock_analysis",
            "market_metadata": None,
            "macro_context": None,
            "industry_context": None,
            "company_analysis": None,
            "agent_results": [],
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
