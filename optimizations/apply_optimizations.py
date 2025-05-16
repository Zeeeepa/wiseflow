"""
Apply performance optimizations to WiseFlow.

This module provides functions to apply all performance optimizations to WiseFlow.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional
import importlib
import sys

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimizations.database_optimizations import optimize_all_databases
from optimizations.crawler_optimizations import content_cache, rate_limiter
from optimizations.llm_optimizations import llm_cache, openai_circuit_breaker
from optimizations.thread_pool_optimizations import adaptive_thread_pool_manager
from optimizations.resource_monitor_optimizations import optimized_resource_monitor
from optimizations.dashboard_optimizations import dashboard_optimizer

logger = logging.getLogger(__name__)

async def apply_database_optimizations():
    """Apply database optimizations."""
    logger.info("Applying database optimizations...")
    await optimize_all_databases()
    logger.info("Database optimizations applied")

async def apply_crawler_optimizations():
    """Apply crawler optimizations."""
    logger.info("Applying crawler optimizations...")
    
    # Initialize content cache
    cache_dir = os.path.join(os.getenv("PROJECT_DIR", ""), ".crawl4ai", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Nothing to do here as the optimizations are applied when the modules are imported
    logger.info("Crawler optimizations applied")

async def apply_llm_optimizations():
    """Apply LLM optimizations."""
    logger.info("Applying LLM optimizations...")
    
    # Initialize LLM cache
    cache_dir = os.path.join(os.getenv("PROJECT_DIR", ""), ".crawl4ai", "llm_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Nothing to do here as the optimizations are applied when the modules are imported
    logger.info("LLM optimizations applied")

async def apply_thread_pool_optimizations():
    """Apply thread pool optimizations."""
    logger.info("Applying thread pool optimizations...")
    
    # Nothing to do here as the optimizations are applied when the modules are imported
    logger.info("Thread pool optimizations applied")

async def apply_resource_monitor_optimizations():
    """Apply resource monitor optimizations."""
    logger.info("Applying resource monitor optimizations...")
    
    # Initialize resource monitor
    log_dir = os.path.join(os.getenv("PROJECT_DIR", ""), ".crawl4ai", "resource_logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Start the optimized resource monitor
    await optimized_resource_monitor.start()
    
    logger.info("Resource monitor optimizations applied")

async def apply_dashboard_optimizations():
    """Apply dashboard optimizations."""
    logger.info("Applying dashboard optimizations...")
    
    # Initialize dashboard optimizer
    cache_dir = os.path.join(os.getenv("PROJECT_DIR", ""), ".crawl4ai", "dashboard_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Nothing to do here as the optimizations are applied when the modules are imported
    logger.info("Dashboard optimizations applied")

async def apply_all_optimizations():
    """Apply all optimizations."""
    logger.info("Applying all performance optimizations...")
    
    # Apply optimizations in order
    await apply_database_optimizations()
    await apply_crawler_optimizations()
    await apply_llm_optimizations()
    await apply_thread_pool_optimizations()
    await apply_resource_monitor_optimizations()
    await apply_dashboard_optimizations()
    
    logger.info("All performance optimizations applied")

def patch_modules():
    """Patch existing modules with optimized versions."""
    logger.info("Patching modules with optimized versions...")
    
    # Patch resource monitor
    try:
        from core import resource_monitor
        resource_monitor.resource_monitor = optimized_resource_monitor
        logger.info("Patched core.resource_monitor")
    except ImportError:
        logger.warning("Could not patch core.resource_monitor")
    
    # Patch thread pool manager
    try:
        from core import thread_pool_manager
        thread_pool_manager.thread_pool_manager = adaptive_thread_pool_manager
        logger.info("Patched core.thread_pool_manager")
    except ImportError:
        logger.warning("Could not patch core.thread_pool_manager")
    
    logger.info("Module patching complete")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the optimization process
    asyncio.run(apply_all_optimizations())
    
    # Patch modules
    patch_modules()
    
    logger.info("Performance optimization process completed")

