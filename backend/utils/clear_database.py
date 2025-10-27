#!/usr/bin/env python3
"""
Clear all data from the AH comprehensive database
"""

import sqlite3
import sys
import os

def clear_database(db_path: str = None):
    """Clear all data from the database while keeping schema"""
    try:
        # Resolve database path to the project root's grocery_database.db by default
        if db_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            db_path = os.path.join(base_dir, "grocery_database.db")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗑️  Clearing database...")
        
        # Delete all data from tables (in correct order due to foreign keys)
        cursor.execute("DELETE FROM price_history")
        print("   ✓ Cleared price_history")
        
        cursor.execute("DELETE FROM products")
        print("   ✓ Cleared products")
        
        cursor.execute("DELETE FROM brands")
        print("   ✓ Cleared brands")
        
        cursor.execute("DELETE FROM categories")
        print("   ✓ Cleared categories")
        
        # Vacuum to reclaim space
        conn.commit()
        conn.execute("VACUUM")
        conn.commit()
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM brands")
        brands_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM categories")
        categories_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM price_history")
        history_count = cursor.fetchone()[0]
        
        total = products_count + brands_count + categories_count + history_count
        
        if total == 0:
            print("\n✅ Database cleared successfully!")
            print(f"   📊 All tables are now empty")
        else:
            print(f"\n⚠️  Warning: {total} records still remain")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error clearing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Allow optional CLI arg for custom DB path
    arg_db_path = sys.argv[1] if len(sys.argv) > 1 else None
    clear_database(arg_db_path)

