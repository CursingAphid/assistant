#!/usr/bin/env python3
"""
Complete Albert Heijn Data Sync Script
This single script syncs ALL Albert Heijn data:
1. All brands A-Z (except AH brands) - ~17,000 products
2. AH brands (AH, AH Biologisch, AH Terra) - ~10,000+ products
3. All categories
4. Smart resync with price history
"""

import asyncio
import logging
import aiohttp
from datetime import datetime
from AH.ah_comprehensive_scraper import AlbertHeijnComprehensiveScraper
from AH.ah_selenium_scraper import AHSeleniumScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('AH/complete_ah_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Complete Albert Heijn data sync"""
    print("🔄 COMPLETE ALBERT HEIJN DATA SYNC")
    print("="*70)
    print("This will sync ALL Albert Heijn data:")
    print("• All brands A-Z (except AH brands) - ~17,000 products")
    print("• AH brands (AH, AH Biologisch, AH Terra) - ~10,000+ products") 
    print("• All categories")
    print("• Smart resync with price history")
    print("="*70)
    
    start_time = datetime.now()
    
    try:
        # Step 1: Comprehensive scraping (all brands except AH)
        print("\n🚀 STEP 1: Comprehensive Brand Scraping")
        print("-" * 50)
        comprehensive_scraper = AlbertHeijnComprehensiveScraper(max_concurrent=20)
        
        # Run comprehensive scraping for all letters A-Z
        letters = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        
        # Setup database
        await comprehensive_scraper.setup_database()
        
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
            await comprehensive_scraper.resync_categories(session)
            
            # Then, process letters concurrently
            tasks = [comprehensive_scraper.resync_letter(session, letter) for letter in letters]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count total results
            comprehensive_results = {
                'brands_scraped': 0,
                'products_found': 0,
                'products_new': 0,
                'products_updated': 0,
                'products_unchanged': 0
            }
            
            for result in results:
                if isinstance(result, dict):
                    comprehensive_results['brands_scraped'] += result.get('brands', 0)
                    comprehensive_results['products_found'] += result.get('products', 0)
                    comprehensive_results['products_new'] += result.get('new', 0)
                    comprehensive_results['products_updated'] += result.get('updated', 0)
                    comprehensive_results['products_unchanged'] += result.get('unchanged', 0)
        
        print(f"\n✅ Comprehensive scraping complete!")
        print(f"📊 Brands scraped: {comprehensive_results.get('brands_scraped', 0)}")
        print(f"📦 Products found: {comprehensive_results.get('products_found', 0)}")
        print(f"🆕 New products: {comprehensive_results.get('products_new', 0)}")
        print(f"💰 Price updates: {comprehensive_results.get('products_updated', 0)}")
        
        # Step 2: Selenium scraping (AH brands)
        print("\n🚀 STEP 2: AH Brand Scraping (Selenium)")
        print("-" * 50)
        selenium_scraper = AHSeleniumScraper()
        
        ah_brands = [
            {'name': 'AH', 'url': 'https://www.ah.nl/producten/merk/ah'},
            {'name': 'AH Biologisch', 'url': 'https://www.ah.nl/producten/merk/ah-biologisch'},
            {'name': 'AH Terra', 'url': 'https://www.ah.nl/producten/merk/ah-terra'},
        ]
        
        await selenium_scraper.run_selenium_scrape(ah_brands)
        
        # Final statistics
        elapsed = datetime.now() - start_time
        print("\n" + "="*70)
        print("🎉 COMPLETE ALBERT HEIJN SYNC FINISHED!")
        print("="*70)
        print(f"⏱️  Total time: {elapsed}")
        print(f"📊 Comprehensive brands: {comprehensive_results.get('brands_scraped', 0)}")
        print(f"📦 Comprehensive products: {comprehensive_results.get('products_found', 0)}")
        print(f"🤖 Selenium brands: 3 (AH, AH Biologisch, AH Terra)")
        print(f"💾 Database: ../grocery_database.db")
        
        # Get final database stats
        db_stats = await selenium_scraper.get_database_stats()
        print(f"\n📊 FINAL DATABASE STATISTICS:")
        print(f"🏷️  Total brands: {db_stats['total_brands']}")
        print(f"📂 Total categories: {db_stats['total_categories']}")
        print(f"📦 Total products: {db_stats['total_products']}")
        print(f"💰 Total price changes: {db_stats['total_price_changes']}")
        print(f"🕐 Recent changes (24h): {db_stats['recent_price_changes']}")
        
        print(f"\n📈 Products by source:")
        for source, count in db_stats['products_by_source'].items():
            print(f"  {source}: {count} products")
            
    except Exception as e:
        logger.error(f"Error during complete sync: {e}")
        print(f"\n❌ Error during sync: {e}")
        print("Check the log file for details: complete_ah_sync.log")

if __name__ == "__main__":
    asyncio.run(main())
