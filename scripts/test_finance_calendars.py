#!/usr/bin/env python3
"""
Test finance_calendars library for fetching bulk earnings data from NASDAQ
"""

from finance_calendars.finance_calendars import get_earnings_by_date, get_earnings_today
from datetime import datetime, timedelta
import json
import pandas as pd

def test_earnings_fetch():
    """Test fetching earnings data from NASDAQ"""
    
    print("🚀 ~ file: test_finance_calendars.py:13 → test_earnings_fetch → Testing finance_calendars library")
    
    # First test today's earnings
    print("\n📊 Testing today's earnings...")
    try:
        today_earnings = get_earnings_today()
        if isinstance(today_earnings, pd.DataFrame):
            print(f"🚀 ~ file: test_finance_calendars.py:20 → test_earnings_fetch → Today's earnings count: {len(today_earnings)}")
            if not today_earnings.empty:
                print("\nSample of today's earnings (first 5):")
                print(today_earnings.head())
                print("\nColumns available:", today_earnings.columns.tolist())
        else:
            print("No earnings data for today")
    except Exception as e:
        print(f"❌ Error fetching today's earnings: {str(e)}")
    
    # Now test fetching for specific dates
    print("\n📅 Testing earnings by date...")
    dates_to_check = []
    for i in range(7):  # Check next 7 days
        date = datetime.now() + timedelta(days=i)
        dates_to_check.append(date)
    
    all_earnings = []
    earnings_by_date = {}
    
    for date_obj in dates_to_check:
        date_str = date_obj.strftime('%Y-%m-%d')
        try:
            print(f"\n🚀 ~ file: test_finance_calendars.py:41 → test_earnings_fetch → Fetching earnings for {date_str}...")
            earnings_data = get_earnings_by_date(date_obj)
            
            if isinstance(earnings_data, pd.DataFrame) and not earnings_data.empty:
                print(f"   Found {len(earnings_data)} companies reporting")
                earnings_by_date[date_str] = earnings_data
                
                # Convert DataFrame to list of dicts for easier handling
                earnings_list = earnings_data.to_dict('records')
                for earning in earnings_list:
                    earning['report_date'] = date_str
                all_earnings.extend(earnings_list)
                
                # Show sample for first date with data
                if len(all_earnings) == len(earnings_list):  # First date with data
                    print("\n📊 Sample earnings data structure:")
                    sample = earnings_list[0] if earnings_list else {}
                    for key, value in sample.items():
                        print(f"   - {key}: {value} ({type(value).__name__})")
            else:
                print(f"   No earnings found for {date_str}")
                
        except Exception as e:
            print(f"   ❌ Error fetching {date_str}: {str(e)}")
    
    # Summary
    print(f"\n📈 Summary:")
    print(f"   Total earnings found: {len(all_earnings)}")
    print(f"   Dates with earnings: {len(earnings_by_date)}")
    
    if earnings_by_date:
        print("\n📅 Earnings distribution:")
        for date, df in earnings_by_date.items():
            print(f"   {date}: {len(df)} companies")
    
    # Save sample data
    if all_earnings:
        sample_file = "sample_earnings_data.json"
        with open(sample_file, 'w') as f:
            # Take first 20 earnings
            sample_data = all_earnings[:20]
            # Convert any non-serializable types
            for item in sample_data:
                for key, value in item.items():
                    if pd.isna(value):
                        item[key] = None
                    elif isinstance(value, (pd.Timestamp, datetime)):
                        item[key] = str(value)
            json.dump(sample_data, f, indent=2, default=str)
        print(f"\n💾 Sample data saved to {sample_file}")
    
    return all_earnings

def test_bulk_download():
    """Test downloading earnings for entire month"""
    print("\n🗓️ Testing bulk download for entire month...")
    
    # Get all dates for current month
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # Calculate days in current month
    if current_month == 12:
        next_month = 1
        next_year = current_year + 1
    else:
        next_month = current_month + 1
        next_year = current_year
    
    days_in_month = (datetime(next_year, next_month, 1) - timedelta(days=1)).day
    
    print(f"🚀 ~ file: test_finance_calendars.py:108 → test_bulk_download → Downloading earnings for {current_year}-{current_month:02d}")
    
    monthly_earnings = []
    for day in range(1, days_in_month + 1):
        date_obj = datetime(current_year, current_month, day)
        date_str = date_obj.strftime('%Y-%m-%d')
        try:
            earnings = get_earnings_by_date(date_obj)
            if isinstance(earnings, pd.DataFrame) and not earnings.empty:
                earnings_list = earnings.to_dict('records')
                for earning in earnings_list:
                    earning['report_date'] = date_str
                monthly_earnings.extend(earnings_list)
                print(f"   {date_str}: {len(earnings)} companies")
        except Exception as e:
            # Skip errors for individual dates
            pass
    
    print(f"\n✅ Total earnings for the month: {len(monthly_earnings)}")
    
    # Save monthly data
    if monthly_earnings:
        monthly_file = f"earnings_{current_year}_{current_month:02d}.json"
        with open(monthly_file, 'w') as f:
            # Clean data for JSON serialization
            for item in monthly_earnings:
                for key, value in item.items():
                    if pd.isna(value):
                        item[key] = None
                    elif isinstance(value, (pd.Timestamp, datetime)):
                        item[key] = str(value)
            json.dump(monthly_earnings, f, indent=2, default=str)
        print(f"💾 Monthly data saved to {monthly_file}")
    
    return monthly_earnings

if __name__ == "__main__":
    print("=" * 60)
    print("NASDAQ Earnings Calendar Data Test")
    print("=" * 60)
    
    # Test basic fetching
    earnings = test_earnings_fetch()
    
    # Ask if user wants to download entire month
    print("\n" + "=" * 60)
    print("Note: Bulk download will fetch entire month's data.")
    print("This may take a few minutes...")
    # For automated testing, we'll skip the bulk download for now
    # Uncomment the next line to test bulk download
    # monthly_data = test_bulk_download()
    
    print("\n✅ Test completed!")