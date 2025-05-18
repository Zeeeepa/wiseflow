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
                cls._instances[cls] = super(Singleton, cls).__new__(cls)
                cls._instances[cls].__init__(*args, **kwargs)
                # Set a flag to prevent __init__ from being called again
                cls._instances[cls]._initialized = True
        return cls._instances[cls]
