"""
WiseFlow API Client.

This module provides a client for interacting with the WiseFlow API.
"""

import json
import logging
import aiohttp
import requests
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

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
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the API.
        
        Returns:
            Dict[str, Any]: Health check response
        """
        url = self._get_url("/health")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
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
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Content processing failed: {str(e)}")
            return {"error": str(e)}
    
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
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            return [{"error": str(e)}]
    
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
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Information extraction failed: {str(e)}")
            return {"error": str(e)}
    
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
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Content analysis failed: {str(e)}")
            return {"error": str(e)}
    
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
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Contextual understanding failed: {str(e)}")
            return {"error": str(e)}
    
    # Webhook management methods
    def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all registered webhooks.
        
        Returns:
            List[Dict[str, Any]]: List of webhook configurations
        """
        url = self._get_url("/api/v1/webhooks")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list webhooks: {str(e)}")
            return []
    
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
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to register webhook: {str(e)}")
            return {"error": str(e)}
    
    def get_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Get a webhook by ID.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Dict[str, Any]: Webhook configuration
        """
        url = self._get_url(f"/api/v1/webhooks/{webhook_id}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get webhook: {str(e)}")
            return {"error": str(e)}
    
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
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to update webhook: {str(e)}")
            return {"error": str(e)}
    
    def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Delete a webhook.
        
        Args:
            webhook_id: ID of the webhook to delete
            
        Returns:
            Dict[str, Any]: Webhook deletion result
        """
        url = self._get_url(f"/api/v1/webhooks/{webhook_id}")
        
        try:
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to delete webhook: {str(e)}")
            return {"error": str(e)}
    
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
        url = self._get_url("/api/v1/webhooks/trigger")
        
        payload = {
            "event": event,
            "data": data,
            "async_mode": async_mode
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to trigger webhook: {str(e)}")
            return {"error": str(e)}


class AsyncWiseFlowClient:
    """Asynchronous client for interacting with the WiseFlow API."""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the asynchronous WiseFlow API client.
        
        Args:
            base_url: Base URL of the WiseFlow API
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
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
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the API.
        
        Returns:
            Dict[str, Any]: Health check response
        """
        url = self._get_url("/health")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def process_content(
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
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Content processing failed: {str(e)}")
            return {"error": str(e)}
    
    async def batch_process(
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
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            return [{"error": str(e)}]
    
    # Integration endpoints
    async def extract_information(
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
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Information extraction failed: {str(e)}")
            return {"error": str(e)}
    
    async def analyze_content(
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
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Content analysis failed: {str(e)}")
            return {"error": str(e)}
    
    async def contextual_understanding(
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
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Contextual understanding failed: {str(e)}")
            return {"error": str(e)}
    
    # Webhook management methods
    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all registered webhooks.
        
        Returns:
            List[Dict[str, Any]]: List of webhook configurations
        """
        url = self._get_url("/api/v1/webhooks")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Failed to list webhooks: {str(e)}")
            return []
    
    async def register_webhook(
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
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Failed to register webhook: {str(e)}")
            return {"error": str(e)}
    
    async def get_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Get a webhook by ID.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Dict[str, Any]: Webhook configuration
        """
        url = self._get_url(f"/api/v1/webhooks/{webhook_id}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Failed to get webhook: {str(e)}")
            return {"error": str(e)}
    
    async def update_webhook(
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
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Failed to update webhook: {str(e)}")
            return {"error": str(e)}
    
    async def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Delete a webhook.
        
        Args:
            webhook_id: ID of the webhook to delete
            
        Returns:
            Dict[str, Any]: Webhook deletion result
        """
        url = self._get_url(f"/api/v1/webhooks/{webhook_id}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=self.headers) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Failed to delete webhook: {str(e)}")
            return {"error": str(e)}
    
    async def trigger_webhook(
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
        url = self._get_url("/api/v1/webhooks/trigger")
        
        payload = {
            "event": event,
            "data": data,
            "async_mode": async_mode
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Failed to trigger webhook: {str(e)}")
            return {"error": str(e)}
