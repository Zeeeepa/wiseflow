#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parallel Research Manager.

This module provides functionality for managing multiple concurrent research flows.
"""

import asyncio
import logging
import uuid
import time
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from threading import Lock

from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI
from core.plugins.connectors.research.state import ReportState, Sections
from core.plugins.connectors.research import get_research_graph

logger = logging.getLogger(__name__)

class ResearchFlowStatus(str, Enum):
    """Status of a research flow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ResearchFlow:
    """A research flow with its state and metadata."""
    
    def __init__(
        self, 
        flow_id: str, 
        topic: str, 
        config: Configuration,
        previous_results: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize a research flow.
        
        Args:
            flow_id: Unique identifier for the flow
            topic: Research topic
            config: Research configuration
            previous_results: Optional results from a previous research flow
            metadata: Optional metadata
        """
        self.flow_id = flow_id
        self.topic = topic
        self.config = config
        self.previous_results = previous_results
        self.metadata = metadata or {}
        self.status = ResearchFlowStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.progress: float = 0.0
        self.task: Optional[asyncio.Task] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the research flow to a dictionary.
        
        Returns:
            Dictionary representation of the research flow
        """
        return {
            "flow_id": self.flow_id,
            "topic": self.topic,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "error": self.error,
            "metadata": self.metadata,
            "config": {
                "search_api": self.config.search_api.value,
                "research_mode": self.config.research_mode.value,
                "max_search_depth": self.config.max_search_depth,
                "number_of_queries": self.config.number_of_queries
            }
        }

class ParallelResearchManager:
    """Manager for parallel research flows.
    
    This class provides functionality for managing multiple concurrent research flows,
    including creating, retrieving, listing, and cancelling flows.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = ParallelResearchManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the parallel research manager."""
        self.flows: Dict[str, ResearchFlow] = {}
        self.lock = Lock()
        self.max_concurrent_flows = 10  # Default value, can be configured
    
    def set_max_concurrent_flows(self, max_flows: int) -> None:
        """Set the maximum number of concurrent flows.
        
        Args:
            max_flows: Maximum number of concurrent flows
        """
        with self.lock:
            self.max_concurrent_flows = max_flows
    
    def create_flow(
        self, 
        topic: str, 
        config: Optional[Configuration] = None,
        previous_results: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new research flow.
        
        Args:
            topic: Research topic
            config: Optional research configuration
            previous_results: Optional results from a previous research flow
            metadata: Optional metadata
            
        Returns:
            Flow ID
            
        Raises:
            ValueError: If the maximum number of concurrent flows is reached
        """
        with self.lock:
            # Check if maximum number of concurrent flows is reached
            active_flows = sum(1 for flow in self.flows.values() 
                              if flow.status in [ResearchFlowStatus.PENDING, ResearchFlowStatus.RUNNING])
            
            if active_flows >= self.max_concurrent_flows:
                raise ValueError(f"Maximum number of concurrent flows reached ({self.max_concurrent_flows})")
            
            # Create a new flow ID
            flow_id = str(uuid.uuid4())
            
            # Create a new flow
            flow = ResearchFlow(
                flow_id=flow_id,
                topic=topic,
                config=config or Configuration(),
                previous_results=previous_results,
                metadata=metadata
            )
            
            # Add the flow to the dictionary
            self.flows[flow_id] = flow
            
            # Return the flow ID
            return flow_id
    
    def get_flow(self, flow_id: str) -> Optional[ResearchFlow]:
        """Get a research flow by ID.
        
        Args:
            flow_id: Flow ID
            
        Returns:
            Research flow or None if not found
        """
        with self.lock:
            return self.flows.get(flow_id)
    
    def list_flows(
        self, 
        status: Optional[Union[ResearchFlowStatus, List[ResearchFlowStatus]]] = None
    ) -> List[Dict[str, Any]]:
        """List all research flows, optionally filtered by status.
        
        Args:
            status: Optional status or list of statuses to filter by
            
        Returns:
            List of research flows as dictionaries
        """
        with self.lock:
            flows = list(self.flows.values())
            
            # Filter by status if provided
            if status:
                if isinstance(status, list):
                    flows = [flow for flow in flows if flow.status in status]
                else:
                    flows = [flow for flow in flows if flow.status == status]
            
            # Convert to dictionaries
            return [flow.to_dict() for flow in flows]
    
    def cancel_flow(self, flow_id: str) -> bool:
        """Cancel a research flow.
        
        Args:
            flow_id: Flow ID
            
        Returns:
            True if the flow was cancelled, False otherwise
        """
        with self.lock:
            flow = self.flows.get(flow_id)
            
            if not flow:
                return False
            
            # Only cancel if the flow is pending or running
            if flow.status not in [ResearchFlowStatus.PENDING, ResearchFlowStatus.RUNNING]:
                return False
            
            # Cancel the task if it exists
            if flow.task and not flow.task.done():
                flow.task.cancel()
            
            # Update the flow status
            flow.status = ResearchFlowStatus.CANCELLED
            flow.completed_at = datetime.now()
            
            return True
    
    def cleanup_completed_flows(self, max_age_hours: int = 24) -> int:
        """Clean up completed, failed, or cancelled flows older than the specified age.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of flows cleaned up
        """
        with self.lock:
            now = datetime.now()
            flows_to_remove = []
            
            for flow_id, flow in self.flows.items():
                if flow.status in [ResearchFlowStatus.COMPLETED, ResearchFlowStatus.FAILED, ResearchFlowStatus.CANCELLED]:
                    completed_at = flow.completed_at or flow.created_at
                    age_hours = (now - completed_at).total_seconds() / 3600
                    
                    if age_hours > max_age_hours:
                        flows_to_remove.append(flow_id)
            
            # Remove the flows
            for flow_id in flows_to_remove:
                del self.flows[flow_id]
            
            return len(flows_to_remove)
    
    async def start_flow(self, flow_id: str) -> bool:
        """Start a research flow.
        
        Args:
            flow_id: Flow ID
            
        Returns:
            True if the flow was started, False otherwise
        """
        with self.lock:
            flow = self.flows.get(flow_id)
            
            if not flow:
                return False
            
            # Only start if the flow is pending
            if flow.status != ResearchFlowStatus.PENDING:
                return False
            
            # Update the flow status
            flow.status = ResearchFlowStatus.RUNNING
            flow.started_at = datetime.now()
        
        # Create a task for the flow
        flow.task = asyncio.create_task(self._execute_flow(flow))
        
        return True
    
    async def start_all_pending_flows(self) -> int:
        """Start all pending flows.
        
        Returns:
            Number of flows started
        """
        with self.lock:
            pending_flows = [flow_id for flow_id, flow in self.flows.items() 
                           if flow.status == ResearchFlowStatus.PENDING]
        
        # Start each flow
        count = 0
        for flow_id in pending_flows:
            if await self.start_flow(flow_id):
                count += 1
        
        return count
    
    async def _execute_flow(self, flow: ResearchFlow) -> None:
        """Execute a research flow.
        
        Args:
            flow: Research flow
        """
        try:
            # Get the research graph
            graph = get_research_graph(flow.config)
            
            # Initialize the state
            state = ReportState(
                topic=flow.topic,
                sections=Sections(sections=[]),
                queries=[],
                search_results=[],
                feedback=None,
                config=flow.config,
                previous_topic=flow.previous_results.get("topic") if flow.previous_results else None
            )
            
            # Set up progress tracking
            def progress_callback(state, event_type, data):
                if event_type == "node_start":
                    node_name = data["node_name"]
                    if node_name == "generate_report_plan":
                        flow.progress = 0.2
                    elif node_name == "write_sections":
                        flow.progress = 0.5
                elif event_type == "node_end":
                    node_name = data["node_name"]
                    if node_name == "generate_report_plan":
                        flow.progress = 0.4
                    elif node_name == "write_sections":
                        flow.progress = 0.9
            
            # Run the research graph with progress tracking
            config = {"callbacks": [progress_callback]}
            result = await graph.ainvoke(state, config=config)
            
            # Format the results
            from core.plugins.connectors.research.utils import format_sections
            formatted_sections = format_sections(result.sections)
            
            # Update the flow with the result
            with self.lock:
                flow.result = {
                    "topic": flow.topic,
                    "sections": formatted_sections,
                    "raw_sections": result.sections,
                    "metadata": {
                        "search_api": flow.config.search_api.value,
                        "research_mode": flow.config.research_mode.value,
                        "search_depth": flow.config.max_search_depth,
                        "queries_per_iteration": flow.config.number_of_queries
                    }
                }
                flow.status = ResearchFlowStatus.COMPLETED
                flow.completed_at = datetime.now()
                flow.progress = 1.0
            
        except asyncio.CancelledError:
            # Flow was cancelled
            with self.lock:
                flow.status = ResearchFlowStatus.CANCELLED
                flow.completed_at = datetime.now()
                flow.error = "Flow was cancelled"
            
        except Exception as e:
            # Flow failed
            logger.exception(f"Error executing flow {flow.flow_id}: {e}")
            
            with self.lock:
                flow.status = ResearchFlowStatus.FAILED
                flow.completed_at = datetime.now()
                flow.error = str(e)

