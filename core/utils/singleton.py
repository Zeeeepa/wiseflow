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
    _lock = threading.RLock()  # Using RLock instead of Lock for reentrant safety
    
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
                instance = super(Singleton, cls).__new__(cls)
                instance.__init__(*args, **kwargs)
                # Set a flag to prevent __init__ from being called again
                instance._initialized = True
                cls._instances[cls] = instance
            return cls._instances[cls]
    
    @classmethod
    def reset_instance(cls):
        """
        Reset the singleton instance.
        
        This method is primarily used for testing purposes.
        It removes the singleton instance from the instances dictionary,
        allowing a new instance to be created on the next call to get_instance.
        
        Returns:
            bool: True if an instance was reset, False if no instance existed.
        """
        with cls._lock:
            if cls in cls._instances:
                del cls._instances[cls]
                return True
            return False
