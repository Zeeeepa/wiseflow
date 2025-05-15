"""
Dashboard module for WiseFlow.

This module provides a web interface for monitoring and managing WiseFlow.
"""

import os
import sys
import logging
from flask import Flask

# Add components
from dashboard.components.resource_metrics import register_blueprint as register_resource_metrics

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask app."""
    app = Flask(__name__)
    
    # Register blueprints
    register_resource_metrics(app)
    
    # Add more blueprints here
    
    return app

def run_dashboard(host='0.0.0.0', port=5000, debug=False):
    """Run the dashboard server."""
    app = create_app()
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_dashboard(debug=True)
