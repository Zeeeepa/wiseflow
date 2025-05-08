"""
Test the LLM error handling functionality.

This module tests the error handling, retry mechanism, timeout handling,
and rate limiting functionality of the LLM integration.
"""

import unittest
import asyncio
import logging
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.llms.litellm_wrapper import LiteLLMWrapper, litellm_llm, litellm_llm_async
from core.llms.exceptions import (
    LLMException, NetworkException, AuthenticationException, RateLimitException,
    TimeoutException, ContentFilterException, ContextLengthException,
    InvalidRequestException, ServiceUnavailableException, QuotaExceededException,
    UnknownException
)
from core.llms.utils import with_retry, with_timeout, RateLimiter, map_exception, is_transient_error


class TestLLMErrorHandling(unittest.TestCase):
    """Test the LLM error handling functionality."""
    
    def setUp(self):
        """Set up the test environment."""
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Create a LiteLLMWrapper instance
        self.wrapper = LiteLLMWrapper(
            default_model="gpt-3.5-turbo",
            timeout=5.0,
            max_retries=2,
            base_delay=0.1,
            max_delay=1.0
        )
        
        # Sample messages for testing
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ]
    
    @patch('core.llms.litellm_wrapper.completion')
    def test_successful_generation(self, mock_completion):
        """Test successful text generation."""
        # Mock the completion function
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, I'm an AI assistant!"
        mock_completion.return_value = mock_response
        
        # Call the function
        result = litellm_llm(
            messages=self.messages,
            model="gpt-3.5-turbo",
            logger=self.logger
        )
        
        # Verify the result
        self.assertEqual(result, "Hello, I'm an AI assistant!")
        mock_completion.assert_called_once()
    
    @patch('core.llms.litellm_wrapper.completion')
    def test_network_error_retry(self, mock_completion):
        """Test retry mechanism for network errors."""
        # Mock the completion function to raise a network error
        mock_completion.side_effect = Exception("Connection reset by peer")
        
        # Call the function and expect a NetworkException
        with self.assertRaises(NetworkException):
            litellm_llm(
                messages=self.messages,
                model="gpt-3.5-turbo",
                max_retries=2,
                logger=self.logger
            )
        
        # Verify that completion was called multiple times (initial + retries)
        self.assertEqual(mock_completion.call_count, 3)
    
    @patch('core.llms.litellm_wrapper.completion')
    def test_rate_limit_error(self, mock_completion):
        """Test handling of rate limit errors."""
        # Import the specific exception from litellm
        from litellm.exceptions import RateLimitError
        
        # Mock the completion function to raise a rate limit error
        mock_completion.side_effect = RateLimitError("Rate limit exceeded")
        
        # Call the function and expect a RateLimitException
        with self.assertRaises(RateLimitException):
            litellm_llm(
                messages=self.messages,
                model="gpt-3.5-turbo",
                max_retries=2,
                logger=self.logger
            )
        
        # Verify that completion was called multiple times (initial + retries)
        self.assertEqual(mock_completion.call_count, 3)
    
    @patch('core.llms.litellm_wrapper.completion')
    def test_context_length_error(self, mock_completion):
        """Test handling of context length errors."""
        # Import the specific exception from litellm
        from litellm.exceptions import ContextWindowExceededError
        
        # Mock the completion function to raise a context length error
        mock_completion.side_effect = ContextWindowExceededError("Context length exceeded")
        
        # Call the function and expect a ContextLengthException
        with self.assertRaises(ContextLengthException):
            litellm_llm(
                messages=self.messages,
                model="gpt-3.5-turbo",
                logger=self.logger
            )
        
        # Verify that completion was called only once (no retries for non-transient errors)
        self.assertEqual(mock_completion.call_count, 1)
    
    @patch('core.llms.litellm_wrapper.completion')
    def test_timeout_error(self, mock_completion):
        """Test handling of timeout errors."""
        # Mock the completion function to take longer than the timeout
        async def slow_completion(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate a slow response
            return MagicMock()
        
        mock_completion.side_effect = asyncio.TimeoutError("Request timed out")
        
        # Call the function and expect a TimeoutException
        with self.assertRaises(TimeoutException):
            litellm_llm(
                messages=self.messages,
                model="gpt-3.5-turbo",
                timeout=0.1,  # Very short timeout
                logger=self.logger
            )
    
    def test_rate_limiter(self):
        """Test the rate limiter functionality."""
        # Create a rate limiter with a low rate
        rate_limiter = RateLimiter(tokens_per_second=1.0, max_tokens=2)
        
        async def test_rate_limiting():
            # First request should go through immediately
            wait_time = await rate_limiter.acquire(1)
            self.assertLess(wait_time, 0.1)
            
            # Second request should also go through immediately
            wait_time = await rate_limiter.acquire(1)
            self.assertLess(wait_time, 0.1)
            
            # Third request should require waiting
            wait_time = await rate_limiter.acquire(1)
            self.assertGreater(wait_time, 0.5)  # Should wait at least 0.5 seconds
        
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(test_rate_limiting())
        loop.close()
    
    def test_exception_mapping(self):
        """Test mapping of exceptions to custom LLM exceptions."""
        # Test mapping of network errors
        network_error = Exception("Connection reset by peer")
        mapped_exception = map_exception(network_error)
        self.assertIsInstance(mapped_exception, NetworkException)
        
        # Test mapping of authentication errors
        auth_error = Exception("Invalid API key")
        mapped_exception = map_exception(auth_error)
        self.assertIsInstance(mapped_exception, AuthenticationException)
        
        # Test mapping of rate limit errors
        rate_limit_error = Exception("Rate limit exceeded")
        mapped_exception = map_exception(rate_limit_error)
        self.assertIsInstance(mapped_exception, RateLimitException)
        
        # Test mapping of timeout errors
        timeout_error = Exception("Request timed out")
        mapped_exception = map_exception(timeout_error)
        self.assertIsInstance(mapped_exception, TimeoutException)
        
        # Test mapping of content filter errors
        content_filter_error = Exception("Content policy violation")
        mapped_exception = map_exception(content_filter_error)
        self.assertIsInstance(mapped_exception, ContentFilterException)
        
        # Test mapping of context length errors
        context_length_error = Exception("Context length exceeded")
        mapped_exception = map_exception(context_length_error)
        self.assertIsInstance(mapped_exception, ContextLengthException)
        
        # Test mapping of unknown errors
        unknown_error = Exception("Some unknown error")
        mapped_exception = map_exception(unknown_error)
        self.assertIsInstance(mapped_exception, UnknownException)
    
    def test_transient_error_detection(self):
        """Test detection of transient errors."""
        # Transient errors
        self.assertTrue(is_transient_error(NetworkException("Network error")))
        self.assertTrue(is_transient_error(RateLimitException("Rate limit exceeded")))
        self.assertTrue(is_transient_error(TimeoutException("Request timed out")))
        self.assertTrue(is_transient_error(ServiceUnavailableException("Service unavailable")))
        
        # Non-transient errors
        self.assertFalse(is_transient_error(AuthenticationException("Authentication error")))
        self.assertFalse(is_transient_error(ContentFilterException("Content filter triggered")))
        self.assertFalse(is_transient_error(ContextLengthException("Context length exceeded")))
        self.assertFalse(is_transient_error(InvalidRequestException("Invalid request")))
        self.assertFalse(is_transient_error(QuotaExceededException("Quota exceeded")))
        self.assertFalse(is_transient_error(UnknownException("Unknown error")))


if __name__ == '__main__':
    unittest.main()

