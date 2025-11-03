#!/usr/bin/env python3
"""
Aldi Comprehensive Scraper
Scrapes Aldi products from www.aldi.nl
"""

import aiohttp
import asyncio
import sqlite3
import re
import time
import logging
import json
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import aiosqlite

# Setup logging
import os
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'aldi_comprehensive_scraper.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AldiComprehensiveScraper:
    def __init__(self, db_path: str = None, max_concurrent: int = 20):
        """Initialize Aldi scraper"""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if db_path is None:
            self.db_path = os.path.join(base_dir, "grocery_database.db")
        else:
            self.db_path = db_path if os.path.isabs(db_path) else os.path.abspath(os.path.join(base_dir, db_path))
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Statistics
        self.stats = {
            'categories_found': 0,
            'categories_scraped': 0,
            'products_found': 0,
            'products_updated': 0,
            'products_new': 0,
            'products_unchanged': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    async def update_database_schema(self):
        """Update database schema to add supermarket column"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # Check if columns already exist
                cursor = await conn.execute("PRAGMA table_info(products)")
                columns = [row[1] for row in await cursor.fetchall()]
                
                # Add supermarket column if it doesn't exist
                if 'supermarket' not in columns:
                    await conn.execute('ALTER TABLE products ADD COLUMN supermarket TEXT NOT NULL DEFAULT "aldi"')
                    logger.info("Added supermarket column to products table")
                
                await conn.commit()
        except Exception as e:
            logger.error(f"Error updating database schema: {e}")
    
    def extract_price_numeric(self, price_str: str) -> float:
        """Extract numeric price from price string"""
        try:
            # Remove € symbol and extract number
            price_match = re.search(r'(\d+[,.]?\d*)', price_str)
            if price_match:
                return float(price_match.group(1).replace(',', '.'))
        except:
            pass
        return None
    
    async def get_all_categories(self, session: aiohttp.ClientSession) -> List[Dict[str, str]]:
        """Get all Aldi categories from the main products page"""
        url = "https://www.aldi.nl/producten.html"
        
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.error(f"Failed to get categories: HTTP {response.status}")
                    return []
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Try to extract JSON data from __NEXT_DATA__ script tag
                next_data_script = soup.find('script', id='__NEXT_DATA__')
                categories_from_json = []
                
                if next_data_script:
                    try:
                        import json
                        next_data = json.loads(next_data_script.string)
                        logger.info("Found __NEXT_DATA__ JSON - extracting categories from JSON")
                        
                        # Recursively search for category data in JSON
                        def find_categories_in_json(obj, path=""):
                            """Recursively search for category-like data in JSON"""
                            found = []
                            if isinstance(obj, dict):
                                # Look for keys that might contain category data
                                for key, value in obj.items():
                                    if 'category' in key.lower() or 'product' in key.lower() or 'link' in key.lower():
                                        if isinstance(value, list):
                                            for item in value:
                                                if isinstance(item, dict) and ('href' in item or 'url' in item or 'path' in item):
                                                    found.append(item)
                                        elif isinstance(value, dict):
                                            if 'href' in value or 'url' in value or 'path' in value:
                                                found.append(value)
                                    found.extend(find_categories_in_json(value, f"{path}.{key}"))
                            elif isinstance(obj, list):
                                for item in obj:
                                    found.extend(find_categories_in_json(item, path))
                            return found
                        
                        # Check for apiData which contains category children
                        if 'props' in next_data and 'pageProps' in next_data['props']:
                            page_props = next_data['props']['pageProps']
                            
                            # Look for apiData with PRODUCT_MGNL_CATEGORY_CHILDREN_GET
                            # apiData is stored as a JSON string, need to parse it
                            if 'apiData' in page_props:
                                try:
                                    api_data_str = page_props['apiData']
                                    if isinstance(api_data_str, str):
                                        api_data = json.loads(api_data_str)
                                    else:
                                        api_data = api_data_str
                                    
                                    for api_item in api_data:
                                        if isinstance(api_item, list) and len(api_item) >= 2:
                                            api_name = api_item[0]
                                            api_response = api_item[1]
                                            
                                            if api_name == 'PRODUCT_MGNL_CATEGORY_CHILDREN_GET':
                                                # This contains all the main category tiles!
                                                if 'res' in api_response:
                                                    categories_data = api_response['res']
                                                    logger.info(f"Found category data in apiData: {len(categories_data)} categories")
                                                    
                                                    # Extract categories from the response
                                                    for category in categories_data:
                                                        if isinstance(category, dict):
                                                            # Skip hidden categories
                                                            if category.get('hideInCategory', False):
                                                                continue
                                                            
                                                            # Extract category name - use navigationTitle or teaserTitle
                                                            name = category.get('navigationTitle') or category.get('teaserTitle') or category.get('title') or ''
                                                            
                                                            # Extract path - convert from /netherlands/producten/... to /producten/...
                                                            path = category.get('path') or ''
                                                            
                                                            if path and name:
                                                                # Convert path format from /netherlands/producten/... to /producten/...
                                                                if path.startswith('/netherlands/producten/'):
                                                                    path = path.replace('/netherlands/producten/', '/producten/')
                                                                elif path.startswith('/netherlands/'):
                                                                    path = path.replace('/netherlands/', '/')
                                                                
                                                                # Make URL absolute
                                                                if path.startswith('/'):
                                                                    full_url = f"https://www.aldi.nl{path}"
                                                                elif path.startswith('http'):
                                                                    full_url = path
                                                                else:
                                                                    full_url = f"https://www.aldi.nl/{path}"
                                                                
                                                                # Add .html if not present
                                                                if not full_url.endswith('.html') and not full_url.endswith('/'):
                                                                    full_url = f"{full_url}.html"
                                                                
                                                                categories_from_json.append({
                                                                    'name': name,
                                                                    'url': full_url
                                                                })
                                except (json.JSONDecodeError, KeyError) as e:
                                    logger.warning(f"Could not parse apiData: {e}")
                            
                            # Also check flyoutNavigation which contains the main category links
                            if 'page' in page_props and 'header' in page_props['page']:
                                header = page_props['page']['header']
                                if '0' in header and 'flyoutNavigation' in header['0']:
                                    flyout_nav = header['0']['flyoutNavigation']
                                    for nav_item in flyout_nav:
                                        if isinstance(nav_item, dict) and 'PRODUCTEN' in nav_item:
                                            producten_nav = nav_item['PRODUCTEN']
                                            
                                            # Collect all categories from both navigation columns
                                            # Main categories are in subNavCol2 with id starting with "parent-"
                                            for col_key in ['subNavCol1', 'subNavCol2']:
                                                if col_key in producten_nav:
                                                    for subnav in producten_nav[col_key]:
                                                        if isinstance(subnav, dict):
                                                            name = subnav.get('name', '')
                                                            path = subnav.get('path', '')
                                                            nav_id = subnav.get('id', '')
                                                            
                                                            # Get main categories (id starting with "parent-")
                                                            # Also include main category pages that match tile-grid pattern
                                                            if (path and name and 
                                                                nav_id.startswith('parent-') and 
                                                                '/producten/' in path and
                                                                path.endswith('.html') and
                                                                subnav.get('parent') != 'more'):
                                                                if path.startswith('/'):
                                                                    full_url = f"https://www.aldi.nl{path}"
                                                                else:
                                                                    full_url = f"https://www.aldi.nl/{path}"
                                                                
                                                                categories_from_json.append({
                                                                    'name': name,
                                                                    'url': full_url
                                                                })
                                            
                                            # Also check if there are categories in a different structure
                                            # Look for all direct links to main category pages
                                            # The tile-grid categories might be in a different API call or structure
                        
                        logger.info(f"Extracted {len(categories_from_json)} categories from JSON")
                        
                    except Exception as e:
                        logger.warning(f"Could not parse __NEXT_DATA__ JSON: {e}")
                        import traceback
                        logger.debug(traceback.format_exc())
                
                # If we found categories in JSON, use them
                if categories_from_json:
                    # Remove duplicates
                    unique_categories = []
                    seen_urls = set()
                    for cat in categories_from_json:
                        if cat['url'] not in seen_urls:
                            unique_categories.append(cat)
                            seen_urls.add(cat['url'])
                    
                    logger.info(f"Found {len(unique_categories)} unique categories from JSON")
                    self.stats['categories_found'] = len(unique_categories)
                    return unique_categories
                
                # Fallback: Try to parse HTML (in case HTML is actually rendered server-side)
                # Debug: Check if tile-grid exists
                tile_grid = soup.select_one('div.tile-grid')
                logger.info(f"Found tile-grid div: {tile_grid is not None}")
                
                # Find category links in the tile-grid div
                category_links = []
                
                # Try different selectors for category links
                selectors = [
                    'div.tile-grid a[href*="/producten/"]',  # Most specific - links in tile-grid
                    'a[href*="/producten/"][data-testid*="quick-link-item"]',  # By data-testid
                    'a.quick-links-section__item-image[href*="/producten/"]',  # By class
                    'a[href*="/producten/"]'  # Fallback - all product links
                ]
                
                for selector in selectors:
                    links = soup.select(selector)
                    logger.info(f"Selector '{selector}' found {len(links)} links")
                    if links:
                        category_links.extend(links)
                        logger.info(f"Found {len(links)} links with selector: {selector}")
                        break  # Use first selector that finds links
                
                # If no links found, try to find any links with producten
                if not category_links:
                    all_producten_links = soup.select('a[href*="/producten/"]')
                    logger.info(f"Found {len(all_producten_links)} total links with '/producten/' in href")
                    if all_producten_links:
                        # Show first few for debugging
                        for i, link in enumerate(all_producten_links[:5]):
                            logger.info(f"  Link {i+1}: href={link.get('href')}, text={link.get_text(strip=True)[:50]}")
                
                # Remove duplicates
                seen_hrefs = set()
                unique_links = []
                for link in category_links:
                    href = link.get('href', '')
                    if href and href not in seen_hrefs:
                        unique_links.append(link)
                        seen_hrefs.add(href)
                
                category_links = unique_links
                
                categories = []
                
                for link in category_links:
                    href = link.get('href', '')
                    
                    # Get category name from title attribute or span text
                    category_name = link.get('title', '').strip()
                    
                    # If no title, try to get from the span with class quick-links-section__item-image__title
                    if not category_name:
                        title_span = link.select_one('span.quick-links-section__item-image__title')
                        if title_span:
                            category_name = title_span.get_text(strip=True)
                    
                    # If still no name, try getting text from the link itself
                    if not category_name:
                        category_name = link.get_text(strip=True)
                    
                    # Filter out non-category links
                    if (href and category_name and 
                        len(category_name) > 2 and 
                        '/producten/' in href and
                        not href.endswith('/producten.html') and
                        not href.endswith('/producten/')):
                        
                        # Make URL absolute if relative
                        if href.startswith('/'):
                            full_url = f"https://www.aldi.nl{href}"
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = f"https://www.aldi.nl/{href}"
                        
                        categories.append({
                            'name': category_name,
                            'url': full_url
                        })
                
                # Remove duplicates by URL
                unique_categories = []
                seen_urls = set()
                for cat in categories:
                    if cat['url'] not in seen_urls:
                        unique_categories.append(cat)
                        seen_urls.add(cat['url'])
                
                logger.info(f"Found {len(unique_categories)} unique categories")
                self.stats['categories_found'] = len(unique_categories)
                return unique_categories
                
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            self.stats['errors'] += 1
            return []
    
    async def get_subcategories_for_category(self, session: aiohttp.ClientSession, category_url: str) -> List[Dict[str, str]]:
        """Get subcategories from a category page"""
        try:
            async with session.get(category_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.error(f"Failed to get subcategories from {category_url}: HTTP {response.status}")
                    return []
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Try to extract JSON data from __NEXT_DATA__ script tag
                next_data_script = soup.find('script', id='__NEXT_DATA__')
                subcategories = []
                
                if next_data_script:
                    try:
                        next_data = json.loads(next_data_script.string)
                        page_props = next_data['props']['pageProps']
                        
                        # Check for apiData which contains subcategory children
                        if 'apiData' in page_props:
                            api_data_str = page_props['apiData']
                            if isinstance(api_data_str, str):
                                api_data = json.loads(api_data_str)
                            else:
                                api_data = api_data_str
                            
                            for api_item in api_data:
                                if isinstance(api_item, list) and len(api_item) >= 2:
                                    api_name = api_item[0]
                                    api_response = api_item[1]
                                    
                                    if api_name == 'PRODUCT_MGNL_CATEGORY_CHILDREN_GET':
                                        # This contains the subcategory data
                                        if 'res' in api_response:
                                            subcategories_data = api_response['res']
                                            logger.info(f"Found {len(subcategories_data)} subcategories in {category_url}")
                                            
                                            # Extract subcategories from the response
                                            for subcategory in subcategories_data:
                                                if isinstance(subcategory, dict):
                                                    # Skip hidden subcategories
                                                    if subcategory.get('hideInCategory', False):
                                                        continue
                                                    
                                                    # Extract subcategory name
                                                    name = subcategory.get('navigationTitle') or subcategory.get('teaserTitle') or subcategory.get('title') or ''
                                                    
                                                    # Extract path
                                                    path = subcategory.get('path') or ''
                                                    
                                                    if path and name:
                                                        # Convert path format from /netherlands/producten/... to /producten/...
                                                        if path.startswith('/netherlands/producten/'):
                                                            path = path.replace('/netherlands/producten/', '/producten/')
                                                        elif path.startswith('/netherlands/'):
                                                            path = path.replace('/netherlands/', '/')
                                                        
                                                        # Make URL absolute
                                                        if path.startswith('/'):
                                                            full_url = f"https://www.aldi.nl{path}"
                                                        elif path.startswith('http'):
                                                            full_url = path
                                                        else:
                                                            full_url = f"https://www.aldi.nl/{path}"
                                                        
                                                        # Add .html if not present
                                                        if not full_url.endswith('.html') and not full_url.endswith('/'):
                                                            full_url = f"{full_url}.html"
                                                        
                                                        subcategories.append({
                                                            'name': name,
                                                            'url': full_url
                                                        })
                        else:
                            logger.warning(f"No apiData found in {category_url}")
                    
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Could not parse __NEXT_DATA__ JSON from {category_url}: {e}")
                
                # Fallback: Try to parse HTML for subcategories
                if not subcategories:
                    tile_grid = soup.select_one('div.tile-grid')
                    if tile_grid:
                        category_links = tile_grid.select('a[href*="/producten/"]')
                        for link in category_links:
                            href = link.get('href', '')
                            name = link.get('title', '').strip()
                            
                            if not name:
                                title_span = link.select_one('span.quick-links-section__item-image__title')
                                if title_span:
                                    name = title_span.get_text(strip=True)
                            
                            if href and name:
                                if href.startswith('/'):
                                    full_url = f"https://www.aldi.nl{href}"
                                else:
                                    full_url = href
                                
                                subcategories.append({
                                    'name': name,
                                    'url': full_url
                                })
                
                logger.info(f"Found {len(subcategories)} subcategories for {category_url}")
                return subcategories
                
        except Exception as e:
            logger.error(f"Error getting subcategories from {category_url}: {e}")
            self.stats['errors'] += 1
            return []

async def main():
    """Main function to scrape Aldi products"""
    scraper = AldiComprehensiveScraper()
    
    print("🚀 Aldi Comprehensive Scraper")
    print("="*60)
    print("This will scrape Aldi products")
    print("="*60)
    
    try:
        # Update database schema
        await scraper.update_database_schema()
        
        # Create aiohttp session
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,nl;q=0.8',
            'Accept-Encoding': 'gzip, deflate',  # Removed 'br' (Brotli) to avoid decoding issues
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(headers=headers, connector=connector, timeout=timeout) as session:
            # Test category extraction
            print("\n📂 Fetching all categories from Aldi...")
            categories = await scraper.get_all_categories(session)
            
            if categories:
                print(f"\n✅ Found {len(categories)} categories:")
                print("-" * 60)
                for i, cat in enumerate(categories[:10], 1):  # Show first 10
                    print(f"{i}. {cat['name']}")
                    print(f"   URL: {cat['url']}")
                if len(categories) > 10:
                    print(f"\n... and {len(categories) - 10} more categories")
                
                # Test subcategory extraction for first category
                if categories:
                    print(f"\n📂 Testing subcategory extraction for: {categories[0]['name']}")
                    print("-" * 60)
                    subcategories = await scraper.get_subcategories_for_category(session, categories[0]['url'])
                    if subcategories:
                        print(f"✅ Found {len(subcategories)} subcategories:")
                        for i, subcat in enumerate(subcategories, 1):
                            print(f"  {i}. {subcat['name']}")
                            print(f"     URL: {subcat['url']}")
                    else:
                        print("❌ No subcategories found")
            else:
                print("\n❌ No categories found")
        
        print("\n✅ Aldi scraper initialized")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")

if __name__ == "__main__":
    asyncio.run(main())
