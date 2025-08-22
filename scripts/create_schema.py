#!/usr/bin/env python3
"""Create database schema for earnings data"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def create_schema():
    """Create the earnings database schema"""
    
    # Read the schema file
    with open('automation/database/schema_earnings.sql', 'r') as f:
        schema_sql = f.read()
    
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        # Execute schema creation
        cursor.execute(schema_sql)
        conn.commit()
        print("✅ Database schema created successfully!")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('earnings_calendar', 'earnings_import_history')
        """)
        
        tables = cursor.fetchall()
        print(f"📊 Created tables: {[t[0] for t in tables]}")
        
    except Exception as e:
        print(f"❌ Error creating schema: {str(e)}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_schema()