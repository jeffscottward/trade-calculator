#!/bin/bash

# Cron job setup for automated earnings data fetching
# Add these lines to your crontab using: crontab -e

echo "# Trade Calculator Automated Data Fetching"
echo ""
echo "# Daily fetch at 9:00 AM ET (fetch tomorrow's earnings)"
echo "0 9 * * * cd /Users/jeffscottward/Documents/GitHub/trading/trade-calculator && source venv/bin/activate && python api/cron_daily_fetch.py >> logs/cron_daily.log 2>&1"
echo ""
echo "# Pre-trade refresh at 3:50 PM ET (10 min before market close)"
echo "50 15 * * 1-5 cd /Users/jeffscottward/Documents/GitHub/trading/trade-calculator && source venv/bin/activate && python api/cron_pretrade_fetch.py >> logs/cron_pretrade.log 2>&1"
echo ""
echo "# Note: Times are in ET. Adjust for your server's timezone if needed"
echo "# Note: Second job only runs Monday-Friday (trading days)"
echo ""
echo "To install these cron jobs:"
echo "1. Run: crontab -e"
echo "2. Copy and paste the above lines (without the echo and quotes)"
echo "3. Save and exit"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To remove all cron jobs: crontab -r"