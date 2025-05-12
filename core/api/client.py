"""
WiseFlow API Client.

This module provides a client for interacting with the WiseFlow API.
"""

import json
import logging
import asyncio
import aiohttp
import requests
from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, Awaitable

logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar('T')

class APIError(Exception):
    """Exception raised for API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict[str, Any]] = None):
        """
        Initialize the API error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            response: API response
        """
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

class WiseFlowClient:
    """Client for interacting with the WiseFlow API."""
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 60, max_retries: int = 3):
        """
        Initialize the WiseFlow API client.
        
        Args:
            base_url: Base URL of the WiseFlow API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def _get_url(self, endpoint: str) -> str:
        """
        Get the full URL for an endpoint.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            str: Full URL
        """
        return f"{self.base_url}/{endpoint.lstrip('/')}"
    
    def _handle_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle API response.
        
        Args:
            response: API response
            
        Returns:
            Dict[str, Any]: Processed response
            
        Raises:
            APIError: If the response indicates an error
        """
        if not response.get("success", True):
            errors = response.get("errors", [])
            error_message = response.get("message", "Unknown API error")
            if errors:
                error_details = ", ".join([error.get("detail", "") for error in errors])
                error_message = f"{error_message}: {error_details}"
            
            raise APIError(error_message, response=response)
        
        return response
    
    def _handle_request_exception(self, e: Exception, endpoint: str) -> Dict[str, Any]:
        """
        Handle request exception.
        
        Args:
            e: Exception
            endpoint: API endpoint
            
        Returns:
            Dict[str, Any]: Error response
            
        Raises:
            APIError: With details about the exception
        """
        logger.error(f"Request to {endpoint} failed: {str(e)}", exc_info=True)
        raise APIError(f"Request failed: {str(e)}")
    
    def _make_sync_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a synchronous HTTP request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            json_data: JSON data for request body
            params: Query parameters
            
        Returns:
            Dict[str, Any]: API response
            
        Raises:
            APIError: If the request fails
        """
        url = self._get_url(endpoint)
        
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return self._handle_response(response.json())
            except requests.exceptions.HTTPError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    # Retry server errors
                    logger.warning(f"Server error on attempt {attempt + 1}, retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
                # Try to parse error response
                try:
                    error_data = e.response.json()
                    raise APIError(
                        message=error_data.get("message", str(e)),
                        status_code=e.response.status_code,
                        response=error_data
                    )
                except (ValueError, KeyError):
                    # Couldn't parse error response
                    raise APIError(
                        message=str(e),
                        status_code=e.response.status_code
                    )
            except Exception as e:
                return self._handle_request_exception(e, endpoint)
    
    async def _make_async_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an asynchronous HTTP request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            json_data: JSON data for request body
            params: Query parameters
            
        Returns:
            Dict[str, Any]: API response
            
        Raises:
            APIError: If the request fails
        """
        url = self._get_url(endpoint)
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        json=json_data,
                        params=params,
                        headers=self.headers,
                        timeout=self.timeout
                    ) as response:
                        response.raise_for_status()
                        return self._handle_response(await response.json())
            except aiohttp.ClientResponseError as e:
                if e.status >= 500 and attempt < self.max_retries - 1:
                    # Retry server errors
                    logger.warning(f"Server error on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
                # Try to parse error response
                try:
                    error_text = await e.response.text()
                    error_data = json.loads(error_text)
                    raise APIError(
                        message=error_data.get("message", str(e)),
                        status_code=e.status,
                        response=error_data
                    )
                except (ValueError, KeyError):
                    # Couldn't parse error response
                    raise APIError(
                        message=str(e),
                        status_code=e.status
                    )
            except Exception as e:
                return self._handle_request_exception(e, endpoint)
    
    # Synchronous API methods
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the API.
        
        Returns:
            Dict[str, Any]: Health check response
        """
        try:
            return self._make_sync_request("GET", "/health")
        except APIError as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def process_content(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        use_multi_step_reasoning: bool = False,
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process content using specialized prompting strategies.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            use_multi_step_reasoning: Whether to use multi-step reasoning
            references: Optional reference materials for contextual understanding
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The processing result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "references": references,
            "metadata": metadata or {}
        }
        
        return self._make_sync_request("POST", "/api/v1/process", json_data=payload)
    
    def batch_process(
        self,
        items: List[Dict[str, Any]],
        focus_point: str,
        explanation: str = "",
        use_multi_step_reasoning: bool = False,
        max_concurrency: int = 5
    ) -> Dict[str, Any]:
        """
        Process multiple items concurrently.
        
        Args:
            items: List of items to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            use_multi_step_reasoning: Whether to use multi-step reasoning
            max_concurrency: Maximum number of concurrent processes
            
        Returns:
            Dict[str, Any]: The processing results
        """
        payload = {
            "items": items,
            "focus_point": focus_point,
            "explanation": explanation,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "max_concurrency": max_concurrency
        }
        
        return self._make_sync_request("POST", "/api/v1/batch-process", json_data=payload)
    
    def extract_information(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract information from content.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            references: Optional reference materials for contextual understanding
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The extraction result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": False,
            "references": references,
            "metadata": metadata or {}
        }
        
        return self._make_sync_request("POST", "/api/v1/integration/extract", json_data=payload)
    
    def analyze_content(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze content using multi-step reasoning.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            references: Optional reference materials for contextual understanding
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The analysis result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": True,
            "references": references,
            "metadata": metadata or {}
        }
        
        return self._make_sync_request("POST", "/api/v1/integration/analyze", json_data=payload)
    
    def contextual_understanding(
        self,
        content: str,
        focus_point: str,
        references: str,
        explanation: str = "",
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process content with contextual understanding.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            references: Reference materials for contextual understanding
            explanation: Additional explanation or context
            content_type: The type of content
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The contextual understanding result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": False,
            "references": references,
            "metadata": metadata or {}
        }
        
        return self._make_sync_request("POST", "/api/v1/integration/contextual", json_data=payload)
    
    # Webhook management methods
    def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all registered webhooks.
        
        Returns:
            List[Dict[str, Any]]: List of webhook configurations
        """
        response = self._make_sync_request("GET", "/api/v1/webhooks")
        return response.get("data", {}).get("webhooks", [])
    
    def register_webhook(
        self,
        endpoint: str,
        events: List[str],
        headers: Optional[Dict[str, str]] = None,
        secret: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new webhook.
        
        Args:
            endpoint: Webhook endpoint URL
            events: List of events to trigger the webhook
            headers: Optional headers to include in webhook requests
            secret: Optional secret for signing webhook payloads
            description: Optional description of the webhook
            
        Returns:
            Dict[str, Any]: Webhook registration result
        """
        payload = {
            "endpoint": endpoint,
            "events": events,
            "headers": headers or {},
            "secret": secret,
            "description": description
        }
        
        return self._make_sync_request("POST", "/api/v1/webhooks", json_data=payload)
    
    def get_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Get a webhook by ID.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Dict[str, Any]: Webhook configuration
        """
        return self._make_sync_request("GET", f"/api/v1/webhooks/{webhook_id}")
    
    def update_webhook(
        self,
        webhook_id: str,
        endpoint: Optional[str] = None,
        events: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        secret: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing webhook.
        
        Args:
            webhook_id: ID of the webhook to update
            endpoint: New endpoint URL (optional)
            events: New list of events (optional)
            headers: New headers (optional)
            secret: New secret (optional)
            description: New description (optional)
            
        Returns:
            Dict[str, Any]: Webhook update result
        """
        payload = {}
        if endpoint is not None:
            payload["endpoint"] = endpoint
        if events is not None:
            payload["events"] = events
        if headers is not None:
            payload["headers"] = headers
        if secret is not None:
            payload["secret"] = secret
        if description is not None:
            payload["description"] = description
        
        return self._make_sync_request("PUT", f"/api/v1/webhooks/{webhook_id}", json_data=payload)
    
    def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Delete a webhook.
        
        Args:
            webhook_id: ID of the webhook to delete
            
        Returns:
            Dict[str, Any]: Webhook deletion result
        """
        return self._make_sync_request("DELETE", f"/api/v1/webhooks/{webhook_id}")
    
    def trigger_webhook(
        self,
        event: str,
        data: Dict[str, Any],
        async_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Trigger webhooks for a specific event.
        
        Args:
            event: Event name
            data: Data to send
            async_mode: Whether to trigger webhooks asynchronously
            
        Returns:
            Dict[str, Any]: Webhook trigger result
        """
        payload = {
            "event": event,
            "data": data,
            "async_mode": async_mode
        }
        
        return self._make_sync_request("POST", "/api/v1/webhooks/trigger", json_data=payload)
    
    # Asynchronous API methods
    async def async_health_check(self) -> Dict[str, Any]:
        """
        Check the health of the API asynchronously.
        
        Returns:
            Dict[str, Any]: Health check response
        """
        try:
            return await self._make_async_request("GET", "/health")
        except APIError as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def async_process_content(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        use_multi_step_reasoning: bool = False,
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process content using specialized prompting strategies asynchronously.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            use_multi_step_reasoning: Whether to use multi-step reasoning
            references: Optional reference materials for contextual understanding
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The processing result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "references": references,
            "metadata": metadata or {}
        }
        
        return await self._make_async_request("POST", "/api/v1/process", json_data=payload)
    
    async def async_batch_process(
        self,
        items: List[Dict[str, Any]],
        focus_point: str,
        explanation: str = "",
        use_multi_step_reasoning: bool = False,
        max_concurrency: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Process multiple items concurrently asynchronously.
        
        Args:
            items: List of items to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            use_multi_step_reasoning: Whether to use multi-step reasoning
            max_concurrency: Maximum number of concurrent processes
            
        Returns:
            List[Dict[str, Any]]: The processing results
        """
        payload = {
            "items": items,
            "focus_point": focus_point,
            "explanation": explanation,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "max_concurrency": max_concurrency
        }
        
        return await self._make_async_request("POST", "/api/v1/batch-process", json_data=payload)
    
    async def async_extract_information(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract information from content asynchronously.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            references: Optional reference materials for contextual understanding
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The extraction result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": False,
            "references": references,
            "metadata": metadata or {}
        }
        
        return await self._make_async_request("POST", "/api/v1/integration/extract", json_data=payload)
    
    async def async_analyze_content(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze content using multi-step reasoning asynchronously.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            references: Optional reference materials for contextual understanding
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The analysis result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": True,
            "references": references,
            "metadata": metadata or {}
        }
        
        return await self._make_async_request("POST", "/api/v1/integration/analyze", json_data=payload)
    
    async def async_contextual_understanding(
        self,
        content: str,
        focus_point: str,
        references: str,
        explanation: str = "",
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process content with contextual understanding asynchronously.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            references: Reference materials for contextual understanding
            explanation: Additional explanation or context
            content_type: The type of content
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The contextual understanding result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": False,
            "references": references,
            "metadata": metadata or {}
        }
        
        return await self._make_async_request("POST", "/api/v1/integration/contextual", json_data=payload)
    
    async def async_list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all registered webhooks asynchronously.
        
        Returns:
            List[Dict[str, Any]]: List of webhook configurations
        """
        response = await self._make_async_request("GET", "/api/v1/webhooks")
        return response.get("data", {}).get("webhooks", [])
    
    async def async_register_webhook(
        self,
        endpoint: str,
        events: List[str],
        headers: Optional[Dict[str, str]] = None,
        secret: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new webhook asynchronously.
        
        Args:
            endpoint: Webhook endpoint URL
            events: List of events to trigger the webhook
            headers: Optional headers to include in webhook requests
            secret: Optional secret for signing webhook payloads
            description: Optional description of the webhook
            
        Returns:
            Dict[str, Any]: Webhook registration result
        """
        payload = {
            "endpoint": endpoint,
            "events": events,
            "headers": headers or {},
            "secret": secret,
            "description": description
        }
        
        return await self._make_async_request("POST", "/api/v1/webhooks", json_data=payload)
    
    async def async_get_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Get a webhook by ID asynchronously.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Dict[str, Any]: Webhook configuration
        """
        return await self._make_async_request("GET", f"/api/v1/webhooks/{webhook_id}")
    
    async def async_update_webhook(
        self,
        webhook_id: str,
        endpoint: Optional[str] = None,
        events: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        secret: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing webhook asynchronously.
        
        Args:
            webhook_id: ID of the webhook to update
            endpoint: New endpoint URL (optional)
            events: New list of events (optional)
            headers: New headers (optional)
            secret: New secret (optional)
            description: New description (optional)
            
        Returns:
            Dict[str, Any]: Webhook update result
        """
        payload = {}
        if endpoint is not None:
            payload["endpoint"] = endpoint
        if events is not None:
            payload["events"] = events
        if headers is not None:
            payload["headers"] = headers
        if secret is not None:
            payload["secret"] = secret
        if description is not None:
            payload["description"] = description
        
        return await self._make_async_request("PUT", f"/api/v1/webhooks/{webhook_id}", json_data=payload)
    
    async def async_delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Delete a webhook asynchronously.
        
        Args:
            webhook_id: ID of the webhook to delete
            
        Returns:
            Dict[str, Any]: Webhook deletion result
        """
        return await self._make_async_request("DELETE", f"/api/v1/webhooks/{webhook_id}")
    
    async def async_trigger_webhook(
        self,
        event: str,
        data: Dict[str, Any],
        async_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Trigger webhooks for a specific event asynchronously.
        
        Args:
            event: Event name
            data: Data to send
            async_mode: Whether to trigger webhooks asynchronously
            
        Returns:
            Dict[str, Any]: Webhook trigger result
        """
        payload = {
            "event": event,
            "data": data,
            "async_mode": async_mode
        }
        
        return await self._make_async_request("POST", "/api/v1/webhooks/trigger", json_data=payload)


class AsyncWiseFlowClient:
    """Asynchronous client for interacting with the WiseFlow API."""
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 60, max_retries: int = 3):
        """
        Initialize the asynchronous WiseFlow API client.
        
        Args:
            base_url: Base URL of the WiseFlow API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def _get_url(self, endpoint: str) -> str:
        """
        Get the full URL for an endpoint.
        
        Args:
            endpoint: API endpoint
            
        Returns:
            str: Full URL
        """
        return f"{self.base_url}/{endpoint.lstrip('/')}"
    
    async def _make_async_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an asynchronous HTTP request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            json_data: JSON data for request body
            params: Query parameters
            
        Returns:
            Dict[str, Any]: API response
            
        Raises:
            APIError: If the request fails
        """
        url = self._get_url(endpoint)
        
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        json=json_data,
                        params=params,
                        headers=self.headers,
                        timeout=self.timeout
                    ) as response:
                        response.raise_for_status()
                        return self._handle_response(await response.json())
            except aiohttp.ClientResponseError as e:
                if e.status >= 500 and attempt < self.max_retries - 1:
                    # Retry server errors
                    logger.warning(f"Server error on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
                # Try to parse error response
                try:
                    error_text = await e.response.text()
                    error_data = json.loads(error_text)
                    raise APIError(
                        message=error_data.get("message", str(e)),
                        status_code=e.status,
                        response=error_data
                    )
                except (ValueError, KeyError):
                    # Couldn't parse error response
                    raise APIError(
                        message=str(e),
                        status_code=e.status
                    )
            except Exception as e:
                return self._handle_request_exception(e, endpoint)
    
    # Asynchronous API methods
    async def async_health_check(self) -> Dict[str, Any]:
        """
        Check the health of the API asynchronously.
        
        Returns:
            Dict[str, Any]: Health check response
        """
        try:
            return await self._make_async_request("GET", "/health")
        except APIError as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def async_process_content(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        use_multi_step_reasoning: bool = False,
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process content using specialized prompting strategies asynchronously.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            use_multi_step_reasoning: Whether to use multi-step reasoning
            references: Optional reference materials for contextual understanding
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The processing result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "references": references,
            "metadata": metadata or {}
        }
        
        return await self._make_async_request("POST", "/api/v1/process", json_data=payload)
    
    async def async_batch_process(
        self,
        items: List[Dict[str, Any]],
        focus_point: str,
        explanation: str = "",
        use_multi_step_reasoning: bool = False,
        max_concurrency: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Process multiple items concurrently asynchronously.
        
        Args:
            items: List of items to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            use_multi_step_reasoning: Whether to use multi-step reasoning
            max_concurrency: Maximum number of concurrent processes
            
        Returns:
            List[Dict[str, Any]]: The processing results
        """
        payload = {
            "items": items,
            "focus_point": focus_point,
            "explanation": explanation,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "max_concurrency": max_concurrency
        }
        
        return await self._make_async_request("POST", "/api/v1/batch-process", json_data=payload)
    
    async def async_extract_information(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract information from content asynchronously.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            references: Optional reference materials for contextual understanding
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The extraction result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": False,
            "references": references,
            "metadata": metadata or {}
        }
        
        return await self._make_async_request("POST", "/api/v1/integration/extract", json_data=payload)
    
    async def async_analyze_content(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze content using multi-step reasoning asynchronously.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            references: Optional reference materials for contextual understanding
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The analysis result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": True,
            "references": references,
            "metadata": metadata or {}
        }
        
        return await self._make_async_request("POST", "/api/v1/integration/analyze", json_data=payload)
    
    async def async_contextual_understanding(
        self,
        content: str,
        focus_point: str,
        references: str,
        explanation: str = "",
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process content with contextual understanding asynchronously.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            references: Reference materials for contextual understanding
            explanation: Additional explanation or context
            content_type: The type of content
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The contextual understanding result
        """
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": False,
            "references": references,
            "metadata": metadata or {}
        }
        
        return await self._make_async_request("POST", "/api/v1/integration/contextual", json_data=payload)
    
    async def async_list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all registered webhooks asynchronously.
        
        Returns:
            List[Dict[str, Any]]: List of webhook configurations
        """
        response = await self._make_async_request("GET", "/api/v1/webhooks")
        return response.get("data", {}).get("webhooks", [])
    
    async def async_register_webhook(
        self,
        endpoint: str,
        events: List[str],
        headers: Optional[Dict[str, str]] = None,
        secret: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new webhook asynchronously.
        
        Args:
            endpoint: Webhook endpoint URL
            events: List of events to trigger the webhook
            headers: Optional headers to include in webhook requests
            secret: Optional secret for signing webhook payloads
            description: Optional description of the webhook
            
        Returns:
            Dict[str, Any]: Webhook registration result
        """
        payload = {
            "endpoint": endpoint,
            "events": events,
            "headers": headers or {},
            "secret": secret,
            "description": description
        }
        
        return await self._make_async_request("POST", "/api/v1/webhooks", json_data=payload)
    
    async def async_get_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Get a webhook by ID asynchronously.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Dict[str, Any]: Webhook configuration
        """
        return await self._make_async_request("GET", f"/api/v1/webhooks/{webhook_id}")
    
    async def async_update_webhook(
        self,
        webhook_id: str,
        endpoint: Optional[str] = None,
        events: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        secret: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing webhook asynchronously.
        
        Args:
            webhook_id: ID of the webhook to update
            endpoint: New endpoint URL (optional)
            events: New list of events (optional)
            headers: New headers (optional)
            secret: New secret (optional)
            description: New description (optional)
            
        Returns:
            Dict[str, Any]: Webhook update result
        """
        payload = {}
        if endpoint is not None:
            payload["endpoint"] = endpoint
        if events is not None:
            payload["events"] = events
        if headers is not None:
            payload["headers"] = headers
        if secret is not None:
            payload["secret"] = secret
        if description is not None:
            payload["description"] = description
        
        return await self._make_async_request("PUT", f"/api/v1/webhooks/{webhook_id}", json_data=payload)
    
    async def async_delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Delete a webhook asynchronously.
        
        Args:
            webhook_id: ID of the webhook to delete
            
        Returns:
            Dict[str, Any]: Webhook deletion result
        """
        return await self._make_async_request("DELETE", f"/api/v1/webhooks/{webhook_id}")
    
    async def async_trigger_webhook(
        self,
        event: str,
        data: Dict[str, Any],
        async_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Trigger webhooks for a specific event asynchronously.
        
        Args:
            event: Event name
            data: Data to send
            async_mode: Whether to trigger webhooks asynchronously
            
        Returns:
            Dict[str, Any]: Webhook trigger result
        """
        payload = {
            "event": event,
            "data": data,
            "async_mode": async_mode
        }
        
        return await self._make_async_request("POST", "/api/v1/webhooks/trigger", json_data=payload)
