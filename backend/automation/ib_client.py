#!/usr/bin/env python3
"""
Interactive Brokers Client Portal API Client
Handles authentication and data fetching from IB Client Portal Gateway
"""

import os
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# Disable SSL warnings for self-signed certificate
urllib3.disable_warnings(InsecureRequestWarning)

class IBClient:
    """Client for interacting with IB Client Portal API"""
    
    def __init__(self, base_url: str = "https://localhost:5001/v1/api"):
        """
        Initialize IB Client
        
        Args:
            base_url: Base URL for IB Client Portal API
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification for self-signed cert
        self.account_id = None
        
    def get_auth_status(self) -> Dict[str, Any]:
        """Check authentication status"""
        try:
            response = self.session.get(f"{self.base_url}/iserver/auth/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error checking auth status: {e}")
            return {"authenticated": False, "error": str(e)}
    
    def reauthenticate(self) -> bool:
        """Trigger reauthentication"""
        try:
            response = self.session.post(f"{self.base_url}/iserver/reauthenticate")
            response.raise_for_status()
            result = response.json()
            
            # Wait a moment for auth to complete
            time.sleep(2)
            
            # Check auth status
            auth_status = self.get_auth_status()
            return auth_status.get('authenticated', False)
        except Exception as e:
            print(f"Error reauthenticating: {e}")
            return False
    
    def get_accounts(self) -> List[str]:
        """Get list of accounts"""
        try:
            response = self.session.get(f"{self.base_url}/portfolio/accounts")
            response.raise_for_status()
            accounts = response.json()
            if accounts and len(accounts) > 0:
                self.account_id = accounts[0]['accountId']
            return accounts
        except Exception as e:
            print(f"Error getting accounts: {e}")
            return []
    
    def search_contract(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Search for a contract by symbol
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Contract information or None
        """
        try:
            response = self.session.get(
                f"{self.base_url}/iserver/secdef/search",
                params={"symbol": symbol}
            )
            response.raise_for_status()
            data = response.json()
            
            # Return first matching stock contract
            if isinstance(data, list):
                for contract in data:
                    # Check if this contract has STK section and matches symbol
                    sections = contract.get('sections', [])
                    has_stock = any(s.get('secType') == 'STK' for s in sections)
                    
                    if (has_stock and 
                        contract.get('symbol') and 
                        contract.get('symbol').upper() == symbol.upper()):
                        return contract
                
                # Fallback to first result with STK section
                for contract in data:
                    sections = contract.get('sections', [])
                    if any(s.get('secType') == 'STK' for s in sections):
                        return contract
                        
                # Last fallback to first result
                return data[0] if data else None
            
            return None
            
        except Exception as e:
            print(f"Error searching contract for {symbol}: {e}")
            return None
    
    def get_contract_details(self, conid: str) -> Optional[Dict[str, Any]]:
        """Get detailed contract information"""
        try:
            response = self.session.get(
                f"{self.base_url}/iserver/contract/{conid}/info"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting contract details for {conid}: {e}")
            return None
    
    def get_historical_data(
        self, 
        conid: str, 
        period: str = "2w",
        bar: str = "1d",
        outside_rth: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get historical market data
        
        Args:
            conid: Contract ID
            period: Time period (1d, 1w, 2w, 1m, etc.)
            bar: Bar size (1min, 5min, 1h, 1d, etc.)
            outside_rth: Include outside regular trading hours
            
        Returns:
            Historical data or None
        """
        try:
            params = {
                "conid": conid,
                "period": period,
                "bar": bar,
                "outsideRth": outside_rth
            }
            
            response = self.session.get(
                f"{self.base_url}/iserver/marketdata/history",
                params=params
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error getting historical data for {conid}: {e}")
            return None
    
    def get_option_chain(self, symbol: str, month: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get option chain for a symbol
        
        Args:
            symbol: Stock ticker symbol
            month: Expiration month (format: YYYYMM)
            
        Returns:
            Option chain data or None
        """
        try:
            # First get the contract
            contract = self.search_contract(symbol)
            if not contract:
                print(f"Contract not found for {symbol}")
                return None
            
            conid = contract.get('conid')
            
            # Get option chains
            response = self.session.get(
                f"{self.base_url}/iserver/secdef/info",
                params={
                    "conid": conid,
                    "sectype": "OPT",
                    "month": month or "ALL"
                }
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error getting option chain for {symbol}: {e}")
            return None
    
    def get_option_strikes(self, symbol: str, expiry: str, right: str = "C") -> Optional[List[Dict[str, Any]]]:
        """
        Get available strikes for options
        
        Args:
            symbol: Stock ticker symbol
            expiry: Expiration date (YYYYMMDD)
            right: Option right (C for Call, P for Put)
            
        Returns:
            List of strikes with contract IDs
        """
        try:
            # Get base contract
            contract = self.search_contract(symbol)
            if not contract:
                return None
            
            conid = contract.get('conid')
            
            # Get strikes for specific expiry
            response = self.session.get(
                f"{self.base_url}/iserver/secdef/strikes",
                params={
                    "conid": conid,
                    "sectype": "OPT",
                    "month": expiry[:6],  # YYYYMM format
                    "exchange": "SMART"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Filter for specific expiry and right
            strikes = []
            if 'call' in data and right == 'C':
                strikes = data['call']
            elif 'put' in data and right == 'P':
                strikes = data['put']
                
            return strikes
            
        except Exception as e:
            print(f"Error getting option strikes for {symbol}: {e}")
            return None
    
    def get_market_data(self, conids: List[str], fields: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get real-time market data for contracts
        
        Args:
            conids: List of contract IDs
            fields: List of field IDs to retrieve
                    31 = Last Price
                    84 = Bid
                    85 = Ask
                    86 = Volume
                    7295 = Implied Volatility
                    
        Returns:
            Market data snapshot
        """
        if fields is None:
            fields = ["31", "84", "85", "86", "7295"]
            
        try:
            # Subscribe to market data
            response = self.session.get(
                f"{self.base_url}/iserver/marketdata/snapshot",
                params={
                    "conids": ",".join(conids),
                    "fields": ",".join(fields)
                }
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error getting market data: {e}")
            return None
    
    def get_account_summary(self) -> Optional[Dict[str, Any]]:
        """Get account summary including balances and P&L"""
        try:
            if not self.account_id:
                self.get_accounts()
            
            if not self.account_id:
                print("No account ID available")
                return None
            
            response = self.session.get(
                f"{self.base_url}/portfolio/{self.account_id}/summary"
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error getting account summary: {e}")
            return None
    
    def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """Get current positions"""
        try:
            if not self.account_id:
                self.get_accounts()
            
            if not self.account_id:
                print("No account ID available")
                return None
            
            response = self.session.get(
                f"{self.base_url}/portfolio/{self.account_id}/positions/0"
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error getting positions: {e}")
            return None
    
    def place_order(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Place an order
        
        Args:
            order: Order details dictionary
            
        Returns:
            Order response or None
        """
        try:
            if not self.account_id:
                self.get_accounts()
            
            if not self.account_id:
                print("No account ID available")
                return None
            
            # Prepare order payload
            payload = {
                "orders": [order]
            }
            
            response = self.session.post(
                f"{self.base_url}/iserver/account/{self.account_id}/orders",
                json=payload
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error placing order: {e}")
            return None


def test_connection():
    """Test IB Client Portal connection"""
    client = IBClient()
    
    print("Testing IB Client Portal Connection...")
    print("-" * 50)
    
    # Check auth status
    auth_status = client.get_auth_status()
    print(f"Initial Authentication Status: {auth_status}")
    
    # Try to reauthenticate if not authenticated
    if not auth_status.get('authenticated'):
        print("\nAttempting to reauthenticate...")
        if client.reauthenticate():
            print("Reauthentication successful!")
            auth_status = client.get_auth_status()
        else:
            print("Reauthentication failed.")
    
    if auth_status.get('authenticated'):
        # Get accounts
        accounts = client.get_accounts()
        print(f"Available Accounts: {accounts}")
        
        # Test searching for a contract
        symbol = "AAPL"
        contract = client.search_contract(symbol)
        if contract:
            print(f"\nContract found for {symbol}:")
            print(f"  Contract ID: {contract.get('conid')}")
            print(f"  Description: {contract.get('description')}")
            
            # Get historical data
            conid = contract.get('conid')
            hist_data = client.get_historical_data(conid, period="5d", bar="1d")
            if hist_data and 'data' in hist_data:
                print(f"\nHistorical Data (last 5 days):")
                for bar in hist_data['data'][-5:]:
                    print(f"  {bar.get('t')}: Close={bar.get('c')}, Volume={bar.get('v')}")
    else:
        print("Not authenticated. Please log in to the Client Portal Gateway.")
    
    return client


if __name__ == "__main__":
    test_connection()