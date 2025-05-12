"""
Unit tests for the API error handling module.
"""

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError

from core.api.errors import (
    ErrorCode, ErrorDetail, ErrorResponse, APIError,
    AuthenticationError, InvalidAPIKeyError, ValidationError,
    ResourceNotFoundError, ProcessingError, ExternalServiceError,
    WebhookError, RateLimitExceededError, create_error_response,
    api_error_handler, validation_error_handler, general_exception_handler
)

@pytest.mark.unit
@pytest.mark.api
class TestAPIErrors:
    """Tests for the API error handling module."""
    
    def test_error_code_enum(self):
        """Test the ErrorCode enum."""
        assert ErrorCode.INVALID_API_KEY == "ERR-101"
        assert ErrorCode.VALIDATION_ERROR == "ERR-201"
        assert ErrorCode.NOT_FOUND == "ERR-301"
        assert ErrorCode.PROCESSING_ERROR == "ERR-401"
        assert ErrorCode.EXTERNAL_SERVICE_ERROR == "ERR-501"
        assert ErrorCode.INTERNAL_ERROR == "ERR-901"
    
    def test_error_detail_model(self):
        """Test the ErrorDetail model."""
        detail = ErrorDetail(
            loc=["body", "field"],
            msg="Field is required",
            type="value_error.missing"
        )
        
        assert detail.loc == ["body", "field"]
        assert detail.msg == "Field is required"
        assert detail.type == "value_error.missing"
    
    def test_error_response_model(self):
        """Test the ErrorResponse model."""
        response = ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Validation error",
            details=[
                ErrorDetail(
                    loc=["body", "field"],
                    msg="Field is required",
                    type="value_error.missing"
                )
            ],
            request_id="test-request-id"
        )
        
        assert response.error_code == ErrorCode.VALIDATION_ERROR
        assert response.message == "Validation error"
        assert len(response.details) == 1
        assert response.details[0].msg == "Field is required"
        assert response.request_id == "test-request-id"
        assert response.timestamp is not None
    
    def test_api_error(self):
        """Test the APIError class."""
        error = APIError(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Internal server error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        assert error.error_code == ErrorCode.INTERNAL_ERROR
        assert error.message == "Internal server error"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert str(error) == "Internal server error"
    
    def test_authentication_error(self):
        """Test the AuthenticationError class."""
        error = AuthenticationError()
        
        assert error.error_code == ErrorCode.UNAUTHORIZED
        assert error.message == "Authentication failed"
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Custom message
        error = AuthenticationError(message="Custom auth error")
        assert error.message == "Custom auth error"
    
    def test_invalid_api_key_error(self):
        """Test the InvalidAPIKeyError class."""
        error = InvalidAPIKeyError()
        
        assert error.error_code == ErrorCode.INVALID_API_KEY
        assert error.message == "Invalid API key"
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_validation_error(self):
        """Test the ValidationError class."""
        error = ValidationError()
        
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.message == "Validation error"
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        
        # With details
        details = [
            ErrorDetail(
                loc=["body", "field"],
                msg="Field is required",
                type="value_error.missing"
            )
        ]
        error = ValidationError(details=details)
        assert error.details == details
    
    def test_resource_not_found_error(self):
        """Test the ResourceNotFoundError class."""
        error = ResourceNotFoundError(
            resource_type="webhook",
            resource_id="123"
        )
        
        assert error.error_code == ErrorCode.NOT_FOUND
        assert error.message == "Webhook not found: 123"
        assert error.status_code == status.HTTP_404_NOT_FOUND
        
        # Custom message
        error = ResourceNotFoundError(
            resource_type="webhook",
            resource_id="123",
            message="Custom not found message"
        )
        assert error.message == "Custom not found message"
    
    def test_processing_error(self):
        """Test the ProcessingError class."""
        error = ProcessingError()
        
        assert error.error_code == ErrorCode.PROCESSING_ERROR
        assert error.message == "Error processing request"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Custom message
        error = ProcessingError(message="Custom processing error")
        assert error.message == "Custom processing error"
    
    def test_external_service_error(self):
        """Test the ExternalServiceError class."""
        error = ExternalServiceError(service_name="test-service")
        
        assert error.error_code == ErrorCode.EXTERNAL_SERVICE_ERROR
        assert error.message == "Error communicating with external service: test-service"
        assert error.status_code == status.HTTP_502_BAD_GATEWAY
        
        # Custom message
        error = ExternalServiceError(
            service_name="test-service",
            message="Custom external service error"
        )
        assert error.message == "Custom external service error"
    
    def test_webhook_error(self):
        """Test the WebhookError class."""
        error = WebhookError(webhook_id="123")
        
        assert error.error_code == ErrorCode.WEBHOOK_ERROR
        assert error.message == "Error with webhook: 123"
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Custom message
        error = WebhookError(
            webhook_id="123",
            message="Custom webhook error"
        )
        assert error.message == "Custom webhook error"
    
    def test_rate_limit_exceeded_error(self):
        """Test the RateLimitExceededError class."""
        error = RateLimitExceededError()
        
        assert error.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert error.message == "Rate limit exceeded"
        assert error.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    
    def test_create_error_response(self):
        """Test the create_error_response function."""
        response = create_error_response(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Validation error",
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.body is not None
        
        # With request
        mock_request = Request({"type": "http"})
        response = create_error_response(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Validation error",
            status_code=status.HTTP_400_BAD_REQUEST,
            request=mock_request
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_api_error_handler(self):
        """Test the api_error_handler function."""
        error = APIError(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Internal server error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
        mock_request = Request({"type": "http"})
        response = await api_error_handler(mock_request, error)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    @pytest.mark.asyncio
    async def test_validation_error_handler(self):
        """Test the validation_error_handler function."""
        error = RequestValidationError(
            errors=[
                {
                    "loc": ["body", "field"],
                    "msg": "Field is required",
                    "type": "value_error.missing"
                }
            ]
        )
        
        mock_request = Request({"type": "http"})
        response = await validation_error_handler(mock_request, error)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """Test the general_exception_handler function."""
        error = Exception("Test exception")
        
        mock_request = Request({"type": "http"})
        response = await general_exception_handler(mock_request, error)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

