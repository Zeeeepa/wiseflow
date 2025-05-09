"""
System tests for performance.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from api_server import app as api_app
from dashboard.main import app as dashboard_app


@pytest.mark.system
@pytest.mark.performance
@pytest.mark.slow
class TestPerformance:
    """System tests for performance."""
    
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
    
    @pytest.fixture
    def mock_plugin_manager(self):
        """Create a mock dashboard plugin manager with controlled response times."""
        with patch("dashboard.main.dashboard_plugin_manager") as mock:
            # Define analyze_entities method with controlled response time
            def mock_analyze_entities(*args, **kwargs):
                # Simulate processing time
                time.sleep(0.2)
                return {
                    "entities": [
                        {"id": "entity-1", "name": "John Doe", "type": "person"},
                        {"id": "entity-2", "name": "Acme Corp", "type": "organization"},
                    ],
                    "relationships": [
                        {"id": "rel-1", "source": "entity-1", "target": "entity-2", "type": "works_for"},
                    ],
                }
            
            # Define analyze_trends method with controlled response time
            def mock_analyze_trends(*args, **kwargs):
                # Simulate processing time
                time.sleep(0.3)
                return {
                    "trends": [
                        {"id": "trend-1", "name": "Increasing Revenue", "direction": "up", "confidence": 0.8},
                        {"id": "trend-2", "name": "Market Share Decline", "direction": "down", "confidence": 0.7},
                    ],
                    "time_periods": [
                        {"id": "period-1", "name": "Q1 2023", "start": "2023-01-01", "end": "2023-03-31"},
                        {"id": "period-2", "name": "Q2 2023", "start": "2023-04-01", "end": "2023-06-30"},
                    ],
                }
            
            # Assign the mock methods
            mock.analyze_entities.side_effect = mock_analyze_entities
            mock.analyze_trends.side_effect = mock_analyze_trends
            
            yield mock
    
    def test_process_content_performance(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test the performance of processing content."""
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
        
        # Check the performance
        assert elapsed_time < 0.5, f"Processing content took too long: {elapsed_time:.2f} seconds"
    
    def test_process_content_with_reasoning_performance(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test the performance of processing content with multi-step reasoning."""
        # Measure the time to process content with reasoning
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
                "use_multi_step_reasoning": True,
            },
        )
        
        # Calculate the elapsed time
        elapsed_time = time.time() - start_time
        
        # Check the response
        assert response.status_code == 200
        assert "summary" in response.json()
        assert "reasoning_steps" in response.json()
        
        # Check the performance
        assert elapsed_time < 0.6, f"Processing content with reasoning took too long: {elapsed_time:.2f} seconds"
    
    def test_process_content_with_references_performance(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test the performance of processing content with contextual understanding."""
        # Measure the time to process content with references
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
                "references": "Test references",
            },
        )
        
        # Calculate the elapsed time
        elapsed_time = time.time() - start_time
        
        # Check the response
        assert response.status_code == 200
        assert "summary" in response.json()
        
        # Check the performance
        assert elapsed_time < 0.7, f"Processing content with references took too long: {elapsed_time:.2f} seconds"
    
    def test_batch_process_performance(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test the performance of batch processing."""
        # Measure the time to batch process content
        start_time = time.time()
        
        # Make the request
        response = api_client.post(
            "/api/v1/batch-process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "items": [
                    {"content": "Content 1", "content_type": "text"},
                    {"content": "Content 2", "content_type": "html"},
                ],
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "use_multi_step_reasoning": True,
                "max_concurrency": 2,
            },
        )
        
        # Calculate the elapsed time
        elapsed_time = time.time() - start_time
        
        # Check the response
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 2
        
        # Check the performance
        assert elapsed_time < 1.0, f"Batch processing took too long: {elapsed_time:.2f} seconds"
    
    def test_analyze_text_entity_performance(self, dashboard_client, mock_plugin_manager):
        """Test the performance of analyzing text with the entity analyzer."""
        # Measure the time to analyze text
        start_time = time.time()
        
        # Make the request
        response = dashboard_client.post(
            "/analyze",
            json={
                "text": "John Doe works for Acme Corp.",
                "analyzer_type": "entity",
                "config": {"include_relationships": True},
            },
        )
        
        # Calculate the elapsed time
        elapsed_time = time.time() - start_time
        
        # Check the response
        assert response.status_code == 200
        assert "entities" in response.json()
        assert "relationships" in response.json()
        
        # Check the performance
        assert elapsed_time < 0.5, f"Analyzing text with entity analyzer took too long: {elapsed_time:.2f} seconds"
    
    def test_analyze_text_trend_performance(self, dashboard_client, mock_plugin_manager):
        """Test the performance of analyzing text with the trend analyzer."""
        # Measure the time to analyze text
        start_time = time.time()
        
        # Make the request
        response = dashboard_client.post(
            "/analyze",
            json={
                "text": "Revenue increased in Q1 2023 but market share declined in Q2 2023.",
                "analyzer_type": "trend",
                "config": {"include_time_periods": True},
            },
        )
        
        # Calculate the elapsed time
        elapsed_time = time.time() - start_time
        
        # Check the response
        assert response.status_code == 200
        assert "trends" in response.json()
        assert "time_periods" in response.json()
        
        # Check the performance
        assert elapsed_time < 0.6, f"Analyzing text with trend analyzer took too long: {elapsed_time:.2f} seconds"
    
    def test_visualize_knowledge_graph_performance(self, dashboard_client, mock_plugin_manager):
        """Test the performance of visualizing a knowledge graph."""
        # Mock the visualization function
        with patch("dashboard.visualization.knowledge_graph.visualize_knowledge_graph") as mock_visualize:
            # Mock the visualization function with controlled response time
            def mock_visualize_knowledge_graph(*args, **kwargs):
                # Simulate processing time
                time.sleep(0.2)
                return {
                    "visualization_type": "knowledge_graph",
                    "data": {"nodes": [], "edges": []},
                    "html": "<div>Knowledge Graph Visualization</div>",
                }
            
            mock_visualize.side_effect = mock_visualize_knowledge_graph
            
            # Measure the time to visualize a knowledge graph
            start_time = time.time()
            
            # Make the request
            response = dashboard_client.post(
                "/visualize/knowledge-graph",
                json={
                    "text": "John Doe works for Acme Corp.",
                    "analyzer_type": "entity",
                    "config": {"theme": "light"},
                },
            )
            
            # Calculate the elapsed time
            elapsed_time = time.time() - start_time
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["visualization_type"] == "knowledge_graph"
            
            # Check the performance
            assert elapsed_time < 0.8, f"Visualizing knowledge graph took too long: {elapsed_time:.2f} seconds"
    
    def test_visualize_trend_performance(self, dashboard_client, mock_plugin_manager):
        """Test the performance of visualizing a trend."""
        # Mock the visualization function
        with patch("dashboard.visualization.trend.visualize_trend") as mock_visualize:
            # Mock the visualization function with controlled response time
            def mock_visualize_trend(*args, **kwargs):
                # Simulate processing time
                time.sleep(0.2)
                return {
                    "visualization_type": "trend",
                    "data": {"trends": [], "time_periods": []},
                    "html": "<div>Trend Visualization</div>",
                }
            
            mock_visualize.side_effect = mock_visualize_trend
            
            # Measure the time to visualize a trend
            start_time = time.time()
            
            # Make the request
            response = dashboard_client.post(
                "/visualize/trend",
                json={
                    "text": "Revenue increased in Q1 2023 but market share declined in Q2 2023.",
                    "analyzer_type": "trend",
                    "config": {"theme": "dark"},
                },
            )
            
            # Calculate the elapsed time
            elapsed_time = time.time() - start_time
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["visualization_type"] == "trend"
            
            # Check the performance
            assert elapsed_time < 0.9, f"Visualizing trend took too long: {elapsed_time:.2f} seconds"
    
    def test_webhook_trigger_performance(self, api_client, test_env_vars, mock_webhook_manager):
        """Test the performance of triggering webhooks."""
        # Measure the time to trigger webhooks
        start_time = time.time()
        
        # Make the request
        response = api_client.post(
            "/api/v1/webhooks/trigger",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event": "content.processed",
                "data": {"content_id": "123", "status": "success"},
                "async_mode": False,
            },
        )
        
        # Calculate the elapsed time
        elapsed_time = time.time() - start_time
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["event"] == "content.processed"
        
        # Check the performance
        assert elapsed_time < 0.5, f"Triggering webhooks took too long: {elapsed_time:.2f} seconds"
    
    def test_concurrent_requests_performance(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test the performance of handling concurrent requests."""
        import threading
        
        # Number of concurrent requests
        num_requests = 5
        
        # List to store response times
        response_times = []
        
        # Function to make a request and record the response time
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
            
            # Check the response
            assert response.status_code == 200
            
            # Record the response time
            response_times.append(elapsed_time)
        
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
        
        # Check the performance
        assert avg_response_time < 1.0, f"Average response time for concurrent requests was too high: {avg_response_time:.2f} seconds"
        
        # Check that all requests were processed
        assert len(response_times) == num_requests

