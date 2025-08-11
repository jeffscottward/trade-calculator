# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Options trading calculator implementing Black-Scholes pricing model with real-time Yahoo Finance data. Features a GUI built with FreeSimpleGUI and uses Yang-Zhang volatility calculations for improved accuracy over standard historical volatility.

## Key Commands

### Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Main calculator GUI
python calculator.py

# Debug mode with detailed logging (logs to logs/ folder)
python scripts/run_with_debug.py

# Test Yahoo Finance API connectivity
python scripts/test_yfinance.py
```

## Architecture

### Core Components

**calculator.py** - Main application
- `compute_recommendation()`: Core calculation engine that fetches options chains and calculates recommendations
- `yang_zhang()`: Implements Yang-Zhang volatility estimator using OHLC data for more accurate volatility than simple close-to-close
- `build_term_structure()`: Creates interpolated implied volatility curve from discrete option expiration dates
- `filter_dates()`: Filters option expiration dates to only include those 45+ days out
- `main_gui()`: GUI event loop with threading for non-blocking API calls

### Critical Dependencies

**scripts/tkinter_fix.py**
- MUST be imported before FreeSimpleGUI on Python 3.13+
- Patches tkinter's trace method API changes (w→write, r→read, u→unset)
- Without this, application crashes on Python 3.13 with `_tkinter.TclError`

### Threading Model

The application uses threading to prevent UI freezes during Yahoo Finance API calls:
1. User input triggers background thread
2. Thread fetches options data and performs calculations
3. Main thread polls for completion and updates GUI
4. Window values dictionary maintains state between updates

### Yahoo Finance Integration

Rate limiting handling:
- Automatic retry with cookie strategy toggling (basic ↔ csrf)
- HTTP 429 errors require 1-2 minute wait
- Cache stored in `~/.cache/py-yfinance`
- Test connectivity with `python scripts/test_yfinance.py`

## Project Structure

```
trade-calculator/
├── calculator.py           # Main application
├── requirements.txt        # Dependencies
├── docs/                   # Documentation
│   ├── Earnings Research.pdf
│   ├── Earnings Tracker.xlsx
│   └── youtube_transcript.txt
├── scripts/                # Utility scripts
│   ├── calculator_debug.py # Debug wrapper
│   ├── run_with_debug.py   # Detailed logging runner
│   ├── test_yfinance.py    # API connectivity test
│   └── tkinter_fix.py      # Python 3.13+ compatibility
└── logs/                   # Debug logs (gitignored)
```

## Common Issues and Solutions

### Yahoo Finance Rate Limiting (429 errors)
1. Wait 1-2 minutes for rate limit reset
2. Run `python scripts/test_yfinance.py` to verify API access
3. Clear cache if persistent: `rm -rf ~/.cache/py-yfinance`

### Python 3.13 Compatibility
The tkinter_fix.py module is automatically imported to handle API changes. If seeing tkinter trace errors, ensure calculator.py imports are in correct order.

### Debug Workflow
Use `python scripts/run_with_debug.py` which:
- Creates timestamped logs in `logs/` folder
- Shows step-by-step import process
- Captures full stack traces with line numbers
- Helps identify rate limiting vs code issues

## External Resources

- **Discord Support**: https://discord.gg/krdByJHuHc
- **YouTube Tutorial**: https://www.youtube.com/watch?v=oW6MHjzxHpU
- **Monte Carlo Results**: https://docs.google.com/document/d/1_7UoFIqrTftoz-PJ0rxkttMc24inrAbWuZSbbOV-Jwk/
- **Trade Tracker Template**: https://docs.google.com/spreadsheets/d/1z_PMFqmV_2XqlCcCAdA4wgxqDg0Ym7iSeygNRpsnpO8/