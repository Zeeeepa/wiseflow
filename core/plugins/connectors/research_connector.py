"""Research connector for wiseflow.

This connector provides deep research capabilities using various search APIs and research modes.
It's based on the open_deep_research library but implemented directly in wiseflow.
"""

from typing import Dict, Any, Optional, List
from enum import Enum

from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.utils import format_sections
from core.plugins.connectors.research.state import ReportState, Sections
from core.plugins.connectors.research.parallel_manager import ParallelManager, TaskPriority, parallel_map
from core.utils.error_handling import (
    WiseflowError, PluginError, DataProcessingError, ConnectionError, 
    TimeoutError, ValidationError
)
from core.utils.error_manager import (
    with_error_handling, retry, ErrorSeverity, RecoveryStrategy, error_manager
)
from core.utils.logging_config import logger, with_context

class ResearchError(PluginError):
    """Error raised during research operations."""
    pass

class QueryGenerationError(ResearchError):
    """Error raised when query generation fails."""
    pass

class SearchError(ResearchError):
    """Error raised when search fails."""
    pass

class ContentProcessingError(ResearchError):
    """Error raised when content processing fails."""
    pass

class ReportGenerationError(ResearchError):
    """Error raised when report generation fails."""
    pass

class ResearchConnector:
    """Research connector for wiseflow.
    
    This connector provides deep research capabilities using various search APIs and research modes.
    It supports:
    - Multiple research modes (linear, graph-based, multi-agent)
    - Configurable search APIs (Tavily, Perplexity, Exa, etc.)
    - Continuous topic research (building on previous queries)
    - Customizable parameters for search depth and query generation
    """
    
    def __init__(self, config: Optional[Configuration] = None):
        """Initialize the research connector.
        
        Args:
            config (Configuration, optional): Configuration for the research. Defaults to None.
        """
        self.config = config or Configuration()
        self.parallel_manager = ParallelManager(max_workers=self.config.max_parallel_tasks)
        
    @with_error_handling(
        error_types=[Exception],
        severity=ErrorSeverity.HIGH,
        recovery_strategy=RecoveryStrategy.RETRY,
        notify=True,
        log_level="error",
        max_recovery_attempts=2
    )
    async def research(self, topic: str, **kwargs) -> Dict[str, Any]:
        """Perform research on a topic.
        
        Args:
            topic (str): The topic to research
            **kwargs: Additional arguments to override configuration
            
        Returns:
            Dict[str, Any]: The research results including report sections and metadata
            
        Raises:
            ResearchError: If research fails
            ValidationError: If input validation fails
            ConnectionError: If connection to search APIs fails
            TimeoutError: If research times out
        """
        # Update config with any kwargs
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Validate input
        if not topic or not isinstance(topic, str):
            raise ValidationError(
                "Invalid topic",
                {"topic": topic}
            )
        
        # Get the appropriate research graph based on configuration
        from core.plugins.connectors.research import get_research_graph
        graph = get_research_graph(self.config)
        
        try:
            # Initialize research state
            state = ReportState(topic=topic)
            
            # Execute the research graph
            if self.config.research_mode == ResearchMode.PARALLEL:
                # Use parallel execution
                result = await self._execute_parallel_research(topic, state)
            else:
                # Use sequential execution
                result = await graph.execute(state)
            
            # Format the results
            formatted_result = self._format_research_results(result)
            
            return formatted_result
            
        except Exception as e:
            # Transform generic exceptions into specific research errors
            if "query generation" in str(e).lower():
                raise QueryGenerationError(
                    f"Failed to generate queries for topic: {topic}",
                    {"topic": topic, "config": self.config.to_dict()},
                    e
                )
            elif "search" in str(e).lower():
                raise SearchError(
                    f"Failed to search for topic: {topic}",
                    {"topic": topic, "config": self.config.to_dict()},
                    e
                )
            elif "content processing" in str(e).lower() or "parsing" in str(e).lower():
                raise ContentProcessingError(
                    f"Failed to process content for topic: {topic}",
                    {"topic": topic, "config": self.config.to_dict()},
                    e
                )
            elif "report generation" in str(e).lower() or "summary" in str(e).lower():
                raise ReportGenerationError(
                    f"Failed to generate report for topic: {topic}",
                    {"topic": topic, "config": self.config.to_dict()},
                    e
                )
            else:
                raise ResearchError(
                    f"Research failed for topic: {topic}",
                    {"topic": topic, "config": self.config.to_dict()},
                    e
                )
    
    async def _execute_parallel_research(self, topic: str, state: ReportState) -> Dict[str, Any]:
        """Execute research in parallel.
        
        Args:
            topic (str): The topic to research
            state (ReportState): The initial research state
            
        Returns:
            Dict[str, Any]: The research results
            
        Raises:
            ResearchError: If parallel research fails
        """
        try:
            # Reset the parallel manager
            self.parallel_manager.reset()
            
            # Generate queries
            queries = await self._generate_queries(topic)
            
            # Add search tasks
            for i, query in enumerate(queries):
                self.parallel_manager.add_task(
                    task_id=f"search_{i}",
                    func=self._execute_search,
                    args=(query, state),
                    priority=TaskPriority.HIGH,
                    max_retries=2
                )
            
            # Add content processing task (depends on all search tasks)
            self.parallel_manager.add_task(
                task_id="process_content",
                func=self._process_content,
                args=(state,),
                dependencies=[f"search_{i}" for i in range(len(queries))],
                priority=TaskPriority.NORMAL,
                max_retries=2
            )
            
            # Add report generation task (depends on content processing)
            self.parallel_manager.add_task(
                task_id="generate_report",
                func=self._generate_report,
                args=(state,),
                dependencies=["process_content"],
                priority=TaskPriority.LOW,
                max_retries=1
            )
            
            # Execute all tasks
            await self.parallel_manager.execute_all(
                timeout=self.config.timeout,
                raise_on_failure=True
            )
            
            # Get the report result
            report_result = self.parallel_manager.get_task_result("generate_report")
            
            if not report_result:
                # Check for errors
                errors = self.parallel_manager.get_all_errors()
                if errors:
                    error_details = {task_id: str(error) for task_id, error in errors.items()}
                    raise ResearchError(
                        f"Parallel research failed for topic: {topic}",
                        {"topic": topic, "errors": error_details}
                    )
                else:
                    raise ResearchError(
                        f"No report generated for topic: {topic}",
                        {"topic": topic}
                    )
            
            return report_result
            
        except Exception as e:
            # Log the error with context
            logger.error(
                f"Parallel research failed: {e}",
                extra={"topic": topic, "error": str(e)}
            )
            
            # Rethrow as ResearchError
            if not isinstance(e, WiseflowError):
                raise ResearchError(
                    f"Parallel research failed for topic: {topic}",
                    {"topic": topic},
                    e
                )
            raise
    
    @retry(
        max_retries=3,
        retry_delay=1.0,
        backoff_factor=2.0,
        retryable_errors=[ConnectionError, TimeoutError]
    )
    async def _generate_queries(self, topic: str) -> List[str]:
        """Generate search queries for a topic.
        
        Args:
            topic (str): The topic to generate queries for
            
        Returns:
            List[str]: List of generated queries
            
        Raises:
            QueryGenerationError: If query generation fails
        """
        try:
            # Import query generator
            from core.plugins.connectors.research.query_generator import generate_queries
            
            # Generate queries
            queries = await generate_queries(
                topic, 
                num_queries=self.config.num_queries,
                model=self.config.query_model
            )
            
            return queries
            
        except Exception as e:
            raise QueryGenerationError(
                f"Failed to generate queries for topic: {topic}",
                {"topic": topic},
                e
            )
    
    @retry(
        max_retries=2,
        retry_delay=1.0,
        backoff_factor=2.0,
        retryable_errors=[ConnectionError, TimeoutError]
    )
    async def _execute_search(self, query: str, state: ReportState) -> Dict[str, Any]:
        """Execute a search query.
        
        Args:
            query (str): The query to search for
            state (ReportState): The research state
            
        Returns:
            Dict[str, Any]: The search results
            
        Raises:
            SearchError: If search fails
        """
        try:
            # Import search executor
            from core.plugins.connectors.research.search_executor import execute_search
            
            # Execute search
            search_results = await execute_search(
                query,
                api=self.config.search_api,
                max_results=self.config.max_results_per_query
            )
            
            # Update state with search results
            state.add_search_results(query, search_results)
            
            return search_results
            
        except Exception as e:
            raise SearchError(
                f"Failed to execute search for query: {query}",
                {"query": query},
                e
            )
    
    async def _process_content(self, state: ReportState) -> Dict[str, Any]:
        """Process search results content.
        
        Args:
            state (ReportState): The research state with search results
            
        Returns:
            Dict[str, Any]: The processed content
            
        Raises:
            ContentProcessingError: If content processing fails
        """
        try:
            # Import content processor
            from core.plugins.connectors.research.content_processor import process_content
            
            # Process content
            processed_content = await process_content(
                state.search_results,
                model=self.config.processing_model
            )
            
            # Update state with processed content
            state.set_processed_content(processed_content)
            
            return processed_content
            
        except Exception as e:
            raise ContentProcessingError(
                "Failed to process content",
                {"num_results": len(state.search_results)},
                e
            )
    
    async def _generate_report(self, state: ReportState) -> Dict[str, Any]:
        """Generate a report from processed content.
        
        Args:
            state (ReportState): The research state with processed content
            
        Returns:
            Dict[str, Any]: The generated report
            
        Raises:
            ReportGenerationError: If report generation fails
        """
        try:
            # Import report generator
            from core.plugins.connectors.research.report_generator import generate_report
            
            # Generate report
            report = await generate_report(
                state.topic,
                state.processed_content,
                model=self.config.report_model,
                format=self.config.report_format
            )
            
            # Update state with report
            state.set_report(report)
            
            return report
            
        except Exception as e:
            raise ReportGenerationError(
                f"Failed to generate report for topic: {state.topic}",
                {"topic": state.topic},
                e
            )
    
    def _format_research_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format the research results.
        
        Args:
            result (Dict[str, Any]): The raw research results
            
        Returns:
            Dict[str, Any]: The formatted research results
        """
        # Extract sections from the result
        sections = result.get("sections", {})
        
        # Format sections
        formatted_sections = format_sections(sections)
        
        # Create the formatted result
        formatted_result = {
            "topic": result.get("topic", ""),
            "summary": result.get("summary", ""),
            "sections": formatted_sections,
            "sources": result.get("sources", []),
            "metadata": {
                "query_count": len(result.get("queries", [])),
                "source_count": len(result.get("sources", [])),
                "section_count": len(formatted_sections),
                "config": self.config.to_dict()
            }
        }
        
        return formatted_result
