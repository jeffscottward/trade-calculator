#!/usr/bin/env python3
"""Create trades database schema"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def create_trades_schema():
    """Create the trades database schema"""
    
    # Read the schema file
    schema_path = os.path.join(os.path.dirname(__file__), 'schema_trades.sql')
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        # Execute schema creation
        cursor.execute(schema_sql)
        conn.commit()
        print("✅ Trades schema created successfully!")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('trades', 'positions', 'portfolio_history', 'trade_analysis')
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print(f"📊 Created tables: {[t[0] for t in tables]}")
        
        # Verify views were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public' 
            AND table_name IN ('active_trades_view', 'trade_performance_view')
            ORDER BY table_name
        """)
        
        views = cursor.fetchall()
        print(f"👁️  Created views: {[v[0] for v in views]}")
        
    except Exception as e:
        print(f"❌ Error creating schema: {str(e)}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_trades_schema()