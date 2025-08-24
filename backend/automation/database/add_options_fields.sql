-- Add options-specific fields to trades table for calendar spreads
ALTER TABLE trades 
ADD COLUMN IF NOT EXISTS company_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS front_strike NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS front_expiry DATE,
ADD COLUMN IF NOT EXISTS front_premium NUMERIC(10,4),
ADD COLUMN IF NOT EXISTS front_contracts INTEGER,
ADD COLUMN IF NOT EXISTS back_strike NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS back_expiry DATE,
ADD COLUMN IF NOT EXISTS back_premium NUMERIC(10,4),
ADD COLUMN IF NOT EXISTS back_contracts INTEGER,
ADD COLUMN IF NOT EXISTS net_debit NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS iv_crush NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS expected_move NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS actual_move NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS position_size VARCHAR(10),
ADD COLUMN IF NOT EXISTS recommendation VARCHAR(20),
ADD COLUMN IF NOT EXISTS current_price NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS unrealized_pnl NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS expected_exit_date DATE,
ADD COLUMN IF NOT EXISTS portfolio_value NUMERIC(12,2);

-- Portfolio history table for tracking value over time
CREATE TABLE IF NOT EXISTS portfolio_history (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_value NUMERIC(12,2) NOT NULL,
    cash_balance NUMERIC(12,2),
    positions_value NUMERIC(12,2),
    daily_pnl NUMERIC(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date)
);

-- Index for faster date lookups
CREATE INDEX IF NOT EXISTS idx_portfolio_history_date ON portfolio_history(date);