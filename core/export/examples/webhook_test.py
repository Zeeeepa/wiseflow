#!/usr/bin/env python3
"""
Test script for the webhook functionality.
"""

import os
import sys
import logging
import json
from datetime import datetime
import threading
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs

# Add parent directory to path to allow importing from core.export
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from core.export.webhook import get_webhook_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variable to store received webhooks
received_webhooks = []

class WebhookHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for webhooks."""
    
    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            payload = json.loads(post_data.decode('utf-8'))
            logger.info(f"Received webhook: {json.dumps(payload, indent=2)}")
            
            # Store the webhook
            received_webhooks.append({
                "payload": payload,
                "headers": dict(self.headers),
                "timestamp": datetime.now().isoformat()
            })
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to avoid printing to stderr."""
        return

def start_webhook_server(port=8000):
    """Start a webhook server."""
    handler = WebhookHandler
    httpd = socketserver.TCPServer(("", port), handler)
    
    logger.info(f"Starting webhook server on port {port}")
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    return httpd

def test_webhook():
    """Test webhook functionality."""
    logger.info("=== Webhook Test ===")
    
    # Start webhook server
    port = 8000
    httpd = start_webhook_server(port)
    
    try:
        # Get webhook manager
        webhook_manager = get_webhook_manager()
        
        # Register a webhook
        webhook_id = webhook_manager.register_webhook(
            endpoint=f"http://localhost:{port}/webhook",
            events=["test_event"],
            headers={"X-Test-Header": "test-value"},
            secret="test-secret",
            description="Test webhook"
        )
        
        logger.info(f"Registered webhook: {webhook_id}")
        
        # Trigger the webhook
        test_data = {
            "message": "This is a test webhook",
            "timestamp": datetime.now().isoformat()
        }
        
        responses = webhook_manager.trigger_webhook(
            event="test_event",
            data=test_data,
            async_mode=False  # Use synchronous mode for testing
        )
        
        logger.info(f"Webhook responses: {json.dumps(responses, indent=2, default=str)}")
        
        # Wait a bit for the webhook to be processed
        import time
        time.sleep(1)
        
        # Check if webhook was received
        if received_webhooks:
            logger.info(f"Received {len(received_webhooks)} webhooks:")
            for i, webhook in enumerate(received_webhooks):
                logger.info(f"Webhook {i+1}:")
                logger.info(f"  Payload: {json.dumps(webhook['payload'], indent=2)}")
                logger.info(f"  Headers: {webhook['headers']}")
                
                # Verify signature if present
                if "X-Webhook-Signature" in webhook["headers"]:
                    signature = webhook["headers"]["X-Webhook-Signature"]
                    is_valid = webhook_manager.verify_signature(
                        payload=webhook["payload"],
                        signature=signature,
                        secret="test-secret"
                    )
                    logger.info(f"  Signature valid: {is_valid}")
        else:
            logger.warning("No webhooks received")
        
        # Clean up
        webhook_manager.delete_webhook(webhook_id)
        logger.info(f"Deleted webhook: {webhook_id}")
        
    finally:
        # Shutdown the server
        httpd.shutdown()
        logger.info("Webhook server stopped")
    
    logger.info("Webhook test completed")

if __name__ == "__main__":
    test_webhook()
