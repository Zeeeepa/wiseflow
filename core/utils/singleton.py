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
                cls._instances[cls] = cls(*args, **kwargs)
        return cls._instances[cls]

