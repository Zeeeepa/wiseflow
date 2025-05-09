#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency Injection Container for WiseFlow.

This module provides a centralized dependency injection container for managing
service dependencies throughout the application. It supports registration,
resolution, and lifecycle management of services.
"""

import inspect
import logging
from typing import Dict, Any, Optional, Type, Callable, TypeVar, cast, get_type_hints

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ServiceNotFoundException(Exception):
    """Exception raised when a requested service is not found in the container."""
    pass

class CircularDependencyException(Exception):
    """Exception raised when a circular dependency is detected."""
    pass

class ServiceLifetime:
    """Service lifetime options."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"

class ServiceRegistration:
    """Registration information for a service."""
    
    def __init__(
        self,
        service_type: Type,
        implementation_type: Optional[Type] = None,
        factory: Optional[Callable[['DIContainer'], Any]] = None,
        instance: Optional[Any] = None,
        lifetime: str = ServiceLifetime.TRANSIENT
    ):
        """
        Initialize a service registration.
        
        Args:
            service_type: The type of the service (usually an interface)
            implementation_type: The implementation type (concrete class)
            factory: Factory function to create the service
            instance: Existing instance of the service
            lifetime: Lifetime of the service (singleton, transient, scoped)
        """
        self.service_type = service_type
        self.implementation_type = implementation_type
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime
        
        # Validate registration
        if not any([implementation_type, factory, instance]):
            raise ValueError("At least one of implementation_type, factory, or instance must be provided")
        
        if instance and lifetime != ServiceLifetime.SINGLETON:
            logger.warning(f"Service {service_type.__name__} has an instance but lifetime is not singleton")

