"""
Tests for the specialized prompting module.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from core.llms.advanced.specialized_prompting import (
    SpecializedPromptProcessor,
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_MARKDOWN,
    CONTENT_TYPE_CODE,
    CONTENT_TYPE_ACADEMIC,
    CONTENT_TYPE_VIDEO,
    CONTENT_TYPE_SOCIAL,
    TASK_EXTRACTION,
    TASK_REASONING
)

class TestSpecializedPromptProcessor:
    """Tests for the SpecializedPromptProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create a SpecializedPromptProcessor for testing."""
        return SpecializedPromptProcessor(
            primary_model="gpt-3.5-turbo",
            secondary_model="gpt-3.5-turbo",
            api_key="test-api-key",
            api_base="https://api.openai.com/v1"
        )
    
    @pytest.mark.asyncio
    @patch("core.llms.advanced.specialized_prompting.LiteLLMWrapper")
    async def test_process_text_extraction(self, mock_litellm_wrapper, processor):
        """Test processing text content for extraction."""
        # Set up the mock
        mock_instance = mock_litellm_wrapper.return_value
        mock_instance.generate = AsyncMock()
        mock_instance.generate.return_value = {
            "text": "Extracted information",
            "metadata": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                },
                "latency": 0.5,
                "timestamp": "2023-01-01T00:00:00.000Z"
            }
        }
        
        # Call the method
        result = await processor.process(
            content="Test content",
            focus_point="Test focus point",
            content_type=CONTENT_TYPE_TEXT,
            explanation="Test explanation",
            use_multi_step_reasoning=False,
            references=None,
            metadata={}
        )
        
        # Check the result
        assert "summary" in result
        assert result["summary"] == "Extracted information"
        assert "metadata" in result
        assert result["metadata"]["model"] == "gpt-3.5-turbo"
        assert result["metadata"]["content_type"] == CONTENT_TYPE_TEXT
        assert result["metadata"]["task"] == TASK_EXTRACTION
        
        # Verify the mock was called with the correct arguments
        mock_litellm_wrapper.assert_called_once_with(
            api_key="test-api-key",
            api_base="https://api.openai.com/v1",
            model="gpt-3.5-turbo"
        )
        assert mock_instance.generate.call_count == 1
        # Check that the messages parameter contains the content and focus point
        messages = mock_instance.generate.call_args[1]["messages"]
        assert any("Test content" in message["content"] for message in messages)
        assert any("Test focus point" in message["content"] for message in messages)
    
    @pytest.mark.asyncio
    @patch("core.llms.advanced.specialized_prompting.LiteLLMWrapper")
    async def test_process_html_extraction(self, mock_litellm_wrapper, processor):
        """Test processing HTML content for extraction."""
        # Set up the mock
        mock_instance = mock_litellm_wrapper.return_value
        mock_instance.generate = AsyncMock()
        mock_instance.generate.return_value = {
            "text": "Extracted information from HTML",
            "metadata": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                },
                "latency": 0.5,
                "timestamp": "2023-01-01T00:00:00.000Z"
            }
        }
        
        # Call the method
        result = await processor.process(
            content="<html><body><h1>Test</h1><p>Content</p></body></html>",
            focus_point="Test focus point",
            content_type=CONTENT_TYPE_HTML,
            explanation="Test explanation",
            use_multi_step_reasoning=False,
            references=None,
            metadata={}
        )
        
        # Check the result
        assert "summary" in result
        assert result["summary"] == "Extracted information from HTML"
        assert "metadata" in result
        assert result["metadata"]["model"] == "gpt-3.5-turbo"
        assert result["metadata"]["content_type"] == CONTENT_TYPE_HTML
        assert result["metadata"]["task"] == TASK_EXTRACTION
    
    @pytest.mark.asyncio
    @patch("core.llms.advanced.specialized_prompting.LiteLLMWrapper")
    async def test_process_with_multi_step_reasoning(self, mock_litellm_wrapper, processor):
        """Test processing with multi-step reasoning."""
        # Set up the mock
        mock_instance = mock_litellm_wrapper.return_value
        mock_instance.generate = AsyncMock()
        
        # First call (extraction)
        mock_instance.generate.side_effect = [
            {
                "text": "Extracted information",
                "metadata": {
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30
                    },
                    "latency": 0.5,
                    "timestamp": "2023-01-01T00:00:00.000Z"
                }
            },
            # Second call (reasoning)
            {
                "text": "Reasoned information",
                "metadata": {
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "usage": {
                        "prompt_tokens": 15,
                        "completion_tokens": 25,
                        "total_tokens": 40
                    },
                    "latency": 0.6,
                    "timestamp": "2023-01-01T00:00:00.000Z"
                }
            }
        ]
        
        # Call the method
        result = await processor.process(
            content="Test content",
            focus_point="Test focus point",
            content_type=CONTENT_TYPE_TEXT,
            explanation="Test explanation",
            use_multi_step_reasoning=True,
            references=None,
            metadata={}
        )
        
        # Check the result
        assert "summary" in result
        assert result["summary"] == "Reasoned information"
        assert "metadata" in result
        assert result["metadata"]["model"] == "gpt-3.5-turbo"
        assert result["metadata"]["content_type"] == CONTENT_TYPE_TEXT
        assert result["metadata"]["task"] == TASK_REASONING
        
        # Verify the mock was called twice
        assert mock_instance.generate.call_count == 2
    
    @pytest.mark.asyncio
    @patch("core.llms.advanced.specialized_prompting.LiteLLMWrapper")
    async def test_process_with_references(self, mock_litellm_wrapper, processor):
        """Test processing with references."""
        # Set up the mock
        mock_instance = mock_litellm_wrapper.return_value
        mock_instance.generate = AsyncMock()
        mock_instance.generate.return_value = {
            "text": "Extracted information with references",
            "metadata": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                },
                "latency": 0.5,
                "timestamp": "2023-01-01T00:00:00.000Z"
            }
        }
        
        # Call the method
        result = await processor.process(
            content="Test content",
            focus_point="Test focus point",
            content_type=CONTENT_TYPE_TEXT,
            explanation="Test explanation",
            use_multi_step_reasoning=False,
            references=["Reference 1", "Reference 2"],
            metadata={}
        )
        
        # Check the result
        assert "summary" in result
        assert result["summary"] == "Extracted information with references"
        assert "metadata" in result
        
        # Verify the mock was called with references
        messages = mock_instance.generate.call_args[1]["messages"]
        assert any("Reference 1" in message["content"] for message in messages) or \
               any("Reference 2" in message["content"] for message in messages)
    
    @pytest.mark.asyncio
    @patch("core.llms.advanced.specialized_prompting.LiteLLMWrapper")
    async def test_process_with_error(self, mock_litellm_wrapper, processor):
        """Test processing with an error."""
        # Set up the mock to raise an exception
        mock_instance = mock_litellm_wrapper.return_value
        mock_instance.generate = AsyncMock()
        mock_instance.generate.side_effect = Exception("Test error")
        
        # Call the method
        with pytest.raises(Exception) as excinfo:
            await processor.process(
                content="Test content",
                focus_point="Test focus point",
                content_type=CONTENT_TYPE_TEXT,
                explanation="Test explanation",
                use_multi_step_reasoning=False,
                references=None,
                metadata={}
            )
        
        # Check the exception
        assert "Test error" in str(excinfo.value)

