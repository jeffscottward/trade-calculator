"""
NASDAQ Earnings Calendar Fetcher
Fetches earnings data from NASDAQ website (free, no API key required)
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import logging
from bs4 import BeautifulSoup
import json

logger = logging.getLogger(__name__)

def fetch_nasdaq_earnings(date_str: str) -> List[Dict]:
    """
    Fetch earnings calendar from NASDAQ for a specific date
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        List of earnings dictionaries
    """
    try:
        # NASDAQ earnings calendar URL
        url = f"https://api.nasdaq.com/api/calendar/earnings"
        
        # Headers to mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.nasdaq.com',
            'Referer': 'https://www.nasdaq.com/'
        }
        
        # Parameters for the API
        params = {
            'date': date_str
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch from NASDAQ: {response.status_code}")
            return []
            
        data = response.json()
        
        # Extract earnings data
        earnings_list = []
        if 'data' in data and 'rows' in data['data']:
            for row in data['data']['rows']:
                earnings_list.append({
                    'ticker': row.get('symbol', ''),
                    'companyName': row.get('name', ''),
                    'reportTime': row.get('time', 'TBD'),  # "time-not-supplied", "before-market", "after-market"
                    'marketCap': row.get('marketCap', ''),
                    'fiscalQuarterEnding': row.get('fiscalQuarterEnding', ''),
                    'estimate': row.get('epsForecast', ''),
                    'lastYearEPS': row.get('lastYearEPS', ''),
                    'lastYearReportDate': row.get('lastYearRptDt', ''),
                    'noOfEstimates': row.get('noOfEsts', 0)
                })
        
        logger.info(f"Found {len(earnings_list)} earnings for {date_str} from NASDAQ")
        return earnings_list
        
    except Exception as e:
        logger.error(f"Error fetching NASDAQ earnings: {e}")
        return []

def fetch_tradable_earnings(date_str: str) -> List[Dict]:
    """
    Fetch earnings and filter for tradable US stocks only
    Removes OTC, foreign stocks, and low-liquidity names
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        List of filtered earnings dictionaries
    """
    earnings = fetch_nasdaq_earnings(date_str)
    
    # Filter out OTC and foreign stocks
    filtered = []
    for earning in earnings:
        ticker = earning.get('ticker', '')
        
        # Skip OTC/foreign stocks (usually end with F, Y)
        if ticker and not ticker.endswith('F') and not ticker.endswith('Y'):
            # Additional filtering could be added here
            # e.g., minimum market cap, US exchanges only, etc.
            filtered.append(earning)
    
    logger.info(f"Filtered to {len(filtered)} tradable stocks from {len(earnings)} total")
    return filtered

if __name__ == "__main__":
    # Test the fetcher
    from datetime import datetime
    
    test_date = datetime(2025, 8, 25).strftime('%Y-%m-%d')
    earnings = fetch_tradable_earnings(test_date)
    
    print(f"\nEarnings for {test_date}:")
    for e in earnings[:10]:  # Show first 10
        print(f"  {e['ticker']}: {e['companyName']} - {e['reportTime']}")