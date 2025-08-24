-- Earnings Calendar Database Schema
-- Stores earnings data fetched from NASDAQ

-- Drop existing tables if they exist (for development)
DROP TABLE IF EXISTS earnings_calendar CASCADE;

-- Create main earnings calendar table
CREATE TABLE earnings_calendar (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    report_date DATE NOT NULL,
    report_time VARCHAR(50), -- 'time-pre-market', 'time-after-hours', 'time-not-supplied'
    market_cap VARCHAR(50), -- Store as string since it comes formatted
    market_cap_numeric BIGINT, -- Parsed numeric value for queries
    fiscal_quarter_ending VARCHAR(20),
    eps_forecast VARCHAR(20),
    eps_forecast_numeric DECIMAL(10, 2), -- Parsed numeric value
    num_estimates INTEGER,
    last_year_report_date DATE,
    last_year_eps VARCHAR(20),
    last_year_eps_numeric DECIMAL(10, 2), -- Parsed numeric value
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Add indexes for common queries
    UNIQUE(ticker, report_date)
);

-- Create indexes for performance
CREATE INDEX idx_earnings_calendar_report_date ON earnings_calendar(report_date);
CREATE INDEX idx_earnings_calendar_ticker ON earnings_calendar(ticker);
CREATE INDEX idx_earnings_calendar_report_time ON earnings_calendar(report_time);
CREATE INDEX idx_earnings_calendar_market_cap ON earnings_calendar(market_cap_numeric);
CREATE INDEX idx_earnings_calendar_report_date_time ON earnings_calendar(report_date, report_time);

-- Create function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_earnings_calendar_updated_at 
    BEFORE UPDATE ON earnings_calendar 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create view for easier querying with parsed values
CREATE VIEW earnings_calendar_view AS
SELECT 
    id,
    ticker,
    company_name,
    report_date,
    CASE 
        WHEN report_time = 'time-pre-market' THEN 'BMO'
        WHEN report_time = 'time-after-hours' THEN 'AMC'
        WHEN report_time = 'time-not-supplied' THEN 'TBD'
        ELSE 'TBD'
    END as report_time_formatted,
    report_time as report_time_raw,
    market_cap,
    market_cap_numeric,
    fiscal_quarter_ending,
    eps_forecast,
    eps_forecast_numeric,
    num_estimates,
    last_year_report_date,
    last_year_eps,
    last_year_eps_numeric,
    -- Calculate expected move (placeholder - would need options data)
    CASE 
        WHEN last_year_eps_numeric IS NOT NULL AND eps_forecast_numeric IS NOT NULL 
        THEN ABS((eps_forecast_numeric - last_year_eps_numeric) / NULLIF(last_year_eps_numeric, 0)) * 100
        ELSE NULL
    END as eps_growth_pct,
    created_at,
    updated_at
FROM earnings_calendar;

-- Sample query to get earnings for a specific date
-- SELECT * FROM earnings_calendar_view 
-- WHERE report_date = '2025-01-22' 
-- ORDER BY market_cap_numeric DESC;