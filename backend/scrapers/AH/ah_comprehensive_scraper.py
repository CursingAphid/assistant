#!/usr/bin/env python3
"""
Albert Heijn Comprehensive Scraper
Scrapes ALL brands (A-Z including AH) + ALL categories for complete coverage
"""

import aiohttp
import asyncio
import sqlite3
import re
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
import os
from bs4 import BeautifulSoup
import aiosqlite

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'comprehensive_scraper.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AlbertHeijnComprehensiveScraper:
    def __init__(self, db_path: Optional[str] = None, max_concurrent: int = 20):
        """Initialize comprehensive scraper with ALL brands + categories"""
        # Resolve DB to project root by default
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if db_path is None:
            self.db_path = os.path.join(base_dir, "grocery_database.db")
        else:
            self.db_path = db_path if os.path.isabs(db_path) else os.path.abspath(os.path.join(base_dir, db_path))
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Statistics
        self.stats = {
            'letters_processed': 0,
            'brands_found': 0,
            'brands_scraped': 0,
            'categories_found': 0,
            'categories_scraped': 0,
            'products_found': 0,
            'products_updated': 0,
            'products_new': 0,
            'products_unchanged': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    async def setup_database(self):
        """Setup SQLite database with enhanced tables for brands, categories, and products"""
        async with aiosqlite.connect(self.db_path) as conn:
            # Create brands table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS brands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    letter TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create categories table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create products table with source tracking
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand_id INTEGER,
                    category_id INTEGER,
                    name TEXT NOT NULL,
                    current_price REAL,
                    url TEXT UNIQUE,
                    source_type TEXT NOT NULL, -- 'brand' or 'category'
                    supermarket TEXT NOT NULL DEFAULT 'ah', -- 'ah' or 'aldi'
                    page_number INTEGER DEFAULT 8,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (brand_id) REFERENCES brands (id),
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )
            ''')
            
            # Create price history table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products (id)
                )
            ''')
            
            # Create indexes for faster lookups
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_brands_letter ON brands(letter)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_products_url ON products(url)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_products_source ON products(source_type)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_products_price ON products(current_price)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(product_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(changed_at)')
            
            await conn.commit()
        
        # Update schema to add sale columns if they don't exist
        await self.update_database_schema()
        
        logger.info(f"Comprehensive database setup complete: {self.db_path}")
    
    async def update_database_schema(self):
        """Update database schema to add sale tracking columns"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # Check if columns already exist
                cursor = await conn.execute("PRAGMA table_info(products)")
                columns = [row[1] for row in await cursor.fetchall()]
                
                # Add isSale column if it doesn't exist
                if 'isSale' not in columns:
                    await conn.execute('ALTER TABLE products ADD COLUMN isSale INTEGER DEFAULT 0')
                    logger.info("Added isSale column to products table")
                
                # Add salePrice column if it doesn't exist
                if 'salePrice' not in columns:
                    await conn.execute('ALTER TABLE products ADD COLUMN salePrice REAL')
                    logger.info("Added salePrice column to products table")
                
                # Add isFutureSale column if it doesn't exist
                if 'isFutureSale' not in columns:
                    await conn.execute('ALTER TABLE products ADD COLUMN isFutureSale INTEGER DEFAULT 0')
                    logger.info("Added isFutureSale column to products table")
                
                # Add saleStartsAt column if it doesn't exist
                if 'saleStartsAt' not in columns:
                    await conn.execute('ALTER TABLE products ADD COLUMN saleStartsAt TEXT')
                    logger.info("Added saleStartsAt column to products table")
                
                # Add saleType column if it doesn't exist
                if 'saleType' not in columns:
                    await conn.execute('ALTER TABLE products ADD COLUMN saleType TEXT')
                    logger.info("Added saleType column to products table")
                
                # Add supermarket column if it doesn't exist
                if 'supermarket' not in columns:
                    await conn.execute('ALTER TABLE products ADD COLUMN supermarket TEXT NOT NULL DEFAULT "ah"')
                    logger.info("Added supermarket column to products table")
                
                await conn.commit()
        except Exception as e:
            logger.error(f"Error updating database schema: {e}")
    
    async def get_all_categories(self, session: aiohttp.ClientSession) -> List[Dict[str, str]]:
        """Get all AH categories from the main products page"""
        url = "https://www.ah.nl/producten"
        
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.error(f"Failed to get categories: HTTP {response.status}")
                    return []
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find category links - try multiple selectors
                category_links = []
                
                # Try different selectors for category links
                selectors = [
                    'a[href*="/producten/"]',
                    'a[href*="/categorie/"]',
                    '.category-link',
                    '[data-testid*="category"]',
                    'a[href*="/producten/"][href*="categorie"]'
                ]
                
                for selector in selectors:
                    links = soup.select(selector)
                    if links:
                        category_links.extend(links)
                        logger.debug(f"Found {len(links)} links with selector: {selector}")
                
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
                exclude_terms = ['Eerder gekocht', 'Ontdek nieuwe producten', 'AH Voordeelshop', 'AH Premium', 'AH Basic']
                exclude_names = ['producten', 'merk', 'letter']
                
                for link in category_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Filter out non-category links
                    if (href and text and 
                        len(text) > 2 and 
                        '/producten/' in href and
                        not any(term in text for term in exclude_terms) and
                        not any(name in href for name in exclude_names) and
                        not href.endswith('/producten') and
                        not href.endswith('/producten/')):
                        
                        categories.append({
                            'name': text,
                            'url': href
                        })
                
                # Remove duplicates
                unique_categories = []
                seen_urls = set()
                for cat in categories:
                    if cat['url'] not in seen_urls:
                        unique_categories.append(cat)
                        seen_urls.add(cat['url'])
                
                logger.info(f"Found {len(unique_categories)} unique categories")
                return unique_categories
                
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            self.stats['errors'] += 1
            return []
    
    async def get_brands_for_letter(self, session: aiohttp.ClientSession, letter: str) -> List[Dict[str, str]]:
        """Get all brands for a specific letter"""
        url = f"https://www.ah.nl/producten?letter={letter}"
        
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.error(f"Failed to get brands for letter {letter}: HTTP {response.status}")
                    return []
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find brand links
                brand_links = soup.select('a[href*="/producten/merk/"]')
                
                brands = []
                for link in brand_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if href and text and len(text) > 1:
                        brands.append({
                            'name': text,
                            'url': href,
                            'letter': letter
                        })
                
                logger.info(f"Found {len(brands)} brands for letter {letter}")
                return brands
                
        except Exception as e:
            logger.error(f"Error getting brands for letter {letter}: {e}")
            self.stats['errors'] += 1
            return []
    
    async def save_or_update_brand(self, brand: Dict[str, str]) -> Optional[int]:
        """Save brand to database or update last_scraped timestamp"""
        async with aiosqlite.connect(self.db_path) as conn:
            try:
                # Try to insert new brand
                await conn.execute('''
                    INSERT OR IGNORE INTO brands (name, url, letter)
                    VALUES (?, ?, ?)
                ''', (brand['name'], brand['url'], brand['letter']))
                
                # Update last_scraped timestamp
                await conn.execute('''
                    UPDATE brands SET last_scraped = CURRENT_TIMESTAMP 
                    WHERE name = ?
                ''', (brand['name'],))
                
                # Get the brand_id
                cursor = await conn.execute('SELECT id FROM brands WHERE name = ?', (brand['name'],))
                result = await cursor.fetchone()
                brand_id = result[0] if result else None
                
                await conn.commit()
                return brand_id
                
            except Exception as e:
                logger.error(f"Error saving brand {brand['name']}: {e}")
                return None
    
    async def save_or_update_category(self, category: Dict[str, str]) -> Optional[int]:
        """Save category to database or update last_scraped timestamp"""
        async with aiosqlite.connect(self.db_path) as conn:
            try:
                # Try to insert new category
                await conn.execute('''
                    INSERT OR IGNORE INTO categories (name, url)
                    VALUES (?, ?)
                ''', (category['name'], category['url']))
                
                # Update last_scraped timestamp
                await conn.execute('''
                    UPDATE categories SET last_scraped = CURRENT_TIMESTAMP 
                    WHERE name = ?
                ''', (category['name'],))
                
                # Get the category_id
                cursor = await conn.execute('SELECT id FROM categories WHERE name = ?', (category['name'],))
                result = await cursor.fetchone()
                category_id = result[0] if result else None
                
                await conn.commit()
                return category_id
                
            except Exception as e:
                logger.error(f"Error saving category {category['name']}: {e}")
                return None
    
    async def get_products_from_url(self, session: aiohttp.ClientSession, url: str, page: int = 8) -> List[Dict[str, str]]:
        """Get products from any URL (brand or category)"""
        # Convert relative URL to absolute and add page parameter
        if url.startswith('/'):
            full_url = f"https://www.ah.nl{url}?page={page}"
        else:
            full_url = f"{url}?page={page}"
        
        try:
            async with session.get(full_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.debug(f"HTTP {response.status} for {full_url}")
                    return []
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find product articles
                product_articles = soup.select('article.product-card-portrait_root__ZiRpZ')
                
                products = []
                for article in product_articles:
                    try:
                        product = self.extract_product_info(article)
                        if product:
                            products.append(product)
                    except Exception as e:
                        logger.debug(f"Error extracting product: {e}")
                        continue
                
                return products
                
        except Exception as e:
            logger.error(f"Error scraping {full_url}: {e}")
            self.stats['errors'] += 1
            return []
    
    def extract_product_info(self, article) -> Dict[str, str]:
        """Extract product information from an article element"""
        try:
            # Extract BOTH the current price and the original price (if on sale)
            price = None
            original_price = None
            price_amounts = article.select('div[data-testhook="price-amount"]')
            
            # First pass: Find the OLD price (aria-label "Oude prijs")
            for pa in price_amounts:
                cls = pa.get('class') or []
                cls_str = ' '.join(cls).lower()
                if 'price-amount_was' in cls_str:
                    # This is the "was" price - extract it as original_price
                    sr = pa.select_one('.sr-only')
                    aria = sr.get('aria-label', '') if sr else ''
                    if aria and aria.lower().startswith('oude prijs:'):
                        m = re.search(r'€\s*(\d+[,.]\d{2})', aria)
                        if m:
                            original_price = f"€{m.group(1)}"
                            continue
                    
                    # Also try to extract from the div itself
                    integer_part = pa.select_one('.price-amount_integer__+e2XO')
                    fractional_part = pa.select_one('.price-amount_fractional__kjJ7u')
                    if integer_part and fractional_part:
                        integer_text = integer_part.get_text(strip=True)
                        fractional_text = fractional_part.get_text(strip=True)
                        if integer_text.isdigit() and fractional_text.isdigit():
                            price_text = f"{integer_text}.{fractional_text}"
                            try:
                                price_num = float(price_text)
                                if 0.01 <= price_num <= 1000.0:
                                    original_price = f"€{price_text}"
                            except ValueError:
                                pass
            
            # Second pass: Find the CURRENT price (highlighted/bonus or regular)
            # Preference 1: aria-label that starts with "Prijs:" (current price), skip "Oude prijs"
            for pa in price_amounts:
                cls = pa.get('class') or []
                cls_str = ' '.join(cls).lower()
                if 'price-amount_was' in cls_str:
                    continue  # Skip the old price
                    
                sr = pa.select_one('.sr-only')
                aria = sr.get('aria-label', '') if sr else ''
                if aria and aria.lower().startswith('prijs:') and not aria.lower().startswith('oude prijs'):
                    m = re.search(r'€\s*(\d+[,.]\d{2})', aria)
                    if m:
                        price = f"€{m.group(1)}"
                        break
            
            # Preference 2: highlighted/bonus price-amount block (current sale price)
            if not price and price_amounts:
                highlighted = None
                for pa in price_amounts:
                    cls = pa.get('class') or []
                    cls_str = ' '.join(cls).lower()
                    if 'price-amount_was' in cls_str:
                        continue
                    if 'price-amount_highlight' in cls_str or 'price-amount_bonus' in cls_str:
                        highlighted = pa
                        break
                if highlighted:
                    integer_part = highlighted.select_one('.price-amount_integer__+e2XO')
                    fractional_part = highlighted.select_one('.price-amount_fractional__kjJ7u')
                    if integer_part and fractional_part:
                        integer_text = integer_part.get_text(strip=True)
                        fractional_text = fractional_part.get_text(strip=True)
                        if integer_text.isdigit() and fractional_text.isdigit() and len(integer_text) <= 3 and len(fractional_text) == 2:
                            price_text = f"{integer_text}.{fractional_text}"
                            try:
                                price_num = float(price_text)
                                if 0.01 <= price_num <= 1000.0:
                                    price = f"€{price_text}"
                            except ValueError:
                                pass
            
            # Fallback to last price-amount if no highlighted one
            if not price and price_amounts:
                # Get the last non-was price
                valid_prices = [pa for pa in price_amounts if 'price-amount_was' not in ' '.join(pa.get('class') or []).lower()]
                if valid_prices:
                    target = valid_prices[-1]
                    integer_part = target.select_one('.price-amount_integer__+e2XO')
                    fractional_part = target.select_one('.price-amount_fractional__kjJ7u')
                    if integer_part and fractional_part:
                        integer_text = integer_part.get_text(strip=True)
                        fractional_text = fractional_part.get_text(strip=True)
                        if integer_text.isdigit() and fractional_text.isdigit() and len(integer_text) <= 3 and len(fractional_text) == 2:
                            price_text = f"{integer_text}.{fractional_text}"
                            try:
                                price_num = float(price_text)
                                if 0.01 <= price_num <= 1000.0:
                                    price = f"€{price_text}"
                            except ValueError:
                                pass
            
            # Fallback to text extraction
            if not price:
                full_text = article.get_text(strip=True)
                price = self.extract_price(full_text)
            
            # Extract product name from the specific title element
            product_name = None
            title_elem = article.select_one('[data-testhook="product-title-line-clamp"]')
            if title_elem:
                product_name = title_elem.get_text(strip=True)
            
            # Fallback to old extraction method
            if not product_name or product_name == "Product not identified":
                full_text = article.get_text(strip=True)
                product_name = self.extract_product_name(full_text)
                if not product_name or product_name == "Product not identified":
                    return None
            
            # Extract URL
            url = None
            link_elem = article.select_one('a[href]')
            if link_elem:
                href = link_elem['href']
                if href.startswith('/'):
                    url = f"https://www.ah.nl{href}"
                elif href.startswith('http'):
                    url = href
            
            # Skip products in bonus groups as they appear as separate products anyway
            if url and '/bonus/groep/' in url:
                logger.debug(f"Skipping bonus group product: {product_name}")
                return None
            
            # Detect sale status and calculate sale price
            # The current price is what we display, and if there's an original price, we use it as context
            # But for sale_price, we want the current discounted price
            is_active_sale, is_future_sale, sale_price, sale_starts_at, sale_type = self.detect_sale_and_calculate_price(article, price)
            
            product = {
                'name': product_name,
                'price': price,  # Current/display price (the sale price if on sale)
                'url': url,
                'isSale': is_active_sale,
                'isFutureSale': is_future_sale,
                'salePrice': sale_price,
                'saleStartsAt': sale_starts_at,
                'saleType': sale_type
            }
            
            return product
            
        except Exception as e:
            logger.debug(f"Error extracting product info: {e}")
            return None
    
    def extract_product_name(self, text: str) -> str:
        """Extract product name from text"""
        # Remove common prefixes and suffixes
        text = re.sub(r'^(ml|g|l|stuks|kg|cl|per stuk|per pakket|online|pakket|korting|voordeel|nieuw|vegan|biologisch|halal|kosher)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(€\d+[,.]?\d*|€\d+[,.]?\d*€)', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split by common separators and take meaningful parts
        parts = text.split()
        meaningful_parts = []
        
        for part in parts:
            if len(part) > 2 and not re.match(r'^[0-9,.]*$', part):
                meaningful_parts.append(part)
                if len(meaningful_parts) >= 4:  # Limit to 4 meaningful words
                    break
        
        if meaningful_parts:
            return ' '.join(meaningful_parts)
        
        return "Product not identified"
    
    def extract_price(self, text: str) -> str:
        """Extract price from text"""
        # Skip unit size matches (e.g., "0,75 l" or "1,98 l")
        text_without_units = re.sub(r'\d+[,.]\d+\s*(l|ml|g|kg|cl|m)\b', '', text, flags=re.IGNORECASE)
        
        price_patterns = [
            r'€\s*(\d+[,.]?\d*)',
            r'(\d+[,.]?\d*)\s*€',
            r'(\d{1,3},\d{2})',  # Match prices like 9,99 or 99,99
            r'(\d{1,3}\.\d{2})',  # Match prices like 9.99 or 99.99
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text_without_units)
            if match:
                price_value = match.group(1)
                try:
                    # Validate price range
                    price_num = float(price_value.replace(',', '.'))
                    if 0.01 <= price_num <= 1000.0:  # Extended range including cents
                        return f"€{price_value}"
                except ValueError:
                    continue
        
        return "Not available"
    
    def detect_sale_and_calculate_price(self, article, current_price: str) -> tuple[bool, bool, float, str, str]:
        """
        Detect if product is on sale and calculate sale price
        Returns: (is_active_sale: bool, is_future_sale: bool, sale_price: float or None, sale_starts_at: str or None, sale_type: str or None)
        """
        is_active_sale = False
        is_future_sale = False
        sale_price = None
        sale_starts_at = None
        sale_type = None
        
        try:
            # Look for sale badges in multiple locations with priority:
            # 1. Smart-label paragraphs FIRST (for "vanaf maandag", "vandaag", etc.)
            # 2. Shield badges (for "2e Halve Prijs", "gratis", etc.)
            # 3. Fallback to legacy class names
            
            sale_elements = []
            
            # Method 1: Find smart-label paragraphs FIRST (date indicators)
            smart_labels = article.select('p[data-testhook="product-smart-label"]')
            for label in smart_labels:
                sale_elements.extend(label.select('span'))
                if label.get_text(strip=True):
                    sale_elements.append(label)
            
            # Method 2: Find shield badges (sale type badges)
            shield_divs = article.select('div[data-testhook="product-shield"]')
            for shield_div in shield_divs:
                sale_elements.extend(shield_div.select('span'))
                if shield_div.get_text(strip=True):
                    sale_elements.append(shield_div)
            
            # DO NOT use Method 3 (legacy class names) as it's too broad and matches non-sale elements
            # Only use validated sale badges from Method 1 (smart-labels) and Method 2 (product-shield)
            
            sale_spans = sale_elements
            
            # Collect all sale text from all spans to check for dates and sale keywords
            all_sale_texts = [span.get_text(strip=True).lower() for span in sale_spans]
            combined_sale_text = ' '.join(all_sale_texts)
            
            # Extract ONLY date text from smart-labels for saleStartsAt
            date_text = None
            if smart_labels:
                date_text = ' '.join([label.get_text(strip=True) for label in smart_labels]).strip()
            
            # Check if we have a date indicator anywhere in the sale badges
            has_vandaag = 'vandaag' in combined_sale_text
            has_future_date = any(day in combined_sale_text for day in ['maandag', 'morgen', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag', 'zondag'])
            has_sale_keywords = any(keyword in combined_sale_text for keyword in ['halve prijs', 'gratis', 'korting', 'voor', '%'])
            
            # If we have sale badges, determine if this is an active or future sale
            if sale_spans and has_sale_keywords:
                # Determine the sale type first
                sale_type = combined_sale_text.strip() if combined_sale_text else None
                
                # Special handling for cases that need calculation (like "2e HALVE PRIJS")
                needs_calculation = any(phrase in combined_sale_text for phrase in ['halve prijs', 'gratis', 'voor'])
                
                if needs_calculation:
                    # Get the full article context to calculate sale price
                    article_text = article.get_text(' ', strip=True)
                    sale_price = self.calculate_sale_price(article_text, current_price)
                    logger.debug(f"Calculated sale price for '{sale_type}': {sale_price}")
                else:
                    # Use the current price as the sale price
                    sale_price = self.extract_price_numeric(current_price)
                
                # Determine sale status based on date indicators
                if has_vandaag:
                    is_active_sale = True
                    logger.debug(f"Active sale detected (vandaag): {sale_type} - Price: {current_price}")
                elif has_future_date:
                    is_future_sale = True
                    sale_starts_at = date_text if date_text else combined_sale_text.strip()
                    logger.debug(f"Future sale detected: {sale_type} - Starts: {sale_starts_at}, Future sale price: {current_price}")
                elif has_sale_keywords:
                    # Sale badge present but no specific date - treat as active
                    is_active_sale = True
                    logger.debug(f"Active sale detected (badge, no date): {sale_type} - Price: {current_price}")
        
        except Exception as e:
            logger.debug(f"Error detecting sale: {e}")
        
        # Note: We don't mark products as on sale based on unit-based pricing alone
        # Unit pricing is informational, not a sale indicator
        # Only mark as sale if there's an actual sale label ("vandaag", etc.)
        
        return is_active_sale, is_future_sale, sale_price, sale_starts_at, sale_type
    
    def calculate_sale_price(self, text: str, regular_price: str) -> float:
        """
        Calculate sale price from different sale formats:
        - "2 voor 0.99" → 0.99 / 2 = 0.495
        - "1 EURO KORTING" → regular_price - 1.0
        - "30% Korting" or "40% KORTING" → regular_price * 0.7 or 0.6
        - "VOOR 1.89" → 1.89
        - "1 + 1 GRATIS" or "2 + 1 GRATIS" → buy X, get Y free
        - "2E GRATIS" or "3E GRATIS" → second/third free
        - "100 GRAM voor 1.69" → unit-based pricing
        """
        try:
            text_lower = text.lower()
            
            # Remove commas and clean up text
            text_clean = re.sub(r'[^\d\s.%-]', ' ', text_lower)
            
            # Format 1: "X voor Y.YY" (e.g., "2 voor 0.99")
            voor_match = re.search(r'(\d+)\s+voor\s+(\d+[,.]?\d*)', text_lower)
            if voor_match:
                quantity = int(voor_match.group(1))
                total_price = float(voor_match.group(2).replace(',', '.'))
                sale_price = total_price / quantity
                logger.debug(f"Found 'X voor Y' format: {quantity} voor {total_price} = {sale_price}")
                return sale_price
            
            # Format 2: "VOOR X.XX" (e.g., "VOOR 1.89")
            direct_price_match = re.search(r'voor\s+(\d+[,.]?\d*)', text_lower)
            if direct_price_match:
                sale_price = float(direct_price_match.group(1).replace(',', '.'))
                logger.debug(f"Found 'VOOR X.XX' format: {sale_price}")
                return sale_price
            
            # Format 3: "X EURO KORTING" or "X EUR KORTING" (e.g., "1 EURO KORTING")
            euro_korting_match = re.search(r'(\d+)\s+euro\s+korting', text_lower)
            if euro_korting_match:
                discount = float(euro_korting_match.group(1))
                # Extract regular price
                regular_price_num = self.extract_price_numeric(regular_price)
                if regular_price_num:
                    sale_price = regular_price_num - discount
                    logger.debug(f"Found 'X EURO KORTING' format: {discount} off {regular_price_num} = {sale_price}")
                    return max(0, sale_price)  # Ensure non-negative
            
            # Format 4: "X% Korting" or "X % KORTING" (e.g., "30% Korting")
            percentage_match = re.search(r'(\d+)\s*%\s+korting', text_lower)
            if percentage_match:
                discount_percent = float(percentage_match.group(1))
                regular_price_num = self.extract_price_numeric(regular_price)
                if regular_price_num:
                    sale_price = regular_price_num * (1 - discount_percent / 100)
                    logger.debug(f"Found 'X% Korting' format: {discount_percent}% off {regular_price_num} = {sale_price}")
                    return max(0, sale_price)
            
            # Format 5a: "2E HALVE PRIJS" (every 2nd item half price)
            halve_prijs_match = re.search(r'(\d+)(e|de)\s+halve\s+prijs', text_lower)
            if halve_prijs_match:
                every_number = int(halve_prijs_match.group(1))
                # "2e halve prijs" means every 2nd item is half price
                # If you buy 2 items: 1 full price + 1 half price = 1.5x the price for 2 items
                regular_price_num = self.extract_price_numeric(regular_price)
                if regular_price_num:
                    # Average price per item = (1 full + 0.5 full) / 2 = 0.75 × regular_price
                    sale_price = regular_price_num * 0.75
                    logger.debug(f"Found '{every_number}e halve prijs' format: {sale_price}")
                    return sale_price
            
            # Format 5b: "HALVE PRIJS" or "50% OFF" (all items half price)
            if 'halve' in text_lower and 'prijs' in text_lower and 'halve prijs' in text_lower:
                # Check if it's NOT "2e halve prijs" (we already handled that above)
                if not re.search(r'\d+e\s+halve\s+prijs', text_lower):
                    regular_price_num = self.extract_price_numeric(regular_price)
                    if regular_price_num:
                        sale_price = regular_price_num / 2
                        logger.debug(f"Found 'HALVE PRIJS' format: {sale_price}")
                        return sale_price
            
            # Format 6: "1 + 1 GRATIS" or "2 + 1 GRATIS" or "1+1 gratis"
            gratis_match = re.search(r'(\d+)\s*\+\s*(\d+)\s+(gratis|free)', text_lower)
            if gratis_match:
                buy = int(gratis_match.group(1))
                free = int(gratis_match.group(2))
                regular_price_num = self.extract_price_numeric(regular_price)
                if regular_price_num:
                    # Price per unit = (buy * regular_price) / (buy + free)
                    sale_price = (buy * regular_price_num) / (buy + free)
                    logger.debug(f"Found 'X+Y gratis' format: {buy}+{free} gratis = {sale_price}")
                    return sale_price
            
            # Format 7: "2E GRATIS" or "3E GRATIS" (second/third free)
            egratis_match = re.search(r'(\d+)(e|de)\s+gratis', text_lower)
            if egratis_match:
                free_number = int(egratis_match.group(1))
                # e.g., "2e gratis" means every Xth item is free
                # "2e gratis" = buy 2, get 1 free = 2 items for price of 1
                # "3e gratis" = buy 3, get 1 free = 3 items for price of 2
                regular_price_num = self.extract_price_numeric(regular_price)
                if regular_price_num:
                    # For "2e gratis": get 2 items for price of 1 → per unit = price / 2
                    # For "3e gratis": get 3 items for price of 2 → per unit = (2 × price) / 3
                    items_you_pay_for = free_number - 1
                    items_you_get = free_number
                    sale_price = (items_you_pay_for * regular_price_num) / items_you_get
                    logger.debug(f"Found 'Xe gratis' format: {free_number}e gratis = {sale_price}")
                    return sale_price
            
            # Format 8: "100 GRAM voor 1.69" - unit-based pricing
            unit_match = re.search(r'(\d+)\s+(gram|g|ml|l|kg|cl)\s+voor\s+(\d+[,.]?\d*)', text_lower)
            if unit_match:
                unit_amount = float(unit_match.group(1))
                unit_type = unit_match.group(2)
                price = float(unit_match.group(3).replace(',', '.'))
                # Price per unit (e.g., per 100g)
                sale_price = price / unit_amount
                logger.debug(f"Found unit-based pricing: {unit_amount} {unit_type} voor {price} = {sale_price} per unit")
                return sale_price
        
        except Exception as e:
            logger.debug(f"Error calculating sale price: {e}")
        
        return None
    
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
    
    def calculate_unit_based_price(self, article, regular_price: str) -> float:
        """
        Calculate price based on promotional unit pricing (e.g., "€0.99 per 100g")
        Only treats this as a sale if there's an explicit promotional unit price message
        """
        try:
            # Get the full article text to look for promotional unit pricing
            full_text = article.get_text(strip=True).lower()
            
            # Look for explicit promotional unit pricing messages like:
            # "€0.99 per 100g", "per 100 gram €1.50", "0,99 cent per 100 gram", etc.
            
            # Pattern 1: "€X.XX per 100g" or "€X,XX per 100 gram"
            promo_unit_match = re.search(r'€\s*(\d+[,.]?\d*)\s+per\s+100\s*(g|gram|ml|kg|cl)', full_text)
            if promo_unit_match:
                unit_price = float(promo_unit_match.group(1).replace(',', '.'))
                logger.debug(f"Found promotional unit price: €{unit_price} per 100{promo_unit_match.group(2)}")
                return unit_price
            
            # Pattern 2: "per 100 gram €X.XX" (reversed order)
            promo_unit_match2 = re.search(r'per\s+100\s+(g|gram|ml)\s+€\s*(\d+[,.]?\d*)', full_text)
            if promo_unit_match2:
                unit_price = float(promo_unit_match2.group(2).replace(',', '.'))
                logger.debug(f"Found promotional unit price (reversed): €{unit_price} per 100{promo_unit_match2.group(1)}")
                return unit_price
            
            # Pattern 3: "100 gram voor €X.XX" (dutch format)
            promo_unit_match3 = re.search(r'100\s+(g|gram|ml|kg|cl)\s+voor\s+€\s*(\d+[,.]?\d*)', full_text)
            if promo_unit_match3:
                unit_price = float(promo_unit_match3.group(2).replace(',', '.'))
                logger.debug(f"Found promotional unit price (Dutch format): €{unit_price} per 100{promo_unit_match3.group(1)}")
                return unit_price
        
        except Exception as e:
            logger.debug(f"Error calculating unit-based price: {e}")
        
        return None
    
    async def smart_save_products(self, products: List[Dict[str, str]], brand_id: Optional[int] = None, category_id: Optional[int] = None, source_type: str = "brand") -> Dict[str, int]:
        """Smart save products - only update if price changed or new product"""
        if not products:
            return {'new': 0, 'updated': 0, 'unchanged': 0}
        
        async with aiosqlite.connect(self.db_path) as conn:
            stats = {'new': 0, 'updated': 0, 'unchanged': 0}
            
            try:
                for product in products:
                    if not product.get('url'):
                        continue
                    
                    # Check if product already exists
                    cursor = await conn.execute('''
                        SELECT id, current_price FROM products 
                        WHERE url = ?
                    ''', (product['url'],))
                    
                    existing = await cursor.fetchone()
                    
                    if existing:
                        product_id, old_price = existing
                        
                        # Convert price to float
                        price_float = self.extract_price_numeric(product['price'])
                        
                        # Check if price changed
                        if old_price != price_float:
                            # Price changed - update product and add to history
                            await conn.execute('''
                                UPDATE products 
                                SET current_price = ?, last_updated = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', (price_float, product_id))
                            
                            # Add to price history
                            await conn.execute('''
                                INSERT INTO price_history (product_id, price)
                                VALUES (?, ?)
                            ''', (product_id, price_float))
                            
                            stats['updated'] += 1
                            logger.info(f"💰 Price changed: {product['name']} {old_price} → {price_float}")
                        else:
                            # Price unchanged
                            stats['unchanged'] += 1
                    else:
                        # New product
                        is_sale = product.get('isSale', False)
                        is_future_sale = product.get('isFutureSale', False)
                        sale_price = product.get('salePrice')
                        sale_starts_at = product.get('saleStartsAt')
                        sale_type = product.get('saleType')
                        
                        # Convert price to float
                        price_float = self.extract_price_numeric(product['price'])
                        
                        cursor = await conn.execute('''
                            INSERT INTO products (brand_id, category_id, name, current_price, url, source_type, page_number, isSale, isFutureSale, salePrice, saleStartsAt, saleType, supermarket)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (brand_id, category_id, product['name'], price_float, product['url'], source_type, 8, int(is_sale), int(is_future_sale), sale_price, sale_starts_at, sale_type, 'ah'))
                        
                        product_id = cursor.lastrowid
                        
                        # Add initial price to history
                        await conn.execute('''
                            INSERT INTO price_history (product_id, price)
                            VALUES (?, ?)
                        ''', (product_id, price_float))
                        
                        stats['new'] += 1
                        logger.info(f"🆕 New product: {product['name']} - {product['price']}")
                
                await conn.commit()
                return stats
                
            except Exception as e:
                logger.error(f"Error saving products: {e}")
                self.stats['errors'] += 1
                return stats
    
    async def scrape_brand(self, session: aiohttp.ClientSession, brand: Dict[str, str]) -> Dict[str, int]:
        """Scrape a single brand with smart resync"""
        async with self.semaphore:  # Limit concurrent requests
            try:
                logger.info(f"🔍 Smart scraping brand: {brand['name']}")
                
                # Save/update brand
                brand_id = await self.save_or_update_brand(brand)
                if not brand_id:
                    return {'products': 0, 'new': 0, 'updated': 0, 'unchanged': 0}
                
                # Get products from brand page 8
                products = await self.get_products_from_url(session, brand['url'], page=8)
                
                if products:
                    # Smart save products
                    stats = await self.smart_save_products(products, brand_id=brand_id, source_type="brand")
                    logger.info(f"📦 {brand['name']}: {len(products)} products ({stats['new']} new, {stats['updated']} updated, {stats['unchanged']} unchanged)")
                    return {'products': len(products), **stats}
                else:
                    logger.info(f"📦 No products found for {brand['name']}")
                    return {'products': 0, 'new': 0, 'updated': 0, 'unchanged': 0}
                
            except Exception as e:
                logger.error(f"Error scraping brand {brand['name']}: {e}")
                self.stats['errors'] += 1
                return {'products': 0, 'new': 0, 'updated': 0, 'unchanged': 0}
    
    async def scrape_category(self, session: aiohttp.ClientSession, category: Dict[str, str]) -> Dict[str, int]:
        """Scrape a single category with smart resync"""
        async with self.semaphore:  # Limit concurrent requests
            try:
                logger.info(f"🔍 Smart scraping category: {category['name']}")
                
                # Save/update category
                category_id = await self.save_or_update_category(category)
                if not category_id:
                    return {'products': 0, 'new': 0, 'updated': 0, 'unchanged': 0}
                
                # Get products from category page 8
                products = await self.get_products_from_url(session, category['url'], page=8)
                
                if products:
                    # Smart save products
                    stats = await self.smart_save_products(products, category_id=category_id, source_type="category")
                    logger.info(f"📦 {category['name']}: {len(products)} products ({stats['new']} new, {stats['updated']} updated, {stats['unchanged']} unchanged)")
                    return {'products': len(products), **stats}
                else:
                    logger.info(f"📦 No products found for {category['name']}")
                    return {'products': 0, 'new': 0, 'updated': 0, 'unchanged': 0}
                
            except Exception as e:
                logger.error(f"Error scraping category {category['name']}: {e}")
                self.stats['errors'] += 1
                return {'products': 0, 'new': 0, 'updated': 0, 'unchanged': 0}
    
    async def resync_letter(self, session: aiohttp.ClientSession, letter: str) -> Dict[str, int]:
        """Resync all brands for a specific letter"""
        logger.info(f"🔄 Smart resyncing letter: {letter.upper()}")
        
        # Get all brands for this letter
        brands = await self.get_brands_for_letter(session, letter)
        self.stats['brands_found'] += len(brands)
        
        if not brands:
            logger.warning(f"No brands found for letter {letter}")
            return {'brands': 0, 'products': 0, 'new': 0, 'updated': 0, 'unchanged': 0}
        
        # Filter out specific AH brands that need Selenium (they will be handled by Selenium scraper)
        selenium_ah_brands = ['AH', 'AH Biologisch', 'AH Terra']
        non_selenium_brands = [brand for brand in brands if brand['name'] not in selenium_ah_brands]
        logger.info(f"📊 Non-Selenium brands for {letter}: {len(non_selenium_brands)}")
        
        if not non_selenium_brands:
            return {'brands': 0, 'products': 0, 'new': 0, 'updated': 0, 'unchanged': 0}
        
        # Process brands concurrently
        tasks = [self.scrape_brand(session, brand) for brand in non_selenium_brands]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count results
        brands_scraped = len(non_selenium_brands)
        products_found = sum(result.get('products', 0) if isinstance(result, dict) else 0 for result in results)
        products_new = sum(result.get('new', 0) if isinstance(result, dict) else 0 for result in results)
        products_updated = sum(result.get('updated', 0) if isinstance(result, dict) else 0 for result in results)
        products_unchanged = sum(result.get('unchanged', 0) if isinstance(result, dict) else 0 for result in results)
        
        self.stats['brands_scraped'] += brands_scraped
        self.stats['products_found'] += products_found
        self.stats['products_new'] += products_new
        self.stats['products_updated'] += products_updated
        self.stats['products_unchanged'] += products_unchanged
        
        logger.info(f"✅ Letter {letter.upper()} resync complete: {brands_scraped} brands, {products_found} products ({products_new} new, {products_updated} updated, {products_unchanged} unchanged)")
        return {'brands': brands_scraped, 'products': products_found, 'new': products_new, 'updated': products_updated, 'unchanged': products_unchanged}
    
    async def resync_categories(self, session: aiohttp.ClientSession) -> Dict[str, int]:
        """Resync all AH categories"""
        logger.info(f"🔄 Smart resyncing AH categories")
        
        # Get all categories
        categories = await self.get_all_categories(session)
        self.stats['categories_found'] = len(categories)
        
        if not categories:
            logger.warning("No categories found")
            return {'categories': 0, 'products': 0, 'new': 0, 'updated': 0, 'unchanged': 0}
        
        logger.info(f"📊 Categories found: {len(categories)}")
        
        # Process categories concurrently
        tasks = [self.scrape_category(session, category) for category in categories]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count results
        categories_scraped = len(categories)
        products_found = sum(result.get('products', 0) if isinstance(result, dict) else 0 for result in results)
        products_new = sum(result.get('new', 0) if isinstance(result, dict) else 0 for result in results)
        products_updated = sum(result.get('updated', 0) if isinstance(result, dict) else 0 for result in results)
        products_unchanged = sum(result.get('unchanged', 0) if isinstance(result, dict) else 0 for result in results)
        
        self.stats['categories_scraped'] += categories_scraped
        self.stats['products_found'] += products_found
        self.stats['products_new'] += products_new
        self.stats['products_updated'] += products_updated
        self.stats['products_unchanged'] += products_unchanged
        
        logger.info(f"✅ Categories resync complete: {categories_scraped} categories, {products_found} products ({products_new} new, {products_updated} updated, {products_unchanged} unchanged)")
        return {'categories': categories_scraped, 'products': products_found, 'new': products_new, 'updated': products_updated, 'unchanged': products_unchanged}
    
    async def get_database_stats(self) -> Dict[str, int]:
        """Get comprehensive statistics from database"""
        async with aiosqlite.connect(self.db_path) as conn:
            # Count brands
            cursor = await conn.execute('SELECT COUNT(*) FROM brands')
            brand_count = (await cursor.fetchone())[0]
            
            # Count categories
            cursor = await conn.execute('SELECT COUNT(*) FROM categories')
            category_count = (await cursor.fetchone())[0]
            
            # Count products
            cursor = await conn.execute('SELECT COUNT(*) FROM products')
            product_count = (await cursor.fetchone())[0]
            
            # Count products by source
            cursor = await conn.execute('SELECT source_type, COUNT(*) FROM products GROUP BY source_type')
            products_by_source = dict(await cursor.fetchall())
            
            # Count price changes
            cursor = await conn.execute('SELECT COUNT(*) FROM price_history')
            price_changes = (await cursor.fetchone())[0]
            
            # Count brands by letter
            cursor = await conn.execute('SELECT letter, COUNT(*) FROM brands GROUP BY letter ORDER BY letter')
            brands_by_letter = dict(await cursor.fetchall())
            
            # Recent price changes (last 24 hours)
            cursor = await conn.execute('''
                SELECT COUNT(*) FROM price_history 
                WHERE changed_at > datetime('now', '-1 day')
            ''')
            recent_changes = (await cursor.fetchone())[0]
            
            return {
                'total_brands': brand_count,
                'total_categories': category_count,
                'total_products': product_count,
                'products_by_source': products_by_source,
                'total_price_changes': price_changes,
                'recent_price_changes': recent_changes,
                'brands_by_letter': brands_by_letter
            }
    
    async def print_final_stats(self):
        """Print comprehensive final statistics"""
        elapsed = datetime.now() - self.stats['start_time']
        
        print("\n" + "="*80)
        print("🎉 COMPREHENSIVE SCRAPING COMPLETE!")
        print("="*80)
        print(f"⏱️  Total time: {elapsed}")
        print(f"📊 Letters processed: {self.stats['letters_processed']}")
        print(f"🏷️  Brands found: {self.stats['brands_found']}")
        print(f"🔍 Brands scraped: {self.stats['brands_scraped']}")
        print(f"📂 Categories found: {self.stats['categories_found']}")
        print(f"🔍 Categories scraped: {self.stats['categories_scraped']}")
        print(f"📦 Products found: {self.stats['products_found']}")
        print(f"🆕 New products: {self.stats['products_new']}")
        print(f"💰 Price updates: {self.stats['products_updated']}")
        print(f"✅ Unchanged: {self.stats['products_unchanged']}")
        print(f"❌ Errors: {self.stats['errors']}")
        
        # Database stats
        db_stats = await self.get_database_stats()
        
        print(f"\n💾 Database: {self.db_path}")
        print(f"🏷️  Total brands in DB: {db_stats['total_brands']}")
        print(f"📂 Total categories in DB: {db_stats['total_categories']}")
        print(f"📦 Total products in DB: {db_stats['total_products']}")
        print(f"💰 Total price changes tracked: {db_stats['total_price_changes']}")
        print(f"🕐 Recent price changes (24h): {db_stats['recent_price_changes']}")
        
        print(f"\n📊 Products by source:")
        for source, count in db_stats['products_by_source'].items():
            print(f"  {source}: {count} products")
        
        print("\n📈 Brands by letter:")
        for letter, count in sorted(db_stats['brands_by_letter'].items()):
            print(f"  {letter}: {count} brands")

async def main():
    """Main async function for comprehensive scraping"""
    scraper = AlbertHeijnComprehensiveScraper(max_concurrent=20)
    
    print("🔄 Albert Heijn Comprehensive Scraper - ALL BRANDS A-Z (EXCLUDING 3 AH BRANDS)")
    print("="*70)
    print("This will scrape ALL brands A-Z (excluding AH, AH Biologisch, AH Terra).")
    print("These 3 AH brands will be handled separately by Selenium scraper.")
    print("Other AH brands (AH Basic, AH Excellent, etc.) will be scraped normally.")
    print("Estimated time: 20-40 minutes for complete coverage")
    print("="*70)
    
    print("🚀 Starting comprehensive scraping automatically...")
    
    try:
        # Setup database
        await scraper.setup_database()
        
        # Process all letters A-Z
        letters = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        
        # Create aiohttp session
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,nl;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(headers=headers, connector=connector, timeout=timeout) as session:
            # First, scrape categories
            await scraper.resync_categories(session)
            
            # Then, process letters concurrently
            tasks = [scraper.resync_letter(session, letter) for letter in letters]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count total results
            for result in results:
                if isinstance(result, dict):
                    scraper.stats['letters_processed'] += 1
        
        await scraper.print_final_stats()
        
    except KeyboardInterrupt:
        print("\n⏹️  Resync interrupted by user")
        await scraper.print_final_stats()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await scraper.print_final_stats()

if __name__ == "__main__":
    asyncio.run(main())
