"""
Unit tests for the entity extraction functionality.

This module contains unit tests for the entity extraction functionality.
"""

import pytest
from unittest.mock import MagicMock, patch

from core.analysis.entity_extraction import EntityExtractor

pytestmark = pytest.mark.unit


@pytest.fixture
def entity_extractor():
    """Create an EntityExtractor for testing."""
    return EntityExtractor()


@patch("core.analysis.entity_extraction.EntityExtractor._extract_entities_with_spacy")
def test_extract_entities_with_spacy(mock_extract_entities_with_spacy, entity_extractor):
    """Test extracting entities with spaCy."""
    # Set up the mock
    mock_extract_entities_with_spacy.return_value = [
        {"type": "PERSON", "text": "John Doe", "start": 0, "end": 8},
        {"type": "ORG", "text": "Acme Corp", "start": 20, "end": 29},
        {"type": "DATE", "text": "2023-01-01", "start": 40, "end": 50},
    ]
    
    # Call the method
    text = "John Doe works at Acme Corp since 2023-01-01."
    result = entity_extractor.extract_entities(text, method="spacy")
    
    # Check that the _extract_entities_with_spacy method was called with the correct arguments
    mock_extract_entities_with_spacy.assert_called_once_with(text)
    
    # Check the result
    assert result == mock_extract_entities_with_spacy.return_value


@patch("core.analysis.entity_extraction.EntityExtractor._extract_entities_with_nltk")
def test_extract_entities_with_nltk(mock_extract_entities_with_nltk, entity_extractor):
    """Test extracting entities with NLTK."""
    # Set up the mock
    mock_extract_entities_with_nltk.return_value = [
        {"type": "PERSON", "text": "John Doe", "start": 0, "end": 8},
        {"type": "ORG", "text": "Acme Corp", "start": 20, "end": 29},
        {"type": "DATE", "text": "2023-01-01", "start": 40, "end": 50},
    ]
    
    # Call the method
    text = "John Doe works at Acme Corp since 2023-01-01."
    result = entity_extractor.extract_entities(text, method="nltk")
    
    # Check that the _extract_entities_with_nltk method was called with the correct arguments
    mock_extract_entities_with_nltk.assert_called_once_with(text)
    
    # Check the result
    assert result == mock_extract_entities_with_nltk.return_value


@patch("core.analysis.entity_extraction.EntityExtractor._extract_entities_with_llm")
def test_extract_entities_with_llm(mock_extract_entities_with_llm, entity_extractor):
    """Test extracting entities with LLM."""
    # Set up the mock
    mock_extract_entities_with_llm.return_value = [
        {"type": "PERSON", "text": "John Doe", "start": 0, "end": 8},
        {"type": "ORG", "text": "Acme Corp", "start": 20, "end": 29},
        {"type": "DATE", "text": "2023-01-01", "start": 40, "end": 50},
    ]
    
    # Call the method
    text = "John Doe works at Acme Corp since 2023-01-01."
    result = entity_extractor.extract_entities(text, method="llm")
    
    # Check that the _extract_entities_with_llm method was called with the correct arguments
    mock_extract_entities_with_llm.assert_called_once_with(text)
    
    # Check the result
    assert result == mock_extract_entities_with_llm.return_value


def test_extract_entities_with_invalid_method(entity_extractor):
    """Test extracting entities with an invalid method."""
    # Call the method with an invalid method
    text = "John Doe works at Acme Corp since 2023-01-01."
    with pytest.raises(ValueError):
        entity_extractor.extract_entities(text, method="invalid_method")


@patch("core.analysis.entity_extraction.spacy.load")
def test_extract_entities_with_spacy_implementation(mock_spacy_load, entity_extractor):
    """Test the implementation of _extract_entities_with_spacy."""
    # Set up the mock
    mock_nlp = MagicMock()
    mock_spacy_load.return_value = mock_nlp
    
    # Set up the mock doc
    mock_doc = MagicMock()
    mock_nlp.return_value = mock_doc
    
    # Set up the mock entities
    mock_entity1 = MagicMock()
    mock_entity1.label_ = "PERSON"
    mock_entity1.text = "John Doe"
    mock_entity1.start_char = 0
    mock_entity1.end_char = 8
    
    mock_entity2 = MagicMock()
    mock_entity2.label_ = "ORG"
    mock_entity2.text = "Acme Corp"
    mock_entity2.start_char = 20
    mock_entity2.end_char = 29
    
    mock_entity3 = MagicMock()
    mock_entity3.label_ = "DATE"
    mock_entity3.text = "2023-01-01"
    mock_entity3.start_char = 40
    mock_entity3.end_char = 50
    
    mock_doc.ents = [mock_entity1, mock_entity2, mock_entity3]
    
    # Call the method
    text = "John Doe works at Acme Corp since 2023-01-01."
    result = entity_extractor._extract_entities_with_spacy(text)
    
    # Check that spacy.load was called with the correct arguments
    mock_spacy_load.assert_called_once_with("en_core_web_sm")
    
    # Check that the nlp model was called with the correct arguments
    mock_nlp.assert_called_once_with(text)
    
    # Check the result
    assert len(result) == 3
    assert result[0]["type"] == "PERSON"
    assert result[0]["text"] == "John Doe"
    assert result[0]["start"] == 0
    assert result[0]["end"] == 8
    assert result[1]["type"] == "ORG"
    assert result[1]["text"] == "Acme Corp"
    assert result[1]["start"] == 20
    assert result[1]["end"] == 29
    assert result[2]["type"] == "DATE"
    assert result[2]["text"] == "2023-01-01"
    assert result[2]["start"] == 40
    assert result[2]["end"] == 50


