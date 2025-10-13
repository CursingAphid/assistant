#!/usr/bin/env python3
"""
Improved Albert Heijn Price Checker
This version uses a more robust approach to handle Albert Heijn's website structure
"""

import requests
from bs4 import BeautifulSoup
import json
import sys
import re
from urllib.parse import quote_plus
import time

def get_albert_heijn_price(product_name: str) -> dict:
    """
    Get the current price of a product from Albert Heijn using multiple methods
    
    Args:
        product_name: Name of the product to search for
        
    Returns:
        Dictionary with product information
    """
    try:
        # Method 1: Try the search API endpoint
        result = try_search_api(product_name)
        if result.get('success'):
            return result
        
        # Method 2: Try direct search page scraping
        result = try_search_page_scraping(product_name)
        if result.get('success'):
            return result
        
        # Method 3: Try with different search terms
        result = try_alternative_search(product_name)
        if result.get('success'):
            return result
        
        return {
            'success': False,
            'error': 'No products found with any method',
            'product_name': product_name,
            'methods_tried': ['search_api', 'search_page', 'alternative_search']
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'product_name': product_name
        }

def try_search_api(product_name: str) -> dict:
    """Try using Albert Heijn's search API"""
    try:
        # Albert Heijn's search API endpoint
        api_url = "https://www.ah.nl/zoeken/api/search"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,nl;q=0.8',
            'Referer': 'https://www.ah.nl/zoeken',
        }
        
        params = {
            'query': product_name,
            'size': 1,
            'sort': 'relevance'
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('products') and len(data['products']) > 0:
                product = data['products'][0]
                return parse_api_product(product, product_name)
        
        return {'success': False, 'error': 'API returned no products'}
        
    except Exception as e:
        return {'success': False, 'error': f'API error: {str(e)}'}

def try_search_page_scraping(product_name: str) -> dict:
    """Try scraping the search results page"""
    try:
        encoded_query = quote_plus(product_name)
        search_url = f"https://www.ah.nl/zoeken?query={encoded_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,nl;q=0.8',
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for various product card patterns
        product_selectors = [
            '[data-testid*="product"]',
            '.product-card',
            '.product-tile',
            '.product-item',
            '[class*="product"]',
            '[data-testid*="tile"]'
        ]
        
        product_card = None
        for selector in product_selectors:
            product_card = soup.select_one(selector)
            if product_card:
                break
        
        if product_card:
            return parse_html_product(product_card, product_name)
        
        return {'success': False, 'error': 'No product cards found on page'}
        
    except Exception as e:
        return {'success': False, 'error': f'Scraping error: {str(e)}'}

def try_alternative_search(product_name: str) -> dict:
    """Try with alternative search terms"""
    try:
        # Try with common variations
        variations = [
            product_name.lower(),
            product_name.title(),
            product_name.upper(),
            product_name.replace(' ', '-'),
            product_name.replace(' ', '_')
        ]
        
        for variation in variations:
            if variation != product_name:
                result = try_search_page_scraping(variation)
                if result.get('success'):
                    result['original_search'] = product_name
                    result['found_with_variation'] = variation
                    return result
        
        return {'success': False, 'error': 'No products found with variations'}
        
    except Exception as e:
        return {'success': False, 'error': f'Variation search error: {str(e)}'}

def parse_api_product(product: dict, original_name: str) -> dict:
    """Parse product data from API response"""
    try:
        return {
            'success': True,
            'product_name': original_name,
            'found_product_name': product.get('title', original_name),
            'price': product.get('price', {}).get('now', 'Not available'),
            'unit_price': product.get('price', {}).get('unitSize', 'Not available'),
            'discount': product.get('discount', {}).get('label', 'No discount') if product.get('discount') else 'No discount',
            'url': f"https://www.ah.nl{product.get('link', '')}" if product.get('link') else None,
            'availability': 'Available' if product.get('availability', {}).get('isAvailable', True) else 'Out of stock',
            'method': 'api'
        }
    except Exception as e:
        return {'success': False, 'error': f'API parsing error: {str(e)}'}

def parse_html_product(card, original_name: str) -> dict:
    """Parse product data from HTML card"""
    try:
        result = {
            'success': True,
            'product_name': original_name,
            'method': 'html_scraping'
        }
        
        # Extract product name
        name_selectors = ['h3', 'h4', '[data-testid*="title"]', '[class*="title"]', '[class*="name"]']
        for selector in name_selectors:
            name_elem = card.select_one(selector)
            if name_elem:
                result['found_product_name'] = name_elem.get_text(strip=True)
                break
        
        if 'found_product_name' not in result:
            result['found_product_name'] = original_name
        
        # Extract price
        price_selectors = [
            '[data-testid*="price"]',
            '[class*="price"]',
            '[class*="amount"]',
            'span:contains("€")',
            'div:contains("€")'
        ]
        
        for selector in price_selectors:
            price_elem = card.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'€\s*(\d+[,.]?\d*)', price_text)
                if price_match:
                    result['price'] = f"€{price_match.group(1)}"
                    break
        
        if 'price' not in result:
            result['price'] = 'Not available'
        
        # Extract URL
        link_elem = card.select_one('a[href]')
        if link_elem:
            href = link_elem['href']
            if href.startswith('/'):
                result['url'] = f"https://www.ah.nl{href}"
            elif href.startswith('http'):
                result['url'] = href
        
        # Default values
        result.setdefault('unit_price', 'Not available')
        result.setdefault('discount', 'No discount')
        result.setdefault('availability', 'Available')
        
        return result
        
    except Exception as e:
        return {'success': False, 'error': f'HTML parsing error: {str(e)}'}

def main():
    """Main function for command-line usage"""
    if len(sys.argv) > 1:
        product_name = ' '.join(sys.argv[1:])
    else:
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
