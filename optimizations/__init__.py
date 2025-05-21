"""
WiseFlow Performance Optimizations.

This package provides performance optimizations for the WiseFlow project.
"""

from .apply_optimizations import apply_all_optimizations, patch_modules
from .database_optimizations import optimize_all_databases
from .crawler_optimizations import content_cache, rate_limiter
from .llm_optimizations import llm_cache, openai_circuit_breaker
from .thread_pool_optimizations import adaptive_thread_pool_manager
from .resource_monitor_optimizations import optimized_resource_monitor
from .dashboard_optimizations import dashboard_optimizer
from .benchmark import PerformanceBenchmark, APIBenchmark, run_benchmarks

__all__ = [
    'apply_all_optimizations',
    'patch_modules',
    'optimize_all_databases',
    'content_cache',
    'rate_limiter',
    'llm_cache',
    'openai_circuit_breaker',
    'adaptive_thread_pool_manager',
    'optimized_resource_monitor',
    'dashboard_optimizer',
    'PerformanceBenchmark',
    'APIBenchmark',
    'run_benchmarks'
]

