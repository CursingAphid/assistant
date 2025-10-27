#!/usr/bin/env python3
"""
Albert Heijn Selenium Scraper for AH Brands
Uses browser automation to click "meer weergeven" and get ALL products
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
from typing import List, Dict
import aiosqlite
import asyncio
import undetected_chromedriver as uc

# Setup logging
import os
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'ah_selenium_scraper.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AHSeleniumScraper:
    def __init__(self, db_path: str = None):
        """Initialize Selenium scraper for AH brands"""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if db_path is None:
            self.db_path = os.path.join(base_dir, "grocery_database.db")
        else:
            self.db_path = db_path if os.path.isabs(db_path) else os.path.abspath(os.path.join(base_dir, db_path))
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome driver with undetected-chromedriver to bypass Cloudflare"""
        try:
            # Use undetected-chromedriver which automatically bypasses most anti-bot systems
            options = uc.ChromeOptions()
            
            # Run in normal mode (not headless) to avoid detection
            # options.add_argument('--headless=new')  # Keep disabled to avoid detection
            
            # Incognito mode
            options.add_argument('--incognito')
            
            # Optional: Reduce fingerprinting
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-features=IsolateOrigins,site-per-process')
            
            # Create the driver with undetected-chromedriver
            self.driver = uc.Chrome(
                version_main=None,  # Auto-detect Chrome version
                options=options,
                use_subprocess=False  # Use single process
            )
            
            logger.info("Chrome driver setup complete with undetected-chromedriver")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            # Fallback to regular selenium if undetected fails
            try:
                options = Options()
                options.add_argument('--incognito')
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                logger.warning("Fallback to regular Chrome driver")
                return True
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                return False
    
    async def scrape_ah_brand(self, brand_name: str, brand_url: str, brand_id: int = None) -> List[Dict[str, str]]:
        """Scrape all products from an AH brand using Selenium"""
        if not self.driver:
            if not self.setup_driver():
                return []
        
        logger.info(f"🔍 Selenium scraping AH brand: {brand_name}")
        
        try:
            # Check if driver is still active
            if not self.driver:
                logger.error(f"Driver not available for {brand_name}")
                return []
            
            # Navigate to brand page
            logger.info(f"Navigating to {brand_url}")
            self.driver.get(brand_url)
            
            # Add random delay to appear more human-like
            import random
            time.sleep(random.uniform(3, 6))  # Wait 3-6 seconds randomly
            
            logger.info(f"Page loaded, waiting for content")
            
            # Handle privacy/cookie consent message using Selenium (avoid PyAutoGUI)
            try:
                wait = WebDriverWait(self.driver, 10)
                decline_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testhook='decline-cookies']"))
                )
                decline_button.click()
                logger.info(f"Dismissed privacy consent for {brand_name} via Selenium click")
                time.sleep(1)
            except TimeoutException:
                logger.debug("Privacy consent decline button not found (already dismissed or not present)")
            except Exception as e:
                logger.debug(f"Could not dismiss privacy consent for {brand_name} via Selenium: {e}")
            
            # Check for "Access Denied" or similar
            if "access denied" in self.driver.page_source.lower():
                logger.error(f"Access denied for {brand_name}")
                return []
            
            all_products = []
            
            # First, get products from the main page (no filters)
            logger.info(f"📦 Scraping main page products for {brand_name}")
            main_products = await self.scrape_products_from_current_page(brand_name, brand_id)
            all_products.extend(main_products)
            logger.info(f"Found {len(main_products)} products on main page")
            
            # Save initial products to database
            if main_products:
                try:
                    stats = await self.smart_save_products(main_products, brand_id=brand_id, source_type=brand_name)
                except Exception as save_error:
                    logger.error(f"Error saving initial products: {save_error}")
            
            # Step 1: Collect all filter URLs first
            filter_buttons = await self.find_filter_buttons()
            logger.info(f"🔍 Found {len(filter_buttons)} filter buttons: {[btn['text'] for btn in filter_buttons]}")
            
            # Step 2: Process each filter URL sequentially
            for i, filter_info in enumerate(filter_buttons):
                try:
                    logger.info(f"🎯 Processing filter {i+1}/{len(filter_buttons)}: {filter_info['text']}")
                    
                    # Get the filter URL
                    target_url = filter_info.get('url')
                    if not target_url:
                        logger.warning(f"No URL found for filter '{filter_info['text']}' - skipping")
                        continue
                    
                    logger.info(f"🌐 Navigating to: {target_url}")
                    
                    # Navigate to the filter URL
                    self.driver.get(target_url)
                    time.sleep(3)  # Wait for filtered page to load
                    
                    # Click "meer weergeven" until no more button
                    await self.click_meer_weergeven_until_done(f"{brand_name} - {filter_info['text']}", brand_id)
                    
                    # Get final product count for this filter
                    final_products = await self.scrape_products_from_current_page(
                        f"{brand_name} - {filter_info['text']}",
                        brand_id
                    )
                    all_products.extend(final_products)
                    logger.info(f"✅ Filter '{filter_info['text']}' complete - {len(final_products)} total products processed")
                    
                    # Move to next filter (no need to return to base URL)
                    logger.info(f"➡️  Moving to next filter...")
                    logger.info(f"📍 Current URL after filter: {self.driver.current_url}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing filter {filter_info.get('text', 'unknown')}: {e}")
                    # Continue to next filter even if this one failed
                    continue
            
            # Remove duplicates based on product URL
            unique_products = []
            seen_urls = set()
            for product in all_products:
                if product.get('url') and product['url'] not in seen_urls:
                    seen_urls.add(product['url'])
                    unique_products.append(product)
            
            logger.info(f"📊 Total unique products found: {len(unique_products)} (removed {len(all_products) - len(unique_products)} duplicates)")
            return unique_products
            
        except Exception as e:
            logger.error(f"Error scraping {brand_name}: {e}")
            # If window was closed, try to restart driver
            if "no such window" in str(e).lower() or "web view not found" in str(e).lower():
                logger.info(f"Window closed for {brand_name}, attempting to restart driver...")
                try:
                    self.close_driver()
                    time.sleep(2)
                    self.setup_driver()
                except Exception as restart_error:
                    logger.error(f"Failed to restart driver: {restart_error}")
            return []
    
    async def find_filter_buttons(self) -> List[Dict[str, any]]:
        """Find available filter quick-links (anchor elements) and return text + full URL."""
        filter_links: List[Dict[str, any]] = []
        try:
            # Prefer the quick-link anchors used by AH filters
            anchors = self.driver.find_elements(By.CSS_SELECTOR, "a[data-testhook='filter-item']")
            for a in anchors:
                try:
                    title_el = a.find_element(By.CSS_SELECTOR, "[data-testhook='filter-item-title']")
                    amount_el = None
                    try:
                        amount_el = a.find_element(By.CSS_SELECTOR, "[data-testhook='filter-item-amount']")
                    except Exception:
                        amount_el = None

                    title = title_el.text.strip() if title_el else a.text.strip()
                    amount = amount_el.text.strip() if amount_el else ""
                    text = f"{title} {amount}".strip()

                    href = a.get_attribute('href')
                    if href and href.startswith('/'):
                        href = f"https://www.ah.nl{href}"

                    # Only keep known filters to avoid unrelated links
                    if any(k in title.lower() for k in [
                        'bonus', 'prijsfavoriet', 'vega', 'vegan', 'nederland', 'diepvries', 'nieuw'
                    ]):
                        filter_links.append({'text': text, 'url': href})
                        logger.debug(f"Found filter link: {text} -> {href}")
                except Exception:
                    continue

            # Fallback to previous xpath strategy if anchors not found
            if not filter_links:
                candidates = self.driver.find_elements(By.XPATH, "//span[contains(@class,'quick-link_text') or contains(text(),'BONUS') or contains(text(),'Prijsfavoriet') or contains(text(),'Vega') or contains(text(),'Vegan') or contains(text(),'Uit Nederland') or contains(text(),'Diepvries') or contains(text(),'Nieuw')]/ancestor::a[1]")
                for a in candidates:
                    try:
                        text = a.text.strip()
                        href = a.get_attribute('href')
                        if href and href.startswith('/'):
                            href = f"https://www.ah.nl{href}"
                        if any(k in text.lower() for k in [
                            'bonus', 'prijsfavoriet', 'vega', 'vegan', 'nederland', 'diepvries', 'nieuw'
                        ]):
                            filter_links.append({'text': text, 'url': href})
                    except Exception:
                        continue

            # De-duplicate by text
            unique: List[Dict[str, any]] = []
            seen = set()
            for fl in filter_links:
                key = fl['text'].lower()
                if key not in seen:
                    seen.add(key)
                    unique.append(fl)

            logger.info(f"Found {len(unique)} unique filter links")
            return unique
        except Exception as e:
            logger.error(f"Error finding filter buttons: {e}")
            return []
    
    async def clear_all_active_filters(self):
        """Clear all currently active filters by clicking them"""
        try:
            # Find all active filter buttons (they usually have a different class or attribute when active)
            active_filter_selectors = [
                "//button[contains(@class, 'active')]",
                "//button[contains(@class, 'selected')]", 
                "//button[contains(@class, 'filter') and contains(@class, 'active')]",
                "//button[contains(@class, 'filter-chip') and contains(@class, 'active')]",
                "//button[@aria-pressed='true']",
                "//button[contains(@class, 'filter') and @aria-pressed='true']"
            ]
            
            active_filters_cleared = 0
            for selector in active_filter_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        try:
                            # Click to deactivate the filter
                            self.driver.execute_script("arguments[0].click();", element)
                            active_filters_cleared += 1
                            logger.debug(f"Cleared active filter: {element.text.strip()}")
                        except:
                            continue
                except:
                    continue
            
            if active_filters_cleared > 0:
                logger.info(f"🧹 Cleared {active_filters_cleared} active filters")
                time.sleep(1)  # Wait for filters to be cleared
            else:
                logger.debug("No active filters found to clear")
                
        except Exception as e:
            logger.debug(f"Error clearing active filters: {e}")
    
    async def is_filter_active(self, filter_element) -> bool:
        """Check if a filter button is currently active"""
        try:
            # Check various indicators that a filter is active
            active_indicators = [
                'active' in filter_element.get_attribute('class').lower(),
                'selected' in filter_element.get_attribute('class').lower(),
                filter_element.get_attribute('aria-pressed') == 'true',
                'data-active' in filter_element.get_attribute('outerHTML').lower()
            ]
            
            return any(active_indicators)
        except Exception as e:
            logger.debug(f"Error checking if filter is active: {e}")
            return False

    async def click_meer_weergeven_until_done(self, filter_name: str, brand_id: int = None) -> None:
        """Click 'meer weergeven' button until no more button is found"""
        try:
            max_clicks = 1000  # Set a reasonable limit
            click_count = 0
            button_timeout = 30  # seconds
            last_button_time = time.time()
            
            logger.info(f"🔄 Starting 'meer weergeven' clicking for {filter_name}")
            
            while click_count < max_clicks:
                try:
                    # Look for "meer weergeven" button with specific selectors
                    button_selectors = [
                        "//button[@data-testhook='load-more']",  # Most specific
                        "//button[contains(@aria-label, 'toon meer resultaten')]",
                        "//button[contains(@class, 'button-or-anchor_root__LgpRR')]",
                        "//button[contains(@class, 'button-default_root__DAGWZ')]",
                        "//span[contains(text(), 'Meer resultaten')]/parent::button",
                        "//button[contains(text(), 'Meer resultaten')]",
                        "//button[contains(text(), 'meer weergeven')]",
                        "//button[contains(text(), 'Meer weergeven')]"
                    ]
                    
                    button = None
                    for selector in button_selectors:
                        try:
                            button = WebDriverWait(self.driver, 1).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            break
                        except:
                            continue
                    
                    if button:
                        # Reset timeout timer since we found a button
                        last_button_time = time.time()
                        
                        # Scroll to button first
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(1)
                        
                        # Try multiple clicking methods
                        clicked = False
                        
                        # Method 1: Try JavaScript click first (most reliable)
                        try:
                            self.driver.execute_script("arguments[0].click();", button)
                            clicked = True
                            logger.info(f"Clicked 'meer weergeven' #{click_count + 1} for {filter_name} using JavaScript")
                        except Exception as js_error:
                            logger.debug(f"JavaScript click failed: {js_error}")
                        
                        # Method 2: Try PyAutoGUI click
                        if not clicked:
                            try:
                                import pyautogui
                                # Get button's center coordinates
                                location = button.location
                                size = button.size
                                center_x = location['x'] + size['width'] // 2
                                center_y = location['y'] + size['height'] // 2
                                
                                # Click the button with PyAutoGUI
                                pyautogui.click(center_x, center_y)
                                clicked = True
                                logger.info(f"Clicked 'meer weergeven' #{click_count + 1} for {filter_name} using PyAutoGUI")
                            except Exception as pyautogui_error:
                                logger.debug(f"PyAutoGUI click failed: {pyautogui_error}")
                        
                        # Method 3: Try Selenium click as last resort
                        if not clicked:
                            try:
                                button.click()
                                clicked = True
                                logger.info(f"Clicked 'meer weergeven' #{click_count + 1} for {filter_name} using Selenium")
                            except Exception as selenium_error:
                                logger.debug(f"Selenium click failed: {selenium_error}")
                        
                        if clicked:
                            click_count += 1
                            time.sleep(2)  # Wait for new products to load
                            
                            # Check if URL changed unexpectedly (went back to base page)
                            current_url = self.driver.current_url
                            if 'kenmerk=' not in current_url:
                                logger.warning(f"⚠️  URL changed unexpectedly after click #{click_count}: {current_url}")
                                logger.info(f"🔄 Expected filter URL, but got base page. Stopping this filter.")
                                break
                            
                            # Extract and save products after each click
                            try:
                                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                                product_articles = soup.select('article.product-card-portrait_root__ZiRpZ')
                                
                                # Extract new products from current page
                                new_products = []
                                for article in product_articles:
                                    try:
                                        product = self.extract_product_info(article)
                                        if product:
                                            new_products.append(product)
                                    except Exception as e:
                                        logger.debug(f"Error extracting product: {e}")
                                        continue
                                
                                # Save products to database after each click
                                if new_products:
                                    try:
                                        stats = await self.smart_save_products(
                                            new_products,
                                            brand_id=brand_id,  # Use the same brand_id for all filters
                                            source_type="selenium"  # Use consistent source type
                                        )
                                        logger.info(f"💾 Click #{click_count}: Saved {len(new_products)} products - {stats['new']} new, {stats['updated']} updated, {stats['unchanged']} unchanged")
                                    except Exception as save_error:
                                        logger.error(f"Error saving products after click #{click_count}: {save_error}")
                                else:
                                    logger.warning(f"No products found after click #{click_count}")
                                    
                            except Exception as extract_error:
                                logger.error(f"Error extracting products after click #{click_count}: {extract_error}")
                        else:
                            logger.warning(f"All click methods failed for {filter_name}")
                            break
                    else:
                        # Check if we've been waiting too long for a button
                        current_time = time.time()
                        if current_time - last_button_time > button_timeout:
                            logger.info(f"No 'meer weergeven' button found for {button_timeout} seconds - all items loaded for {filter_name}")
                            break
                        
                        # Wait 1 second before checking again
                        time.sleep(1)
                        
                except Exception as e:
                    logger.info(f"No more 'meer weergeven' button found for {filter_name}: {e}")
                    break
            
            logger.info(f"✅ Finished clicking 'meer weergeven' for {filter_name} - clicked {click_count} times")
            
        except Exception as e:
            logger.error(f"Error clicking 'meer weergeven' for {filter_name}: {e}")

    async def scrape_products_from_current_page(self, brand_name: str, brand_id: int = None) -> List[Dict[str, str]]:
        """Scrape all products visible on the current page"""
        products = []
        
        try:
            # Wait a moment for page to stabilize
            time.sleep(2)
            
            # Extract products from current page
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            product_articles = soup.select('article.product-card-portrait_root__ZiRpZ')
            
            logger.info(f"Found {len(product_articles)} product articles on current page for {brand_name}")
            
            for article in product_articles:
                try:
                    product = self.extract_product_info(article)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.debug(f"Error extracting product: {e}")
                    continue
            
            logger.info(f"Extracted {len(products)} products from current page for {brand_name}")
            return products
            
        except Exception as e:
            logger.error(f"Error scraping products from current page: {e}")
            return []

    def extract_product_info(self, article) -> Dict[str, str]:
        """Extract product information from an article element"""
        try:
            # Extract price from the specific price elements FIRST to avoid confusion with unit sizes
            price = None
            price_amounts = article.select('div[data-testhook="price-amount"]')
            # Preference 1: aria-label that starts with "Prijs:" (current price), skip "Oude prijs"
            for pa in price_amounts:
                sr = pa.select_one('.sr-only')
                aria = sr.get('aria-label', '') if sr else ''
                if aria and aria.lower().startswith('prijs:'):
                    m = re.search(r'€\s*(\d+[,.]\d{2})', aria)
                    if m:
                        price = f"€{m.group(1)}"
                        break
            # Preference 2: highlighted/bonus price-amount block
            if not price and price_amounts:
                highlighted = None
                for pa in price_amounts:
                    cls = pa.get('class') or []
                    cls_str = ' '.join(cls).lower()
                    if 'price-amount_highlight' in cls_str or 'price-amount_bonus' in cls_str:
                        highlighted = pa
                        break
                target = highlighted or price_amounts[-1]
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
                else:
                    logger.debug(f"Could not find price parts on target element")
            
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
            is_active_sale, is_future_sale, sale_price, sale_starts_at, sale_type = self.detect_sale_and_calculate_price(article, price)
            
            product = {
                'name': product_name,
                'price': price,
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
        # Find "AH" in the text and extract everything after it until price or end
        ah_match = re.search(r'AH\s+(.+?)(?:\s*-\s*€|\s*€|\s*$)', text, re.IGNORECASE)
        if not ah_match:
            # Try alternative pattern for cases like "Kieslos2 stuksAH"
            ah_match = re.search(r'stuksAH\s+(.+?)(?:\s*-\s*€|\s*€|\s*$)', text, re.IGNORECASE)
        if ah_match:
            product_name = ah_match.group(1).strip()
            
            # Clean up the product name - remove trailing dashes and spaces
            product_name = re.sub(r'\s*-\s*$', '', product_name)
            product_name = re.sub(r'\s*€.*$', '', product_name)  # Remove any remaining price info
            
            # Remove common suffixes and prefixes
            product_name = re.sub(r'\s+(ml|g|l|stuks|kg|cl|per stuk|per pakket|online|pakket|korting|voordeel|nieuw|vegan|biologisch|halal|kosher|prijsfavoriet|kieslos|uit nederland|diepvries|zelf afbakken|2e gratis|2 voor|3 voor|voor|pers min|wasbeurten|meter|gram|st|ca\.|kg|ml|stuks|pers|min|euro korting|halve prijs)', '', product_name, flags=re.IGNORECASE)
            
            # Clean up extra spaces and special characters
            product_name = re.sub(r'\s+', ' ', product_name).strip()
            product_name = re.sub(r'^[-\+\d\s]*', '', product_name)  # Remove leading numbers, dashes, plus signs
            
            # If we have a meaningful product name, return it
            if len(product_name) > 2 and not re.match(r'^[0-9,.\s\-+]*$', product_name):
                return product_name
        
        # Fallback: try to extract meaningful parts from the original text
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
    
    async def save_products_to_db(self, products: List[Dict[str, str]], brand_name: str) -> Dict[str, int]:
        """Save products to database"""
        if not products:
            return {'new': 0, 'updated': 0, 'unchanged': 0}
        
        async with aiosqlite.connect(self.db_path) as conn:
            stats = {'new': 0, 'updated': 0, 'unchanged': 0}
            
            try:
                # Get brand_id
                cursor = await conn.execute('SELECT id FROM brands WHERE name = ?', (brand_name,))
                result = await cursor.fetchone()
                brand_id = result[0] if result else None
                
                if not brand_id:
                    logger.error(f"Brand {brand_name} not found in database")
                    return stats
                
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
                                INSERT INTO price_history (product_id, price, changed_at)
                                VALUES (?, ?, CURRENT_TIMESTAMP)
                            ''', (product_id, price_float))
                            
                            stats['updated'] += 1
                            logger.info(f"💰 Price changed: {product['name']} {old_price} → {price_float}")
                        else:
                            # Price unchanged
                            stats['unchanged'] += 1
                    else:
                        # New product
                        # Convert price to float
                        price_float = self.extract_price_numeric(product['price'])
                        
                        cursor = await conn.execute('''
                            INSERT INTO products (brand_id, name, current_price, url, source_type, page_number)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (brand_id, product['name'], price_float, product['url'], 'selenium', 0))
                        
                        product_id = cursor.lastrowid
                        
                        # Add initial price to history
                        await conn.execute('''
                            INSERT INTO price_history (product_id, price)
                            VALUES (?, ?)
                        ''', (product_id, price_float))
                        
                        stats['new'] += 1
                        # Don't log individual new products - will show summary at the end
                
                await conn.commit()
                
                # Log summary of changes
                if stats['new'] > 0:
                    logger.info(f"🆕 Added {stats['new']} new products")
                if stats['updated'] > 0:
                    logger.info(f"💰 Updated {stats['updated']} products with price changes")
                if stats['unchanged'] > 0:
                    logger.info(f"✅ {stats['unchanged']} products unchanged")
                
                return stats
                
            except Exception as e:
                logger.error(f"Error saving products: {e}")
                return stats
    
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
                
                await conn.commit()
        except Exception as e:
            logger.error(f"Error updating database schema: {e}")
    
    def close_driver(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Browser driver closed")
    
    async def run_selenium_scrape(self, brands: List[Dict[str, str]]) -> Dict[str, int]:
        """Run selenium scraping for AH brands"""
        total_products = 0
        total_new = 0
        total_updated = 0
        total_unchanged = 0
        
        try:
            for brand in brands:
                logger.info(f"🔍 Selenium scraping brand: {brand['name']}")
                
                products = await self.scrape_ah_brand(brand['name'], brand['url'], brand_id=None)
                
                if products:
                    stats = await self.smart_save_products(products, brand_id=None, source_type=brand['name'])
                    
                    total_products += len(products)
                    total_new += stats['new']
                    total_updated += stats['updated']
                    total_unchanged += stats['unchanged']
                    
                    logger.info(f"📦 {brand['name']}: {len(products)} products processed")
                else:
                    logger.warning(f"No products found for {brand['name']}")
            
            return {
                'products_found': total_products,
                'products_new': total_new,
                'products_updated': total_updated,
                'products_unchanged': total_unchanged
            }
            
        except Exception as e:
            logger.error(f"Error during selenium scraping: {e}")
            return {
                'products_found': total_products,
                'products_new': total_new,
                'products_updated': total_updated,
                'products_unchanged': total_unchanged
            }
        finally:
            self.close_driver()
    
    async def smart_save_products(self, products: List[Dict[str, str]], brand_id: int = None, source_type: str = "brand") -> Dict[str, int]:
        """Smart save products with price change detection"""
        if not products:
            return {'new': 0, 'updated': 0, 'unchanged': 0}
        
        async with aiosqlite.connect(self.db_path) as conn:
            stats = {'new': 0, 'updated': 0, 'unchanged': 0}
            
            try:
                # If brand_id is not provided, we'll need to get it from the brand name
                # For now, we'll use a default brand_id or create one if needed
                if not brand_id:
                    # Try to get or create brand_id for AH brands
                    cursor = await conn.execute('SELECT id FROM brands WHERE name = ?', (source_type,))
                    result = await cursor.fetchone()
                    brand_id = result[0] if result else None
                    
                    # If exact match not found, create the brand
                    if not brand_id:
                        cursor = await conn.execute('''
                            INSERT INTO brands (name, url, letter) 
                            VALUES (?, ?, ?)
                        ''', (source_type, f"https://www.ah.nl/producten/merk/{source_type.lower().replace(' ', '-')}", 'A'))
                        brand_id = cursor.lastrowid
                        await conn.commit()
                
                if not brand_id:
                    logger.error(f"Brand ID not found for {source_type}")
                    return stats
                
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
                                INSERT INTO price_history (product_id, price, changed_at)
                                VALUES (?, ?, CURRENT_TIMESTAMP)
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
                            INSERT INTO products (brand_id, name, current_price, url, source_type, page_number, isSale, isFutureSale, salePrice, saleStartsAt, saleType)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (brand_id, product['name'], price_float, product['url'], 'selenium', 0, int(is_sale), int(is_future_sale), sale_price, sale_starts_at, sale_type))
                        
                        product_id = cursor.lastrowid
                        
                        # Add initial price to history
                        await conn.execute('''
                            INSERT INTO price_history (product_id, price)
                            VALUES (?, ?)
                        ''', (product_id, price_float))
                        
                        stats['new'] += 1
                        # Don't log individual new products - will show summary at the end
                
                await conn.commit()
                
                # Log summary of changes
                if stats['new'] > 0:
                    logger.info(f"🆕 Added {stats['new']} new products")
                if stats['updated'] > 0:
                    logger.info(f"💰 Updated {stats['updated']} products with price changes")
                if stats['unchanged'] > 0:
                    logger.info(f"✅ {stats['unchanged']} products unchanged")
                
                return stats
                
            except Exception as e:
                logger.error(f"Error saving products: {e}")
                return stats
    
    async def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Count products
                cursor = await db.execute("SELECT COUNT(*) FROM products")
                product_count = (await cursor.fetchone())[0]
                
                # Count brands
                cursor = await db.execute("SELECT COUNT(*) FROM brands")
                brand_count = (await cursor.fetchone())[0]
                
                # Count categories
                cursor = await db.execute("SELECT COUNT(*) FROM categories")
                category_count = (await cursor.fetchone())[0]
                
                # Count products by source
                cursor = await db.execute("SELECT source_type, COUNT(*) FROM products GROUP BY source_type")
                products_by_source = dict(await cursor.fetchall())
                
                # Count price changes
                cursor = await db.execute("SELECT COUNT(*) FROM price_history")
                price_changes = (await cursor.fetchone())[0]
                
                # Recent price changes (last 24 hours)
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM price_history 
                    WHERE changed_at > datetime('now', '-1 day')
                """)
                recent_changes = (await cursor.fetchone())[0]
                
                return {
                    'total_products': product_count,
                    'total_brands': brand_count,
                    'total_categories': category_count,
                    'products_by_source': products_by_source,
                    'total_price_changes': price_changes,
                    'recent_price_changes': recent_changes
                }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {
                'total_products': 0,
                'total_brands': 0,
                'total_categories': 0,
                'products_by_source': {},
                'total_price_changes': 0,
                'recent_price_changes': 0
            }

async def main():
    """Main function to scrape AH brands with Selenium"""
    scraper = AHSeleniumScraper()
    
    # Update database schema to add sale tracking columns
    await scraper.update_database_schema()
    
    # AH brands that need Selenium scraping
    ah_brands = [
        {"name": "AH", "url": "https://www.ah.nl/producten/merk/ah"},
        {"name": "AH Biologisch", "url": "https://www.ah.nl/producten/merk/ah-biologisch"},
        {"name": "AH Terra", "url": "https://www.ah.nl/producten/merk/ah-terra"}
    ]
    
    print("🤖 Albert Heijn Selenium Scraper - AH Brands")
    print("="*60)
    print("This will use browser automation to get ALL AH products")
    print("Estimated time: 10-20 minutes for 3 AH brands")
    print("="*60)
    
    try:
        total_products = 0
        total_new = 0
        total_updated = 0
        total_unchanged = 0
        
        for brand in ah_brands:
            logger.info(f"🚀 Starting Selenium scrape for {brand['name']}")
            
            # Scrape products using Selenium
            products = await scraper.scrape_ah_brand(brand['name'], brand['url'], brand_id=None)
            
            if products:
                # Save to database
                stats = await scraper.save_products_to_db(products, brand['name'])
                
                total_products += len(products)
                total_new += stats['new']
                total_updated += stats['updated']
                total_unchanged += stats['unchanged']
                
                logger.info(f"📦 {brand['name']}: {len(products)} products processed")
            else:
                logger.warning(f"No products found for {brand['name']}")
        
        print("\n" + "="*60)
        print("🎉 SELENIUM SCRAPING COMPLETE!")
        print("="*60)
        print(f"📦 Total products: {total_products}")
        print(f"🆕 New products: {total_new}")
        print(f"💰 Price updates: {total_updated}")
        print(f"✅ Unchanged: {total_unchanged}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Selenium scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        scraper.close_driver()

if __name__ == "__main__":
    asyncio.run(main())
