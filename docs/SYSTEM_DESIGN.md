# Automated Earnings Volatility Trading System Design

## Executive Summary

This document outlines the design for an automated trading system that implements the earnings volatility selling strategy described in the research. The system will automatically identify qualifying earnings events, calculate position sizes, and execute calendar spread trades through Interactive Brokers.

## Strategy Overview

### Core Strategy
- **Primary Structure**: Long calendar spreads (sell front month, buy back month)
- **Alternative Structure**: Short straddles (higher returns, higher risk)
- **Entry Timing**: 15 minutes before market close on day before earnings
- **Exit Timing**: 15 minutes after market open on day after earnings
- **Position Sizing**: 6% of portfolio per trade (10% Kelly criterion)

### Trade Qualification Criteria
1. **Term Structure Slope**: Negative slope between front month and 45+ day expiration
2. **30-Day Average Volume**: Above minimum threshold for liquidity
3. **IV/RV Ratio**: Implied volatility overpriced relative to realized volatility

## Technology Stack

### Broker: Interactive Brokers
**Rationale:**
- Most mature and stable API for automated trading
- Best pricing for active options traders ($0.15-$0.65 per contract)
- Native Python API support with generous rate limits
- Professional-grade execution and international market access
- Used in original research for commission calculations

**Alternatives Considered:**
- ~~TD Ameritrade~~: Discontinued May 2024, migrated to Schwab
- ~~Charles Schwab~~: New API with 7-day token expiration, manual approval process
- ~~Robinhood~~: Limited API access, not suitable for professional trading

### Data Sources

#### Earnings Calendar: Alpha Vantage
- **Free Tier**: 500 API calls/day
- **Features**: 3/6/12 month earnings horizons
- **Format**: CSV output
- **Official NASDAQ vendor**

#### Market Data: Yahoo Finance (yfinance)
- Real-time stock prices
- Options chains with Greeks
- Historical price data for volatility calculations
- Implied volatility for all strikes/expirations

#### Backup Data: Interactive Brokers API
- Real-time market data through TWS
- Options chains and Greeks
- Can serve as fallback if Yahoo Finance rate limits

## System Architecture

```
┌─────────────────────────────────────────────┐
│           Cron Job Scheduler                │
│         (Daily at 3:00 PM ET)               │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│       Earnings Scanner Module               │
│   - Fetch tomorrow's earnings (Alpha Vantage)│
│   - Filter for liquid stocks                │
│   - Calculate predictor variables           │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│        Trade Qualification Engine           │
│   - Check term structure slope              │
│   - Verify volume requirements              │
│   - Calculate IV/RV ratio                   │
│   - Generate trade recommendations          │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│         Position Sizing Module              │
│   - Apply Kelly criterion (6% per trade)    │
│   - Check portfolio constraints             │
│   - Calculate exact contract quantities     │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│      Interactive Brokers Execution          │
│   - Connect via IB Gateway/TWS              │
│   - Place calendar spread orders            │
│   - Set exit orders for next morning        │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│         Monitoring & Logging                │
│   - Track order status                      │
│   - Log trades to database                  │
│   - Send alerts on errors                   │
│   - Calculate P&L and statistics            │
└─────────────────────────────────────────────┘
```

## Implementation Phases

*Note: With AI-powered development, these phases can be implemented rapidly in parallel rather than sequentially over weeks.*

### Phase 1: Data Pipeline
- [ ] Set up Alpha Vantage API for earnings calendar
- [ ] Implement earnings scanner with filtering
- [ ] Create volatility calculation functions (Yang-Zhang)
- [ ] Build term structure analysis module

### Phase 2: Trade Logic
- [ ] Implement trade qualification engine
- [ ] Add position sizing calculations
- [ ] Create trade recommendation system
- [ ] Build paper trading simulator for testing

### Phase 3: Broker Integration
- [ ] Set up Interactive Brokers API connection
- [ ] Implement order placement for calendar spreads
- [ ] Add order monitoring and status tracking
- [ ] Create exit order automation

### Phase 4: Automation & Monitoring
- [ ] Set up cron job for daily scanning
- [ ] Connect to Neon DB for trade logging
- [ ] Add email/SMS alerting system
- [ ] Create performance tracking dashboard

### Phase 5: Risk Management
- [ ] Add portfolio exposure limits
- [ ] Implement stop-loss mechanisms
- [ ] Create drawdown monitoring
- [ ] Add manual override capabilities

