#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for the LLM integration in WiseFlow.

This module contains unit tests for the various components of the LLM integration,
including error handling, caching, token management, and model fallback.
"""

import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import json
import tempfile
import shutil

# Import components to test
from core.llms.error_handling import (
    with_retries,
    LLMError,
    RateLimitError,
    map_provider_error
)

from core.llms.caching import (
    LLMCache,
    cached_llm_call
)

from core.llms.token_management import (
    TokenCounter,
    TokenOptimizer,
    TokenUsageTracker
)

from core.llms.model_management import (
    ModelCapabilities,
    ModelSelector,
    ModelFailoverManager,
    with_model_fallback
)

from core.llms import llm_manager

class TestErrorHandling(unittest.TestCase):
    """Tests for the error handling module."""
    
    async def test_with_retries_success(self):
        """Test successful function call with retries."""
        mock_func = AsyncMock(return_value="success")
        result = await with_retries(mock_func, "arg1", "arg2", kwarg1="value1")
        self.assertEqual(result, "success")
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
    
    async def test_with_retries_non_retryable_error(self):
        """Test non-retryable error."""
        mock_func = AsyncMock(side_effect=ValueError("test error"))
        with self.assertRaises(ValueError):
            await with_retries(mock_func, "arg1")
        self.assertEqual(mock_func.call_count, 1)
    
    async def test_with_retries_retryable_error(self):
        """Test retryable error with eventual success."""
        mock_func = AsyncMock(side_effect=[RateLimitError("rate limit"), "success"])
        result = await with_retries(
            mock_func, "arg1",
            max_retries=3,
            initial_backoff=0.01,  # Small value for faster tests
            retryable_errors=[RateLimitError]
        )
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 2)
    
    async def test_with_retries_max_retries_exceeded(self):
        """Test max retries exceeded."""
        mock_func = AsyncMock(side_effect=RateLimitError("rate limit"))
        with self.assertRaises(RateLimitError):
            await with_retries(
                mock_func, "arg1",
                max_retries=2,
                initial_backoff=0.01,  # Small value for faster tests
                retryable_errors=[RateLimitError]
            )
        self.assertEqual(mock_func.call_count, 3)  # Initial call + 2 retries
    
    def test_map_provider_error(self):
        """Test mapping provider-specific errors."""
        # OpenAI errors
        openai_error = Exception("rate limit exceeded")
        mapped_error = map_provider_error("openai", openai_error)
        self.assertIsInstance(mapped_error, RateLimitError)
        
        # Unknown provider
        unknown_error = Exception("unknown error")
        mapped_error = map_provider_error("unknown", unknown_error)
        self.assertEqual(str(mapped_error), "Unknown error (unknown): unknown error")

class TestCaching(unittest.TestCase):
    """Tests for the caching module."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = LLMCache(cache_dir=self.temp_dir, ttl=60)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    async def test_cache_get_set(self):
        """Test getting and setting cache entries."""
        messages = [{"role": "user", "content": "test message"}]
        model = "test-model"
        
        # Initially not in cache
        result = await self.cache.get(messages, model)
        self.assertIsNone(result)
        
        # Set in cache
        await self.cache.set(messages, model, "test response")
        
        # Now should be in cache
        result = await self.cache.get(messages, model)
        self.assertEqual(result, "test response")
    
    async def test_cache_expiration(self):
        """Test cache entry expiration."""
        messages = [{"role": "user", "content": "test message"}]
        model = "test-model"
        
        # Set in cache with very short TTL
        cache = LLMCache(cache_dir=self.temp_dir, ttl=0.1)  # 100ms TTL
        await cache.set(messages, model, "test response")
        
        # Should be in cache initially
        result = await cache.get(messages, model)
        self.assertEqual(result, "test response")
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should be expired now
        result = await cache.get(messages, model)
        self.assertIsNone(result)
    
    async def test_cached_llm_call(self):
        """Test cached LLM call."""
        messages = [{"role": "user", "content": "test message"}]
        model = "test-model"
        
        # Mock LLM function
        mock_llm_func = AsyncMock(return_value="test response")
        
        # First call (cache miss)
        result = await cached_llm_call(
            mock_llm_func,
            messages, model,
            use_cache=True,
            cache=self.cache
        )
        self.assertEqual(result, "test response")
        mock_llm_func.assert_called_once_with(messages, model)
        
        # Reset mock
        mock_llm_func.reset_mock()
        
        # Second call (cache hit)
        result = await cached_llm_call(
            mock_llm_func,
            messages, model,
            use_cache=True,
            cache=self.cache
        )
        self.assertEqual(result, "test response")
        mock_llm_func.assert_not_called()  # Should not call the function again

