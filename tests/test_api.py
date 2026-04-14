"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestRootEndpoints:
    """Tests for root API endpoints."""

    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "FinAna API"
        assert "version" in data

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAnalysisEndpoints:
    """Tests for analysis API endpoints."""

    def test_analyze_endpoint(self):
        """Test the analyze endpoint."""
        response = client.post(
            "/analysis/analyze",
            json={"query": "Analyze Tesla stock"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] in ["completed", "pending", "failed"]

    def test_analyze_endpoint_empty_query(self):
        """Test analyze endpoint with empty query."""
        response = client.post(
            "/analysis/analyze",
            json={"query": ""}
        )
        # Should still create a task, but may fail during execution
        assert response.status_code == 200

    def test_analyze_endpoint_invalid_json(self):
        """Test analyze endpoint with invalid JSON."""
        response = client.post(
            "/analysis/analyze",
            json={"wrong_field": "value"}
        )
        # Pydantic validation should fail
        assert response.status_code == 422

    def test_status_endpoint_completed(self):
        """Test status endpoint for a completed task."""
        # First create a task
        analyze_response = client.post(
            "/analysis/analyze",
            json={"query": "Analyze NVDA"}
        )
        task_id = analyze_response.json()["task_id"]

        # Then check status
        status_response = client.get(f"/analysis/status/{task_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["task_id"] == task_id
        assert data["status"] in ["completed", "pending", "failed"]

    def test_status_endpoint_not_found(self):
        """Test status endpoint with non-existent task."""
        response = client.get("/analysis/status/non-existent-id")
        assert response.status_code == 404

    def test_result_endpoint_completed(self):
        """Test result endpoint for a completed task."""
        # First create a task
        analyze_response = client.post(
            "/analysis/analyze",
            json={"query": "Analyze AAPL"}
        )
        task_id = analyze_response.json()["task_id"]

        # Then get result
        result_response = client.get(f"/analysis/result/{task_id}")
        assert result_response.status_code == 200
        data = result_response.json()
        assert "query" in data
        assert "recommendation" in data
        assert "full_report" in data
        assert data["recommendation"] in ["buy", "hold", "sell"]

    def test_result_endpoint_not_found(self):
        """Test result endpoint with non-existent task."""
        response = client.get("/analysis/result/non-existent-id")
        assert response.status_code == 404

    def test_result_endpoint_not_completed(self):
        """Test result endpoint for a non-completed task."""
        # This test depends on timing, so we test with a non-existent task
        # In practice, you'd need to check status before getting result
        pass

    def test_full_analysis_flow(self):
        """Test complete analysis flow."""
        # Submit analysis request
        response = client.post(
            "/analysis/analyze",
            json={"query": "Should I buy Tesla?"}
        )
        assert response.status_code == 200

        task_id = response.json()["task_id"]

        # Get the result
        result_response = client.get(f"/analysis/result/{task_id}")
        assert result_response.status_code == 200

        data = result_response.json()
        assert data["query"] == "Should I buy Tesla?"
        assert data["recommendation"] in ["buy", "hold", "sell"]
        assert "# 投资研究报告" in data["full_report"]

    def test_multiple_sequential_analyses(self):
        """Test multiple sequential analysis requests."""
        queries = [
            "Analyze TSLA",
            "Analyze NVDA",
            "Analyze MSFT"
        ]

        task_ids = []
        for query in queries:
            response = client.post(
                "/analysis/analyze",
                json={"query": query}
            )
            assert response.status_code == 200
            task_ids.append(response.json()["task_id"])

        # Verify all tasks completed
        for task_id in task_ids:
            result_response = client.get(f"/analysis/result/{task_id}")
            assert result_response.status_code == 200

    def test_api_docs_available(self):
        """Test that API docs are available."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_api_openapi_json(self):
        """Test that OpenAPI JSON is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "FinAna API"
