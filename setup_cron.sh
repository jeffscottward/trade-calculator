#!/bin/bash

# Setup script for automated trading system cron jobs
# Run this script to configure the cron schedule

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
MAIN_SCRIPT="$SCRIPT_DIR/automation/main.py"

echo "Setting up cron jobs for automated trading system..."

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Check if virtual environment exists
if [ ! -f "$PYTHON_PATH" ]; then
    echo "Error: Virtual environment not found at $PYTHON_PATH"
    echo "Please create a virtual environment first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Backup existing crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null

# Define cron jobs
CRON_JOBS="
# Automated Trading System - Earnings Volatility Strategy
# All times in Eastern Time (ET)

# Daily earnings scan - 3:00 PM ET
0 15 * * 1-5 cd $SCRIPT_DIR && $PYTHON_PATH $MAIN_SCRIPT --action scan >> $SCRIPT_DIR/logs/cron.log 2>&1

# Enter positions - 3:45 PM ET (15 minutes before close)
45 15 * * 1-5 cd $SCRIPT_DIR && $PYTHON_PATH $MAIN_SCRIPT --action enter >> $SCRIPT_DIR/logs/cron.log 2>&1

# Exit positions - 9:45 AM ET (15 minutes after open)
45 9 * * 1-5 cd $SCRIPT_DIR && $PYTHON_PATH $MAIN_SCRIPT --action exit >> $SCRIPT_DIR/logs/cron.log 2>&1

# Daily performance report - 6:00 PM ET
0 18 * * 1-5 cd $SCRIPT_DIR && $PYTHON_PATH $MAIN_SCRIPT --action report >> $SCRIPT_DIR/logs/cron.log 2>&1

# System health check - Every hour during market hours
0 10-16 * * 1-5 cd $SCRIPT_DIR && $PYTHON_PATH $MAIN_SCRIPT --action health >> $SCRIPT_DIR/logs/cron.log 2>&1
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
    echo "✅ Cron jobs installed successfully!"
    echo ""
    echo "To verify, run: crontab -l"
    echo "To remove, run: crontab -e and delete the relevant lines"
else
    echo "Installation cancelled."
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Initialize the database: python automation/database/init_db.py"
echo "2. Configure your .env file with API keys and credentials"
echo "3. Test the system: python automation/main.py --action health"
echo "4. Monitor logs: tail -f logs/automation.log"