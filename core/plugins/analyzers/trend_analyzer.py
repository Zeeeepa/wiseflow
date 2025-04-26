"""
Trend Analyzer Plugin for Wiseflow.

This plugin analyzes processed data to identify trends and patterns over time.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import re
from collections import Counter

from core.plugins.analyzers import AnalyzerBase, AnalysisResult
from core.plugins.processors import ProcessedData
from core.llms.litellm_wrapper import litellm_llm

logger = logging.getLogger(__name__)

class TrendAnalyzer(AnalyzerBase):
    """Analyzer for identifying trends in processed data."""
    
    name: str = "trend_analyzer"
    description: str = "Identifies trends and patterns in processed data over time"
    analyzer_type: str = "trend"
    
    # Default prompt for trend analysis
    DEFAULT_TREND_PROMPT = """
    You are an expert in trend analysis. Identify key trends, patterns, and insights from the following text.
    Focus on:
    1. Emerging topics or themes
    2. Changes in sentiment or opinion
    3. Evolving narratives or discussions
    4. Recurring patterns or cycles
    5. Notable shifts or turning points
    
    For each trend you identify, provide:
    1. A concise title for the trend
    2. A description of the trend
    3. Supporting evidence from the text
    4. The significance or implications of the trend
    
    Format your response as a JSON array of objects with the following structure:
    [
      {
        "title": "trend title",
        "description": "description of the trend",
        "evidence": "supporting evidence from the text",
        "significance": "significance or implications"
      }
    ]
    
    Text to analyze:
    {text}
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the trend analyzer."""
        super().__init__(config)
        self.trend_prompt = self.config.get("trend_prompt", self.DEFAULT_TREND_PROMPT)
        self.model = self.config.get("model", "gpt-3.5-turbo")
        self.min_word_length = self.config.get("min_word_length", 4)
        self.max_keywords = self.config.get("max_keywords", 20)
        self.stopwords = self.config.get("stopwords", [
            "the", "and", "a", "to", "of", "in", "is", "that", "it", "with", "for", "as", "on", "was", "be", "this", "by"
        ])
        
    def analyze(self, processed_data: ProcessedData, params: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """Analyze processed data to identify trends."""
        params = params or {}
        
        if not processed_data or not processed_data.processed_content:
            logger.warning("No processed content to analyze")
            return AnalysisResult(
                processed_data=processed_data,
                analysis_content={"trends": [], "keywords": []},
                metadata={"error": "No processed content to analyze"}
            )
        
        try:
            # Extract text from processed content
            text = self._extract_text(processed_data.processed_content)
            
            if not text:
                logger.warning("No text content found in processed data")
                return AnalysisResult(
                    processed_data=processed_data,
                    analysis_content={"trends": [], "keywords": []},
                    metadata={"error": "No text content found in processed data"}
                )
            
            # Extract keywords
            keywords = self._extract_keywords(text)
            
            # Identify trends
            trends = self._identify_trends(text)
            
            # Create analysis result
            analysis_content = {
                "trends": trends,
                "keywords": keywords
            }
            
            metadata = {
                "trend_count": len(trends),
                "keyword_count": len(keywords),
                "source_type": processed_data.metadata.get("source_type", "unknown"),
                "analysis_time": datetime.now().isoformat()
            }
            
            return AnalysisResult(
                processed_data=processed_data,
                analysis_content=analysis_content,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error analyzing data: {e}")
            return AnalysisResult(
                processed_data=processed_data,
                analysis_content={"trends": [], "keywords": []},
                metadata={"error": str(e)}
            )
    
    def _extract_text(self, processed_content: Any) -> str:
        """Extract text from processed content."""
        if isinstance(processed_content, str):
            return processed_content
        
        if isinstance(processed_content, list):
            # Try to extract text from a list of items
            text_parts = []
            for item in processed_content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict) and "content" in item:
                    text_parts.append(item["content"])
            
            return "\n\n".join(text_parts)
        
        if isinstance(processed_content, dict):
            # Try to extract text from a dictionary
            if "content" in processed_content:
                return processed_content["content"]
            
            # Try to find any text fields
            text_parts = []
            for key, value in processed_content.items():
                if isinstance(value, str) and len(value) > 50:  # Assume longer strings are content
                    text_parts.append(value)
            
            return "\n\n".join(text_parts)
        
        return str(processed_content)
    
    def _extract_keywords(self, text: str) -> List[Dict[str, Any]]:
        """Extract keywords from text."""
        # Clean the text
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
        text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
        
        # Tokenize
        words = text.split()
        
        # Filter words
        filtered_words = [
            word for word in words 
            if len(word) >= self.min_word_length and word not in self.stopwords
        ]
        
        # Count word frequencies
        word_counts = Counter(filtered_words)
        
        # Get the most common words
        top_keywords = word_counts.most_common(self.max_keywords)
        
        # Format the results
        keywords = [
            {
                "keyword": keyword,
                "count": count,
                "frequency": count / len(filtered_words) if filtered_words else 0
            }
            for keyword, count in top_keywords
        ]
        
        return keywords
    
    def _identify_trends(self, text: str) -> List[Dict[str, Any]]:
        """Identify trends in text using LLM."""
        try:
            # Prepare the prompt
            prompt = self.trend_prompt.format(text=text)
            
            # Call the LLM
            messages = [
                {"role": "system", "content": "You are an expert in trend analysis."},
                {"role": "user", "content": prompt}
            ]
            
            response = litellm_llm(messages, self.model)
            
            # Parse the response
            return self._parse_json_response(response)
            
        except Exception as e:
            logger.error(f"Error identifying trends: {e}")
            return []
    
    def _parse_json_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse JSON from LLM response."""
        try:
            # Try to parse the entire response as JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            json_pattern = r'\[\s*\{.*\}\s*\]'
            matches = re.search(json_pattern, response, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches.group(0))
                except json.JSONDecodeError:
                    pass
            
            # Try to extract JSON with triple backticks
            json_pattern = r'```(?:json)?\s*([\s\S]*?)```'
            matches = re.search(json_pattern, response, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches.group(1))
                except json.JSONDecodeError:
                    pass
            
            logger.error(f"Failed to parse JSON from response: {response}")
            return []
