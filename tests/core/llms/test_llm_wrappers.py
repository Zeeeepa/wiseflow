"""
Unit tests for the LLM wrappers.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.llms.openai_wrapper import openai_llm
from core.llms.litellm_wrapper import litellm_call


@pytest.mark.unit
class TestOpenAIWrapper:
    """Test the OpenAI wrapper."""
    
    @pytest.mark.asyncio
    @patch("core.llms.openai_wrapper.openai.ChatCompletion.acreate")
    async def test_openai_llm(self, mock_acreate):
        """Test the openai_llm function."""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test response."
        mock_acreate.return_value = mock_response
        
        # Call the function
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ]
        response = await openai_llm(messages)
        
        # Check the result
        assert response == "This is a test response."
        mock_acreate.assert_called_once()
        
        # Check the arguments
        args, kwargs = mock_acreate.call_args
        assert kwargs["model"] == "gpt-3.5-turbo"
        assert kwargs["messages"] == messages
        assert kwargs["temperature"] == 0.7
        assert kwargs["max_tokens"] == 1000
    
    @pytest.mark.asyncio
    @patch("core.llms.openai_wrapper.openai.ChatCompletion.acreate")
    async def test_openai_llm_with_params(self, mock_acreate):
        """Test the openai_llm function with custom parameters."""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test response."
        mock_acreate.return_value = mock_response
        
        # Call the function with custom parameters
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ]
        response = await openai_llm(
            messages,
            model="gpt-4",
            temperature=0.5,
            max_tokens=500,
            top_p=0.9,
            frequency_penalty=0.2,
            presence_penalty=0.1
        )
        
        # Check the result
        assert response == "This is a test response."
        mock_acreate.assert_called_once()
        
        # Check the arguments
        args, kwargs = mock_acreate.call_args
        assert kwargs["model"] == "gpt-4"
        assert kwargs["messages"] == messages
        assert kwargs["temperature"] == 0.5
        assert kwargs["max_tokens"] == 500
        assert kwargs["top_p"] == 0.9
        assert kwargs["frequency_penalty"] == 0.2
        assert kwargs["presence_penalty"] == 0.1
    
    @pytest.mark.asyncio
    @patch("core.llms.openai_wrapper.openai.ChatCompletion.acreate")
    async def test_openai_llm_error_handling(self, mock_acreate):
        """Test error handling in the openai_llm function."""
        # Set up the mock to raise an exception
        mock_acreate.side_effect = Exception("Test error")
        
        # Call the function
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ]
        
        # Check that the function handles the error
        with pytest.raises(Exception, match="Test error"):
            await openai_llm(messages)


@pytest.mark.unit
class TestLiteLLMWrapper:
    """Test the LiteLLM wrapper."""
    
    @pytest.mark.asyncio
    @patch("core.llms.litellm_wrapper.litellm.acompletion")
    async def test_litellm_call(self, mock_acompletion):
        """Test the litellm_call function."""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test response."
        mock_acompletion.return_value = mock_response
        
        # Call the function
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ]
        response = await litellm_call(messages)
        
        # Check the result
        assert response == "This is a test response."
        mock_acompletion.assert_called_once()
        
        # Check the arguments
        args, kwargs = mock_acompletion.call_args
        assert kwargs["model"] == "gpt-3.5-turbo"
        assert kwargs["messages"] == messages
        assert kwargs["temperature"] == 0.7
        assert kwargs["max_tokens"] == 1000
    
    @pytest.mark.asyncio
    @patch("core.llms.litellm_wrapper.litellm.acompletion")
    async def test_litellm_call_with_params(self, mock_acompletion):
        """Test the litellm_call function with custom parameters."""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test response."
        mock_acompletion.return_value = mock_response
        
        # Call the function with custom parameters
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ]
        response = await litellm_call(
            messages,
            model="anthropic/claude-3-opus",
            temperature=0.5,
            max_tokens=500,
            top_p=0.9,
            frequency_penalty=0.2,
            presence_penalty=0.1
        )
        
        # Check the result
        assert response == "This is a test response."
        mock_acompletion.assert_called_once()
        
        # Check the arguments
        args, kwargs = mock_acompletion.call_args
        assert kwargs["model"] == "anthropic/claude-3-opus"
        assert kwargs["messages"] == messages
        assert kwargs["temperature"] == 0.5
        assert kwargs["max_tokens"] == 500
        assert kwargs["top_p"] == 0.9
        assert kwargs["frequency_penalty"] == 0.2
        assert kwargs["presence_penalty"] == 0.1
    
    @pytest.mark.asyncio
    @patch("core.llms.litellm_wrapper.litellm.acompletion")
    async def test_litellm_call_error_handling(self, mock_acompletion):
        """Test error handling in the litellm_call function."""
        # Set up the mock to raise an exception
        mock_acompletion.side_effect = Exception("Test error")
        
        # Call the function
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ]
        
        # Check that the function handles the error
        with pytest.raises(Exception, match="Test error"):
            await litellm_call(messages)

