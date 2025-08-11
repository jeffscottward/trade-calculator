# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an options trading calculator that provides Black-Scholes pricing with real-time Yahoo Finance data integration. The application uses a GUI built with FreeSimpleGUI and implements Yang-Zhang volatility calculations for more accurate options pricing.

## Key Commands

### Setup and Installation
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Main application
python calculator.py

# Debug mode with detailed logging
python scripts/run_with_debug.py

# Test Yahoo Finance connection
python scripts/test_yfinance.py
```

### Development and Testing
```bash
# No automated tests currently - manual GUI testing required
# Check Yahoo Finance API status if rate limiting occurs
python scripts/test_yfinance.py
```

## Architecture and Key Components

### Core Modules

**calculator.py** - Main application entry point
- `main_gui()`: Primary GUI loop that handles user interaction and real-time data updates
- `yang_zhang()`: Implements Yang-Zhang volatility estimator for more accurate volatility calculations than simple historical volatility
- `build_term_structure()`: Creates interpolated volatility term structure from options chain data
- Thread-based architecture for non-blocking Yahoo Finance API calls

### Python 3.13 Compatibility

**scripts/tkinter_fix.py** - Critical compatibility layer
- Patches tkinter's trace methods that changed in Python 3.13
- Must be imported before FreeSimpleGUI to prevent crashes
- Converts old trace modes ('w', 'r', 'u') to new API ('write', 'read', 'unset')
- Automatically loaded by calculator.py from scripts folder

### Data Flow

1. User inputs ticker symbol → spawns background thread
2. Thread fetches options chain from Yahoo Finance API
3. Extracts and filters expiration dates (45+ days out)
4. Calculates implied volatility term structure
5. Updates GUI with real-time pricing

### Yahoo Finance Rate Limiting

The application handles Yahoo Finance API rate limits (HTTP 429):
- Automatic cookie/crumb refresh on failure
- Cache clearing utility in scripts/test_yfinance.py
- Retry logic with strategy toggling (basic ↔ csrf)

### GUI State Management

- Non-blocking updates using threading
- Window values persist between updates
- Real-time price refresh without freezing UI

## Important Considerations

### API Rate Limits
Yahoo Finance enforces rate limiting. If encountering 429 errors:
1. Wait 1-2 minutes before retrying
2. Run `python scripts/test_yfinance.py` to verify API access
3. Clear cache if persistent issues occur

### Virtual Environment
Always use the virtual environment to ensure correct package versions, especially for FreeSimpleGUI compatibility.

### Debugging
Use `python scripts/run_with_debug.py` for detailed logging. Logs are saved with timestamps in `logs/` folder in format `debug_YYYYMMDD_HHMMSS.log`.

### Project Organization
- **docs/**: Contains documentation, Excel tracker, PDF research, and YouTube transcript
- **scripts/**: Utility scripts for debugging and testing
- **logs/**: Debug logs (gitignored, created automatically)

## External Resources

- Discord support: https://discord.gg/krdByJHuHc
- Monte Carlo/Backtest results: https://docs.google.com/document/d/1_7UoFIqrTftoz-PJ0rxkttMc24inrAbWuZSbbOV-Jwk/
- Trade Tracker Template: https://docs.google.com/spreadsheets/d/1z_PMFqmV_2XqlCcCAdA4wgxqDg0Ym7iSeygNRpsnpO8/