#!/usr/bin/env python3
"""
Test script for the WiseFlow API server.

This script tests the basic functionality of the API server.
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_server():
    """Test the API server."""
    # Get API key from environment
    api_key = os.environ.get("WISEFLOW_API_KEY", "dev-api-key")
    
    # Get API host and port from environment
    api_host = os.environ.get("API_HOST", "0.0.0.0")
    api_port = int(os.environ.get("API_PORT", 8000))
    
    # Base URL
    base_url = f"http://{api_host}:{api_port}"
    
    # Test root endpoint
    try:
        response = requests.get(f"{base_url}/")
        print(f"Root endpoint: {response.status_code}")
        print(response.json())
    except Exception as e:
        print(f"Error testing root endpoint: {str(e)}")
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health endpoint: {response.status_code}")
        print(response.json())
    except Exception as e:
        print(f"Error testing health endpoint: {str(e)}")
    
    # Test process endpoint with API key
    try:
        headers = {"X-API-Key": api_key}
        data = {
            "content": "This is a test content.",
            "focus_point": "Extract key information",
            "explanation": "This is a test",
            "content_type": "text/plain",
            "use_multi_step_reasoning": False
        }
        response = requests.post(
            f"{base_url}/api/v1/process",
            headers=headers,
            json=data
        )
        print(f"Process endpoint: {response.status_code}")
        if response.status_code == 200:
            print("Process endpoint test successful")
        else:
            print(response.json())
    except Exception as e:
        print(f"Error testing process endpoint: {str(e)}")

if __name__ == "__main__":
    test_api_server()

