import threading

class Singleton:
    """
    A thread-safe singleton base class.
    
    This class implements the singleton pattern, ensuring that only one instance
    of a class exists throughout the application. It uses a thread lock to ensure
    thread safety when creating instances.
    
    Usage:
        class MyClass(Singleton):
            def __init__(self, *args, **kwargs):
                # Skip initialization if already initialized
                if hasattr(self, '_initialized') and self._initialized:
                    return
                    
                # Your initialization code here
                pass
                
        # Get the singleton instance
        instance = MyClass.get_instance(*args, **kwargs)
        # or
        instance = MyClass(*args, **kwargs)  # This will call get_instance internally
    """
    _instances = {}
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """
        Override __new__ to implement the singleton pattern.
        
        This ensures that even direct instantiation (e.g., MyClass()) will use
        the singleton instance.
        
        Args:
            *args: Variable length argument list to pass to the constructor.
            **kwargs: Arbitrary keyword arguments to pass to the constructor.
            
        Returns:
            The singleton instance of the class.
        """
        return cls.get_instance(*args, **kwargs)
    
    @classmethod
    def get_instance(cls, *args, **kwargs):
        """
        Get or create the singleton instance of the class.
        
        Args:
            *args: Variable length argument list to pass to the constructor.
            **kwargs: Arbitrary keyword arguments to pass to the constructor.
            
        Returns:
            The singleton instance of the class.
        """
        with cls._lock:
            if cls not in cls._instances:
                # Create a new instance without calling __init__
                instance = super(Singleton, cls).__new__(cls)
                # Set the _initialized flag to False before initialization
                instance._initialized = False
                # Store the instance before initialization to prevent recursion
                cls._instances[cls] = instance
                # Now call __init__ which will check the _initialized flag
                instance.__init__(*args, **kwargs)
                # Set the flag to True after initialization
                instance._initialized = True
                return instance
            return cls._instances[cls]
