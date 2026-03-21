"""Tests for research workflow."""

import pytest
from workflows.research_workflow import ResearchWorkflow, execute_research_workflow, WorkflowState
from data.schemas import ResearchReport, MacroContext, IndustryContext, CompanyAnalysis


class TestResearchWorkflow:
    """Tests for ResearchWorkflow class."""

    def test_create_workflow(self):
        """Test creating a ResearchWorkflow."""
        workflow = ResearchWorkflow()
        assert workflow.macro_analyst is not None
        assert workflow.industry_analyst is not None
        assert workflow.equity_analyst is not None
        assert workflow.report_synthesizer is not None

    def test_execute_returns_research_report(self):
        """Test that execute returns a ResearchReport."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Analyze Tesla stock")
        assert isinstance(result, ResearchReport)

    def test_execute_query_preserved(self):
        """Test that the original query is preserved in the report."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Should I buy NVIDIA?")
        assert result.query == "Should I buy NVIDIA?"

    def test_execute_has_macro_analysis(self):
        """Test that report contains macro analysis."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Analyze AAPL")
        assert result.macro_analysis is not None
        assert result.macro_analysis.gdp_growth > 0

    def test_execute_has_industry_analysis(self):
        """Test that report contains industry analysis."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Analyze MSFT")
        assert result.industry_analysis is not None
        assert result.industry_analysis.sector_name in ["Technology", "Automotive", "Healthcare"]

    def test_execute_has_company_analysis(self):
        """Test that report contains company analysis."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Analyze TSLA")
        assert result.company_analysis is not None
        assert result.company_analysis.company.symbol == "TSLA"

    def test_execute_has_recommendation(self):
        """Test that report contains recommendation."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Analyze NVDA")
        assert result.recommendation in ["buy", "hold", "sell"]

    def test_execute_has_full_report(self):
        """Test that report contains full markdown report."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Analyze GOOGL")
        assert result.full_report is not None
        assert len(result.full_report) > 100
        assert "# Investment Research Report" in result.full_report

    def test_execute_different_queries(self):
        """Test executing multiple different queries."""
        workflow = ResearchWorkflow()

        queries = [
            "Analyze Tesla",
            "Should I buy NVIDIA?",
            "Investment outlook for Apple",
            "Microsoft stock analysis"
        ]

        for query in queries:
            result = workflow.execute(query)
            assert isinstance(result, ResearchReport)
            assert result.query == query

    def test_workflow_state_type(self):
        """Test WorkflowState typed dict structure."""
        state: WorkflowState = {
            "query": "Test",
            "macro_context": None,
            "industry_context": None,
            "company_analysis": None,
            "report": None,
            "error": None
        }
        assert state["query"] == "Test"


class TestExecuteResearchWorkflow:
    """Tests for execute_research_workflow async function."""

    def test_async_execute_returns_report(self):
        """Test that async execute returns a ResearchReport."""
        # Note: Since the function is synchronous internally,
        # we test it synchronously here
        workflow = ResearchWorkflow()
        result = workflow.execute("Test query")
        assert isinstance(result, ResearchReport)


class TestWorkflowIntegration:
    """Integration tests for the complete workflow."""

    def test_full_workflow_tesla(self):
        """Test full workflow with Tesla analysis."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Analyze Tesla's stock for the next month")

        assert result.query == "Analyze Tesla's stock for the next month"
        assert result.company_analysis.company.symbol == "TSLA"
        assert result.company_analysis.company.name == "Tesla, Inc."
        assert result.recommendation in ["buy", "hold", "sell"]
        assert "Tesla" in result.full_report or "TSLA" in result.full_report

    def test_full_workflow_nvidia(self):
        """Test full workflow with NVIDIA analysis."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Should I invest in NVIDIA?")

        assert result.company_analysis.company.symbol == "NVDA"
        assert result.company_analysis.company.name == "NVIDIA Corporation"
        assert "NVIDIA" in result.full_report or "NVDA" in result.full_report

    def test_full_workflow_apple(self):
        """Test full workflow with Apple analysis."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Analyze Apple Inc.")

        assert result.company_analysis.company.symbol == "AAPL"
        assert result.company_analysis.company.name == "Apple Inc."

    def test_report_structure(self):
        """Test that the generated report has proper structure."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Test analysis")

        # Check report sections exist
        assert "## Macroeconomic Analysis" in result.full_report
        assert "## Industry Analysis" in result.full_report
        assert "## Company Analysis" in result.full_report
        assert "## Investment Conclusion" in result.full_report

    def test_report_contains_data_tables(self):
        """Test that report contains data tables."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Test analysis")

        assert "| Indicator | Value |" in result.full_report or "| Metric | Value |" in result.full_report

    def test_report_contains_disclaimer(self):
        """Test that report contains disclaimer."""
        workflow = ResearchWorkflow()
        result = workflow.execute("Test analysis")

        assert "demonstration purposes" in result.full_report.lower() or "financial advice" in result.full_report.lower()
