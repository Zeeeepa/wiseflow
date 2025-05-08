#!/usr/bin/env python3
"""
Dashboard entry point for Wiseflow.

This script initializes and runs the dashboard server.
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path to allow importing from core
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def main():
    """Run the dashboard server."""
    try:
        # Import the FastAPI app from main.py
        from dashboard.main import app
        import uvicorn
        
        # Get port and host from environment variables with fallbacks
        port = int(os.environ.get("DASHBOARD_PORT", 8080))
        host = os.environ.get("DASHBOARD_HOST", "0.0.0.0")
        
        # Check if port is available
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((host, port))
            s.close()
        except socket.error:
            # Port is not available, find an available port
            s.bind((host, 0))
            port = s.getsockname()[1]
            s.close()
            logger.info(f"Port {os.environ.get('DASHBOARD_PORT', 8080)} is not available, using port {port} instead")
        
        # Run the FastAPI app with uvicorn
        logger.info(f"Starting dashboard server on {host}:{port}")
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=os.environ.get("DASHBOARD_RELOAD", "false").lower() == "true"
        )
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure all required dependencies are installed.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting dashboard server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

