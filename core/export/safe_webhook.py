"""
Thread-safe webhook module for WiseFlow.

This module provides functionality for integrating with external systems via webhooks
with proper thread safety and resource management.
"""

import logging
import json
import os
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import hmac
import hashlib
import base64
import uuid
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Pydantic models for webhook data
class WebhookConfig(BaseModel):
    """Webhook configuration model."""
    endpoint: str
    events: List[str]
    headers: Dict[str, str] = Field(default_factory=dict)
    secret: Optional[str] = None
    description: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[str] = None
    last_triggered: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0

class WebhookResponse(BaseModel):
    """Webhook response model."""
    webhook_id: str
    event: str
    timestamp: str
    status_code: Optional[int] = None
    response: Optional[str] = None
    error: Optional[str] = None
    success: bool

class WebhookManager:
    """Thread-safe manager for webhook operations."""
    
    def __init__(self, config_path: str = "webhooks.json"):
        """
        Initialize the webhook manager.
        
        Args:
            config_path: Path to the webhook configuration file
        """
        self.config_path = config_path
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.secret_key = os.environ.get("WEBHOOK_SECRET_KEY", "wiseflow-webhook-secret")
        self._lock = asyncio.Lock()
        self._session: Optional[aiohttp.ClientSession] = None
        self._active_tasks: Set[asyncio.Task] = set()
        
        # Load webhooks if config file exists
        self._load_webhooks()
    
    def _load_webhooks(self):
        """Load webhooks from the configuration file if it exists."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    webhook_dict = json.load(f)
                    
                # Convert to Pydantic models
                for webhook_id, webhook_data in webhook_dict.items():
                    self.webhooks[webhook_id] = WebhookConfig(**webhook_data)
                    
                logger.info(f"Loaded {len(self.webhooks)} webhooks")
            except Exception as e:
                logger.error(f"Failed to load webhooks: {str(e)}")
    
    async def _save_webhooks(self):
        """Save webhooks to the configuration file."""
        async with self._lock:
            try:
                # Convert Pydantic models to dict
                webhook_dict = {
                    webhook_id: webhook.dict()
                    for webhook_id, webhook in self.webhooks.items()
                }
                
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(webhook_dict, f, indent=2)
                    
                logger.info(f"Saved {len(self.webhooks)} webhooks")
            except Exception as e:
                logger.error(f"Failed to save webhooks: {str(e)}")
    
    async def register_webhook(self, 
                        endpoint: str, 
                        events: List[str], 
                        headers: Optional[Dict[str, str]] = None,
                        secret: Optional[str] = None,
                        description: Optional[str] = None) -> str:
        """
        Register a new webhook.
        
        Args:
            endpoint: Webhook endpoint URL
            events: List of events to trigger the webhook
            headers: Optional headers to include in webhook requests
            secret: Optional secret for signing webhook payloads
            description: Optional description of the webhook
            
        Returns:
            Webhook ID
        """
        webhook_id = f"webhook_{uuid.uuid4().hex[:8]}"
        
        webhook = WebhookConfig(
            endpoint=endpoint,
            events=events,
            headers=headers or {},
            secret=secret,
            description=description or f"Webhook for {', '.join(events)}",
        )
        
        async with self._lock:
            self.webhooks[webhook_id] = webhook
        
        await self._save_webhooks()
        
        logger.info(f"Registered webhook {webhook_id} for events: {', '.join(events)}")
        return webhook_id
    
    async def update_webhook(self, 
                      webhook_id: str, 
                      endpoint: Optional[str] = None,
                      events: Optional[List[str]] = None,
                      headers: Optional[Dict[str, str]] = None,
                      secret: Optional[str] = None,
                      description: Optional[str] = None) -> bool:
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
            True if updated, False otherwise
        """
        async with self._lock:
            if webhook_id not in self.webhooks:
                logger.error(f"Webhook not found: {webhook_id}")
                return False
            
            webhook = self.webhooks[webhook_id]
            
            if endpoint:
                webhook.endpoint = endpoint
            
            if events:
                webhook.events = events
            
            if headers:
                webhook.headers = headers
            
            if secret is not None:  # Allow setting to empty string to remove secret
                webhook.secret = secret
            
            if description:
                webhook.description = description
            
            webhook.updated_at = datetime.now().isoformat()
        
        await self._save_webhooks()
        
        logger.info(f"Updated webhook {webhook_id}")
        return True
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """
        Delete a webhook.
        
        Args:
            webhook_id: ID of the webhook to delete
            
        Returns:
            True if deleted, False otherwise
        """
        async with self._lock:
            if webhook_id not in self.webhooks:
                logger.error(f"Webhook not found: {webhook_id}")
                return False
            
            del self.webhooks[webhook_id]
        
        await self._save_webhooks()
        
        logger.info(f"Deleted webhook {webhook_id}")
        return True
    
    async def get_webhook(self, webhook_id: str) -> Optional[WebhookConfig]:
        """
        Get a webhook by ID.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Webhook configuration if found, None otherwise
        """
        async with self._lock:
            return self.webhooks.get(webhook_id)
    
    async def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all registered webhooks.
        
        Returns:
            List of webhook configurations
        """
        async with self._lock:
            return [
                {
                    "id": webhook_id,
                    "endpoint": webhook.endpoint,
                    "events": webhook.events,
                    "description": webhook.description or "",
                    "created_at": webhook.created_at,
                    "last_triggered": webhook.last_triggered,
                    "success_count": webhook.success_count,
                    "failure_count": webhook.failure_count
                }
                for webhook_id, webhook in self.webhooks.items()
            ]
    
    async def trigger_webhook(self, 
                       event: str, 
                       data: Dict[str, Any],
                       async_mode: bool = True) -> List[WebhookResponse]:
        """
        Trigger webhooks for a specific event.
        
        Args:
            event: Event name
            data: Data to send
            async_mode: Whether to trigger webhooks asynchronously
            
        Returns:
            List of webhook responses (only for synchronous mode)
        """
        # Find webhooks that should be triggered for this event
        async with self._lock:
            matching_webhooks = {
                webhook_id: webhook
                for webhook_id, webhook in self.webhooks.items()
                if event in webhook.events
            }
        
        if not matching_webhooks:
            logger.info(f"No webhooks registered for event: {event}")
            return []
        
        logger.info(f"Triggering {len(matching_webhooks)} webhooks for event: {event}")
        
        if async_mode:
            # Trigger webhooks asynchronously
            for webhook_id, webhook in matching_webhooks.items():
                task = asyncio.create_task(
                    self._send_webhook_request(webhook_id, webhook, event, data)
                )
                self._active_tasks.add(task)
                task.add_done_callback(self._active_tasks.discard)
            
            return []
        else:
            # Trigger webhooks synchronously
            tasks = [
                self._send_webhook_request(webhook_id, webhook, event, data)
                for webhook_id, webhook in matching_webhooks.items()
            ]
            
            return await asyncio.gather(*tasks)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create an aiohttp session.
        
        Returns:
            aiohttp.ClientSession
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session
    
    async def _send_webhook_request(self, 
                             webhook_id: str, 
                             webhook: WebhookConfig, 
                             event: str, 
                             data: Dict[str, Any]) -> WebhookResponse:
        """
        Send a webhook request.
        
        Args:
            webhook_id: Webhook ID
            webhook: Webhook configuration
            event: Event name
            data: Data to send
            
        Returns:
            Response information
        """
        endpoint = webhook.endpoint
        headers = webhook.headers.copy()
        
        # Prepare payload
        payload = {
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "webhook_id": webhook_id
        }
        
        # Add signature if secret is provided
        if webhook.secret:
            signature = self._generate_signature(payload, webhook.secret)
            headers["X-Webhook-Signature"] = signature
        
        # Add default headers
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("User-Agent", "Wiseflow-Webhook/1.0")
        
        response_info = WebhookResponse(
            webhook_id=webhook_id,
            event=event,
            timestamp=datetime.now().isoformat(),
            success=False
        )
        
        try:
            session = await self._get_session()
            
            async with session.post(
                endpoint,
                json=payload,
                headers=headers
            ) as response:
                # Update webhook stats
                async with self._lock:
                    if webhook_id in self.webhooks:
                        self.webhooks[webhook_id].last_triggered = datetime.now().isoformat()
                        
                        if 200 <= response.status < 300:
                            self.webhooks[webhook_id].success_count += 1
                            logger.info(f"Webhook {webhook_id} triggered successfully: {response.status}")
                        else:
                            self.webhooks[webhook_id].failure_count += 1
                            logger.warning(f"Webhook {webhook_id} failed with status code: {response.status}")
                
                response_text = await response.text()
                
                response_info.status_code = response.status
                response_info.response = response_text[:1000]  # Limit response text
                response_info.success = 200 <= response.status < 300
            
        except Exception as e:
            async with self._lock:
                if webhook_id in self.webhooks:
                    self.webhooks[webhook_id].failure_count += 1
            
            logger.error(f"Failed to trigger webhook {webhook_id}: {str(e)}")
            
            response_info.error = str(e)
            response_info.success = False
        
        # Save updated webhook stats
        await self._save_webhooks()
        
        return response_info
    
    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """
        Generate a signature for the webhook payload.
        
        Args:
            payload: Webhook payload
            secret: Secret key
            
        Returns:
            Signature string
        """
        payload_str = json.dumps(payload, sort_keys=True)
        hmac_obj = hmac.new(
            secret.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(hmac_obj.digest()).decode('utf-8')
    
    def verify_signature(self, 
                        payload: Dict[str, Any], 
                        signature: str, 
                        secret: str) -> bool:
        """
        Verify a webhook signature.
        
        Args:
            payload: Webhook payload
            signature: Signature to verify
            secret: Secret key
            
        Returns:
            True if signature is valid, False otherwise
        """
        expected_signature = self._generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)
    
    async def cleanup(self):
        """
        Clean up resources.
        
        This should be called when shutting down the application.
        """
        # Cancel any active tasks
        for task in self._active_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        
        # Close the session
        if self._session and not self._session.closed:
            await self._session.close()

# Create a singleton instance
_webhook_manager = None

async def get_webhook_manager() -> WebhookManager:
    """
    Get the webhook manager instance.
    
    Returns:
        Webhook manager instance
    """
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager
"""

