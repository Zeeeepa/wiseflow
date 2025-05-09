"""
Unit tests for the webhook functionality.

This module contains unit tests for the webhook functionality.
"""

import json
import pytest
import uuid
from unittest.mock import MagicMock, patch, AsyncMock

from core.export.webhook import WebhookManager, get_webhook_manager

pytestmark = pytest.mark.unit


@pytest.fixture
def webhook_manager():
    """Create a webhook manager for testing."""
    return WebhookManager()


def test_webhook_manager_singleton():
    """Test that the webhook manager is a singleton."""
    manager1 = get_webhook_manager()
    manager2 = get_webhook_manager()
    assert manager1 is manager2


def test_register_webhook(webhook_manager):
    """Test registering a webhook."""
    # Register a webhook
    webhook_id = webhook_manager.register_webhook(
        endpoint="https://example.com/webhook",
        events=["test.event"],
        headers={"X-Test-Header": "test-value"},
        secret="test-secret",
        description="Test webhook"
    )
    
    # Check that the webhook was registered
    assert webhook_id is not None
    assert webhook_id in webhook_manager._webhooks
    
    # Check the webhook data
    webhook = webhook_manager._webhooks[webhook_id]
    assert webhook["endpoint"] == "https://example.com/webhook"
    assert webhook["events"] == ["test.event"]
    assert webhook["headers"] == {"X-Test-Header": "test-value"}
    assert webhook["secret"] == "test-secret"
    assert webhook["description"] == "Test webhook"


def test_list_webhooks(webhook_manager):
    """Test listing webhooks."""
    # Register webhooks
    webhook_id1 = webhook_manager.register_webhook(
        endpoint="https://example.com/webhook1",
        events=["test.event1"],
        headers={"X-Test-Header": "test-value1"},
        secret="test-secret1",
        description="Test webhook 1"
    )
    webhook_id2 = webhook_manager.register_webhook(
        endpoint="https://example.com/webhook2",
        events=["test.event2"],
        headers={"X-Test-Header": "test-value2"},
        secret="test-secret2",
        description="Test webhook 2"
    )
    
    # List webhooks
    webhooks = webhook_manager.list_webhooks()
    
    # Check the webhooks
    assert len(webhooks) == 2
    assert webhooks[0]["webhook_id"] == webhook_id1
    assert webhooks[0]["endpoint"] == "https://example.com/webhook1"
    assert webhooks[0]["events"] == ["test.event1"]
    assert webhooks[0]["headers"] == {"X-Test-Header": "test-value1"}
    assert webhooks[0]["secret"] == "test-secret1"
    assert webhooks[0]["description"] == "Test webhook 1"
    assert webhooks[1]["webhook_id"] == webhook_id2
    assert webhooks[1]["endpoint"] == "https://example.com/webhook2"
    assert webhooks[1]["events"] == ["test.event2"]
    assert webhooks[1]["headers"] == {"X-Test-Header": "test-value2"}
    assert webhooks[1]["secret"] == "test-secret2"
    assert webhooks[1]["description"] == "Test webhook 2"


def test_get_webhook(webhook_manager):
    """Test getting a webhook."""
    # Register a webhook
    webhook_id = webhook_manager.register_webhook(
        endpoint="https://example.com/webhook",
        events=["test.event"],
        headers={"X-Test-Header": "test-value"},
        secret="test-secret",
        description="Test webhook"
    )
    
    # Get the webhook
    webhook = webhook_manager.get_webhook(webhook_id)
    
    # Check the webhook
    assert webhook is not None
    assert webhook["endpoint"] == "https://example.com/webhook"
    assert webhook["events"] == ["test.event"]
    assert webhook["headers"] == {"X-Test-Header": "test-value"}
    assert webhook["secret"] == "test-secret"
    assert webhook["description"] == "Test webhook"


def test_get_webhook_not_found(webhook_manager):
    """Test getting a non-existent webhook."""
    # Get a non-existent webhook
    webhook = webhook_manager.get_webhook("non-existent-webhook-id")
    
    # Check that the webhook is None
    assert webhook is None


def test_update_webhook(webhook_manager):
    """Test updating a webhook."""
    # Register a webhook
    webhook_id = webhook_manager.register_webhook(
        endpoint="https://example.com/webhook",
        events=["test.event"],
        headers={"X-Test-Header": "test-value"},
        secret="test-secret",
        description="Test webhook"
    )
    
    # Update the webhook
    success = webhook_manager.update_webhook(
        webhook_id=webhook_id,
        endpoint="https://example.com/updated-webhook",
        events=["updated.event"],
        headers={"X-Updated-Header": "updated-value"},
        secret="updated-secret",
        description="Updated webhook"
    )
    
    # Check that the update was successful
    assert success
    
    # Get the updated webhook
    webhook = webhook_manager.get_webhook(webhook_id)
    
    # Check the updated webhook
    assert webhook is not None
    assert webhook["endpoint"] == "https://example.com/updated-webhook"
    assert webhook["events"] == ["updated.event"]
    assert webhook["headers"] == {"X-Updated-Header": "updated-value"}
    assert webhook["secret"] == "updated-secret"
    assert webhook["description"] == "Updated webhook"


