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
    # Try different possible webhook paths
    webhook_urls = [
        "http://localhost:5678/webhook/python-trigger",
        "http://localhost:5678/webhook/TszaEKjuYUTrfDp3",
        "http://localhost:5678/webhook-test/python-trigger",
        "http://localhost:5678/webhook-test/TszaEKjuYUTrfDp3"
    ]
    
    # Data to send to the workflow
    data = {
        "message": "Hello from Python!",
        "timestamp": time.time(),
        "user": "python_script",
        "temperature": 25.5,
        "humidity": 60,
        "location": "San Francisco"
    }
    
    # Try each webhook URL until one works
    for webhook_url in webhook_urls:
        try:
            print(f"🚀 Trying webhook URL: {webhook_url}")
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
                return  # Success, exit the function
            else:
                print(f"❌ Error: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error for {webhook_url}")
        except requests.exceptions.Timeout:
            print(f"❌ Timeout for {webhook_url}")
        except Exception as e:
            print(f"❌ Unexpected error for {webhook_url}: {e}")
    
    print("\n🔍 None of the webhook URLs worked. Please check:")
    print("1. Is the workflow activated (toggle is green)?")
    print("2. What is the exact webhook URL shown in the n8n interface?")
    print("3. Try using the 'Test URL' button in n8n first")

if __name__ == "__main__":
    trigger_n8n_workflow()
