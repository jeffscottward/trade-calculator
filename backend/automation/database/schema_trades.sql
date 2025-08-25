-- Trading System Database Schema
-- Stores real and backtest trades, positions, and performance metrics

-- Drop existing tables if they exist (for development)
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS portfolio_history CASCADE;
DROP TABLE IF EXISTS trade_analysis CASCADE;

-- Create main trades table for executed trades
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    trade_type VARCHAR(50) DEFAULT 'Calendar Spread',
    earnings_date DATE NOT NULL,
    entry_date TIMESTAMP NOT NULL,
    exit_date TIMESTAMP,
    
    -- Options legs details
    front_strike DECIMAL(10, 2) NOT NULL,
    front_expiry DATE NOT NULL,
    front_premium DECIMAL(10, 4) NOT NULL,
    front_contracts INTEGER NOT NULL,
    
    back_strike DECIMAL(10, 2) NOT NULL,
    back_expiry DATE NOT NULL,
    back_premium DECIMAL(10, 4) NOT NULL,
    back_contracts INTEGER NOT NULL,
    
    -- Trade economics
    net_debit DECIMAL(10, 4) NOT NULL,
    closing_credit DECIMAL(10, 4),
    position_size DECIMAL(12, 2) NOT NULL,
    position_size_pct DECIMAL(5, 2),
    
    -- Stock prices
    entry_stock_price DECIMAL(10, 2),
    exit_stock_price DECIMAL(10, 2),
    
    -- Volatility metrics
    entry_iv DECIMAL(10, 2),
    exit_iv DECIMAL(10, 2),
    iv_crush DECIMAL(10, 2),
    realized_volatility DECIMAL(10, 2),
    
    -- Movement metrics
    expected_move DECIMAL(10, 2),
    actual_move DECIMAL(10, 2),
    
    -- P&L
    front_pnl DECIMAL(12, 2),
    back_pnl DECIMAL(12, 2),
    total_pnl DECIMAL(12, 2),
    pnl_percent DECIMAL(10, 2),
    
    -- Status and metadata
    status VARCHAR(20) DEFAULT 'open', -- open, closed, cancelled
    recommendation VARCHAR(20), -- RECOMMENDED, CONSIDER, AVOID
    ib_order_id VARCHAR(50),
    source VARCHAR(20) DEFAULT 'live', -- live, backtest, paper
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create positions table for current holdings
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER REFERENCES trades(id),
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    
    -- Position details
    position_type VARCHAR(20), -- calendar_spread, long_call, short_call
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(10, 4) NOT NULL,
    current_price DECIMAL(10, 4),
    
    -- Greeks (for risk management)
    delta DECIMAL(10, 4),
    gamma DECIMAL(10, 4),
    theta DECIMAL(10, 4),
    vega DECIMAL(10, 4),
    
    -- P&L
    unrealized_pnl DECIMAL(12, 2),
    unrealized_pnl_percent DECIMAL(10, 2),
    
    -- Status
    status VARCHAR(20) DEFAULT 'open',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create portfolio history table for tracking account value over time
CREATE TABLE portfolio_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Account values
    total_value DECIMAL(12, 2) NOT NULL,
    cash_balance DECIMAL(12, 2) NOT NULL,
    positions_value DECIMAL(12, 2) NOT NULL,
    
    -- Daily metrics
    daily_pnl DECIMAL(12, 2),
    daily_pnl_percent DECIMAL(10, 2),
    
    -- Cumulative metrics
    cumulative_pnl DECIMAL(12, 2),
    cumulative_return_percent DECIMAL(10, 2),
    
    -- Risk metrics
    positions_count INTEGER DEFAULT 0,
    exposure_percent DECIMAL(10, 2),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(timestamp)
);

