# Automated Earnings Volatility Trading System Design

## Executive Summary

This document outlines the design for an automated trading system that implements the earnings volatility selling strategy described in the research. The system will automatically identify qualifying earnings events, calculate position sizes, and execute calendar spread trades through Interactive Brokers.

**Current Implementation Status**: Web interface operational with earnings calendar, real-time data fetching, and analysis capabilities. Database integration complete for earnings data storage.

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

### Frontend: Next.js with TypeScript

**Status: ✅ Implemented**

- React-based UI with t-stack-base foundation
- Interactive earnings calendar with month navigation
- Real-time earnings data table with search/filter
- Trade analysis modal for displaying recommendations
- Responsive design with Tailwind CSS

### Backend: FastAPI (Python)

**Status: ✅ Implemented**

- RESTful API endpoints for earnings data
- Integration with multiple data sources
- Trade analysis endpoint (mock implementation ready for calculator.py integration)
- CORS configured for frontend communication

### Broker: Interactive Brokers

**Status: 🔄 In Progress**

- Client Portal Gateway configured on port 5001
- Paper trading setup for testing
- **Rationale:**
  - Most mature and stable API for automated trading
  - Best pricing for active options traders ($0.15-$0.65 per contract)
  - Native Python API support with generous rate limits
  - Professional-grade execution and international market access

### Data Sources

#### Primary: NASDAQ via finance_calendars

**Status: ✅ Implemented**

- Free access to all US stocks earnings data
- Bulk data import capability
- No API key required
- Real-time updates available

#### Secondary: NASDAQ API

**Status: ✅ Implemented**

- **Free**: No API key required
- **Features**: US stocks earnings calendar
- **Format**: JSON output
- Filters out OTC/foreign stocks automatically

#### Market Data: Yahoo Finance (yfinance)

**Status: ✅ Configured**

- Real-time stock prices
- Options chains with Greeks
- Historical price data for volatility calculations
- Implied volatility for all strikes/expirations

## System Architecture

### Current Implementation

```
┌─────────────────────────────────────────────┐
│         Next.js Frontend (Port 3001)        │
│   - Earnings Calendar Component ✅           │
│   - Earnings Data Table ✅                   │
│   - Trade Analysis Modal ✅                  │
│   - Real-time Updates (WebSocket pending)   │
└────────────┬────────────────────────────────┘
             │ HTTP/REST
             ▼
┌─────────────────────────────────────────────┐
│      FastAPI Backend (Port 8000) ✅         │
│   - /api/earnings/{date}                    │
│   - /api/earnings/calendar/month            │
│   - /api/analyze/{ticker}                   │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│        Data Layer (Hybrid Approach)         │
│   ┌────────────────┐  ┌──────────────────┐ │
│   │  PostgreSQL DB │  │  External APIs   │ │
│   │  (Primary) ✅   │  │  (Fallback) ✅    │ │
│   │                │  │                  │ │
│   │  - Earnings    │  │  - NASDAQ API    │ │
│   │    Calendar    │  │  - Yahoo Finance │ │
│   │  - Import      │  │  - NASDAQ Direct │ │
│   │    History     │  │                  │ │
│   └────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│    Automated Data Import (Cron) ✅          │
│   - Daily NASDAQ earnings fetch             │
│   - Database population                     │
│   - Import history tracking                 │
└─────────────────────────────────────────────┘
```

### Planned Broker Integration

```
┌─────────────────────────────────────────────┐
│      Interactive Brokers Integration 🔄     │
│   - IB Client Portal (Port 5001) ✅          │
│   - Order Placement API (Pending)           │
│   - Position Management (Pending)           │
│   - Real-time Market Data (Pending)         │
└─────────────────────────────────────────────┘
```

## Database Schema

### Implemented Tables

#### earnings_calendar ✅

```sql
CREATE TABLE earnings_calendar (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    report_date DATE NOT NULL,
    report_time VARCHAR(50), -- 'BMO', 'AMC', 'TBD'
    market_cap VARCHAR(50),
    market_cap_numeric BIGINT,
    fiscal_quarter_ending VARCHAR(20),
    eps_forecast VARCHAR(20),
    eps_forecast_numeric DECIMAL(10, 2),
    num_estimates INTEGER,
    last_year_report_date DATE,
    last_year_eps VARCHAR(20),
    last_year_eps_numeric DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, report_date)
);
```

#### earnings_import_history ✅

