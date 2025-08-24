#!/usr/bin/env python
"""
Cron job script to fetch tomorrow's earnings data
Run this at 9 AM ET daily to prepare for next day's trades
"""
import asyncio
import logging
from datetime import date, timedelta
from database_operations import fetch_and_store_earnings_for_date

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fetch_tomorrow_earnings():
    """Fetch and store earnings data for tomorrow"""
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    
    logger.info(f"Fetching earnings data for tomorrow: {tomorrow_str}")
    
    # Force refresh to get latest data
    success = await fetch_and_store_earnings_for_date(tomorrow_str, force_refresh=True)
    
    if success:
        logger.info(f"✅ Successfully fetched and stored earnings for {tomorrow_str}")
    else:
        logger.warning(f"⚠️ Failed to fetch earnings for {tomorrow_str}")
    
    return success

if __name__ == "__main__":
    print("\n🚀 Daily earnings fetch cron job")
    print("Fetching tomorrow's earnings data...")
    
    result = asyncio.run(fetch_tomorrow_earnings())
    
    if result:
        print("✅ Cron job completed successfully")
    else:
        print("❌ Cron job failed")
        exit(1)