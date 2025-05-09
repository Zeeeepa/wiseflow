"""
Benchmark utilities for WiseFlow.

This module provides functions to benchmark performance in WiseFlow.
"""

import os
import time
import asyncio
import logging
import psutil
import json
import aiofiles
import statistics
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import concurrent.futures
import requests
import random
import string
from tqdm import tqdm

logger = logging.getLogger(__name__)

class PerformanceBenchmark:
    """
    Performance benchmark for WiseFlow.
    
    This class provides functionality to benchmark performance metrics.
    """
    
    def __init__(
        self,
        output_dir: str,
        name: str = "benchmark",
        iterations: int = 5,
        warmup_iterations: int = 1
    ):
        """
        Initialize the performance benchmark.
        
        Args:
            output_dir: Directory to store benchmark results
            name: Name of the benchmark
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations
        """
        self.output_dir = output_dir
        self.name = name
        self.iterations = iterations
        self.warmup_iterations = warmup_iterations
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.results: Dict[str, List[Dict[str, Any]]] = {}
    
    async def run_benchmark(
        self,
        benchmark_func: Callable,
        name: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run a benchmark.
        
        Args:
            benchmark_func: Function to benchmark
            name: Name of the benchmark
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Dictionary with benchmark results
        """
        logger.info(f"Running benchmark: {name}")
        
        # Initialize results
        if name not in self.results:
            self.results[name] = []
        
        # Run warmup iterations
        logger.info(f"Running {self.warmup_iterations} warmup iterations...")
        for i in range(self.warmup_iterations):
            await benchmark_func(*args, **kwargs)
        
        # Run benchmark iterations
        logger.info(f"Running {self.iterations} benchmark iterations...")
        
        iteration_results = []
        
        for i in range(self.iterations):
            # Measure CPU and memory before
            cpu_before = psutil.cpu_percent(interval=0.1)
            memory_before = psutil.virtual_memory().used
            
            # Measure time
            start_time = time.time()
            
            # Run function
            result = await benchmark_func(*args, **kwargs)
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Measure CPU and memory after
            cpu_after = psutil.cpu_percent(interval=0.1)
            memory_after = psutil.virtual_memory().used
            
            # Calculate memory usage
            memory_used = memory_after - memory_before
            
            # Store iteration result
            iteration_result = {
                "iteration": i + 1,
                "elapsed_time": elapsed_time,
                "cpu_before": cpu_before,
                "cpu_after": cpu_after,
                "memory_before": memory_before,
                "memory_after": memory_after,
                "memory_used": memory_used,
                "timestamp": datetime.now().isoformat()
            }
            
            iteration_results.append(iteration_result)
            
            logger.info(f"Iteration {i + 1}/{self.iterations}: {elapsed_time:.4f}s")
        
        # Calculate statistics
        elapsed_times = [r["elapsed_time"] for r in iteration_results]
        memory_used = [r["memory_used"] for r in iteration_results]
        
        stats = {
            "name": name,
            "iterations": self.iterations,
            "time_min": min(elapsed_times),
            "time_max": max(elapsed_times),
            "time_mean": statistics.mean(elapsed_times),
            "time_median": statistics.median(elapsed_times),
            "time_stdev": statistics.stdev(elapsed_times) if len(elapsed_times) > 1 else 0,
            "memory_min": min(memory_used),
            "memory_max": max(memory_used),
            "memory_mean": statistics.mean(memory_used),
            "memory_median": statistics.median(memory_used),
            "memory_stdev": statistics.stdev(memory_used) if len(memory_used) > 1 else 0,
            "timestamp": datetime.now().isoformat(),
            "iteration_results": iteration_results
        }
        
        # Store results
        self.results[name].append(stats)
        
        # Save results to file
        await self._save_results()
        
        # Generate charts
        self._generate_charts()
        
        logger.info(f"Benchmark complete: {name}")
        logger.info(f"Time (mean): {stats['time_mean']:.4f}s")
        logger.info(f"Memory (mean): {stats['memory_mean'] / (1024 * 1024):.2f} MB")
        
        return stats
    
    async def _save_results(self):
        """Save benchmark results to file."""
        results_file = os.path.join(self.output_dir, f"{self.name}_results.json")
        
        try:
            async with aiofiles.open(results_file, "w") as f:
                await f.write(json.dumps(self.results, indent=2))
        except Exception as e:
            logger.error(f"Error saving benchmark results: {e}")
    
    def _generate_charts(self):
        """Generate charts from benchmark results."""
        try:
            # Create charts directory
            charts_dir = os.path.join(self.output_dir, "charts")
            os.makedirs(charts_dir, exist_ok=True)
            
            # Generate time comparison chart
            self._generate_time_comparison_chart(charts_dir)
            
            # Generate memory comparison chart
            self._generate_memory_comparison_chart(charts_dir)
        except Exception as e:
            logger.error(f"Error generating benchmark charts: {e}")
    
    def _generate_time_comparison_chart(self, charts_dir: str):
        """
        Generate time comparison chart.
        
        Args:
            charts_dir: Directory to store charts
        """
        plt.figure(figsize=(12, 8))
        
        benchmark_names = []
        mean_times = []
        std_times = []
        
        for name, results in self.results.items():
            if results:
                benchmark_names.append(name)
                mean_times.append(results[-1]["time_mean"])
                std_times.append(results[-1]["time_stdev"])
        
        x = np.arange(len(benchmark_names))
        
        plt.bar(x, mean_times, yerr=std_times, align='center', alpha=0.7, capsize=10)
        plt.xticks(x, benchmark_names, rotation=45, ha='right')
        plt.ylabel('Time (seconds)')
        plt.title('Benchmark Time Comparison')
        plt.tight_layout()
        
        chart_file = os.path.join(charts_dir, f"{self.name}_time_comparison.png")
        plt.savefig(chart_file)
        plt.close()
    
    def _generate_memory_comparison_chart(self, charts_dir: str):
        """
        Generate memory comparison chart.
        
        Args:
            charts_dir: Directory to store charts
        """
        plt.figure(figsize=(12, 8))
        
        benchmark_names = []
        mean_memory = []
        std_memory = []
        
        for name, results in self.results.items():
            if results:
                benchmark_names.append(name)
                # Convert to MB
                mean_memory.append(results[-1]["memory_mean"] / (1024 * 1024))
                std_memory.append(results[-1]["memory_stdev"] / (1024 * 1024))
        
        x = np.arange(len(benchmark_names))
        
        plt.bar(x, mean_memory, yerr=std_memory, align='center', alpha=0.7, capsize=10)
        plt.xticks(x, benchmark_names, rotation=45, ha='right')
        plt.ylabel('Memory (MB)')
        plt.title('Benchmark Memory Comparison')
        plt.tight_layout()
        
        chart_file = os.path.join(charts_dir, f"{self.name}_memory_comparison.png")
        plt.savefig(chart_file)
        plt.close()

class APIBenchmark:
    """
    API benchmark for WiseFlow.
    
    This class provides functionality to benchmark API endpoints.
    """
    
    def __init__(
        self,
        base_url: str,
        output_dir: str,
        name: str = "api_benchmark",
        iterations: int = 10,
        warmup_iterations: int = 2,
        concurrent_users: int = 5
    ):
        """
        Initialize the API benchmark.
        
        Args:
            base_url: Base URL of the API
            output_dir: Directory to store benchmark results
            name: Name of the benchmark
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations
            concurrent_users: Number of concurrent users to simulate
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.name = name
        self.iterations = iterations
        self.warmup_iterations = warmup_iterations
        self.concurrent_users = concurrent_users
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.results: Dict[str, List[Dict[str, Any]]] = {}
    
    async def benchmark_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Benchmark an API endpoint.
        
        Args:
            endpoint: API endpoint to benchmark
            method: HTTP method
            data: Request data
            headers: Request headers
            name: Benchmark name
            
        Returns:
            Dictionary with benchmark results
        """
        name = name or f"{method}_{endpoint}"
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        logger.info(f"Benchmarking API endpoint: {url}")
        
        # Initialize results
        if name not in self.results:
            self.results[name] = []
        
        # Run warmup iterations
        logger.info(f"Running {self.warmup_iterations} warmup iterations...")
        for i in range(self.warmup_iterations):
            response = requests.request(method, url, json=data, headers=headers)
            response.raise_for_status()
        
        # Run benchmark iterations
        logger.info(f"Running {self.iterations} benchmark iterations with {self.concurrent_users} concurrent users...")
        
        all_iteration_results = []
        
        for i in range(self.iterations):
            # Create a thread pool for concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrent_users) as executor:
                # Submit concurrent requests
                futures = []
                for j in range(self.concurrent_users):
                    # Add a random query parameter to prevent caching
                    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    request_url = f"{url}?nocache={random_str}"
                    
                    future = executor.submit(
                        self._make_request,
                        method,
                        request_url,
                        data,
                        headers
                    )
                    futures.append(future)
                
                # Wait for all requests to complete
                iteration_results = []
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    iteration_results.append(result)
                    all_iteration_results.append(result)
            
            # Calculate statistics for this iteration
            response_times = [r["response_time"] for r in iteration_results]
            mean_time = statistics.mean(response_times)
            
            logger.info(f"Iteration {i + 1}/{self.iterations}: Mean response time: {mean_time:.4f}s")
        
        # Calculate overall statistics
        response_times = [r["response_time"] for r in all_iteration_results]
        status_codes = [r["status_code"] for r in all_iteration_results]
        
        stats = {
            "name": name,
            "endpoint": endpoint,
            "method": method,
            "iterations": self.iterations,
            "concurrent_users": self.concurrent_users,
            "total_requests": len(all_iteration_results),
            "successful_requests": sum(1 for r in all_iteration_results if r["status_code"] < 400),
            "failed_requests": sum(1 for r in all_iteration_results if r["status_code"] >= 400),
            "time_min": min(response_times),
            "time_max": max(response_times),
            "time_mean": statistics.mean(response_times),
            "time_median": statistics.median(response_times),
            "time_stdev": statistics.stdev(response_times) if len(response_times) > 1 else 0,
            "time_p95": np.percentile(response_times, 95),
            "time_p99": np.percentile(response_times, 99),
            "status_codes": {str(code): status_codes.count(code) for code in set(status_codes)},
            "timestamp": datetime.now().isoformat(),
            "iteration_results": all_iteration_results
        }
        
        # Store results
        self.results[name].append(stats)
        
        # Save results to file
        await self._save_results()
        
        # Generate charts
        self._generate_charts()
        
        logger.info(f"API benchmark complete: {name}")
        logger.info(f"Mean response time: {stats['time_mean']:.4f}s")
        logger.info(f"Requests per second: {self.concurrent_users / stats['time_mean']:.2f}")
        logger.info(f"Success rate: {stats['successful_requests'] / stats['total_requests'] * 100:.2f}%")
        
        return stats
    
    def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Make an HTTP request and measure response time.
        
        Args:
            method: HTTP method
            url: URL to request
            data: Request data
            headers: Request headers
            
        Returns:
            Dictionary with request results
        """
        start_time = time.time()
        
        try:
            response = requests.request(method, url, json=data, headers=headers)
            status_code = response.status_code
            response_size = len(response.content)
            
            try:
                response_data = response.json()
            except:
                response_data = None
        except Exception as e:
            status_code = 0
            response_size = 0
            response_data = None
        
        response_time = time.time() - start_time
        
        return {
            "response_time": response_time,
            "status_code": status_code,
            "response_size": response_size,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _save_results(self):
        """Save benchmark results to file."""
        results_file = os.path.join(self.output_dir, f"{self.name}_results.json")
        
        try:
            async with aiofiles.open(results_file, "w") as f:
                await f.write(json.dumps(self.results, indent=2))
        except Exception as e:
            logger.error(f"Error saving API benchmark results: {e}")
    
    def _generate_charts(self):
        """Generate charts from benchmark results."""
        try:
            # Create charts directory
            charts_dir = os.path.join(self.output_dir, "charts")
            os.makedirs(charts_dir, exist_ok=True)
            
            # Generate response time comparison chart
            self._generate_response_time_chart(charts_dir)
            
            # Generate throughput comparison chart
            self._generate_throughput_chart(charts_dir)
        except Exception as e:
            logger.error(f"Error generating API benchmark charts: {e}")
    
    def _generate_response_time_chart(self, charts_dir: str):
        """
        Generate response time comparison chart.
        
        Args:
            charts_dir: Directory to store charts
        """
        plt.figure(figsize=(12, 8))
        
        endpoint_names = []
        mean_times = []
        p95_times = []
        
        for name, results in self.results.items():
            if results:
                endpoint_names.append(name)
                mean_times.append(results[-1]["time_mean"])
                p95_times.append(results[-1]["time_p95"])
        
        x = np.arange(len(endpoint_names))
        width = 0.35
        
        plt.bar(x - width/2, mean_times, width, label='Mean')
        plt.bar(x + width/2, p95_times, width, label='95th Percentile')
        
        plt.xlabel('Endpoint')
        plt.ylabel('Response Time (seconds)')
        plt.title('API Response Time Comparison')
        plt.xticks(x, endpoint_names, rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        
        chart_file = os.path.join(charts_dir, f"{self.name}_response_time.png")
        plt.savefig(chart_file)
        plt.close()
    
    def _generate_throughput_chart(self, charts_dir: str):
        """
        Generate throughput comparison chart.
        
        Args:
            charts_dir: Directory to store charts
        """
        plt.figure(figsize=(12, 8))
        
        endpoint_names = []
        throughput = []
        
        for name, results in self.results.items():
            if results:
                endpoint_names.append(name)
                # Calculate requests per second
                throughput.append(self.concurrent_users / results[-1]["time_mean"])
        
        x = np.arange(len(endpoint_names))
        
        plt.bar(x, throughput, align='center', alpha=0.7)
        plt.xticks(x, endpoint_names, rotation=45, ha='right')
        plt.ylabel('Requests per Second')
        plt.title('API Throughput Comparison')
        plt.tight_layout()
        
        chart_file = os.path.join(charts_dir, f"{self.name}_throughput.png")
        plt.savefig(chart_file)
        plt.close()

async def run_benchmarks():
    """Run all benchmarks."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create output directory
    output_dir = os.path.join(os.getenv("PROJECT_DIR", ""), ".crawl4ai", "benchmarks")
    os.makedirs(output_dir, exist_ok=True)
    
    # Create benchmark instance
    benchmark = PerformanceBenchmark(
        output_dir=output_dir,
        name="wiseflow_performance",
        iterations=5,
        warmup_iterations=1
    )
    
    # Define benchmark functions
    async def benchmark_database():
        """Benchmark database operations."""
        from optimizations.database_optimizations import optimize_database
        
        # Create a temporary database for benchmarking
        db_path = os.path.join(output_dir, "benchmark.db")
        
        # Run the benchmark
        await optimize_database(db_path)
        
        # Clean up
        if os.path.exists(db_path):
            os.remove(db_path)
    
    async def benchmark_crawler():
        """Benchmark crawler operations."""
        from optimizations.crawler_optimizations import process_image_async
        
        # Create a test image
        img_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00\x00\x00\tpHYs\x00\x00\x0e\xc3\x00\x00\x0e\xc3\x01\xc7o\xa8d\x00\x00\x00\x18tEXtSoftware\x00paint.net 4.0.6\xfc\x8cc\xdf\x00\x00\x00JIDAT8Oc\xf8\xff\xff?\x03%\x80\x89\x81B@\xb1\x01\xff\x19\x18\xfe\x93\xa3\x9f\x05\xc8\xb0\x93\x1c\x03\x98\x80\x06\xfc\'\xc7\x00F\xa0\x01\xff\xc9\xd1\xcf\x02\x14\xfc\x8f\x8b\x8f\r\x0c\x03\x03\x18\x88\xd5\x8c\xce\x1f\x18\x03\x00\xf2\xc8\x11\x11\xfc\x10\xb8\xce\x00\x00\x00\x00IEND\xaeB`\x82'
        
        # Process the image
        await process_image_async(img_data)
    
    async def benchmark_llm():
        """Benchmark LLM operations."""
        from optimizations.llm_optimizations import llm_cache
        
        # Create a test prompt
        model = "gpt-3.5-turbo"
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        # Get from cache (should be a cache miss)
        result = await llm_cache.get(model, messages)
        
        # Set in cache
        await llm_cache.set(model, messages, "I'm doing well, thank you for asking!")
        
        # Get from cache again (should be a cache hit)
        result = await llm_cache.get(model, messages)
    
    async def benchmark_thread_pool():
        """Benchmark thread pool operations."""
        from optimizations.thread_pool_optimizations import adaptive_thread_pool_manager
        
        # Define a test function
        def test_function(n):
            time.sleep(0.1)
            return n * n
        
        # Submit tasks
        tasks = []
        for i in range(10):
            task_id = adaptive_thread_pool_manager.submit(test_function, i)
            tasks.append(task_id)
        
        # Wait for tasks to complete
        while any(adaptive_thread_pool_manager.get_task_status(task_id) != "completed" for task_id in tasks):
            await asyncio.sleep(0.1)
        
        # Get results
        results = [adaptive_thread_pool_manager.get_task_result(task_id) for task_id in tasks]
    
    async def benchmark_resource_monitor():
        """Benchmark resource monitor operations."""
        from optimizations.resource_monitor_optimizations import optimized_resource_monitor
        
        # Start the resource monitor
        await optimized_resource_monitor.start()
        
        # Get resource usage
        usage = optimized_resource_monitor.get_resource_usage()
        
        # Stop the resource monitor
        await optimized_resource_monitor.stop()
    
    async def benchmark_dashboard():
        """Benchmark dashboard operations."""
        from optimizations.dashboard_optimizations import dashboard_optimizer
        
        # Create test data
        data = [{"id": i, "name": f"Item {i}", "value": i * 10} for i in range(100)]
        
        # Paginate data
        paginated = await dashboard_optimizer.paginate_data(data, page=1, items_per_page=20)
        
        # Filter data
        filtered = dashboard_optimizer.filter_data(data, {"value": [10, 20, 30]})
        
        # Sort data
        sorted_data = dashboard_optimizer.sort_data(data, "value", "desc")
    
    # Run benchmarks
    await benchmark.run_benchmark(benchmark_database, "database")
    await benchmark.run_benchmark(benchmark_crawler, "crawler")
    await benchmark.run_benchmark(benchmark_llm, "llm")
    await benchmark.run_benchmark(benchmark_thread_pool, "thread_pool")
    await benchmark.run_benchmark(benchmark_resource_monitor, "resource_monitor")
    await benchmark.run_benchmark(benchmark_dashboard, "dashboard")
    
    logger.info("All benchmarks completed")

if __name__ == "__main__":
    asyncio.run(run_benchmarks())