class DIContainer:
    """
    Dependency Injection Container for WiseFlow.
    
    This class provides a centralized container for managing service dependencies
    throughout the application. It supports registration, resolution, and lifecycle
    management of services.
    """
    
    def __init__(self):
        """Initialize the container."""
        self._registrations: Dict[Type, ServiceRegistration] = {}
        self._resolving: Dict[Type, bool] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
        self._current_scope: Optional[str] = None
    
    def register(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type] = None,
        lifetime: str = ServiceLifetime.TRANSIENT
    ) -> None:
        """
        Register a service with its implementation.
        
        Args:
            service_type: The type of the service (usually an interface)
            implementation_type: The implementation type (concrete class)
            lifetime: Lifetime of the service (singleton, transient, scoped)
        """
        if implementation_type is None:
            implementation_type = service_type
            
        self._registrations[service_type] = ServiceRegistration(
            service_type=service_type,
            implementation_type=implementation_type,
            lifetime=lifetime
        )
        
        logger.debug(f"Registered {service_type.__name__} with implementation {implementation_type.__name__}")
    
    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """
        Register an existing instance of a service.
        
        Args:
            service_type: The type of the service
            instance: The instance to register
        """
        self._registrations[service_type] = ServiceRegistration(
            service_type=service_type,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON
        )
        
        logger.debug(f"Registered instance of {service_type.__name__}")
    
    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[['DIContainer'], T],
        lifetime: str = ServiceLifetime.TRANSIENT
    ) -> None:
        """
        Register a factory function for creating a service.
        
        Args:
            service_type: The type of the service
            factory: Factory function to create the service
            lifetime: Lifetime of the service (singleton, transient, scoped)
        """
        self._registrations[service_type] = ServiceRegistration(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime
        )
        
        logger.debug(f"Registered factory for {service_type.__name__}")
    
    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service from the container.
        
        Args:
            service_type: The type of the service to resolve
            
        Returns:
            An instance of the requested service
            
        Raises:
            ServiceNotFoundException: If the service is not registered
            CircularDependencyException: If a circular dependency is detected
        """
        # Check if the service is registered
        if service_type not in self._registrations:
            raise ServiceNotFoundException(f"Service {service_type.__name__} is not registered")
        
        # Get the registration
        registration = self._registrations[service_type]
        
        # Check for circular dependencies
        if service_type in self._resolving and self._resolving[service_type]:
            raise CircularDependencyException(f"Circular dependency detected for {service_type.__name__}")
        
        # Mark as resolving
        self._resolving[service_type] = True
        
        try:
            # Return existing instance for singletons
            if registration.lifetime == ServiceLifetime.SINGLETON and registration.instance is not None:
                return cast(T, registration.instance)
            
            # Return existing instance for scoped services
            if (
                registration.lifetime == ServiceLifetime.SCOPED
                and self._current_scope is not None
                and service_type in self._scoped_instances.get(self._current_scope, {})
            ):
                return cast(T, self._scoped_instances[self._current_scope][service_type])
            
            # Create a new instance
            instance = self._create_instance(registration)
            
            # Store singleton instances
            if registration.lifetime == ServiceLifetime.SINGLETON:
                registration.instance = instance
            
            # Store scoped instances
            if registration.lifetime == ServiceLifetime.SCOPED and self._current_scope is not None:
                if self._current_scope not in self._scoped_instances:
                    self._scoped_instances[self._current_scope] = {}
                self._scoped_instances[self._current_scope][service_type] = instance
            
            return cast(T, instance)
        finally:
            # Mark as no longer resolving
            self._resolving[service_type] = False
    
    def _create_instance(self, registration: ServiceRegistration) -> Any:
        """
        Create an instance of a service.
        
        Args:
            registration: The service registration
            
        Returns:
            An instance of the service
        """
        # Use factory if provided
        if registration.factory is not None:
            return registration.factory(self)
        
        # Use implementation type
        if registration.implementation_type is not None:
            # Get constructor parameters
            constructor = registration.implementation_type.__init__
            if constructor is object.__init__:
                # No constructor parameters
                return registration.implementation_type()
            
            # Get parameter types
            type_hints = get_type_hints(constructor)
            signature = inspect.signature(constructor)
            
            # Resolve dependencies
            args = {}
            for name, param in signature.parameters.items():
                if name == 'self':
                    continue
                
                # Get parameter type
                param_type = type_hints.get(name, Any)
                
                # Skip optional parameters with default values
                if param.default is not inspect.Parameter.empty:
                    continue
                
                # Resolve the dependency
                try:
                    args[name] = self.resolve(param_type)
                except ServiceNotFoundException:
                    logger.warning(f"Could not resolve parameter {name} of type {param_type} for {registration.implementation_type.__name__}")
                    # If the parameter is optional, skip it
                    if param.default is not inspect.Parameter.empty:
                        continue
                    raise
            
            # Create the instance
            return registration.implementation_type(**args)
        
        # Should not reach here
        raise ValueError("Invalid service registration")
    
    def create_scope(self, scope_id: str) -> 'DIScope':
        """
        Create a new dependency injection scope.
        
        Args:
            scope_id: Unique identifier for the scope
            
        Returns:
            A new scope
        """
        return DIScope(self, scope_id)
    
    def begin_scope(self, scope_id: str) -> None:
        """
        Begin a new scope.
        
        Args:
            scope_id: Unique identifier for the scope
        """
        self._current_scope = scope_id
        if scope_id not in self._scoped_instances:
            self._scoped_instances[scope_id] = {}
    
    def end_scope(self, scope_id: str) -> None:
        """
        End a scope and dispose of its instances.
        
        Args:
            scope_id: Unique identifier for the scope
        """
        if self._current_scope == scope_id:
            self._current_scope = None
        
        if scope_id in self._scoped_instances:
            # Dispose of instances that implement IDisposable
            for instance in self._scoped_instances[scope_id].values():
                if hasattr(instance, 'dispose') and callable(getattr(instance, 'dispose')):
                    try:
                        instance.dispose()
                    except Exception as e:
                        logger.error(f"Error disposing instance: {e}")
            
            del self._scoped_instances[scope_id]

class DIScope:
    """
    Dependency Injection Scope.
    
    This class represents a scope for dependency injection, allowing scoped
    services to be created and disposed of together.
    """
    
    def __init__(self, container: DIContainer, scope_id: str):
        """
        Initialize a new scope.
        
        Args:
            container: The parent container
            scope_id: Unique identifier for the scope
        """
        self.container = container
        self.scope_id = scope_id
    
    def __enter__(self) -> 'DIScope':
        """Enter the scope context."""
        self.container.begin_scope(self.scope_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the scope context and dispose of instances."""
        self.container.end_scope(self.scope_id)
    
    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service from the container within this scope.
        
        Args:
            service_type: The type of the service to resolve
            
        Returns:
            An instance of the requested service
        """
        return self.container.resolve(service_type)

# Create a singleton instance
container = DIContainer()

def get_container() -> DIContainer:
    """
    Get the global container instance.
    
    Returns:
        The global container instance
    """
    return container