class TestTokenManagement(unittest.TestCase):
    """Tests for the token management module."""
    
    def setUp(self):
        """Set up test environment."""
        self.token_counter = TokenCounter()
        self.token_optimizer = TokenOptimizer(self.token_counter)
        self.token_tracker = TokenUsageTracker()
    
    def test_token_counting(self):
        """Test token counting."""
        # Test text token counting
        text = "This is a test message."
        count = self.token_counter.count_tokens(text)
        self.assertGreater(count, 0)
        
        # Test message token counting
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ]
        count = self.token_counter.count_message_tokens(messages)
        self.assertGreater(count, 0)
    
    def test_token_optimization(self):
        """Test token optimization."""
        # Test prompt optimization
        long_prompt = "This is a test message. " * 100
        max_tokens = 20
        optimized = self.token_optimizer.optimize_prompt(long_prompt, max_tokens)
        self.assertLessEqual(self.token_counter.count_tokens(optimized), max_tokens)
        
        # Test message optimization
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "The capital of France is Paris."},
            {"role": "user", "content": "What about Germany?"}
        ]
        max_tokens = 15
        optimized = self.token_optimizer.optimize_messages(messages, max_tokens)
        self.assertLessEqual(self.token_counter.count_message_tokens(optimized), max_tokens)
    
    def test_token_usage_tracking(self):
        """Test token usage tracking."""
        # Track usage
        self.token_tracker.track_usage("gpt-3.5-turbo", 100, 50)
        
        # Get usage summary
        summary = self.token_tracker.get_usage_summary()
        self.assertEqual(summary["total_prompt_tokens"], 100)
        self.assertEqual(summary["total_completion_tokens"], 50)
        self.assertEqual(summary["total_tokens"], 150)
        
        # Estimate cost
        estimate = self.token_tracker.estimate_cost("gpt-3.5-turbo", "Test message")
        self.assertIn("estimated_cost", estimate)

class TestModelManagement(unittest.TestCase):
    """Tests for the model management module."""
    
    def setUp(self):
        """Set up test environment."""
        self.model_capabilities = ModelCapabilities()
        self.model_selector = ModelSelector(
            primary_model="gpt-3.5-turbo",
            secondary_model="gpt-4",
            model_capabilities=self.model_capabilities
        )
        self.failover_manager = ModelFailoverManager(
            model_capabilities=self.model_capabilities,
            model_selector=self.model_selector
        )
    
    def test_model_capabilities(self):
        """Test model capabilities."""
        # Test getting context length
        context_length = self.model_capabilities.get_context_length("gpt-3.5-turbo")
        self.assertEqual(context_length, 4096)
        
        # Test checking feature support
        supports_functions = self.model_capabilities.supports_feature("gpt-4", "functions")
        self.assertTrue(supports_functions)
        
        # Test getting performance rating
        rating = self.model_capabilities.get_performance_rating("gpt-4", "reasoning")
        self.assertEqual(rating, "high")
    
    def test_model_selector(self):
        """Test model selector."""
        # Test selecting model based on task
        model = self.model_selector.select_model("extraction")
        self.assertEqual(model, "gpt-3.5-turbo")  # Should use primary model
        
        # Test selecting model based on token count
        model = self.model_selector.select_model("extraction", token_count=10000)
        self.assertNotEqual(model, "gpt-3.5-turbo")  # Should use a model with larger context
        
        # Test selecting model based on features
        model = self.model_selector.select_model(
            "vision",
            required_features=["vision"]
        )
        self.assertEqual(model, "gpt-4-vision-preview")  # Should use a model with vision support
    
    def test_model_failover(self):
        """Test model failover."""
        # Mark primary model as failed
        self.failover_manager.mark_model_failure(
            "gpt-3.5-turbo",
            RateLimitError("rate limit")
        )
        
        # Get fallback model
        fallback_model = self.failover_manager.get_fallback_model(
            "gpt-3.5-turbo",
            "extraction"
        )
        self.assertEqual(fallback_model, "gpt-4")  # Should use secondary model
        
        # Mark secondary model as failed
        self.failover_manager.mark_model_failure(
            "gpt-4",
            RateLimitError("rate limit")
        )
        
        # Get another fallback model
        fallback_model = self.failover_manager.get_fallback_model(
            "gpt-3.5-turbo",
            "extraction"
        )
        self.assertNotEqual(fallback_model, "gpt-3.5-turbo")  # Should use another model
        self.assertNotEqual(fallback_model, "gpt-4")  # Should not use failed models
    
    async def test_with_model_fallback(self):
        """Test with_model_fallback function."""
        # Mock LLM function
        mock_llm_func = AsyncMock(side_effect=[
            RateLimitError("rate limit"),  # First call fails
            "fallback response"  # Second call succeeds
        ])
        
        # Mock failover manager
        mock_failover_manager = MagicMock()
        mock_failover_manager.get_fallback_model.side_effect = [
            "gpt-3.5-turbo",  # First model (will fail)
            "gpt-4"  # Fallback model (will succeed)
        ]
        mock_failover_manager.mark_model_failure = MagicMock()
        mock_failover_manager.mark_model_success = MagicMock()
        
        # Call with fallback
        response, model_used = await with_model_fallback(
            mock_llm_func,
            [{"role": "user", "content": "test"}],
            "gpt-3.5-turbo",
            mock_failover_manager
        )
        
        self.assertEqual(response, "fallback response")
        self.assertEqual(model_used, "gpt-4")
        self.assertEqual(mock_llm_func.call_count, 2)
        mock_failover_manager.mark_model_failure.assert_called_once()
        mock_failover_manager.mark_model_success.assert_called_once()

