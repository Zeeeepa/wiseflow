"""
Text processor plugin for processing and normalizing text data.
"""

import re
import html
import unicodedata
from typing import Any, Dict, List, Optional, Union, Tuple
import logging
from bs4 import BeautifulSoup
import langdetect
from langdetect.lang_detect_exception import LangDetectException
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

from core.plugins.base import ProcessorPlugin

logger = logging.getLogger(__name__)

# Download NLTK resources if needed
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)


class TextProcessor(ProcessorPlugin):
    """Processor for text data cleaning, normalization, and analysis."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the text processor.
        
        Args:
            config: Configuration dictionary with the following keys:
                - remove_html: Whether to remove HTML tags (default: True)
                - normalize_whitespace: Whether to normalize whitespace (default: True)
                - remove_urls: Whether to remove URLs (default: True)
                - remove_emails: Whether to remove email addresses (default: True)
                - detect_language: Whether to detect language (default: True)
                - analyze_sentiment: Whether to analyze sentiment (default: True)
                - min_text_length: Minimum text length for language detection (default: 10)
        """
        super().__init__(config)
        self.remove_html = self.config.get('remove_html', True)
        self.normalize_whitespace = self.config.get('normalize_whitespace', True)
        self.remove_urls = self.config.get('remove_urls', True)
        self.remove_emails = self.config.get('remove_emails', True)
        self.detect_language = self.config.get('detect_language', True)
        self.analyze_sentiment = self.config.get('analyze_sentiment', True)
        self.min_text_length = self.config.get('min_text_length', 10)
        
        self.sentiment_analyzer = None
        
    def initialize(self) -> bool:
        """Initialize the text processor.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if self.analyze_sentiment:
            try:
                self.sentiment_analyzer = SentimentIntensityAnalyzer()
            except Exception as e:
                logger.error(f"Failed to initialize sentiment analyzer: {str(e)}")
                self.analyze_sentiment = False
                
        self.initialized = True
        return True
        
    def process(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Process text data.
        
        Args:
            data: Text data to process
            **kwargs: Additional parameters:
                - return_original: Whether to include original text in result (default: False)
                - custom_processors: List of custom processor functions to apply
                
        Returns:
            Dict[str, Any]: Processed text data with metadata
        """
        if not self.initialized:
            self.initialize()
            
        if not isinstance(data, str):
            if hasattr(data, 'text') or hasattr(data, 'content'):
                # Handle requests.Response or similar objects
                text = getattr(data, 'text', None) or getattr(data, 'content', '').decode('utf-8')
            elif isinstance(data, dict) and ('text' in data or 'content' in data):
                # Handle dictionary with text or content key
                text = data.get('text', data.get('content', ''))
            else:
                # Try to convert to string
                try:
                    text = str(data)
                except Exception as e:
                    logger.error(f"Could not convert data to text: {str(e)}")
                    return {'error': 'Invalid input data type', 'processed_text': ''}
        else:
            text = data
            
        original_text = text
        result = {'processed_text': text}
        
        # Apply custom processors first if provided
        custom_processors = kwargs.get('custom_processors', [])
        for processor in custom_processors:
            try:
                text = processor(text)
            except Exception as e:
                logger.error(f"Error in custom processor: {str(e)}")
                
        # Remove HTML tags
        if self.remove_html and text:
            text = self._remove_html_tags(text)
            
        # Normalize whitespace
        if self.normalize_whitespace and text:
            text = self._normalize_whitespace(text)
            
        # Remove URLs
        if self.remove_urls and text:
            text = self._remove_urls(text)
            
        # Remove email addresses
        if self.remove_emails and text:
            text = self._remove_emails(text)
            
        # Detect language
        if self.detect_language and text and len(text) >= self.min_text_length:
            lang = self._detect_language(text)
            if lang:
                result['language'] = lang
                
        # Analyze sentiment
        if self.analyze_sentiment and text and len(text) >= self.min_text_length:
            sentiment = self._analyze_sentiment(text)
            result['sentiment'] = sentiment
            
        result['processed_text'] = text
        
        # Include original text if requested
        if kwargs.get('return_original', False):
            result['original_text'] = original_text
            
        return result
        
    def _remove_html_tags(self, text: str) -> str:
        """Remove HTML tags from text.
        
        Args:
            text: Input text
            
        Returns:
            str: Text with HTML tags removed
        """
        try:
            # Use BeautifulSoup for robust HTML parsing
            soup = BeautifulSoup(text, 'html.parser')
            text = soup.get_text(separator=' ')
            
            # Decode HTML entities
            text = html.unescape(text)
            
            return text
        except Exception as e:
            logger.error(f"Error removing HTML tags: {str(e)}")
            return text
            
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text.
        
        Args:
            text: Input text
            
        Returns:
            str: Text with normalized whitespace
        """
        # Replace multiple whitespace characters with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize Unicode characters
        text = unicodedata.normalize('NFKC', text)
        
        # Strip leading and trailing whitespace
        text = text.strip()
        
        return text
        
    def _remove_urls(self, text: str) -> str:
        """Remove URLs from text.
        
        Args:
            text: Input text
            
        Returns:
            str: Text with URLs removed
        """
        # URL regex pattern
        url_pattern = r'https?://\S+|www\.\S+'
        
        # Replace URLs with empty string
        text = re.sub(url_pattern, '', text)
        
        return text
        
    def _remove_emails(self, text: str) -> str:
        """Remove email addresses from text.
        
        Args:
            text: Input text
            
        Returns:
            str: Text with email addresses removed
        """
        # Email regex pattern
        email_pattern = r'\S+@\S+\.\S+'
        
        # Replace email addresses with empty string
        text = re.sub(email_pattern, '', text)
        
        return text
        
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect the language of text.
        
        Args:
            text: Input text
            
        Returns:
            Optional[str]: Detected language code or None if detection failed
        """
        try:
            return langdetect.detect(text)
        except LangDetectException as e:
            logger.debug(f"Language detection failed: {str(e)}")
            return None
            
    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text.
        
        Args:
            text: Input text
            
        Returns:
            Dict[str, float]: Sentiment scores
        """
        if not self.sentiment_analyzer:
            return {'compound': 0.0, 'positive': 0.0, 'neutral': 0.0, 'negative': 0.0}
            
        try:
            scores = self.sentiment_analyzer.polarity_scores(text)
            return scores
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            return {'compound': 0.0, 'positive': 0.0, 'neutral': 0.0, 'negative': 0.0}

