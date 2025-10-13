#!/usr/bin/env python3
"""
Simple Albert Heijn Price Checker for n8n Integration
This script can be triggered by n8n workflows to get product prices
"""

import requests
from bs4 import BeautifulSoup
import json
import sys
import re
from urllib.parse import quote_plus

def get_albert_heijn_price(product_name: str) -> dict:
    """
    Get the current price of a product from Albert Heijn
    
    Args:
        product_name: Name of the product to search for
        
    Returns:
        Dictionary with product information
    """
    try:
        # Encode the search query
        encoded_query = quote_plus(product_name)
        search_url = f"https://www.ah.nl/zoeken?query={encoded_query}"
        
        # Set headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        # Make the request
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the first product card
        product_card = soup.find('div', class_=re.compile(r'product-card|product-tile'))
        
        if not product_card:
            return {
                'success': False,
                'error': 'No products found',
                'product_name': product_name
            }
        
        # Extract product information
        result = {
            'success': True,
            'product_name': product_name,
            'searched_at': None,
            'price': None,
            'unit_price': None,
            'discount': None,
            'url': None,
            'availability': 'Available'
        }
        
        # Extract product name
        name_element = product_card.find(['h3', 'h4', 'span'], class_=re.compile(r'title|name'))
        if name_element:
            result['found_product_name'] = name_element.get_text(strip=True)
        
        # Extract price
        price_element = product_card.find(['span', 'div'], class_=re.compile(r'price'))
        if price_element:
            price_text = price_element.get_text(strip=True)
            price_match = re.search(r'€\s*(\d+[,.]?\d*)', price_text)
            if price_match:
                result['price'] = f"€{price_match.group(1)}"
        
        # Extract unit price
        unit_price_element = product_card.find(['span', 'div'], class_=re.compile(r'unit-price|per-unit'))
        if unit_price_element:
            result['unit_price'] = unit_price_element.get_text(strip=True)
        
        # Extract discount
        discount_element = product_card.find(['span', 'div'], class_=re.compile(r'discount|sale|offer'))
        if discount_element:
            result['discount'] = discount_element.get_text(strip=True)
        
        # Extract product URL
        link_element = product_card.find('a', href=True)
        if link_element:
            href = link_element['href']
            if href.startswith('/'):
                result['url'] = f"https://www.ah.nl{href}"
            elif href.startswith('http'):
                result['url'] = href
        
        return result
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Network error: {str(e)}',
            'product_name': product_name
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'product_name': product_name
        }

def main():
    """Main function for command-line usage"""
    if len(sys.argv) > 1:
        # Get product name from command line argument
        product_name = ' '.join(sys.argv[1:])
    else:
        # Get product name from user input
        product_name = input("Enter product name: ").strip()
    
    if not product_name:
        print("❌ Please enter a product name")
        return
    
    print(f"🔍 Searching for: {product_name}")
    result = get_albert_heijn_price(product_name)
    
    # Print result as JSON for n8n integration
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
