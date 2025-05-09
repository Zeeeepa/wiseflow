import os
import time
import psutil
from colorama import Fore
from typing import Optional, Dict, List, Any, Tuple
import asyncio
import gc
import logging
import traceback
import random

# from contextlib import nullcontext, asynccontextmanager
from contextlib import asynccontextmanager

async def close(self):
    """
    Close the web crawler.
    
    This method cleans up resources used by the crawler.
    
    Steps:
    1. Clean up browser resources
    2. Close any open pages and contexts
    """
    # Cancel memory monitor task
    if self._memory_monitor_task and not self._memory_monitor_task.done():
        self._memory_monitor_task.cancel()
        try:
            await self._memory_monitor_task
        except asyncio.CancelledError:
            pass
    
    # Cancel any active tasks
    async with self._task_lock:
        for task in self._active_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to complete or be cancelled
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        self._active_tasks.clear()
    
    # Close crawler strategy
    try:
        await self.crawler_strategy.__aexit__(None, None, None)
    except Exception as e:
        self.logger.error(f"Error closing crawler strategy: {str(e)}")
    
    # Clear domain cooldowns
    self._domain_cooldowns.clear()
    
    # Clear memory history
    self._memory_history.clear()
    
    # Force garbage collection
    gc.collect()
    
    self.ready = False
