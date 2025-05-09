"""
Tests for the LLM interface.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

# Create the directory structure if it doesn't exist
import os
os.makedirs(os.path.dirname(__file__), exist_ok=True)
with open(os.path.join(os.path.dirname(__file__), "__init__.py"), "w") as f:
    f.write("# LLM tests\n")

# Import the modules to test
from core.llms.litellm_wrapper import LiteLLMWrapper
from core.llms.openai_wrapper import OpenAIWrapper

class TestLiteLLMWrapper:
    """Tests for the LiteLLM wrapper."""
    
    @pytest.fixture
    def litellm_wrapper(self):
        """Create a LiteLLM wrapper for testing."""
        return LiteLLMWrapper(
            api_key="test-api-key",
            api_base="https://api.openai.com/v1",
            model="gpt-3.5-turbo"
        )
    
    @pytest.mark.asyncio
    @patch("core.llms.litellm_wrapper.litellm.acompletion")
    async def test_generate(self, mock_acompletion, litellm_wrapper):
        """Test the generate method."""
        # Set up the mock
        mock_acompletion.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Test response"
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
        
        # Call the method
        response = await litellm_wrapper.generate(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, world!"}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Check the response
        assert "text" in response
        assert response["text"] == "Test response"
        assert "metadata" in response
        assert response["metadata"]["model"] == "gpt-3.5-turbo"
        assert response["metadata"]["usage"]["prompt_tokens"] == 10
        assert response["metadata"]["usage"]["completion_tokens"] == 20
        assert response["metadata"]["usage"]["total_tokens"] == 30
        
        # Verify the mock was called with the correct arguments
        mock_acompletion.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, world!"}
            ],
            temperature=0.7,
            max_tokens=1000,
            api_key="test-api-key",
            api_base="https://api.openai.com/v1"
        )
    
    @pytest.mark.asyncio
    @patch("core.llms.litellm_wrapper.litellm.acompletion")
    async def test_generate_with_error(self, mock_acompletion, litellm_wrapper):
        """Test the generate method with an error."""
        # Set up the mock to raise an exception
        mock_acompletion.side_effect = Exception("Test error")
        
        # Call the method
        with pytest.raises(Exception) as excinfo:
            await litellm_wrapper.generate(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, world!"}
                ],
                temperature=0.7,
                max_tokens=1000
            )
        
        # Check the exception
        assert "Test error" in str(excinfo.value)

class TestOpenAIWrapper:
    """Tests for the OpenAI wrapper."""
    
    @pytest.fixture
    def openai_wrapper(self):
        """Create an OpenAI wrapper for testing."""
        return OpenAIWrapper(
            api_key="test-api-key",
            api_base="https://api.openai.com/v1",
            model="gpt-3.5-turbo"
        )
    
    @pytest.mark.asyncio
    @patch("core.llms.openai_wrapper.openai.ChatCompletion.acreate")
    async def test_generate(self, mock_acreate, openai_wrapper):
        """Test the generate method."""
        # Set up the mock
        mock_acreate.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Test response"
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
        
        # Call the method
        response = await openai_wrapper.generate(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, world!"}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Check the response
        assert "text" in response
        assert response["text"] == "Test response"
        assert "metadata" in response
        assert response["metadata"]["model"] == "gpt-3.5-turbo"
        assert response["metadata"]["usage"]["prompt_tokens"] == 10
        assert response["metadata"]["usage"]["completion_tokens"] == 20
        assert response["metadata"]["usage"]["total_tokens"] == 30
        
        # Verify the mock was called with the correct arguments
        mock_acreate.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, world!"}
            ],
            temperature=0.7,
            max_tokens=1000
        )
    
    @pytest.mark.asyncio
    @patch("core.llms.openai_wrapper.openai.ChatCompletion.acreate")
    async def test_generate_with_error(self, mock_acreate, openai_wrapper):
        """Test the generate method with an error."""
        # Set up the mock to raise an exception
        mock_acreate.side_effect = Exception("Test error")
        
        # Call the method
        with pytest.raises(Exception) as excinfo:
            await openai_wrapper.generate(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello, world!"}
                ],
                temperature=0.7,
                max_tokens=1000
            )
        
        # Check the exception
        assert "Test error" in str(excinfo.value)

