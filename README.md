# 🛒 Albert Heijn Price Checker

A comprehensive Python project for checking Albert Heijn product prices with multiple interfaces and database capabilities.

## ✨ Features

- **Real-time price checking** from Albert Heijn website
- **Beautiful Streamlit web interface** with autocomplete
- **Complete website price scanner** with database storage
- **SQLite database** with price history tracking
- **n8n workflow integration** for automation
- **Python API** for programmatic access
- **Demo data** for testing and development

## 🚀 Quick Start

### Prerequisites
- Python 3.9+ (required for modern type hints like tuple[...])
- Node.js (for n8n integration)

### Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Start n8n (optional):**
```bash
npm start
```
Access n8n at http://localhost:5678

## 🖥️ Interfaces

The previous Streamlit UI and related scripts are not part of this refactor. Current focus is on scrapers and database.

### App Features

1. **Search Interface**: Type any product name to check prices
2. **Quick Buttons**: One-click search for melk, brood, kaas, eieren, appels, yoghurt
3. **Search History**: View and repeat previous searches
4. **Real-time Results**: Live price checking with Albert Heijn
5. **Settings Panel**: Choose scraping method and auto-refresh options
6. **Responsive Design**: Works on desktop, tablet, and mobile
7. **Find Cheapest**: Button to find cheapest products across all categories

## 🗄️ Database and Scrapers

Tools to scrape AH categories/brands and store prices in an SQLite database at `grocery_database.db`.

### Usage

```bash
# Clear DB tables (keeps schema)
python3 backend/utils/clear_database.py

# Run AH comprehensive scraper (example; see script docstring for details)
# python3 backend/scrapers/AH/ah_comprehensive_scraper.py --db ./grocery_database.db

# Run Selenium scraper for AH brands (example)
# python3 backend/scrapers/AH/ah_selenium_scraper.py --db ./grocery_database.db
```

### Features

- **🔍 Complete Website Scan** - Scans all Albert Heijn categories
- **💾 SQLite Database** - Stores all products with prices, brands, categories
- **📊 Price History** - Tracks price changes over time
- **🏷️ Category Analysis** - Organizes products by category
- **🏢 Brand Analysis** - Groups products by brand
- **📈 Data Analytics** - Comprehensive analysis tools
- **📤 Export Options** - Export data to CSV
- **🔄 Incremental Updates** - Update existing products

### Database Schema

**Products Table:**
- Product name, brand, category
- Current price, unit price
- Product URL, image URL
- Availability, discount info
- Creation/update timestamps

**Price History Table:**
- Historical price data
- Price change tracking
- Scan timestamps

**Categories Table:**
- Category information
- Product counts
- Last scan timestamps

### Scanner Capabilities

1. **Multi-Strategy Scanning** - Uses different URL patterns to find all products
2. **Duplicate Prevention** - Avoids storing duplicate products
3. **Price Change Tracking** - Records price history for analysis
4. **Error Handling** - Robust error handling and logging
5. **Progress Tracking** - Real-time progress updates
6. **Respectful Scraping** - Rate limiting and delays

### Analysis

You can inspect the SQLite DB directly (e.g., with DB Browser for SQLite) or add your own analysis scripts.

**Analysis Features:**
- Database statistics and overview
- Product search functionality
- Cheapest/most expensive products
- Category and brand analysis
- Price distribution analysis
- Price history tracking
- CSV export capabilities

### Example Usage

```bash
# Start complete scan (may take hours)
python3 run_scanner.py
# Choose option 1

# Analyze results
python3 run_scanner.py
# Choose option 2

# Quick stats
python3 run_scanner.py
# Choose option 3
```

## 🔧 Python API

The previous ad-hoc API helpers referenced here were removed in this refactor.

## 🔗 n8n Integration

Use `npm start` to launch n8n. Any previous example workflow/client files were removed.

## 📁 Project Structure (key files)

```
backend/
  utils/
    clear_database.py
  scrapers/
    AH/
      ah_comprehensive_scraper.py
      ah_selenium_scraper.py
    Aldi/
      aldi_comprehensive_scraper.py
grocery_database.db
requirements.txt
package.json
README.md
```

## 🎯 Use Cases

- **Price comparison** across categories
- **Finding cheapest products** in each category
- **Brand analysis** and pricing strategies
- **Historical price tracking** and trends
- **Data analysis** and insights
- **Budget shopping** optimization
- **Workflow automation** with n8n

## 📊 Example Results

### Streamlit Interface
- Real-time price checking with autocomplete
- Search history and statistics
- Beautiful responsive design
- Find cheapest products feature

### Database Scanner
```
📊 Database Overview:
Total products: 15,432
Categories: 20
Brands: 1,247
Products with prices: 15,432
Price range: €0.85 - €89.99
Average price: €3.47
Recent scan days: 7

🏷️ Top Categories by Product Count:
  Groente & Fruit: 2,156 products (avg: €2.34)
  Melk & Zuivel: 1,847 products (avg: €2.89)
  Brood & Banket: 1,234 products (avg: €1.95)
  ...
```

## 🚀 Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. (Optional) Start n8n: `npm start`
3. Use the scrapers in `backend/utils/scrapers/AH` to populate `grocery_database.db`

## 📝 License

This project is for educational and personal use. Please respect Albert Heijn's terms of service when using the scraping functionality.

## 🤝 Contributing

Feel free to submit issues and enhancement requests!