"""
Metrics collection and reporting for WiseFlow.

This module provides utilities for collecting and reporting metrics about
the WiseFlow system, including API request metrics, LLM usage metrics,
and system resource metrics.
"""

import time
import logging
import asyncio
import psutil
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logger = logging.getLogger(__name__)

# Global metrics storage
_metrics = {
    "api": {
        "requests": {
            "total": 0,
            "success": 0,
            "error": 0,
            "by_endpoint": {},
            "by_status": {},
            "by_method": {},
        },
        "response_time": {
            "avg_ms": 0,
            "min_ms": float('inf'),
            "max_ms": 0,
            "p50_ms": 0,
            "p95_ms": 0,
            "p99_ms": 0,
            "samples": [],
        },
    },
    "llm": {
        "requests": {
            "total": 0,
            "success": 0,
            "error": 0,
            "by_model": {},
        },
        "tokens": {
            "prompt": 0,
            "completion": 0,
            "total": 0,
            "by_model": {},
        },
        "cost": {
            "total": 0.0,
            "by_model": {},
        },
        "response_time": {
            "avg_ms": 0,
            "min_ms": float('inf'),
            "max_ms": 0,
            "samples": [],
        },
    },
    "system": {
        "cpu": {
            "percent": 0,
            "samples": [],
        },
        "memory": {
            "percent": 0,
            "used_mb": 0,
            "available_mb": 0,
            "samples": [],
        },
        "disk": {
            "percent": 0,
            "used_gb": 0,
            "available_gb": 0,
        },
    },
    "cache": {
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0,
        "size_mb": 0,
    },
    "uptime": {
        "start_time": datetime.now().isoformat(),
        "uptime_seconds": 0,
    },
}

# Metrics middleware
class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting API request metrics."""
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and collect metrics."""
        # Record start time
        start_time = time.time()
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Record metrics
            duration_ms = (time.time() - start_time) * 1000
            record_request_metrics(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                success=(response.status_code < 400)
            )
            
            return response
        except Exception as e:
            # Record error metrics
            duration_ms = (time.time() - start_time) * 1000
            record_request_metrics(
                endpoint=request.url.path,
                method=request.method,
                status_code=500,
                duration_ms=duration_ms,
                success=False
            )
            
            # Re-raise the exception
            raise

def setup_metrics(app: FastAPI):
    """
    Set up metrics collection for a FastAPI app.
    
    Args:
        app: FastAPI app to set up metrics for
    """
    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    # Start background task for system metrics collection
    @app.on_event("startup")
    async def start_metrics_collection():
        asyncio.create_task(collect_system_metrics())

async def collect_system_metrics(interval_seconds: int = 60):
    """
    Collect system metrics at regular intervals.
    
    Args:
        interval_seconds: Interval between metrics collections in seconds
    """
    while True:
        try:
            # Update uptime
            start_time = datetime.fromisoformat(_metrics["uptime"]["start_time"])
            _metrics["uptime"]["uptime_seconds"] = (datetime.now() - start_time).total_seconds()
            
            # Collect CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            _metrics["system"]["cpu"]["percent"] = cpu_percent
            _metrics["system"]["cpu"]["samples"].append((time.time(), cpu_percent))
            
            # Trim samples to keep only the last hour
            _metrics["system"]["cpu"]["samples"] = [
                sample for sample in _metrics["system"]["cpu"]["samples"]
                if time.time() - sample[0] < 3600
            ]
            
            # Collect memory metrics
            memory = psutil.virtual_memory()
            _metrics["system"]["memory"]["percent"] = memory.percent
            _metrics["system"]["memory"]["used_mb"] = memory.used / (1024 * 1024)
            _metrics["system"]["memory"]["available_mb"] = memory.available / (1024 * 1024)
            _metrics["system"]["memory"]["samples"].append((time.time(), memory.percent))
            
            # Trim samples to keep only the last hour
            _metrics["system"]["memory"]["samples"] = [
                sample for sample in _metrics["system"]["memory"]["samples"]
                if time.time() - sample[0] < 3600
            ]
            
            # Collect disk metrics
            disk = psutil.disk_usage("/")
            _metrics["system"]["disk"]["percent"] = disk.percent
            _metrics["system"]["disk"]["used_gb"] = disk.used / (1024 * 1024 * 1024)
            _metrics["system"]["disk"]["available_gb"] = disk.free / (1024 * 1024 * 1024)
            
            # Wait for next collection
            await asyncio.sleep(interval_seconds)
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            await asyncio.sleep(interval_seconds)