-- Create trade analysis table for storing analysis results
CREATE TABLE trade_analysis (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER REFERENCES trades(id),
    ticker VARCHAR(10) NOT NULL,
    analysis_date TIMESTAMP NOT NULL,
    
    -- Entry criteria scores
    volume_score DECIMAL(5, 2),
    iv_rv_ratio_score DECIMAL(5, 2),
    term_structure_score DECIMAL(5, 2),
    overall_score DECIMAL(5, 2),
    
    -- Analysis results
    recommendation VARCHAR(20),
    confidence_level DECIMAL(5, 2),
    reasons JSONB,
    
    -- Market conditions
    market_conditions JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_trades_ticker ON trades(ticker);
CREATE INDEX idx_trades_entry_date ON trades(entry_date);
CREATE INDEX idx_trades_exit_date ON trades(exit_date);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_source ON trades(source);
CREATE INDEX idx_trades_earnings_date ON trades(earnings_date);

CREATE INDEX idx_positions_ticker ON positions(ticker);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_trade_id ON positions(trade_id);

CREATE INDEX idx_portfolio_history_timestamp ON portfolio_history(timestamp);

CREATE INDEX idx_trade_analysis_ticker ON trade_analysis(ticker);
CREATE INDEX idx_trade_analysis_trade_id ON trade_analysis(trade_id);

-- Create function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_trades_updated_at 
    BEFORE UPDATE ON trades 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at 
    BEFORE UPDATE ON positions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create view for active trades with current P&L
CREATE VIEW active_trades_view AS
SELECT 
    t.id,
    t.ticker,
    t.company_name,
    t.trade_type,
    t.earnings_date,
    t.entry_date,
    t.front_strike,
    t.front_expiry,
    t.back_strike,
    t.back_expiry,
    t.net_debit,
    t.position_size,
    t.entry_stock_price,
    t.expected_move,
    p.current_price,
    p.unrealized_pnl,
    p.unrealized_pnl_percent,
    t.status,
    t.recommendation,
    (t.earnings_date - CURRENT_DATE) AS days_to_earnings
FROM trades t
LEFT JOIN positions p ON t.id = p.trade_id
WHERE t.status = 'open'
ORDER BY t.earnings_date;

-- Create view for trade performance metrics
CREATE VIEW trade_performance_view AS
SELECT 
    COUNT(*) AS total_trades,
    COUNT(CASE WHEN status = 'closed' THEN 1 END) AS closed_trades,
    COUNT(CASE WHEN status = 'open' THEN 1 END) AS open_trades,
    COUNT(CASE WHEN total_pnl > 0 AND status = 'closed' THEN 1 END) AS winning_trades,
    COUNT(CASE WHEN total_pnl <= 0 AND status = 'closed' THEN 1 END) AS losing_trades,
    CASE 
        WHEN COUNT(CASE WHEN status = 'closed' THEN 1 END) > 0 
        THEN (COUNT(CASE WHEN total_pnl > 0 AND status = 'closed' THEN 1 END)::DECIMAL / 
              COUNT(CASE WHEN status = 'closed' THEN 1 END)::DECIMAL) * 100
        ELSE 0 
    END AS win_rate,
    AVG(CASE WHEN total_pnl > 0 AND status = 'closed' THEN total_pnl END) AS avg_win,
    AVG(CASE WHEN total_pnl <= 0 AND status = 'closed' THEN total_pnl END) AS avg_loss,
    SUM(CASE WHEN status = 'closed' THEN total_pnl ELSE 0 END) AS total_realized_pnl,
    SUM(CASE WHEN status = 'open' THEN 
        (SELECT unrealized_pnl FROM positions WHERE trade_id = trades.id LIMIT 1) 
        ELSE 0 END) AS total_unrealized_pnl,
    AVG(pnl_percent) FILTER (WHERE status = 'closed') AS avg_return_percent,
    STDDEV(pnl_percent) FILTER (WHERE status = 'closed') AS return_std_dev
FROM trades;

-- Sample queries
-- Get current open positions:
-- SELECT * FROM active_trades_view;

-- Get overall performance:
-- SELECT * FROM trade_performance_view;

-- Get portfolio value history:
-- SELECT * FROM portfolio_history ORDER BY timestamp DESC LIMIT 30;