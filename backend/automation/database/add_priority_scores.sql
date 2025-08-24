-- Add priority scoring columns to earnings_events table
-- This enables sophisticated ranking of trade opportunities

ALTER TABLE earnings_events 
ADD COLUMN IF NOT EXISTS priority_score DECIMAL(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS iv_rv_score DECIMAL(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS term_slope_score DECIMAL(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS liquidity_score DECIMAL(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS market_cap_score DECIMAL(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS market_cap_numeric BIGINT DEFAULT 0;

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_earnings_events_priority 
ON earnings_events(scan_date DESC, priority_score DESC);

-- Add comments explaining the scoring system
COMMENT ON COLUMN earnings_events.priority_score IS 'Overall priority score (0-100) for ranking trade opportunities';
COMMENT ON COLUMN earnings_events.iv_rv_score IS 'IV/RV ratio component score (40% weight)';
COMMENT ON COLUMN earnings_events.term_slope_score IS 'Term structure slope component score (30% weight)';
COMMENT ON COLUMN earnings_events.liquidity_score IS 'Liquidity/volume component score (20% weight)';
COMMENT ON COLUMN earnings_events.market_cap_score IS 'Market cap component score (10% weight)';
COMMENT ON COLUMN earnings_events.market_cap_numeric IS 'Numeric market cap value for calculations';