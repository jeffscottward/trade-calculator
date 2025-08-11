# Automated Earnings Volatility Trading System

An automated options trading system that sells volatility around earnings events using calendar spreads, with Interactive Brokers integration for execution.

## 📺 Video Tutorial

Watch the full explanation and strategy breakdown:
- **YouTube**: [Options Trading Strategy Tutorial](https://www.youtube.com/watch?v=oW6MHjzxHpU&t=1s)

## 🤝 Community Support

Join our Discord community for help and discussions:
- **Discord**: [Join Server](https://discord.gg/krdByJHuHc)

## 🚀 Quick Start

### Prerequisites

- Python 3.10+ (tested on 3.10.11, now compatible with 3.13+)
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/jeffscottward/trade-calculator.git
cd trade-calculator
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Calculator

```bash
python calculator.py
```

For debugging with detailed logs:
```bash
python scripts/run_with_debug.py
```

To test Yahoo Finance connection:
```bash
python scripts/test_yfinance.py
```

### Running the IB Client Portal API Server

```bash
# Start the IB Client Portal API server on port 5001
python automation/ib_client_portal_server.py
```

Note: The server is configured to run on port 5001 instead of the default 5000.

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

## 🛠️ Features

### Current Features
- **Black-Scholes Options Pricing**: Accurate theoretical options pricing
- **Yang-Zhang Volatility**: Advanced volatility calculation for better accuracy
- **Real-time Data**: Live market data from Yahoo Finance
- **GUI Interface**: User-friendly interface built with FreeSimpleGUI
- **Trade Qualification**: Analyzes term structure, volume, and IV/RV ratios

### Automation Features
- **Automated Scanning**: Daily earnings event detection via Alpha Vantage API
- **Interactive Brokers Integration**: Automated order execution via TWS/Gateway API
- **IB Client Portal API**: REST API for account data and trading (port 5001)
- **Position Management**: Automatic entry 15 min before close, exit 15 min after open
- **Risk Controls**: Portfolio limits, drawdown monitoring, emergency stops
- **Performance Tracking**: Real-time P&L, win rate, and Sharpe ratio monitoring

## 📋 Disclaimer

This software is provided solely for educational and research purposes. It is not intended to provide investment advice, and no investment recommendations are made herein. The developers are not financial advisors and accept no responsibility for any financial decisions or losses resulting from the use of this software. Always consult a professional financial advisor before making any investment decisions.

## 🏦 Broker Integration

### Why Interactive Brokers?

After researching multiple broker APIs, we've selected **Interactive Brokers** for the following reasons:

1. **Best API Support**: Native Python API with excellent documentation and stability
2. **Competitive Pricing**: $0.15-$0.65 per options contract for active traders
3. **Professional Features**: Advanced order types, portfolio margin, international markets
4. **Proven Track Record**: Used in the original research and backtesting
5. **No Token Expiration**: Unlike Schwab's 7-day tokens, IB maintains persistent connections

### Data Sources

- **Earnings Calendar**: Alpha Vantage (500 free API calls/day)
- **Market Data**: Yahoo Finance via yfinance library
- **Backup Data**: Interactive Brokers real-time feed
- **IB Client Portal API**: REST API documentation at [IB Campus](https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#introduction)

## 🔄 Automated Trading Workflow

1. **Daily Scan (3:00 PM ET)**: Identify tomorrow's earnings events
2. **Qualification**: Check term structure, volume, and IV/RV ratios
3. **Position Sizing**: Calculate 6% portfolio allocation per trade
4. **Order Entry**: Place calendar spread 15 minutes before close
5. **Exit**: Close position 15 minutes after market open next day
6. **Logging**: Track all trades and performance metrics

See [System Design Document](docs/SYSTEM_DESIGN.md) for detailed architecture.

## 🐛 Troubleshooting

If you encounter Yahoo Finance rate limiting (429 errors):
1. Wait 1-2 minutes and try again
2. Run `python scripts/test_yfinance.py` to test the connection
3. Check the Discord community for support

## 📁 Project Structure

```
trade-calculator/
├── calculator.py              # Main application with GUI
├── requirements.txt           # Python dependencies
├── docs/                      # Documentation and resources
│   ├── SYSTEM_DESIGN.md      # Automated trading system architecture
│   ├── Earnings Research.pdf # Original strategy research
│   ├── Earnings Tracker.xlsx # Trade tracking spreadsheet
│   └── youtube_transcript.txt# Full strategy explanation
├── scripts/                   # Utility scripts
│   ├── calculator_debug.py   # Debug version with error tracking
│   ├── run_with_debug.py     # Debug wrapper with detailed logging
│   ├── test_yfinance.py      # Yahoo Finance connection tester
│   └── tkinter_fix.py        # Python 3.13 compatibility layer
├── automation/                # Automated trading modules
│   ├── earnings_scanner.py   # Daily earnings event scanner
│   ├── trade_executor.py     # IB order execution
│   ├── position_manager.py   # Entry/exit automation
│   ├── risk_monitor.py       # Risk management system
│   └── ib_client_portal_server.py # IB Client Portal API server (port 5001)
└── logs/                      # Debug logs (gitignored)
```