"""
Test script for Interactive Brokers API connection
Tests both TWS API and Client Portal API connections
"""

import sys
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_client_portal_api():
    """Test IB Client Portal API connection"""
    try:
        # Add current directory to path for imports
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from ib_api_client import IBAPIClient, CalendarSpreadOrder
        
        logger.info("=" * 50)
        logger.info("Testing IB Client Portal API Connection")
        logger.info("=" * 50)
        
        # Initialize client with paper trading
        client = IBAPIClient(paper_trading=True)
        logger.info("✅ Client initialized")
        
        # Try to authenticate
        logger.info("Attempting authentication...")
        if client.authenticate():
            logger.info("✅ Authentication successful")
            
            # Get account info
            account_info = client.get_account_info()
            if account_info:
                logger.info(f"✅ Account info retrieved: {account_info}")
            else:
                logger.warning("⚠️ Could not retrieve account info")
                
            # Test creating a sample calendar spread order (not placing it)
            test_spread = CalendarSpreadOrder(
                symbol="SPY",
                strike=450.0,
                front_expiry="20250207",
                back_expiry="20250307", 
                option_type="CALL",
                quantity=1
            )
            logger.info(f"✅ Test spread order created: {test_spread}")
            
        else:
            logger.warning("⚠️ Authentication failed - Client Portal Gateway may not be running")
            logger.info("Please ensure IB Client Portal Gateway is running on port 5001")
            logger.info("Start it from clientportal.gw/bin directory with ./run.sh")
            
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.info("Make sure you're running from the automation directory")
    except Exception as e:
        logger.error(f"❌ Client Portal API test failed: {e}")

def test_tws_api():
    """Test IB TWS API connection"""
    try:
        # Add current directory to path for imports
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from trade_executor import IBTradeExecutor
        
        logger.info("=" * 50)
        logger.info("Testing IB TWS API Connection")
        logger.info("=" * 50)
        
        # Initialize executor
        executor = IBTradeExecutor()
        logger.info("✅ Trade executor initialized")
        
        # Try to connect
        logger.info("Attempting TWS connection...")
        if executor.connect_to_ib():
            logger.info("✅ Connected to TWS/Gateway")
            
            # Check if we have an order ID
            if executor.next_order_id:
                logger.info(f"✅ Next order ID: {executor.next_order_id}")
            
            # Give it a moment to receive account data
            time.sleep(2)
            
            # Disconnect
            executor.disconnect()
            logger.info("✅ Disconnected successfully")
        else:
            logger.warning("⚠️ Could not connect to TWS/Gateway")
            logger.info("Please ensure TWS or IB Gateway is running:")
            logger.info("- Paper trading: Port 7497")
            logger.info("- Live trading: Port 7496")
            
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.info("Make sure ibapi is installed: pip install ibapi")
    except Exception as e:
        logger.error(f"❌ TWS API test failed: {e}")

def main():
    """Run all connection tests"""
    logger.info("Starting Interactive Brokers API Connection Tests")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("")
    
    # Test Client Portal API first (REST API)
    test_client_portal_api()
    
    logger.info("")
    
    # Test TWS API (Socket-based)
    test_tws_api()
    
    logger.info("")
    logger.info("=" * 50)
    logger.info("Connection tests complete")
    logger.info("=" * 50)
    
    # Recommendations
    logger.info("\n📋 Recommendations:")
    logger.info("1. For automated trading, TWS API (trade_executor.py) is more robust")
    logger.info("2. Client Portal API is good for account info and simple orders")
    logger.info("3. Make sure to have either TWS or IB Gateway running")
    logger.info("4. Paper trading uses port 7497, live uses 7496")
    logger.info("5. Client Portal Gateway uses port 5001")

if __name__ == "__main__":
    main()