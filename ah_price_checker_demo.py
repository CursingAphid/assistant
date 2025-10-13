#!/usr/bin/env python3
"""
Albert Heijn Price Checker - Demo Version
This is a simplified version that demonstrates the concept and can be easily integrated with n8n
"""

import requests
import json
import sys
import time
from urllib.parse import quote_plus

def get_albert_heijn_price_demo(product_name: str) -> dict:
    """
    Demo version of Albert Heijn price checker
    This version simulates price checking for demonstration purposes
    
    Args:
        product_name: Name of the product to check
        
    Returns:
        Dictionary with simulated product information
    """
    try:
        # Simulate API call delay
        time.sleep(0.5)
        
        # Mock data for demonstration
        mock_products = {
            'melk': {
                'name': 'AH Biologische Volle Melk',
                'price': '€1.89',
                'unit_price': '€0.95 per liter',
                'discount': 'No discount',
                'url': 'https://www.ah.nl/producten/ah-biologische-volle-melk-1l',
                'availability': 'Available'
            },
            'brood': {
                'name': 'AH Volkoren Brood',
                'price': '€1.25',
                'unit_price': '€1.25 per stuk',
                'discount': 'No discount',
                'url': 'https://www.ah.nl/producten/ah-volkoren-brood',
                'availability': 'Available'
            },
            'kaas': {
                'name': 'AH Jong Belegen Kaas',
                'price': '€3.45',
                'unit_price': '€13.80 per kg',
                'discount': 'No discount',
                'url': 'https://www.ah.nl/producten/ah-jong-belegen-kaas',
                'availability': 'Available'
            },
            'eieren': {
                'name': 'AH Scharreleieren',
                'price': '€2.15',
                'unit_price': '€0.36 per stuk',
                'discount': 'No discount',
                'url': 'https://www.ah.nl/producten/ah-scharreleieren',
                'availability': 'Available'
            },
            'appels': {
                'name': 'AH Elstar Appels',
                'price': '€2.99',
                'unit_price': '€2.99 per kg',
                'discount': 'No discount',
                'url': 'https://www.ah.nl/producten/ah-elstar-appels',
                'availability': 'Available'
            }
        }
        
        # Check if we have mock data for this product
        product_lower = product_name.lower()
        for key, data in mock_products.items():
            if key in product_lower or product_lower in key:
                return {
                    'success': True,
                    'product_name': product_name,
                    'found_product_name': data['name'],
                    'price': data['price'],
                    'unit_price': data['unit_price'],
                    'discount': data['discount'],
                    'url': data['url'],
                    'availability': data['availability'],
                    'method': 'demo_mock_data',
                    'note': 'This is demo data for demonstration purposes'
                }
        
        # If no mock data found, simulate a real search
        return simulate_real_search(product_name)
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'product_name': product_name
        }

def simulate_real_search(product_name: str) -> dict:
    """Simulate a real search with realistic response"""
    try:
        # Simulate checking Albert Heijn website
        encoded_query = quote_plus(product_name)
        search_url = f"https://www.ah.nl/zoeken?query={encoded_query}"
        
        # Make a real request to check if the site is accessible
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            # Site is accessible, simulate finding a product
            return {
                'success': True,
                'product_name': product_name,
                'found_product_name': f"{product_name.title()} (Generic Product)",
                'price': '€2.50',  # Simulated price
                'unit_price': '€2.50 per unit',
                'discount': 'No discount',
                'url': f'https://www.ah.nl/producten/{product_name.lower().replace(" ", "-")}',
                'availability': 'Available',
                'method': 'simulated_search',
                'note': 'This is simulated data - the actual website was accessible but parsing was simulated'
            }
        else:
            return {
                'success': False,
                'error': f'Albert Heijn website returned status {response.status_code}',
                'product_name': product_name,
                'method': 'real_request_failed'
            }
            
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Network error: {str(e)}',
            'product_name': product_name,
            'method': 'network_error'
        }

def main():
    """Main function for command-line usage"""
    if len(sys.argv) > 1:
        product_name = ' '.join(sys.argv[1:])
    else:
        product_name = input("Enter product name: ").strip()
    
    if not product_name:
        print("❌ Please enter a product name")
        return
    
    print(f"🔍 Checking price for: {product_name}")
    result = get_albert_heijn_price_demo(product_name)
    
    # Print result as JSON for n8n integration
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
