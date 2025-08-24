"""
Interactive Brokers Client Portal API Integration
For automated calendar spread execution
"""

import os
import requests
import json
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import schedule
import time as time_module
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CalendarSpreadOrder:
    """Represents a calendar spread order"""
    symbol: str
    strike: float
    front_expiry: str  # Format: YYYYMMDD
    back_expiry: str   # Format: YYYYMMDD
    option_type: str   # 'CALL' or 'PUT'
    quantity: int
    action: str = 'BUY'  # Calendar spreads are typically bought
    order_type: str = 'MKT'  # Market order for now

class IBAPIClient:
    """Client for Interactive Brokers Client Portal API"""
    
    def __init__(self, paper_trading=True):
        """Initialize IB API client
        
        Args:
            paper_trading: Use paper trading account (default True)
        """
        self.paper_trading = paper_trading
        self.base_url = "https://localhost:5001/v1/api"  # Client Portal Gateway on port 5001
        self.username = os.getenv('IB_PAPER_USERNAME' if paper_trading else 'IB_USERNAME')
        self.account = os.getenv('IB_PAPER_ACCOUNT' if paper_trading else 'IB_ACCOUNT')
        
        if not self.username or not self.account:
            raise ValueError("IB credentials not found in environment variables")
        
        # Session for persistent connection
        self.session = requests.Session()
        self.session.verify = False  # Client Portal uses self-signed cert
        
        # Suppress SSL warnings for self-signed cert
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.authenticated = False
        logger.info(f"IB API Client initialized for {'paper' if paper_trading else 'live'} trading")
        
    def authenticate(self) -> bool:
        """Authenticate with IB Client Portal API
        
        IMPORTANT: The Client Portal Gateway requires manual browser-based authentication.
        You must log in through the web interface at https://localhost:5001 first.
        This method only checks if authentication is already complete.
        
        Returns:
            True if authentication successful
        """
        try:
            # Check authentication status
            response = self.session.get(f"{self.base_url}/iserver/auth/status")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('authenticated', False):
                    self.authenticated = True
                    logger.info("✅ Already authenticated with IB API")
                    return True
                else:
                    logger.warning("⚠️ Not authenticated yet")
                    logger.info("Please complete authentication:")
                    logger.info("1. Open browser: https://localhost:5001")
                    logger.info("2. Accept certificate warning")
                    logger.info("3. Log in with paper trading credentials")
                    logger.info("4. Keep browser tab open")
                    return False
            elif response.status_code == 401:
                logger.warning("⚠️ IB Client Portal requires authentication")
                logger.info("Please log in at https://localhost:5001")
                return False
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information
        
        Returns:
            Account information dict or None
        """
        try:
            response = self.session.get(f"{self.base_url}/portfolio/accounts")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get account info: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return None
    
    def search_contract(self, symbol: str) -> Optional[int]:
        """Search for contract ID by symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Contract ID or None
        """
        try:
            params = {
                'symbol': symbol,
                'name': True,
                'secType': 'STK'
            }
            response = self.session.get(f"{self.base_url}/iserver/secdef/search", params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0].get('conid')
            return None
            
        except Exception as e:
            logger.error(f"Error searching contract: {str(e)}")
            return None
    
    def get_option_chain(self, symbol: str, expiry: str) -> Optional[List[Dict]]:
        """Get option chain for a symbol
        
        Args:
            symbol: Stock symbol
            expiry: Expiration date (YYYYMMDD)
            
        Returns:
            List of option contracts or None
        """
        try:
            # First get the underlying contract ID
            conid = self.search_contract(symbol)
            if not conid:
                logger.error(f"Could not find contract ID for {symbol}")
                return None
            
            # Get option chain
            response = self.session.get(f"{self.base_url}/iserver/secdef/strikes",
                                       params={'conid': conid, 'month': expiry[:6], 'exchange': 'SMART'})
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"Error getting option chain: {str(e)}")
            return None
    
    def place_calendar_spread(self, spread: CalendarSpreadOrder) -> Optional[str]:
        """Place a calendar spread order
        
        Args:
            spread: CalendarSpreadOrder object
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            # Calendar spread is a combo order in IB
            # We need to create a multi-leg order
            
            # Get contract IDs for both legs
            front_conid = self._get_option_conid(spread.symbol, spread.strike, 
                                                spread.front_expiry, spread.option_type)
            back_conid = self._get_option_conid(spread.symbol, spread.strike,
                                               spread.back_expiry, spread.option_type)
            
            if not front_conid or not back_conid:
                logger.error("Could not find option contract IDs")
                return None
            
            # Create combo order
            order = {
                'acctId': self.account,
                'orders': [{
                    'acctId': self.account,
                    'conid': front_conid,  # This would need to be a combo contract
                    'orderType': spread.order_type,
                    'side': spread.action,
                    'quantity': spread.quantity,
                    'tif': 'DAY',
                    # Calendar spread specific fields would go here
                    # IB requires special handling for multi-leg orders
                }]
            }
            
            # Place order
            response = self.session.post(f"{self.base_url}/iserver/account/{self.account}/orders",
                                        json=order)
            
            if response.status_code == 200:
                data = response.json()
                order_id = data[0].get('order_id') if data else None
                logger.info(f"Calendar spread order placed: {order_id}")
                return order_id
            else:
                logger.error(f"Failed to place order: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing calendar spread: {str(e)}")
            return None
    
    def _get_option_conid(self, symbol: str, strike: float, expiry: str, 
                          option_type: str) -> Optional[int]:
        """Get contract ID for specific option
        
        Args:
            symbol: Stock symbol
            strike: Strike price
            expiry: Expiration date (YYYYMMDD)
            option_type: 'CALL' or 'PUT'
            
        Returns:
            Contract ID or None
        """
        # This would need to query IB's option contract search
        # Implementation depends on IB's specific API endpoints
        logger.warning("Option contract search not fully implemented")
        return None
    
    def check_order_status(self, order_id: str) -> Optional[str]:
        """Check status of an order
        
        Args:
            order_id: Order ID from place_calendar_spread
            
        Returns:
            Order status or None
        """
        try:
            response = self.session.get(f"{self.base_url}/iserver/account/orders")
            
            if response.status_code == 200:
                orders = response.json()
                for order in orders:
                    if str(order.get('orderId')) == str(order_id):
                        return order.get('status')
            return None
            
        except Exception as e:
            logger.error(f"Error checking order status: {str(e)}")
            return None


class TradingScheduler:
    """Handles scheduled execution of trades"""
    
    def __init__(self, ib_client: IBAPIClient):
        """Initialize trading scheduler
        
        Args:
            ib_client: IBAPIClient instance
        """
        self.ib_client = ib_client
        self.scheduled_trades = []
        
    def schedule_earnings_trades(self, earnings_date: str, trades: List[CalendarSpreadOrder]):
        """Schedule trades for 15 minutes before market close
        
        Args:
            earnings_date: Date of earnings (YYYY-MM-DD)
            trades: List of calendar spread orders to execute
        """
        # Schedule for 3:45 PM ET (15 minutes before close)
        schedule_time = "15:45"  # 3:45 PM in 24-hour format
        
        # Add to scheduled trades
        self.scheduled_trades.append({
            'date': earnings_date,
            'time': schedule_time,
            'trades': trades
        })
        
        logger.info(f"Scheduled {len(trades)} trades for {earnings_date} at {schedule_time} ET")
        
        # Schedule the job
        schedule.every().day.at(schedule_time).do(self._execute_scheduled_trades, earnings_date)
    
    def _execute_scheduled_trades(self, earnings_date: str):
        """Execute scheduled trades for a specific date
        
        Args:
            earnings_date: Date to execute trades for
        """
        # Find trades for this date
        for scheduled in self.scheduled_trades:
            if scheduled['date'] == earnings_date:
                logger.info(f"Executing {len(scheduled['trades'])} trades for {earnings_date}")
                
                for trade in scheduled['trades']:
                    order_id = self.ib_client.place_calendar_spread(trade)
                    if order_id:
                        logger.info(f"Successfully placed order {order_id} for {trade.symbol}")
                    else:
                        logger.error(f"Failed to place order for {trade.symbol}")
                
                # Remove from scheduled trades
                self.scheduled_trades.remove(scheduled)
                break
    
    def run_scheduler(self):
        """Run the scheduler loop"""
        logger.info("Starting trading scheduler...")
        while True:
            schedule.run_pending()
            time_module.sleep(60)  # Check every minute


def main():
    """Main function for testing"""
    # Initialize client
    client = IBAPIClient(paper_trading=True)
    
    # Authenticate
    if client.authenticate():
        logger.info("Authentication successful")
        
        # Get account info
        account_info = client.get_account_info()
        if account_info:
            logger.info(f"Account info: {json.dumps(account_info, indent=2)}")
        
        # Example: Create a calendar spread order
        example_spread = CalendarSpreadOrder(
            symbol="AAPL",
            strike=190.0,
            front_expiry="20250207",  # Feb 7, 2025
            back_expiry="20250307",    # Mar 7, 2025
            option_type="CALL",
            quantity=10
        )
        
        # Schedule for execution
        scheduler = TradingScheduler(client)
        scheduler.schedule_earnings_trades("2025-02-06", [example_spread])
        
        # For testing, you can execute immediately instead of waiting
        # order_id = client.place_calendar_spread(example_spread)
        # if order_id:
        #     logger.info(f"Order placed: {order_id}")
        
    else:
        logger.error("Authentication failed. Please log in to Client Portal Gateway at https://localhost:5001")


if __name__ == "__main__":
    main()