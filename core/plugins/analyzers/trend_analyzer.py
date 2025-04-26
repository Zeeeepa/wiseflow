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
from tenacity import retry, stop_after_attempt, wait_exponential

from core.plugins.analyzers import AnalyzerBase, AnalysisResult
from core.plugins.processors import ProcessedData
from core.plugins.utils import TextExtractor
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
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_min_wait = self.config.get("retry_min_wait", 4)
        self.retry_max_wait = self.config.get("retry_max_wait", 10)
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
            text = TextExtractor.extract_text(processed_data.processed_content)
            
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
    
    def _extract_keywords(self, text: str) -> List[Dict[str, Any]]:
        """Extract keywords from text."""
        try:
            # Tokenize the text
            words = re.findall(r'\b\w+\b', text.lower())
            
            # Filter out stopwords and short words
            filtered_words = [word for word in words if word not in self.stopwords and len(word) >= self.min_word_length]
            
            # Count word frequencies
            word_counts = Counter(filtered_words)
            
            # Get the most common words
            top_keywords = word_counts.most_common(self.max_keywords)
            
            # Format the keywords
            keywords = [{"keyword": keyword, "count": count} for keyword, count in top_keywords]
            
            return keywords
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _identify_trends(self, text: str) -> List[Dict[str, Any]]:
        """Identify trends in text using LLM with retry logic."""
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
            raise  # Let retry handle the error
    
    def _parse_json_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse JSON response from LLM."""
        try:
            # Extract JSON from the response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            # If no JSON array found, try to parse the entire response
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.debug(f"Response: {response}")
            return []
