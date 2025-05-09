#!/usr/bin/env python3
"""
Webhook management for WiseFlow.

This module provides functionality for managing webhooks.
"""

import json
import logging
import uuid
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class WebhookManager:
    """Manager for webhooks."""
    
    def __init__(self):
        """Initialize the webhook manager."""
        self.webhooks = {}
    
    def register_webhook(
        self,
        endpoint: str,
        events: List[str],
        headers: Optional[Dict[str, str]] = None,
        secret: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Register a new webhook.
        
        Args:
            endpoint: Webhook endpoint URL
            events: List of events to trigger the webhook
            headers: Optional headers to include in webhook requests
            secret: Optional secret for signing webhook payloads
            description: Optional description of the webhook
            
        Returns:
            str: Webhook ID
        """
        webhook_id = str(uuid.uuid4())
        
        self.webhooks[webhook_id] = {
            "endpoint": endpoint,
            "events": events,
            "headers": headers or {},
            "secret": secret,
            "description": description,
        }
        
        logger.info(f"Registered webhook {webhook_id} for events {events}")
        
        return webhook_id
    
    def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all registered webhooks.
        
        Returns:
            List[Dict[str, Any]]: List of webhook configurations
        """
        return [
            {"webhook_id": webhook_id, **webhook}
            for webhook_id, webhook in self.webhooks.items()
        ]
    
    def get_webhook(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a webhook by ID.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Optional[Dict[str, Any]]: Webhook configuration or None if not found
        """
        return self.webhooks.get(webhook_id)
    
    def update_webhook(
        self,
        webhook_id: str,
        endpoint: Optional[str] = None,
        events: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        secret: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """
        Update an existing webhook.
        
        Args:
            webhook_id: ID of the webhook to update
            endpoint: New endpoint URL
            events: New list of events
            headers: New headers
            secret: New secret
            description: New description
            
        Returns:
            bool: True if successful, False otherwise
        """
        if webhook_id not in self.webhooks:
            return False
        
        webhook = self.webhooks[webhook_id]
        
        if endpoint is not None:
            webhook["endpoint"] = endpoint
        
        if events is not None:
            webhook["events"] = events
        
        if headers is not None:
            webhook["headers"] = headers
        
        if secret is not None:
            webhook["secret"] = secret
        
        if description is not None:
            webhook["description"] = description
        
        logger.info(f"Updated webhook {webhook_id}")
        
        return True
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """
        Delete a webhook.
        
        Args:
            webhook_id: ID of the webhook to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if webhook_id not in self.webhooks:
            return False
        
        del self.webhooks[webhook_id]
        
        logger.info(f"Deleted webhook {webhook_id}")
        
        return True
    
    def trigger_webhook(
        self,
        event: str,
        data: Dict[str, Any],
        async_mode: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Trigger webhooks for a specific event.
        
        Args:
            event: Event name
            data: Data to send
            async_mode: Whether to trigger webhooks asynchronously
            
        Returns:
            List[Dict[str, Any]]: List of webhook responses
        """
        # Find webhooks that match the event
        matching_webhooks = [
            (webhook_id, webhook)
            for webhook_id, webhook in self.webhooks.items()
            if event in webhook["events"]
        ]
        
        if not matching_webhooks:
            logger.info(f"No webhooks found for event {event}")
            return []
        
        logger.info(f"Triggering {len(matching_webhooks)} webhooks for event {event}")
        
        if async_mode:
            # Trigger webhooks asynchronously
            asyncio.create_task(self._trigger_webhooks_async(event, data, matching_webhooks))
            return []
        else:
            # Trigger webhooks synchronously
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._trigger_webhooks_async(event, data, matching_webhooks))
    
    async def _trigger_webhooks_async(
        self,
        event: str,
        data: Dict[str, Any],
        matching_webhooks: List[tuple]
    ) -> List[Dict[str, Any]]:
        """
        Trigger webhooks asynchronously.
        
        Args:
            event: Event name
            data: Data to send
            matching_webhooks: List of (webhook_id, webhook) tuples
            
        Returns:
            List[Dict[str, Any]]: List of webhook responses
        """
        responses = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for webhook_id, webhook in matching_webhooks:
                task = self._trigger_single_webhook(session, webhook_id, webhook, event, data)
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [
            response for response in responses
            if not isinstance(response, Exception)
        ]
    
    async def _trigger_single_webhook(
        self,
        session: aiohttp.ClientSession,
        webhook_id: str,
        webhook: Dict[str, Any],
        event: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger a single webhook.
        
        Args:
            session: aiohttp client session
            webhook_id: Webhook ID
            webhook: Webhook configuration
            event: Event name
            data: Data to send
            
        Returns:
            Dict[str, Any]: Webhook response
        """
        endpoint = webhook["endpoint"]
        headers = webhook["headers"].copy()
        headers["Content-Type"] = "application/json"
        
        payload = {
            "event": event,
            "data": data,
            "timestamp": None  # Will be filled in by the API server
        }
        
        try:
            async with session.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=10
            ) as response:
                status_code = response.status
                response_text = await response.text()
                
                try:
                    response_json = json.loads(response_text)
                except json.JSONDecodeError:
                    response_json = {"text": response_text}
                
                logger.info(f"Webhook {webhook_id} response: {status_code}")
                
                return {
                    "webhook_id": webhook_id,
                    "status_code": status_code,
                    "response": response_json,
                }
        except Exception as e:
            logger.error(f"Error triggering webhook {webhook_id}: {str(e)}")
            
            return {
                "webhook_id": webhook_id,
                "status_code": 0,
                "error": str(e),
            }

# Singleton instance
_webhook_manager = None

def get_webhook_manager() -> WebhookManager:
    """
    Get the singleton webhook manager instance.
    
    Returns:
        WebhookManager: Webhook manager instance
    """
    global _webhook_manager
    
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    
    return _webhook_manager

