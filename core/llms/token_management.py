"""
Token management utilities for LLM interactions.

This module provides utilities for counting, tracking, and optimizing token usage
in LLM interactions to improve efficiency and reduce costs.
"""

import json
import logging
import re
import os
import time
import sqlite3
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime, timedelta
import threading

from .config import llm_config

# Try to import tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

# Try to import transformers for alternative token counting
try:
    from transformers import AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class TokenCounter:
    """
    Utility class for counting tokens in text and messages.
    
    This class provides methods for counting tokens in text and messages,
    using tiktoken if available or falling back to alternative methods.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the token counter.
        
        Args:
            logger: Optional logger for logging token counts
        """
        self.logger = logger
        self.encoders = {}
        self.transformers_tokenizers = {}
        
        # Load model-specific token counting rules
        self.model_token_rules = {
            # OpenAI models
            "gpt-3.5-turbo": {"tokens_per_message": 4, "tokens_per_name": 1},
            "gpt-4": {"tokens_per_message": 4, "tokens_per_name": 1},
            "gpt-4-32k": {"tokens_per_message": 4, "tokens_per_name": 1},
            "gpt-4-1106-preview": {"tokens_per_message": 4, "tokens_per_name": 1},
            "gpt-4-vision-preview": {"tokens_per_message": 4, "tokens_per_name": 1},
            
            # Anthropic models
            "claude-2": {"tokens_per_message": 3, "tokens_per_name": 1},
            "claude-instant-1": {"tokens_per_message": 3, "tokens_per_name": 1},
        }
    
    def _get_encoder(self, model: str):
        """
        Get the appropriate encoder for a model.
        
        Args:
            model: Model name
            
        Returns:
            Tiktoken encoder for the model
        """
        if not TIKTOKEN_AVAILABLE:
            return None
        
        if model not in self.encoders:
            try:
                self.encoders[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fall back to cl100k_base for unknown models (used by GPT-4, text-embedding-ada-002)
                try:
                    self.encoders[model] = tiktoken.get_encoding("cl100k_base")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error getting tiktoken encoding for model {model}: {e}")
                    return None
        
        return self.encoders[model]
    
    def _get_transformers_tokenizer(self, model: str):
        """
        Get a transformers tokenizer for a model.
        
        Args:
            model: Model name
            
        Returns:
            Transformers tokenizer for the model
        """
        if not TRANSFORMERS_AVAILABLE:
            return None
        
        if model not in self.transformers_tokenizers:
            try:
                # Map model names to HuggingFace model names
                hf_model_map = {
                    "gpt-3.5-turbo": "gpt2",
                    "gpt-4": "gpt2",
                    "gpt-4-32k": "gpt2",
                    "gpt-4-1106-preview": "gpt2",
                    "gpt-4-vision-preview": "gpt2",
                    "claude-2": "facebook/bart-large",
                    "claude-instant-1": "facebook/bart-large",
                }
                
                hf_model = hf_model_map.get(model, "gpt2")
                self.transformers_tokenizers[model] = AutoTokenizer.from_pretrained(hf_model)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Error getting transformers tokenizer for model {model}: {e}")
                return None
        
        return self.transformers_tokenizers[model]
    
    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Count the number of tokens in a text string.
        
        Args:
            text: Text to count tokens in
            model: Model name to use for token counting
            
        Returns:
            Number of tokens in the text
        """
        if not text:
            return 0
            
        # Try tiktoken first (most accurate)
        if TIKTOKEN_AVAILABLE:
            encoder = self._get_encoder(model)
            if encoder:
                try:
                    return len(encoder.encode(text))
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error counting tokens with tiktoken: {e}")
        
        # Try transformers as a second option
        if TRANSFORMERS_AVAILABLE:
            tokenizer = self._get_transformers_tokenizer(model)
            if tokenizer:
                try:
                    return len(tokenizer.encode(text))
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error counting tokens with transformers: {e}")
        
        # Fall back to approximate counting
        return self._approximate_token_count(text)
    
    def _approximate_token_count(self, text: str) -> int:
        """
        Approximate the number of tokens in a text string.
        
        This is a fallback method when tiktoken and transformers are not available.
        It's less accurate but provides a reasonable approximation.
        
        Args:
            text: Text to count tokens in
            
        Returns:
            Approximate number of tokens in the text
        """
        if not text:
            return 0
            
        # Split by whitespace for word count
        words = text.split()
        
        # Count punctuation and special characters
        punctuation = sum(1 for c in text if c in '.,;:!?()[]{}"\'`~@#$%^&*-+=|\\<>/') 
        
        # Count numbers (roughly 1 token per 2-3 digits)
        numbers = len(re.findall(r'\d+', text))
        digits = sum(len(match) for match in re.findall(r'\d+', text))
        number_tokens = max(1, int(digits / 2.5))
        
        # Estimate: each word is ~1.3 tokens, punctuation is ~0.5 tokens, numbers vary
        return int(len(words) * 1.3 + punctuation * 0.5 + number_tokens)
    
    def count_message_tokens(self, messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> int:
        """
        Count the number of tokens in a list of messages.
        
        Args:
            messages: List of message dictionaries
            model: Model name to use for token counting
            
        Returns:
            Number of tokens in the messages
        """
        if not messages:
            return 0
            
        # Get model-specific token counting rules
        model_rules = self.model_token_rules.get(
            model, 
            {"tokens_per_message": 4, "tokens_per_name": 1}  # Default to GPT-3.5/4 rules
        )
        
        if TIKTOKEN_AVAILABLE:
            encoder = self._get_encoder(model)
            if encoder:
                try:
                    # Format: every message follows <|start|>{role/name}\n{content}<|end|>
                    # If there's a name, the role is omitted
                    num_tokens = 0
                    for message in messages:
                        num_tokens += model_rules["tokens_per_message"]  # Message overhead
                        for key, value in message.items():
                            if not value:
                                continue
                            num_tokens += len(encoder.encode(value))
                            if key == "name":  # If there's a name, the role is omitted
                                num_tokens -= model_rules["tokens_per_name"]
                    
                    # Add trailing message overhead (for completion)
                    num_tokens += 3  # Every reply is primed with <|start|>assistant<|message|>
                    
                    return num_tokens
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error counting message tokens with tiktoken: {e}")
        
        # Fall back to approximate counting
        total_tokens = 0
        for message in messages:
            # Count tokens in message content
            content = message.get("content", "")
            if content:
                total_tokens += self.count_tokens(content, model)
            
            # Add overhead for message format
            total_tokens += model_rules["tokens_per_message"]
            
            # Add tokens for function calls if present
            if "function_call" in message:
                function_call = message["function_call"]
                if isinstance(function_call, dict):
                    function_call_str = json.dumps(function_call)
                    total_tokens += self.count_tokens(function_call_str, model)
        
        # Add trailing message overhead
        total_tokens += 3
        
        return total_tokens
    
    def estimate_completion_tokens(self, prompt_tokens: int, model: str = "gpt-3.5-turbo") -> int:
        """
        Estimate the number of completion tokens based on prompt tokens.
        
        This is a rough estimate based on typical response patterns.
        
        Args:
            prompt_tokens: Number of tokens in the prompt
            model: Model name
            
        Returns:
            Estimated number of completion tokens
        """
        # Different models have different response patterns
        if "gpt-3.5" in model:
            # GPT-3.5 typically generates responses ~1.5x the prompt length
            return int(prompt_tokens * 1.5)
        elif "gpt-4" in model:
            # GPT-4 typically generates more detailed responses
            return int(prompt_tokens * 2.0)
        elif "claude" in model:
            # Claude models typically generate responses similar to GPT-4
            return int(prompt_tokens * 2.0)
        else:
            # Default estimate
            return prompt_tokens
    
    def get_max_tokens(self, model: str) -> int:
        """
        Get the maximum number of tokens supported by a model.
        
        Args:
            model: Model name
            
        Returns:
            Maximum number of tokens
        """
        # Model context lengths
        context_lengths = {
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-1106-preview": 128000,
            "gpt-4-vision-preview": 128000,
            "claude-2": 100000,
            "claude-instant-1": 100000,
        }
        
        return context_lengths.get(model, 4096)  # Default to 4096 if model not found

class TokenOptimizer:
    """
    Utility class for optimizing token usage in prompts and messages.
    
    This class provides methods for optimizing prompts and messages to reduce token usage
    while preserving the essential information.
    """
    
    def __init__(self, token_counter: TokenCounter, logger: Optional[logging.Logger] = None):
        """
        Initialize the token optimizer.
        
        Args:
            token_counter: TokenCounter instance for counting tokens
            logger: Optional logger for logging optimizations
        """
        self.token_counter = token_counter
        self.logger = logger
    
    def optimize_prompt(self, prompt: str, max_tokens: int, model: str = "gpt-3.5-turbo") -> str:
        """
        Optimize a prompt to fit within a token limit.
        
        Args:
            prompt: Prompt to optimize
            max_tokens: Maximum number of tokens
            model: Model name
            
        Returns:
            Optimized prompt
        """
        current_tokens = self.token_counter.count_tokens(prompt, model)
        
        if current_tokens <= max_tokens:
            return prompt
        
        # Calculate the reduction ratio needed
        reduction_ratio = max_tokens / current_tokens
        
        # If we need a small reduction, try simple truncation
        if reduction_ratio > 0.8:
            return self._truncate_prompt(prompt, max_tokens, model)
        
        # For more significant reductions, use more aggressive optimization
        return self._optimize_prompt_content(prompt, max_tokens, model)
    
    def _truncate_prompt(self, prompt: str, max_tokens: int, model: str) -> str:
        """
        Truncate a prompt to fit within a token limit.
        
        Args:
            prompt: Prompt to truncate
            max_tokens: Maximum number of tokens
            model: Model name
            
        Returns:
            Truncated prompt
        """
        # Split the prompt into paragraphs
        paragraphs = prompt.split("\n\n")
        
        # If we have multiple paragraphs, keep the first and last paragraphs
        # (usually instructions and examples) and truncate the middle
        if len(paragraphs) > 2:
            first_paragraph = paragraphs[0]
            last_paragraph = paragraphs[-1]
            
            # Calculate tokens for first and last paragraphs
            first_tokens = self.token_counter.count_tokens(first_paragraph, model)
            last_tokens = self.token_counter.count_tokens(last_paragraph, model)
            
            # Calculate how many tokens we have left for the middle
            middle_tokens = max_tokens - first_tokens - last_tokens - 2  # 2 tokens for newlines
            
            if middle_tokens > 0:
                # Join the middle paragraphs
                middle_paragraphs = "\n\n".join(paragraphs[1:-1])
                
                # Truncate the middle
                if self.token_counter.count_tokens(middle_paragraphs, model) > middle_tokens:
                    middle_paragraphs = self._truncate_text(middle_paragraphs, middle_tokens, model)
                
                return f"{first_paragraph}\n\n{middle_paragraphs}\n\n{last_paragraph}"
        
        # If we don't have multiple paragraphs or the above approach doesn't work,
        # simply truncate the prompt
        return self._truncate_text(prompt, max_tokens, model)
    
    def _truncate_text(self, text: str, max_tokens: int, model: str) -> str:
        """
        Truncate text to fit within a token limit.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens
            model: Model name
            
        Returns:
            Truncated text
        """
        if self.token_counter.count_tokens(text, model) <= max_tokens:
            return text
        
        # If tiktoken is available, use it for precise truncation
        if TIKTOKEN_AVAILABLE:
            encoder = self.token_counter._get_encoder(model)
            if encoder:
                try:
                    tokens = encoder.encode(text)
                    truncated = encoder.decode(tokens[:max_tokens])
                    
                    # Add ellipsis to indicate truncation
                    if len(truncated) < len(text):
                        truncated += "..."
                    
                    return truncated
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error truncating text with tiktoken: {e}")
        
        # Otherwise, use a simple approach based on character count
        # Estimate: 1 token ~= 4 characters
        char_limit = max_tokens * 4
        if len(text) > char_limit:
            return text[:char_limit] + "..."
        
        return text
    
    def _optimize_prompt_content(self, prompt: str, max_tokens: int, model: str) -> str:
        """
        Optimize prompt content to fit within a token limit.
        
        This method uses more aggressive optimization techniques for larger reductions.
        
        Args:
            prompt: Prompt to optimize
            max_tokens: Maximum number of tokens
            model: Model name
            
        Returns:
            Optimized prompt
        """
        # Split the prompt into sections
        sections = self._split_into_sections(prompt)
        
        # Calculate current tokens
        current_tokens = self.token_counter.count_tokens(prompt, model)
        
        # Calculate the reduction factor needed
        reduction_factor = max_tokens / current_tokens
        
        # Prioritize sections (instructions and examples are more important)
        prioritized_sections = self._prioritize_sections(sections)
        
        # Allocate tokens to sections based on priority
        optimized_sections = []
        remaining_tokens = max_tokens
        
        for section, priority in prioritized_sections:
            # Calculate tokens for this section
            section_tokens = self.token_counter.count_tokens(section, model)
            
            # Allocate tokens based on priority and remaining tokens
            allocated_tokens = min(
                section_tokens,  # Don't allocate more than needed
                int(section_tokens * reduction_factor * priority),  # Scale by priority
                remaining_tokens  # Don't exceed remaining tokens
            )
            
            # Optimize the section to fit within allocated tokens
            if allocated_tokens < section_tokens:
                optimized_section = self._truncate_text(section, allocated_tokens, model)
            else:
                optimized_section = section
            
            optimized_sections.append(optimized_section)
            remaining_tokens -= self.token_counter.count_tokens(optimized_section, model)
            
            # Stop if we've used all tokens
            if remaining_tokens <= 0:
                break
        
        # Join the optimized sections
        optimized_prompt = "\n\n".join(optimized_sections)
        
        # Final check and truncation if needed
        if self.token_counter.count_tokens(optimized_prompt, model) > max_tokens:
            optimized_prompt = self._truncate_text(optimized_prompt, max_tokens, model)
        
        return optimized_prompt
    
    def _split_into_sections(self, prompt: str) -> List[str]:
        """
        Split a prompt into logical sections.
        
        Args:
            prompt: Prompt to split
            
        Returns:
            List of sections
        """
        # Split by double newlines (paragraph breaks)
        sections = prompt.split("\n\n")
        
        # Merge very short sections with the next section
        merged_sections = []
        current_section = ""
        
        for section in sections:
            if len(current_section) == 0:
                current_section = section
            elif len(section.strip()) < 50:  # Very short section
                current_section += "\n\n" + section
            else:
                merged_sections.append(current_section)
                current_section = section
        
        if current_section:
            merged_sections.append(current_section)
        
        return merged_sections
    
    def _prioritize_sections(self, sections: List[str]) -> List[Tuple[str, float]]:
        """
        Prioritize sections based on their importance.
        
        Args:
            sections: List of sections
            
        Returns:
            List of (section, priority) tuples
        """
        prioritized = []
        
        for i, section in enumerate(sections):
            # Determine priority based on position and content
            if i == 0:
                # First section (usually instructions) gets highest priority
                priority = 1.0
            elif i == len(sections) - 1:
                # Last section gets high priority
                priority = 0.9
            elif "example" in section.lower() or "instruction" in section.lower():
                # Examples and instructions get high priority
                priority = 0.9
            elif "context" in section.lower() or "background" in section.lower():
                # Context gets medium priority
                priority = 0.7
            else:
                # Other sections get lower priority
                priority = 0.5
            
            prioritized.append((section, priority))
        
        # Sort by priority (highest first)
        return sorted(prioritized, key=lambda x: x[1], reverse=True)
    
    def optimize_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        model: str = "gpt-3.5-turbo"
    ) -> List[Dict[str, str]]:
        """
        Optimize a list of messages to fit within a token limit.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum number of tokens
            model: Model name
            
        Returns:
            Optimized list of messages
        """
        current_tokens = self.token_counter.count_message_tokens(messages, model)
        
        if current_tokens <= max_tokens:
            return messages
        
        # Always keep the system message and the most recent user message
        system_message = None
        user_messages = []
        assistant_messages = []
        
        for message in messages:
            if message["role"] == "system":
                system_message = message
            elif message["role"] == "user":
                user_messages.append(message)
            elif message["role"] == "assistant":
                assistant_messages.append(message)
        
        # Start with the essential messages
        optimized_messages = []
        if system_message:
            optimized_messages.append(system_message)
        
        # Add the most recent user message
        if user_messages:
            optimized_messages.append(user_messages[-1])
        
        # Calculate remaining tokens
        current_tokens = self.token_counter.count_message_tokens(optimized_messages, model)
        remaining_tokens = max_tokens - current_tokens
        
        # If we have remaining tokens, add as many previous messages as possible
        if remaining_tokens > 0 and len(messages) > len(optimized_messages):
            # Interleave previous user and assistant messages, starting from the most recent
            previous_messages = []
            for i in range(min(len(user_messages) - 1, len(assistant_messages))):
                if i < len(assistant_messages):
                    previous_messages.append(assistant_messages[-(i+1)])
                if i < len(user_messages) - 1:
                    previous_messages.append(user_messages[-(i+2)])
            
            # Add as many previous messages as possible
            for message in previous_messages:
                message_tokens = self.token_counter.count_message_tokens([message], model)
                if message_tokens <= remaining_tokens:
                    optimized_messages.insert(1 if system_message else 0, message)
                    remaining_tokens -= message_tokens
                else:
                    # If the message is too long, try to optimize it
                    if message["role"] == "user" and remaining_tokens > 50:
                        optimized_content = self.optimize_prompt(message["content"], remaining_tokens - 10, model)
                        optimized_message = message.copy()
                        optimized_message["content"] = optimized_content
                        optimized_messages.insert(1 if system_message else 0, optimized_message)
                    break
        
        return optimized_messages
    
    def optimize_for_model(
        self,
        content: Union[str, List[Dict[str, str]]],
        model: str,
        max_tokens: Optional[int] = None
    ) -> Union[str, List[Dict[str, str]]]:
        """
        Optimize content to fit within a model's context limit.
        
        Args:
            content: Text or list of message dictionaries
            model: Model name
            max_tokens: Optional maximum tokens (defaults to model's limit)
            
        Returns:
            Optimized content
        """
        # Get model's maximum context length
        model_max_tokens = self.token_counter.get_max_tokens(model)
        
        # Use provided max_tokens or 90% of model's limit
        max_tokens = max_tokens or int(model_max_tokens * 0.9)
        
        # Ensure max_tokens doesn't exceed model's limit
        max_tokens = min(max_tokens, model_max_tokens)
        
        # Optimize based on content type
        if isinstance(content, str):
            return self.optimize_prompt(content, max_tokens, model)
        else:
            return self.optimize_messages(content, max_tokens, model)

class TokenUsageTracker:
    """
    Utility class for tracking token usage across LLM calls.
    
    This class provides methods for tracking and reporting token usage
    to monitor costs and optimize usage patterns.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None, db_path: Optional[str] = None):
        """
        Initialize the token usage tracker.
        
        Args:
            logger: Optional logger for logging token usage
            db_path: Optional path to SQLite database for persistent storage
        """
        self.logger = logger
        self.token_counter = TokenCounter(logger)
        self.usage_log = []
        self.model_usage = {}
        self.db_path = db_path or os.path.join(
            os.environ.get("PROJECT_DIR", ""), 
            "llm_usage.db"
        )
        self.lock = threading.Lock()
        
        # Cost per 1K tokens for different models (input/output)
        self.cost_per_1k_tokens = {
            # OpenAI models
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-32k": {"input": 0.06, "output": 0.12},
            "gpt-4-1106-preview": {"input": 0.01, "output": 0.03},
            "gpt-4-vision-preview": {"input": 0.01, "output": 0.03},
            "text-embedding-ada-002": {"input": 0.0001, "output": 0.0},
            
            # Anthropic models
            "claude-2": {"input": 0.008, "output": 0.024},
            "claude-instant-1": {"input": 0.0016, "output": 0.0056},
            
            # Default for unknown models
            "default": {"input": 0.002, "output": 0.002}
        }
        
        # Initialize database if persistent storage is enabled
        if self.db_path:
            self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database for persistent storage."""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Create tables if they don't exist
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    model TEXT,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    cost REAL,
                    success INTEGER,
                    task TEXT,
                    session_id TEXT
                )
                ''')
                
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_usage (
                    model TEXT PRIMARY KEY,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    cost REAL,
                    calls INTEGER,
                    successful_calls INTEGER,
                    last_updated REAL
                )
                ''')
                
                conn.commit()
                conn.close()
                
                # Load existing model usage from database
                self._load_model_usage()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error initializing token usage database: {e}")
    
    def _load_model_usage(self):
        """Load model usage from the database."""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM model_usage")
                rows = cursor.fetchall()
                
                for row in cursor.description:
                    print(row[0])
                
                for row in rows:
                    model = row[0]
                    self.model_usage[model] = {
                        "prompt_tokens": row[1],
                        "completion_tokens": row[2],
                        "total_tokens": row[3],
                        "cost": row[4],
                        "calls": row[5],
                        "successful_calls": row[6]
                    }
                
                conn.close()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error loading model usage from database: {e}")
    
    def _save_usage_entry(self, entry):
        """Save a usage entry to the database."""
        if not self.db_path:
            return
            
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                INSERT INTO usage_log (
                    timestamp, model, prompt_tokens, completion_tokens, 
                    total_tokens, cost, success, task, session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry["timestamp"],
                    entry["model"],
                    entry["prompt_tokens"],
                    entry["completion_tokens"],
                    entry["total_tokens"],
                    entry["cost"],
                    1 if entry["success"] else 0,
                    entry.get("task", ""),
                    entry.get("session_id", "")
                ))
                
                conn.commit()
                conn.close()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error saving usage entry to database: {e}")
    
    def _update_model_usage(self, model, prompt_tokens, completion_tokens, cost, success):
        """Update model usage in the database."""
        if not self.db_path:
            return
            
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Check if model exists
                cursor.execute("SELECT * FROM model_usage WHERE model = ?", (model,))
                row = cursor.fetchone()
                
                if row:
                    # Update existing model
                    cursor.execute('''
                    UPDATE model_usage SET
                        prompt_tokens = prompt_tokens + ?,
                        completion_tokens = completion_tokens + ?,
                        total_tokens = total_tokens + ?,
                        cost = cost + ?,
                        calls = calls + 1,
                        successful_calls = successful_calls + ?,
                        last_updated = ?
                    WHERE model = ?
                    ''', (
                        prompt_tokens,
                        completion_tokens,
                        prompt_tokens + completion_tokens,
                        cost,
                        1 if success else 0,
                        time.time(),
                        model
                    ))
                else:
                    # Insert new model
                    cursor.execute('''
                    INSERT INTO model_usage (
                        model, prompt_tokens, completion_tokens, total_tokens,
                        cost, calls, successful_calls, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        model,
                        prompt_tokens,
                        completion_tokens,
                        prompt_tokens + completion_tokens,
                        cost,
                        1,
                        1 if success else 0,
                        time.time()
                    ))
                
                conn.commit()
                conn.close()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error updating model usage in database: {e}")
    
    def track_usage(
        self, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int, 
        success: bool = True,
        task: str = "",
        session_id: str = ""
    ) -> Dict[str, Any]:
        """
        Track token usage for an LLM call.
        
        Args:
            model: Model name
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            success: Whether the call was successful
            task: Optional task identifier
            session_id: Optional session identifier
            
        Returns:
            Dictionary with usage information
        """
        # Calculate cost
        cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
        
        # Create usage entry
        usage_entry = {
            "timestamp": time.time(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost": cost,
            "success": success,
            "task": task,
            "session_id": session_id
        }
        
        # Add to usage log
        self.usage_log.append(usage_entry)
        
        # Update model usage
        if model not in self.model_usage:
            self.model_usage[model] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost": 0,
                "calls": 0,
                "successful_calls": 0
            }
        
        self.model_usage[model]["prompt_tokens"] += prompt_tokens
        self.model_usage[model]["completion_tokens"] += completion_tokens
        self.model_usage[model]["total_tokens"] += prompt_tokens + completion_tokens
        self.model_usage[model]["cost"] += cost
        self.model_usage[model]["calls"] += 1
        if success:
            self.model_usage[model]["successful_calls"] += 1
        
        # Save to database if enabled
        self._save_usage_entry(usage_entry)
        self._update_model_usage(model, prompt_tokens, completion_tokens, cost, success)
        
        # Log usage
        if self.logger:
            self.logger.info(
                f"LLM usage: model={model}, tokens={prompt_tokens}+{completion_tokens}={prompt_tokens+completion_tokens}, "
                f"cost=${cost:.6f}, success={success}"
            )
        
        return usage_entry
    
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate the cost of an LLM call.
        
        Args:
            model: Model name
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            
        Returns:
            Cost in USD
        """
        # Get cost per 1K tokens for the model
        if model in self.cost_per_1k_tokens:
            costs = self.cost_per_1k_tokens[model]
        else:
            # Default to gpt-3.5-turbo costs if model not found
            costs = self.cost_per_1k_tokens["default"]
        
        # Calculate cost
        input_cost = (prompt_tokens / 1000) * costs["input"]
        output_cost = (completion_tokens / 1000) * costs["output"]
        
        return input_cost + output_cost
    
    def get_usage_summary(self, days: Optional[int] = None) -> Dict[str, Any]:
        """
        Get a summary of token usage.
        
        Args:
            days: Optional number of days to include in the summary
            
        Returns:
            Dictionary with usage summary
        """
        if days and self.db_path:
            # Get usage from database for the specified time period
            return self._get_usage_summary_from_db(days)
        
        # Calculate from in-memory usage log
        total_prompt_tokens = sum(entry["prompt_tokens"] for entry in self.usage_log)
        total_completion_tokens = sum(entry["completion_tokens"] for entry in self.usage_log)
        total_tokens = total_prompt_tokens + total_completion_tokens
        total_cost = sum(entry["cost"] for entry in self.usage_log)
        total_calls = len(self.usage_log)
        successful_calls = sum(1 for entry in self.usage_log if entry["success"])
        
        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "model_usage": self.model_usage
        }
    
    def _get_usage_summary_from_db(self, days: int) -> Dict[str, Any]:
        """
        Get usage summary from the database for a specific time period.
        
        Args:
            days: Number of days to include in the summary
            
        Returns:
            Dictionary with usage summary
        """
        if not self.db_path:
            return self.get_usage_summary()
            
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Calculate timestamp for N days ago
                cutoff_time = time.time() - (days * 24 * 60 * 60)
                
                # Get total usage
                cursor.execute('''
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                    SUM(prompt_tokens) as total_prompt_tokens,
                    SUM(completion_tokens) as total_completion_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost) as total_cost
                FROM usage_log
                WHERE timestamp >= ?
                ''', (cutoff_time,))
                
                row = cursor.fetchone()
                
                if not row or row[0] == 0:
                    conn.close()
                    return {
                        "total_calls": 0,
                        "successful_calls": 0,
                        "success_rate": 0,
                        "total_prompt_tokens": 0,
                        "total_completion_tokens": 0,
                        "total_tokens": 0,
                        "total_cost": 0,
                        "model_usage": {}
                    }
                
                total_calls = row[0]
                successful_calls = row[1]
                total_prompt_tokens = row[2]
                total_completion_tokens = row[3]
                total_tokens = row[4]
                total_cost = row[5]
                
                # Get model-specific usage
                cursor.execute('''
                SELECT 
                    model,
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(completion_tokens) as completion_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost) as cost,
                    COUNT(*) as calls,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls
                FROM usage_log
                WHERE timestamp >= ?
                GROUP BY model
                ''', (cutoff_time,))
                
                model_usage = {}
                for row in cursor.fetchall():
                    model_usage[row[0]] = {
                        "prompt_tokens": row[1],
                        "completion_tokens": row[2],
                        "total_tokens": row[3],
                        "cost": row[4],
                        "calls": row[5],
                        "successful_calls": row[6]
                    }
                
                conn.close()
                
                return {
                    "total_calls": total_calls,
                    "successful_calls": successful_calls,
                    "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
                    "total_prompt_tokens": total_prompt_tokens,
                    "total_completion_tokens": total_completion_tokens,
                    "total_tokens": total_tokens,
                    "total_cost": total_cost,
                    "model_usage": model_usage,
                    "days": days
                }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting usage summary from database: {e}")
            return self.get_usage_summary()
    
    def estimate_cost(self, model: str, prompt: Union[str, List[Dict[str, str]]], estimated_completion_tokens: Optional[int] = None) -> Dict[str, float]:
        """
        Estimate the cost of an LLM call before making it.
        
        Args:
            model: Model name
            prompt: Prompt text or list of message dictionaries
            estimated_completion_tokens: Optional estimated number of completion tokens
            
        Returns:
            Dictionary with estimated token counts and cost
        """
        # Count prompt tokens
        if isinstance(prompt, str):
            prompt_tokens = self.token_counter.count_tokens(prompt, model)
        else:
            prompt_tokens = self.token_counter.count_message_tokens(prompt, model)
        
        # Estimate completion tokens if not provided
        if estimated_completion_tokens is None:
            estimated_completion_tokens = self.token_counter.estimate_completion_tokens(prompt_tokens, model)
        
        # Calculate estimated cost
        estimated_cost = self._calculate_cost(model, prompt_tokens, estimated_completion_tokens)
        
        return {
            "prompt_tokens": prompt_tokens,
            "estimated_completion_tokens": estimated_completion_tokens,
            "estimated_total_tokens": prompt_tokens + estimated_completion_tokens,
            "estimated_cost": estimated_cost
        }
    
    def get_usage_by_day(self, days: int = 30) -> Dict[str, Any]:
        """
        Get token usage grouped by day.
        
        Args:
            days: Number of days to include
            
        Returns:
            Dictionary with usage by day
        """
        if not self.db_path:
            return {"error": "Persistent storage not enabled"}
            
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Calculate timestamp for N days ago
                cutoff_time = time.time() - (days * 24 * 60 * 60)
                
                # Get usage by day
                cursor.execute('''
                SELECT 
                    date(datetime(timestamp, 'unixepoch')) as day,
                    COUNT(*) as calls,
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(completion_tokens) as completion_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost) as cost
                FROM usage_log
                WHERE timestamp >= ?
                GROUP BY day
                ORDER BY day
                ''', (cutoff_time,))
                
                daily_usage = []
                for row in cursor.fetchall():
                    daily_usage.append(dict(row))
                
                conn.close()
                
                return {
                    "daily_usage": daily_usage,
                    "days": days
                }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting usage by day: {e}")
            return {"error": str(e)}
    
    def get_usage_by_model(self, days: Optional[int] = None) -> Dict[str, Any]:
        """
        Get token usage grouped by model.
        
        Args:
            days: Optional number of days to include
            
        Returns:
            Dictionary with usage by model
        """
        if days is None or not self.db_path:
            return {"model_usage": self.model_usage}
            
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Calculate timestamp for N days ago
                cutoff_time = time.time() - (days * 24 * 60 * 60)
                
                # Get usage by model
                cursor.execute('''
                SELECT 
                    model,
                    COUNT(*) as calls,
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(completion_tokens) as completion_tokens,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost) as cost
                FROM usage_log
                WHERE timestamp >= ?
                GROUP BY model
                ORDER BY total_tokens DESC
                ''', (cutoff_time,))
                
                model_usage = []
                for row in cursor.fetchall():
                    model_usage.append(dict(row))
                
                conn.close()
                
                return {
                    "model_usage": model_usage,
                    "days": days
                }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting usage by model: {e}")
            return {"error": str(e)}
    
    def clear_usage_history(self) -> bool:
        """
        Clear usage history from memory and database.
        
        Returns:
            True if successful, False otherwise
        """
        # Clear in-memory usage
        self.usage_log = []
        self.model_usage = {}
        
        # Clear database if enabled
        if self.db_path:
            try:
                with self.lock:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute("DELETE FROM usage_log")
                    cursor.execute("DELETE FROM model_usage")
                    
                    conn.commit()
                    conn.close()
                
                if self.logger:
                    self.logger.info("Cleared usage history")
                
                return True
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error clearing usage history: {e}")
                return False
        
        return True

# Create singleton instances
token_counter = TokenCounter()
token_optimizer = TokenOptimizer(token_counter)
token_usage_tracker = TokenUsageTracker()
