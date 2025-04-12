"""
Notification system for Wiseflow dashboard.

This module provides functionality for sending notifications about new insights,
trends, and other events.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import json
import os
from datetime import datetime
import uuid

from core.utils.pb_api import PbTalker

logger = logging.getLogger(__name__)

class Notification:
    """Base class for notifications."""
    
    def __init__(
        self,
        title: str,
        message: str,
        notification_type: str,
        source_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize a notification.
        
        Args:
            title: The notification title
            message: The notification message
            notification_type: The type of notification
            source_id: The ID of the source that triggered the notification
            user_id: The ID of the user to notify
            metadata: Additional metadata
        """
        self.notification_id = f"notification_{uuid.uuid4().hex[:8]}"
        self.title = title
        self.message = message
        self.type = notification_type
        self.source_id = source_id
        self.user_id = user_id
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.read = False
        self.read_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the notification to a dictionary."""
        return {
            "notification_id": self.notification_id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "source_id": self.source_id,
            "user_id": self.user_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "read": self.read,
            "read_at": self.read_at.isoformat() if self.read_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Notification':
        """Create a notification from a dictionary."""
        notification = cls(
            title=data["title"],
            message=data["message"],
            notification_type=data["type"],
            source_id=data.get("source_id"),
            user_id=data.get("user_id"),
            metadata=data.get("metadata", {})
        )
        
        notification.notification_id = data.get("notification_id", notification.notification_id)
        notification.read = data.get("read", False)
        
        # Set timestamps
        if data.get("created_at"):
            try:
                notification.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
                
        if data.get("read_at") and notification.read:
            try:
                notification.read_at = datetime.fromisoformat(data["read_at"])
            except (ValueError, TypeError):
                pass
        
        return notification
    
    def mark_as_read(self) -> None:
        """Mark the notification as read."""
        self.read = True
        self.read_at = datetime.now()


class InsightNotification(Notification):
    """Notification for new insights."""
    
    def __init__(
        self,
        title: str,
        message: str,
        insight_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize an insight notification."""
        super().__init__(
            title=title,
            message=message,
            notification_type="insight",
            source_id=insight_id,
            user_id=user_id,
            metadata=metadata or {}
        )


class TrendNotification(Notification):
    """Notification for trend changes."""
    
    def __init__(
        self,
        title: str,
        message: str,
        trend_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize a trend notification."""
        super().__init__(
            title=title,
            message=message,
            notification_type="trend",
            source_id=trend_id,
            user_id=user_id,
            metadata=metadata or {}
        )


class SystemNotification(Notification):
    """Notification for system events."""
    
    def __init__(
        self,
        title: str,
        message: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize a system notification."""
        super().__init__(
            title=title,
            message=message,
            notification_type="system",
            source_id=None,
            user_id=user_id,
            metadata=metadata or {}
        )


class NotificationManager:
    """Manages notifications."""
    
    def __init__(self, pb: PbTalker):
        """Initialize the notification manager."""
        self.pb = pb
    
    def create_notification(self, notification: Notification) -> str:
        """Create a new notification."""
        notification_data = notification.to_dict()
        
        # Add notification to database
        notification_id = self.pb.add("notifications", notification_data)
        
        if not notification_id:
            logger.error(f"Failed to save notification: {notification.title}")
        
        return notification_id
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID."""
        notifications = self.pb.read("notifications", filter=f'notification_id="{notification_id}"')
        
        if notifications:
            notification_data = notifications[0]
            notification_type = notification_data.get("type", "")
            
            if notification_type == "insight":
                return InsightNotification.from_dict(notification_data)
            elif notification_type == "trend":
                return TrendNotification.from_dict(notification_data)
            elif notification_type == "system":
                return SystemNotification.from_dict(notification_data)
            else:
                return Notification.from_dict(notification_data)
        
        return None
    
    def get_notifications(self, user_id: Optional[str] = None, unread_only: bool = False) -> List[Notification]:
        """Get notifications for a user."""
        filter_str = []
        
        if user_id:
            filter_str.append(f'user_id="{user_id}"')
        
        if unread_only:
            filter_str.append('read=false')
        
        filter_query = " && ".join(filter_str) if filter_str else ""
        
        notifications_data = self.pb.read("notifications", filter=filter_query)
        
        notifications = []
        for notification_data in notifications_data:
            notification_type = notification_data.get("type", "")
            
            if notification_type == "insight":
                notification = InsightNotification.from_dict(notification_data)
            elif notification_type == "trend":
                notification = TrendNotification.from_dict(notification_data)
            elif notification_type == "system":
                notification = SystemNotification.from_dict(notification_data)
            else:
                notification = Notification.from_dict(notification_data)
            
            notifications.append(notification)
        
        return notifications
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        notification = self.get_notification(notification_id)
        
        if notification:
            notification.mark_as_read()
            
            # Update notification in database
            notifications = self.pb.read("notifications", filter=f'notification_id="{notification_id}"')
            
            if notifications:
                return bool(self.pb.update("notifications", notifications[0]["id"], notification.to_dict()))
        
        return False
    
    def mark_all_as_read(self, user_id: str) -> bool:
        """Mark all notifications for a user as read."""
        notifications = self.get_notifications(user_id, unread_only=True)
        
        success = True
        for notification in notifications:
            if not self.mark_as_read(notification.notification_id):
                success = False
        
        return success
    
    def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification."""
        notifications = self.pb.read("notifications", filter=f'notification_id="{notification_id}"')
        
        if notifications:
            return self.pb.delete("notifications", notifications[0]["id"])
        
        return False
    
    def create_insight_notification(
        self,
        title: str,
        message: str,
        insight_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a notification for a new insight."""
        notification = InsightNotification(
            title=title,
            message=message,
            insight_id=insight_id,
            user_id=user_id,
            metadata=metadata
        )
        
        return self.create_notification(notification)
    
    def create_trend_notification(
        self,
        title: str,
        message: str,
        trend_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a notification for a trend change."""
        notification = TrendNotification(
            title=title,
            message=message,
            trend_id=trend_id,
            user_id=user_id,
            metadata=metadata
        )
        
        return self.create_notification(notification)
    
    def create_system_notification(
        self,
        title: str,
        message: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a system notification."""
        notification = SystemNotification(
            title=title,
            message=message,
            user_id=user_id,
            metadata=metadata
        )
        
        return self.create_notification(notification)


def configure_notifications(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Configure notification settings.
    
    Args:
        settings: Notification settings
    
    Returns:
        Updated notification settings
    """
    # Validate and normalize settings
    normalized_settings = {
        "enabled": settings.get("enabled", True),
        "types": {
            "insight": settings.get("types", {}).get("insight", True),
            "trend": settings.get("types", {}).get("trend", True),
            "system": settings.get("types", {}).get("system", True)
        },
        "delivery_methods": {
            "in_app": settings.get("delivery_methods", {}).get("in_app", True),
            "email": settings.get("delivery_methods", {}).get("email", False),
            "webhook": settings.get("delivery_methods", {}).get("webhook", False)
        },
        "webhook_url": settings.get("webhook_url", ""),
        "email_settings": settings.get("email_settings", {})
    }
    
    return normalized_settings