def test_update_webhook_partial(webhook_manager):
    """Test partially updating a webhook."""
    # Register a webhook
    webhook_id = webhook_manager.register_webhook(
        endpoint="https://example.com/webhook",
        events=["test.event"],
        headers={"X-Test-Header": "test-value"},
        secret="test-secret",
        description="Test webhook"
    )
    
    # Update only the endpoint and events
    success = webhook_manager.update_webhook(
        webhook_id=webhook_id,
        endpoint="https://example.com/updated-webhook",
        events=["updated.event"]
    )
    
    # Check that the update was successful
    assert success
    
    # Get the updated webhook
    webhook = webhook_manager.get_webhook(webhook_id)
    
    # Check the updated webhook
    assert webhook is not None
    assert webhook["endpoint"] == "https://example.com/updated-webhook"
    assert webhook["events"] == ["updated.event"]
    assert webhook["headers"] == {"X-Test-Header": "test-value"}
    assert webhook["secret"] == "test-secret"
    assert webhook["description"] == "Test webhook"


def test_update_webhook_not_found(webhook_manager):
    """Test updating a non-existent webhook."""
    # Update a non-existent webhook
    success = webhook_manager.update_webhook(
        webhook_id="non-existent-webhook-id",
        endpoint="https://example.com/updated-webhook",
        events=["updated.event"],
        headers={"X-Updated-Header": "updated-value"},
        secret="updated-secret",
        description="Updated webhook"
    )
    
    # Check that the update failed
    assert not success


def test_delete_webhook(webhook_manager):
    """Test deleting a webhook."""
    # Register a webhook
    webhook_id = webhook_manager.register_webhook(
        endpoint="https://example.com/webhook",
        events=["test.event"],
        headers={"X-Test-Header": "test-value"},
        secret="test-secret",
        description="Test webhook"
    )
    
    # Delete the webhook
    success = webhook_manager.delete_webhook(webhook_id)
    
    # Check that the deletion was successful
    assert success
    
    # Check that the webhook is no longer in the webhooks
    assert webhook_id not in webhook_manager._webhooks
    
    # Try to get the deleted webhook
    webhook = webhook_manager.get_webhook(webhook_id)
    
    # Check that the webhook is None
    assert webhook is None


def test_delete_webhook_not_found(webhook_manager):
    """Test deleting a non-existent webhook."""
    # Delete a non-existent webhook
    success = webhook_manager.delete_webhook("non-existent-webhook-id")
    
    # Check that the deletion failed
    assert not success


@patch("core.export.webhook.requests.post")
def test_trigger_webhook_sync(mock_post, webhook_manager):
    """Test triggering a webhook synchronously."""
    # Set up the mock
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"success": True}
    
    # Register a webhook
    webhook_id = webhook_manager.register_webhook(
        endpoint="https://example.com/webhook",
        events=["test.event"],
        headers={"X-Test-Header": "test-value"},
        secret="test-secret",
        description="Test webhook"
    )
    
    # Trigger the webhook
    responses = webhook_manager.trigger_webhook(
        event="test.event",
        data={"test": "value"},
        async_mode=False
    )
    
    # Check that the webhook was triggered
    assert len(responses) == 1
    assert responses[0]["webhook_id"] == webhook_id
    assert responses[0]["status_code"] == 200
    assert responses[0]["response"] == {"success": True}
    
    # Check that the request was made correctly
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://example.com/webhook"
    assert kwargs["headers"]["X-Test-Header"] == "test-value"
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert kwargs["headers"]["X-Webhook-Event"] == "test.event"
    assert "X-Webhook-Signature" in kwargs["headers"]
    assert json.loads(kwargs["data"]) == {
        "event": "test.event",
        "data": {"test": "value"},
        "timestamp": kwargs["json"]["timestamp"]
    }


@patch("core.export.webhook.aiohttp.ClientSession")
@pytest.mark.asyncio
async def test_trigger_webhook_async(mock_session, webhook_manager):
    """Test triggering a webhook asynchronously."""
    # Set up the mock
    mock_session_instance = AsyncMock()
    mock_session.return_value.__aenter__.return_value = mock_session_instance
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"success": True}
    mock_session_instance.post.return_value.__aenter__.return_value = mock_response
    
    # Register a webhook
    webhook_id = webhook_manager.register_webhook(
        endpoint="https://example.com/webhook",
        events=["test.event"],
        headers={"X-Test-Header": "test-value"},
        secret="test-secret",
        description="Test webhook"
    )
    
    # Trigger the webhook
    responses = webhook_manager.trigger_webhook(
        event="test.event",
        data={"test": "value"},
        async_mode=True
    )
    
    # Check that the responses are empty (async mode)
    assert len(responses) == 0
    
    # Check that the request was made correctly
    mock_session_instance.post.assert_called_once()
    args, kwargs = mock_session_instance.post.call_args
    assert args[0] == "https://example.com/webhook"
    assert kwargs["headers"]["X-Test-Header"] == "test-value"
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert kwargs["headers"]["X-Webhook-Event"] == "test.event"
    assert "X-Webhook-Signature" in kwargs["headers"]
    assert kwargs["json"] == {
        "event": "test.event",
        "data": {"test": "value"},
        "timestamp": kwargs["json"]["timestamp"]
    }

