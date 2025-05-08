#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for the processor fixes.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime
import json

from core.connectors import DataItem
from core.plugins.processors import ProcessorBase, ProcessedData
from core.plugins.processors.text.text_processor import TextProcessor


class TestProcessorBaseFixes(unittest.TestCase):
    """Test cases for the ProcessorBase fixes."""

    class MockProcessor(ProcessorBase):
        """Mock processor for testing."""
        
        name = "mock_processor"
        description = "Mock processor for testing"
        processor_type = "mock"
        
        def __init__(self, config=None, should_fail=False):
            super().__init__(config)
            self.should_fail = should_fail
            self.process_called = False
            
        def process(self, data_item, params=None):
            """Mock process method."""
            self.process_called = True
            if self.should_fail:
                raise Exception("Mock processing failure")
            
            return ProcessedData(
                original_item=data_item,
                processed_content=[
                    {
                        "content": f"Processed: {data_item.content}",
                        "type": "text"
                    }
                ],
                metadata={"source": data_item.source_id}
            )

    def test_initialization(self):
        """Test processor initialization."""
        processor = self.MockProcessor({"model": "test-model"})
        self.assertEqual(processor.config["model"], "test-model")
        self.assertEqual(processor.error_count, 0)
        self.assertIsNone(processor.last_run_time)

    def test_process(self):
        """Test process method."""
        processor = self.MockProcessor()
        data_item = DataItem(
            source_id="test-1",
            content="Test content",
            metadata={"key": "value"}
        )
        
        result = processor.process(data_item)
        self.assertTrue(processor.process_called)
        self.assertIsInstance(result, ProcessedData)
        self.assertEqual(result.original_item, data_item)
        self.assertEqual(len(result.processed_content), 1)
        self.assertEqual(result.processed_content[0]["content"], "Processed: Test content")
        self.assertEqual(result.metadata["source"], "test-1")

    def test_process_failure(self):
        """Test process method failure."""
        processor = self.MockProcessor(should_fail=True)
        data_item = DataItem(
            source_id="test-1",
            content="Test content",
            metadata={"key": "value"}
        )
        
        with self.assertRaises(Exception):
            processor.process(data_item)
        self.assertTrue(processor.process_called)

    def test_batch_process(self):
        """Test batch_process method."""
        processor = self.MockProcessor()
        data_items = [
            DataItem(
                source_id="test-1",
                content="Test content 1",
                metadata={"key": "value1"}
            ),
            DataItem(
                source_id="test-2",
                content="Test content 2",
                metadata={"key": "value2"}
            )
        ]
        
        results = processor.batch_process(data_items)
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], ProcessedData)
        self.assertEqual(results[0].original_item, data_items[0])
        self.assertEqual(results[1].original_item, data_items[1])
        self.assertEqual(results[0].processed_content[0]["content"], "Processed: Test content 1")
        self.assertEqual(results[1].processed_content[0]["content"], "Processed: Test content 2")
        self.assertIsNotNone(processor.last_run_time)

    def test_batch_process_with_error(self):
        """Test batch_process method with one item failing."""
        processor = self.MockProcessor()
        
        # Override process method to fail for the second item
        original_process = processor.process
        def mock_process(data_item, params=None):
            if data_item.source_id == "test-2":
                raise Exception("Test error")
            return original_process(data_item, params)
        
        processor.process = mock_process
        
        data_items = [
            DataItem(
                source_id="test-1",
                content="Test content 1",
                metadata={"key": "value1"}
            ),
            DataItem(
                source_id="test-2",
                content="Test content 2",
                metadata={"key": "value2"}
            )
        ]
        
        results = processor.batch_process(data_items)
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], ProcessedData)
        self.assertIsInstance(results[1], ProcessedData)
        
        # First item should be processed normally
        self.assertEqual(results[0].original_item, data_items[0])
        self.assertEqual(results[0].processed_content[0]["content"], "Processed: Test content 1")
        
        # Second item should have error metadata
        self.assertEqual(results[1].original_item, data_items[1])
        self.assertEqual(len(results[1].processed_content), 0)
        self.assertIn("error", results[1].metadata)
        self.assertEqual(results[1].metadata["error_type"], "Exception")
        
        # Error count should be incremented
        self.assertEqual(processor.error_count, 1)

    async def test_async_process(self):
        """Test process_async method."""
        processor = self.MockProcessor()
        data_item = DataItem(
            source_id="test-1",
            content="Test content",
            metadata={"key": "value"}
        )
        
        result = await processor.process_async(data_item)
        self.assertTrue(processor.process_called)
        self.assertIsInstance(result, ProcessedData)
        self.assertEqual(result.original_item, data_item)
        self.assertEqual(result.processed_content[0]["content"], "Processed: Test content")

    async def test_batch_process_async(self):
        """Test batch_process_async method."""
        processor = self.MockProcessor()
        data_items = [
            DataItem(
                source_id="test-1",
                content="Test content 1",
                metadata={"key": "value1"}
            ),
            DataItem(
                source_id="test-2",
                content="Test content 2",
                metadata={"key": "value2"}
            )
        ]
        
        results = await processor.batch_process_async(data_items)
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], ProcessedData)
        self.assertEqual(results[0].original_item, data_items[0])
        self.assertEqual(results[1].original_item, data_items[1])
        self.assertEqual(results[0].processed_content[0]["content"], "Processed: Test content 1")
        self.assertEqual(results[1].processed_content[0]["content"], "Processed: Test content 2")
        self.assertIsNotNone(processor.last_run_time)

    def test_get_status(self):
        """Test get_status method."""
        processor = self.MockProcessor({
            "api_key": "secret_key",
            "model": "test-model"
        })
        processor.error_count = 3
        processor.update_last_run()
        
        status = processor.get_status()
        self.assertEqual(status["name"], "mock_processor")
        self.assertEqual(status["description"], "Mock processor for testing")
        self.assertEqual(status["processor_type"], "mock")
        self.assertEqual(status["error_count"], 3)
        self.assertIsNotNone(status["last_run"])
        
        # Check that sensitive info is not included
        self.assertNotIn("api_key", status["config"])
        self.assertIn("model", status["config"])


