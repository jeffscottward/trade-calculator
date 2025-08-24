#!/usr/bin/env python
"""
Simple IB API connection test
Tests basic connectivity to Interactive Brokers
"""

import logging
import time
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_tws_connection():
    """Test basic TWS API connection"""
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
        from ibapi.contract import Contract
        
        class TestApp(EWrapper, EClient):
            def __init__(self):
                EClient.__init__(self, self)
                self.connected = False
                
            def error(self, reqId, errorCode, errorString):
                logger.error(f"Error {errorCode}: {errorString}")
                if errorCode == 502:
                    logger.error("Cannot connect to TWS/Gateway")
                    self.connected = False
                    
            def nextValidId(self, orderId):
                self.connected = True
                logger.info(f"✅ Connected! Next order ID: {orderId}")
                
        app = TestApp()
        
        # Try to connect to paper trading port
        logger.info("Attempting to connect to IB Gateway/TWS on port 7497 (paper trading)...")
        app.connect("127.0.0.1", 7497, clientId=1)
        
        # Run for a few seconds to test connection
        import threading
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        
        # Wait for connection
        time.sleep(5)
        
        if app.connected:
            logger.info("✅ Successfully connected to Interactive Brokers!")
            app.disconnect()
            return True
        else:
            logger.warning("⚠️ Could not connect to TWS/Gateway")
            logger.info("Please ensure TWS or IB Gateway is running on port 7497")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def test_client_portal():
    """Test Client Portal API connection"""
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        logger.info("\nTesting Client Portal Gateway on port 5001...")
        
        # Try to reach the API
        response = requests.get("https://localhost:5001/v1/api/iserver/auth/status", verify=False, timeout=2)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('authenticated'):
                logger.info("✅ Client Portal is running and authenticated!")
            else:
                logger.info("✅ Client Portal is running but needs authentication")
                logger.info("Please log in at https://localhost:5001")
            return True
        elif response.status_code == 401:
            logger.info("✅ Client Portal is running but needs authentication")
            logger.info("Please log in at https://localhost:5001")
            logger.info("Check .env file for IB_BROWSER_USERNAME for web login")
            logger.info("After login, you should see 'Client login succeeds'")
            return True
        else:
            logger.warning(f"Client Portal returned status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.warning("⚠️ Client Portal Gateway is not running")
        logger.info("Start it from clientportal.gw/bin directory with ./run.sh")
        return False
    except Exception as e:
        logger.error(f"❌ Client Portal test failed: {e}")
        return False

def main():
    logger.info("=" * 60)
    logger.info("Interactive Brokers Connection Test")
    logger.info(f"Time: {datetime.now()}")
    logger.info("=" * 60)
    
    # Test TWS/Gateway connection
    tws_ok = test_tws_connection()
    
    # Test Client Portal connection
    cp_ok = test_client_portal()
    
    logger.info("\n" + "=" * 60)
    logger.info("Test Results:")
    logger.info(f"TWS/Gateway: {'✅ Connected' if tws_ok else '❌ Not Connected'}")
    logger.info(f"Client Portal: {'✅ Running' if cp_ok else '❌ Not Running'}")
    
    if not tws_ok and not cp_ok:
        logger.info("\n📋 Next Steps:")
        logger.info("1. Download IB Gateway from Interactive Brokers website")
        logger.info("2. Log in with your IB credentials")
        logger.info("3. Configure API settings in IB Gateway:")
        logger.info("   - Enable API connections")
        logger.info("   - Set port to 7497 for paper trading")
        logger.info("   - Allow connections from 127.0.0.1")
        logger.info("4. Run this test again")
    elif cp_ok and not tws_ok:
        logger.info("\n📋 Client Portal is running!")
        logger.info("Log in at https://localhost:5001 with credentials from .env")
        logger.info("After login, API will use paper account: DUM451177")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main()