# Backend - Automated Trading System

This directory contains all Python backend code for the automated earnings volatility trading system.

## Directory Structure

```
backend/
├── api/                    # FastAPI server for web frontend
│   ├── main.py            # FastAPI application
│   ├── nasdaq_earnings.py # NASDAQ API integration
│   ├── analysis_engine.py # Options analysis logic
│   ├── cron_*.py          # Scheduled data fetching
│   └── setup_cron.sh      # API cron job setup
│
├── automation/            # Core trading bot
│   ├── main.py           # Trading system orchestrator
│   ├── config.py         # Configuration loader
│   ├── earnings_scanner.py    # Earnings event scanner
│   ├── trade_executor.py      # IB order execution
│   ├── position_manager.py    # Entry/exit timing
│   ├── risk_monitor.py        # Risk management
│   ├── ib_api_client.py       # IB Client Portal API
│   ├── database/              # Database operations
│   ├── utils/                 # Utility functions
│   └── setup_cron.sh          # Trading bot cron setup
│
├── scripts/               # Development utilities
│   ├── test_yfinance.py       # Yahoo Finance testing
│   └── test_finance_calendars.py # Calendar testing
│
├── clientportal.gw/       # IB Client Portal Gateway
│   └── bin/run.sh        # Gateway startup script
│
├── logs/                  # Application logs
├── requirements.txt       # Python dependencies
└── venv/                  # Virtual environment (gitignored)
```

## Setup

1. **Create virtual environment:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
# Copy .env.example from project root
cp ../.env.example ../.env
# Edit ../.env with your credentials
```

## Running the Backend

### Development Mode

Use the root-level startup script:
```bash
cd ..
./scripts/start-dev.sh
```

This starts:
- FastAPI server on port 3000
- IB Client Portal on port 5001
- Next.js frontend on port 3001

### Individual Components

**FastAPI Server:**
```bash
source venv/bin/activate
cd api
python main.py
```

**Trading Bot:**
```bash
source venv/bin/activate
cd automation
python main.py --action health
```

**IB Client Portal:**
```bash
cd clientportal.gw/bin
./run.sh
```

## Cron Jobs

The system has two sets of cron jobs:

1. **API Data Fetching** (`api/setup_cron.sh`)
   - 9:00 AM ET: Daily earnings fetch
   - 3:50 PM ET: Pre-trade refresh

2. **Trading Bot** (`automation/setup_cron.sh`)
   - 3:00 PM ET: Scan for opportunities
   - 3:45 PM ET: Enter positions
   - 9:45 AM ET: Exit positions
   - 6:00 PM ET: Performance report

To set up cron jobs, use the root-level selector:
```bash
cd ..
./scripts/setup_cron.sh
```

## Testing

**Test IB Connection:**
```bash
cd automation
python test_ib_connection.py
python test_ib_api_full.py
```

**Test Yahoo Finance:**
```bash
cd scripts
python test_yfinance.py
```

## Database

The system uses PostgreSQL (Neon DB). Initialize the schema:
```bash
cd automation/database
python init_db.py
```

## Key Configuration

All configuration is in `automation/config.py` which loads from the `.env` file:
- Trading parameters (position sizing, risk limits)
- API credentials (IB, database)
- Notification settings (email, Discord)