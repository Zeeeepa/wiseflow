"""
Token management utilities for LLM interactions.

This module provides utilities for counting, tracking, and optimizing token usage
in LLM interactions to improve efficiency and reduce costs.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Union, Any

# Try to import tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

class TokenCounter:
    """
    Utility class for counting tokens in text and messages.
    
    This class provides methods for counting tokens in text and messages,
    using tiktoken if available or falling back to approximate counting.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the token counter.
        
        Args:
            logger: Optional logger for logging token counts
        """
        self.logger = logger
        self.encoders = {}
    
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
                self.encoders[model] = tiktoken.get_encoding("cl100k_base")
        
        return self.encoders[model]
    
    def count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Count the number of tokens in a text string.
        
        Args:
            text: Text to count tokens in
            model: Model name to use for token counting
            
        Returns:
            Number of tokens in the text
        """
        if TIKTOKEN_AVAILABLE:
            encoder = self._get_encoder(model)
            return len(encoder.encode(text))
        else:
            # Fallback to approximate counting if tiktoken is not available
            return self._approximate_token_count(text)
    
    def _approximate_token_count(self, text: str) -> int:
        """
        Approximate the number of tokens in a text string.
        
        This is a fallback method when tiktoken is not available.
        It's less accurate but provides a reasonable approximation.
        
        Args:
            text: Text to count tokens in
            
        Returns:
            Approximate number of tokens in the text
        """
        # Split by whitespace for word count
        words = text.split()
        
        # Count punctuation and special characters
        punctuation = sum(1 for c in text if c in '.,;:!?()[]{}"\'`~@#$%^&*-+=|\\<>/') 
        
        # Estimate: each word is ~1.3 tokens, punctuation is ~0.5 tokens
        return int(len(words) * 1.3 + punctuation * 0.5)
    
    def count_message_tokens(self, messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> int:
        """
        Count the number of tokens in a list of messages.
        
        Args:
            messages: List of message dictionaries
            model: Model name to use for token counting
            
        Returns:
            Number of tokens in the messages
        """
        if TIKTOKEN_AVAILABLE:
            encoder = self._get_encoder(model)
            
            # Different models have different message formats and token counting rules
            if "gpt-3.5" in model or "gpt-4" in model:
                # Format: every message follows <|start|>{role/name}\n{content}<|end|>
                # If there's a name, the role is omitted
                num_tokens = 0
                for message in messages:
                    num_tokens += 4  # Every message follows <|start|>{role/name}\n{content}<|end|>
                    for key, value in message.items():
                        num_tokens += len(encoder.encode(value))
                        if key == "name":  # If there's a name, the role is omitted
                            num_tokens -= 1  # Role is omitted
                return num_tokens
            else:
                # For other models, just count the tokens in the text
                return sum(self.count_tokens(json.dumps(message), model) for message in messages)
        else:
            # Fallback to approximate counting
            return sum(self._approximate_token_count(json.dumps(message)) for message in messages)
    
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
        else:
            # Default estimate
            return prompt_tokens

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
            tokens = encoder.encode(text)
            return encoder.decode(tokens[:max_tokens])
        
        # Otherwise, use a simple approach based on character count
        # Estimate: 1 token ~= 4 characters
        char_limit = max_tokens * 4
        if len(text) > char_limit:
            return text[:char_limit] + "..."
        
        return text
    
    def _optimize_prompt_content(self, prompt: str, max_tokens: int, model: str) -> str:
        """
        Optimize prompt content to fit within a token limit.
        
        This method uses more aggressive optimization techniques:
        - Remove redundant whitespace
        - Shorten examples
        - Summarize lengthy descriptions
        
        Args:
            prompt: Prompt to optimize
            max_tokens: Maximum number of tokens
            model: Model name
            
        Returns:
            Optimized prompt
        """
        # Remove redundant whitespace
        prompt = re.sub(r'\n\s*\n', '\n\n', prompt)
        prompt = re.sub(r' {2,}', ' ', prompt)
        
        # Check if we're now within the limit
        if self.token_counter.count_tokens(prompt, model) <= max_tokens:
            return prompt
        
        # Identify and shorten examples (text between triple backticks)
        def shorten_example(match):
            example = match.group(1)
            if len(example.split('\n')) > 5:
                # Keep first 2 and last 2 lines
                lines = example.split('\n')
                shortened = '\n'.join(lines[:2] + ['...'] + lines[-2:])
                return f"```{shortened}```"
            return match.group(0)
        
        prompt = re.sub(r'```([\s\S]*?)```', shorten_example, prompt)
        
        # Check if we're now within the limit
        if self.token_counter.count_tokens(prompt, model) <= max_tokens:
            return prompt
        
        # As a last resort, truncate the prompt
        return self._truncate_prompt(prompt, max_tokens, model)
    
    def optimize_messages(self, messages: List[Dict[str, str]], max_tokens: int, model: str = "gpt-3.5-turbo") -> List[Dict[str, str]]:
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

class TokenUsageTracker:
    """
    Utility class for tracking token usage across LLM calls.
    
    This class provides methods for tracking and reporting token usage
    to monitor costs and optimize usage patterns.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the token usage tracker.
        
        Args:
            logger: Optional logger for logging token usage
        """
        self.logger = logger
        self.token_counter = TokenCounter(logger)
        self.usage_log = []
        self.model_usage = {}
        
        # Cost per 1K tokens for different models (input/output)
        self.cost_per_1k_tokens = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-32k": {"input": 0.06, "output": 0.12},
            "gpt-4-1106-preview": {"input": 0.01, "output": 0.03},
            "gpt-4-vision-preview": {"input": 0.01, "output": 0.03},
            "text-embedding-ada-002": {"input": 0.0001, "output": 0.0},
            "claude-2": {"input": 0.008, "output": 0.024},
            "claude-instant-1": {"input": 0.0016, "output": 0.0056}
        }
    
    def track_usage(self, model: str, prompt_tokens: int, completion_tokens: int, success: bool = True) -> Dict[str, Any]:
        """
        Track token usage for an LLM call.
        
        Args:
            model: Model name
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            success: Whether the call was successful
            
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
            "success": success
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
            costs = self.cost_per_1k_tokens["gpt-3.5-turbo"]
        
        # Calculate cost
        input_cost = (prompt_tokens / 1000) * costs["input"]
        output_cost = (completion_tokens / 1000) * costs["output"]
        
        return input_cost + output_cost
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Get a summary of token usage.
        
        Returns:
            Dictionary with usage summary
        """
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

# Create singleton instances
token_counter = TokenCounter()
token_optimizer = TokenOptimizer(token_counter)
token_usage_tracker = TokenUsageTracker()

