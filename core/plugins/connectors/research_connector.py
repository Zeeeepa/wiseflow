"""Research connector for wiseflow.

This connector provides deep research capabilities using various search APIs and research modes.
It's based on the open_deep_research library but implemented directly in wiseflow.
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Union, Callable, Tuple
from enum import Enum

from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI, CacheStrategy
from core.plugins.connectors.research.utils import format_sections, ResearchError, SearchAPIError, ConfigurationError
from core.plugins.connectors.research.state import ReportState, Sections

logger = logging.getLogger(__name__)

class ResearchStatus(Enum):
    """Status of a research operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ResearchConnector:
    """Research connector for wiseflow.
    
    This connector provides deep research capabilities using various search APIs and research modes.
    It supports:
    - Multiple research modes (linear, graph-based, multi-agent)
    - Configurable search APIs (Tavily, Perplexity, Exa, etc.)
    - Continuous topic research (building on previous queries)
    - Customizable parameters for search depth and query generation
    - Comprehensive error handling and recovery
    - Performance optimization through caching
    - Flexible configuration options
    """
    
    def __init__(self, config: Optional[Configuration] = None):
        """Initialize the research connector.
        
        Args:
            config (Configuration, optional): Configuration for the research. Defaults to None.
        """
        self.config = config or Configuration()
        self._status = ResearchStatus.PENDING
        self._progress_callbacks: List[Callable[[str, float], None]] = []
        self._error_callbacks: List[Callable[[Exception], None]] = []
        
    def research(self, topic: str, **kwargs) -> Dict[str, Any]:
        """Perform research on a topic.
        
        Args:
            topic (str): The topic to research
            **kwargs: Additional arguments to override configuration
            
        Returns:
            Dict[str, Any]: The research results including report sections and metadata
            
        Raises:
            ResearchError: If there's an error during research
            ConfigurationError: If there's an error with the configuration
            SearchAPIError: If there's an error with the search API
        """
        start_time = time.time()
        self._status = ResearchStatus.IN_PROGRESS
        self._report_progress("Starting research", 0.0)
        
        try:
            # Update config with any kwargs
            self._update_config_from_kwargs(kwargs)
            
            # Get the appropriate research graph based on configuration
            from core.plugins.connectors.research import get_research_graph
            graph = get_research_graph(self.config)
            
            # Initialize the state
            state = ReportState(
                topic=topic,
                sections=Sections(sections=[]),
                queries=[],
                search_results=[],
                feedback=None,
                config=self.config
            )
            
            # Run the research graph
            self._report_progress("Running research graph", 0.2)
            result = graph.invoke(state)
            
            # Format the results
            self._report_progress("Formatting results", 0.9)
            formatted_sections = format_sections(result.sections)
            
            # Create the result dictionary
            research_result = {
                "topic": topic,
                "sections": formatted_sections,
                "raw_sections": result.sections,
                "metadata": {
                    "search_api": self.config.search_api.value,
                    "research_mode": self.config.research_mode.value,
                    "search_depth": self.config.max_search_depth,
                    "queries_per_iteration": self.config.number_of_queries,
                    "duration_seconds": time.time() - start_time
                }
            }
            
            self._status = ResearchStatus.COMPLETED
            self._report_progress("Research completed", 1.0)
            
            return research_result
            
        except Exception as e:
            self._status = ResearchStatus.FAILED
            self._report_progress(f"Research failed: {str(e)}", 1.0)
            self._report_error(e)
            
            # Re-raise the exception with more context
            if isinstance(e, (ResearchError, ConfigurationError, SearchAPIError)):
                raise
            else:
                raise ResearchError(f"Research failed: {str(e)}") from e
    
    def continuous_research(self, previous_results: Dict[str, Any], new_topic: str, **kwargs) -> Dict[str, Any]:
        """Continue research based on previous results.
        
        Args:
            previous_results (Dict[str, Any]): Results from a previous research call
            new_topic (str): The new topic or follow-up question
            **kwargs: Additional arguments to override configuration
            
        Returns:
            Dict[str, Any]: The research results including report sections and metadata
            
        Raises:
            ResearchError: If there's an error during research
            ConfigurationError: If there's an error with the configuration
            SearchAPIError: If there's an error with the search API
        """
        start_time = time.time()
        self._status = ResearchStatus.IN_PROGRESS
        self._report_progress("Starting continuous research", 0.0)
        
        try:
            # Update config with any kwargs
            self._update_config_from_kwargs(kwargs)
            
            # Get the appropriate research graph based on configuration
            from core.plugins.connectors.research import get_research_graph
            graph = get_research_graph(self.config)
            
            # Initialize the state with previous context
            state = ReportState(
                topic=new_topic,
                sections=previous_results.get("raw_sections", Sections(sections=[])),
                queries=[],
                search_results=[],
                feedback=None,
                config=self.config,
                previous_topic=previous_results.get("topic", "")
            )
            
            # Run the research graph
            self._report_progress("Running research graph", 0.2)
            result = graph.invoke(state)
            
            # Format the results
            self._report_progress("Formatting results", 0.9)
            formatted_sections = format_sections(result.sections)
            
            # Create the result dictionary
            research_result = {
                "topic": new_topic,
                "previous_topic": previous_results.get("topic", ""),
                "sections": formatted_sections,
                "raw_sections": result.sections,
                "metadata": {
                    "search_api": self.config.search_api.value,
                    "research_mode": self.config.research_mode.value,
                    "search_depth": self.config.max_search_depth,
                    "queries_per_iteration": self.config.number_of_queries,
                    "continuous": True,
                    "duration_seconds": time.time() - start_time
                }
            }
            
            self._status = ResearchStatus.COMPLETED
            self._report_progress("Continuous research completed", 1.0)
            
            return research_result
            
        except Exception as e:
            self._status = ResearchStatus.FAILED
            self._report_progress(f"Continuous research failed: {str(e)}", 1.0)
            self._report_error(e)
            
            # Re-raise the exception with more context
            if isinstance(e, (ResearchError, ConfigurationError, SearchAPIError)):
                raise
            else:
                raise ResearchError(f"Continuous research failed: {str(e)}") from e
    
    def set_config(self, **kwargs) -> None:
        """Update the configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        self._update_config_from_kwargs(kwargs)
    
    def get_status(self) -> ResearchStatus:
        """Get the current status of the research.
        
        Returns:
            ResearchStatus: The current status
        """
        return self._status
    
    def register_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """Register a callback for progress updates.
        
        Args:
            callback (Callable[[str, float], None]): Callback function that takes a message and progress percentage
        """
        self._progress_callbacks.append(callback)
    
    def register_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """Register a callback for error handling.
        
        Args:
            callback (Callable[[Exception], None]): Callback function that takes an exception
        """
        self._error_callbacks.append(callback)
    
    def save_config(self, filepath: str) -> None:
        """Save the current configuration to a file.
        
        Args:
            filepath (str): Path to save the configuration
        """
        self.config.save_to_file(filepath)
    
    @classmethod
    def load_config(cls, filepath: str) -> Configuration:
        """Load configuration from a file.
        
        Args:
            filepath (str): Path to the configuration file
            
        Returns:
            Configuration: The loaded configuration
        """
        return Configuration.load_from_file(filepath)
    
    def _update_config_from_kwargs(self, kwargs: Dict[str, Any]) -> None:
        """Update configuration from keyword arguments.
        
        Args:
            kwargs (Dict[str, Any]): Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Re-validate configuration after updates
        self.config._validate_configuration()
    
    def _report_progress(self, message: str, progress: float) -> None:
        """Report progress to registered callbacks.
        
        Args:
            message (str): Progress message
            progress (float): Progress percentage (0.0 to 1.0)
        """
        logger.info(f"Research progress: {message} ({progress:.1%})")
        for callback in self._progress_callbacks:
            try:
                callback(message, progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {str(e)}")
    
    def _report_error(self, error: Exception) -> None:
        """Report error to registered callbacks.
        
        Args:
            error (Exception): The error that occurred
        """
        logger.error(f"Research error: {str(error)}", exc_info=True)
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error in error callback: {str(e)}")
                
    def stream_research(self, topic: str, **kwargs) -> Tuple[Dict[str, Any], Callable[[], None]]:
        """Start a research operation that streams results as they become available.
        
        Args:
            topic (str): The topic to research
            **kwargs: Additional arguments to override configuration
            
        Returns:
            Tuple[Dict[str, Any], Callable[[], None]]: Initial result structure and a function to cancel the operation
            
        Note:
            This method returns immediately with an initial result structure.
            Results will be updated as they become available through the registered callbacks.
        """
        # Update config with any kwargs
        self._update_config_from_kwargs(kwargs)
        
        # Create initial result structure
        result = {
            "topic": topic,
            "sections": [],
            "raw_sections": Sections(sections=[]),
            "metadata": {
                "search_api": self.config.search_api.value,
                "research_mode": self.config.research_mode.value,
                "search_depth": self.config.max_search_depth,
                "queries_per_iteration": self.config.number_of_queries,
                "status": "pending",
                "progress": 0.0
            }
        }
        
        # Start research in a separate thread
        import threading
        cancel_event = threading.Event()
        
        def research_thread():
            try:
                if cancel_event.is_set():
                    return
                
                # Get the appropriate research graph based on configuration
                from core.plugins.connectors.research import get_research_graph
                graph = get_research_graph(self.config)
                
                # Initialize the state
                state = ReportState(
                    topic=topic,
                    sections=Sections(sections=[]),
                    queries=[],
                    search_results=[],
                    feedback=None,
                    config=self.config
                )
                
                # Run the research graph
                if cancel_event.is_set():
                    return
                    
                result_state = graph.invoke(state)
                
                # Update the result
                result["raw_sections"] = result_state.sections
                result["sections"] = format_sections(result_state.sections)
                result["metadata"]["status"] = "completed"
                result["metadata"]["progress"] = 1.0
                
                self._status = ResearchStatus.COMPLETED
                self._report_progress("Research completed", 1.0)
                
            except Exception as e:
                result["metadata"]["status"] = "failed"
                result["metadata"]["error"] = str(e)
                
                self._status = ResearchStatus.FAILED
                self._report_progress(f"Research failed: {str(e)}", 1.0)
                self._report_error(e)
        
        thread = threading.Thread(target=research_thread)
        thread.daemon = True
        thread.start()
        
        def cancel():
            cancel_event.set()
            result["metadata"]["status"] = "cancelled"
            self._status = ResearchStatus.FAILED
            self._report_progress("Research cancelled", 1.0)
        
        return result, cancel
