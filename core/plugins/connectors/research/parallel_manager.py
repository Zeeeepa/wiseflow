"""
Parallel research manager for WiseFlow.

This module provides a manager for executing parallel research tasks.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Set
from datetime import datetime

from core.task_management import (
    Task,
    TaskPriority,
    TaskStatus,
    TaskManager,
    TaskError
)
from core.plugins.connectors.research.configuration import Configuration
from core.plugins.connectors.research.state import ReportState
from core.plugins.connectors.research.graph_workflow import graph as research_graph
from core.plugins.connectors.research.multi_agent import graph as multi_agent_graph
from core.event_system import EventType, Event, publish_sync, create_task_event

logger = logging.getLogger(__name__)

class ParallelResearchManager:
    """
    Manager for parallel research tasks.
    
    This class provides functionality to execute multiple research tasks in parallel.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(ParallelResearchManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, max_concurrent_research: int = 3):
        """
        Initialize the parallel research manager.
        
        Args:
            max_concurrent_research: Maximum number of concurrent research tasks
        """
        if self._initialized:
            return
            
        self.max_concurrent_research = max_concurrent_research
        self.task_manager = TaskManager()
        self.active_research: Dict[str, Dict[str, Any]] = {}
        self.research_semaphore = asyncio.Semaphore(max_concurrent_research)
        
        self._initialized = True
        
        logger.info(f"Parallel research manager initialized with {max_concurrent_research} max concurrent research tasks")
    
    async def create_research_task(
        self,
        topic: str,
        config: Optional[Configuration] = None,
        use_multi_agent: bool = False,
        priority: TaskPriority = TaskPriority.NORMAL,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new research task.
        
        Args:
            topic: Research topic
            config: Research configuration
            use_multi_agent: Whether to use the multi-agent approach
            priority: Priority of the task
            tags: List of tags for categorizing the task
            metadata: Additional metadata for the task
            
        Returns:
            Task ID
        """
        # Create a unique ID for the research
        research_id = f"research_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.active_research)}"
        
        # Create initial state
        state = ReportState(
            topic=topic,
            config=config or Configuration(),
            sections=None,
            queries=None,
            search_results=None
        )
        
        # Register the research task
        task_id = self.task_manager.register_task(
            name=f"Research: {topic}",
            func=self._execute_research,
            research_id=research_id,
            state=state,
            use_multi_agent=use_multi_agent,
            priority=priority,
            tags=tags or ["research"],
            metadata=metadata or {},
            description=f"Research task for topic: {topic}"
        )
        
        # Store research information
        self.active_research[research_id] = {
            "task_id": task_id,
            "topic": topic,
            "state": state,
            "use_multi_agent": use_multi_agent,
            "created_at": datetime.now(),
            "status": "pending"
        }
        
        # Publish event
        try:
            event = create_task_event(
                EventType.RESEARCH_CREATED,
                task_id,
                {
                    "research_id": research_id,
                    "topic": topic,
                    "use_multi_agent": use_multi_agent
                }
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish research created event: {e}")
        
        logger.info(f"Research task created: {task_id} ({topic})")
        return task_id
    
    async def _execute_research(
        self,
        research_id: str,
        state: ReportState,
        use_multi_agent: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a research task.
        
        Args:
            research_id: Research ID
            state: Initial state
            use_multi_agent: Whether to use the multi-agent approach
            
        Returns:
            Research results
        """
        async with self.research_semaphore:
            try:
                # Update research status
                self.active_research[research_id]["status"] = "running"
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.RESEARCH_STARTED,
                        self.active_research[research_id]["task_id"],
                        {
                            "research_id": research_id,
                            "topic": state.topic,
                            "use_multi_agent": use_multi_agent
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish research started event: {e}")
                
                logger.info(f"Research task started: {research_id} ({state.topic})")
                
                # Select the appropriate graph
                graph = multi_agent_graph if use_multi_agent else research_graph
                
                # Execute the research
                result = await graph.ainvoke(state)
                
                # Update research status
                self.active_research[research_id]["status"] = "completed"
                self.active_research[research_id]["result"] = result
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.RESEARCH_COMPLETED,
                        self.active_research[research_id]["task_id"],
                        {
                            "research_id": research_id,
                            "topic": state.topic,
                            "use_multi_agent": use_multi_agent
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish research completed event: {e}")
                
                logger.info(f"Research task completed: {research_id} ({state.topic})")
                return result
            except Exception as e:
                # Update research status
                self.active_research[research_id]["status"] = "failed"
                self.active_research[research_id]["error"] = str(e)
                
                # Publish event
                try:
                    event = create_task_event(
                        EventType.RESEARCH_FAILED,
                        self.active_research[research_id]["task_id"],
                        {
                            "research_id": research_id,
                            "topic": state.topic,
                            "use_multi_agent": use_multi_agent,
                            "error": str(e)
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish research failed event: {e}")
                
                logger.error(f"Research task failed: {research_id} ({state.topic}): {e}")
                raise TaskError(f"Research task failed: {str(e)}")
    
    async def cancel_research(self, research_id: str) -> bool:
        """
        Cancel a research task.
        
        Args:
            research_id: Research ID
            
        Returns:
            True if the research was cancelled, False otherwise
        """
        if research_id not in self.active_research:
            logger.warning(f"Research {research_id} not found for cancellation")
            return False
        
        task_id = self.active_research[research_id]["task_id"]
        cancelled = await self.task_manager.cancel_task(task_id)
        
        if cancelled:
            # Update research status
            self.active_research[research_id]["status"] = "cancelled"
            
            # Publish event
            try:
                event = create_task_event(
                    EventType.RESEARCH_CANCELLED,
                    task_id,
                    {
                        "research_id": research_id,
                        "topic": self.active_research[research_id]["topic"],
                        "reason": "cancelled by user"
                    }
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish research cancelled event: {e}")
            
            logger.info(f"Research task cancelled: {research_id} ({self.active_research[research_id]['topic']})")
        
        return cancelled
    
    def get_research_status(self, research_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a research task.
        
        Args:
            research_id: Research ID
            
        Returns:
            Research status or None if not found
        """
        if research_id not in self.active_research:
            return None
        
        research = self.active_research[research_id]
        task = self.task_manager.get_task(research["task_id"])
        
        if not task:
            return None
        
        # Get task progress
        progress, progress_message = self.task_manager.get_task_progress(research["task_id"])
        
        return {
            "research_id": research_id,
            "task_id": research["task_id"],
            "topic": research["topic"],
            "status": research["status"],
            "use_multi_agent": research["use_multi_agent"],
            "created_at": research["created_at"].isoformat(),
            "progress": progress,
            "progress_message": progress_message,
            "error": research.get("error")
        }
    
    def get_all_research(self) -> List[Dict[str, Any]]:
        """
        Get all research tasks.
        
        Returns:
            List of research status dictionaries
        """
        return [
            self.get_research_status(research_id) or {"research_id": research_id, "status": "unknown"}
            for research_id in self.active_research
        ]
    
    def get_active_research(self) -> List[Dict[str, Any]]:
        """
        Get all active research tasks.
        
        Returns:
            List of active research status dictionaries
        """
        return [
            self.get_research_status(research_id)
            for research_id in self.active_research
            if self.active_research[research_id]["status"] in ["pending", "running"]
        ]
    
    def get_research_result(self, research_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the result of a research task.
        
        Args:
            research_id: Research ID
            
        Returns:
            Research result or None if not found or not completed
        """
        if research_id not in self.active_research:
            return None
        
        research = self.active_research[research_id]
        
        if research["status"] != "completed":
            return None
        
        return research.get("result")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get parallel research manager metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "max_concurrent_research": self.max_concurrent_research,
            "active_slots": self.research_semaphore._value,
            "total_research": len(self.active_research),
            "pending_research": len([r for r in self.active_research.values() if r["status"] == "pending"]),
            "running_research": len([r for r in self.active_research.values() if r["status"] == "running"]),
            "completed_research": len([r for r in self.active_research.values() if r["status"] == "completed"]),
            "failed_research": len([r for r in self.active_research.values() if r["status"] == "failed"]),
            "cancelled_research": len([r for r in self.active_research.values() if r["status"] == "cancelled"])
        }

# Create a singleton instance
parallel_research_manager = ParallelResearchManager()

