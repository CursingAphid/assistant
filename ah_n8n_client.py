#!/usr/bin/env python3
"""
Albert Heijn Price Checker - n8n Integration
This script triggers the n8n workflow to get Albert Heijn product prices
"""

import requests
import json
import time
import sys

def trigger_ah_price_check(product_name: str, n8n_url: str = "http://localhost:5678") -> dict:
    """
    Trigger the Albert Heijn price check workflow in n8n
    
    Args:
        product_name: Name of the product to check
        n8n_url: Base URL of n8n instance
        
    Returns:
        Dictionary with the response from n8n
    """
    webhook_url = f"{n8n_url}/webhook/ah-price-check"
    
    data = {
        "product_name": product_name,
        "timestamp": time.time(),
        "requested_by": "python_script"
    }
    
    try:
        print(f"🔍 Checking price for: {product_name}")
        print(f"📡 Sending request to: {webhook_url}")
        
        response = requests.post(
            webhook_url,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Request successful!")
            return result
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "response": response.text
            }
            
    except requests.exceptions.ConnectionError:
        error_msg = "❌ Connection error: Make sure n8n is running and the workflow is activated"
        print(error_msg)
        return {
            "success": False,
            "error": "Connection error",
            "message": error_msg
        }
    except requests.exceptions.Timeout:
        error_msg = "❌ Timeout: The workflow took too long to respond"
        print(error_msg)
        return {
            "success": False,
            "error": "Timeout",
            "message": error_msg
        }
    except Exception as e:
        error_msg = f"❌ Unexpected error: {e}"
        print(error_msg)
        return {
            "success": False,
            "error": str(e),
            "message": error_msg
        }

def print_price_result(result: dict):
    """Print the price check result in a nice format"""
    print("\n" + "="*50)
    
    if result.get("status") == "success":
        print("🛒 ALBERT HEIJN PRICE CHECK RESULT")
        print("="*50)
        print(f"📦 Product: {result.get('found_product_name', 'Unknown')}")
        print(f"💰 Price: {result.get('price', 'Not available')}")
        
        if result.get('unit_price') and result.get('unit_price') != 'Not available':
            print(f"📏 Unit Price: {result.get('unit_price')}")
        
        if result.get('discount') and result.get('discount') != 'No discount':
            print(f"🏷️ Discount: {result.get('discount')}")
        
        if result.get('url') and result.get('url') != 'Not available':
            print(f"🔗 URL: {result.get('url')}")
        
        print(f"📦 Availability: {result.get('availability', 'Unknown')}")
        print(f"⏰ Checked at: {result.get('execution_time', 'Unknown')}")
        
    else:
        print("❌ PRICE CHECK FAILED")
        print("="*50)
        print(f"📦 Product: {result.get('product_name', 'Unknown')}")
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        print(f"⏰ Failed at: {result.get('execution_time', 'Unknown')}")
    
    print("="*50)

def main():
    """Main function for command-line usage"""
    print("🛒 Albert Heijn Price Checker (n8n Integration)")
    print("="*50)
    
    if len(sys.argv) > 1:
        # Get product name from command line argument
        product_name = ' '.join(sys.argv[1:])
    else:
        # Get product name from user input
        product_name = input("Enter product name: ").strip()
    
    if not product_name:
        print("❌ Please enter a product name")
        return
    
    # Trigger the n8n workflow
    result = trigger_ah_price_check(product_name)
    
    # Print the result
    print_price_result(result)
    
    # Also print raw JSON for debugging
    print("\n📋 Raw Response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
