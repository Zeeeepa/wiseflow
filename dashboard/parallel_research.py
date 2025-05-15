"""
Parallel Research Flow models and API for the dashboard.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import json
import os
from datetime import datetime
import uuid
from enum import Enum
from pydantic import BaseModel, Field

from core.utils.pb_api import PbTalker

logger = logging.getLogger(__name__)

class ResearchFlowStatus(str, Enum):
    """Status of a research flow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class ResearchTaskStatus(str, Enum):
    """Status of a research task within a flow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class ResearchTask(BaseModel):
    """A task within a research flow."""
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    name: str
    description: Optional[str] = None
    status: ResearchTaskStatus = ResearchTaskStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    source: str  # Source type (e.g., "web", "github", "arxiv")
    source_config: Dict[str, Any]  # Configuration for the source
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ResearchFlow(BaseModel):
    """A parallel research flow."""
    flow_id: str = Field(default_factory=lambda: f"flow_{uuid.uuid4().hex[:8]}")
    name: str
    description: Optional[str] = None
    status: ResearchFlowStatus = ResearchFlowStatus.PENDING
    tasks: List[ResearchTask] = []
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def add_task(self, task: ResearchTask) -> None:
        """Add a task to the flow."""
        self.tasks.append(task)
        self.updated_at = datetime.now()
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the flow."""
        for i, task in enumerate(self.tasks):
            if task.task_id == task_id:
                self.tasks.pop(i)
                self.updated_at = datetime.now()
                return True
        return False
    
    def update_task_status(self, task_id: str, status: ResearchTaskStatus, 
                          progress: Optional[float] = None, 
                          results: Optional[Dict[str, Any]] = None,
                          error_message: Optional[str] = None) -> bool:
        """Update the status of a task."""
        for task in self.tasks:
            if task.task_id == task_id:
                task.status = status
                
                if progress is not None:
                    task.progress = progress
                
                if results is not None:
                    task.results = results
                
                if error_message is not None:
                    task.error_message = error_message
                
                task.updated_at = datetime.now()
                
                if status == ResearchTaskStatus.RUNNING and task.started_at is None:
                    task.started_at = datetime.now()
                
                if status in [ResearchTaskStatus.COMPLETED, ResearchTaskStatus.FAILED, ResearchTaskStatus.CANCELLED]:
                    task.completed_at = datetime.now()
                
                # Update flow status based on tasks
                self._update_flow_status()
                
                return True
        
        return False
    
    def _update_flow_status(self) -> None:
        """Update the flow status based on task statuses."""
        if not self.tasks:
            self.status = ResearchFlowStatus.PENDING
            return
        
        # Check if all tasks are completed
        if all(task.status == ResearchTaskStatus.COMPLETED for task in self.tasks):
            self.status = ResearchFlowStatus.COMPLETED
            self.completed_at = datetime.now()
            return
        
        # Check if any task is running
        if any(task.status == ResearchTaskStatus.RUNNING for task in self.tasks):
            self.status = ResearchFlowStatus.RUNNING
            if self.started_at is None:
                self.started_at = datetime.now()
            return
        
        # Check if any task has failed
        if any(task.status == ResearchTaskStatus.FAILED for task in self.tasks):
            # If some tasks are still running, keep the flow as running
            if any(task.status == ResearchTaskStatus.RUNNING for task in self.tasks):
                self.status = ResearchFlowStatus.RUNNING
            else:
                self.status = ResearchFlowStatus.FAILED
            return
        
        # Check if all tasks are paused
        if all(task.status in [ResearchTaskStatus.PAUSED, ResearchTaskStatus.COMPLETED] for task in self.tasks) and \
           any(task.status == ResearchTaskStatus.PAUSED for task in self.tasks):
            self.status = ResearchFlowStatus.PAUSED
            return
        
        # Check if all tasks are cancelled
        if all(task.status in [ResearchTaskStatus.CANCELLED, ResearchTaskStatus.COMPLETED] for task in self.tasks) and \
           any(task.status == ResearchTaskStatus.CANCELLED for task in self.tasks):
            self.status = ResearchFlowStatus.CANCELLED
            return
        
        # Default to pending if some tasks are still pending
        self.status = ResearchFlowStatus.PENDING
    
    def get_progress(self) -> float:
        """Get the overall progress of the flow."""
        if not self.tasks:
            return 0.0
        
        total_progress = sum(task.progress for task in self.tasks)
        return total_progress / len(self.tasks)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the flow to a dictionary."""
        return {
            "flow_id": self.flow_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "tasks": [task.dict() for task in self.tasks],
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.get_progress()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchFlow':
        """Create a flow from a dictionary."""
        tasks = []
        for task_data in data.get("tasks", []):
            task = ResearchTask(
                task_id=task_data.get("task_id"),
                name=task_data.get("name"),
                description=task_data.get("description"),
                status=ResearchTaskStatus(task_data.get("status", "pending")),
                progress=task_data.get("progress", 0.0),
                source=task_data.get("source"),
                source_config=task_data.get("source_config", {}),
                results=task_data.get("results"),
                error_message=task_data.get("error_message"),
                created_at=datetime.fromisoformat(task_data.get("created_at")) if task_data.get("created_at") else datetime.now(),
                updated_at=datetime.fromisoformat(task_data.get("updated_at")) if task_data.get("updated_at") else datetime.now(),
                started_at=datetime.fromisoformat(task_data.get("started_at")) if task_data.get("started_at") else None,
                completed_at=datetime.fromisoformat(task_data.get("completed_at")) if task_data.get("completed_at") else None
            )
            tasks.append(task)
        
        flow = cls(
            flow_id=data.get("flow_id"),
            name=data.get("name"),
            description=data.get("description"),
            status=ResearchFlowStatus(data.get("status", "pending")),
            tasks=tasks,
            user_id=data.get("user_id"),
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data.get("updated_at")) if data.get("updated_at") else datetime.now(),
            started_at=datetime.fromisoformat(data.get("started_at")) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data.get("completed_at")) if data.get("completed_at") else None
        )
        
        return flow


class ResearchFlowManager:
    """Manager for research flows."""
    
    def __init__(self, pb: PbTalker):
        """Initialize the research flow manager."""
        self.pb = pb
    
    def create_flow(self, name: str, description: Optional[str] = None, user_id: Optional[str] = None) -> ResearchFlow:
        """Create a new research flow."""
        flow = ResearchFlow(
            name=name,
            description=description,
            user_id=user_id
        )
        
        # Save to database
        flow_data = flow.to_dict()
        flow_id = self.pb.add("research_flows", flow_data)
        
        if not flow_id:
            logger.error(f"Failed to save research flow: {name}")
        
        return flow
    
    def get_flow(self, flow_id: str) -> Optional[ResearchFlow]:
        """Get a research flow by ID."""
        flows = self.pb.read("research_flows", filter=f'flow_id="{flow_id}"')
        
        if flows:
            return ResearchFlow.from_dict(flows[0])
        
        return None
    
    def get_all_flows(self, user_id: Optional[str] = None, status: Optional[ResearchFlowStatus] = None) -> List[ResearchFlow]:
        """Get all research flows for a user."""
        filter_parts = []
        
        if user_id:
            filter_parts.append(f'user_id="{user_id}"')
        
        if status:
            filter_parts.append(f'status="{status.value}"')
        
        filter_str = " && ".join(filter_parts) if filter_parts else ""
        
        flows_data = self.pb.read("research_flows", filter=filter_str)
        
        return [ResearchFlow.from_dict(data) for data in flows_data]
    
    def update_flow(self, flow: ResearchFlow) -> bool:
        """Update a research flow."""
        flows = self.pb.read("research_flows", filter=f'flow_id="{flow.flow_id}"')
        
        if flows:
            flow_data = flow.to_dict()
            success = self.pb.update("research_flows", flows[0]["id"], flow_data)
            return bool(success)
        
        return False
    
    def delete_flow(self, flow_id: str) -> bool:
        """Delete a research flow."""
        flows = self.pb.read("research_flows", filter=f'flow_id="{flow_id}"')
        
        if flows:
            return self.pb.delete("research_flows", flows[0]["id"])
        
        return False
    
    def add_task_to_flow(self, flow_id: str, task: ResearchTask) -> bool:
        """Add a task to a research flow."""
        flow = self.get_flow(flow_id)
        
        if flow:
            flow.add_task(task)
            return self.update_flow(flow)
        
        return False
    
    def remove_task_from_flow(self, flow_id: str, task_id: str) -> bool:
        """Remove a task from a research flow."""
        flow = self.get_flow(flow_id)
        
        if flow:
            if flow.remove_task(task_id):
                return self.update_flow(flow)
        
        return False
    
    def update_task_status(self, flow_id: str, task_id: str, status: ResearchTaskStatus, 
                          progress: Optional[float] = None, 
                          results: Optional[Dict[str, Any]] = None,
                          error_message: Optional[str] = None) -> bool:
        """Update the status of a task in a research flow."""
        flow = self.get_flow(flow_id)
        
        if flow:
            if flow.update_task_status(task_id, status, progress, results, error_message):
                return self.update_flow(flow)
        
        return False
    
    def start_flow(self, flow_id: str) -> bool:
        """Start a research flow."""
        flow = self.get_flow(flow_id)
        
        if flow and flow.status == ResearchFlowStatus.PENDING:
            flow.status = ResearchFlowStatus.RUNNING
            flow.started_at = datetime.now()
            flow.updated_at = datetime.now()
            
            # Set all pending tasks to running
            for task in flow.tasks:
                if task.status == ResearchTaskStatus.PENDING:
                    task.status = ResearchTaskStatus.RUNNING
                    task.started_at = datetime.now()
                    task.updated_at = datetime.now()
            
            return self.update_flow(flow)
        
        return False
    
    def pause_flow(self, flow_id: str) -> bool:
        """Pause a research flow."""
        flow = self.get_flow(flow_id)
        
        if flow and flow.status == ResearchFlowStatus.RUNNING:
            flow.status = ResearchFlowStatus.PAUSED
            flow.updated_at = datetime.now()
            
            # Set all running tasks to paused
            for task in flow.tasks:
                if task.status == ResearchTaskStatus.RUNNING:
                    task.status = ResearchTaskStatus.PAUSED
                    task.updated_at = datetime.now()
            
            return self.update_flow(flow)
        
        return False
    
    def resume_flow(self, flow_id: str) -> bool:
        """Resume a paused research flow."""
        flow = self.get_flow(flow_id)
        
        if flow and flow.status == ResearchFlowStatus.PAUSED:
            flow.status = ResearchFlowStatus.RUNNING
            flow.updated_at = datetime.now()
            
            # Set all paused tasks to running
            for task in flow.tasks:
                if task.status == ResearchTaskStatus.PAUSED:
                    task.status = ResearchTaskStatus.RUNNING
                    task.updated_at = datetime.now()
            
            return self.update_flow(flow)
        
        return False
    
    def cancel_flow(self, flow_id: str) -> bool:
        """Cancel a research flow."""
        flow = self.get_flow(flow_id)
        
        if flow and flow.status in [ResearchFlowStatus.RUNNING, ResearchFlowStatus.PAUSED, ResearchFlowStatus.PENDING]:
            flow.status = ResearchFlowStatus.CANCELLED
            flow.updated_at = datetime.now()
            
            # Set all non-completed tasks to cancelled
            for task in flow.tasks:
                if task.status not in [ResearchTaskStatus.COMPLETED, ResearchTaskStatus.FAILED]:
                    task.status = ResearchTaskStatus.CANCELLED
                    task.updated_at = datetime.now()
                    task.completed_at = datetime.now()
            
            return self.update_flow(flow)
        
        return False