```sql
CREATE TABLE earnings_import_history (
    id SERIAL PRIMARY KEY,
    import_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    records_imported INTEGER NOT NULL,
    source VARCHAR(50) DEFAULT 'NASDAQ',
    status VARCHAR(20) DEFAULT 'completed',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Pending Tables (From Original Design)

#### trades

```sql
-- To be implemented when broker integration complete
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    earnings_event_id INTEGER REFERENCES earnings_events(id),
    trade_type VARCHAR(20) NOT NULL,
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
```

## Implementation Status

### ✅ Completed Components

1. **Frontend Foundation**
   - Next.js application with TypeScript
   - Earnings calendar with date selection
   - Earnings data table with search/filter
   - Trade analysis modal
   - Responsive design

2. **Backend API**
   - FastAPI server on port 8000
   - Earnings data endpoints
   - Trade analysis endpoint (mock)
   - CORS configuration

3. **Data Pipeline**
   - NASDAQ earnings data fetching via finance_calendars
   - Bulk import script (earnings_data_importer.py)
   - Database schema for earnings storage
   - Automated update mechanism (cron script)

4. **Database Integration**
   - PostgreSQL schema created
   - Earnings calendar table
   - Import history tracking
   - Fallback to API when DB unavailable

### 🔄 In Progress

1. **Trade Analysis Engine**
   - Integration with calculator.py
   - Real volatility calculations
   - Term structure analysis
   - Position sizing logic

2. **Interactive Brokers Integration**
   - Client Portal Gateway setup (port 5001)
   - Order placement implementation
   - Position monitoring

### 📋 Pending Implementation

1. **Real-time Updates**
   - WebSocket implementation
   - Live earnings notifications
   - Trade status updates

2. **Risk Management**
   - Portfolio exposure limits
   - Stop-loss mechanisms
   - Drawdown monitoring
   - Manual override capabilities

3. **Performance Tracking**
   - Trade history logging
   - P&L calculations
   - Win rate tracking
   - Sharpe ratio computation

4. **Automation**
   - Entry order automation (3:45 PM)
   - Exit order automation (9:45 AM)
   - Daily performance reports

## Configuration Files

### Current Implementation

#### .env (Required Variables)

```bash
# Database
DATABASE_URL=postgresql://user:pass@host/db

# Data Sources
# NASDAQ API - No key required

# Interactive Brokers (Future)
IB_ACCOUNT=DU1234567
IB_HOST=127.0.0.1
IB_PORT=5001
```

#### automation/config.py

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# API Configuration
# NASDAQ API doesn't require API key

# Strategy Parameters
STRATEGY_CONFIG = {
    'position_size_pct': 0.06,
    'max_concurrent_positions': 3,
    'term_structure_threshold': -0.1,
    'volume_threshold': 1000000,
    'iv_rv_threshold': 1.2
}

# Risk Limits
RISK_CONFIG = {
    'max_daily_loss_pct': 0.10,
    'max_consecutive_losses': 3,
    'max_portfolio_exposure': 0.20,
    'min_stock_price': 20.0
}
```

## Cron Job Configuration

### Implemented

```bash
# Daily earnings data update - 6:00 AM ET
0 6 * * * /path/to/scripts/update_earnings_data.sh

# Weekly full refresh - Sunday 2:00 AM ET
0 2 * * 0 /path/to/venv/bin/python /path/to/automation/earnings_data_importer.py --days 60
```

### Planned

```bash
# Daily trade scanner - 3:00 PM ET (1 hour before close)
0 15 * * 1-5 /usr/bin/python3 /path/to/earnings_scanner.py

# Morning exit handler - 9:45 AM ET (15 minutes after open)
45 9 * * 1-5 /usr/bin/python3 /path/to/exit_handler.py

# Performance report - Daily at 6:00 PM ET
0 18 * * 1-5 /usr/bin/python3 /path/to/performance_report.py
```

## Testing Strategy

### Current Testing

1. **Frontend**: Manual testing with mock data removed, using real API data
2. **API**: Testing with curl/Postman
3. **Data Import**: Successfully importing NASDAQ earnings data

### Planned Testing

1. **Backtesting**: Historical simulation on 2023-2024 data
2. **Paper Trading**: 30-day trial with IB paper account
3. **Limited Live**: Start with 1% position sizes
4. **Full Production**: Scale to 6% after 20 successful trades

## Next Development Priorities

1. **Complete Trade Analysis Integration**
   - Connect calculator.py logic to API
   - Implement real volatility calculations
   - Add term structure analysis

2. **Interactive Brokers Connection**
   - Complete Client Portal API integration
   - Implement order placement
   - Add position monitoring

3. **Automate Trade Execution**
   - Entry order scheduling
   - Exit order automation
   - Error handling and retries

4. **Add Performance Tracking**
   - Trade logging to database
   - Real-time P&L updates
   - Performance metrics dashboard

## Architecture Decisions

### Why Database-First for Earnings Data

- Eliminates API rate limiting issues
- Provides sub-50ms response times
- Ensures data availability offline
- Allows historical data preservation
- Reduces external dependencies

### Why FastAPI over Next.js API Routes

- Better Python ecosystem integration
- Direct access to trading libraries (yfinance, ib_insync)
- Cleaner separation of concerns
- Easier to scale independently
- Avoids confusion between two API servers

### Why NASDAQ via finance_calendars

- Free access to all US stocks
- No API key required
- Bulk download capability
- More comprehensive than other free alternatives

## Monitoring & Alerts

### Implemented

- Import history tracking in database
- API fallback monitoring
- Console logging for debugging

### Planned

- Failed trade execution alerts
- Position size limit warnings
- Unusual market condition detection
- System error notifications

## Future Enhancements

- Machine learning for trade selection
- Multiple strategy variations
- Additional broker support
- Advanced charting capabilities
- Mobile application
- Automated parameter optimization

---

*Last Updated: January 2025*
*Status: Active Development - Web Interface Operational*