@patch("core.analysis.entity_extraction.nltk.ne_chunk")
@patch("core.analysis.entity_extraction.nltk.pos_tag")
@patch("core.analysis.entity_extraction.nltk.word_tokenize")
def test_extract_entities_with_nltk_implementation(mock_word_tokenize, mock_pos_tag, mock_ne_chunk, entity_extractor):
    """Test the implementation of _extract_entities_with_nltk."""
    # Set up the mocks
    mock_word_tokenize.return_value = ["John", "Doe", "works", "at", "Acme", "Corp", "since", "2023-01-01", "."]
    mock_pos_tag.return_value = [
        ("John", "NNP"), ("Doe", "NNP"), ("works", "VBZ"), ("at", "IN"),
        ("Acme", "NNP"), ("Corp", "NNP"), ("since", "IN"), ("2023-01-01", "CD"), (".", ".")
    ]
    
    # Set up the mock tree
    mock_tree = MagicMock()
    mock_ne_chunk.return_value = mock_tree
    
    # Set up the mock subtrees
    mock_subtree1 = MagicMock()
    mock_subtree1.label() = "PERSON"
    mock_subtree1.leaves.return_value = [("John", "NNP"), ("Doe", "NNP")]
    
    mock_subtree2 = MagicMock()
    mock_subtree2.label() = "ORGANIZATION"
    mock_subtree2.leaves.return_value = [("Acme", "NNP"), ("Corp", "NNP")]
    
    mock_tree.subtrees.return_value = [mock_subtree1, mock_subtree2]
    
    # Call the method
    text = "John Doe works at Acme Corp since 2023-01-01."
    result = entity_extractor._extract_entities_with_nltk(text)
    
    # Check that the NLTK methods were called with the correct arguments
    mock_word_tokenize.assert_called_once_with(text)
    mock_pos_tag.assert_called_once_with(mock_word_tokenize.return_value)
    mock_ne_chunk.assert_called_once_with(mock_pos_tag.return_value)
    
    # Check the result
    assert len(result) == 2
    assert result[0]["type"] == "PERSON"
    assert result[0]["text"] == "John Doe"
    assert result[1]["type"] == "ORGANIZATION"
    assert result[1]["text"] == "Acme Corp"


@patch("core.analysis.entity_extraction.EntityExtractor._get_llm_client")
def test_extract_entities_with_llm_implementation(mock_get_llm_client, entity_extractor):
    """Test the implementation of _extract_entities_with_llm."""
    # Set up the mock
    mock_llm_client = MagicMock()
    mock_get_llm_client.return_value = mock_llm_client
    
    # Set up the mock response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = """
    [
        {"type": "PERSON", "text": "John Doe", "start": 0, "end": 8},
        {"type": "ORG", "text": "Acme Corp", "start": 20, "end": 29},
        {"type": "DATE", "text": "2023-01-01", "start": 40, "end": 50}
    ]
    """
    mock_llm_client.chat.completions.create.return_value = mock_response
    
    # Call the method
    text = "John Doe works at Acme Corp since 2023-01-01."
    result = entity_extractor._extract_entities_with_llm(text)
    
    # Check that the _get_llm_client method was called
    mock_get_llm_client.assert_called_once()
    
    # Check that the chat.completions.create method was called with the correct arguments
    mock_llm_client.chat.completions.create.assert_called_once()
    args, kwargs = mock_llm_client.chat.completions.create.call_args
    assert kwargs["model"] == "gpt-3.5-turbo"
    assert len(kwargs["messages"]) == 2
    assert kwargs["messages"][0]["role"] == "system"
    assert "entity extraction" in kwargs["messages"][0]["content"].lower()
    assert kwargs["messages"][1]["role"] == "user"
    assert kwargs["messages"][1]["content"] == text
    
    # Check the result
    assert len(result) == 3
    assert result[0]["type"] == "PERSON"
    assert result[0]["text"] == "John Doe"
    assert result[0]["start"] == 0
    assert result[0]["end"] == 8
    assert result[1]["type"] == "ORG"
    assert result[1]["text"] == "Acme Corp"
    assert result[1]["start"] == 20
    assert result[1]["end"] == 29
    assert result[2]["type"] == "DATE"
    assert result[2]["text"] == "2023-01-01"
    assert result[2]["start"] == 40
    assert result[2]["end"] == 50

