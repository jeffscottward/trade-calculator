# Trade Calculator

An options trading calculator with Black-Scholes pricing model and real-time Yahoo Finance data integration.

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

## 📚 Documentation

### Installation Guide
Detailed Python installation instructions: [Google Docs Guide](https://docs.google.com/document/d/1BrC7OrSTBqFs5Q-ZlYTMBJYDaS5r5nrE0070sa0qmaA/edit?tab=t.0#heading=h.tfjao7msc0g8)

### Monte Carlo / Backtest Results
View the comprehensive backtest analysis: [Backtest Results](https://docs.google.com/document/d/1_7UoFIqrTftoz-PJ0rxkttMc24inrAbWuZSbbOV-Jwk/edit?tab=t.0#heading=h.kc4shq41bugz)

### Trade Tracker Template
Get the trade tracking spreadsheet: [Google Sheets Template](https://docs.google.com/spreadsheets/d/1z_PMFqmV_2XqlCcCAdA4wgxqDg0Ym7iSeygNRpsnpO8/edit?gid=0#gid=0)
- Go to File → Make a copy (for Google Sheets)
- Or download for Excel (tested primarily in Google Sheets)

## 🛠️ Features

- **Black-Scholes Options Pricing**: Accurate theoretical options pricing
- **Yang-Zhang Volatility**: Advanced volatility calculation for better accuracy
- **Real-time Data**: Live market data from Yahoo Finance
- **GUI Interface**: User-friendly interface built with FreeSimpleGUI
- **Python 3.13 Compatibility**: Includes compatibility fixes for latest Python versions

## 📋 Disclaimer

This software is provided solely for educational and research purposes. It is not intended to provide investment advice, and no investment recommendations are made herein. The developers are not financial advisors and accept no responsibility for any financial decisions or losses resulting from the use of this software. Always consult a professional financial advisor before making any investment decisions.

## 🐛 Troubleshooting

If you encounter Yahoo Finance rate limiting (429 errors):
1. Wait 1-2 minutes and try again
2. Run `python scripts/test_yfinance.py` to test the connection
3. Check the Discord community for support

## 📁 Project Structure

```
trade-calculator/
├── calculator.py           # Main application with GUI
├── requirements.txt        # Python dependencies
├── docs/                  # Documentation and resources
│   ├── Earnings Research.pdf
│   ├── Earnings Tracker.xlsx
│   └── youtube_transcript.txt
├── scripts/               # Utility scripts
│   ├── calculator_debug.py    # Debug version with error tracking
│   ├── run_with_debug.py      # Debug wrapper with detailed logging
│   ├── test_yfinance.py       # Yahoo Finance connection tester
│   └── tkinter_fix.py         # Python 3.13 compatibility layer
└── logs/                  # Debug logs (gitignored)
```