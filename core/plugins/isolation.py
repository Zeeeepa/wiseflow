"""
Plugin isolation module for Wiseflow.

This module provides utilities for isolating plugin execution.
"""

import logging
import threading
import traceback
import time
import functools
from typing import Dict, Any, Optional, Callable, TypeVar, cast

from core.utils.error_handling import PluginError, handle_exceptions

logger = logging.getLogger(__name__)

# Type variable for function return type
T = TypeVar('T')

class PluginIsolationManager:
    """
    Plugin isolation manager.
    
    This class provides functionality to isolate plugin execution.
    """
    
    def __init__(self):
        """Initialize the plugin isolation manager."""
        self.isolation_enabled = True
        self.timeout_enabled = True
        self.default_timeout = 30.0  # seconds
        self.plugin_timeouts: Dict[str, float] = {}
    
    def set_isolation_enabled(self, enabled: bool) -> None:
        """
        Enable or disable plugin isolation.
        
        Args:
            enabled: Whether isolation should be enabled
        """
        self.isolation_enabled = enabled
        logger.info(f"Plugin isolation {'enabled' if enabled else 'disabled'}")
    
    def set_timeout_enabled(self, enabled: bool) -> None:
        """
        Enable or disable plugin timeouts.
        
        Args:
            enabled: Whether timeouts should be enabled
        """
        self.timeout_enabled = enabled
        logger.info(f"Plugin timeouts {'enabled' if enabled else 'disabled'}")
    
    def set_default_timeout(self, timeout: float) -> None:
        """
        Set the default timeout for plugin execution.
        
        Args:
            timeout: Timeout in seconds
        """
        self.default_timeout = timeout
        logger.info(f"Default plugin timeout set to {timeout} seconds")
    
    def set_plugin_timeout(self, plugin_name: str, timeout: float) -> None:
        """
        Set the timeout for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            timeout: Timeout in seconds
        """
        self.plugin_timeouts[plugin_name] = timeout
        logger.info(f"Timeout for plugin {plugin_name} set to {timeout} seconds")
    
    def get_plugin_timeout(self, plugin_name: str) -> float:
        """
        Get the timeout for a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Timeout in seconds
        """
        return self.plugin_timeouts.get(plugin_name, self.default_timeout)
    
    def isolate(self, plugin_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        Decorator to isolate plugin execution.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                if not self.isolation_enabled:
                    return func(*args, **kwargs)
                
                # Use error handler to catch and log any exceptions
                try:
                    # Execute with timeout if enabled
                    if self.timeout_enabled:
                        timeout = self.get_plugin_timeout(plugin_name)
                        result = self._execute_with_timeout(func, timeout, *args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    return result
                except Exception as e:
                    # Convert to PluginError
                    plugin_error = PluginError(
                        f"Error in plugin {plugin_name}: {str(e)}",
                        {
                            "plugin_name": plugin_name,
                            "function": func.__name__,
                            "args": str(args),
                            "kwargs": str(kwargs)
                        },
                        e
                    )
                    
                    # Log the error
                    logger.error(f"Error in plugin {plugin_name}: {str(e)}")
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                    
                    # Re-raise as PluginError
                    raise plugin_error
            
            return wrapper
        
        return decorator
    
    def _execute_with_timeout(self, func: Callable[..., T], timeout: float, *args: Any, **kwargs: Any) -> T:
        """
        Execute a function with a timeout.
        
        Args:
            func: Function to execute
            timeout: Timeout in seconds
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            TimeoutError: If the function execution times out
        """
        result: Optional[T] = None
        error: Optional[Exception] = None
        completed = threading.Event()
        
        def target() -> None:
            nonlocal result, error
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                error = e
            finally:
                completed.set()
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        
        if not completed.wait(timeout):
            raise TimeoutError(f"Plugin execution timed out after {timeout} seconds")
        
        if error:
            raise error
        
        return cast(T, result)

# Global isolation manager instance
isolation_manager = PluginIsolationManager()

