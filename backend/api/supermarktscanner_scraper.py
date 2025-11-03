#!/usr/bin/env python3
"""
Supermarktscanner scraper module
Extracts product data from Supermarktscanner.nl
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from datetime import datetime

def extract_products_from_page(html_content: str) -> List[Dict[str, str]]:
    """Extract product information from Supermarktscanner HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    products = []
    seen_products = set()
    
    # Helper function to check if an element is in a promotional section
    def is_in_promotional_section(element):
        """Check if an element is within a promotional 'Beste aanbiedingen' section"""
        parent = element.parent if element else None
        depth = 0
        max_depth = 10  # Prevent infinite loops
        
        while parent and depth < max_depth:
            parent_class = ' '.join(parent.get('class', [])) if parent and parent.get('class') else ''
            parent_id = parent.get('id', '') if parent else ''
            
            # Check for specific promotional section containers (not just text)
            # Look for the actual promotional section container IDs/classes
            if ('carousel-uitgelicht' in parent_id.lower() or
                'uitgelicht-content' in parent_class.lower()):
                return True
            
            # Check if this is within a specific promotional row/container
            # The promotional section usually has a specific structure
            if parent_id and 'carousel' in parent_id.lower():
                # Check if it's the promotional carousel, not search results
                parent_text = parent.get_text() if parent else ''
                if 'beste aanbiedingen' in parent_text.lower()[:1000] and len(parent_text) > 500:
                    # This is likely the promotional section at the bottom
                    return True
            
            parent = parent.parent if parent else None
            depth += 1
        
        return False
    
    # Find product containers - look for elements with class "cbp-pgitem" or similar product containers
    product_containers = soup.find_all('div', class_=re.compile(r'cbp-pgitem|col-item', re.I))
    
    for container in product_containers:
        # Skip if in promotional section
        if is_in_promotional_section(container):
            continue
        
        # Find the main price - look for h3 with class "pgprice"
        price_h3 = container.find('h3', class_=re.compile(r'pgprice', re.I))
        if not price_h3:
            continue
        
        # Extract main price - it might have a discount span, so we need both prices
        # Format examples: "2.75 0.99" (discount + current price) or "2.69" (just price)
        price_text = price_h3.get_text(strip=True)
        
        original_price = None
        price = None
        on_discount = False
        
        # Check if there's a discount span (pgpricediscount) - if so, get both prices
        discount_span = price_h3.find('span', class_=re.compile(r'pgpricediscount', re.I))
        if discount_span:
            # Product is on discount
            on_discount = True
            # Get the original price from the discount span
            discount_text = discount_span.get_text(strip=True)
            original_price_match = re.search(r'(\d+[,.]?\d*)', discount_text)
            if original_price_match:
                original_price = original_price_match.group(1)
            
            # Get the discounted price (text after the discount span)
            # Remove discount text from price_text and get the remaining number
            price_text_after_discount = price_text.replace(discount_text, '').strip()
            # Extract the last number (current/discounted price)
            price_match = re.search(r'(\d+[,.]?\d*)\s*$', price_text_after_discount)
            if price_match:
                price = price_match.group(1)
            else:
                continue
        else:
            # No discount - just extract the price number
            price_match = re.search(r'(\d+[,.]?\d*)', price_text)
            if price_match:
                price = price_match.group(1)
            else:
                continue
        
        # Find product title - look for h3 that's not the price h3
        # First, get all h3 tags in the container
        all_h3s_in_container = container.find_all('h3')
        title_h3 = None
        
        # Find the h3 that's NOT the price h3
        for h3 in all_h3s_in_container:
            h3_class = h3.get('class', [])
            if h3_class:
                class_str = ' '.join(h3_class).lower()
                if 'pgprice' not in class_str:
                    title_h3 = h3
                    break
            else:
                # h3 with no class is likely the title
                title_h3 = h3
                break
        
        # If still not found, try to find title in cbp-pginfo section
        if not title_h3:
            info_div = container.find('div', class_=re.compile(r'cbp-pginfo', re.I))
            if info_div:
                title_h3 = info_div.find('h3')
        
        if not title_h3:
            continue
        
        title = title_h3.get_text(strip=True)
        # Clean up title - remove any leading numbers
        title = re.sub(r'^\d+[,.]?\d*\s*', '', title).strip()
        
        if len(title) < 3 or len(title) > 200:
            continue
        
        # Extract size - look in cbp-pgprice or cbp-pginfo
        size = None
        size_span = container.find('span', class_=re.compile(r'cbp-pgprice', re.I))
        if size_span:
            size_text = size_span.get_text(strip=True)
            size_match = re.search(r'(\d+\s*(?:gram|g|ml|l|kg|st|stuks))', size_text, re.I)
            if size_match:
                size = size_match.group(1)
        
        # If not found, look in parent text
        if not size:
            parent_text = container.get_text()
            size_match = re.search(r'(\d+\s*(?:gram|g|ml|l|kg|st|stuks))', parent_text, re.I)
            if size_match:
                size = size_match.group(1)
        
        # Extract product image
        # Images are typically in the parent container (col-item) or in cbp-pgitem-flip
        image_url = None
        
        # First, check if container has a parent (col-item) that might have the image
        parent_container = container.parent if container else None
        
        # Look for image in cbp-pgitem-flip div (inside container or parent)
        flip_div = container.find('div', class_=re.compile(r'cbp-pgitem-flip', re.I))
        if not flip_div and parent_container:
            flip_div = parent_container.find('div', class_=re.compile(r'cbp-pgitem-flip', re.I))
        
        if flip_div:
            product_link = flip_div.find('a', class_=re.compile(r'product-link', re.I))
            if product_link:
                img = product_link.find('img')
                if img:
                    # Check data-lazy first (lazy loading), then src, then other attributes
                    image_url = (img.get('data-lazy') or 
                                img.get('data-src') or 
                                img.get('data-lazy-src') or 
                                img.get('src') or 
                                '')
                    # If image_url is a placeholder or relative, skip it
                    if image_url and (image_url.startswith('/img/pixel') or 
                                     image_url.startswith('pixel') or
                                     'pixel' in image_url.lower()):
                        image_url = None
                    # Make sure it's a full URL
                    if image_url and not image_url.startswith('http'):
                        image_url = None
        
        # If still not found, search in parent container for any image
        if not image_url and parent_container:
            all_imgs = parent_container.find_all('img')
            for img in all_imgs:
                # Skip logo images
                src = img.get('src', '')
                if 'shops_logo' in src or 'logo' in src.lower():
                    continue
                
                # Check for product image
                image_url = (img.get('data-lazy') or 
                            img.get('data-src') or 
                            img.get('data-lazy-src') or 
                            img.get('src') or 
                            '')
                if image_url and (image_url.startswith('http') and 
                                 'pixel' not in image_url.lower() and
                                 'logo' not in image_url.lower()):
                    break
                else:
                    image_url = None
        
        # Extract discount action/promotion text (e.g., "2E GRATIS", "Aanbieding: ACTIE")
        discount_action = None
        
        # Look for discountTag span in container or parent
        discount_tag_span = container.find('span', class_=re.compile(r'discountTag', re.I))
        if not discount_tag_span and parent_container:
            discount_tag_span = parent_container.find('span', class_=re.compile(r'discountTag', re.I))
        
        if discount_tag_span:
            discount_action = discount_tag_span.get_text(strip=True)
            # Clean up common prefixes
            discount_action = re.sub(r'^Aanbieding:\s*', '', discount_action, flags=re.I)
            discount_action = discount_action.strip()
        
        # If not found, look for any span with promotion text
        if not discount_action:
            all_spans = container.find_all('span')
            if parent_container:
                all_spans.extend(parent_container.find_all('span'))
            
            for span in all_spans:
                span_text = span.get_text(strip=True)
                # Check for common promotion patterns
                if (re.search(r'\d+[eE]\s*GRATIS', span_text) or  # "2E GRATIS"
                    re.search(r'\d+\s*VOOR\s*\d+', span_text, re.I) or  # "2 VOOR 1"
                    re.search(r'BONUS', span_text, re.I) or
                    (len(span_text) > 5 and len(span_text) < 50 and 
                     ('aanbieding' in span_text.lower() or 'actie' in span_text.lower() or 'gratis' in span_text.lower()))):
                    discount_action = span_text.strip()
                    break
        
        # Extract discount expiration date (e.g., "t/m di 04-11-2025")
        discount_date = None
        discount_timestamp = None
        discount_date_h6 = container.find('h6', class_=re.compile(r'pgdiscountdate', re.I))
        if not discount_date_h6 and parent_container:
            discount_date_h6 = parent_container.find('h6', class_=re.compile(r'pgdiscountdate', re.I))
        
        if discount_date_h6:
            discount_date = discount_date_h6.get_text(strip=True)
            # Clean up parentheses and common prefixes
            discount_date = re.sub(r'^\(', '', discount_date)
            discount_date = re.sub(r'\)$', '', discount_date)
            discount_date = discount_date.strip()
            
            # Convert date to timestamp
            # Parse formats like "t/m di 04-11-2025" or "geldig t/m di 04-11-2025"
            # Extract date part (DD-MM-YYYY)
            date_match = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', discount_date)
            if date_match:
                try:
                    day = int(date_match.group(1))
                    month = int(date_match.group(2))
                    year = int(date_match.group(3))
                    
                    # Create datetime object (end of day for expiration date)
                    dt = datetime(year, month, day, 23, 59, 59)
                    discount_timestamp = int(dt.timestamp())
                except (ValueError, OverflowError):
                    # Invalid date, keep discount_date as string but no timestamp
                    pass
        
        # Extract supermarket from logo
        supermarket = None
        logo_img = container.find('img', src=re.compile(r'shops_logo', re.I))
        if logo_img:
            src = logo_img.get('src', '').lower()
            alt = logo_img.get('alt', '').lower()
            if 'dekamarkt' in src or 'dekamarkt' in alt:
                supermarket = 'Dekamarkt'
            elif 'ah' in src or 'ah' in alt or 'albert' in src or 'albert' in alt:
                supermarket = 'Albert Heijn'
            elif 'aldi' in src or 'aldi' in alt:
                supermarket = 'Aldi'
            elif 'dirk' in src or 'dirk' in alt:
                supermarket = 'Dirk'
            elif 'hoogvliet' in src or 'hoogvliet' in alt:
                supermarket = 'Hoogvliet'
            elif 'jumbo' in src or 'jumbo' in alt:
                supermarket = 'Jumbo'
            elif 'plus' in src or 'plus' in alt:
                supermarket = 'Plus'
            elif 'vomar' in src or 'vomar' in alt:
                supermarket = 'Vomar'
            elif 'coop' in src or 'coop' in alt:
                supermarket = 'Coop'
        
        # Create product entry
        product_key = f"{title}_{price}_{supermarket}"
        if product_key not in seen_products:
            product_data = {
                'title': title,
                'price': f"€{price}",
                'size': size or 'N/A',
                'image': image_url or 'N/A',
                'supermarket': supermarket or 'Unknown',
                'on_discount': on_discount
            }
            
            # Add original price if on discount
            if on_discount and original_price:
                product_data['original_price'] = f"€{original_price}"
            
            # Add discount action if available
            if discount_action:
                product_data['discount_action'] = discount_action
            
            # Add discount expiration date if available
            if discount_date:
                product_data['discount_date'] = discount_date
                # Add timestamp if we successfully parsed the date
                if discount_timestamp:
                    product_data['discount_timestamp'] = discount_timestamp
            
            products.append(product_data)
            seen_products.add(product_key)
    
    return products

def search_supermarktscanner(keyword: str) -> List[Dict[str, str]]:
    """Search Supermarktscanner for products"""
    url = f"https://www.supermarktscanner.nl/product.php?keyword={keyword}"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        products = extract_products_from_page(response.text)
        return products
    
    except Exception as e:
        raise Exception(f"Error fetching data: {e}")

