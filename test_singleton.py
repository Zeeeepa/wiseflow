import threading
import time
import unittest
from core.utils.singleton import Singleton

class TestSingleton(Singleton):
    def __init__(self, value=None):
        # Skip initialization if already initialized
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.value = value or "default"
        print(f"Initializing TestSingleton with value: {self.value}")

class AnotherSingleton(Singleton):
    def __init__(self, name=None):
        # Skip initialization if already initialized
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.name = name or "default_name"
        print(f"Initializing AnotherSingleton with name: {self.name}")

class SingletonTests(unittest.TestCase):
    def setUp(self):
        # Reset singleton instances before each test
        TestSingleton.reset_instance()
        AnotherSingleton.reset_instance()
    
    def test_basic_singleton(self):
        """Test that multiple instantiations return the same instance."""
        print("\nTest: Basic Singleton")
        instance1 = TestSingleton(value="test1")
        instance2 = TestSingleton(value="test2")
        
        self.assertIs(instance1, instance2, "Instances should be the same object")
        self.assertEqual(instance1.value, "test1", "Value should be from first initialization")
        print("✓ Basic singleton test passed")
    
    def test_get_instance_method(self):
        """Test that get_instance method returns the same instance."""
        print("\nTest: get_instance Method")
        instance1 = TestSingleton(value="test1")
        instance2 = TestSingleton.get_instance(value="test2")
        
        self.assertIs(instance1, instance2, "Direct instantiation and get_instance should return same object")
        print("✓ get_instance method test passed")
    
    def test_multiple_singleton_classes(self):
        """Test that different singleton classes have separate instances."""
        print("\nTest: Multiple Singleton Classes")
        test_instance = TestSingleton(value="test_value")
        another_instance = AnotherSingleton(name="another_name")
        
        self.assertIsNot(test_instance, another_instance, "Different singleton classes should have different instances")
        self.assertEqual(test_instance.value, "test_value")
        self.assertEqual(another_instance.name, "another_name")
        print("✓ Multiple singleton classes test passed")
    
    def test_thread_safety(self):
        """Test thread safety of singleton creation."""
        print("\nTest: Thread Safety")
        # This will store any exceptions raised in threads
        exceptions = []
        # This will store the instances created in each thread
        instances = []
        
        def create_instance(thread_id):
            try:
                instance = TestSingleton(value=f"thread-{thread_id}")
                instances.append(instance)
            except Exception as e:
                exceptions.append(e)
        
        # Create and start threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_instance, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check for exceptions
        self.assertEqual(len(exceptions), 0, f"Threads raised exceptions: {exceptions}")
        
        # Check that all instances are the same object
        first_instance = instances[0]
        for instance in instances[1:]:
            self.assertIs(instance, first_instance, "All instances from threads should be the same object")
        
        # Check that the value is from the first thread that succeeded
        self.assertTrue(first_instance.value.startswith("thread-"), 
                        f"Instance value should start with 'thread-', got {first_instance.value}")
        print("✓ Thread safety test passed")
    
    def test_reset_instance(self):
        """Test that reset_instance allows creating a new instance."""
        print("\nTest: Reset Instance")
        instance1 = TestSingleton(value="test1")
        self.assertEqual(instance1.value, "test1")
        
        # Reset the instance
        reset_result = TestSingleton.reset_instance()
        self.assertTrue(reset_result, "reset_instance should return True when an instance was reset")
        
        # Create a new instance
        instance2 = TestSingleton(value="test2")
        self.assertEqual(instance2.value, "test2", "After reset, a new instance should be created with new values")
        
        # Try resetting when no instance exists
        TestSingleton.reset_instance()
        reset_result = TestSingleton.reset_instance()
        self.assertFalse(reset_result, "reset_instance should return False when no instance exists")
        
        print("✓ Reset instance test passed")

def manual_test():
    """Run manual tests with print statements for visual verification."""
    print("\n=== Manual Tests ===")
    print("Testing basic singleton functionality:")
    instance1 = TestSingleton(value="test1")
    print(f"Instance 1 value: {instance1.value}")
    
    instance2 = TestSingleton(value="test2")
    print(f"Instance 2 value: {instance2.value}")
    
    print(f"Are instances the same object? {instance1 is instance2}")
    print(f"Final value: {instance1.value}")
    
    print("\nTesting reset_instance:")
    reset_result = TestSingleton.reset_instance()
    print(f"Reset result: {reset_result}")
    
    instance3 = TestSingleton(value="test3")
    print(f"New instance after reset, value: {instance3.value}")
    
    print("\nTesting thread safety:")
    # Reset the singleton instances
    TestSingleton.reset_instance()
    
    threads = []
    for i in range(10):
        thread = threading.Thread(target=lambda i: print(f"Thread {i} got instance with value: {TestSingleton(value=f'thread-{i}').value}"), args=(i,))
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
    print("=== Running Unit Tests ===")
    # Run the unit tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    
    # Run manual tests
    manual_test()
