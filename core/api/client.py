"""
WiseFlow API Client.

This module provides a client for interacting with the WiseFlow API.
"""

import json
import logging
import aiohttp
import requests
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class APIClientError(Exception):
    """Exception for API client errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict[str, Any]] = None):
        """
        Initialize the API client error.
        
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
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the WiseFlow API client.
        
        Args:
            base_url: Base URL of the WiseFlow API
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "WiseFlowClient/1.0"
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
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response.
        
        Args:
            response: HTTP response
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            APIClientError: If the response indicates an error
        """
        try:
            response_data = response.json()
            
            # Check for error response
            if response.status_code >= 400:
                error_message = response_data.get("message", "Unknown error")
                error_code = response_data.get("error_code", "UNKNOWN")
                raise APIClientError(
                    message=f"{error_code}: {error_message}",
                    status_code=response.status_code,
                    response=response_data
                )
            
            # Return data field if present, otherwise return the whole response
            if isinstance(response_data, dict) and "data" in response_data:
                return response_data["data"]
            
            return response_data
        except json.JSONDecodeError:
            raise APIClientError(
                message=f"Invalid JSON response: {response.text}",
                status_code=response.status_code
            )
    
    async def _handle_async_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """
        Handle asynchronous API response.
        
        Args:
            response: HTTP response
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            APIClientError: If the response indicates an error
        """
        try:
            response_data = await response.json()
            
            # Check for error response
            if response.status >= 400:
                error_message = response_data.get("message", "Unknown error")
                error_code = response_data.get("error_code", "UNKNOWN")
                raise APIClientError(
                    message=f"{error_code}: {error_message}",
                    status_code=response.status,
                    response=response_data
                )
            
            # Return data field if present, otherwise return the whole response
            if isinstance(response_data, dict) and "data" in response_data:
                return response_data["data"]
            
            return response_data
        except json.JSONDecodeError:
            raise APIClientError(
                message=f"Invalid JSON response: {await response.text()}",
                status_code=response.status
            )
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the API.
        
        Returns:
            Dict[str, Any]: Health check response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/health")
        
        try:
            response = requests.get(url)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Health check failed: {str(e)}")
            raise APIClientError(message=f"Health check failed: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/process")
        
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "references": references,
            "metadata": metadata or {}
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Content processing failed: {str(e)}")
            raise APIClientError(message=f"Content processing failed: {str(e)}")
    
    def batch_process(
        self,
        items: List[Dict[str, Any]],
        focus_point: str,
        explanation: str = "",
        use_multi_step_reasoning: bool = False,
        max_concurrency: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Process multiple items concurrently.
        
        Args:
            items: List of items to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            use_multi_step_reasoning: Whether to use multi-step reasoning
            max_concurrency: Maximum number of concurrent processes
            
        Returns:
            List[Dict[str, Any]]: The processing results
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/batch-process")
        
        payload = {
            "items": items,
            "focus_point": focus_point,
            "explanation": explanation,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "max_concurrency": max_concurrency
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Batch processing failed: {str(e)}")
            raise APIClientError(message=f"Batch processing failed: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/integration/extract")
        
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": False,
            "references": references,
            "metadata": metadata or {}
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Information extraction failed: {str(e)}")
            raise APIClientError(message=f"Information extraction failed: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/integration/analyze")
        
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": True,
            "references": references,
            "metadata": metadata or {}
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Content analysis failed: {str(e)}")
            raise APIClientError(message=f"Content analysis failed: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/integration/contextual")
        
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": False,
            "references": references,
            "metadata": metadata or {}
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Contextual understanding failed: {str(e)}")
            raise APIClientError(message=f"Contextual understanding failed: {str(e)}")
    
    # Webhook management methods
    def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all registered webhooks.
        
        Returns:
            List[Dict[str, Any]]: List of webhook configurations
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/webhooks")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list webhooks: {str(e)}")
            raise APIClientError(message=f"Failed to list webhooks: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/webhooks")
        
        payload = {
            "endpoint": endpoint,
            "events": events,
            "headers": headers or {},
            "secret": secret,
            "description": description
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to register webhook: {str(e)}")
            raise APIClientError(message=f"Failed to register webhook: {str(e)}")
    
    def get_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Get a webhook by ID.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Dict[str, Any]: Webhook configuration
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/webhooks/{webhook_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get webhook: {str(e)}")
            raise APIClientError(message=f"Failed to get webhook: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/webhooks/{webhook_id}")
        
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
        
        try:
            response = requests.put(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to update webhook: {str(e)}")
            raise APIClientError(message=f"Failed to update webhook: {str(e)}")
    
    def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Delete a webhook.
        
        Args:
            webhook_id: ID of the webhook to delete
            
        Returns:
            Dict[str, Any]: Webhook deletion result
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/webhooks/{webhook_id}")
        
        try:
            response = requests.delete(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to delete webhook: {str(e)}")
            raise APIClientError(message=f"Failed to delete webhook: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/webhooks/trigger")
        
        payload = {
            "event": event,
            "data": data,
            "async_mode": async_mode
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to trigger webhook: {str(e)}")
            raise APIClientError(message=f"Failed to trigger webhook: {str(e)}")
    
    # Information processing methods
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    # Async methods
    async def async_health_check(self) -> Dict[str, Any]:
        """
        Check the health of the API asynchronously.
        
        Returns:
            Dict[str, Any]: Health check response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/health")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Health check failed: {str(e)}")
            raise APIClientError(message=f"Health check failed: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/process")
        
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "references": references,
            "metadata": metadata or {}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Content processing failed: {str(e)}")
            raise APIClientError(message=f"Content processing failed: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/batch-process")
        
        payload = {
            "items": items,
            "focus_point": focus_point,
            "explanation": explanation,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "max_concurrency": max_concurrency
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Batch processing failed: {str(e)}")
            raise APIClientError(message=f"Batch processing failed: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/integration/extract")
        
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": False,
            "references": references,
            "metadata": metadata or {}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Information extraction failed: {str(e)}")
            raise APIClientError(message=f"Information extraction failed: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/integration/analyze")
        
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": True,
            "references": references,
            "metadata": metadata or {}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Content analysis failed: {str(e)}")
            raise APIClientError(message=f"Content analysis failed: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/integration/contextual")
        
        payload = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": False,
            "references": references,
            "metadata": metadata or {}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Contextual understanding failed: {str(e)}")
            raise APIClientError(message=f"Contextual understanding failed: {str(e)}")
    
    async def async_list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all registered webhooks asynchronously.
        
        Returns:
            List[Dict[str, Any]]: List of webhook configurations
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/webhooks")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to list webhooks: {str(e)}")
            raise APIClientError(message=f"Failed to list webhooks: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/webhooks")
        
        payload = {
            "endpoint": endpoint,
            "events": events,
            "headers": headers or {},
            "secret": secret,
            "description": description
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to register webhook: {str(e)}")
            raise APIClientError(message=f"Failed to register webhook: {str(e)}")
    
    async def async_get_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Get a webhook by ID asynchronously.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Dict[str, Any]: Webhook configuration
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/webhooks/{webhook_id}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get webhook: {str(e)}")
            raise APIClientError(message=f"Failed to get webhook: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/webhooks/{webhook_id}")
        
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
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(url, json=payload, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to update webhook: {str(e)}")
            raise APIClientError(message=f"Failed to update webhook: {str(e)}")
    
    async def async_delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Delete a webhook asynchronously.
        
        Args:
            webhook_id: ID of the webhook to delete
            
        Returns:
            Dict[str, Any]: Webhook deletion result
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/webhooks/{webhook_id}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to delete webhook: {str(e)}")
            raise APIClientError(message=f"Failed to delete webhook: {str(e)}")
    
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
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/webhooks/trigger")
        
        payload = {
            "event": event,
            "data": data,
            "async_mode": async_mode
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to trigger webhook: {str(e)}")
            raise APIClientError(message=f"Failed to trigger webhook: {str(e)}")
    
    async def async_get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID asynchronously.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    async def async_list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items asynchronously.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    async def async_process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point asynchronously.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    async def async_generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items asynchronously.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    return await self._handle_async_response(response)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
        
        try:
            response = requests.get(url, params=params, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to list information: {str(e)}")
            raise APIClientError(message=f"Failed to list information: {str(e)}")
    
    def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process sources based on a focus point.
        
        Args:
            sources: List of sources to process
            focus_point: Focus point for processing
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Process response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/process")
        
        payload = {
            "sources": sources,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to process sources: {str(e)}")
            raise APIClientError(message=f"Failed to process sources: {str(e)}")
    
    def generate_summary(
        self,
        information_ids: List[str],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_ids: List of information IDs to summarize
            focus_point: Focus point for summarization
            explanation: Additional explanation or context
            
        Returns:
            Dict[str, Any]: Summary response
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information/summary")
        
        payload = {
            "information_ids": information_ids,
            "focus_point": focus_point,
            "explanation": explanation
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise APIClientError(message=f"Failed to generate summary: {str(e)}")
    
    def get_information(self, information_id: str) -> Dict[str, Any]:
        """
        Get information by ID.
        
        Args:
            information_id: Information ID
            
        Returns:
            Dict[str, Any]: Information details
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url(f"/api/v1/information/{information_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            return self._handle_response(response)
        except requests.RequestException as e:
            logger.error(f"Failed to get information: {str(e)}")
            raise APIClientError(message=f"Failed to get information: {str(e)}")
    
    def list_information(
        self,
        page: int = 1,
        page_size: int = 10,
        focus_point: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List information items.
        
        Args:
            page: Page number
            page_size: Items per page
            focus_point: Filter by focus point
            source_type: Filter by source type
            
        Returns:
            Dict[str, Any]: Paginated list of information items
            
        Raises:
            APIClientError: If the request fails
        """
        url = self._get_url("/api/v1/information")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if focus_point:
            params["focus_point"] = focus_point
        if source_type:
            params["source_type"] = source_type
