"""
Advanced connector plugin example for Wiseflow.

This plugin demonstrates advanced features of the plugin system.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List

from core.plugins.base import ConnectorPlugin, PluginMetadata, PluginSecurityLevel
from core.event_system import EventType, Event, subscribe, unsubscribe, publish_sync

logger = logging.getLogger(__name__)


class AdvancedConnector(ConnectorPlugin):
    """Advanced connector plugin example."""
    
    name = "advanced_connector"
    description = "Advanced connector plugin example"
    version = "1.0.0"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the advanced connector.
        
        Args:
            config: Configuration dictionary with the following keys:
                - api_url: API URL to connect to
                - api_key: API key for authentication
                - cache_timeout: Cache timeout in seconds (default: 300)
                - retry_count: Number of retries for failed requests (default: 3)
        """
        super().__init__(config)
        
        # Set up metadata
        self.metadata = PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author="Wiseflow Team",
            website="https://example.com/plugins/advanced-connector",
            license="MIT",
            min_system_version="4.0.0",
            max_system_version="5.0.0",
            dependencies={
                "text_processor": ">=1.0.0"
            },
            security_level=PluginSecurityLevel.MEDIUM
        )
        
        # Configuration
        self.api_url = self.config.get("api_url", "https://api.example.com")
        self.api_key = self.config.get("api_key", "")
        self.cache_timeout = self.config.get("cache_timeout", 300)
        self.retry_count = self.config.get("retry_count", 3)
        
        # Internal state
        self.connected = False
        self.cache = {}
        self.cache_timestamps = {}
        self.request_count = 0
        self.error_count = 0
        self.last_error = None
        self.lock = threading.RLock()
        self.background_thread = None
        self.stop_background = threading.Event()
    
    def initialize(self) -> bool:
        """
        Initialize the connector.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        logger.info(f"Initializing {self.name} connector")
        
        # Validate configuration
        if not self.validate_config():
            logger.error(f"Invalid configuration for {self.name} connector")
            return False
        
        # Subscribe to events
        self._subscribe_to_event(EventType.SYSTEM_SHUTDOWN, self._handle_system_shutdown)
        
        # Register resources
        self._register_resource("thread", self.lock)
        
        # Start background thread
        self.background_thread = threading.Thread(target=self._background_task)
        self.background_thread.daemon = True
        self._register_resource("thread", self.background_thread)
        self.background_thread.start()
        
        self.initialized = True
        return True
    
    def validate_config(self) -> bool:
        """
        Validate the connector configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # API key is required
        if not self.api_key:
            logger.error(f"{self.name} connector requires an API key")
            return False
        
        # Cache timeout must be positive
        if self.cache_timeout <= 0:
            logger.error(f"{self.name} connector cache timeout must be positive")
            return False
        
        # Retry count must be non-negative
        if self.retry_count < 0:
            logger.error(f"{self.name} connector retry count must be non-negative")
            return False
        
        return True
    
    def connect(self) -> bool:
        """
        Connect to the API.
        
        Returns:
            bool: True if connection was successful, False otherwise
        """
        logger.info(f"Connecting to {self.api_url}")
        
        with self.lock:
            # Simulate connection
            time.sleep(0.5)
            
            # Set connected state
            self.connected = True
            
            # Publish connection event
            self._publish_connection_event(True)
            
            return True
    
    def disconnect(self) -> bool:
        """
        Disconnect from the API.
        
        Returns:
            bool: True if disconnection was successful, False otherwise
        """
        logger.info(f"Disconnecting from {self.api_url}")
        
        with self.lock:
            # Stop background thread
            if self.background_thread and self.background_thread.is_alive():
                self.stop_background.set()
                self.background_thread.join(timeout=2.0)
            
            # Simulate disconnection
            time.sleep(0.5)
            
            # Set connected state
            self.connected = False
            
            # Publish disconnection event
            self._publish_connection_event(False)
            
            return True
    
    def fetch_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch data from the API.
        
        Args:
            query: Query string
            **kwargs: Additional parameters:
                - force_refresh: Force refresh cache (default: False)
                - timeout: Request timeout in seconds (default: 10)
                
        Returns:
            Dict[str, Any]: Dictionary containing the fetched data
        """
        logger.debug(f"Fetching data for query: {query}")
        
        # Check if we're connected
        if not self.connected:
            if not self.connect():
                return {"error": "Failed to connect to API"}
        
        # Check cache
        force_refresh = kwargs.get("force_refresh", False)
        if not force_refresh and query in self.cache:
            cache_time = self.cache_timestamps.get(query, 0)
            if time.time() - cache_time < self.cache_timeout:
                logger.debug(f"Using cached data for query: {query}")
                return self.cache[query]
        
        # Simulate API request
        with self.lock:
            self.request_count += 1
            
            # Simulate processing
            time.sleep(0.2)
            
            # Generate response
            response = {
                "query": query,
                "timestamp": time.time(),
                "results": [
                    {"id": 1, "name": f"Result 1 for {query}"},
                    {"id": 2, "name": f"Result 2 for {query}"},
                    {"id": 3, "name": f"Result 3 for {query}"}
                ],
                "metadata": {
                    "total_results": 3,
                    "processing_time": 0.2
                }
            }
            
            # Update cache
            self.cache[query] = response
            self.cache_timestamps[query] = time.time()
            
            return response
    
    def shutdown(self) -> bool:
        """
        Shutdown the connector.
        
        Returns:
            bool: True if shutdown was successful, False otherwise
        """
        logger.info(f"Shutting down {self.name} connector")
        
        # Disconnect if connected
        if self.connected:
            self.disconnect()
        
        # Unsubscribe from events
        self._unsubscribe_from_all_events()
        
        # Clear cache
        self.cache.clear()
        self.cache_timestamps.clear()
        
        self.initialized = False
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get connector statistics.
        
        Returns:
            Dict[str, Any]: Dictionary containing statistics
        """
        with self.lock:
            return {
                "connected": self.connected,
                "request_count": self.request_count,
                "error_count": self.error_count,
                "cache_size": len(self.cache),
                "last_error": str(self.last_error) if self.last_error else None
            }
    
    def clear_cache(self) -> None:
        """Clear the cache."""
        with self.lock:
            self.cache.clear()
            self.cache_timestamps.clear()
            logger.info(f"Cleared cache for {self.name} connector")
    
    def _handle_system_shutdown(self, event: Event) -> None:
        """
        Handle system shutdown event.
        
        Args:
            event: Event object
        """
        logger.info(f"Received system shutdown event, disconnecting {self.name} connector")
        self.disconnect()
    
    def _publish_connection_event(self, connected: bool) -> None:
        """
        Publish connection event.
        
        Args:
            connected: Whether the connector is connected
        """
        event_data = {
            "connector": self.name,
            "connected": connected,
            "timestamp": time.time()
        }
        
        event = Event(
            EventType.CUSTOM,
            event_data,
            self.name
        )
        
        publish_sync(event)
    
    def _background_task(self) -> None:
        """Background task for maintenance operations."""
        logger.info(f"Starting background task for {self.name} connector")
        
        while not self.stop_background.is_set():
            try:
                # Perform maintenance operations
                with self.lock:
                    # Clean expired cache entries
                    current_time = time.time()
                    expired_keys = [
                        key for key, timestamp in self.cache_timestamps.items()
                        if current_time - timestamp > self.cache_timeout
                    ]
                    
                    for key in expired_keys:
                        if key in self.cache:
                            del self.cache[key]
                        if key in self.cache_timestamps:
                            del self.cache_timestamps[key]
                    
                    if expired_keys:
                        logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
            
            except Exception as e:
                logger.error(f"Error in background task: {e}")
                with self.lock:
                    self.error_count += 1
                    self.last_error = e
            
            # Sleep for a while
            self.stop_background.wait(60.0)  # Check every minute
        
        logger.info(f"Background task for {self.name} connector stopped")

