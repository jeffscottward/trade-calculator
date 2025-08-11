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

### Phase 1: Data Pipeline (Week 1-2)
- [ ] Set up Alpha Vantage API for earnings calendar
- [ ] Implement earnings scanner with filtering
- [ ] Create volatility calculation functions (Yang-Zhang)
- [ ] Build term structure analysis module

### Phase 2: Trade Logic (Week 2-3)
- [ ] Implement trade qualification engine
- [ ] Add position sizing calculations
- [ ] Create trade recommendation system
- [ ] Build paper trading simulator for testing

### Phase 3: Broker Integration (Week 3-4)
- [ ] Set up Interactive Brokers API connection
- [ ] Implement order placement for calendar spreads
- [ ] Add order monitoring and status tracking
- [ ] Create exit order automation

### Phase 4: Automation & Monitoring (Week 4-5)
- [ ] Set up cron job for daily scanning
- [ ] Implement database for trade logging
- [ ] Add email/SMS alerting system
- [ ] Create performance tracking dashboard

### Phase 5: Risk Management (Week 5-6)
- [ ] Add portfolio exposure limits
- [ ] Implement stop-loss mechanisms
- [ ] Create drawdown monitoring
- [ ] Add manual override capabilities

## Database Schema

```sql
-- Earnings events table
CREATE TABLE earnings_events (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(10),
    earnings_date DATE,
    scan_date TIMESTAMP,
    term_structure_slope FLOAT,
    avg_volume_30d INTEGER,
    iv_rv_ratio FLOAT,
    recommendation VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trades table
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(10),
    earnings_event_id INTEGER,
    trade_type VARCHAR(20), -- 'calendar' or 'straddle'
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    entry_price DECIMAL(10,2),
    exit_price DECIMAL(10,2),
    contracts INTEGER,
    pnl DECIMAL(10,2),
    status VARCHAR(20),
    ib_order_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (earnings_event_id) REFERENCES earnings_events(id)
);

-- Performance metrics table
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY,
    date DATE,
    total_trades INTEGER,
    winning_trades INTEGER,
    total_pnl DECIMAL(10,2),
    max_drawdown DECIMAL(10,2),
    sharpe_ratio FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
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
BROKER_CONFIG = {
    'provider': 'interactive_brokers',
    'host': '127.0.0.1',
    'port': 7497,  # TWS Paper Trading
    'client_id': 1,
    'account': 'DU1234567'  # Paper account for testing
}

DATA_CONFIG = {
    'alpha_vantage_key': 'YOUR_API_KEY',
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