## Database Configuration

### Neon DB (PostgreSQL)

We're using Neon DB, a serverless PostgreSQL database, for persistent storage of trades and performance metrics.

**Connection Details:**
```python
# Store in .env file (NEVER commit to git)
DATABASE_URL = os.getenv('DATABASE_URL')
```

**Key Benefits:**
- Serverless PostgreSQL with auto-scaling
- Built-in connection pooling
- Automatic backups and point-in-time recovery
- Zero cold starts for cron job executions

## Database Schema

```sql
-- PostgreSQL schema for Neon DB

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

-- Index for faster queries
CREATE INDEX idx_earnings_date ON earnings_events(earnings_date);
CREATE INDEX idx_symbol ON earnings_events(symbol);

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

-- Index for performance queries
CREATE INDEX idx_trade_status ON trades(status);
CREATE INDEX idx_trade_symbol ON trades(symbol);

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

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_earnings_events_updated_at BEFORE UPDATE ON earnings_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_performance_metrics_updated_at BEFORE UPDATE ON performance_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Cron Job Configuration

```bash
# Daily earnings scanner - 3:00 PM ET (1 hour before market close)
0 15 * * 1-5 /usr/bin/python3 /path/to/earnings_scanner.py

# Morning exit handler - 9:45 AM ET (15 minutes after open)
45 9 * * 1-5 /usr/bin/python3 /path/to/exit_handler.py

# Performance report - Daily at 6:00 PM ET
0 18 * * 1-5 /usr/bin/python3 /path/to/performance_report.py
```

## Risk Management Rules

1. **Position Limits**
   - Maximum 6% of portfolio per trade
   - Maximum 3 concurrent positions
   - No more than 20% total portfolio exposure

2. **Trade Filters**
   - Minimum stock price: $20
   - Minimum average volume: 1M shares/day
   - Minimum options volume: 100 contracts/day

3. **Emergency Stops**
   - Halt trading if daily loss exceeds 10%
   - Pause system if 3 consecutive losses
   - Manual review required after any loss >15%

## Configuration File

```python
# config.py
import os
from urllib.parse import urlparse

# Neon DB Configuration - Load from environment variable
DATABASE_URL = os.getenv('DATABASE_URL')  # Must be set in .env file
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Parse database URL for connection pooling
db_url = urlparse(DATABASE_URL)
DATABASE_CONFIG = {
    'host': db_url.hostname,
    'port': db_url.port or 5432,
    'database': db_url.path[1:],
    'user': db_url.username,
    'password': db_url.password,
    'sslmode': 'require',
    'connect_timeout': 10
}

BROKER_CONFIG = {
    'provider': 'interactive_brokers',
    'host': '127.0.0.1',
    'port': 7497,  # TWS Paper Trading
    'client_id': 1,
    'account': 'DU1234567'  # Paper account for testing
}

DATA_CONFIG = {
    'alpha_vantage_key': os.getenv('ALPHA_VANTAGE_KEY', 'YOUR_API_KEY'),
    'earnings_horizon': '3month',
    'yfinance_cache': True
}

STRATEGY_CONFIG = {
    'position_size_pct': 0.06,  # 6% per trade
    'max_concurrent_positions': 3,
    'term_structure_threshold': -0.1,
    'volume_threshold': 1000000,
    'iv_rv_threshold': 1.2
}

RISK_CONFIG = {
    'max_daily_loss_pct': 0.10,
    'max_consecutive_losses': 3,
    'max_portfolio_exposure': 0.20,
    'min_stock_price': 20.0
}
```

## Monitoring & Alerts

### Key Metrics to Track
- Win rate (target: 66%)
- Average return per trade (target: 7.3%)
- Maximum drawdown (alert if >20%)
- Sharpe ratio (target: >3.0)

### Alert Conditions
- Failed trade execution
- Position size exceeds limits
- Unusual market conditions
- System errors or disconnections

## Testing Strategy

1. **Backtesting**: Run historical simulation on 2023-2024 data
2. **Paper Trading**: 30-day trial with IB paper account
3. **Limited Live**: Start with 1% position sizes
4. **Full Production**: Scale to 6% after 20 successful trades

## Future Enhancements

- Add machine learning for improved trade selection
- Implement multiple strategy variations
- Add support for additional brokers
- Create web-based monitoring dashboard
- Implement automated parameter optimization