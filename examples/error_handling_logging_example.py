#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example script demonstrating the improved error handling and logging in WiseFlow.

This script shows how to use the various error handling and logging utilities
provided by WiseFlow to create robust and well-logged applications.
"""

import os
import sys
import time
import asyncio
import random
from typing import Dict, Any, List, Optional

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import WiseFlow utilities
from core.utils.logging_config import (
    logger, get_logger, with_context, LogContext,
    log_execution, log_method_calls, configure_logging
)
from core.utils.error_handling import (
    WiseflowError, ValidationError, ConnectionError, DataProcessingError,
    handle_exceptions, ErrorHandler, async_error_handler, retry,
    log_error, save_error_to_file
)

# Configure logging for this example
configure_logging(
    log_level="DEBUG",
    log_to_console=True,
    log_to_file=True,
    app_name="error_handling_example",
    structured_logging=False,
    enhanced_format=True
)

# Get a logger for this module
example_logger = get_logger("error_handling_example")

# Example data
SAMPLE_DATA = {
    "users": [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
    ],
    "products": [
        {"id": 101, "name": "Laptop", "price": 999.99},
        {"id": 102, "name": "Phone", "price": 499.99},
        {"id": 103, "name": "Tablet", "price": 299.99}
    ]
}

# Example 1: Basic error handling with WiseflowError classes
def validate_user(user_data: Dict[str, Any]) -> bool:
    """
    Validate user data.
    
    Args:
        user_data: User data to validate
        
    Returns:
        True if the user data is valid
        
    Raises:
        ValidationError: If the user data is invalid
    """
    if not isinstance(user_data, dict):
        raise ValidationError("User data must be a dictionary", {"provided_type": type(user_data).__name__})
    
    required_fields = ["id", "name", "email"]
    for field in required_fields:
        if field not in user_data:
            raise ValidationError(f"Missing required field: {field}", {"user_data": user_data})
    
    if not isinstance(user_data["id"], int):
        raise ValidationError("User ID must be an integer", {"provided_id": user_data["id"]})
    
    if not isinstance(user_data["name"], str) or not user_data["name"]:
        raise ValidationError("User name must be a non-empty string", {"provided_name": user_data["name"]})
    
    if not isinstance(user_data["email"], str) or "@" not in user_data["email"]:
        raise ValidationError("User email must be a valid email address", {"provided_email": user_data["email"]})
    
    return True

# Example 2: Using the handle_exceptions decorator
@handle_exceptions(
    error_types=[ValidationError, KeyError, TypeError],
    default_message="Failed to process user",
    log_error=True,
    reraise=False,
    default_return=None
)
def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a user by ID.
    
    Args:
        user_id: User ID to look up
        
    Returns:
        User data if found, None otherwise
    """
    if not isinstance(user_id, int):
        raise ValidationError("User ID must be an integer", {"provided_id": user_id})
    
    for user in SAMPLE_DATA["users"]:
        if user["id"] == user_id:
            return user
    
    raise ValidationError(f"User not found with ID: {user_id}")

# Example 3: Using the retry decorator
@retry(
    max_retries=3,
    retry_delay=1,
    retry_backoff=2.0,
    retry_exceptions=[ConnectionError, TimeoutError],
    retry_condition=lambda e: isinstance(e, ConnectionError) and random.random() < 0.7
)
def fetch_external_api(url: str) -> Dict[str, Any]:
    """
    Fetch data from an external API.
    
    Args:
        url: URL to fetch data from
        
    Returns:
        API response data
        
    Raises:
        ConnectionError: If the API request fails
    """
    example_logger.info(f"Fetching data from {url}")
    
    # Simulate API request with random failure
    if random.random() < 0.7:
        raise ConnectionError(
            f"Failed to connect to API: {url}",
            {"url": url, "attempt": time.time()},
            retry_after=1
        )
    
    # Simulate successful API response
    return {"status": "success", "data": {"timestamp": time.time()}}

# Example 4: Using the ErrorHandler context manager
def process_product(product_id: int) -> Dict[str, Any]:
    """
    Process a product by ID.
    
    Args:
        product_id: Product ID to process
        
    Returns:
        Processed product data
    """
    with ErrorHandler(
        error_types=[ValidationError, KeyError, TypeError],
        default={"status": "error", "message": "Failed to process product"},
        log_error=True,
        context={"product_id": product_id}
    ) as handler:
        # Find the product
        product = None
        for p in SAMPLE_DATA["products"]:
            if p["id"] == product_id:
                product = p
                break
        
        if not product:
            raise ValidationError(f"Product not found with ID: {product_id}")
        
        # Process the product
        processed_product = {
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "price_with_tax": product["price"] * 1.1,
            "currency": "USD",
            "in_stock": True
        }
        
        return processed_product
    
    # If we get here, an error occurred
    if handler.error_occurred:
        example_logger.warning(f"Error processing product {product_id}: {handler.error}")
    
    return handler.result

