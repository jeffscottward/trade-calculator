# Python Code Organization Overview

## Project Structure Summary

The Python codebase is organized into several key directories and modules:

```
.
├── backend/
│   ├── api/                    # FastAPI backend server
│   │   └── setup_cron.sh      # API data fetching cron setup
│   └── automation/             # Core trading bot logic
│       └── setup_cron.sh      # Trading bot cron setup
└── scripts/                # Utility and debug scripts
    ├── setup_cron.sh          # Master cron setup selector
    └── start-dev.sh           # Development startup script
```

## 1. API Directory (`/api`)
**Purpose**: FastAPI backend server for the web frontend

### Core Files:
- **`main.py`** - FastAPI server with earnings calendar endpoints
  - Serves earnings data to Next.js frontend
  - Handles CORS for localhost:3000/3001
  - Provides SSE streaming for progress updates
  - Caches NASDAQ API responses (5-minute cache)

### Data Fetching:
- **`nasdaq_earnings.py`** - NASDAQ earnings calendar API integration
- **`analysis_engine.py`** - Options analysis and volatility calculations
- **`database_operations.py`** - PostgreSQL/Neon DB operations

### Scheduled Jobs:
- **`cron_daily_fetch.py`** - Daily earnings data fetch (9 AM ET)
- **`cron_pretrade_fetch.py`** - Pre-trade data refresh (3:50 PM ET)
- **`fetch_august_data.py`** - Historical data importer
- **`setup_cron.sh`** - API data fetching cron configuration

## 2. Automation Directory (`/automation`)
**Purpose**: Core automated trading system

### Main Components:
- **`main.py`** - System orchestrator that coordinates all components
- **`config.py`** - Central configuration (loads from .env)
- **`earnings_scanner.py`** - Scans for qualifying earnings events
  - Entry criteria: negative term structure, volume > 1M, IV/RV > 1.2
- **`trade_executor.py`** - Interactive Brokers order execution
- **`position_manager.py`** - Entry/exit timing automation
  - Entry: 15 min before close (3:45 PM ET)
  - Exit: 15 min after open (9:45 AM ET)
- **`risk_monitor.py`** - Portfolio limits and drawdown protection
  - Max 3 concurrent positions
  - 20% max exposure
  - Daily loss limits

### IB Integration:
- **`ib_api_client.py`** - Client Portal REST API wrapper
  - Authentication handling
  - Calendar spread order structure
  - Contract search and validation
- **`earnings_data_importer.py`** - Bulk data import utilities

### Test Scripts:
- **`test_ib_simple.py`** - Basic connectivity test
- **`test_ib_connection.py`** - Authentication verification  
- **`test_ib_api_full.py`** - Comprehensive API test suite
- **`test_trade_flow.py`** - Complete trading workflow test
- **`test_real_paper_trade.py`** - Live paper trading test

### Sub-modules:
- **`database/`** - Database management
  - `db_manager.py` - PostgreSQL operations
  - `init_db.py` - Schema initialization
- **`utils/`** - Utility functions
  - `volatility.py` - Yang-Zhang volatility calculations
  - `options_analysis.py` - Term structure and pricing
  - `notifications.py` - Email/Discord alerts

## 3. Scripts Directory (`/scripts`)
**Purpose**: Development and debugging utilities

- **`test_yfinance.py`** - Yahoo Finance API testing
- **`test_finance_calendars.py`** - Calendar data testing
- **`create_schema.py`** - Database schema creation
- **`update_earnings_data.sh`** - Data update utility

## 4. Root Level Files

### Development Scripts:
- **`scripts/start-dev.sh`** - Unified startup script
  - Starts FastAPI backend (port 3000)
  - Starts Next.js frontend (port 3001)
  - Starts IB Client Portal (port 5001)
  - Handles all services in one command

- **`scripts/setup_cron.sh`** - Master cron setup selector (choose which jobs to install)
- **`backend/automation/setup_cron.sh`** - Trading bot cron setup
  - Daily scan at 3:00 PM ET
  - Enter positions at 3:45 PM ET
  - Exit positions at 9:45 AM ET
  - Performance reports at 6:00 PM ET
- **`backend/api/setup_cron.sh`** - API data cron setup
  - Daily earnings fetch at 9:00 AM ET
  - Pre-trade refresh at 3:50 PM ET

## Recommended Cleanup Actions

### 1. ~~Consolidate Duplicates~~ ✅ RESOLVED
- Moved cron setup scripts to their respective folders
- Both are now named `setup_cron.sh` in their own directories
- Created master `setup_cron.sh` selector script in scripts folder

### 2. Organize Test Scripts
- Move all test files to a dedicated `tests/` directory:
  ```
  tests/
  ├── ib/
  │   ├── test_simple.py
  │   ├── test_connection.py
  │   ├── test_api_full.py
  │   ├── test_trade_flow.py
  │   └── test_real_paper_trade.py
  └── utils/
      ├── test_yfinance.py
      └── test_finance_calendars.py
  ```

### 3. Separate Concerns
- `api/` should only contain FastAPI-related code
- Move `analysis_engine.py` to `automation/utils/` since it's shared
- Consider moving database operations to `automation/database/`

### 4. ~~Environment Management~~ ✅ RESOLVED
- Removed venv from root
- Backend has its own venv (gitignored)

### 5. Documentation
- Each major directory should have its own README.md
- Consider adding docstrings to all main classes/functions

## Data Flow

1. **Daily Scan (3:00 PM ET)**:
   - `backend/automation/main.py` → `earnings_scanner.py` → Qualifies trades

2. **Trade Entry (3:45 PM ET)**:
   - `backend/automation/position_manager.py` → `trade_executor.py` → IB API

3. **Trade Exit (9:45 AM ET)**:
   - `backend/automation/position_manager.py` → Closes positions via IB API

4. **Web Interface**:
   - Next.js frontend → FastAPI (`backend/api/main.py`) → Database/NASDAQ API

## Key Configuration Files

- `.env` - API keys and credentials (at project root)
- `backend/automation/config.py` - Trading parameters and limits
- Database schema in `backend/automation/database/init_db.py`

## Current Status

✅ **Working**:
- FastAPI backend serving earnings data
- IB Client Portal authentication
- Database connectivity
- Frontend UI
- All IB API tests passing

🔧 **Needs Attention**:
- Consolidate duplicate cron scripts
- Remove venv from repository
- Organize test files
- Add comprehensive error handling
- Document API endpoints