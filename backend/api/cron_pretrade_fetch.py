#!/usr/bin/env python
"""
Pre-trade cron job to refresh earnings data 10 minutes before market close
Run this at 3:50 PM ET on trading days
"""
import asyncio
import logging
from datetime import date
from database_operations import fetch_and_store_earnings_for_date

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def refresh_today_earnings():
    """Refresh today's earnings data before trades execute"""
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    
    logger.info(f"Refreshing earnings data for today: {today_str}")
    logger.info("This ensures we have the latest data before executing trades at market close")
    
    # Force refresh to get latest data
    success = await fetch_and_store_earnings_for_date(today_str, force_refresh=True)
    
    if success:
        logger.info(f"✅ Successfully refreshed earnings for {today_str}")
        logger.info("Ready for trade execution at 4:00 PM ET")
    else:
        logger.warning(f"⚠️ Failed to refresh earnings for {today_str}")
        logger.warning("Trades may execute with stale data")
    
    return success

if __name__ == "__main__":
    print("\n🚀 Pre-trade earnings refresh")
    print("Refreshing today's earnings data before market close...")
    print("Trades will execute in 10 minutes at 4:00 PM ET")
    
    result = asyncio.run(refresh_today_earnings())
    
    if result:
        print("✅ Pre-trade refresh completed successfully")
    else:
        print("❌ Pre-trade refresh failed - check logs")
        exit(1)