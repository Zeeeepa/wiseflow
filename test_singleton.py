import threading
import time
from core.utils.singleton import Singleton

class TestSingleton(Singleton):
    def __init__(self, value=None):
        # Skip initialization if already initialized
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.value = value or "default"
        print(f"Initializing TestSingleton with value: {self.value}")

def test_singleton_instance():
    # First instance
    instance1 = TestSingleton(value="test1")
    print(f"Instance 1 value: {instance1.value}")
    
    # Second instance should be the same object
    instance2 = TestSingleton(value="test2")
    print(f"Instance 2 value: {instance2.value}")
    
    # Check if they are the same object
    print(f"Are instances the same object? {instance1 is instance2}")
    print(f"Final value: {instance1.value}")

def create_instance(thread_id):
    instance = TestSingleton(value=f"thread-{thread_id}")
    print(f"Thread {thread_id} got instance with value: {instance.value}")

def test_thread_safety():
    threads = []
    for i in range(10):
        thread = threading.Thread(target=create_instance, args=(i,))
        threads.append(thread)
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Get the final instance
    final_instance = TestSingleton()
    print(f"Final instance value after all threads: {final_instance.value}")

if __name__ == "__main__":
    print("Testing basic singleton functionality:")
    test_singleton_instance()
    
    print("\nTesting thread safety:")
    # Reset the singleton instances
    TestSingleton._instances = {}
    test_thread_safety()
