#!/usr/bin/env python3
"""
Albert Heijn Price Checker
A Python project to fetch current product prices from Albert Heijn (Dutch supermarket)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import quote_plus
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Product:
    """Data class to represent a product"""
    name: str
    price: Optional[str]
    unit_price: Optional[str]
    unit_size: Optional[str]
    discount: Optional[str]
    url: Optional[str]
    image_url: Optional[str]
    availability: Optional[str]

class AlbertHeijnScraper:
    """Main class for scraping Albert Heijn product data"""
    
    def __init__(self):
        self.base_url = "https://www.ah.nl"
        self.search_url = "https://www.ah.nl/zoeken"
        self.session = requests.Session()
        
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def search_products(self, query: str, limit: int = 10) -> List[Product]:
        """
        Search for products on Albert Heijn website
        
        Args:
            query: Product name to search for
            limit: Maximum number of products to return
            
        Returns:
            List of Product objects
        """
        try:
            # Encode the search query
            encoded_query = quote_plus(query)
            search_url = f"{self.search_url}?query={encoded_query}"
            
            logger.info(f"Searching for: {query}")
            logger.info(f"URL: {search_url}")
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            products = self._parse_search_results(soup, limit)
            
            logger.info(f"Found {len(products)} products")
            return products
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching search results: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []
    
    def _parse_search_results(self, soup: BeautifulSoup, limit: int) -> List[Product]:
        """Parse the search results HTML"""
        products = []
        
        # Look for product cards in the search results
        product_cards = soup.find_all('div', class_=re.compile(r'product-card|product-tile'))
        
        for card in product_cards[:limit]:
            try:
                product = self._extract_product_info(card)
                if product:
                    products.append(product)
            except Exception as e:
                logger.warning(f"Error parsing product card: {e}")
                continue
        
        return products
    
    def _extract_product_info(self, card) -> Optional[Product]:
        """Extract product information from a product card"""
        try:
            # Extract product name
            name_element = card.find(['h3', 'h4', 'span'], class_=re.compile(r'title|name|product-name'))
            name = name_element.get_text(strip=True) if name_element else "Unknown Product"
            
            # Extract price
            price_element = card.find(['span', 'div'], class_=re.compile(r'price'))
            price = None
            if price_element:
                price_text = price_element.get_text(strip=True)
                # Extract price using regex
                price_match = re.search(r'€\s*(\d+[,.]?\d*)', price_text)
                if price_match:
                    price = f"€{price_match.group(1)}"
            
            # Extract unit price
            unit_price_element = card.find(['span', 'div'], class_=re.compile(r'unit-price|per-unit'))
            unit_price = unit_price_element.get_text(strip=True) if unit_price_element else None
            
            # Extract discount
            discount_element = card.find(['span', 'div'], class_=re.compile(r'discount|sale|offer'))
            discount = discount_element.get_text(strip=True) if discount_element else None
            
            # Extract product URL
            link_element = card.find('a', href=True)
            url = None
            if link_element:
                href = link_element['href']
                if href.startswith('/'):
                    url = f"{self.base_url}{href}"
                elif href.startswith('http'):
                    url = href
            
            # Extract image URL
            img_element = card.find('img', src=True)
            image_url = img_element['src'] if img_element else None
            
            # Extract availability
            availability_element = card.find(['span', 'div'], class_=re.compile(r'availability|stock'))
            availability = availability_element.get_text(strip=True) if availability_element else "Available"
            
            return Product(
                name=name,
                price=price,
                unit_price=unit_price,
                unit_size=None,  # Would need more specific parsing
                discount=discount,
                url=url,
                image_url=image_url,
                availability=availability
            )
            
        except Exception as e:
            logger.warning(f"Error extracting product info: {e}")
            return None
    
    def get_product_price(self, product_name: str) -> Optional[str]:
        """
        Get the current price of a specific product
        
        Args:
            product_name: Name of the product to search for
            
        Returns:
            Price string or None if not found
        """
        products = self.search_products(product_name, limit=1)
        if products and products[0].price:
            return products[0].price
        return None
    
    def get_product_details(self, product_name: str) -> Optional[Product]:
        """
        Get detailed information about a specific product
        
        Args:
            product_name: Name of the product to search for
            
        Returns:
            Product object or None if not found
        """
        products = self.search_products(product_name, limit=1)
        return products[0] if products else None

def main():
    """Main function for command-line usage"""
    scraper = AlbertHeijnScraper()
    
    print("🛒 Albert Heijn Price Checker")
    print("=" * 40)
    
    while True:
        try:
            product_name = input("\nEnter product name (or 'quit' to exit): ").strip()
            
            if product_name.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not product_name:
                print("❌ Please enter a product name")
                continue
            
            print(f"\n🔍 Searching for: {product_name}")
            print("⏳ Please wait...")
            
            # Get product details
            product = scraper.get_product_details(product_name)
            
            if product:
                print(f"\n✅ Found: {product.name}")
                print(f"💰 Price: {product.price or 'Not available'}")
                if product.unit_price:
                    print(f"📏 Unit Price: {product.unit_price}")
                if product.discount:
                    print(f"🏷️ Discount: {product.discount}")
                if product.url:
                    print(f"🔗 URL: {product.url}")
                print(f"📦 Availability: {product.availability}")
            else:
                print(f"❌ No products found for '{product_name}'")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
