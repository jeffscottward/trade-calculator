#!/bin/bash
# Update earnings data from NASDAQ
# This script should be run daily via cron to keep earnings data current

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Log file
LOG_FILE="$PROJECT_ROOT/logs/earnings_update.log"
mkdir -p "$PROJECT_ROOT/logs"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_message "Starting earnings data update"

# Change to project directory
cd "$PROJECT_ROOT" || exit 1

# Activate virtual environment
source venv/bin/activate

# Update earnings for the next 30 days
python automation/earnings_data_importer.py --days 30

# Check if update was successful
if [ $? -eq 0 ]; then
    log_message "Earnings data update completed successfully"
else
    log_message "ERROR: Earnings data update failed"
    exit 1
fi

# Optional: Send notification on failure
# You can add email notification or Slack webhook here

log_message "Update process finished"