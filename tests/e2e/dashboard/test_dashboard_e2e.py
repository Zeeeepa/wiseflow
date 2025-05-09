"""
End-to-end tests for the dashboard functionality.

This module contains end-to-end tests for the dashboard functionality.
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from dashboard.main import app as dashboard_app

pytestmark = [pytest.mark.e2e, pytest.mark.dashboard]


@pytest.fixture
def dashboard_client():
    """Create a test client for the dashboard app."""
    return TestClient(dashboard_app)


@pytest.fixture
def mock_dashboard_backend():
    """Mock the dashboard backend for testing."""
    with patch("dashboard.backend") as mock:
        # Set up the mock
        mock.get_reports.return_value = [
            {
                "id": "report-1",
                "title": "Test Report 1",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "content": "This is test report 1",
                "metadata": {"tags": ["test", "report"]},
            },
            {
                "id": "report-2",
                "title": "Test Report 2",
                "created_at": "2023-01-02T00:00:00",
                "updated_at": "2023-01-02T00:00:00",
                "content": "This is test report 2",
                "metadata": {"tags": ["test", "report"]},
            },
        ]
        
        mock.get_report.return_value = {
            "id": "report-1",
            "title": "Test Report 1",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
            "content": "This is test report 1",
            "metadata": {"tags": ["test", "report"]},
        }
        
        mock.create_report.return_value = {
            "id": "report-3",
            "title": "Test Report 3",
            "created_at": "2023-01-03T00:00:00",
            "updated_at": "2023-01-03T00:00:00",
            "content": "This is test report 3",
            "metadata": {"tags": ["test", "report"]},
        }
        
        mock.update_report.return_value = {
            "id": "report-1",
            "title": "Updated Test Report 1",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-03T00:00:00",
            "content": "This is updated test report 1",
            "metadata": {"tags": ["test", "report", "updated"]},
        }
        
        mock.delete_report.return_value = True
        
        mock.get_searches.return_value = [
            {
                "id": "search-1",
                "query": "Test Query 1",
                "created_at": "2023-01-01T00:00:00",
                "results": ["result-1", "result-2"],
                "metadata": {"tags": ["test", "search"]},
            },
            {
                "id": "search-2",
                "query": "Test Query 2",
                "created_at": "2023-01-02T00:00:00",
                "results": ["result-3", "result-4"],
                "metadata": {"tags": ["test", "search"]},
            },
        ]
        
        mock.get_search.return_value = {
            "id": "search-1",
            "query": "Test Query 1",
            "created_at": "2023-01-01T00:00:00",
            "results": ["result-1", "result-2"],
            "metadata": {"tags": ["test", "search"]},
        }
        
        mock.create_search.return_value = {
            "id": "search-3",
            "query": "Test Query 3",
            "created_at": "2023-01-03T00:00:00",
            "results": ["result-5", "result-6"],
            "metadata": {"tags": ["test", "search"]},
        }
        
        mock.delete_search.return_value = True
        
        yield mock


def test_dashboard_home(dashboard_client):
    """Test the dashboard home page."""
    response = dashboard_client.get("/")
    assert response.status_code == 200
    assert "WiseFlow Dashboard" in response.text


def test_dashboard_reports_page(dashboard_client, mock_dashboard_backend):
    """Test the dashboard reports page."""
    response = dashboard_client.get("/reports")
    assert response.status_code == 200
    assert "Reports" in response.text
    
    # Check that the get_reports method was called
    mock_dashboard_backend.get_reports.assert_called_once()


def test_dashboard_report_detail_page(dashboard_client, mock_dashboard_backend):
    """Test the dashboard report detail page."""
    response = dashboard_client.get("/reports/report-1")
    assert response.status_code == 200
    assert "Test Report 1" in response.text
    
    # Check that the get_report method was called with the correct arguments
    mock_dashboard_backend.get_report.assert_called_once_with("report-1")


def test_dashboard_create_report_page(dashboard_client):
    """Test the dashboard create report page."""
    response = dashboard_client.get("/reports/create")
    assert response.status_code == 200
    assert "Create Report" in response.text


def test_dashboard_create_report_submit(dashboard_client, mock_dashboard_backend):
    """Test submitting the dashboard create report form."""
    response = dashboard_client.post(
        "/reports/create",
        data={
            "title": "Test Report 3",
            "content": "This is test report 3",
            "tags": "test,report",
        }
    )
    assert response.status_code == 302  # Redirect after successful creation
    assert response.headers["location"] == "/reports/report-3"
    
    # Check that the create_report method was called with the correct arguments
    mock_dashboard_backend.create_report.assert_called_once_with(
        title="Test Report 3",
        content="This is test report 3",
        metadata={"tags": ["test", "report"]},
    )


def test_dashboard_edit_report_page(dashboard_client, mock_dashboard_backend):
    """Test the dashboard edit report page."""
    response = dashboard_client.get("/reports/report-1/edit")
    assert response.status_code == 200
    assert "Edit Report" in response.text
    assert "Test Report 1" in response.text
    
    # Check that the get_report method was called with the correct arguments
    mock_dashboard_backend.get_report.assert_called_once_with("report-1")


def test_dashboard_edit_report_submit(dashboard_client, mock_dashboard_backend):
    """Test submitting the dashboard edit report form."""
    response = dashboard_client.post(
        "/reports/report-1/edit",
        data={
            "title": "Updated Test Report 1",
            "content": "This is updated test report 1",
            "tags": "test,report,updated",
        }
    )
    assert response.status_code == 302  # Redirect after successful update
    assert response.headers["location"] == "/reports/report-1"
    
    # Check that the update_report method was called with the correct arguments
    mock_dashboard_backend.update_report.assert_called_once_with(
        report_id="report-1",
        title="Updated Test Report 1",
        content="This is updated test report 1",
        metadata={"tags": ["test", "report", "updated"]},
    )


def test_dashboard_delete_report(dashboard_client, mock_dashboard_backend):
    """Test deleting a report."""
    response = dashboard_client.post("/reports/report-1/delete")
    assert response.status_code == 302  # Redirect after successful deletion
    assert response.headers["location"] == "/reports"
    
    # Check that the delete_report method was called with the correct arguments
    mock_dashboard_backend.delete_report.assert_called_once_with("report-1")


def test_dashboard_searches_page(dashboard_client, mock_dashboard_backend):
    """Test the dashboard searches page."""
    response = dashboard_client.get("/searches")
    assert response.status_code == 200
    assert "Searches" in response.text
    
    # Check that the get_searches method was called
    mock_dashboard_backend.get_searches.assert_called_once()


def test_dashboard_search_detail_page(dashboard_client, mock_dashboard_backend):
    """Test the dashboard search detail page."""
    response = dashboard_client.get("/searches/search-1")
    assert response.status_code == 200
    assert "Test Query 1" in response.text
    
    # Check that the get_search method was called with the correct arguments
    mock_dashboard_backend.get_search.assert_called_once_with("search-1")


def test_dashboard_create_search_page(dashboard_client):
    """Test the dashboard create search page."""
    response = dashboard_client.get("/searches/create")
    assert response.status_code == 200
    assert "Create Search" in response.text


def test_dashboard_create_search_submit(dashboard_client, mock_dashboard_backend):
    """Test submitting the dashboard create search form."""
    response = dashboard_client.post(
        "/searches/create",
        data={
            "query": "Test Query 3",
            "tags": "test,search",
        }
    )
    assert response.status_code == 302  # Redirect after successful creation
    assert response.headers["location"] == "/searches/search-3"
    
    # Check that the create_search method was called with the correct arguments
    mock_dashboard_backend.create_search.assert_called_once_with(
        query="Test Query 3",
        metadata={"tags": ["test", "search"]},
    )


def test_dashboard_delete_search(dashboard_client, mock_dashboard_backend):
    """Test deleting a search."""
    response = dashboard_client.post("/searches/search-1/delete")
    assert response.status_code == 302  # Redirect after successful deletion
    assert response.headers["location"] == "/searches"
    
    # Check that the delete_search method was called with the correct arguments
    mock_dashboard_backend.delete_search.assert_called_once_with("search-1")


def test_dashboard_api_reports(dashboard_client, mock_dashboard_backend):
    """Test the dashboard API reports endpoint."""
    response = dashboard_client.get("/api/reports")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["id"] == "report-1"
    assert response.json()[1]["id"] == "report-2"
    
    # Check that the get_reports method was called
    mock_dashboard_backend.get_reports.assert_called_once()


def test_dashboard_api_report(dashboard_client, mock_dashboard_backend):
    """Test the dashboard API report endpoint."""
    response = dashboard_client.get("/api/reports/report-1")
    assert response.status_code == 200
    assert response.json()["id"] == "report-1"
    assert response.json()["title"] == "Test Report 1"
    
    # Check that the get_report method was called with the correct arguments
    mock_dashboard_backend.get_report.assert_called_once_with("report-1")


def test_dashboard_api_searches(dashboard_client, mock_dashboard_backend):
    """Test the dashboard API searches endpoint."""
    response = dashboard_client.get("/api/searches")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["id"] == "search-1"
    assert response.json()[1]["id"] == "search-2"
    
    # Check that the get_searches method was called
    mock_dashboard_backend.get_searches.assert_called_once()


def test_dashboard_api_search(dashboard_client, mock_dashboard_backend):
    """Test the dashboard API search endpoint."""
    response = dashboard_client.get("/api/searches/search-1")
    assert response.status_code == 200
    assert response.json()["id"] == "search-1"
    assert response.json()["query"] == "Test Query 1"
    
    # Check that the get_search method was called with the correct arguments
    mock_dashboard_backend.get_search.assert_called_once_with("search-1")

