#!/usr/bin/env python
"""
Test placing a REAL paper trade with Interactive Brokers
This will actually place an order in your paper trading account!
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import time

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def place_test_calendar_spread():
    """Place a real calendar spread in the paper account"""
    try:
        from automation.ib_api_client import IBAPIClient, CalendarSpreadOrder
        
        logger.info("=" * 60)
        logger.info("REAL Paper Trade Test - Calendar Spread")
        logger.info("=" * 60)
        logger.info("⚠️ WARNING: This will place a REAL order in your paper account!")
        logger.info("")
        
        # Initialize client
        client = IBAPIClient(paper_trading=True)
        
        # Check authentication
        if not client.authenticate():
            logger.error("❌ Not authenticated. Please log in at https://localhost:5001")
            return False
        
        logger.info("✅ Authenticated successfully")
        
        # Create a small, conservative test order
        # Using SPY with ATM strike and small size
        test_order = CalendarSpreadOrder(
            symbol="SPY",
            strike=560.0,  # Approximately ATM for SPY
            front_expiry="20250922",  # ~30 days out
            back_expiry="20251022",   # ~60 days out
            option_type="CALL",
            quantity=1,  # Just 1 spread for testing
            order_type="MKT"  # Market order for immediate fill
        )
        
        logger.info("\n📋 Order Details:")
        logger.info(f"Symbol: {test_order.symbol}")
        logger.info(f"Strike: ${test_order.strike}")
        logger.info(f"Front Expiry: {test_order.front_expiry}")
        logger.info(f"Back Expiry: {test_order.back_expiry}")
        logger.info(f"Type: {test_order.option_type}")
        logger.info(f"Quantity: {test_order.quantity} spread(s)")
        logger.info(f"Order Type: {test_order.order_type}")
        
        # Confirmation
        logger.info("\n" + "=" * 40)
        response = input("Do you want to place this order? (yes/no): ")
        
        if response.lower() != 'yes':
            logger.info("❌ Order cancelled by user")
            return False
        
        logger.info("\n🚀 Placing order...")
        
        # Place the order
        order_id = client.place_calendar_spread(test_order)
        
        if order_id:
            logger.info(f"✅ Order placed successfully!")
            logger.info(f"Order ID: {order_id}")
            
            # Wait a moment for order to process
            time.sleep(3)
            
            # Check order status
            logger.info("\nChecking order status...")
            status = client.check_order_status(order_id)
            
            if status:
                logger.info(f"Order Status: {status}")
            else:
                logger.info("Could not retrieve order status")
            
            logger.info("\n✅ Test complete!")
            logger.info("Check your IB account to see the order")
            logger.info("The order can be cancelled from IB if needed")
            
            return True
        else:
            logger.error("❌ Failed to place order")
            logger.info("This might be because:")
            logger.info("1. The option contract lookup is not fully implemented")
            logger.info("2. Market is closed")
            logger.info("3. Invalid strike or expiry")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error placing trade: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_account_orders():
    """Check current orders in the account"""
    try:
        import requests
        import urllib3
        import json
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        logger.info("\n" + "=" * 60)
        logger.info("Checking Account Orders")
        logger.info("=" * 60)
        
        session = requests.Session()
        session.verify = False
        
        response = session.get("https://localhost:5001/v1/api/iserver/account/orders")
        
        if response.status_code == 200:
            data = response.json()
            orders = data.get('orders', [])
            
            if orders:
                logger.info(f"Found {len(orders)} order(s):")
                for order in orders:
                    logger.info(f"\nOrder ID: {order.get('orderId')}")
                    logger.info(f"Symbol: {order.get('ticker')}")
                    logger.info(f"Status: {order.get('status')}")
                    logger.info(f"Size: {order.get('size')}")
                    logger.info(f"Price: {order.get('price')}")
            else:
                logger.info("No open orders found")
                
            return True
        else:
            logger.error(f"Failed to get orders: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking orders: {e}")
        return False

def main():
    """Main test function"""
    logger.info("Interactive Brokers Paper Trading Test")
    logger.info("=" * 60)
    
    # First check existing orders
    logger.info("Checking existing orders...")
    check_account_orders()
    
    # Ask if user wants to place a test trade
    logger.info("\n" + "=" * 60)
    logger.info("Ready to place a test calendar spread")
    logger.info("This will place a REAL order in your paper account")
    logger.info("The order will be for 1 SPY calendar spread")
    logger.info("=" * 60)
    
    response = input("\nProceed with test trade? (yes/no): ")
    
    if response.lower() == 'yes':
        success = place_test_calendar_spread()
        
        if success:
            # Check orders again to see our new order
            logger.info("\nChecking orders after placement...")
            check_account_orders()
    else:
        logger.info("Test cancelled")
    
    logger.info("\n" + "=" * 60)
    logger.info("Test complete")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()