# Example 5: Using async_error_handler for async functions
async def fetch_user_async(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a user asynchronously.
    
    Args:
        user_id: User ID to fetch
        
    Returns:
        User data if found, None otherwise
    """
    # Simulate async operation
    await asyncio.sleep(0.1)
    
    # Simulate random failure
    if random.random() < 0.3:
        raise ConnectionError(f"Failed to fetch user with ID: {user_id}")
    
    # Find the user
    for user in SAMPLE_DATA["users"]:
        if user["id"] == user_id:
            return user
    
    raise ValidationError(f"User not found with ID: {user_id}")

async def process_users_async(user_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Process multiple users asynchronously.
    
    Args:
        user_ids: List of user IDs to process
        
    Returns:
        List of processed user data
    """
    results = []
    
    for user_id in user_ids:
        user = await async_error_handler(
            fetch_user_async(user_id),
            error_types=[ConnectionError, ValidationError],
            default=None,
            log_error=True,
            retry_count=2,
            retry_delay=0.5,
            context={"user_id": user_id}
        )
        
        if user:
            results.append(user)
    
    return results

# Example 6: Using log_execution decorator
@log_execution(log_args=True, log_result=True, level="INFO")
def calculate_total_price(products: List[Dict[str, Any]]) -> float:
    """
    Calculate the total price of products.
    
    Args:
        products: List of products
        
    Returns:
        Total price
    """
    return sum(product["price"] for product in products)

# Example 7: Using log_method_calls decorator
@log_method_calls(exclude=["__init__"], level="DEBUG")
class UserService:
    """Service for managing users."""
    
    def __init__(self):
        """Initialize the user service."""
        self.users = SAMPLE_DATA["users"]
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID to look up
            
        Returns:
            User data if found, None otherwise
        """
        for user in self.users:
            if user["id"] == user_id:
                return user
        return None
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            user_data: User data to create
            
        Returns:
            Created user data
        """
        # Validate user data
        validate_user(user_data)
        
        # Check if user already exists
        for user in self.users:
            if user["id"] == user_data["id"]:
                raise ValidationError(f"User already exists with ID: {user_data['id']}")
        
        # Add user
        self.users.append(user_data)
        return user_data
    
    def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a user.
        
        Args:
            user_id: User ID to update
            user_data: User data to update
            
        Returns:
            Updated user data if found, None otherwise
        """
        for i, user in enumerate(self.users):
            if user["id"] == user_id:
                # Update user
                updated_user = {**user, **user_data}
                self.users[i] = updated_user
                return updated_user
        return None

# Example 8: Using LogContext for structured logging
def process_order(order_id: str, user_id: int, products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process an order.
    
    Args:
        order_id: Order ID
        user_id: User ID
        products: List of products
        
    Returns:
        Processed order data
    """
    with LogContext(order_id=order_id, user_id=user_id, product_count=len(products)):
        logger.info("Processing order")
        
        # Get user
        user = get_user_by_id(user_id)
        if not user:
            logger.error(f"User not found with ID: {user_id}")
            return {"status": "error", "message": "User not found"}
        
        # Calculate total
        total = calculate_total_price(products)
        
        # Create order
        order = {
            "id": order_id,
            "user": user,
            "products": products,
            "total": total,
            "status": "processed",
            "timestamp": time.time()
        }
        
        logger.info(f"Order processed successfully with total: {total}")
        return order

# Main function to run the examples
async def main():
    """Run the examples."""
    example_logger.info("Starting error handling and logging examples")
    
    # Example 1: Basic error handling with WiseflowError classes
    example_logger.info("Example 1: Basic error handling with WiseflowError classes")
    try:
        validate_user(SAMPLE_DATA["users"][0])
        example_logger.info("User validation successful")
    except ValidationError as e:
        log_error(e)
    
    try:
        validate_user("not a user")
        example_logger.info("User validation successful")
    except ValidationError as e:
        log_error(e)
    
    # Example 2: Using the handle_exceptions decorator
    example_logger.info("Example 2: Using the handle_exceptions decorator")
    user = get_user_by_id(1)
    example_logger.info(f"Found user: {user}")
    
    user = get_user_by_id("not an id")
    example_logger.info(f"Result with invalid ID: {user}")
    
    user = get_user_by_id(999)
    example_logger.info(f"Result with non-existent ID: {user}")
    
    # Example 3: Using the retry decorator
    example_logger.info("Example 3: Using the retry decorator")
    try:
        result = fetch_external_api("https://api.example.com/data")
        example_logger.info(f"API result: {result}")
    except ConnectionError as e:
        log_error(e)
    
    # Example 4: Using the ErrorHandler context manager
    example_logger.info("Example 4: Using the ErrorHandler context manager")
    product = process_product(101)
    example_logger.info(f"Processed product: {product}")
    
    product = process_product(999)
    example_logger.info(f"Result with non-existent product ID: {product}")
    
    # Example 5: Using async_error_handler for async functions
    example_logger.info("Example 5: Using async_error_handler for async functions")
    users = await process_users_async([1, 2, 3, 999])
    example_logger.info(f"Processed users: {users}")
    
    # Example 6: Using log_execution decorator
    example_logger.info("Example 6: Using log_execution decorator")
    total = calculate_total_price(SAMPLE_DATA["products"])
    example_logger.info(f"Total price: {total}")
    
    # Example 7: Using log_method_calls decorator
    example_logger.info("Example 7: Using log_method_calls decorator")
    user_service = UserService()
    user = user_service.get_user(1)
    example_logger.info(f"Found user: {user}")
    
    try:
        new_user = user_service.create_user({
            "id": 4,
            "name": "Dave",
            "email": "dave@example.com"
        })
        example_logger.info(f"Created user: {new_user}")
    except ValidationError as e:
        log_error(e)
    
    updated_user = user_service.update_user(1, {"name": "Alice Smith"})
    example_logger.info(f"Updated user: {updated_user}")
    
    # Example 8: Using LogContext for structured logging
    example_logger.info("Example 8: Using LogContext for structured logging")
    order = process_order("ORD-123", 1, SAMPLE_DATA["products"])
    example_logger.info(f"Processed order: {order}")
    
    example_logger.info("All examples completed")

if __name__ == "__main__":
    asyncio.run(main())

