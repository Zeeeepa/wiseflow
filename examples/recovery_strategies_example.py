"""
Recovery Strategies Example

This example demonstrates how to use different recovery strategies in WiseFlow,
including retry, fallback, cache, and composite strategies.
"""

import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List, Optional

# Import recovery strategies
from core.utils.recovery_strategies import (
    RecoveryStrategy,
    RetryStrategy,
    FallbackStrategy,
    CacheStrategy,
    CompositeStrategy,
    with_retry,
    with_fallback,
    with_cache,
    with_composite_recovery
)

# Simulated external API client
class ExternalAPIClient:
    """Simulated external API client with various failure modes."""
    
    def __init__(self, failure_rate: float = 0.3):
        """
        Initialize the API client.
        
        Args:
            failure_rate: Probability of API call failure (0.0 to 1.0)
        """
        self.failure_rate = failure_rate
        self.call_count = 0
    
    async def get_data(self, query: str) -> Dict[str, Any]:
        """
        Get data from the external API.
        
        Args:
            query: Search query
            
        Returns:
            Dict[str, Any]: API response
            
        Raises:
            ConnectionError: If API connection fails
            TimeoutError: If API request times out
        """
        self.call_count += 1
        print(f"API call #{self.call_count} for query: {query}")
        
        # Simulate random failure
        failure_type = random.random()
        
        if failure_type < self.failure_rate * 0.5:
            # Simulate connection error
            print("  → Connection error!")
            raise ConnectionError("API connection failed")
        
        elif failure_type < self.failure_rate:
            # Simulate timeout
            print("  → Timeout error!")
            raise TimeoutError("API request timed out")
        
        # Simulate successful response with random delay
        delay = random.uniform(0.1, 0.5)
        await asyncio.sleep(delay)
        
        print(f"  → Success (took {delay:.2f}s)")
        return {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "results": [
                {"title": f"Result 1 for {query}", "score": 0.95},
                {"title": f"Result 2 for {query}", "score": 0.87},
                {"title": f"Result 3 for {query}", "score": 0.82}
            ]
        }

# Example functions for different recovery strategies

async def demonstrate_retry_strategy():
    """Demonstrate retry strategy for handling transient failures."""
    
    print("\n=== Retry Strategy Example ===\n")
    
    # Create API client with high failure rate
    api_client = ExternalAPIClient(failure_rate=0.7)
    
    # Create retry strategy
    retry_strategy = RetryStrategy(
        max_retries=3,
        initial_backoff=0.5,
        backoff_multiplier=2.0,
        max_backoff=5.0,
        jitter=True
    )
    
    # Apply retry strategy using decorator
    @with_retry(
        max_retries=3,
        initial_backoff=0.5,
        backoff_multiplier=2.0,
        jitter=True
    )
    async def get_data_with_retry(query: str) -> Dict[str, Any]:
        """Get data with retry strategy."""
        return await api_client.get_data(query)
    
    # Try to get data with retry
    try:
        print("Calling API with retry strategy...")
        result = await get_data_with_retry("climate change")
        print(f"Retry strategy succeeded: {result}\n")
    except Exception as e:
        print(f"Retry strategy failed after multiple attempts: {e}\n")

async def demonstrate_fallback_strategy():
    """Demonstrate fallback strategy for handling failures."""
    
    print("\n=== Fallback Strategy Example ===\n")
    
    # Create API client with moderate failure rate
    api_client = ExternalAPIClient(failure_rate=0.5)
    
    # Define fallback function
    async def fallback_data_source(query: str) -> Dict[str, Any]:
        """Fallback data source when primary source fails."""
        print(f"Using fallback data source for query: {query}")
        await asyncio.sleep(0.2)  # Simulate some processing time
        
        return {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "results": [
                {"title": f"Fallback result for {query}", "score": 0.7}
            ],
            "note": "Using fallback results due to API failure"
        }
    
    # Apply fallback strategy using decorator
    @with_fallback(fallback_func=fallback_data_source)
    async def get_data_with_fallback(query: str) -> Dict[str, Any]:
        """Get data with fallback strategy."""
        return await api_client.get_data(query)
    
    # Try to get data with fallback
    try:
        print("Calling API with fallback strategy...")
        result = await get_data_with_fallback("renewable energy")
        print(f"Result: {result}\n")
    except Exception as e:
        print(f"Both primary and fallback failed: {e}\n")

