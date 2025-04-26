"""
Mock OpenAI client for testing.
"""

import sys
import json
from unittest.mock import MagicMock

# Create a mock OpenAI client
mock_openai = MagicMock()

# Mock the OpenAI response for entity extraction
entity_extraction_response = json.dumps([
    {
        "name": "OpenAI GPT-4",
        "type": "ai_model",
        "confidence": 0.95,
        "description": "A large language model developed by OpenAI"
    },
    {
        "name": "Claude 2",
        "type": "ai_model",
        "confidence": 0.92,
        "description": "A large language model developed by Anthropic"
    }
])

# Mock the OpenAI response for relationship extraction
relationship_extraction_response = json.dumps([
    {
        "source": "OpenAI GPT-4",
        "target": "OpenAI",
        "type": "developed_by",
        "confidence": 0.9,
        "description": "GPT-4 was developed by OpenAI"
    },
    {
        "source": "Claude 2",
        "target": "Anthropic",
        "type": "developed_by",
        "confidence": 0.9,
        "description": "Claude 2 was developed by Anthropic"
    }
])

# Mock the OpenAI response for entity linking
entity_linking_response = json.dumps({
    "linked_entities": [
        ["OpenAI GPT-4", "GPT-4 by OpenAI"],
        ["Claude 2"]
    ],
    "confidence": [0.92, 1.0]
})

# Mock the OpenAI response for entity merging
entity_merging_response = json.dumps({
    "merged_entity": {
        "name": "OpenAI GPT-4",
        "type": "ai_model",
        "sources": ["web_source_1", "academic_source_1"],
        "metadata": {
            "developer": "OpenAI",
            "release_date": "2023-03-14",
            "type": "language_model",
            "creator": "OpenAI",
            "published": "March 2023",
            "category": "language_model"
        }
    }
})

# Configure the mock to return appropriate responses
async def mock_agenerate(prompt, **kwargs):
    if "entity extraction" in prompt.lower():
        return entity_extraction_response
    elif "relationship extraction" in prompt.lower():
        return relationship_extraction_response
    elif "entity linking" in prompt.lower():
        return entity_linking_response
    elif "entity merging" in prompt.lower():
        return entity_merging_response
    else:
        return "{}"

# Set up the mock
mock_openai.agenerate = mock_agenerate

# Patch the OpenAI client
sys.modules["core.llms.openai_wrapper"] = MagicMock()
sys.modules["core.llms.openai_wrapper"].openai_llm = mock_openai
