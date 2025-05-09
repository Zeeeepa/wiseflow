"""
Unit tests for the data mining functionality.

This module contains unit tests for the data mining functionality.
"""

import pytest
from unittest.mock import MagicMock, patch

from core.analysis.data_mining import (
    DataMiner, TextAnalyzer, EntityExtractor, PatternRecognizer,
    TrendAnalyzer, DataVisualization
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_text_analyzer():
    """Mock the TextAnalyzer for testing."""
    mock = MagicMock(spec=TextAnalyzer)
    mock.analyze_text.return_value = {
        "sentiment": "positive",
        "keywords": ["test", "data", "mining"],
        "summary": "This is a test summary",
        "language": "en",
        "readability_score": 0.8,
    }
    return mock


@pytest.fixture
def mock_entity_extractor():
    """Mock the EntityExtractor for testing."""
    mock = MagicMock(spec=EntityExtractor)
    mock.extract_entities.return_value = [
        {"type": "PERSON", "text": "John Doe", "start": 0, "end": 8},
        {"type": "ORG", "text": "Acme Corp", "start": 20, "end": 29},
        {"type": "DATE", "text": "2023-01-01", "start": 40, "end": 50},
    ]
    return mock


@pytest.fixture
def mock_pattern_recognizer():
    """Mock the PatternRecognizer for testing."""
    mock = MagicMock(spec=PatternRecognizer)
    mock.find_patterns.return_value = [
        {"pattern": "test pattern 1", "occurrences": 5, "confidence": 0.9},
        {"pattern": "test pattern 2", "occurrences": 3, "confidence": 0.8},
    ]
    return mock


@pytest.fixture
def mock_trend_analyzer():
    """Mock the TrendAnalyzer for testing."""
    mock = MagicMock(spec=TrendAnalyzer)
    mock.analyze_trends.return_value = [
        {"trend": "test trend 1", "strength": 0.9, "direction": "up"},
        {"trend": "test trend 2", "strength": 0.7, "direction": "down"},
    ]
    return mock


@pytest.fixture
def mock_data_visualization():
    """Mock the DataVisualization for testing."""
    mock = MagicMock(spec=DataVisualization)
    mock.create_visualization.return_value = {
        "type": "bar_chart",
        "data": {"labels": ["A", "B", "C"], "values": [1, 2, 3]},
        "title": "Test Visualization",
    }
    return mock


@pytest.fixture
def data_miner(mock_text_analyzer, mock_entity_extractor, mock_pattern_recognizer, mock_trend_analyzer, mock_data_visualization):
    """Create a DataMiner with mock components for testing."""
    return DataMiner(
        text_analyzer=mock_text_analyzer,
        entity_extractor=mock_entity_extractor,
        pattern_recognizer=mock_pattern_recognizer,
        trend_analyzer=mock_trend_analyzer,
        data_visualization=mock_data_visualization,
    )


def test_data_miner_initialization(data_miner, mock_text_analyzer, mock_entity_extractor, mock_pattern_recognizer, mock_trend_analyzer, mock_data_visualization):
    """Test initializing the DataMiner."""
    assert data_miner.text_analyzer == mock_text_analyzer
    assert data_miner.entity_extractor == mock_entity_extractor
    assert data_miner.pattern_recognizer == mock_pattern_recognizer
    assert data_miner.trend_analyzer == mock_trend_analyzer
    assert data_miner.data_visualization == mock_data_visualization


def test_data_miner_analyze_text(data_miner, mock_text_analyzer):
    """Test analyzing text with the DataMiner."""
    text = "This is a test text for data mining analysis."
    result = data_miner.analyze_text(text)
    
    # Check that the text_analyzer.analyze_text method was called with the correct arguments
    mock_text_analyzer.analyze_text.assert_called_once_with(text)
    
    # Check the result
    assert result == mock_text_analyzer.analyze_text.return_value


def test_data_miner_extract_entities(data_miner, mock_entity_extractor):
    """Test extracting entities with the DataMiner."""
    text = "John Doe works at Acme Corp since 2023-01-01."
    result = data_miner.extract_entities(text)
    
    # Check that the entity_extractor.extract_entities method was called with the correct arguments
    mock_entity_extractor.extract_entities.assert_called_once_with(text)
    
    # Check the result
    assert result == mock_entity_extractor.extract_entities.return_value


def test_data_miner_find_patterns(data_miner, mock_pattern_recognizer):
    """Test finding patterns with the DataMiner."""
    data = ["This is test pattern 1", "This is test pattern 2", "This is test pattern 1 again"]
    result = data_miner.find_patterns(data)
    
    # Check that the pattern_recognizer.find_patterns method was called with the correct arguments
    mock_pattern_recognizer.find_patterns.assert_called_once_with(data)
    
    # Check the result
    assert result == mock_pattern_recognizer.find_patterns.return_value


def test_data_miner_analyze_trends(data_miner, mock_trend_analyzer):
    """Test analyzing trends with the DataMiner."""
    data = [
        {"date": "2023-01-01", "value": 1},
        {"date": "2023-01-02", "value": 2},
        {"date": "2023-01-03", "value": 3},
    ]
    result = data_miner.analyze_trends(data)
    
    # Check that the trend_analyzer.analyze_trends method was called with the correct arguments
    mock_trend_analyzer.analyze_trends.assert_called_once_with(data)
    
    # Check the result
    assert result == mock_trend_analyzer.analyze_trends.return_value


def test_data_miner_create_visualization(data_miner, mock_data_visualization):
    """Test creating a visualization with the DataMiner."""
    data = {"labels": ["A", "B", "C"], "values": [1, 2, 3]}
    visualization_type = "bar_chart"
    title = "Test Visualization"
    result = data_miner.create_visualization(data, visualization_type, title)
    
    # Check that the data_visualization.create_visualization method was called with the correct arguments
    mock_data_visualization.create_visualization.assert_called_once_with(data, visualization_type, title)
    
    # Check the result
    assert result == mock_data_visualization.create_visualization.return_value


def test_data_miner_process_data(data_miner, mock_text_analyzer, mock_entity_extractor, mock_pattern_recognizer, mock_trend_analyzer):
    """Test processing data with the DataMiner."""
    data = {
        "text": "John Doe works at Acme Corp since 2023-01-01.",
        "time_series": [
            {"date": "2023-01-01", "value": 1},
            {"date": "2023-01-02", "value": 2},
            {"date": "2023-01-03", "value": 3},
        ],
        "patterns": ["This is test pattern 1", "This is test pattern 2", "This is test pattern 1 again"],
    }
    
    result = data_miner.process_data(data)
    
    # Check that the appropriate methods were called with the correct arguments
    mock_text_analyzer.analyze_text.assert_called_once_with(data["text"])
    mock_entity_extractor.extract_entities.assert_called_once_with(data["text"])
    mock_pattern_recognizer.find_patterns.assert_called_once_with(data["patterns"])
    mock_trend_analyzer.analyze_trends.assert_called_once_with(data["time_series"])
    
    # Check the result structure
    assert "text_analysis" in result
    assert "entities" in result
    assert "patterns" in result
    assert "trends" in result
    
    # Check the result values
    assert result["text_analysis"] == mock_text_analyzer.analyze_text.return_value
    assert result["entities"] == mock_entity_extractor.extract_entities.return_value
    assert result["patterns"] == mock_pattern_recognizer.find_patterns.return_value
    assert result["trends"] == mock_trend_analyzer.analyze_trends.return_value


def test_data_miner_generate_report(data_miner, mock_text_analyzer, mock_entity_extractor, mock_pattern_recognizer, mock_trend_analyzer, mock_data_visualization):
    """Test generating a report with the DataMiner."""
    data = {
        "text": "John Doe works at Acme Corp since 2023-01-01.",
        "time_series": [
            {"date": "2023-01-01", "value": 1},
            {"date": "2023-01-02", "value": 2},
            {"date": "2023-01-03", "value": 3},
        ],
        "patterns": ["This is test pattern 1", "This is test pattern 2", "This is test pattern 1 again"],
    }
    
    result = data_miner.generate_report(data)
    
    # Check that the appropriate methods were called with the correct arguments
    mock_text_analyzer.analyze_text.assert_called_once_with(data["text"])
    mock_entity_extractor.extract_entities.assert_called_once_with(data["text"])
    mock_pattern_recognizer.find_patterns.assert_called_once_with(data["patterns"])
    mock_trend_analyzer.analyze_trends.assert_called_once_with(data["time_series"])
    mock_data_visualization.create_visualization.assert_called()
    
    # Check the result structure
    assert "text_analysis" in result
    assert "entities" in result
    assert "patterns" in result
    assert "trends" in result
    assert "visualizations" in result
    
    # Check the result values
    assert result["text_analysis"] == mock_text_analyzer.analyze_text.return_value
    assert result["entities"] == mock_entity_extractor.extract_entities.return_value
    assert result["patterns"] == mock_pattern_recognizer.find_patterns.return_value
    assert result["trends"] == mock_trend_analyzer.analyze_trends.return_value
    assert isinstance(result["visualizations"], list)
    assert len(result["visualizations"]) > 0

