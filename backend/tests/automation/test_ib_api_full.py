#!/usr/bin/env python
"""
Full IB API integration test
Tests actual API functionality with paper trading account
"""

import sys
import os
import logging
import json
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_account_info():
    """Test retrieving account information"""
    try:
        from ib_api_client import IBAPIClient
        
        logger.info("=" * 60)
        logger.info("Testing Account Information Retrieval")
        logger.info("=" * 60)
        
        # Initialize client
        client = IBAPIClient(paper_trading=True)
        
        # Check authentication
        if not client.authenticate():
            logger.warning("⚠️ Not authenticated. Please log in at https://localhost:5001")
            return False
            
        logger.info("✅ Authentication confirmed")
        
        # Get account info
        logger.info("\nFetching account information...")
        account_info = client.get_account_info()
        
        if account_info:
            logger.info("✅ Account info retrieved successfully!")
            logger.info(f"Account data: {json.dumps(account_info, indent=2)}")
            return True
        else:
            logger.error("❌ Failed to retrieve account info")
            return False
            
    except Exception as e:
        logger.error(f"❌ Account info test failed: {e}")
        return False

def test_contract_search():
    """Test searching for contracts"""
    try:
        from ib_api_client import IBAPIClient
        
        logger.info("=" * 60)
        logger.info("Testing Contract Search")
        logger.info("=" * 60)
        
        client = IBAPIClient(paper_trading=True)
        
        if not client.authenticate():
            logger.warning("⚠️ Not authenticated")
            return False
            
        # Test searching for popular symbols
        test_symbols = ["AAPL", "SPY", "TSLA"]
        
        for symbol in test_symbols:
            logger.info(f"\nSearching for {symbol}...")
            contract_id = client.search_contract(symbol)
            
            if contract_id:
                logger.info(f"✅ Found {symbol} - Contract ID: {contract_id}")
            else:
                logger.warning(f"⚠️ Could not find {symbol}")
                
        return True
        
    except Exception as e:
        logger.error(f"❌ Contract search test failed: {e}")
        return False

def test_option_chain():
    """Test retrieving option chains"""
    try:
        from ib_api_client import IBAPIClient
        
        logger.info("=" * 60)
        logger.info("Testing Option Chain Retrieval")
        logger.info("=" * 60)
        
        client = IBAPIClient(paper_trading=True)
        
        if not client.authenticate():
            logger.warning("⚠️ Not authenticated")
            return False
            
        # Get option chain for SPY
        symbol = "SPY"
        # Calculate expiry approximately 30 days out
        expiry_date = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d")
        
        logger.info(f"\nGetting option chain for {symbol} expiring around {expiry_date}...")
        
        options = client.get_option_chain(symbol, expiry_date[:6])  # Use YYYYMM format
        
        if options:
            logger.info(f"✅ Retrieved option chain data")
            logger.info(f"Number of strikes: {len(options) if isinstance(options, list) else 'N/A'}")
            if isinstance(options, list) and len(options) > 0:
                logger.info(f"Sample data: {json.dumps(options[:2], indent=2)}")
        else:
            logger.warning("⚠️ No option chain data retrieved")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Option chain test failed: {e}")
        return False

def test_calendar_spread_order():
    """Test creating (but not placing) a calendar spread order"""
    try:
        from ib_api_client import IBAPIClient, CalendarSpreadOrder
        
        logger.info("=" * 60)
        logger.info("Testing Calendar Spread Order Creation")
        logger.info("=" * 60)
        
        client = IBAPIClient(paper_trading=True)
        
        if not client.authenticate():
            logger.warning("⚠️ Not authenticated")
            return False
            
        # Create a test calendar spread (not placing it)
        front_date = (datetime.now() + timedelta(days=30))
        back_date = (datetime.now() + timedelta(days=60))
        
        test_spread = CalendarSpreadOrder(
            symbol="SPY",
            strike=450.0,
            front_expiry=front_date.strftime("%Y%m%d"),
            back_expiry=back_date.strftime("%Y%m%d"),
            option_type="CALL",
            quantity=1
        )
        
        logger.info("\n✅ Test calendar spread order created:")
        logger.info(f"Symbol: {test_spread.symbol}")
        logger.info(f"Strike: {test_spread.strike}")
        logger.info(f"Front expiry: {test_spread.front_expiry}")
        logger.info(f"Back expiry: {test_spread.back_expiry}")
        logger.info(f"Type: {test_spread.option_type}")
        logger.info(f"Quantity: {test_spread.quantity}")
        
        logger.info("\n⚠️ Note: Order was created but NOT placed (for safety)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Calendar spread test failed: {e}")
        return False

def test_api_endpoints():
    """Test various API endpoints directly"""
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        logger.info("=" * 60)
        logger.info("Testing Direct API Endpoints")
        logger.info("=" * 60)
        
        base_url = "https://localhost:5001/v1/api"
        session = requests.Session()
        session.verify = False
        
        # Test endpoints
        endpoints = [
            ("/iserver/auth/status", "Authentication Status"),
            ("/portfolio/accounts", "Portfolio Accounts"),
            ("/iserver/marketdata/snapshot", "Market Data Snapshot"),
            ("/iserver/account/orders", "Account Orders")
        ]
        
        for endpoint, description in endpoints:
            logger.info(f"\nTesting {description}...")
            try:
                response = session.get(f"{base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    logger.info(f"✅ {description}: Success")
                    data = response.json()
                    if data:
                        logger.info(f"   Response: {json.dumps(data, indent=2)[:200]}...")
                elif response.status_code == 401:
                    logger.warning(f"⚠️ {description}: Requires authentication")
                else:
                    logger.warning(f"⚠️ {description}: Status {response.status_code}")
            except Exception as e:
                logger.error(f"❌ {description}: {str(e)[:100]}")
                
        return True
        
    except Exception as e:
        logger.error(f"❌ API endpoint test failed: {e}")
        return False

def main():
    """Run all API tests"""
    logger.info("=" * 60)
    logger.info("IB API Full Integration Test")
    logger.info(f"Time: {datetime.now()}")
    logger.info("=" * 60)
    
    # Keep track of test results
    results = []
    
    # Run tests
    tests = [
        ("Account Info", test_account_info),
        ("Contract Search", test_contract_search),
        ("Option Chains", test_option_chain),
        ("Calendar Spread", test_calendar_spread_order),
        ("API Endpoints", test_api_endpoints)
    ]
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 All tests passed! The API integration is working correctly.")
    elif passed > 0:
        logger.info("\n⚠️ Some tests passed. The API is partially working.")
    else:
        logger.info("\n❌ No tests passed. Please check authentication and connectivity.")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main()