def record_request_metrics(
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: float,
    success: bool
):
    """
    Record metrics for an API request.
    
    Args:
        endpoint: API endpoint
        method: HTTP method
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        success: Whether the request was successful
    """
    # Update total requests
    _metrics["api"]["requests"]["total"] += 1
    
    # Update success/error counts
    if success:
        _metrics["api"]["requests"]["success"] += 1
    else:
        _metrics["api"]["requests"]["error"] += 1
    
    # Update by endpoint
    if endpoint not in _metrics["api"]["requests"]["by_endpoint"]:
        _metrics["api"]["requests"]["by_endpoint"][endpoint] = {
            "total": 0,
            "success": 0,
            "error": 0,
        }
    _metrics["api"]["requests"]["by_endpoint"][endpoint]["total"] += 1
    if success:
        _metrics["api"]["requests"]["by_endpoint"][endpoint]["success"] += 1
    else:
        _metrics["api"]["requests"]["by_endpoint"][endpoint]["error"] += 1
    
    # Update by status
    status_str = str(status_code)
    if status_str not in _metrics["api"]["requests"]["by_status"]:
        _metrics["api"]["requests"]["by_status"][status_str] = 0
    _metrics["api"]["requests"]["by_status"][status_str] += 1
    
    # Update by method
    if method not in _metrics["api"]["requests"]["by_method"]:
        _metrics["api"]["requests"]["by_method"][method] = 0
    _metrics["api"]["requests"]["by_method"][method] += 1
    
    # Update response time metrics
    _metrics["api"]["response_time"]["samples"].append(duration_ms)
    
    # Trim samples to keep only the last 1000
    if len(_metrics["api"]["response_time"]["samples"]) > 1000:
        _metrics["api"]["response_time"]["samples"].pop(0)
    
    # Update min/max
    _metrics["api"]["response_time"]["min_ms"] = min(
        _metrics["api"]["response_time"]["min_ms"],
        duration_ms
    )
    _metrics["api"]["response_time"]["max_ms"] = max(
        _metrics["api"]["response_time"]["max_ms"],
        duration_ms
    )
    
    # Update average
    samples = _metrics["api"]["response_time"]["samples"]
    _metrics["api"]["response_time"]["avg_ms"] = sum(samples) / len(samples)
    
    # Update percentiles
    sorted_samples = sorted(samples)
    _metrics["api"]["response_time"]["p50_ms"] = sorted_samples[int(len(sorted_samples) * 0.5)]
    _metrics["api"]["response_time"]["p95_ms"] = sorted_samples[int(len(sorted_samples) * 0.95)]
    _metrics["api"]["response_time"]["p99_ms"] = sorted_samples[int(len(sorted_samples) * 0.99)]

def record_llm_metrics(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: float,
    success: bool,
    cost: Optional[float] = None
):
    """
    Record metrics for an LLM request.
    
    Args:
        model: LLM model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        duration_ms: Request duration in milliseconds
        success: Whether the request was successful
        cost: Optional cost of the request
    """
    # Update total requests
    _metrics["llm"]["requests"]["total"] += 1
    
    # Update success/error counts
    if success:
        _metrics["llm"]["requests"]["success"] += 1
    else:
        _metrics["llm"]["requests"]["error"] += 1
    
    # Update by model
    if model not in _metrics["llm"]["requests"]["by_model"]:
        _metrics["llm"]["requests"]["by_model"][model] = {
            "total": 0,
            "success": 0,
            "error": 0,
        }
    _metrics["llm"]["requests"]["by_model"][model]["total"] += 1
    if success:
        _metrics["llm"]["requests"]["by_model"][model]["success"] += 1
    else:
        _metrics["llm"]["requests"]["by_model"][model]["error"] += 1
    
    # Update token metrics
    _metrics["llm"]["tokens"]["prompt"] += prompt_tokens
    _metrics["llm"]["tokens"]["completion"] += completion_tokens
    _metrics["llm"]["tokens"]["total"] += prompt_tokens + completion_tokens
    
    # Update by model
    if model not in _metrics["llm"]["tokens"]["by_model"]:
        _metrics["llm"]["tokens"]["by_model"][model] = {
            "prompt": 0,
            "completion": 0,
            "total": 0,
        }
    _metrics["llm"]["tokens"]["by_model"][model]["prompt"] += prompt_tokens
    _metrics["llm"]["tokens"]["by_model"][model]["completion"] += completion_tokens
    _metrics["llm"]["tokens"]["by_model"][model]["total"] += prompt_tokens + completion_tokens
    
    # Update cost metrics if provided
    if cost is not None:
        _metrics["llm"]["cost"]["total"] += cost
        
        if model not in _metrics["llm"]["cost"]["by_model"]:
            _metrics["llm"]["cost"]["by_model"][model] = 0
        _metrics["llm"]["cost"]["by_model"][model] += cost
    
    # Update response time metrics
    _metrics["llm"]["response_time"]["samples"].append(duration_ms)
    
    # Trim samples to keep only the last 1000
    if len(_metrics["llm"]["response_time"]["samples"]) > 1000:
        _metrics["llm"]["response_time"]["samples"].pop(0)
    
    # Update min/max
    _metrics["llm"]["response_time"]["min_ms"] = min(
        _metrics["llm"]["response_time"]["min_ms"],
        duration_ms
    )
    _metrics["llm"]["response_time"]["max_ms"] = max(
        _metrics["llm"]["response_time"]["max_ms"],
        duration_ms
    )
    
    # Update average
    samples = _metrics["llm"]["response_time"]["samples"]
    _metrics["llm"]["response_time"]["avg_ms"] = sum(samples) / len(samples)

