"""
Non-functional validation tests for the WiseFlow system.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from api_server import app as api_app
from dashboard.main import app as dashboard_app


@pytest.mark.validation
@pytest.mark.non_functional
class TestNonFunctionalValidation:
    """Non-functional validation tests for the WiseFlow system."""
    
    @pytest.fixture
    def mock_specialized_prompt_processor(self):
        """Create a mock specialized prompt processor with controlled response times."""
        with patch("api_server.SpecializedPromptProcessor") as mock:
            processor = MagicMock()
            
            # Define process method with controlled response time
            async def mock_process(*args, **kwargs):
                # Simulate processing time
                time.sleep(0.1)
                return {
                    "summary": "Test summary",
                    "metadata": {"key": "value"},
                }
            
            # Define multi_step_reasoning method with controlled response time
            async def mock_multi_step_reasoning(*args, **kwargs):
                # Simulate processing time
                time.sleep(0.2)
                return {
                    "summary": "Test reasoning summary",
                    "reasoning_steps": ["Step 1", "Step 2"],
                    "metadata": {"key": "value"},
                }
            
            # Define contextual_understanding method with controlled response time
            async def mock_contextual_understanding(*args, **kwargs):
                # Simulate processing time
                time.sleep(0.3)
                return {
                    "summary": "Test contextual summary",
                    "metadata": {"key": "value"},
                }
            
            # Define batch_process method with controlled response time
            async def mock_batch_process(*args, **kwargs):
                # Simulate processing time
                time.sleep(0.5)
                return [
                    {"summary": "Summary 1", "metadata": {"key": "value1"}},
                    {"summary": "Summary 2", "metadata": {"key": "value2"}},
                ]
            
            # Assign the mock methods
            processor.process.side_effect = mock_process
            processor.multi_step_reasoning.side_effect = mock_multi_step_reasoning
            processor.contextual_understanding.side_effect = mock_contextual_understanding
            processor.batch_process.side_effect = mock_batch_process
            
            mock.return_value = processor
            yield processor
    
    @pytest.fixture
    def mock_webhook_manager(self):
        """Create a mock webhook manager."""
        with patch("api_server.get_webhook_manager") as mock:
            manager = MagicMock()
            manager.register_webhook.return_value = "test-webhook-id"
            manager.trigger_webhook.return_value = [
                {"webhook_id": "webhook1", "status": "success"},
                {"webhook_id": "webhook2", "status": "success"},
            ]
            mock.return_value = manager
            yield manager
    
    def test_response_time_validation(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test that the API response time meets the requirements."""
        # Define the maximum acceptable response time
        max_response_time = 0.5  # seconds
        
        # Measure the time to process content
        start_time = time.time()
        
        # Make the request
        response = api_client.post(
            "/api/v1/process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": False,
            },
        )
        
        # Calculate the elapsed time
        elapsed_time = time.time() - start_time
        
        # Check the response
        assert response.status_code == 200
        assert "summary" in response.json()
        
        # Validate the response time
        assert elapsed_time < max_response_time, f"Response time ({elapsed_time:.2f}s) exceeds maximum acceptable time ({max_response_time:.2f}s)"
    
    def test_concurrent_requests_validation(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test that the API can handle concurrent requests."""
        import threading
        
        # Define the number of concurrent requests
        num_requests = 5
        
        # Define the maximum acceptable average response time
        max_avg_response_time = 1.0  # seconds
        
        # List to store response times and status codes
        response_times = []
        status_codes = []
        
        # Function to make a request and record the response time and status code
        def make_request():
            start_time = time.time()
            
            # Make the request
            response = api_client.post(
                "/api/v1/process",
                headers={"X-API-Key": "test-api-key"},
                json={
                    "content": "Test content",
                    "focus_point": "Test focus",
                    "explanation": "Test explanation",
                    "content_type": "text",
                    "use_multi_step_reasoning": False,
                },
            )
            
            # Calculate the elapsed time
            elapsed_time = time.time() - start_time
            
            # Record the response time and status code
            response_times.append(elapsed_time)
            status_codes.append(response.status_code)
        
        # Create threads for concurrent requests
        threads = []
        for _ in range(num_requests):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start the threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Calculate the average response time
        avg_response_time = sum(response_times) / len(response_times)
        
        # Validate the response times and status codes
        assert all(status_code == 200 for status_code in status_codes), "Not all requests were successful"
        assert len(response_times) == num_requests, f"Expected {num_requests} responses, got {len(response_times)}"
        assert avg_response_time < max_avg_response_time, f"Average response time ({avg_response_time:.2f}s) exceeds maximum acceptable time ({max_avg_response_time:.2f}s)"
    
    def test_memory_usage_validation(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test that the API memory usage is within acceptable limits."""
        import psutil
        import os
        
        # Define the maximum acceptable memory increase
        max_memory_increase = 50 * 1024 * 1024  # 50 MB
        
        # Get the current process
        process = psutil.Process(os.getpid())
        
        # Get the initial memory usage
        initial_memory = process.memory_info().rss
        
        # Make multiple requests to simulate load
        for _ in range(10):
            response = api_client.post(
                "/api/v1/process",
                headers={"X-API-Key": "test-api-key"},
                json={
                    "content": "Test content",
                    "focus_point": "Test focus",
                    "explanation": "Test explanation",
                    "content_type": "text",
                    "use_multi_step_reasoning": False,
                },
            )
            
            # Check the response
            assert response.status_code == 200
        
        # Get the final memory usage
        final_memory = process.memory_info().rss
        
        # Calculate the memory increase
        memory_increase = final_memory - initial_memory
        
        # Validate the memory usage
        assert memory_increase < max_memory_increase, f"Memory increase ({memory_increase / (1024 * 1024):.2f} MB) exceeds maximum acceptable increase ({max_memory_increase / (1024 * 1024):.2f} MB)"
    
    def test_error_handling_validation(self, api_client, test_env_vars):
        """Test that the API handles errors gracefully."""
        # Mock the specialized prompt processor to raise an exception
        with patch("api_server.ContentProcessorManager.get_instance") as mock_get_instance:
            processor = MagicMock()
            processor.process_content.side_effect = Exception("Test error")
            mock_get_instance.return_value = processor
            
            # Make the request
            response = api_client.post(
                "/api/v1/process",
                headers={"X-API-Key": "test-api-key"},
                json={
                    "content": "Test content",
                    "focus_point": "Test focus",
                    "explanation": "Test explanation",
                    "content_type": "text",
                    "use_multi_step_reasoning": False,
                },
            )
            
            # Check the response
            assert response.status_code == 500
            assert "Error processing content" in response.json()["detail"]
            assert "Test error" in response.json()["detail"]
    
    def test_api_key_security_validation(self, api_client, test_env_vars):
        """Test that the API key security is enforced."""
        # Make the request without an API key
        response = api_client.post(
            "/api/v1/process",
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": False,
            },
        )
        
        # Check the response
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
        
        # Make the request with an invalid API key
        response = api_client.post(
            "/api/v1/process",
            headers={"X-API-Key": "invalid-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": False,
            },
        )
        
        # Check the response
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
        
        # Make the request with a valid API key
        response = api_client.post(
            "/api/v1/process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": False,
            },
        )
        
        # Check the response
        assert response.status_code == 200
    
    def test_cors_validation(self, api_client):
        """Test that CORS is properly configured."""
        # Make a preflight request
        response = api_client.options(
            "/api/v1/process",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-API-Key",
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "Access-Control-Allow-Methods" in response.headers
        assert "POST" in response.headers["Access-Control-Allow-Methods"]
        assert "Access-Control-Allow-Headers" in response.headers
        assert "Content-Type" in response.headers["Access-Control-Allow-Headers"]
        assert "X-API-Key" in response.headers["Access-Control-Allow-Headers"]
    
    def test_response_format_validation(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test that the API response format is consistent."""
        # Make the request
        response = api_client.post(
            "/api/v1/process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": False,
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "summary" in response.json()
        assert "metadata" in response.json()
        assert "timestamp" in response.json()
        
        # Make the request with multi-step reasoning
        response = api_client.post(
            "/api/v1/process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": True,
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "summary" in response.json()
        assert "reasoning_steps" in response.json()
        assert "metadata" in response.json()
        assert "timestamp" in response.json()
    
    def test_webhook_security_validation(self, api_client, test_env_vars, mock_webhook_manager):
        """Test that webhook security is enforced."""
        # Make the request to register a webhook
        response = api_client.post(
            "/api/v1/webhooks",
            headers={"X-API-Key": "test-api-key"},
            json={
                "endpoint": "https://example.com/webhook",
                "events": ["content.processed", "batch.completed"],
                "headers": {"X-Custom-Header": "value"},
                "secret": "webhook-secret",
                "description": "Test webhook",
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "webhook_id" in response.json()
        
        # Verify that the webhook manager was called with the correct parameters
        mock_webhook_manager.register_webhook.assert_called_once_with(
            endpoint="https://example.com/webhook",
            events=["content.processed", "batch.completed"],
            headers={"X-Custom-Header": "value"},
            secret="webhook-secret",
            description="Test webhook",
        )
    
    def test_dashboard_security_validation(self, dashboard_client):
        """Test that dashboard security is enforced."""
        # Mock the dashboard manager
        with patch("dashboard.main.dashboard_manager") as mock_manager:
            # Mock the get_dashboard method to return None for a non-existent dashboard
            mock_manager.get_dashboard.return_value = None
            
            # Make the request to get a non-existent dashboard
            response = dashboard_client.get("/dashboards/nonexistent-id")
            
            # Check the response
            assert response.status_code == 404
            assert "Dashboard not found" in response.json()["detail"]
            
            # Mock the get_dashboard method to return a dashboard for a specific user
            mock_dashboard = MagicMock()
            mock_dashboard.to_dict.return_value = {
                "id": "test-dashboard-id",
                "name": "Test Dashboard",
                "layout": "grid",
                "user_id": "test-user",
                "visualizations": [],
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
            }
            mock_manager.get_dashboard.return_value = mock_dashboard
            
            # Make the request to get a dashboard for a specific user
            response = dashboard_client.get("/dashboards/test-dashboard-id")
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["user_id"] == "test-user"
            
            # Mock the get_all_dashboards method to return dashboards for a specific user
            mock_manager.get_all_dashboards.return_value = [mock_dashboard]
            
            # Make the request to get all dashboards for a specific user
            response = dashboard_client.get("/dashboards?user_id=test-user")
            
            # Check the response
            assert response.status_code == 200
            assert len(response.json()) == 1
            assert response.json()[0]["user_id"] == "test-user"