class TestLLMManager(unittest.TestCase):
    """Tests for the LLM manager."""
    
    @patch('core.llms.openai_llm')
    async def test_generate(self, mock_openai_llm):
        """Test generate method."""
        mock_openai_llm.return_value = "test response"
        
        # Test with string prompt
        response = await llm_manager.generate(
            prompt="test prompt",
            model="gpt-3.5-turbo",
            provider="openai",
            use_fallback=False
        )
        
        self.assertEqual(response, "test response")
        mock_openai_llm.assert_called_once()
    
    @patch('core.llms.openai_llm_with_fallback')
    async def test_generate_with_fallback(self, mock_openai_llm_with_fallback):
        """Test generate method with fallback."""
        mock_openai_llm_with_fallback.return_value = ("test response", "gpt-4")
        
        # Test with fallback
        response, model_used = await llm_manager.generate(
            prompt="test prompt",
            model="gpt-3.5-turbo",
            provider="openai",
            use_fallback=True
        )
        
        self.assertEqual(response, "test response")
        self.assertEqual(model_used, "gpt-4")
        mock_openai_llm_with_fallback.assert_called_once()
    
    @patch('core.llms.token_counter.count_tokens')
    def test_get_token_count(self, mock_count_tokens):
        """Test get_token_count method."""
        mock_count_tokens.return_value = 10
        
        # Test with string
        count = llm_manager.get_token_count("test text")
        self.assertEqual(count, 10)
        mock_count_tokens.assert_called_once()
    
    @patch('core.llms.token_optimizer.optimize_prompt')
    def test_optimize_prompt(self, mock_optimize_prompt):
        """Test optimize_prompt method."""
        mock_optimize_prompt.return_value = "optimized prompt"
        
        # Test optimize prompt
        optimized = llm_manager.optimize_prompt("test prompt", 100)
        self.assertEqual(optimized, "optimized prompt")
        mock_optimize_prompt.assert_called_once()
    
    @patch('core.llms.token_usage_tracker.estimate_cost')
    def test_estimate_cost(self, mock_estimate_cost):
        """Test estimate_cost method."""
        mock_estimate_cost.return_value = {"estimated_cost": 0.01}
        
        # Test estimate cost
        estimate = llm_manager.estimate_cost("test prompt")
        self.assertEqual(estimate["estimated_cost"], 0.01)
        mock_estimate_cost.assert_called_once()
    
    @patch('core.llms.token_usage_tracker.get_usage_summary')
    def test_get_usage_summary(self, mock_get_usage_summary):
        """Test get_usage_summary method."""
        mock_get_usage_summary.return_value = {"total_tokens": 100}
        
        # Test get usage summary
        summary = llm_manager.get_usage_summary()
        self.assertEqual(summary["total_tokens"], 100)
        mock_get_usage_summary.assert_called_once()
    
    @patch('core.llms.llm_cache.get_stats')
    def test_get_cache_stats(self, mock_get_stats):
        """Test get_cache_stats method."""
        mock_get_stats.return_value = {"hit_rate": 0.5}
        
        # Test get cache stats
        stats = llm_manager.get_cache_stats()
        self.assertEqual(stats["hit_rate"], 0.5)
        mock_get_stats.assert_called_once()
    
    @patch('core.llms.llm_cache.invalidate')
    async def test_invalidate_cache(self, mock_invalidate):
        """Test invalidate_cache method."""
        # Test invalidate cache
        await llm_manager.invalidate_cache()
        mock_invalidate.assert_called_once_with(None)
        
        # Test invalidate specific key
        mock_invalidate.reset_mock()
        await llm_manager.invalidate_cache("test_key")
        mock_invalidate.assert_called_once_with("test_key")

def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestErrorHandling)
    suite.addTests(loader.loadTestsFromTestCase(TestCaching))
    suite.addTests(loader.loadTestsFromTestCase(TestTokenManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestModelManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestLLMManager))
    
    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    # Set up asyncio event loop for async tests
    loop = asyncio.get_event_loop()
    
    # Run the tests
    loop.run_until_complete(asyncio.gather(
        *[test() for test in [
            TestErrorHandling().test_with_retries_success,
            TestErrorHandling().test_with_retries_non_retryable_error,
            TestErrorHandling().test_with_retries_retryable_error,
            TestErrorHandling().test_with_retries_max_retries_exceeded,
            TestCaching().test_cache_get_set,
            TestCaching().test_cache_expiration,
            TestCaching().test_cached_llm_call,
            TestModelManagement().test_with_model_fallback,
            TestLLMManager().test_generate,
            TestLLMManager().test_generate_with_fallback,
            TestLLMManager().test_invalidate_cache
        ]]
    ))
    
    # Run synchronous tests
    unittest.main()

