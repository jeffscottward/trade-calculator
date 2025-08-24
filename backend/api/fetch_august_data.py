#!/usr/bin/env python
"""
Script to fetch and store all remaining August 2024 earnings data
Includes 10-second delays between requests to avoid hammering APIs
"""
import asyncio
import logging
from datetime import date, timedelta
from database_operations import (
    check_date_has_data, 
    fetch_and_store_earnings_for_date,
    get_db_connection
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fetch_august_data():
    """Fetch and store all remaining August 2024 days"""
    
    # Get today's date
    today = date.today()
    
    # Start from today (August 22, 2024) through end of August
    start_date = date(2024, 8, 22)  # Today is August 22
    end_date = date(2024, 8, 31)
    
    current_date = start_date
    dates_to_fetch = []
    
    while current_date <= end_date:
        dates_to_fetch.append(current_date)
        current_date += timedelta(days=1)
    
    logger.info(f"Will process {len(dates_to_fetch)} dates from August {start_date.day} to {end_date.day}")
    
    successful = 0
    skipped = 0
    failed = 0
    
    for fetch_date in dates_to_fetch:
        date_str = fetch_date.strftime("%Y-%m-%d")
        
        # Check if we already have data
        if check_date_has_data(fetch_date):
            logger.info(f"✓ {date_str}: Data already exists, skipping")
            skipped += 1
        else:
            logger.info(f"📥 {date_str}: Fetching and analyzing earnings data...")
            
            try:
                success = await fetch_and_store_earnings_for_date(date_str, force_refresh=False)
                
                if success:
                    logger.info(f"✅ {date_str}: Successfully stored earnings data")
                    successful += 1
                else:
                    logger.warning(f"⚠️ {date_str}: No earnings data found or failed to store")
                    failed += 1
                    
            except Exception as e:
                logger.error(f"❌ {date_str}: Error fetching data: {e}")
                failed += 1
            
            # Wait 10 seconds between API calls to avoid rate limiting
            if fetch_date != dates_to_fetch[-1]:  # Don't wait after the last date
                logger.info("⏳ Waiting 10 seconds before next request...")
                await asyncio.sleep(10)
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("FETCH COMPLETE")
    logger.info(f"✅ Successful: {successful}")
    logger.info(f"⏭️ Skipped (already existed): {skipped}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"📊 Total processed: {len(dates_to_fetch)}")
    logger.info("="*50)

if __name__ == "__main__":
    print("\n🚀 Starting August 2024 earnings data fetch...")
    print("This will take several minutes due to API rate limiting delays.\n")
    
    # Run the async function
    asyncio.run(fetch_august_data())
    
    print("\n✅ Process complete!")