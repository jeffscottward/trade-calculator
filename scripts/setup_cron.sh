#!/bin/bash

# Master cron setup script for the Trading System
# This script helps you choose which cron jobs to set up

echo "======================================"
echo "Trading System Cron Job Setup"
echo "======================================"
echo ""
echo "This project has two types of cron jobs:"
echo ""
echo "1. AUTOMATION CRON (Main Trading Bot)"
echo "   - Scans for earnings events daily at 3:00 PM ET"
echo "   - Enters positions at 3:45 PM ET (15 min before close)"
echo "   - Exits positions at 9:45 AM ET (15 min after open)"
echo "   - Generates performance reports"
echo "   - Uses: automation/main.py"
echo ""
echo "2. API DATA CRON (Web Interface Data)"
echo "   - Fetches earnings calendar data at 9:00 AM ET"
echo "   - Refreshes data at 3:50 PM ET before trading"
echo "   - Keeps web interface data current"
echo "   - Uses: api/cron_daily_fetch.py and api/cron_pretrade_fetch.py"
echo ""
echo "======================================"
echo ""

PS3="Please select which cron jobs to set up: "
options=("Automation (Trading Bot)" "API (Web Data)" "Both" "Exit")
select opt in "${options[@]}"
do
    case $opt in
        "Automation (Trading Bot)")
            echo "Setting up automation cron jobs..."
            ../backend/automation/setup_cron.sh
            break
            ;;
        "API (Web Data)")
            echo "Setting up API data cron jobs..."
            ../backend/api/setup_cron.sh
            break
            ;;
        "Both")
            echo "Setting up both automation and API cron jobs..."
            echo ""
            echo "First, setting up automation cron jobs..."
            ../backend/automation/setup_cron.sh
            echo ""
            echo "Next, setting up API cron jobs..."
            ../backend/api/setup_cron.sh
            break
            ;;
        "Exit")
            echo "Exiting without changes."
            break
            ;;
        *) echo "Invalid option $REPLY";;
    esac
done

echo ""
echo "Setup complete!"
echo ""
echo "To view all cron jobs: crontab -l"
echo "To edit cron jobs: crontab -e"
echo "To remove all cron jobs: crontab -r"