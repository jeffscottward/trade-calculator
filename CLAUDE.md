# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated earnings volatility trading system that sells calendar spreads around quarterly earnings events. Implements a systematic strategy with 66% historical win rate and 7.3% expected return per trade using Interactive Brokers API for execution.

## Important Date Convention

**CRITICAL**: This application operates in 2025 and beyond. NEVER use 2024 dates. The system is designed for current and future dates only (2025+). Do not implement any functionality that allows going backwards to 2024 or earlier years.

## Critical Security Note

**NEVER expose credentials in code**. All sensitive data must be in `.env` file (gitignored). Check `.env.example` for required variables.

## Debugging Conventions

### Console Logging Format
Always use this format for browser console logs:
```javascript
console.log(
  "🚀 ~ file: filename:linenumber → functionName → variableName:",
  variable
);
```

### Playwright MCP
Always run Playwright MCP in headless mode unless a visible browser is specifically required for the task:
```bash
playwright-mcp --headless
```
Note: Some tasks may require a visible browser (e.g., visual debugging, user interaction testing)

## Key Commands

### Environment Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with actual credentials
```

### Package Manager

**IMPORTANT**: Always use `pnpm` instead of `npm` for all JavaScript/Node.js package management tasks:
- Install: `pnpm install` (not npm install)
- Add packages: `pnpm add <package>` (not npm install <package>)
- Run scripts: `pnpm run <script>` (not npm run <script>)
- Execute packages: `pnpm exec` or `pnpx` (not npx)

### UI Components

**IMPORTANT**: Always use shadcn/ui components when available:
- Check if a shadcn component exists before using external libraries
- Use `pnpx shadcn@latest add <component>` to add new shadcn components
- shadcn components automatically handle dark mode theming
- Prefer shadcn over libraries like react-calendar, react-select, etc.

### Running Components

```bash
# Automated earnings scanner (runs daily at 3 PM ET via cron)
python automation/earnings_scanner.py

# Trade executor (handles IB order placement)
python automation/trade_executor.py

# IB Client Portal Gateway (runs on port 5001)
# Note: Configured to run on port 5001 instead of default 5000
# Run from the clientportal.gw directory
cd clientportal.gw/bin && ./run.sh  # On Windows: run.bat
```

### Database Setup

```bash
# Initialize Neon DB schema
python automation/database/init_db.py
```

## Architecture

### System Components

**automation/** - Core automated trading modules

- `earnings_scanner.py`: Daily scan for qualifying earnings events (NASDAQ API)
- `trade_executor.py`: Interactive Brokers order execution engine
- `position_manager.py`: Entry/exit timing automation (15 min before close/after open)
- `risk_monitor.py`: Portfolio limits and drawdown protection
- `config.py`: Central configuration (loads from .env)

**api/** - FastAPI backend server

- Serves earnings calendar data to web frontend
- SSE streaming for progress updates
- NASDAQ API integration for earnings data

### Trading Strategy Rules

1. **Entry Criteria** (ALL must be met):
   - Negative term structure slope (front month vs 45+ days)
   - 30-day average volume > 1M shares
   - IV/RV ratio > 1.2

2. **Position Sizing**:
   - 6% of portfolio per trade (10% Kelly criterion)
   - Maximum 3 concurrent positions
   - 20% max total exposure

3. **Trade Structure**:
   - Calendar spreads: Sell front month, buy back month (30-day gap)
   - Entry: 15 minutes before market close day before earnings
   - Exit: 15 minutes after market open day after earnings

### Database Schema (Neon DB PostgreSQL)

Key tables:

- `earnings_events`: Tracks scanned earnings with qualification metrics
- `trades`: Records all positions with entry/exit prices and P&L
- `performance_metrics`: Daily performance statistics

Uses PostgreSQL-specific features: SERIAL ids, TIMESTAMP WITH TIME ZONE, triggers for updated_at

### External APIs

**NASDAQ**: Earnings calendar (free, no API key required, better quality US stocks)
**Yahoo Finance**: Real-time options chains and volatility
**Interactive Brokers**: Order execution and market data backup
**IB Client Portal API**: REST API for account data and trading (port 5001)

- Documentation: <https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#introduction>

## Development Workflow

### Adding New Features

1. Update relevant module in `automation/`
2. Add database migrations if schema changes needed
3. Update risk limits in `config.py` if necessary
4. Test with paper trading account first (port 7497)

### Debugging Issues

- Check `logs/` folder for detailed debug output
- Yahoo Finance 429 errors: Wait 1-2 minutes or use `python scripts/test_yfinance.py`
- IB connection issues: Ensure TWS/Gateway running on correct port

## Critical Files Not to Modify

- `.env` - Contains actual credentials (local only)
- Database migration files once applied

## Testing Strategy

1. Paper trade with IB paper account (port 7497)
2. Start with 1% position sizing
3. Monitor first 20 trades before scaling to 6%
4. Track performance metrics in Neon DB

## Broker Configuration

Using **Interactive Brokers Pro** account (not Lite) for:

- Unrestricted API access
- Better execution for options
- No rejection of automated orders

## External Resources

- System Design: `docs/SYSTEM_DESIGN.md`
- Strategy Research: `docs/Earnings Research.pdf`
- Discord Support: <https://discord.gg/krdByJHuHc>

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