async def demonstrate_cache_strategy():
    """Demonstrate cache strategy for handling failures."""
    
    print("\n=== Cache Strategy Example ===\n")
    
    # Create API client with moderate failure rate
    api_client = ExternalAPIClient(failure_rate=0.5)
    
    # Create cache dictionary
    cache: Dict[Tuple, Tuple[Any, datetime]] = {}
    
    # Apply cache strategy using decorator
    @with_cache(
        cache=cache,
        ttl=timedelta(minutes=5)
    )
    async def get_data_with_cache(query: str) -> Dict[str, Any]:
        """Get data with cache strategy."""
        return await api_client.get_data(query)
    
    # Make first call to populate cache
    print("First call (should hit the API):")
    result1 = await get_data_with_cache("machine learning")
    print(f"Result: {result1}\n")
    
    # Make second call with same query (might use cache if API fails)
    print("Second call with same query (might use cache if API fails):")
    result2 = await get_data_with_cache("machine learning")
    print(f"Result: {result2}\n")
    
    # Make call with different query
    print("Call with different query (should hit the API):")
    result3 = await get_data_with_cache("artificial intelligence")
    print(f"Result: {result3}\n")

async def demonstrate_composite_strategy():
    """Demonstrate composite strategy combining multiple strategies."""
    
    print("\n=== Composite Strategy Example ===\n")
    
    # Create API client with high failure rate
    api_client = ExternalAPIClient(failure_rate=0.8)
    
    # Define fallback function
    async def fallback_data_source(query: str) -> Dict[str, Any]:
        """Fallback data source when primary source fails."""
        print(f"Using fallback data source for query: {query}")
        
        # Simulate fallback that sometimes fails too
        if random.random() < 0.3:
            raise Exception("Fallback source also failed")
        
        await asyncio.sleep(0.2)  # Simulate some processing time
        
        return {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "results": [
                {"title": f"Fallback result for {query}", "score": 0.7}
            ],
            "note": "Using fallback results due to API failure"
        }
    
    # Create cache dictionary
    cache: Dict[Tuple, Tuple[Any, datetime]] = {}
    
    # Create individual strategies
    retry_strategy = RetryStrategy(max_retries=2, initial_backoff=0.5)
    fallback_strategy = FallbackStrategy(fallback_func=fallback_data_source)
    cache_strategy = CacheStrategy(cache=cache, ttl=timedelta(minutes=5))
    
    # Create composite strategy
    composite_strategy = CompositeStrategy([
        retry_strategy,      # First try with retries
        fallback_strategy,   # If retries fail, use fallback
        cache_strategy       # If both fail, try to use cache
    ])
    
    # Apply composite strategy using decorator
    @with_composite_recovery(strategies=[retry_strategy, fallback_strategy, cache_strategy])
    async def get_data_with_composite(query: str) -> Dict[str, Any]:
        """Get data with composite recovery strategy."""
        return await api_client.get_data(query)
    
    # Make first call to populate cache
    print("First call (should try API with retries, then fallback, then populate cache):")
    result1 = await get_data_with_composite("quantum computing")
    print(f"Result: {result1}\n")
    
    # Make second call with same query
    print("Second call with same query (might use cache if API and fallback fail):")
    result2 = await get_data_with_composite("quantum computing")
    print(f"Result: {result2}\n")

async def main():
    """Run all demonstrations."""
    await demonstrate_retry_strategy()
    await demonstrate_fallback_strategy()
    await demonstrate_cache_strategy()
    await demonstrate_composite_strategy()

if __name__ == "__main__":
    asyncio.run(main())

