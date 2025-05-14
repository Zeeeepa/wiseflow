"""Parallel Research Manager for WiseFlow.

This module provides a robust manager for handling multiple concurrent research flows,
with resource management, status tracking, and error handling capabilities.
"""

import asyncio
import uuid
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
import traceback

from core.plugins.connectors.research_connector import ResearchConnector
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI

# Configure logging
logger = logging.getLogger(__name__)

class FlowStatus(Enum):
    """Status of a research flow."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FlowInfo:
    """Information about a research flow."""
    id: str
    topic: str
    status: FlowStatus
    config: Optional[Configuration] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    progress: float = 0.0  # Progress from 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ParallelResearchManager:
    """Manager for parallel research flows.
    
    This class manages multiple concurrent research flows, handling resource allocation,
    status tracking, and error recovery.
    
    Attributes:
        max_concurrent_flows (int): Maximum number of concurrent research flows
        active_flows (Dict[str, FlowInfo]): Dictionary of active research flows
        _semaphore (asyncio.Semaphore): Semaphore for limiting concurrent flows
        _lock (asyncio.Lock): Lock for thread-safe operations on shared data
        _running_tasks (Dict[str, asyncio.Task]): Dictionary of running tasks
    """
    
    def __init__(self, max_concurrent_flows: int = 3):
        """Initialize the parallel research manager.
        
        Args:
            max_concurrent_flows (int, optional): Maximum number of concurrent research flows.
                Defaults to 3.
        """
        self.max_concurrent_flows = max_concurrent_flows
        self.active_flows: Dict[str, FlowInfo] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_flows)
        self._lock = asyncio.Lock()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._api_rate_limits: Dict[SearchAPI, asyncio.Semaphore] = {
            SearchAPI.TAVILY: asyncio.Semaphore(2),
            SearchAPI.PERPLEXITY: asyncio.Semaphore(2),
            SearchAPI.EXA: asyncio.Semaphore(2),
            # Add other APIs with appropriate rate limits
        }
        
    async def start_research_flow(self, topic: str, config: Optional[Configuration] = None) -> str:
        """Start a new research flow.
        
        Args:
            topic (str): The topic to research
            config (Optional[Configuration], optional): Configuration for the research.
                Defaults to None.
                
        Returns:
            str: The ID of the new research flow
        """
        flow_id = str(uuid.uuid4())
        
        # Create flow info
        flow_info = FlowInfo(
            id=flow_id,
            topic=topic,
            status=FlowStatus.QUEUED,
            config=config,
            created_at=time.time()
        )
        
        # Add to active flows
        async with self._lock:
            self.active_flows[flow_id] = flow_info
        
        # Create and start the research task
        task = asyncio.create_task(self._run_research_with_semaphore(flow_id, topic, config))
        
        # Store the task
        async with self._lock:
            self._running_tasks[flow_id] = task
        
        # Add callback to handle task completion
        task.add_done_callback(lambda t: asyncio.create_task(self._handle_task_completion(flow_id, t)))
        
        return flow_id
    
    async def _run_research_with_semaphore(self, flow_id: str, topic: str, config: Optional[Configuration] = None) -> None:
        """Run research with semaphore to limit concurrent flows.
        
        Args:
            flow_id (str): The ID of the research flow
            topic (str): The topic to research
            config (Optional[Configuration], optional): Configuration for the research.
                Defaults to None.
        """
        async with self._semaphore:
            await self._run_research(flow_id, topic, config)
    
    async def _run_research(self, flow_id: str, topic: str, config: Optional[Configuration] = None) -> None:
        """Run the research flow.
        
        Args:
            flow_id (str): The ID of the research flow
            topic (str): The topic to research
            config (Optional[Configuration], optional): Configuration for the research.
                Defaults to None.
        """
        # Update flow status to running
        async with self._lock:
            if flow_id not in self.active_flows:
                logger.warning(f"Flow {flow_id} not found in active flows")
                return
            
            flow_info = self.active_flows[flow_id]
            flow_info.status = FlowStatus.RUNNING
            flow_info.started_at = time.time()
        
        try:
            # Create research connector
            connector = ResearchConnector(config)
            
            # Get the search API from config
            search_api = config.search_api if config else Configuration().search_api
            
            # Apply rate limiting for the specific search API
            api_semaphore = self._api_rate_limits.get(search_api)
            if api_semaphore:
                async with api_semaphore:
                    # Perform research
                    results = await self._execute_research(connector, topic)
            else:
                # Perform research without API-specific rate limiting
                results = await self._execute_research(connector, topic)
            
            # Update flow with results
            async with self._lock:
                if flow_id in self.active_flows:
                    flow_info = self.active_flows[flow_id]
                    flow_info.status = FlowStatus.COMPLETED
                    flow_info.completed_at = time.time()
                    flow_info.results = results
                    flow_info.progress = 1.0
        
        except asyncio.CancelledError:
            # Handle cancellation
            async with self._lock:
                if flow_id in self.active_flows:
                    flow_info = self.active_flows[flow_id]
                    flow_info.status = FlowStatus.CANCELLED
                    flow_info.completed_at = time.time()
            
            logger.info(f"Research flow {flow_id} was cancelled")
            raise
        
        except Exception as e:
            # Handle errors
            error_msg = f"Error in research flow {flow_id}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            
            async with self._lock:
                if flow_id in self.active_flows:
                    flow_info = self.active_flows[flow_id]
                    flow_info.status = FlowStatus.FAILED
                    flow_info.completed_at = time.time()
                    flow_info.error = str(e)
    
    async def _execute_research(self, connector: ResearchConnector, topic: str) -> Dict[str, Any]:
        """Execute research using the connector.
        
        This method is separated to allow for easier mocking in tests.
        
        Args:
            connector (ResearchConnector): The research connector
            topic (str): The topic to research
            
        Returns:
            Dict[str, Any]: The research results
        """
        # Convert synchronous research method to async
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, connector.research, topic)
    
    async def _handle_task_completion(self, flow_id: str, task: asyncio.Task) -> None:
        """Handle task completion, including error handling.
        
        Args:
            flow_id (str): The ID of the research flow
            task (asyncio.Task): The completed task
        """
        async with self._lock:
            # Remove task from running tasks
            self._running_tasks.pop(flow_id, None)
            
            # If the task was cancelled, we've already updated the flow status
            if flow_id not in self.active_flows:
                return
            
            flow_info = self.active_flows[flow_id]
            if flow_info.status == FlowStatus.CANCELLED:
                return
            
            # Check for exceptions
            if task.exception():
                if not isinstance(task.exception(), asyncio.CancelledError):
                    flow_info.status = FlowStatus.FAILED
                    flow_info.error = str(task.exception())
                    flow_info.completed_at = time.time()
    
    def get_flow_status(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a research flow.
        
        Args:
            flow_id (str): The ID of the research flow
            
        Returns:
            Optional[Dict[str, Any]]: The flow status information, or None if not found
        """
        if flow_id not in self.active_flows:
            return None
        
        flow_info = self.active_flows[flow_id]
        
        return {
            "id": flow_info.id,
            "topic": flow_info.topic,
            "status": flow_info.status.value,
            "created_at": flow_info.created_at,
            "started_at": flow_info.started_at,
            "completed_at": flow_info.completed_at,
            "progress": flow_info.progress,
            "error": flow_info.error,
            "has_results": flow_info.results is not None,
            "metadata": flow_info.metadata
        }
    
    def get_flow_results(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get the results of a completed research flow.
        
        Args:
            flow_id (str): The ID of the research flow
            
        Returns:
            Optional[Dict[str, Any]]: The research results, or None if not found or not completed
        """
        if flow_id not in self.active_flows:
            return None
        
        flow_info = self.active_flows[flow_id]
        
        if flow_info.status != FlowStatus.COMPLETED:
            return None
        
        return flow_info.results
    
    def get_all_flows(self) -> List[Dict[str, Any]]:
        """Get information about all research flows.
        
        Returns:
            List[Dict[str, Any]]: List of flow status information
        """
        return [self.get_flow_status(flow_id) for flow_id in self.active_flows]
    
    async def cancel_flow(self, flow_id: str) -> bool:
        """Cancel a research flow.
        
        Args:
            flow_id (str): The ID of the research flow
            
        Returns:
            bool: True if the flow was cancelled, False otherwise
        """
        async with self._lock:
            if flow_id not in self.active_flows or flow_id not in self._running_tasks:
                return False
            
            flow_info = self.active_flows[flow_id]
            task = self._running_tasks[flow_id]
            
            # Only cancel if the flow is queued or running
            if flow_info.status in [FlowStatus.QUEUED, FlowStatus.RUNNING]:
                flow_info.status = FlowStatus.CANCELLED
                flow_info.completed_at = time.time()
                task.cancel()
                return True
            
            return False
    
    async def retry_flow(self, flow_id: str) -> Optional[str]:
        """Retry a failed research flow.
        
        Args:
            flow_id (str): The ID of the failed research flow
            
        Returns:
            Optional[str]: The ID of the new research flow, or None if the original flow
                was not found or not in a failed state
        """
        if flow_id not in self.active_flows:
            return None
        
        flow_info = self.active_flows[flow_id]
        
        if flow_info.status != FlowStatus.FAILED:
            return None
        
        # Start a new flow with the same parameters
        return await self.start_research_flow(flow_info.topic, flow_info.config)
    
    async def cleanup_completed_flows(self, max_age_hours: float = 24.0) -> int:
        """Clean up completed, failed, or cancelled flows older than the specified age.
        
        Args:
            max_age_hours (float, optional): Maximum age in hours. Defaults to 24.0.
            
        Returns:
            int: Number of flows cleaned up
        """
        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        flows_to_remove = []
        
        async with self._lock:
            for flow_id, flow_info in self.active_flows.items():
                if flow_info.status in [FlowStatus.COMPLETED, FlowStatus.FAILED, FlowStatus.CANCELLED]:
                    completed_time = flow_info.completed_at or flow_info.created_at
                    if current_time - completed_time > max_age_seconds:
                        flows_to_remove.append(flow_id)
            
            for flow_id in flows_to_remove:
                del self.active_flows[flow_id]
        
        return len(flows_to_remove)
    
    async def update_progress(self, flow_id: str, progress: float) -> bool:
        """Update the progress of a research flow.
        
        Args:
            flow_id (str): The ID of the research flow
            progress (float): The progress value (0.0 to 1.0)
            
        Returns:
            bool: True if the progress was updated, False otherwise
        """
        async with self._lock:
            if flow_id not in self.active_flows:
                return False
            
            flow_info = self.active_flows[flow_id]
            
            if flow_info.status != FlowStatus.RUNNING:
                return False
            
            flow_info.progress = max(0.0, min(1.0, progress))
            return True
    
    async def add_flow_metadata(self, flow_id: str, key: str, value: Any) -> bool:
        """Add metadata to a research flow.
        
        Args:
            flow_id (str): The ID of the research flow
            key (str): The metadata key
            value (Any): The metadata value
            
        Returns:
            bool: True if the metadata was added, False otherwise
        """
        async with self._lock:
            if flow_id not in self.active_flows:
                return False
            
            flow_info = self.active_flows[flow_id]
            flow_info.metadata[key] = value
            return True
    
    async def continuous_research(self, previous_flow_id: str, new_topic: str, config: Optional[Configuration] = None) -> Optional[str]:
        """Continue research based on a previous flow.
        
        Args:
            previous_flow_id (str): The ID of the previous research flow
            new_topic (str): The new topic or follow-up question
            config (Optional[Configuration], optional): Configuration for the research.
                Defaults to None.
                
        Returns:
            Optional[str]: The ID of the new research flow, or None if the previous flow
                was not found or not completed
        """
        # Get the previous flow results
        previous_results = self.get_flow_results(previous_flow_id)
        if not previous_results:
            return None
        
        # Get the previous flow info
        previous_flow_info = self.active_flows.get(previous_flow_id)
        if not previous_flow_info:
            return None
        
        # Use the previous flow's configuration if none provided
        if config is None:
            config = previous_flow_info.config
        
        # Create a new flow ID
        flow_id = str(uuid.uuid4())
        
        # Create flow info
        flow_info = FlowInfo(
            id=flow_id,
            topic=new_topic,
            status=FlowStatus.QUEUED,
            config=config,
            created_at=time.time(),
            metadata={"previous_flow_id": previous_flow_id}
        )
        
        # Add to active flows
        async with self._lock:
            self.active_flows[flow_id] = flow_info
        
        # Create and start the continuous research task
        task = asyncio.create_task(
            self._run_continuous_research_with_semaphore(
                flow_id, previous_results, new_topic, config
            )
        )
        
        # Store the task
        async with self._lock:
            self._running_tasks[flow_id] = task
        
        # Add callback to handle task completion
        task.add_done_callback(lambda t: asyncio.create_task(self._handle_task_completion(flow_id, t)))
        
        return flow_id
    
    async def _run_continuous_research_with_semaphore(
        self, flow_id: str, previous_results: Dict[str, Any], new_topic: str, 
        config: Optional[Configuration] = None
    ) -> None:
        """Run continuous research with semaphore to limit concurrent flows.
        
        Args:
            flow_id (str): The ID of the research flow
            previous_results (Dict[str, Any]): Results from a previous research call
            new_topic (str): The new topic or follow-up question
            config (Optional[Configuration], optional): Configuration for the research.
                Defaults to None.
        """
        async with self._semaphore:
            await self._run_continuous_research(flow_id, previous_results, new_topic, config)
    
    async def _run_continuous_research(
        self, flow_id: str, previous_results: Dict[str, Any], new_topic: str, 
        config: Optional[Configuration] = None
    ) -> None:
        """Run the continuous research flow.
        
        Args:
            flow_id (str): The ID of the research flow
            previous_results (Dict[str, Any]): Results from a previous research call
            new_topic (str): The new topic or follow-up question
            config (Optional[Configuration], optional): Configuration for the research.
                Defaults to None.
        """
        # Update flow status to running
        async with self._lock:
            if flow_id not in self.active_flows:
                logger.warning(f"Flow {flow_id} not found in active flows")
                return
            
            flow_info = self.active_flows[flow_id]
            flow_info.status = FlowStatus.RUNNING
            flow_info.started_at = time.time()
        
        try:
            # Create research connector
            connector = ResearchConnector(config)
            
            # Get the search API from config
            search_api = config.search_api if config else Configuration().search_api
            
            # Apply rate limiting for the specific search API
            api_semaphore = self._api_rate_limits.get(search_api)
            
            # Execute continuous research
            if api_semaphore:
                async with api_semaphore:
                    # Perform continuous research
                    results = await self._execute_continuous_research(connector, previous_results, new_topic)
            else:
                # Perform continuous research without API-specific rate limiting
                results = await self._execute_continuous_research(connector, previous_results, new_topic)
            
            # Update flow with results
            async with self._lock:
                if flow_id in self.active_flows:
                    flow_info = self.active_flows[flow_id]
                    flow_info.status = FlowStatus.COMPLETED
                    flow_info.completed_at = time.time()
                    flow_info.results = results
                    flow_info.progress = 1.0
        
        except asyncio.CancelledError:
            # Handle cancellation
            async with self._lock:
                if flow_id in self.active_flows:
                    flow_info = self.active_flows[flow_id]
                    flow_info.status = FlowStatus.CANCELLED
                    flow_info.completed_at = time.time()
            
            logger.info(f"Research flow {flow_id} was cancelled")
            raise
        
        except Exception as e:
            # Handle errors
            error_msg = f"Error in continuous research flow {flow_id}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            
            async with self._lock:
                if flow_id in self.active_flows:
                    flow_info = self.active_flows[flow_id]
                    flow_info.status = FlowStatus.FAILED
                    flow_info.completed_at = time.time()
                    flow_info.error = str(e)
    
    async def _execute_continuous_research(
        self, connector: ResearchConnector, previous_results: Dict[str, Any], new_topic: str
    ) -> Dict[str, Any]:
        """Execute continuous research using the connector.
        
        Args:
            connector (ResearchConnector): The research connector
            previous_results (Dict[str, Any]): Results from a previous research call
            new_topic (str): The new topic or follow-up question
            
        Returns:
            Dict[str, Any]: The research results
        """
        # Convert synchronous continuous_research method to async
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, connector.continuous_research, previous_results, new_topic)

