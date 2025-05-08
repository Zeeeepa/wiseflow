"""
Tests for the specialized prompting module.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os

from core.llms.advanced.specialized_prompting import (
    SpecializedPromptProcessor,
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_JSON,
    TASK_EXTRACTION,
    TASK_REASONING,
    TASK_SUMMARIZATION
)
from tests.utils import async_test

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    with patch("core.llms.advanced.specialized_prompting.get_llm_client") as mock:
        client = AsyncMock()
        mock.return_value = client
        
        # Mock completion response
        completion_response = {
            "content": json.dumps({
                "result": "Test result",
                "confidence": 0.85,
                "reasoning": "Test reasoning"
            }),
            "model": "gpt-3.5-turbo",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        client.complete.return_value = completion_response
        
        yield client

class TestSpecializedPromptProcessor:
    """Test the SpecializedPromptProcessor class."""
    
    def test_initialization(self):
        """Test initializing the processor."""
        processor = SpecializedPromptProcessor(
            default_model="gpt-3.5-turbo",
            default_temperature=0.7,
            default_max_tokens=1000
        )
        
        assert processor.default_model == "gpt-3.5-turbo"
        assert processor.default_temperature == 0.7
        assert processor.default_max_tokens == 1000
        assert processor.cache is not None
    
    @async_test
    async def test_process_text_extraction(self, mock_llm_client):
        """Test processing text extraction."""
        processor = SpecializedPromptProcessor(
            default_model="gpt-3.5-turbo",
            default_temperature=0.7,
            default_max_tokens=1000
        )
        
        content = """
        Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to intelligence displayed by animals including humans. 
        AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
        """
        
        focus_point = "The definition of artificial intelligence"
        explanation = "Looking for a clear definition of what AI is"
        
        result = await processor.process(
            content=content,
            focus_point=focus_point,
            explanation=explanation,
            content_type=CONTENT_TYPE_TEXT,
            task=TASK_EXTRACTION
        )
        
        assert "result" in result
        assert "confidence" in result
        assert "reasoning" in result
        assert mock_llm_client.complete.call_count == 1
    
    @async_test
    async def test_process_json_reasoning(self, mock_llm_client):
        """Test processing JSON reasoning."""
        processor = SpecializedPromptProcessor(
            default_model="gpt-3.5-turbo",
            default_temperature=0.7,
            default_max_tokens=1000
        )
        
        content = {
            "title": "Artificial Intelligence Overview",
            "sections": [
                {
                    "heading": "Definition",
                    "content": "AI is intelligence demonstrated by machines."
                },
                {
                    "heading": "Applications",
                    "content": "AI applications include web search, recommendation systems, and self-driving cars."
                }
            ]
        }
        
        focus_point = "AI applications"
        explanation = "Looking for information about how AI is applied"
        
        result = await processor.process(
            content=content,
            focus_point=focus_point,
            explanation=explanation,
            content_type=CONTENT_TYPE_JSON,
            task=TASK_REASONING
        )
        
        assert "result" in result
        assert "confidence" in result
        assert "reasoning" in result
        assert mock_llm_client.complete.call_count == 1
    
    @async_test
    async def test_multi_step_reasoning(self, mock_llm_client):
        """Test multi-step reasoning."""
        processor = SpecializedPromptProcessor(
            default_model="gpt-3.5-turbo",
            default_temperature=0.7,
            default_max_tokens=1000
        )
        
        content = """
        Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to intelligence displayed by animals including humans. 
        AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
        """
        
        focus_point = "The evolution of AI research"
        explanation = "Looking for information about how AI research has evolved"
        
        # Mock multiple responses for the steps
        mock_llm_client.complete.side_effect = [
            # Step 1: Initial analysis
            {
                "content": json.dumps({
                    "result": "Initial analysis of AI research evolution",
                    "confidence": 0.8,
                    "reasoning": "Based on the content, AI research is defined as the study of intelligent agents."
                }),
                "model": "gpt-3.5-turbo"
            },
            # Step 2: Detailed reasoning
            {
                "content": json.dumps({
                    "result": "Detailed reasoning about AI research evolution",
                    "confidence": 0.85,
                    "reasoning": "The definition has evolved from mimicking human cognition to rational action."
                }),
                "model": "gpt-3.5-turbo"
            },
            # Step 3: Final synthesis
            {
                "content": json.dumps({
                    "result": "Final synthesis of AI research evolution",
                    "confidence": 0.9,
                    "reasoning": "AI research has shifted from human-like intelligence to goal-oriented systems."
                }),
                "model": "gpt-3.5-turbo"
            }
        ]
        
        result = await processor.multi_step_reasoning(
            content=content,
            focus_point=focus_point,
            explanation=explanation
        )
        
        assert "result" in result
        assert "confidence" in result
        assert "reasoning" in result
        assert "steps" in result
        assert len(result["steps"]) == 3
        assert mock_llm_client.complete.call_count == 3
    
    @async_test
    async def test_chain_of_thought(self, mock_llm_client):
        """Test chain of thought reasoning."""
        processor = SpecializedPromptProcessor(
            default_model="gpt-3.5-turbo",
            default_temperature=0.7,
            default_max_tokens=1000
        )
        
        content = """
        Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to intelligence displayed by animals including humans. 
        AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
        """
        
        focus_point = "The definition of artificial intelligence"
        explanation = "Looking for a clear definition of what AI is"
        
        mock_llm_client.complete.return_value = {
            "content": json.dumps({
                "thoughts": [
                    "The text provides a definition of AI as intelligence demonstrated by machines.",
                    "It contrasts AI with intelligence displayed by animals and humans.",
                    "It also defines AI research as the study of intelligent agents."
                ],
                "result": "AI is defined as intelligence demonstrated by machines, in contrast to natural intelligence in animals and humans.",
                "confidence": 0.9
            }),
            "model": "gpt-3.5-turbo"
        }
        
        result = await processor.chain_of_thought(
            content=content,
            focus_point=focus_point,
            explanation=explanation
        )
        
        assert "result" in result
        assert "confidence" in result
        assert "thoughts" in result
        assert len(result["thoughts"]) == 3
        assert mock_llm_client.complete.call_count == 1
    
    @async_test
    async def test_contextual_understanding(self, mock_llm_client):
        """Test contextual understanding."""
        processor = SpecializedPromptProcessor(
            default_model="gpt-3.5-turbo",
            default_temperature=0.7,
            default_max_tokens=1000
        )
        
        content = """
        Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to intelligence displayed by animals including humans. 
        AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
        """
        
        focus_point = "The definition of artificial intelligence"
        explanation = "Looking for a clear definition of what AI is"
        
        references = """
        Recent advancements in AI:
        1. Large language models like GPT-4 have demonstrated remarkable capabilities in natural language understanding and generation.
        2. Multimodal models can now process and generate content across text, images, and audio.
        3. AI systems are increasingly being deployed in critical domains like healthcare, finance, and autonomous vehicles.
        4. Concerns about AI safety, ethics, and regulation have become more prominent.
        """
        
        mock_llm_client.complete.return_value = {
            "content": json.dumps({
                "result": "AI is defined as machine intelligence, distinct from human intelligence, with recent advancements in language models and multimodal capabilities.",
                "confidence": 0.9,
                "context_integration": "The definition is enhanced by understanding recent developments in large language models and multimodal systems."
            }),
            "model": "gpt-3.5-turbo"
        }
        
        result = await processor.contextual_understanding(
            content=content,
            focus_point=focus_point,
            explanation=explanation,
            references=references
        )
        
        assert "result" in result
        assert "confidence" in result
        assert "context_integration" in result
        assert mock_llm_client.complete.call_count == 1
    
    @async_test
    async def test_caching(self, mock_llm_client):
        """Test result caching."""
        processor = SpecializedPromptProcessor(
            default_model="gpt-3.5-turbo",
            default_temperature=0.7,
            default_max_tokens=1000
        )
        
        content = "Test content for caching"
        focus_point = "Test focus"
        explanation = "Test explanation"
        
        # First call should use the LLM
        await processor.process(
            content=content,
            focus_point=focus_point,
            explanation=explanation,
            content_type=CONTENT_TYPE_TEXT,
            task=TASK_EXTRACTION
        )
        
        assert mock_llm_client.complete.call_count == 1
        
        # Second call with same parameters should use cache
        await processor.process(
            content=content,
            focus_point=focus_point,
            explanation=explanation,
            content_type=CONTENT_TYPE_TEXT,
            task=TASK_EXTRACTION
        )
        
        # Call count should still be 1 if cache was used
        assert mock_llm_client.complete.call_count == 1
        
        # Call with different parameters should use LLM again
        await processor.process(
            content=content,
            focus_point="Different focus",
            explanation=explanation,
            content_type=CONTENT_TYPE_TEXT,
            task=TASK_EXTRACTION
        )
        
        assert mock_llm_client.complete.call_count == 2


@pytest.mark.integration
class TestSpecializedPromptingIntegration:
    """Integration tests for specialized prompting."""
    
    @pytest.mark.skipif(not os.environ.get("RUN_LLM_TESTS"), reason="Skipping LLM tests")
    @async_test
    async def test_real_llm_extraction(self):
        """Test extraction with a real LLM."""
        processor = SpecializedPromptProcessor(
            default_model=os.environ.get("TEST_LLM_MODEL", "gpt-3.5-turbo"),
            default_temperature=0.7,
            default_max_tokens=1000
        )
        
        content = """
        Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to intelligence displayed by animals including humans. 
        AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
        
        The term "artificial intelligence" had previously been used to describe machines that mimic and display "human" cognitive skills that are associated with the human mind, such as "learning" and "problem-solving". This definition has since been rejected by major AI researchers who now describe AI in terms of rationality and acting rationally, which does not limit how intelligence can be articulated.
        
        AI applications include advanced web search engines (e.g., Google), recommendation systems (used by YouTube, Amazon, and Netflix), understanding human speech (such as Siri and Alexa), self-driving cars (e.g., Waymo), generative or creative tools (ChatGPT and AI art), automated decision-making, and competing at the highest level in strategic game systems (such as chess and Go).
        """
        
        focus_point = "Applications of artificial intelligence"
        explanation = "Looking for examples of how AI is applied in real-world systems"
        
        result = await processor.process(
            content=content,
            focus_point=focus_point,
            explanation=explanation,
            content_type=CONTENT_TYPE_TEXT,
            task=TASK_EXTRACTION
        )
        
        assert "result" in result
        assert "confidence" in result
        assert result["confidence"] > 0.5
        
        # Check that the result contains information about AI applications
        assert any(app in result["result"].lower() for app in ["search", "recommendation", "speech", "self-driving", "generative"])
    
    @pytest.mark.skipif(not os.environ.get("RUN_LLM_TESTS"), reason="Skipping LLM tests")
    @async_test
    async def test_real_llm_multi_step_reasoning(self):
        """Test multi-step reasoning with a real LLM."""
        processor = SpecializedPromptProcessor(
            default_model=os.environ.get("TEST_LLM_MODEL", "gpt-3.5-turbo"),
            default_temperature=0.7,
            default_max_tokens=1000
        )
        
        content = """
        Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to intelligence displayed by animals including humans. 
        AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.
        
        The term "artificial intelligence" had previously been used to describe machines that mimic and display "human" cognitive skills that are associated with the human mind, such as "learning" and "problem-solving". This definition has since been rejected by major AI researchers who now describe AI in terms of rationality and acting rationally, which does not limit how intelligence can be articulated.
        """
        
        focus_point = "Evolution of AI definition"
        explanation = "How has the definition of AI changed over time?"
        
        result = await processor.multi_step_reasoning(
            content=content,
            focus_point=focus_point,
            explanation=explanation
        )
        
        assert "result" in result
        assert "confidence" in result
        assert "steps" in result
        assert len(result["steps"]) >= 2
        
        # Check that the result discusses the evolution of AI definition
        assert any(term in result["result"].lower() for term in ["evolution", "change", "shift", "human", "rational"])

