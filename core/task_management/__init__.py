"""
Unified task management system for WiseFlow.

This module provides a consolidated task management system that supports
different execution strategies and provides a consistent API for task
creation, monitoring, and cancellation.
"""

from core.task_management.task import Task, TaskPriority, TaskStatus
from core.task_management.task_manager import TaskManager
from core.task_management.executor import (
    Executor,
    SequentialExecutor,
    ThreadPoolExecutor,
    AsyncExecutor
)
from core.task_management.exceptions import (
    TaskError,
    TaskDependencyError,
    TaskCancellationError,
    TaskTimeoutError
)

__all__ = [
    'Task',
    'TaskPriority',
    'TaskStatus',
    'TaskManager',
    'Executor',
    'SequentialExecutor',
    'ThreadPoolExecutor',
    'AsyncExecutor',
    'TaskError',
    'TaskDependencyError',
    'TaskCancellationError',
    'TaskTimeoutError'
]