def record_cache_metrics(hits: int, misses: int, size_mb: float):
    """
    Record cache metrics.
    
    Args:
        hits: Number of cache hits
        misses: Number of cache misses
        size_mb: Cache size in MB
    """
    _metrics["cache"]["hits"] = hits
    _metrics["cache"]["misses"] = misses
    _metrics["cache"]["size_mb"] = size_mb
    
    # Calculate hit rate
    total = hits + misses
    _metrics["cache"]["hit_rate"] = hits / total if total > 0 else 0.0

def get_metrics() -> Dict[str, Any]:
    """
    Get all metrics.
    
    Returns:
        Dictionary of metrics
    """
    return {
        "api": _metrics["api"],
        "llm": _metrics["llm"],
        "system": _metrics["system"],
        "cache": _metrics["cache"],
        "uptime": _metrics["uptime"],
        "timestamp": datetime.now().isoformat(),
    }

def get_api_metrics() -> Dict[str, Any]:
    """
    Get API metrics.
    
    Returns:
        Dictionary of API metrics
    """
    return {
        "api": _metrics["api"],
        "timestamp": datetime.now().isoformat(),
    }

def get_llm_metrics() -> Dict[str, Any]:
    """
    Get LLM metrics.
    
    Returns:
        Dictionary of LLM metrics
    """
    return {
        "llm": _metrics["llm"],
        "timestamp": datetime.now().isoformat(),
    }

def get_system_metrics() -> Dict[str, Any]:
    """
    Get system metrics.
    
    Returns:
        Dictionary of system metrics
    """
    return {
        "system": _metrics["system"],
        "uptime": _metrics["uptime"],
        "timestamp": datetime.now().isoformat(),
    }

def reset_metrics():
    """Reset all metrics."""
    global _metrics
    
    # Save start time
    start_time = _metrics["uptime"]["start_time"]
    
    # Reset metrics
    _metrics = {
        "api": {
            "requests": {
                "total": 0,
                "success": 0,
                "error": 0,
                "by_endpoint": {},
                "by_status": {},
                "by_method": {},
            },
            "response_time": {
                "avg_ms": 0,
                "min_ms": float('inf'),
                "max_ms": 0,
                "p50_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
                "samples": [],
            },
        },
        "llm": {
            "requests": {
                "total": 0,
                "success": 0,
                "error": 0,
                "by_model": {},
            },
            "tokens": {
                "prompt": 0,
                "completion": 0,
                "total": 0,
                "by_model": {},
            },
            "cost": {
                "total": 0.0,
                "by_model": {},
            },
            "response_time": {
                "avg_ms": 0,
                "min_ms": float('inf'),
                "max_ms": 0,
                "samples": [],
            },
        },
        "system": {
            "cpu": {
                "percent": 0,
                "samples": [],
            },
            "memory": {
                "percent": 0,
                "used_mb": 0,
                "available_mb": 0,
                "samples": [],
            },
            "disk": {
                "percent": 0,
                "used_gb": 0,
                "available_gb": 0,
            },
        },
        "cache": {
            "hits": 0,
            "misses": 0,
            "hit_rate": 0.0,
            "size_mb": 0,
        },
        "uptime": {
            "start_time": start_time,
            "uptime_seconds": 0,
        },
    }

