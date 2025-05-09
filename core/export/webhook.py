"""
Webhook Module for Wiseflow.

This module provides functionality for integrating with external systems via webhooks.
"""

import logging
import json
import os
import time
import threading
import requests
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import hmac
import hashlib
import base64

logger = logging.getLogger(__name__)

class WebhookManager:
    """Manager for webhook operations."""
    
    def __init__(self, config_path: str = "webhooks.json"):
        """
        Initialize the webhook manager.
        
        Args:
            config_path: Path to the webhook configuration file
        """
        self.config_path = config_path
        self.webhooks = {}
        self.secret_key = os.environ.get("WEBHOOK_SECRET_KEY", "wiseflow-webhook-secret")
        
        # Load webhooks if config file exists
        self._load_webhooks()
    
    def _load_webhooks(self):
        """Load webhooks from the configuration file if it exists."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.webhooks = json.load(f)
                    
                logger.info(f"Loaded {len(self.webhooks)} webhooks")
            except Exception as e:
                logger.error(f"Failed to load webhooks: {str(e)}")
    
    def _save_webhooks(self):
        """Save webhooks to the configuration file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.webhooks, f, indent=2)
                
            logger.info(f"Saved {len(self.webhooks)} webhooks")
        except Exception as e:
            logger.error(f"Failed to save webhooks: {str(e)}")
    
    def register_webhook(self, 
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
        webhook_id = f"webhook_{len(self.webhooks) + 1}"
        
        self.webhooks[webhook_id] = {
            "endpoint": endpoint,
            "events": events,
            "headers": headers or {},
            "secret": secret,
            "description": description or f"Webhook for {', '.join(events)}",
            "created_at": datetime.now().isoformat(),
            "last_triggered": None,
            "success_count": 0,
            "failure_count": 0
        }
        
        self._save_webhooks()
        
        logger.info(f"Registered webhook {webhook_id} for events: {', '.join(events)}")
        return webhook_id
    
    def update_webhook(self, 
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
        if webhook_id not in self.webhooks:
            logger.error(f"Webhook not found: {webhook_id}")
            return False
        
        webhook = self.webhooks[webhook_id]
        
        if endpoint:
            webhook["endpoint"] = endpoint
        
        if events:
            webhook["events"] = events
        
        if headers:
            webhook["headers"] = headers
        
        if secret is not None:  # Allow setting to empty string to remove secret
            webhook["secret"] = secret
        
        if description:
            webhook["description"] = description
        
        webhook["updated_at"] = datetime.now().isoformat()
        
        self._save_webhooks()
        
        logger.info(f"Updated webhook {webhook_id}")
        return True
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """
        Delete a webhook.
        
        Args:
            webhook_id: ID of the webhook to delete
            
        Returns:
            True if deleted, False otherwise
        """
        if webhook_id not in self.webhooks:
            logger.error(f"Webhook not found: {webhook_id}")
            return False
        
        del self.webhooks[webhook_id]
        self._save_webhooks()
        
        logger.info(f"Deleted webhook {webhook_id}")
        return True
    
    def get_webhook(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a webhook by ID.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Webhook configuration if found, None otherwise
        """
        return self.webhooks.get(webhook_id)
    
    def list_webhooks(self) -> List[Dict[str, Any]]:
        """
        List all registered webhooks.
        
        Returns:
            List of webhook configurations
        """
        return [
            {
                "id": webhook_id,
                "endpoint": webhook["endpoint"],
                "events": webhook["events"],
                "description": webhook.get("description", ""),
                "created_at": webhook["created_at"],
                "last_triggered": webhook.get("last_triggered"),
                "success_count": webhook.get("success_count", 0),
                "failure_count": webhook.get("failure_count", 0)
            }
            for webhook_id, webhook in self.webhooks.items()
        ]
    
    def trigger_webhook(self, 
                       event: str, 
                       data: Dict[str, Any],
                       async_mode: bool = True) -> List[Dict[str, Any]]:
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
        matching_webhooks = {
            webhook_id: webhook
            for webhook_id, webhook in self.webhooks.items()
            if event in webhook["events"]
        }
        
        if not matching_webhooks:
            logger.info(f"No webhooks registered for event: {event}")
            return []
        
        logger.info(f"Triggering {len(matching_webhooks)} webhooks for event: {event}")
        
        if async_mode:
            # Trigger webhooks asynchronously
            for webhook_id, webhook in matching_webhooks.items():
                thread = threading.Thread(
                    target=self._send_webhook_request,
                    args=(webhook_id, webhook, event, data)
                )
                thread.daemon = True
                thread.start()
            
            return []
        else:
            # Trigger webhooks synchronously
            responses = []
            
            for webhook_id, webhook in matching_webhooks.items():
                response = self._send_webhook_request(webhook_id, webhook, event, data)
                responses.append(response)
            
            return responses
    
    def _send_webhook_request(self, 
                             webhook_id: str, 
                             webhook: Dict[str, Any], 
                             event: str, 
                             data: Dict[str, Any]) -> Dict[str, Any]:
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
        endpoint = webhook["endpoint"]
        headers = webhook.get("headers", {}).copy()
        
        # Prepare payload
        payload = {
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "webhook_id": webhook_id
        }
        
        # Add signature if secret is provided
        if webhook.get("secret"):
            signature = self._generate_signature(payload, webhook["secret"])
            headers["X-Webhook-Signature"] = signature
        
        # Add default headers
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("User-Agent", "Wiseflow-Webhook/1.0")
        
        response_info = {
            "webhook_id": webhook_id,
            "event": event,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            # Update webhook stats
            self.webhooks[webhook_id]["last_triggered"] = datetime.now().isoformat()
            
            if response.status_code >= 200 and response.status_code < 300:
                self.webhooks[webhook_id]["success_count"] = self.webhooks[webhook_id].get("success_count", 0) + 1
                logger.info(f"Webhook {webhook_id} triggered successfully: {response.status_code}")
            else:
                self.webhooks[webhook_id]["failure_count"] = self.webhooks[webhook_id].get("failure_count", 0) + 1
                logger.warning(f"Webhook {webhook_id} failed with status code: {response.status_code}")
            
            response_info.update({
                "status_code": response.status_code,
                "response": response.text[:1000],  # Limit response text
                "success": response.status_code >= 200 and response.status_code < 300
            })
            
        except Exception as e:
            self.webhooks[webhook_id]["failure_count"] = self.webhooks[webhook_id].get("failure_count", 0) + 1
            logger.error(f"Failed to trigger webhook {webhook_id}: {str(e)}")
            
            response_info.update({
                "error": str(e),
                "success": False
            })
        
        # Save updated webhook stats
        self._save_webhooks()
        
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

# Singleton instance
_webhook_manager = None

def get_webhook_manager() -> WebhookManager:
    """
    Get the singleton instance of the webhook manager.
    
    Returns:
        WebhookManager: The webhook manager instance
    """
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager
