"""
Daily earnings scanner that identifies and qualifies trading opportunities.
Runs at 3:00 PM ET to find tomorrow's earnings events.
"""

import logging
from datetime import datetime, timedelta
import requests
import yfinance as yf
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import time

from config import DATA_CONFIG, STRATEGY_CONFIG
from database.db_manager import DatabaseManager
from utils.volatility import calculate_yang_zhang, calculate_iv_rv_ratio
from utils.options_analysis import analyze_term_structure

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EarningsScanner:
    """Scans for upcoming earnings events and qualifies them for trading."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.alpha_vantage_key = DATA_CONFIG['alpha_vantage_key']
        self.strategy_config = STRATEGY_CONFIG
        
    def fetch_earnings_calendar(self) -> List[Dict]:
        """Fetch earnings calendar from Alpha Vantage."""
        if not self.alpha_vantage_key:
            logger.error("Alpha Vantage API key not configured")
            return []
        
        url = 'https://www.alphavantage.co/query'
        params = {
            'function': 'EARNINGS_CALENDAR',
            'horizon': DATA_CONFIG['earnings_horizon'],
            'apikey': self.alpha_vantage_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            # Alpha Vantage returns CSV for earnings calendar
            import io
            import csv
            
            csv_data = io.StringIO(response.text)
            reader = csv.DictReader(csv_data)
            earnings = list(reader)
            
            # Filter for tomorrow's earnings
            tomorrow = (datetime.now() + timedelta(days=1)).date()
            tomorrow_earnings = [
                e for e in earnings 
                if datetime.strptime(e['reportDate'], '%Y-%m-%d').date() == tomorrow
            ]
            
            logger.info(f"Found {len(tomorrow_earnings)} earnings events for tomorrow")
            return tomorrow_earnings
            
        except Exception as e:
            logger.error(f"Failed to fetch earnings calendar: {e}")
            return []
    
    def qualify_trade(self, symbol: str, earnings_date: datetime) -> Dict:
        """Analyze a stock to determine if it qualifies for trading."""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get historical data for volatility calculations
            hist = ticker.history(period="3mo")
            if hist.empty:
                logger.warning(f"No historical data for {symbol}")
                return {'qualified': False, 'reason': 'No historical data'}
            
            # Calculate 30-day average volume
            avg_volume_30d = hist['Volume'].tail(30).mean()
            if avg_volume_30d < self.strategy_config['volume_threshold']:
                return {
                    'qualified': False, 
                    'reason': f'Volume too low: {avg_volume_30d:,.0f}'
                }
            
            # Calculate Yang-Zhang volatility
            yang_zhang_vol = calculate_yang_zhang(hist)
            
            # Get options chain and analyze term structure
            try:
                options_dates = ticker.options
                if len(options_dates) < 2:
                    return {'qualified': False, 'reason': 'Insufficient options dates'}
                
                # Analyze term structure
                term_analysis = analyze_term_structure(ticker, options_dates)
                term_structure_slope = term_analysis.get('slope', 0)
                
                if term_structure_slope >= self.strategy_config['term_structure_threshold']:
                    return {
                        'qualified': False,
                        'reason': f'Term structure not negative: {term_structure_slope:.3f}'
                    }
                
                # Calculate IV/RV ratio
                iv_rv_ratio = calculate_iv_rv_ratio(
                    ticker, 
                    options_dates[0], 
                    yang_zhang_vol
                )
                
                if iv_rv_ratio < self.strategy_config['iv_rv_threshold']:
                    return {
                        'qualified': False,
                        'reason': f'IV/RV ratio too low: {iv_rv_ratio:.2f}'
                    }
                
                # All checks passed
                return {
                    'qualified': True,
                    'term_structure_slope': term_structure_slope,
                    'avg_volume_30d': int(avg_volume_30d),
                    'iv_rv_ratio': iv_rv_ratio,
                    'yang_zhang_vol': yang_zhang_vol,
                    'recommendation': self._get_recommendation(
                        term_structure_slope, avg_volume_30d, iv_rv_ratio
                    )
                }
                
            except Exception as e:
                logger.error(f"Options analysis failed for {symbol}: {e}")
                return {'qualified': False, 'reason': f'Options analysis failed: {str(e)}'}
                
        except Exception as e:
            logger.error(f"Failed to qualify {symbol}: {e}")
            return {'qualified': False, 'reason': f'Analysis failed: {str(e)}'}
    
    def _get_recommendation(self, slope: float, volume: float, iv_rv: float) -> str:
        """Determine trade recommendation based on metrics."""
        # All three criteria met
        if (slope < self.strategy_config['term_structure_threshold'] and
            volume > self.strategy_config['volume_threshold'] and
            iv_rv > self.strategy_config['iv_rv_threshold']):
            return 'RECOMMENDED'
        
        # Two criteria met, including term structure
        criteria_met = sum([
            slope < self.strategy_config['term_structure_threshold'],
            volume > self.strategy_config['volume_threshold'],
            iv_rv > self.strategy_config['iv_rv_threshold']
        ])
        
        if criteria_met == 2 and slope < self.strategy_config['term_structure_threshold']:
            return 'CONSIDER'
        
        return 'AVOID'
    
    def scan_and_store(self) -> List[Dict]:
        """Main scanning function that finds and qualifies trades."""
        logger.info("Starting earnings scan...")
        
        # Fetch tomorrow's earnings
        earnings_events = self.fetch_earnings_calendar()
        if not earnings_events:
            logger.info("No earnings events found for tomorrow")
            return []
        
        qualified_trades = []
        
        for event in earnings_events:
            symbol = event['symbol']
            earnings_date = datetime.strptime(event['reportDate'], '%Y-%m-%d')
            
            logger.info(f"Analyzing {symbol}...")
            
            # Add delay to avoid rate limiting
            time.sleep(1)
            
            # Qualify the trade
            qualification = self.qualify_trade(symbol, earnings_date)
            
            if qualification['qualified']:
                # Store in database
                try:
                    event_id = self.db.insert_earnings_event(
                        symbol=symbol,
                        earnings_date=earnings_date,
                        term_structure_slope=qualification['term_structure_slope'],
                        avg_volume_30d=qualification['avg_volume_30d'],
                        iv_rv_ratio=qualification['iv_rv_ratio'],
                        recommendation=qualification['recommendation']
                    )
                    
                    qualified_trades.append({
                        'id': event_id,
                        'symbol': symbol,
                        'earnings_date': earnings_date,
                        **qualification
                    })
                    
                    logger.info(f"✅ {symbol}: {qualification['recommendation']}")
                    
                except Exception as e:
                    logger.error(f"Failed to store {symbol} in database: {e}")
            else:
                logger.info(f"❌ {symbol}: {qualification.get('reason', 'Unknown')}")
        
        logger.info(f"Scan complete. Found {len(qualified_trades)} qualified trades")
        return qualified_trades
    
    def get_todays_recommendations(self) -> List[Dict]:
        """Get all recommended trades from today's scan."""
        query = """
            SELECT * FROM earnings_events
            WHERE DATE(scan_date) = CURRENT_DATE
            AND recommendation IN ('RECOMMENDED', 'CONSIDER')
            ORDER BY recommendation, symbol
        """
        return self.db.execute_query(query)


def main():
    """Main function to run the earnings scanner."""
    scanner = EarningsScanner()
    
    # Check if Alpha Vantage key is configured
    if not scanner.alpha_vantage_key:
        logger.error("Alpha Vantage API key not configured. Set ALPHA_VANTAGE_KEY in .env")
        return
    
    # Run the scan
    qualified_trades = scanner.scan_and_store()
    
    # Display results
    if qualified_trades:
        print("\n" + "="*60)
        print("QUALIFIED TRADES FOR TOMORROW")
        print("="*60)
        
        for trade in qualified_trades:
            print(f"\nSymbol: {trade['symbol']}")
            print(f"Recommendation: {trade['recommendation']}")
            print(f"Term Structure Slope: {trade['term_structure_slope']:.3f}")
            print(f"30-Day Avg Volume: {trade['avg_volume_30d']:,}")
            print(f"IV/RV Ratio: {trade['iv_rv_ratio']:.2f}")
            print("-"*40)
    else:
        print("\nNo qualified trades found for tomorrow")


if __name__ == "__main__":
    main()