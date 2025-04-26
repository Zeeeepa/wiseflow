"""
Trend Analyzer Plugin for Wiseflow.

This plugin analyzes processed data to identify trends and patterns.
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from core.plugins.analyzers import AnalyzerBase, AnalysisResult
from core.plugins.processors import ProcessedData
from core.plugins.utils import TextExtractor
from core.llms.litellm_wrapper import litellm_llm

logger = logging.getLogger(__name__)

class TrendAnalyzer(AnalyzerBase):
    """Analyzer for identifying trends and patterns in processed data."""
    
    name: str = "trend_analyzer"
    description: str = "Identifies trends and patterns in processed data"
    analyzer_type: str = "trend"
    
    # Default prompt for trend analysis
    DEFAULT_TREND_PROMPT = """
    You are an expert in trend analysis. Identify key trends, patterns, and insights from the following text.
    For each trend or pattern, provide:
    1. A title or name for the trend
    2. A category (e.g., "technology", "business", "social", "economic", etc.)
    3. A detailed description of the trend
    4. Supporting evidence from the text
    5. Potential implications or future developments
    
    Format your response as a JSON array of objects with the following structure:
    [
      {
        "title": "trend title",
        "category": "trend category",
        "description": "detailed description",
        "evidence": "supporting evidence from the text",
        "implications": "potential implications or future developments"
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
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_min_wait = self.config.get("retry_min_wait", 4)
        self.retry_max_wait = self.config.get("retry_max_wait", 10)
        
    def analyze(self, processed_data: ProcessedData, params: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """Analyze processed data to identify trends and patterns."""
        params = params or {}
        
        if not processed_data or not processed_data.processed_content:
            logger.warning("No processed content to analyze")
            return AnalysisResult(
                processed_data=processed_data,
                analysis_content={"trends": []},
                metadata={"error": "No processed content to analyze"}
            )
        
        try:
            # Extract text from processed content
            text = TextExtractor.extract_text(processed_data.processed_content)
            
            if not text:
                logger.warning("No text content found in processed data")
                return AnalysisResult(
                    processed_data=processed_data,
                    analysis_content={"trends": []},
                    metadata={"error": "No text content found in processed data"}
                )
            
            # Extract trends
            trends = self._extract_trends(text)
            
            # Create analysis result
            analysis_content = {
                "trends": trends
            }
            
            metadata = {
                "trend_count": len(trends),
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
                analysis_content={"trends": []},
                metadata={"error": str(e)}
            )
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _extract_trends(self, text: str) -> List[Dict[str, Any]]:
        """Extract trends from text using LLM with retry logic."""
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
            logger.error(f"Error extracting trends: {e}")
            raise  # Let retry handle the error
    
    def _parse_json_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse JSON response from LLM."""
        try:
            # Extract JSON from the response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            # If no JSON array found, try parsing the entire response
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.debug(f"Raw response: {response}")
            return []
