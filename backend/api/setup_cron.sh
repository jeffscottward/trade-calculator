#!/bin/bash

# Setup script for API data fetching cron jobs
# Run this script to configure the API cron schedule

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"
PYTHON_PATH="$BACKEND_DIR/venv/bin/python"

echo "Setting up cron jobs for API data fetching..."

# Create logs directory if it doesn't exist
mkdir -p "$BACKEND_DIR/logs"

# Check if virtual environment exists
if [ ! -f "$PYTHON_PATH" ]; then
    echo "Error: Virtual environment not found at $PYTHON_PATH"
    echo "Please create a virtual environment first:"
    echo "  cd $BACKEND_DIR"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Backup existing crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null

# Define cron jobs
CRON_JOBS="
# Trade Calculator API - Automated Data Fetching
# All times in Eastern Time (ET)

# Daily fetch at 9:00 AM ET (fetch tomorrow's earnings)
0 9 * * * cd $PROJECT_ROOT && source $BACKEND_DIR/venv/bin/activate && python $SCRIPT_DIR/cron_daily_fetch.py >> $BACKEND_DIR/logs/cron_daily.log 2>&1

# Pre-trade refresh at 3:50 PM ET (10 min before market close)
50 15 * * 1-5 cd $PROJECT_ROOT && source $BACKEND_DIR/venv/bin/activate && python $SCRIPT_DIR/cron_pretrade_fetch.py >> $BACKEND_DIR/logs/cron_pretrade.log 2>&1
"

# Add cron jobs
echo "Adding the following cron jobs:"
echo "$CRON_JOBS"
echo ""

read -p "Do you want to install these cron jobs? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Add new cron jobs to existing crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOBS") | crontab -
    echo "✅ API cron jobs installed successfully!"
    echo ""
    echo "To verify, run: crontab -l"
    echo "To remove, run: crontab -e and delete the relevant lines"
else
    echo "Installation cancelled."
fi

echo ""
echo "Setup complete!"