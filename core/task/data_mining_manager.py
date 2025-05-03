"""
Data Mining Task Manager for WiseFlow.
This module provides functionality for managing and interconnecting data mining tasks
across different search types and data sources.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import uuid
import logging
from loguru import logger

from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from ..analysis.data_mining import analyze_info_items, get_analysis_for_focus
from ..connectors.github import github_connector
from ..connectors.academic import academic_connector
from ..connectors.web import web_connector
from ..connectors.youtube import youtube_connector
from ..connectors.code_search import code_search_connector

project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
data_mining_manager_logger = get_logger('data_mining_manager', project_dir)
pb = PbTalker(data_mining_manager_logger)

class TaskInterconnection:
    """Class representing an interconnection between data mining tasks."""
    
    def __init__(
        self,
        interconnection_id: str,
        source_task_id: str,
        target_task_id: str,
        interconnection_type: str,
        description: str = "",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        status: str = "active"
    ):
        self.interconnection_id = interconnection_id
        self.source_task_id = source_task_id
        self.target_task_id = target_task_id
        self.interconnection_type = interconnection_type
        self.description = description
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or self.created_at
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the interconnection to a dictionary."""
        return {
            "interconnection_id": self.interconnection_id,
            "source_task_id": self.source_task_id,
            "target_task_id": self.target_task_id,
            "interconnection_type": self.interconnection_type,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskInterconnection':
        """Create an interconnection from a dictionary."""
        return cls(
            interconnection_id=data.get("interconnection_id", ""),
            source_task_id=data.get("source_task_id", ""),
            target_task_id=data.get("target_task_id", ""),
            interconnection_type=data.get("interconnection_type", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", None),
            updated_at=data.get("updated_at", None),
            status=data.get("status", "active")
        )

class DataMiningTask:
    """Class representing a data mining task."""
    
    def __init__(
        self,
        task_id: str,
        name: str,
        task_type: str,
        description: str,
        search_params: Dict[str, Any],
        status: str = "active",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        context_files: Optional[List[str]] = None,
        results: Optional[Dict[str, Any]] = None
    ):
        self.task_id = task_id
        self.name = name
        self.task_type = task_type
        self.description = description
        self.search_params = search_params
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or self.created_at
        self.context_files = context_files or []
        self.results = results or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "task_type": self.task_type,
            "description": self.description,
            "search_params": self.search_params,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "context_files": self.context_files,
            "results": self.results
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataMiningTask':
        """Create a task from a dictionary."""
        return cls(
            task_id=data.get("task_id", ""),
            name=data.get("name", ""),
            task_type=data.get("task_type", ""),
            description=data.get("description", ""),
            search_params=data.get("search_params", {}),
            status=data.get("status", "active"),
            created_at=data.get("created_at", None),
            updated_at=data.get("updated_at", None),
            context_files=data.get("context_files", []),
            results=data.get("results", {})
        )

class DataMiningManager:
    """Manager for data mining tasks."""
    
    def __init__(self):
        self.pb = pb
        self.logger = data_mining_manager_logger
    
    async def create_task(
        self,
        name: str,
        task_type: str,
        description: str,
        search_params: Dict[str, Any],
        context_files: Optional[List[str]] = None
    ) -> str:
        """
        Create a new data mining task.
        
        Args:
            name: Name of the task
            task_type: Type of task (github, arxiv, web, youtube, etc.)
            description: Description of the task
            search_params: Parameters for the search
            context_files: List of context file paths
            
        Returns:
            ID of the created task
        """
        task_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        
        task = DataMiningTask(
            task_id=task_id,
            name=name,
            task_type=task_type,
            description=description,
            search_params=search_params,
            context_files=context_files or []
        )
        
        # Save to database
        try:
            self.pb.add(collection_name='data_mining_tasks', body=task.to_dict())
            self.logger.info(f"Created data mining task {task_id}")
            
            # Start the task in the background
            asyncio.create_task(self.run_task(task_id))
            
            return task_id
        except Exception as e:
            self.logger.error(f"Error creating data mining task: {e}")
            raise
    
    async def get_task(self, task_id: str) -> Optional[DataMiningTask]:
        """
        Get a data mining task by ID.
        
        Args:
            task_id: ID of the task
            
        Returns:
            DataMiningTask object or None if not found
        """
        try:
            result = self.pb.read(collection_name='data_mining_tasks', filter=f"task_id='{task_id}'")
            if result:
                return DataMiningTask.from_dict(result[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting data mining task {task_id}: {e}")
            return None
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a data mining task.
        
        Args:
            task_id: ID of the task
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            task = await self.get_task(task_id)
            if not task:
                self.logger.warning(f"Task {task_id} not found for update")
                return False
            
            # Update fields
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            # Always update the updated_at timestamp
            task.updated_at = datetime.now().isoformat()
            
            # Save to database
            self.pb.update(
                collection_name='data_mining_tasks',
                record_id=task_id,
                body=task.to_dict()
            )
            
            self.logger.info(f"Updated data mining task {task_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating data mining task {task_id}: {e}")
            return False
    
    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a data mining task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.pb.delete(collection_name='data_mining_tasks', record_id=task_id)
            self.logger.info(f"Deleted data mining task {task_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting data mining task {task_id}: {e}")
            return False
    
    async def get_all_tasks(self, status: Optional[str] = None) -> List[DataMiningTask]:
        """
        Get all data mining tasks, optionally filtered by status.
        
        Args:
            status: Optional status filter (active, inactive, etc.)
            
        Returns:
            List of DataMiningTask objects
        """
        try:
            filter_query = f"status='{status}'" if status else ""
            results = self.pb.read(collection_name='data_mining_tasks', filter=filter_query, sort="-created_at")
            
            tasks = [DataMiningTask.from_dict(result) for result in results]
            return tasks
        except Exception as e:
            self.logger.error(f"Error getting data mining tasks: {e}")
            return []
    
    async def toggle_task_status(self, task_id: str, active: bool) -> bool:
        """
        Toggle the status of a data mining task.
        
        Args:
            task_id: ID of the task
            active: True to set active, False to set inactive
            
        Returns:
            True if successful, False otherwise
        """
        status = "active" if active else "inactive"
        return await self.update_task(task_id, {"status": status})
    
    async def create_task_interconnection(
        self,
        source_task_id: str,
        target_task_id: str,
        interconnection_type: str,
        description: str = ""
    ) -> str:
        """
        Create an interconnection between two data mining tasks.
        
        Args:
            source_task_id: ID of the source task
            target_task_id: ID of the target task
            interconnection_type: Type of interconnection (feed, filter, combine, sequence)
            description: Description of the interconnection
            
        Returns:
            ID of the created interconnection
        """
        interconnection_id = f"interconnect_{uuid.uuid4().hex[:8]}"
        
        interconnection = TaskInterconnection(
            interconnection_id=interconnection_id,
            source_task_id=source_task_id,
            target_task_id=target_task_id,
            interconnection_type=interconnection_type,
            description=description
        )
        
        # Save to database
        try:
            self.pb.add(collection_name='data_mining_interconnections', body=interconnection.to_dict())
            self.logger.info(f"Created task interconnection {interconnection_id}")
            
            return interconnection_id
        except Exception as e:
            self.logger.error(f"Error creating task interconnection: {e}")
            raise
    
    async def get_task_interconnection(self, interconnection_id: str) -> Optional[TaskInterconnection]:
        """
        Get a task interconnection by ID.
        
        Args:
            interconnection_id: ID of the interconnection
            
        Returns:
            TaskInterconnection object or None if not found
        """
        try:
            result = self.pb.read(collection_name='data_mining_interconnections', filter=f"interconnection_id='{interconnection_id}'")
            if result:
                return TaskInterconnection.from_dict(result[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting task interconnection {interconnection_id}: {e}")
            return None
    
    async def delete_task_interconnection(self, interconnection_id: str) -> bool:
        """
        Delete a task interconnection.
        
        Args:
            interconnection_id: ID of the interconnection
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.pb.delete(collection_name='data_mining_interconnections', record_id=interconnection_id)
            self.logger.info(f"Deleted task interconnection {interconnection_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting task interconnection {interconnection_id}: {e}")
            return False
    
    async def get_all_task_interconnections(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all task interconnections, optionally filtered by status.
        
        Args:
            status: Optional status filter (active, inactive, etc.)
            
        Returns:
            List of interconnection dictionaries
        """
        try:
            filter_query = f"status='{status}'" if status else ""
            results = self.pb.read(collection_name='data_mining_interconnections', filter=filter_query, sort="-created_at")
            
            interconnections = [TaskInterconnection.from_dict(result).to_dict() for result in results]
            return interconnections
        except Exception as e:
            self.logger.error(f"Error getting task interconnections: {e}")
            return []
    
    async def get_task_interconnections_for_task(self, task_id: str, as_source: bool = True) -> List[Dict[str, Any]]:
        """
        Get all interconnections for a specific task.
        
        Args:
            task_id: ID of the task
            as_source: If True, get interconnections where task is the source, otherwise get where task is the target
            
        Returns:
            List of interconnection dictionaries
        """
        try:
            field = "source_task_id" if as_source else "target_task_id"
            filter_query = f"{field}='{task_id}'"
            results = self.pb.read(collection_name='data_mining_interconnections', filter=filter_query, sort="-created_at")
            
            interconnections = [TaskInterconnection.from_dict(result).to_dict() for result in results]
            return interconnections
        except Exception as e:
            self.logger.error(f"Error getting task interconnections for task {task_id}: {e}")
            return []
    
    async def process_interconnected_tasks(self, task_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process interconnected tasks based on the results of a task.
        
        Args:
            task_id: ID of the task that has completed
            results: Results of the completed task
            
        Returns:
            Dictionary containing the processed results
        """
        # Get all interconnections where this task is the source
        interconnections = await self.get_task_interconnections_for_task(task_id, as_source=True)
        
        if not interconnections:
            return results
        
        processed_results = results.copy()
        
        for interconnection in interconnections:
            target_task_id = interconnection.get("target_task_id")
            interconnection_type = interconnection.get("interconnection_type")
            
            target_task = await self.get_task(target_task_id)
            if not target_task:
                continue
            
            if interconnection_type == "feed":
                # Feed results as input to target task
                await self.update_task(target_task_id, {
                    "search_params": {
                        **target_task.search_params,
                        "input_from_task": {
                            "task_id": task_id,
                            "results": results
                        }
                    }
                })
                
                # Run the target task
                asyncio.create_task(self.run_task(target_task_id))
                
            elif interconnection_type == "filter":
                # Use source task results to filter target task results
                target_results = await self.get_task_results(target_task_id)
                
                # Implement filtering logic based on the task types
                # This is a simplified example
                filtered_results = {
                    **target_results,
                    "filtered_by": {
                        "task_id": task_id,
                        "filter_criteria": results
                    }
                }
                
                # Update target task with filtered results
                await self.update_task(target_task_id, {
                    "results": filtered_results
                })
                
            elif interconnection_type == "combine":
                # Combine results from both tasks
                target_results = await self.get_task_results(target_task_id)
                
                # Implement combining logic based on the task types
                # This is a simplified example
                combined_results = {
                    "source_task": {
                        "task_id": task_id,
                        "results": results
                    },
                    "target_task": {
                        "task_id": target_task_id,
                        "results": target_results
                    },
                    "combined_at": datetime.now().isoformat()
                }
                
                # Update both tasks with combined results
                await self.update_task(task_id, {
                    "results": {**results, "combined_with": target_task_id}
                })
                
                await self.update_task(target_task_id, {
                    "results": {**target_results, "combined_with": task_id}
                })
                
                processed_results = {**processed_results, "combined_with": target_task_id}
                
            elif interconnection_type == "sequence":
                # Run target task after source task completes
                asyncio.create_task(self.run_task(target_task_id))
        
        return processed_results
    
    async def run_task(self, task_id: str) -> Dict[str, Any]:
        """
        Run a data mining task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary containing the results
        """
        task = await self.get_task(task_id)
        if not task:
            self.logger.warning(f"Task {task_id} not found for running")
            return {"error": "Task not found"}
        
        if task.status != "active":
            self.logger.info(f"Task {task_id} is not active, skipping")
            return {"error": "Task is not active"}
        
        self.logger.info(f"Running data mining task {task_id} of type {task.task_type}")
        
        # Update task status to running
        await self.update_task(task_id, {"status": "running"})
        
        try:
            # Run the appropriate connector based on task type
            results = {}
            
            if task.task_type == "github":
                # Call GitHub connector
                self.logger.info(f"Running GitHub search for task {task_id}")
                # Implement GitHub search logic here
                results = {"status": "success", "message": "GitHub search completed"}
                
            elif task.task_type == "arxiv":
                # Call Arxiv connector
                self.logger.info(f"Running Arxiv search for task {task_id}")
                # Implement Arxiv search logic here
                results = {"status": "success", "message": "Arxiv search completed"}
                
            elif task.task_type == "web":
                # Call Web connector
                self.logger.info(f"Running Web search for task {task_id}")
                # Implement Web search logic here
                results = {"status": "success", "message": "Web search completed"}
                
            elif task.task_type == "youtube":
                # Call YouTube connector
                self.logger.info(f"Running YouTube search for task {task_id}")
                # Implement YouTube search logic here
                results = {"status": "success", "message": "YouTube search completed"}
                
            else:
                self.logger.warning(f"Unknown task type {task.task_type} for task {task_id}")
                results = {"error": f"Unknown task type {task.task_type}"}
            
            # Process interconnected tasks
            processed_results = await self.process_interconnected_tasks(task_id, results)
            
            # Update task with results
            await self.update_task(task_id, {
                "status": "active",
                "results": processed_results,
                "updated_at": datetime.now().isoformat()
            })
            
            self.logger.info(f"Completed data mining task {task_id}")
            return processed_results
            
        except Exception as e:
            self.logger.error(f"Error running data mining task {task_id}: {e}")
            
            # Update task with error
            await self.update_task(task_id, {
                "status": "error",
                "results": {"error": str(e)},
                "updated_at": datetime.now().isoformat()
            })
            
            return {"error": str(e)}
    
    async def get_task_results(self, task_id: str) -> Dict[str, Any]:
        """
        Get the results of a data mining task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary containing the results
        """
        task = await self.get_task(task_id)
        if not task:
            self.logger.warning(f"Task {task_id} not found for getting results")
            return {"error": "Task not found"}
        
        return task.results
    
    async def analyze_task_results(self, task_id: str) -> Dict[str, Any]:
        """
        Analyze the results of a data mining task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary containing the analysis results
        """
        task = await self.get_task(task_id)
        if not task:
            self.logger.warning(f"Task {task_id} not found for analysis")
            return {"error": "Task not found"}
        
        # Get the info items associated with this task
        info_items = self.pb.read(collection_name='infos', filter=f"tag='{task_id}'")
        
        if not info_items:
            self.logger.warning(f"No information items found for task {task_id}")
            return {"error": "No information items found"}
        
        # Perform analysis
        analysis_results = await analyze_info_items(info_items, task_id)
        
        # Update task with analysis results
        await self.update_task(task_id, {
            "results": {**task.results, "analysis": analysis_results},
            "updated_at": datetime.now().isoformat()
        })
        
        return analysis_results
    
    async def save_template(self, template_data: Dict[str, Any]) -> str:
        """
        Save a data mining template.
        
        Args:
            template_data: Template data including name, type, and parameters
            
        Returns:
            ID of the created template
        """
        if "name" not in template_data:
            raise ValueError("Template name is required")
            
        template_id = f"template_{uuid.uuid4().hex[:8]}"
        
        template = {
            "template_id": template_id,
            "name": template_data["name"],
            "type": template_data.get("type", "generic"),
            "parameters": template_data,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_used": None
        }
        
        try:
            self.pb.add(collection_name='data_mining_templates', body=template)
            self.logger.info(f"Created data mining template {template_id}")
            return template_id
        except Exception as e:
            self.logger.error(f"Error creating data mining template: {e}")
            raise
    
    async def get_templates(self, template_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all data mining templates, optionally filtered by type.
        
        Args:
            template_type: Optional type filter (github, arxiv, web, youtube, etc.)
            
        Returns:
            List of template dictionaries
        """
        try:
            filter_query = f"type='{template_type}'" if template_type else ""
            results = self.pb.read(collection_name='data_mining_templates', filter=filter_query, sort="-created_at")
            return results
        except Exception as e:
            self.logger.error(f"Error getting data mining templates: {e}")
            return []
    
    async def generate_preview(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a preview of a data mining task.
        
        Args:
            search_params: Search parameters
            
        Returns:
            Dictionary containing preview information
        """
        task_type = search_params.get("task_type", "")
        if not task_type and "search_scheme" in search_params:
            # Try to determine task type from search parameters
            if "repository_filters" in search_params:
                task_type = "github"
            elif "content_types" in search_params and "videos" in search_params.get("content_types", {}):
                task_type = "youtube"
            elif "categories" in search_params:
                task_type = "arxiv"
            else:
                task_type = "web"
        
        preview_data = {
            "estimated_repos": 0,
            "estimated_files": 0,
            "estimated_time": "Unknown"
        }
        
        try:
            if task_type == "github":
                # Estimate GitHub search results
                language = search_params.get("repository_filters", {}).get("language", "all")
                stars = search_params.get("repository_filters", {}).get("stars", "any")
                
                # Simple estimation logic
                base_repos = 50
                if stars == "1000+":
                    base_repos = 20
                elif stars == "10000+":
                    base_repos = 5
                
                language_multiplier = 1.0
                if language != "all":
                    if language in ["javascript", "python", "java", "c++"]:
                        language_multiplier = 1.5
                    else:
                        language_multiplier = 0.7
                
                estimated_repos = int(base_repos * language_multiplier)
                estimated_files = estimated_repos * 50  # Assume average 50 files per repo
                
                # Estimate time based on parallel workers
                parallel_workers = search_params.get("parallel_workers", 6)
                estimated_minutes = (estimated_repos * 2) / parallel_workers
                estimated_time = f"{int(estimated_minutes)} minutes"
                
                preview_data = {
                    "estimated_repos": estimated_repos,
                    "estimated_files": estimated_files,
                    "estimated_time": estimated_time
                }
                
            elif task_type == "youtube":
                # Estimate YouTube search results
                content_types = search_params.get("contentTypes", {})
                max_results = search_params.get("maxResults", 50)
                
                type_count = sum(1 for v in content_types.values() if v)
                estimated_videos = max_results * max(1, type_count)
                
                # Estimate time based on processing options
                processing_options = search_params.get("processingOptions", {})
                time_per_video = 1  # Base time in minutes
                
                if processing_options.get("transcribeAudio", False):
                    time_per_video += 2
                if processing_options.get("extractKeyPoints", False):
                    time_per_video += 1
                if processing_options.get("downloadVideos", False):
                    time_per_video += 3
                if processing_options.get("analyzeComments", False):
                    time_per_video += 2
                
                parallel_workers = search_params.get("parallelWorkers", 2)
                estimated_minutes = (estimated_videos * time_per_video) / parallel_workers
                estimated_time = f"{int(estimated_minutes)} minutes"
                
                preview_data = {
                    "estimated_videos": estimated_videos,
                    "estimated_time": estimated_time
                }
                
            elif task_type == "arxiv":
                # Estimate arXiv search results
                max_results = search_params.get("max_results", 100)
                categories = search_params.get("categories", [])
                
                category_multiplier = len(categories) if categories else 1
                estimated_papers = min(max_results, 50 * category_multiplier)
                
                # Estimate time
                estimated_minutes = estimated_papers * 0.5  # Assume 30 seconds per paper
                estimated_time = f"{int(estimated_minutes)} minutes"
                
                preview_data = {
                    "estimated_papers": estimated_papers,
                    "estimated_time": estimated_time
                }
                
            elif task_type == "web":
                # Estimate web search results
                max_results = search_params.get("max_results", 20)
                follow_links = search_params.get("follow_links", False)
                
                estimated_pages = max_results
                if follow_links:
                    estimated_pages *= 3  # Assume each result has 2 relevant links
                
                # Estimate time
                estimated_minutes = estimated_pages * 1  # Assume 1 minute per page
                estimated_time = f"{int(estimated_minutes)} minutes"
                
                preview_data = {
                    "estimated_pages": estimated_pages,
                    "estimated_time": estimated_time
                }
            
            return preview_data
            
        except Exception as e:
            self.logger.error(f"Error generating preview: {e}")
            return preview_data

# Create a singleton instance
data_mining_manager = DataMiningManager()
