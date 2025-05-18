"""
Advanced LLM Features Example

This example demonstrates how to use advanced LLM features in WiseFlow,
including specialized prompting, recovery strategies, and experimental features.
"""

import asyncio
import os
from datetime import timedelta
from typing import Dict, Any, Tuple

# Import core functionality
from core.llms.advanced.specialized_prompting import (
    SpecializedPromptProcessor,
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_ACADEMIC,
    TASK_EXTRACTION,
    TASK_SUMMARIZATION
)

# Import recovery strategies
from core.utils.recovery_strategies import (
    RetryStrategy,
    FallbackStrategy,
    with_retry,
    with_fallback
)

# Import experimental features
from core.experimental import (
    chain_of_thought,
    multi_step_reasoning
)

# Configure your API key
os.environ["OPENAI_API_KEY"] = "your-api-key-here"  # Replace with your actual API key

async def demonstrate_specialized_prompting():
    """Demonstrate specialized prompting for different content types."""
    
    print("\n=== Specialized Prompting Example ===\n")
    
    # Create a specialized prompt processor
    processor = SpecializedPromptProcessor()
    
    # Example content
    academic_content = """
    Abstract: This study investigates the impact of climate change on biodiversity
    in tropical rainforests. Through a meta-analysis of 42 peer-reviewed studies,
    we found that a 1°C increase in average temperature correlates with a 5-7%
    reduction in species diversity across multiple taxa. The implications for
    conservation efforts are discussed.
    """
    
    # Process academic content with specialized prompting
    result = await processor.process(
        content=academic_content,
        focus_point="What are the key findings and their implications?",
        explanation="Focus on quantitative results and conservation implications.",
        content_type=CONTENT_TYPE_ACADEMIC,
        task=TASK_EXTRACTION
    )
    
    print(f"Academic Content Analysis:\n{result['result']}\n")
    
    # Example for summarization
    news_content = """
    The city council voted yesterday to approve the new urban development plan
    that will transform the downtown area. The plan includes provisions for
    affordable housing, green spaces, and improved public transportation.
    Critics argue that the plan doesn't address concerns about gentrification,
    while supporters highlight the economic benefits and sustainability features.
    """
    
    # Process news content with summarization
    result = await processor.process(
        content=news_content,
        focus_point="Summarize the key points of the urban development plan and the debate around it.",
        content_type=CONTENT_TYPE_TEXT,
        task=TASK_SUMMARIZATION
    )
    
    print(f"News Content Summarization:\n{result['result']}\n")

async def demonstrate_recovery_strategies():
    """Demonstrate recovery strategies for handling failures."""
    
    print("\n=== Recovery Strategies Example ===\n")
    
    # Example of a function that might fail
    async def unreliable_api_call(query: str) -> Dict[str, Any]:
        """Simulate an unreliable API call that sometimes fails."""
        import random
        
        # Simulate random failure (30% chance)
        if random.random() < 0.3:
            raise ConnectionError("API connection failed")
        
        # Simulate successful response
        return {
            "query": query,
            "results": [
                {"title": f"Result 1 for {query}", "score": 0.95},
                {"title": f"Result 2 for {query}", "score": 0.87},
                {"title": f"Result 3 for {query}", "score": 0.82}
            ]
        }
    
    # Example of a fallback function
    async def fallback_api_call(query: str) -> Dict[str, Any]:
        """Fallback function for when the primary API fails."""
        return {
            "query": query,
            "results": [
                {"title": f"Fallback result for {query}", "score": 0.7}
            ],
            "note": "Using fallback results due to API failure"
        }
    
    # Apply retry strategy
    @with_retry(
        max_retries=3,
        initial_backoff=0.5,
        backoff_multiplier=2.0,
        jitter=True
    )
    async def reliable_api_call(query: str) -> Dict[str, Any]:
        """Make API call with retry strategy."""
        return await unreliable_api_call(query)
    
    # Apply fallback strategy
    @with_fallback(
        fallback_func=fallback_api_call
    )
    async def api_call_with_fallback(query: str) -> Dict[str, Any]:
        """Make API call with fallback strategy."""
        return await unreliable_api_call(query)
    
    # Demonstrate retry strategy
    try:
        print("Calling API with retry strategy...")
        result = await reliable_api_call("climate change")
        print(f"Retry strategy succeeded: {result}\n")
    except Exception as e:
        print(f"Retry strategy failed after multiple attempts: {e}\n")
    
    # Demonstrate fallback strategy
    try:
        print("Calling API with fallback strategy...")
        result = await api_call_with_fallback("renewable energy")
        print(f"Fallback strategy result: {result}\n")
    except Exception as e:
        print(f"Fallback strategy failed: {e}\n")

async def demonstrate_experimental_features():
    """Demonstrate experimental advanced reasoning features."""
    
    print("\n=== Experimental Features Example ===\n")
    
    # Example content for chain of thought reasoning
    complex_problem = """
    A train leaves Station A at 2:00 PM traveling at 60 mph. Another train leaves 
    Station B at 3:00 PM traveling at 75 mph towards Station A. If the stations 
    are 390 miles apart, at what time will the trains meet?
    """
    
    # Use chain of thought reasoning
    print("Using chain of thought reasoning...")
    cot_result = await chain_of_thought(
        content=complex_problem,
        focus_point="Solve the problem step by step.",
        explanation="Show your work and explain each step of the calculation."
    )
    
    print(f"Chain of Thought Result:\n{cot_result['result']}\n")
    
    # Example content for multi-step reasoning
    analysis_request = """
    Company XYZ's quarterly financial data:
    - Q1: Revenue $10M, Expenses $7M
    - Q2: Revenue $12M, Expenses $8M
    - Q3: Revenue $9M, Expenses $7.5M
    - Q4: Revenue $15M, Expenses $10M
    """
    
    # Use multi-step reasoning
    print("Using multi-step reasoning...")
    msr_result = await multi_step_reasoning(
        content=analysis_request,
        focus_point="Analyze the company's financial performance and trends.",
        explanation="Calculate quarterly profits, profit margins, and identify trends."
    )
    
    print(f"Multi-Step Reasoning Result:\n{msr_result['result']}\n")

async def main():
    """Run all demonstrations."""
    await demonstrate_specialized_prompting()
    await demonstrate_recovery_strategies()
    await demonstrate_experimental_features()

if __name__ == "__main__":
    asyncio.run(main())

