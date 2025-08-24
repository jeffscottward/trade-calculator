#!/usr/bin/env python3
"""
Script to drop the unused earnings_import_history table
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation.database import DatabaseManager

def drop_table():
    """Drop the earnings_import_history table"""
    db = DatabaseManager()
    try:
        # Check if table exists
        result = db.execute_query("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'earnings_import_history'
            );
        """)
        exists = result[0]['exists'] if result else False
        
        if exists:
            print("Table 'earnings_import_history' exists. Dropping...")
            db.execute_update("DROP TABLE IF EXISTS earnings_import_history CASCADE;")
            print("✅ Table 'earnings_import_history' dropped successfully")
        else:
            print("Table 'earnings_import_history' does not exist")
        
    except Exception as e:
        print(f"❌ Error dropping table: {e}")

if __name__ == "__main__":
    drop_table()