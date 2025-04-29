"""
Trend analyzer plugin for Wiseflow.

This module provides an analyzer for identifying trends in processed data.
"""

import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from core.plugins.analyzers import AnalyzerBase, AnalysisResult
from core.plugins.processors import ProcessedData
from core.llms.openai_wrapper import openai_llm

logger = logging.getLogger(__name__)

class TrendAnalyzer(AnalyzerBase):
    """Analyzer for identifying trends in processed data."""
    
    name: str = "trend_analyzer"
    description: str = "Analyzer for identifying trends in processed data"
    analyzer_type: str = "trend"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the trend analyzer."""
        super().__init__(config)
        self.default_model = self.config.get("default_model", "gpt-3.5-turbo")
        self.default_temperature = self.config.get("default_temperature", 0.3)
        self.default_max_tokens = self.config.get("default_max_tokens", 1500)
        
    def initialize(self) -> bool:
        """Initialize the trend analyzer."""
        try:
            logger.info(f"Initialized trend analyzer with model: {self.default_model}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize trend analyzer: {e}")
            return False
    
    def analyze(self, processed_data: ProcessedData, params: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Analyze processed data to identify trends.
        
        Args:
            processed_data: The processed data to analyze
            params: Optional analysis parameters
                - model: The model to use
                - temperature: The temperature to use
                - max_tokens: The maximum number of tokens to generate
                - focus_areas: List of areas to focus on for trend analysis
                
        Returns:
            AnalysisResult: The analysis result containing identified trends
        """
        params = params or {}
        
        # Get analysis parameters
        model = params.get("model", self.default_model)
        temperature = params.get("temperature", self.default_temperature)
        max_tokens = params.get("max_tokens", self.default_max_tokens)
        focus_areas = params.get("focus_areas", [])
        
        # Get content and metadata
        content = processed_data.processed_content
        metadata = processed_data.metadata.copy()
        focus_point = metadata.get("focus_point", "")
        
        # Create prompts for trend analysis
        focus_areas_str = ", ".join(focus_areas) if focus_areas else "any relevant areas"
        system_prompt = f"""You are an expert in trend analysis and pattern recognition.
Your task is to identify trends, patterns, and insights from the provided text.
Focus on {focus_areas_str} and identify:
1. Key trends and patterns
2. Emerging topics or themes
3. Potential future developments
4. Significant changes or shifts

Format your response as a JSON object with the following structure:
{{
  "trends": [
    {{
      "name": "trend name",
      "description": "detailed description of the trend",
      "evidence": "evidence from the text supporting this trend",
      "confidence": 0.0-1.0,
      "impact": "potential impact of this trend",
      "timeframe": "short-term, medium-term, or long-term"
    }},
    ...
  ],
  "insights": [
    {{
      "description": "key insight",
      "explanation": "detailed explanation of the insight",
      "implications": "potential implications of this insight"
    }},
    ...
  ],
  "summary": "overall summary of the trends and insights"
}}
"""
        user_prompt = f"Analyze the following text for trends and insights{' related to ' + focus_point if focus_point else ''}:\n\n{content}"
        
        # Analyze trends using LLM
        try:
            logger.info(f"Analyzing trends in processed content")
            
            # Call the LLM
            result = openai_llm(
                system_prompt,
                user_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract the analysis content
            analysis_content = result.get("content", "")
            
            # Parse trends from the analysis content
            trends_data = {}
            
            try:
                # Extract JSON from the response
                json_str = analysis_content
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()
                
                # Parse JSON
                trends_data = json.loads(json_str)
            except Exception as e:
                logger.error(f"Error parsing trends from analysis content: {e}")
            
            # Create analysis info
            analysis_info = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                "trend_count": len(trends_data.get("trends", [])),
                "insight_count": len(trends_data.get("insights", []))
            }
            
            # Update metadata
            metadata.update({
                "analyzed_at": datetime.now().isoformat(),
                "analyzer": self.name,
                "focus_areas": focus_areas
            })
            
            # Create analysis result
            analysis_result = AnalysisResult(
                processed_data=processed_data,
                analysis_content=analysis_content,
                metadata=metadata,
                analysis_info=analysis_info
            )
            
            # Add trends data to the analysis result
            analysis_result.metadata["trends_data"] = trends_data
            
            logger.info(f"Successfully identified {analysis_info['trend_count']} trends and {analysis_info['insight_count']} insights")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            
            # Create error analysis result
            analysis_result = AnalysisResult(
                processed_data=processed_data,
                analysis_content=f"Error analyzing content: {str(e)}",
                metadata=metadata,
                analysis_info={
                    "error": str(e)
                }
            )
            
            return analysis_result