class TestTextProcessorFixes(unittest.TestCase):
    """Test cases for the TextProcessor fixes."""

    @patch('core.plugins.processors.text.text_processor.litellm_llm')
    def test_initialization(self, mock_litellm):
        """Test text processor initialization."""
        processor = TextProcessor({
            "model": "gpt-4",
            "max_chunk_size": 5000,
            "max_retries": 2,
            "retry_delay": 1,
            "memory_threshold": 0.8
        })
        
        self.assertEqual(processor.model, "gpt-4")
        self.assertEqual(processor.max_chunk_size, 5000)
        self.assertEqual(processor.max_retries, 2)
        self.assertEqual(processor.retry_delay, 1)
        self.assertEqual(processor.memory_threshold, 0.8)

    @patch('core.plugins.processors.text.text_processor.litellm_llm')
    def test_process(self, mock_litellm):
        """Test process method."""
        # Mock LLM response
        mock_litellm.return_value = json.dumps({
            "content": "Processed content",
            "type": "text"
        })
        
        processor = TextProcessor({"model": "gpt-4"})
        data_item = DataItem(
            source_id="test-1",
            content="Test content",
            metadata={"author": "Test Author", "publish_date": "2023-01-01"}
        )
        
        result = processor.process(
            data_item,
            {
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "prompts": ["System prompt", "User prompt", "gpt-4"]
            }
        )
        
        self.assertIsInstance(result, ProcessedData)
        self.assertEqual(result.original_item, data_item)
        self.assertEqual(len(result.processed_content), 1)
        self.assertEqual(result.processed_content[0]["content"], "Processed content")
        self.assertEqual(result.processed_content[0]["type"], "text")
        self.assertEqual(result.metadata["focus_point"], "Test focus")
        self.assertEqual(result.metadata["explanation"], "Test explanation")
        
        # Check that LLM was called with correct parameters
        mock_litellm.assert_called_once()
        args, kwargs = mock_litellm.call_args
        self.assertEqual(args[0][0]["role"], "system")
        self.assertEqual(args[0][0]["content"], "System prompt")
        self.assertEqual(args[0][1]["role"], "user")
        self.assertIn("Test content", args[0][1]["content"])
        self.assertIn("User prompt", args[0][1]["content"])
        self.assertEqual(kwargs["model"], "gpt-4")

    @patch('core.plugins.processors.text.text_processor.litellm_llm')
    def test_process_with_error(self, mock_litellm):
        """Test process method with error."""
        # Mock LLM error
        mock_litellm.side_effect = Exception("LLM error")
        
        processor = TextProcessor({"model": "gpt-4"})
        data_item = DataItem(
            source_id="test-1",
            content="Test content",
            metadata={"author": "Test Author", "publish_date": "2023-01-01"}
        )
        
        result = processor.process(
            data_item,
            {
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "prompts": ["System prompt", "User prompt", "gpt-4"]
            }
        )
        
        self.assertIsInstance(result, ProcessedData)
        self.assertEqual(result.original_item, data_item)
        self.assertEqual(len(result.processed_content), 0)
        self.assertIn("error", result.metadata)
        self.assertEqual(result.metadata["error_type"], "Exception")
        self.assertEqual(result.metadata["focus_point"], "Test focus")

    @patch('core.plugins.processors.text.text_processor.litellm_llm')
    def test_split_content(self, mock_litellm):
        """Test _split_content method."""
        processor = TextProcessor()
        
        # Test with content smaller than max size
        content = "Small content"
        chunks = processor._split_content(content, 1000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], content)
        
        # Test with content larger than max size
        content = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
        chunks = processor._split_content(content, 15)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], "Paragraph 1.")
        self.assertEqual(chunks[1], "Paragraph 2.")
        self.assertEqual(chunks[2], "Paragraph 3.")
        
        # Test with very large paragraph
        content = "This is a very long paragraph that exceeds the maximum chunk size and needs to be split into multiple chunks."
        chunks = processor._split_content(content, 20)
        self.assertTrue(len(chunks) > 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 20)

    @patch('core.plugins.processors.text.text_processor.litellm_llm')
    def test_parse_llm_response(self, mock_litellm):
        """Test _parse_llm_response method."""
        processor = TextProcessor()
        
        # Test with JSON response
        response = '```json\n{"content": "Extracted content", "type": "text"}\n```'
        result = processor._parse_llm_response(response, "Test Author", "2023-01-01")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["content"], "Extracted content")
        self.assertEqual(result[0]["type"], "text")
        self.assertEqual(result[0]["author"], "Test Author")
        self.assertEqual(result[0]["publish_date"], "2023-01-01")
        
        # Test with non-JSON response
        response = "Plain text response"
        result = processor._parse_llm_response(response, "Test Author", "2023-01-01")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["content"], "Plain text response")
        self.assertEqual(result[0]["type"], "text")
        self.assertEqual(result[0]["author"], "Test Author")
        self.assertEqual(result[0]["publish_date"], "2023-01-01")
        
        # Test with invalid JSON
        response = '```json\n{"content": "Invalid JSON\n```'
        result = processor._parse_llm_response(response, "Test Author", "2023-01-01")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["content"], response)
        self.assertEqual(result[0]["type"], "text")
        self.assertEqual(result[0]["author"], "Test Author")
        self.assertEqual(result[0]["publish_date"], "2023-01-01")

    @patch('core.plugins.processors.text.text_processor.psutil')
    def test_check_memory_usage(self, mock_psutil):
        """Test _check_memory_usage method."""
        processor = TextProcessor({"memory_threshold": 0.8})
        
        # Test with memory usage below threshold
        mock_psutil.virtual_memory.return_value.percent = 70
        result = processor._check_memory_usage()
        self.assertFalse(result)
        
        # Test with memory usage above threshold
        mock_psutil.virtual_memory.return_value.percent = 90
        result = processor._check_memory_usage()
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()

