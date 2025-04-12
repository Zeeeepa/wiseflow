"""
Notification module for Wiseflow dashboard.

This module provides functionality for sending and managing notifications about new insights,
trends, and system events.
"""

import os
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ...core.utils.pb_api import PbTalker

logger = logging.getLogger(__name__)

class Notification:
    """Class representing a notification."""
    
    def __init__(self, title: str, message: str, notification_type: str = "info", 
                notification_id: Optional[str] = None, timestamp: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a notification.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification (info, warning, error, success)
            notification_id: Optional notification ID (generated if not provided)
            timestamp: Optional timestamp (current time if not provided)
            metadata: Optional metadata
        """
        self.notification_id = notification_id or f"notification_{uuid.uuid4().hex[:8]}"
        self.title = title
        self.message = message
        self.notification_type = notification_type
        self.timestamp = timestamp or datetime.now().isoformat()
        self.metadata = metadata or {}
        self.read = False
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the notification to a dictionary.
        
        Returns:
            Dictionary representation of the notification
        """
        return {
            "notification_id": self.notification_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "read": self.read
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Notification':
        """
        Create a notification from a dictionary.
        
        Args:
            data: Dictionary representation of a notification
            
        Returns:
            Notification object
        """
        notification = cls(
            title=data["title"],
            message=data["message"],
            notification_type=data["notification_type"],
            notification_id=data["notification_id"],
            timestamp=data["timestamp"],
            metadata=data["metadata"]
        )
        notification.read = data.get("read", False)
        return notification


class NotificationManager:
    """Class for managing notifications."""
    
    def __init__(self, pb_client: Optional[PbTalker] = None):
        """
        Initialize the notification manager.
        
        Args:
            pb_client: PocketBase client for database operations
        """
        self.pb_client = pb_client
        self.notifications = {}
        self.settings = {
            "email": {
                "enabled": False,
                "smtp_server": "",
                "smtp_port": 587,
                "smtp_username": "",
                "smtp_password": "",
                "from_address": "",
                "recipients": []
            },
            "slack": {
                "enabled": False,
                "webhook_url": ""
            },
            "web": {
                "enabled": True
            }
        }
        
    def configure(self, settings: Dict[str, Any]) -> bool:
        """
        Configure notification settings.
        
        Args:
            settings: Notification settings
            
        Returns:
            True if successful, False otherwise
        """
        # Update settings
        for channel, channel_settings in settings.items():
            if channel in self.settings:
                self.settings[channel].update(channel_settings)
        
        # Save settings to database if client is available
        if self.pb_client:
            try:
                settings_json = json.dumps(self.settings)
                
                # Check if settings already exist
                existing_settings = self.pb_client.read("settings", filter="key='notification_settings'")
                
                if existing_settings:
                    # Update existing settings
                    record_id = existing_settings[0].get("id")
                    self.pb_client.update("settings", record_id, {"value": settings_json})
                else:
                    # Create new settings
                    self.pb_client.add("settings", {
                        "key": "notification_settings",
                        "value": settings_json
                    })
                
                logger.info("Notification settings saved to database")
                return True
            except Exception as e:
                logger.error(f"Error saving notification settings: {e}")
                return False
        
        return True
    
    def create_notification(self, title: str, message: str, notification_type: str = "info", 
                           metadata: Optional[Dict[str, Any]] = None) -> Notification:
        """
        Create a new notification.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            metadata: Optional metadata
            
        Returns:
            The created notification
        """
        notification = Notification(title, message, notification_type, metadata=metadata)
        self.notifications[notification.notification_id] = notification
        
        # Save to database if client is available
        if self.pb_client:
            self._save_notification(notification)
        
        # Send notification through configured channels
        self._send_notification(notification)
        
        return notification
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """
        Get a notification by ID.
        
        Args:
            notification_id: Notification ID
            
        Returns:
            Notification if found, None otherwise
        """
        # Try to get from memory
        if notification_id in self.notifications:
            return self.notifications[notification_id]
        
        # Try to get from database
        if self.pb_client:
            notification_data = self.pb_client.view("notifications", notification_id)
            if notification_data:
                try:
                    notification_dict = json.loads(notification_data.get("data", "{}"))
                    notification = Notification.from_dict(notification_dict)
                    self.notifications[notification_id] = notification
                    return notification
                except Exception as e:
                    logger.error(f"Error loading notification: {e}")
        
        return None
    
    def list_notifications(self, filter_query: str = "", limit: int = 10, 
                          offset: int = 0) -> List[Dict[str, Any]]:
        """
        List notifications.
        
        Args:
            filter_query: Optional filter query
            limit: Maximum number of notifications to return
            offset: Offset for pagination
            
        Returns:
            List of notification dictionaries
        """
        if self.pb_client:
            try:
                notification_records = self.pb_client.read("notifications", filter=filter_query)
                notifications = []
                
                for record in notification_records:
                    try:
                        notification_dict = json.loads(record.get("data", "{}"))
                        notifications.append(notification_dict)
                    except Exception as e:
                        logger.warning(f"Error parsing notification record: {e}")
                
                # Apply pagination
                paginated_notifications = notifications[offset:offset+limit]
                
                return paginated_notifications
            except Exception as e:
                logger.error(f"Error listing notifications: {e}")
                return []
        else:
            # Return from memory if no database client
            notifications = [n.to_dict() for n in self.notifications.values()]
            
            # Sort by timestamp (newest first)
            notifications.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Apply pagination
            paginated_notifications = notifications[offset:offset+limit]
            
            return paginated_notifications
    
    def mark_as_read(self, notification_id: str) -> bool:
        """
        Mark a notification as read.
        
        Args:
            notification_id: Notification ID
            
        Returns:
            True if successful, False otherwise
        """
        notification = self.get_notification(notification_id)
        if not notification:
            return False
        
        notification.read = True
        
        # Save to database if client is available
        if self.pb_client:
            self._save_notification(notification)
        
        return True
    
    def delete_notification(self, notification_id: str) -> bool:
        """
        Delete a notification.
        
        Args:
            notification_id: Notification ID
            
        Returns:
            True if successful, False otherwise
        """
        if notification_id in self.notifications:
            del self.notifications[notification_id]
        
        # Delete from database if client is available
        if self.pb_client:
            try:
                # Find the record ID
                notification_records = self.pb_client.read("notifications", filter=f"notification_id='{notification_id}'")
                if notification_records:
                    record_id = notification_records[0].get("id")
                    if record_id:
                        self.pb_client.delete("notifications", record_id)
                        return True
            except Exception as e:
                logger.error(f"Error deleting notification: {e}")
                return False
        
        return True
    
    def _save_notification(self, notification: Notification) -> bool:
        """
        Save a notification to the database.
        
        Args:
            notification: Notification to save
            
        Returns:
            True if successful, False otherwise
        """
        if not self.pb_client:
            return False
        
        try:
            notification_dict = notification.to_dict()
            notification_json = json.dumps(notification_dict)
            
            # Check if notification already exists
            existing_records = self.pb_client.read("notifications", filter=f"notification_id='{notification.notification_id}'")
            
            if existing_records:
                # Update existing record
                record_id = existing_records[0].get("id")
                self.pb_client.update("notifications", record_id, {"data": notification_json})
            else:
                # Create new record
                self.pb_client.add("notifications", {
                    "notification_id": notification.notification_id,
                    "title": notification.title,
                    "data": notification_json
                })
            
            return True
        except Exception as e:
            logger.error(f"Error saving notification: {e}")
            return False
    
    def _send_notification(self, notification: Notification) -> None:
        """
        Send a notification through configured channels.
        
        Args:
            notification: Notification to send
        """
        # Send email notification if enabled
        if self.settings["email"]["enabled"]:
            self._send_email_notification(notification)
        
        # Send Slack notification if enabled
        if self.settings["slack"]["enabled"]:
            self._send_slack_notification(notification)
    
    def _send_email_notification(self, notification: Notification) -> bool:
        """
        Send an email notification.
        
        Args:
            notification: Notification to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get email settings
            smtp_server = self.settings["email"]["smtp_server"]
            smtp_port = self.settings["email"]["smtp_port"]
            smtp_username = self.settings["email"]["smtp_username"]
            smtp_password = self.settings["email"]["smtp_password"]
            from_address = self.settings["email"]["from_address"]
            recipients = self.settings["email"]["recipients"]
            
            if not smtp_server or not from_address or not recipients:
                logger.warning("Email notification settings incomplete")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg["From"] = from_address
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = f"Wiseflow Notification: {notification.title}"
            
            # Create HTML body
            html = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; }}
                        .notification {{ padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                        .info {{ background-color: #e3f2fd; border-left: 5px solid #2196F3; }}
                        .warning {{ background-color: #fff9c4; border-left: 5px solid #ffc107; }}
                        .error {{ background-color: #ffebee; border-left: 5px solid #f44336; }}
                        .success {{ background-color: #e8f5e9; border-left: 5px solid #4caf50; }}
                    </style>
                </head>
                <body>
                    <div class="notification {notification.notification_type}">
                        <h2>{notification.title}</h2>
                        <p>{notification.message}</p>
                        <p><small>Sent at: {notification.timestamp}</small></p>
                    </div>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html, "html"))
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent: {notification.title}")
            return True
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False
    
    def _send_slack_notification(self, notification: Notification) -> bool:
        """
        Send a Slack notification.
        
        Args:
            notification: Notification to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get Slack settings
            webhook_url = self.settings["slack"]["webhook_url"]
            
            if not webhook_url:
                logger.warning("Slack notification settings incomplete")
                return False
            
            # Create message payload
            payload = {
                "text": f"*{notification.title}*\n{notification.message}",
                "attachments": [
                    {
                        "color": self._get_slack_color(notification.notification_type),
                        "fields": [
                            {
                                "title": "Type",
                                "value": notification.notification_type,
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": notification.timestamp,
                                "short": True
                            }
                        ]
                    }
                ]
            }
            
            # Add metadata fields if available
            if notification.metadata:
                for key, value in notification.metadata.items():
                    payload["attachments"][0]["fields"].append({
                        "title": key,
                        "value": str(value),
                        "short": True
                    })
            
            # Send to Slack webhook
            import requests
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            
            logger.info(f"Slack notification sent: {notification.title}")
            return True
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False
    
    def _get_slack_color(self, notification_type: str) -> str:
        """
        Get Slack color for notification type.
        
        Args:
            notification_type: Type of notification
            
        Returns:
            Slack color code
        """
        color_map = {
            "info": "#2196F3",
            "warning": "#ffc107",
            "error": "#f44336",
            "success": "#4caf50"
        }
        return color_map.get(notification_type, "#2196F3")


# Create a singleton instance
notification_manager = NotificationManager()

def create_notification(title: str, message: str, notification_type: str = "info", 
                       metadata: Optional[Dict[str, Any]] = None) -> Notification:
    """
    Create a new notification.
    
    Args:
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        metadata: Optional metadata
        
    Returns:
        The created notification
    """
    return notification_manager.create_notification(title, message, notification_type, metadata)

def get_notification(notification_id: str) -> Optional[Notification]:
    """
    Get a notification by ID.
    
    Args:
        notification_id: Notification ID
        
    Returns:
        Notification if found, None otherwise
    """
    return notification_manager.get_notification(notification_id)

def list_notifications(filter_query: str = "", limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """
    List notifications.
    
    Args:
        filter_query: Optional filter query
        limit: Maximum number of notifications to return
        offset: Offset for pagination
        
    Returns:
        List of notification dictionaries
    """
    return notification_manager.list_notifications(filter_query, limit, offset)

def mark_as_read(notification_id: str) -> bool:
    """
    Mark a notification as read.
    
    Args:
        notification_id: Notification ID
        
    Returns:
        True if successful, False otherwise
    """
    return notification_manager.mark_as_read(notification_id)

def delete_notification(notification_id: str) -> bool:
    """
    Delete a notification.
    
    Args:
        notification_id: Notification ID
        
    Returns:
        True if successful, False otherwise
    """
    return notification_manager.delete_notification(notification_id)

def configure_notifications(settings: Dict[str, Any]) -> bool:
    """
    Configure notification settings.
    
    Args:
        settings: Notification settings
        
    Returns:
        True if successful, False otherwise
    """
    return notification_manager.configure(settings)
