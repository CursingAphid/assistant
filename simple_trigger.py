#!/usr/bin/env python3
"""
Simple n8n Webhook Trigger
This is a minimal example of how to trigger an n8n workflow from Python.
"""

import requests
import json
import time

def trigger_n8n_workflow():
    """
    Trigger an n8n workflow via webhook.
    """
    # n8n webhook URL (adjust the path based on your workflow)
    webhook_url = "http://localhost:5678/webhook/python-trigger"
    
    # Data to send to the workflow
    data = {
        "message": "Hello from Python!",
        "timestamp": time.time(),
        "user": "python_script",
        "temperature": 25.5,
        "humidity": 60,
        "location": "San Francisco"
    }
    
    try:
        print("🚀 Triggering n8n workflow...")
        print(f"📤 Sending data: {json.dumps(data, indent=2)}")
        
        # Send POST request to n8n webhook
        response = requests.post(
            webhook_url,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        # Check if request was successful
        if response.status_code == 200:
            print("✅ Workflow triggered successfully!")
            print(f"📥 Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure n8n is running on http://localhost:5678")
    except requests.exceptions.Timeout:
        print("❌ Timeout: The workflow took too long to respond")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    trigger_n8n_workflow()
