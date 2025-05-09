"""
Unified LLM interface for Wiseflow.

This module provides a unified interface for interacting with different LLM backends.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Literal
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    LITELLM = "litellm"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    FALLBACK = "fallback"

class LLMInterface:
    """Unified interface for LLM interactions."""
    
    def __init__(
        self,
        provider: Union[str, LLMProvider] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 60.0,
        max_concurrent_requests: int = 5
    ):
        """Initialize the LLM interface."""
        self.provider = LLMProvider(provider) if provider else self._get_default_provider()
        self.model = model or os.environ.get("PRIMARY_MODEL", "")
        self.api_key = api_key or self._get_api_key()
        self.api_base = api_base or self._get_api_base()
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_concurrent_requests = max_concurrent_requests
        
        # Initialize semaphore for concurrency control
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Initialize the appropriate client
        self._initialize_client()
    
    def _get_default_provider(self) -> LLMProvider:
        """Get the default LLM provider from environment variables."""
        provider = os.environ.get("LLM_PROVIDER", "litellm")
        try:
            return LLMProvider(provider.lower())
        except ValueError:
            logger.warning(f"Invalid LLM provider: {provider}. Using litellm as fallback.")
            return LLMProvider.LITELLM
    
    def _get_api_key(self) -> str:
        """Get the API key for the LLM provider."""
        if self.provider == LLMProvider.OPENAI:
            return os.environ.get("OPENAI_API_KEY", "")
        elif self.provider == LLMProvider.ANTHROPIC:
            return os.environ.get("ANTHROPIC_API_KEY", "")
        elif self.provider == LLMProvider.AZURE:
            return os.environ.get("AZURE_API_KEY", "")
        else:
            return os.environ.get("LLM_API_KEY", "")
    
    def _get_api_base(self) -> str:
        """Get the API base URL for the LLM provider."""
        if self.provider == LLMProvider.OPENAI:
            return os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        elif self.provider == LLMProvider.ANTHROPIC:
            return os.environ.get("ANTHROPIC_API_BASE", "https://api.anthropic.com")
        elif self.provider == LLMProvider.AZURE:
            return os.environ.get("AZURE_API_BASE", "")
        else:
            return os.environ.get("LLM_API_BASE", "")
    
    def _initialize_client(self):
        """Initialize the appropriate client based on the provider."""
        if self.provider == LLMProvider.OPENAI:
            self._initialize_openai_client()
        elif self.provider == LLMProvider.LITELLM:
            self._initialize_litellm_client()
        elif self.provider == LLMProvider.ANTHROPIC:
            self._initialize_anthropic_client()
        elif self.provider == LLMProvider.AZURE:
            self._initialize_azure_client()
        else:
            logger.warning(f"Unsupported provider: {self.provider}. Using fallback.")
            self.provider = LLMProvider.FALLBACK
    
    def _initialize_openai_client(self):
        """Initialize the OpenAI client."""
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)
            logger.info("OpenAI client initialized successfully.")
        except ImportError:
            logger.error("Failed to import OpenAI. Make sure it's installed.")
            self.provider = LLMProvider.FALLBACK
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.provider = LLMProvider.FALLBACK
    
    def _initialize_litellm_client(self):
        """Initialize the LiteLLM client."""
        try:
            import litellm
            self.client = litellm
            logger.info("LiteLLM client initialized successfully.")
        except ImportError:
            logger.error("Failed to import LiteLLM. Make sure it's installed.")
            self.provider = LLMProvider.FALLBACK
        except Exception as e:
            logger.error(f"Failed to initialize LiteLLM client: {e}")
            self.provider = LLMProvider.FALLBACK
    
    def _initialize_anthropic_client(self):
        """Initialize the Anthropic client."""
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("Anthropic client initialized successfully.")
        except ImportError:
            logger.error("Failed to import Anthropic. Make sure it's installed.")
            self.provider = LLMProvider.FALLBACK
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            self.provider = LLMProvider.FALLBACK
    
    def _initialize_azure_client(self):
        """Initialize the Azure OpenAI client."""
        try:
            from openai import AsyncAzureOpenAI
            self.client = AsyncAzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.api_base,
                api_version=os.environ.get("AZURE_API_VERSION", "2023-05-15")
            )
            logger.info("Azure OpenAI client initialized successfully.")
        except ImportError:
            logger.error("Failed to import Azure OpenAI. Make sure it's installed.")
            self.provider = LLMProvider.FALLBACK
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            self.provider = LLMProvider.FALLBACK
    
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using the LLM.
        
        Args:
            messages: List of message dictionaries to send to the API
            model: Model name to use for the API call
            temperature: Temperature for generation
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional keyword arguments to pass to the API
            
        Returns:
            Dictionary with the generated text and metadata
        """
        model = model or self.model
        
        if not model:
            logger.error("No model specified for generation")
            return {
                "text": "",
                "error": "No model specified for generation",
                "metadata": {
                    "provider": self.provider,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
        # Use the appropriate generation method based on the provider
        if self.provider == LLMProvider.OPENAI:
            return await self._generate_openai(messages, model, temperature, max_tokens, **kwargs)
        elif self.provider == LLMProvider.LITELLM:
            return await self._generate_litellm(messages, model, temperature, max_tokens, **kwargs)
        elif self.provider == LLMProvider.ANTHROPIC:
            return await self._generate_anthropic(messages, model, temperature, max_tokens, **kwargs)
        elif self.provider == LLMProvider.AZURE:
            return await self._generate_azure(messages, model, temperature, max_tokens, **kwargs)
        else:
            return await self._generate_fallback(messages, model, temperature, max_tokens, **kwargs)
    
    async def _generate_openai(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using OpenAI."""
        async with self.semaphore:
            start_time = datetime.now()
            
            for retry in range(self.max_retries):
                try:
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    
                    return {
                        "text": response.choices[0].message.content,
                        "metadata": {
                            "provider": self.provider,
                            "model": model,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "usage": {
                                "prompt_tokens": response.usage.prompt_tokens,
                                "completion_tokens": response.usage.completion_tokens,
                                "total_tokens": response.usage.total_tokens
                            },
                            "latency": (datetime.now() - start_time).total_seconds(),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                except Exception as e:
                    logger.error(f"Error generating text with OpenAI (retry {retry+1}/{self.max_retries}): {e}")
                    if retry == self.max_retries - 1:
                        return {
                            "text": "",
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "metadata": {
                                "provider": self.provider,
                                "model": model,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                                "latency": (datetime.now() - start_time).total_seconds(),
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                    await asyncio.sleep(2 ** retry)  # Exponential backoff
    
    async def _generate_litellm(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using LiteLLM."""
        async with self.semaphore:
            start_time = datetime.now()
            
            for retry in range(self.max_retries):
                try:
                    # Run in a thread to avoid blocking the event loop
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None, 
                        lambda: self.client.completion(
                            model=model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            **kwargs
                        )
                    )
                    
                    return {
                        "text": response.choices[0].message.content,
                        "metadata": {
                            "provider": self.provider,
                            "model": model,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "usage": {
                                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                                "total_tokens": getattr(response.usage, "total_tokens", 0)
                            },
                            "latency": (datetime.now() - start_time).total_seconds(),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                except Exception as e:
                    logger.error(f"Error generating text with LiteLLM (retry {retry+1}/{self.max_retries}): {e}")
                    if retry == self.max_retries - 1:
                        return {
                            "text": "",
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "metadata": {
                                "provider": self.provider,
                                "model": model,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                                "latency": (datetime.now() - start_time).total_seconds(),
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                    await asyncio.sleep(2 ** retry)  # Exponential backoff
    
    async def _generate_anthropic(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using Anthropic."""
        async with self.semaphore:
            start_time = datetime.now()
            
            for retry in range(self.max_retries):
                try:
                    # Convert messages to Anthropic format
                    system_message = ""
                    user_messages = []
                    
                    for message in messages:
                        if message.get("role") == "system":
                            system_message = message.get("content", "")
                        elif message.get("role") == "user":
                            user_messages.append(message.get("content", ""))
                    
                    # Combine all user messages with a separator
                    user_content = "\n\n".join(user_messages) if user_messages else ""
                    
                    response = await self.client.messages.create(
                        model=model,
                        system=system_message,
                        messages=[{"role": "user", "content": user_content}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    
                    return {
                        "text": response.content[0].text,
                        "metadata": {
                            "provider": self.provider,
                            "model": model,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "usage": {
                                "prompt_tokens": getattr(response, "usage", {}).get("input_tokens", 0),
                                "completion_tokens": getattr(response, "usage", {}).get("output_tokens", 0),
                                "total_tokens": getattr(response, "usage", {}).get("input_tokens", 0) + 
                                                getattr(response, "usage", {}).get("output_tokens", 0)
                            },
                            "latency": (datetime.now() - start_time).total_seconds(),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                except Exception as e:
                    logger.error(f"Error generating text with Anthropic (retry {retry+1}/{self.max_retries}): {e}")
                    if retry == self.max_retries - 1:
                        return {
                            "text": "",
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "metadata": {
                                "provider": self.provider,
                                "model": model,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                                "latency": (datetime.now() - start_time).total_seconds(),
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                    await asyncio.sleep(2 ** retry)  # Exponential backoff
    
    async def _generate_azure(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using Azure OpenAI."""
        async with self.semaphore:
            start_time = datetime.now()
            
            for retry in range(self.max_retries):
                try:
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    
                    return {
                        "text": response.choices[0].message.content,
                        "metadata": {
                            "provider": self.provider,
                            "model": model,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "usage": {
                                "prompt_tokens": response.usage.prompt_tokens,
                                "completion_tokens": response.usage.completion_tokens,
                                "total_tokens": response.usage.total_tokens
                            },
                            "latency": (datetime.now() - start_time).total_seconds(),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                except Exception as e:
                    logger.error(f"Error generating text with Azure OpenAI (retry {retry+1}/{self.max_retries}): {e}")
                    if retry == self.max_retries - 1:
                        return {
                            "text": "",
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "metadata": {
                                "provider": self.provider,
                                "model": model,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                                "latency": (datetime.now() - start_time).total_seconds(),
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                    await asyncio.sleep(2 ** retry)  # Exponential backoff
    
    async def _generate_fallback(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text using a fallback method."""
        logger.warning("Using fallback generation method")
        
        # Extract the user's message
        user_message = ""
        for message in messages:
            if message.get("role") == "user":
                user_message = message.get("content", "")
                break
        
        return {
            "text": f"Fallback response: Unable to generate text using LLM. Please check your configuration.",
            "metadata": {
                "provider": self.provider,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timestamp": datetime.now().isoformat()
            }
        }

# Create a singleton instance
llm_interface = LLMInterface()

# Convenience function
async def generate(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    **kwargs
) -> Dict[str, Any]:
    """Generate text using the LLM interface."""
    return await llm_interface.generate(messages, model, temperature, max_tokens, **kwargs)

