import os
import time
import psutil
from typing import Dict, List, Callable, Optional, Tuple, Any
import threading
import logging

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """
    A class for monitoring system resources including CPU, memory, disk, and IO usage.
    Provides methods to track resource usage, set thresholds, and trigger callbacks when thresholds are exceeded.
    """
    
    def __init__(self, 
                 check_interval: float = 5.0,
                 cpu_threshold: float = 80.0,
                 memory_threshold: float = 80.0,
                 disk_threshold: float = 80.0,
                 io_threshold: float = 80.0,
                 history_size: int = 60):
        """
        Initialize the ResourceMonitor with configurable thresholds and check interval.
        
        Args:
            check_interval: Time in seconds between resource checks
            cpu_threshold: CPU usage percentage threshold (0-100)
            memory_threshold: Memory usage percentage threshold (0-100)
            disk_threshold: Disk usage percentage threshold (0-100)
            io_threshold: IO usage percentage threshold (0-100)
            history_size: Number of historical data points to keep
        """
        self.check_interval = check_interval
        self.thresholds = {
            'cpu': cpu_threshold,
            'memory': memory_threshold,
            'disk': disk_threshold,
            'io': io_threshold
        }
        
        self.history = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'io': [],
            'timestamp': []
        }
        
        self.history_size = history_size
        self.callbacks = []
        self._stop_event = threading.Event()
        self._monitor_thread = None
        self.last_io_counters = psutil.disk_io_counters()
        self.last_io_time = time.time()
    
    def start(self):
        """Start the resource monitoring thread."""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
            self._monitor_thread.start()
            logger.info("Resource monitoring started")
    
    def stop(self):
        """Stop the resource monitoring thread."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._stop_event.set()
            self._monitor_thread.join(timeout=self.check_interval + 1)
            logger.info("Resource monitoring stopped")
    
    def add_callback(self, callback: Callable[[str, float, float], None]):
        """
        Add a callback function to be called when a resource threshold is exceeded.
        
        Args:
            callback: Function that takes (resource_type, current_value, threshold_value)
        """
        self.callbacks.append(callback)
    
    def get_current_usage(self) -> Dict[str, float]:
        """
        Get the current resource usage.
        
        Returns:
            Dictionary with current usage percentages for cpu, memory, disk, and io
        """
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        # Calculate IO usage based on read/write operations
        current_io_counters = psutil.disk_io_counters()
        current_time = time.time()
        
        io_delta = sum([
            current_io_counters.read_bytes - self.last_io_counters.read_bytes,
            current_io_counters.write_bytes - self.last_io_counters.write_bytes
        ])
        
        time_delta = current_time - self.last_io_time
        io_rate = io_delta / time_delta if time_delta > 0 else 0
        
        # Normalize IO rate to a percentage (assuming 100MB/s is 100%)
        max_io_rate = 100 * 1024 * 1024  # 100 MB/s
        io_percent = min(100.0, (io_rate / max_io_rate) * 100)
        
        self.last_io_counters = current_io_counters
        self.last_io_time = current_time
        
        return {
            'cpu': cpu,
            'memory': memory,
            'disk': disk,
            'io': io_percent
        }
    
    def get_history(self) -> Dict[str, List[float]]:
        """
        Get the historical resource usage data.
        
        Returns:
            Dictionary with lists of historical values for each resource type
        """
        return self.history
    
    def calculate_optimal_thread_count(self) -> int:
        """
        Calculate the optimal number of threads based on current system load.
        
        Returns:
            Recommended number of worker threads
        """
        # Get current CPU and memory usage
        usage = self.get_current_usage()
        cpu_usage = usage['cpu']
        memory_usage = usage['memory']
        
        # Get system information
        cpu_count = os.cpu_count() or 4
        
        # Base calculation on CPU count
        if cpu_usage > 90:
            # System is heavily loaded, use minimal threads
            optimal_count = max(1, int(cpu_count * 0.25))
        elif cpu_usage > 70:
            # System is moderately loaded
            optimal_count = max(1, int(cpu_count * 0.5))
        elif cpu_usage > 50:
            # System has moderate load
            optimal_count = max(1, int(cpu_count * 0.75))
        else:
            # System has light load, use full capacity
            optimal_count = cpu_count
        
        # Adjust based on memory pressure
        if memory_usage > 90:
            optimal_count = max(1, int(optimal_count * 0.5))
        elif memory_usage > 80:
            optimal_count = max(1, int(optimal_count * 0.75))
        
        return optimal_count
    
    def _monitor_resources(self):
        """Internal method to continuously monitor resources."""
        while not self._stop_event.is_set():
            try:
                usage = self.get_current_usage()
                timestamp = time.time()
                
                # Update history
                for resource_type, value in usage.items():
                    self.history[resource_type].append(value)
                    # Trim history if it exceeds the maximum size
                    if len(self.history[resource_type]) > self.history_size:
                        self.history[resource_type].pop(0)
                
                self.history['timestamp'].append(timestamp)
                if len(self.history['timestamp']) > self.history_size:
                    self.history['timestamp'].pop(0)
                
                # Check thresholds and trigger callbacks
                for resource_type, value in usage.items():
                    threshold = self.thresholds.get(resource_type)
                    if threshold and value > threshold:
                        for callback in self.callbacks:
                            try:
                                callback(resource_type, value, threshold)
                            except Exception as e:
                                logger.error(f"Error in resource callback: {e}")
                
                # Sleep until next check
                self._stop_event.wait(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")
                # Sleep a bit before retrying
                self._stop_event.wait(self.check_interval)
    
    def update_thresholds(self, **kwargs):
        """
        Update resource thresholds.
        
        Args:
            **kwargs: Threshold values to update (cpu, memory, disk, io)
        """
        for resource_type, value in kwargs.items():
            if resource_type in self.thresholds and isinstance(value, (int, float)):
                self.thresholds[resource_type] = float(value)
    
    def get_thresholds(self) -> Dict[str, float]:
        """
        Get the current threshold values.
        
        Returns:
            Dictionary with current threshold values
        """
        return self.thresholds.copy()


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Example callback function
    def resource_alert(resource_type, current_value, threshold):
        logger.warning(f"Resource alert: {resource_type} usage at {current_value:.1f}% (threshold: {threshold}%)")
    
    # Create and start the resource monitor
    monitor = ResourceMonitor(
        check_interval=2.0,
        cpu_threshold=70.0,
        memory_threshold=80.0
    )
    
    # Add the callback
    monitor.add_callback(resource_alert)
    
    # Start monitoring
    monitor.start()
    
    try:
        # Run for 30 seconds as an example
        for _ in range(15):
            # Get and print current usage
            usage = monitor.get_current_usage()
            print(f"CPU: {usage['cpu']:.1f}%, Memory: {usage['memory']:.1f}%, "
                  f"Disk: {usage['disk']:.1f}%, IO: {usage['io']:.1f}%")
            
            # Calculate optimal thread count
            optimal_threads = monitor.calculate_optimal_thread_count()
            print(f"Optimal thread count: {optimal_threads}")
            
            time.sleep(2)
    
    finally:
        # Stop monitoring
        monitor.stop()
