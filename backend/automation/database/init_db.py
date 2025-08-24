"""
Initialize the database schema for the automated trading system.
Run this script to create all necessary tables in Neon DB.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from automation.database.db_manager import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PostgreSQL schema creation SQL
SCHEMA_SQL = """
-- Earnings events table
CREATE TABLE IF NOT EXISTS earnings_events (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    earnings_date DATE NOT NULL,
    scan_date TIMESTAMP WITH TIME ZONE NOT NULL,
    term_structure_slope NUMERIC(10,4),
    avg_volume_30d BIGINT,
    iv_rv_ratio NUMERIC(10,4),
    recommendation VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings_events(earnings_date);
CREATE INDEX IF NOT EXISTS idx_symbol ON earnings_events(symbol);

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    earnings_event_id INTEGER REFERENCES earnings_events(id),
    trade_type VARCHAR(20) NOT NULL, -- 'calendar' or 'straddle'
    entry_time TIMESTAMP WITH TIME ZONE,
    exit_time TIMESTAMP WITH TIME ZONE,
    entry_price NUMERIC(10,2),
    exit_price NUMERIC(10,2),
    contracts INTEGER NOT NULL,
    pnl NUMERIC(10,2),
    status VARCHAR(20) NOT NULL,
    ib_order_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance queries
CREATE INDEX IF NOT EXISTS idx_trade_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trade_symbol ON trades(symbol);

-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    total_pnl NUMERIC(12,2),
    max_drawdown NUMERIC(10,2),
    sharpe_ratio NUMERIC(6,3),
    win_rate NUMERIC(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_earnings_events_updated_at ON earnings_events;
CREATE TRIGGER update_earnings_events_updated_at 
    BEFORE UPDATE ON earnings_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_trades_updated_at ON trades;
CREATE TRIGGER update_trades_updated_at 
    BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_performance_metrics_updated_at ON performance_metrics;
CREATE TRIGGER update_performance_metrics_updated_at 
    BEFORE UPDATE ON performance_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""


def init_database():
    """Initialize the database with required schema."""
    try:
        db = DatabaseManager()
        
        # Execute schema creation
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(SCHEMA_SQL)
                conn.commit()
        
        logger.info("Database schema initialized successfully")
        
        # Verify tables were created
        verification_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('earnings_events', 'trades', 'performance_metrics')
        """
        
        tables = db.execute_query(verification_query)
        logger.info(f"Created tables: {[t['table_name'] for t in tables]}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


if __name__ == "__main__":
    success = init_database()
    if success:
        print("✅ Database initialized successfully")
    else:
        print("❌ Failed to initialize database. Check logs for details.")
        sys.exit(1)