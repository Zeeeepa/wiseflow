#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example usage of the WiseFlow error handling and logging system.

This file demonstrates how to use the error handling and logging system in WiseFlow.
"""

import asyncio
import random
from typing import Dict, List, Any, Optional

# Import logging and error handling utilities
from core.utils.logging_config import logger, get_logger, with_context, LogContext
from core.utils.error_handling import (
    WiseflowError,
    ConnectionError,
    DataProcessingError,
    ValidationError,
    handle_exceptions,
    ErrorHandler,
    async_error_handler,
    log_error
)

# Get a module-specific logger
module_logger = get_logger(__name__)

# Example 1: Basic logging
def basic_logging_example():
    """Demonstrate basic logging functionality."""
    module_logger.info("Starting basic logging example")
    
    module_logger.debug("This is a debug message")
    module_logger.info("This is an info message")
    module_logger.success("This is a success message")
    module_logger.warning("This is a warning message")
    module_logger.error("This is an error message")
    module_logger.critical("This is a critical message")
    
    module_logger.info("Finished basic logging example")

# Example 2: Contextual logging
def contextual_logging_example(user_id: str, action: str):
    """
    Demonstrate contextual logging.
    
    Args:
        user_id: User ID for context
        action: Action being performed
    """
    module_logger.info("Starting contextual logging example")
    
    # Add context to logger
    user_logger = with_context(user_id=user_id, action=action)
    
    user_logger.info("User action started")
    
    # Use context manager for temporary context
    with LogContext(request_id="req-123", endpoint="/api/data"):
        logger.info("Processing request")
        logger.debug("Request details: ...")
        logger.success("Request processed successfully")
    
    user_logger.success("User action completed")
    
    module_logger.info("Finished contextual logging example")

# Example 3: Error handling with decorator
@handle_exceptions(
    error_types=[ValueError, TypeError],
    default_message="Error validating user data",
    log_error=True,
    default_return=False
)
def validate_user_data(data: Dict[str, Any]) -> bool:
    """
    Validate user data with error handling.
    
    Args:
        data: User data to validate
        
    Returns:
        True if data is valid, False otherwise
    """
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary")
    
    if "name" not in data:
        raise ValidationError("Name is required", {"field": "name"})
    
    if "age" in data and not isinstance(data["age"], int):
        raise ValidationError("Age must be an integer", {"field": "age", "value": data["age"]})
    
    if "email" in data and "@" not in data["email"]:
        raise ValidationError("Invalid email format", {"field": "email", "value": data["email"]})
    
    return True

# Example 4: Error handling with context manager
def process_payment(payment_id: str, amount: float) -> Dict[str, Any]:
    """
    Process a payment with error handling using context manager.
    
    Args:
        payment_id: Payment ID
        amount: Payment amount
        
    Returns:
        Payment result
    """
    module_logger.info(f"Processing payment {payment_id} for {amount}")
    
    with ErrorHandler(
        error_types=[ConnectionError, ValueError],
        default={"status": "failed", "reason": "Payment processing error"},
        context={"payment_id": payment_id, "amount": amount}
    ) as handler:
        # Simulate payment processing
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if random.random() < 0.3:
            raise ConnectionError("Payment gateway connection failed", {"gateway": "example"})
        
        # Successful payment
        return {"status": "success", "payment_id": payment_id, "amount": amount}
    
    if handler.error_occurred:
        module_logger.warning(f"Payment {payment_id} failed: {handler.error}")
    
    return handler.result

# Example 5: Async error handling
async def fetch_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Fetch a user profile with async error handling.
    
    Args:
        user_id: User ID
        
    Returns:
        User profile data
    """
    module_logger.info(f"Fetching profile for user {user_id}")
    
    # Simulate API call
    async def api_call():
        await asyncio.sleep(0.5)
        if random.random() < 0.3:
            raise ConnectionError("API connection failed", {"endpoint": "/users"})
        return {"id": user_id, "name": "Example User", "email": "user@example.com"}
    
    # Use async error handler
    result = await async_error_handler(
        api_call(),
        error_types=[ConnectionError, TimeoutError],
        default={"id": user_id, "error": "Failed to fetch profile"},
        context={"user_id": user_id, "operation": "fetch_profile"}
    )
    
    return result

# Example 6: Custom error class
class PaymentError(WiseflowError):
    """Error raised when a payment operation fails."""
    
    def __init__(
        self, 
        message: str, 
        payment_id: Optional[str] = None, 
        amount: Optional[float] = None, 
        cause: Optional[Exception] = None
    ):
        details = {
            "payment_id": payment_id,
            "amount": amount
        }
        super().__init__(message, details, cause)

def process_refund(payment_id: str, amount: float) -> Dict[str, Any]:
    """
    Process a refund with custom error handling.
    
    Args:
        payment_id: Payment ID
        amount: Refund amount
        
    Returns:
        Refund result
    """
    module_logger.info(f"Processing refund for payment {payment_id}")
    
    try:
        # Validate refund
        if amount <= 0:
            raise ValueError("Refund amount must be positive")
        
        # Simulate refund processing
        if random.random() < 0.3:
            raise ConnectionError("Refund gateway connection failed", {"gateway": "example"})
        
        # Successful refund
        return {"status": "success", "payment_id": payment_id, "refund_amount": amount}
    
    except Exception as e:
        # Create and log custom error
        error = PaymentError(
            "Refund processing failed",
            payment_id=payment_id,
            amount=amount,
            cause=e
        )
        error.log()
        
        # Return error response
        return {"status": "failed", "reason": str(error), "payment_id": payment_id}

# Main function to run all examples
async def main():
    """Run all examples."""
    module_logger.info("Starting error handling and logging examples")
    
    # Example 1: Basic logging
    basic_logging_example()
    
    # Example 2: Contextual logging
    contextual_logging_example("user-123", "login")
    
    # Example 3: Error handling with decorator
    valid_data = {"name": "John", "age": 30, "email": "john@example.com"}
    invalid_data = {"age": "thirty"}
    
    module_logger.info("Validating valid user data")
    result1 = validate_user_data(valid_data)
    module_logger.info(f"Validation result: {result1}")
    
    module_logger.info("Validating invalid user data")
    result2 = validate_user_data(invalid_data)
    module_logger.info(f"Validation result: {result2}")
    
    # Example 4: Error handling with context manager
    module_logger.info("Processing payments")
    payment1 = process_payment("payment-123", 100.0)
    payment2 = process_payment("payment-456", -50.0)
    module_logger.info(f"Payment 1 result: {payment1}")
    module_logger.info(f"Payment 2 result: {payment2}")
    
    # Example 5: Async error handling
    module_logger.info("Fetching user profiles")
    profile1 = await fetch_user_profile("user-123")
    profile2 = await fetch_user_profile("user-456")
    module_logger.info(f"Profile 1: {profile1}")
    module_logger.info(f"Profile 2: {profile2}")
    
    # Example 6: Custom error class
    module_logger.info("Processing refunds")
    refund1 = process_refund("payment-123", 50.0)
    refund2 = process_refund("payment-456", -25.0)
    module_logger.info(f"Refund 1 result: {refund1}")
    module_logger.info(f"Refund 2 result: {refund2}")
    
    module_logger.info("Finished error handling and logging examples")

# Run the examples
if __name__ == "__main__":
    asyncio.run(main())

