# Automated Earnings Volatility Trading System

An automated options trading system that sells volatility around earnings events using calendar spreads. Features a modern web-based interface for analyzing earnings opportunities and executing trades through Interactive Brokers API.

## 📺 Video Tutorial

Watch the full explanation and strategy breakdown:
- **YouTube**: [Options Trading Strategy Tutorial](https://www.youtube.com/watch?v=oW6MHjzxHpU&t=1s)

## 🤝 Community Support

Join our Discord community for help and discussions:
- **Discord**: [Join Server](https://discord.gg/krdByJHuHc)

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ (tested with 3.10-3.13)
- Node.js 18+ and pnpm package manager
- Interactive Brokers Pro account
- Neon PostgreSQL database (free tier available)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/jeffscottward/trade-calculator.git
cd trade-calculator
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials:
# - IB account credentials
# - Neon DB connection string
# - API keys
```

3. Set up Python backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

4. Set up frontend:
```bash
cd frontend
pnpm install
cd ..
```

5. Initialize database:
```bash
cd backend
python automation/database/init_db.py
cd ..
```

### Running the Application

#### Quick Start (All Services)

```bash
# Start all development services with one command
./scripts/start-dev.sh
```

This will start:
- Next.js frontend on http://localhost:3001
- FastAPI backend on http://localhost:3000
- IB Client Portal Gateway on https://localhost:5001 (requires manual login)

#### Manual Start (Individual Services)

```bash
# Terminal 1: Start backend API
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python api/main.py

# Terminal 2: Start frontend
cd frontend
pnpm run dev

# Terminal 3: Start IB Gateway (if trading)
cd backend/clientportal.gw/bin
./run.sh  # On Windows: run.bat
```

### Testing Components

```bash
# Test Yahoo Finance connection
python scripts/test_yfinance.py

# Test IB connection (gateway must be running)
cd backend
python tests/test_ib_connection.py

# Run automated tests
python -m pytest tests/
```

### Running the IB Client Portal Gateway

```bash
# Navigate to the gateway directory
cd backend/clientportal.gw/bin

# Start the gateway (runs on port 5001)
./run.sh  # On macOS/Linux
run.bat   # On Windows
```

**Important Notes:**
- Gateway runs on **port 5001** (configured to avoid port conflicts)
- Access the gateway at: https://localhost:5001
- Login with your IB credentials (check `.env` for `IB_BROWSER_USERNAME`)
- Keep the browser tab open during your trading session
- Gateway must be running for all trading operations

## 📚 Documentation

### Installation Guide
Detailed Python installation instructions: [Google Docs Guide](https://docs.google.com/document/d/1BrC7OrSTBqFs5Q-ZlYTMBJYDaS5r5nrE0070sa0qmaA/edit?tab=t.0#heading=h.tfjao7msc0g8)

### Monte Carlo / Backtest Results
View the comprehensive backtest analysis: [Backtest Results](https://docs.google.com/document/d/1_7UoFIqrTftoz-PJ0rxkttMc24inrAbWuZSbbOV-Jwk/edit?tab=t.0#heading=h.kc4shq41bugz)

### Trade Tracker Template
Get the trade tracking spreadsheet: [Google Sheets Template](https://docs.google.com/spreadsheets/d/1z_PMFqmV_2XqlCcCAdA4wgxqDg0Ym7iSeygNRpsnpO8/edit?gid=0#gid=0)
- Go to File → Make a copy (for Google Sheets)
- Or download for Excel (tested primarily in Google Sheets)

## 🎯 Strategy Overview

This system implements a systematic approach to selling earnings volatility through calendar spreads:
- **Win Rate**: 66% historical success rate
- **Expected Return**: 7.3% per trade
- **Risk Management**: 6% position sizing (10% Kelly criterion)
- **Trade Structure**: Long calendar spreads (sell front month, buy back month)

### Trade Ranking System

Not all earnings trades are equal. The system uses a sophisticated **Priority Score (0-100)** to rank opportunities:

#### How Priority Scores Work

Each trade is scored based on four key factors:

1. **IV/RV Ratio (40% weight)**: How overpriced is the implied volatility?
   - Compares implied volatility to realized volatility
   - Higher ratios mean options are more expensive relative to actual stock movement
   - Example: IV/RV of 2.0 means options price in 2x the actual volatility

2. **Term Structure Slope (30% weight)**: How steep is the volatility curve?
   - Measures difference between near-term and longer-term implied volatility
   - Negative slopes (backwardation) indicate better opportunities
   - Example: -0.4 slope means front month IV is 40% higher than back month

3. **Liquidity Score (20% weight)**: How easy is it to trade?
   - Based on 30-day average trading volume
   - Higher volume means tighter spreads and easier execution
   - Ensures we can enter and exit positions efficiently

4. **Market Cap (10% weight)**: Company size for stability
   - Larger companies tend to have more liquid options
   - Provides a stability factor but doesn't dominate the ranking

#### Why This Matters

With limited capital (max 20% portfolio exposure, 3 concurrent positions), the system must choose the best opportunities. Instead of trading alphabetically or by company size, it prioritizes trades with:
- The most overpriced volatility
- The steepest term structure advantage
- Sufficient liquidity for clean execution

This ensures maximum expected return within risk limits.

## 🛠️ Features

### Web Interface
- **Earnings Calendar**: Interactive calendar showing upcoming earnings events
- **Stock Analysis**: One-click analysis with IV/RV ratios and term structure
- **Trade Dashboard**: Real-time position monitoring and P&L tracking
- **Risk Overview**: Portfolio exposure and drawdown metrics
- **Search**: Find stocks by ticker or company name
- **Tech Stack**: Next.js 14, React 18, TypeScript, Tailwind CSS, shadcn/ui

### Trading Features
- **Options Pricing**: Black-Scholes model with Greeks calculation
- **Volatility Analysis**: Yang-Zhang volatility with historical comparison
- **Real-time Data**: Live options chains from Yahoo Finance and IB
- **Trade Qualification**: Automated screening based on term structure and IV/RV
- **Position Management**: Automated entry/exit with risk controls

### Automation Capabilities
- **Earnings Detection**: Daily scan via NASDAQ API at 3 PM ET
- **Order Execution**: Fully automated via IB Client Portal API
- **Trade Timing**: Entry at 3:45 PM (before earnings), exit at 9:45 AM (after)
- **Risk Management**: 
  - Position sizing: 6% per trade (Kelly criterion)
  - Max concurrent: 3 positions
  - Portfolio limit: 20% total exposure
  - Stop-loss: 50% of premium received
- **Performance Analytics**: Win rate, Sharpe ratio, maximum drawdown tracking

## ⚠️ Disclaimer

**IMPORTANT**: This software is for educational and research purposes only. 

- Not investment advice - no recommendations are made
- Use at your own risk - real money trading can result in losses
- The developers assume no liability for financial decisions
- Past performance does not guarantee future results
- Always consult a licensed financial advisor before trading

**Risk Warning**: Options trading involves substantial risk and is not suitable for all investors. You can lose more than your initial investment.

## 🏦 Interactive Brokers Integration

### System Requirements

- **Interactive Brokers Pro Account** (not Lite) for unrestricted API access
- **IB Client Portal Gateway** for REST API access (runs on port 5001)
- **Python API Support** via ib_insync library for automated trading

### Key Features

1. **Automated Order Execution**: Full support for complex options orders
2. **Real-time Market Data**: Live feed for options chains and market depth
3. **Portfolio Management**: Automatic position monitoring and P&L tracking
4. **Risk Controls**: Built-in portfolio limits and emergency stops

### Data Sources

- **Earnings Calendar**: NASDAQ API (free, no key required)
- **Options Data**: Yahoo Finance (primary), Interactive Brokers (backup)
- **Market Data**: Real-time feed from IB when gateway is connected
- **Historical Data**: Stored in Neon PostgreSQL for backtesting

### API Documentation

- **IB Client Portal**: [Official Documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/)
- **FastAPI Backend**: Auto-generated docs at http://localhost:3000/docs when running

## 🔄 Automated Trading Workflow

### Daily Operations

1. **3:00 PM ET - Earnings Scan**
   - Scans NASDAQ API for tomorrow's earnings
   - Filters by volume (>1M daily average)
   - Checks IV/RV ratio (>1.2 required)

2. **3:45 PM ET - Trade Qualification**
   - Analyzes term structure slope
   - Verifies options liquidity
   - Calculates position sizes (6% per trade)

3. **3:45 PM ET - Order Entry**
   - Places calendar spread orders via IB API
   - Sells front month, buys back month
   - Sets stop-loss at 50% of premium received

4. **9:45 AM ET Next Day - Position Exit**
   - Closes all earnings positions
   - Records P&L in database
   - Updates performance metrics

### Manual Controls

```bash
# Run earnings scanner manually
cd backend
python automation/earnings_scanner.py

# Execute trades manually
python automation/trade_executor.py

# Monitor positions
python automation/position_manager.py

# Test priority scoring
python ../scripts/test_priority_scoring.py
```

## 🐛 Troubleshooting

### Common Issues

**Yahoo Finance Rate Limiting (429 errors)**
- Wait 1-2 minutes between requests
- Use `python scripts/test_yfinance.py` to verify connection
- Consider using IB market data as backup

**IB Gateway Connection Issues**
- Ensure gateway is running on port 5001
- Check firewall settings for port access
- Verify credentials in `.env` file
- Try restarting the gateway

**Database Connection Errors**
- Verify Neon DB connection string in `.env`
- Check network connectivity
- Run `python automation/database/init_db.py` to reset schema

**Frontend Build Errors**
- Clear Next.js cache: `rm -rf frontend/apps/web/.next`
- Reinstall dependencies: `cd frontend && pnpm install`
- Check Node.js version (requires 18+)

## 📁 Project Structure

```
trade-calculator/
├── backend/                   # Python backend services
│   ├── api/                   # FastAPI server
│   │   ├── endpoints/         # API route handlers
│   │   └── main.py           # Server entry point
│   ├── automation/            # Automated trading modules
│   │   ├── database/          # Neon DB integration
│   │   ├── utils/             # Helper utilities
│   │   ├── config.py         # Central configuration
│   │   ├── earnings_scanner.py   # Daily earnings scanner
│   │   ├── trade_executor.py     # IB order execution
│   │   ├── position_manager.py   # Entry/exit automation
│   │   ├── risk_monitor.py       # Risk management
│   │   └── ib_api_client.py     # IB API wrapper
│   ├── clientportal.gw/       # IB Client Portal Gateway
│   │   ├── bin/               # Executable scripts
│   │   └── root/              # Configuration files
│   ├── tests/                 # Unit and integration tests
│   └── requirements.txt       # Python dependencies
├── frontend/                  # Next.js web application
│   ├── apps/
│   │   └── web/              # Main web app
│   │       ├── src/
│   │       │   ├── app/      # App router pages
│   │       │   ├── components/   # React components
│   │       │   ├── lib/      # Utilities and helpers
│   │       │   └── styles/   # CSS and styling
│   │       └── package.json  # Frontend dependencies
│   └── pnpm-workspace.yaml   # pnpm workspace config
├── docs/                      # Documentation
│   ├── SYSTEM_DESIGN.md     # Architecture overview
│   └── Earnings Research.pdf # Strategy research
├── scripts/                   # Utility scripts
│   ├── start-dev.sh          # Start all services
│   ├── test_yfinance.py     # Test Yahoo Finance
│   └── test_finance_calendars.py
├── .taskmaster/              # Task Master AI integration
├── CLAUDE.md                 # Claude Code instructions
└── README.md                 # This file
```