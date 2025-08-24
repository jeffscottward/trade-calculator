"""
Interactive Brokers trade execution engine for calendar spreads.
Handles order placement, monitoring, and execution.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import threading

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import BarData

from .config import BROKER_CONFIG, STRATEGY_CONFIG, RISK_CONFIG
from .database.db_manager import DatabaseManager
from .utils.options_analysis import find_optimal_calendar_strikes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IBTradeExecutor(EWrapper, EClient):
    """Interactive Brokers trade executor for automated trading."""
    
    def __init__(self):
        EClient.__init__(self, self)
        self.db = DatabaseManager()
        self.next_order_id = None
        self.positions = {}
        self.orders = {}
        self.account_value = 0
        self.connected = False
        
    def error(self, reqId, errorCode, errorString):
        """Handle IB API errors."""
        if errorCode == 502:  # Cannot connect to TWS
            logger.error("Cannot connect to TWS/Gateway. Please ensure it's running.")
            self.connected = False
        else:
            logger.error(f"Error {errorCode}: {errorString}")
    
    def nextValidId(self, orderId):
        """Receive next valid order ID from IB."""
        self.next_order_id = orderId
        self.connected = True
        logger.info(f"Connected to IB. Next order ID: {orderId}")
    
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice,
                   permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        """Handle order status updates."""
        logger.info(f"Order {orderId} status: {status}, filled: {filled}")
        
        if orderId in self.orders:
            self.orders[orderId]['status'] = status
            self.orders[orderId]['filled'] = filled
            self.orders[orderId]['avg_fill_price'] = avgFillPrice
    
    def position(self, account, contract, position, avgCost):
        """Handle position updates."""
        key = f"{contract.symbol}_{contract.lastTradeDateOrContractMonth}"
        self.positions[key] = {
            'symbol': contract.symbol,
            'position': position,
            'avg_cost': avgCost
        }
    
    def connect_to_ib(self) -> bool:
        """Establish connection to Interactive Brokers."""
        try:
            self.connect(
                BROKER_CONFIG['host'],
                BROKER_CONFIG['port'],
                BROKER_CONFIG['client_id']
            )
            
            # Start the socket in a thread
            api_thread = threading.Thread(target=self.run, daemon=True)
            api_thread.start()
            
            # Wait for connection
            timeout = 10
            while not self.connected and timeout > 0:
                time.sleep(1)
                timeout -= 1
            
            if self.connected:
                logger.info("Successfully connected to Interactive Brokers")
                return True
            else:
                logger.error("Failed to connect to Interactive Brokers")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def create_option_contract(self, symbol: str, expiry: str, strike: float,
                              right: str = "C") -> Contract:
        """Create an option contract for IB API."""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "OPT"
        contract.exchange = "SMART"
        contract.currency = "USD"
        contract.lastTradeDateOrContractMonth = expiry.replace("-", "")
        contract.strike = strike
        contract.right = right  # "C" for call, "P" for put
        contract.multiplier = "100"
        
        return contract
    
    def create_calendar_spread_order(self, quantity: int, limit_price: float) -> Order:
        """Create a calendar spread order."""
        order = Order()
        order.action = "BUY"  # Buy the spread (buy back month, sell front month)
        order.orderType = "LMT"
        order.totalQuantity = quantity
        order.lmtPrice = limit_price
        order.transmit = True
        
        return order
    
    def place_calendar_spread(self, symbol: str, front_expiry: str,
                             back_expiry: str, strike: float,
                             quantity: int, limit_price: float) -> Optional[int]:
        """Place a calendar spread order."""
        try:
            if not self.connected:
                logger.error("Not connected to IB")
                return None
            
            # Create the combo contract for calendar spread
            combo_contract = Contract()
            combo_contract.symbol = symbol
            combo_contract.secType = "BAG"  # Combo order
            combo_contract.currency = "USD"
            combo_contract.exchange = "SMART"
            
            # Create legs
            front_leg = Contract()
            front_leg.conId = 0  # Will be determined by IB
            front_leg.symbol = symbol
            front_leg.secType = "OPT"
            front_leg.lastTradeDateOrContractMonth = front_expiry.replace("-", "")
            front_leg.strike = strike
            front_leg.right = "C"
            front_leg.exchange = "SMART"
            front_leg.currency = "USD"
            
            back_leg = Contract()
            back_leg.conId = 0  # Will be determined by IB
            back_leg.symbol = symbol
            back_leg.secType = "OPT"
            back_leg.lastTradeDateOrContractMonth = back_expiry.replace("-", "")
            back_leg.strike = strike
            back_leg.right = "C"
            back_leg.exchange = "SMART"
            back_leg.currency = "USD"
            
            # Define combo legs
            combo_contract.comboLegs = []
            
            # Sell front month (ratio = -1)
            from ibapi.order import ComboLeg
            leg1 = ComboLeg()
            leg1.conId = front_leg.conId
            leg1.ratio = 1
            leg1.action = "SELL"
            leg1.exchange = "SMART"
            
            # Buy back month (ratio = 1)
            leg2 = ComboLeg()
            leg2.conId = back_leg.conId
            leg2.ratio = 1
            leg2.action = "BUY"
            leg2.exchange = "SMART"
            
            combo_contract.comboLegs.append(leg1)
            combo_contract.comboLegs.append(leg2)
            
            # Create order
            order = self.create_calendar_spread_order(quantity, limit_price)
            
            # Place order
            order_id = self.next_order_id
            self.placeOrder(order_id, combo_contract, order)
            
            # Track order
            self.orders[order_id] = {
                'symbol': symbol,
                'type': 'calendar_spread',
                'front_expiry': front_expiry,
                'back_expiry': back_expiry,
                'strike': strike,
                'quantity': quantity,
                'limit_price': limit_price,
                'status': 'submitted',
                'timestamp': datetime.now()
            }
            
            # Increment order ID
            self.next_order_id += 1
            
            logger.info(f"Placed calendar spread order {order_id} for {symbol}")
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to place calendar spread: {e}")
            return None
    
    def execute_recommended_trades(self) -> List[Dict]:
        """Execute all recommended trades from today's scan."""
        if not self.connect_to_ib():
            logger.error("Cannot execute trades - not connected to IB")
            return []
        
        # Get today's recommendations ordered by priority score
        query = """
            SELECT * FROM earnings_events
            WHERE DATE(scan_date) = CURRENT_DATE
            AND recommendation = 'RECOMMENDED'
            AND id NOT IN (SELECT earnings_event_id FROM trades WHERE DATE(entry_time) = CURRENT_DATE)
            ORDER BY priority_score DESC, iv_rv_ratio DESC
            LIMIT 3  -- Respect max concurrent positions
        """
        recommendations = self.db.execute_query(query)
        
        if not recommendations:
            logger.info("No new recommended trades to execute")
            return []
        
        # Check risk limits before trading
        risk_checks = self.db.check_risk_limits()
        if not all(risk_checks.values()):
            logger.warning(f"Risk limits exceeded: {risk_checks}")
            return []
        
        executed_trades = []
        
        for rec in recommendations:
            try:
                symbol = rec['symbol']
                logger.info(f"Executing trade for {symbol}")
                
                # Determine position size
                position_size = self.calculate_position_size(symbol)
                if position_size == 0:
                    logger.warning(f"Position size is 0 for {symbol}, skipping")
                    continue
                
                # Find optimal strike and expiries
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                expirations = ticker.options
                
                # Find front and back month expiries
                front_expiry, back_expiry = self.find_calendar_expiries(expirations)
                
                if not front_expiry or not back_expiry:
                    logger.warning(f"Cannot find suitable expiries for {symbol}")
                    continue
                
                # Find optimal strike
                strikes = find_optimal_calendar_strikes(ticker, front_expiry, back_expiry, 3)
                if not strikes:
                    logger.warning(f"No suitable strikes found for {symbol}")
                    continue
                
                optimal_strike = strikes[0]  # Use most liquid strike
                
                # Calculate limit price (use mid price + small buffer)
                limit_price = optimal_strike['spread_price'] * 1.02
                
                # Place the trade
                order_id = self.place_calendar_spread(
                    symbol=symbol,
                    front_expiry=front_expiry,
                    back_expiry=back_expiry,
                    strike=optimal_strike['strike'],
                    quantity=position_size,
                    limit_price=limit_price
                )
                
                if order_id:
                    # Store in database
                    trade_id = self.db.insert_trade(
                        symbol=symbol,
                        earnings_event_id=rec['id'],
                        trade_type='calendar',
                        entry_price=limit_price,
                        contracts=position_size,
                        ib_order_id=str(order_id)
                    )
                    
                    executed_trades.append({
                        'trade_id': trade_id,
                        'symbol': symbol,
                        'order_id': order_id,
                        'strike': optimal_strike['strike'],
                        'contracts': position_size
                    })
                    
                    logger.info(f"✅ Executed trade for {symbol}")
                
                # Add delay between trades
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to execute trade for {rec['symbol']}: {e}")
        
        return executed_trades
    
    def calculate_position_size(self, symbol: str) -> int:
        """Calculate position size based on Kelly criterion and account value."""
        # This is simplified - in production, get actual account value from IB
        account_value = 100000  # Placeholder
        
        # Calculate position value (6% of account)
        position_value = account_value * STRATEGY_CONFIG['position_size_pct']
        
        # Estimate contract price (simplified)
        contract_price = 300  # Average calendar spread price
        
        # Calculate number of contracts
        contracts = int(position_value / (contract_price * 100))
        
        # Apply maximum position limit
        max_contracts = 10
        return min(contracts, max_contracts)
    
    def find_calendar_expiries(self, expirations: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """Find suitable front and back month expiries for calendar spread."""
        if len(expirations) < 2:
            return None, None
        
        today = datetime.now().date()
        
        # Find front month (closest expiry after earnings)
        front_expiry = None
        for exp in expirations:
            exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
            if exp_date > today:
                front_expiry = exp
                break
        
        if not front_expiry:
            return None, None
        
        # Find back month (approximately 30 days after front)
        front_date = datetime.strptime(front_expiry, '%Y-%m-%d').date()
        target_back_date = front_date + timedelta(days=STRATEGY_CONFIG['calendar_spread_gap_days'])
        
        back_expiry = None
        min_diff = float('inf')
        
        for exp in expirations:
            exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
            if exp_date > front_date:
                diff = abs((exp_date - target_back_date).days)
                if diff < min_diff:
                    min_diff = diff
                    back_expiry = exp
        
        return front_expiry, back_expiry
    
    def close_position(self, trade_id: int, ib_order_id: str):
        """Close an existing calendar spread position."""
        # Implementation for closing positions
        # This would reverse the original trade
        pass


def main():
    """Main function to execute trades."""
    executor = IBTradeExecutor()
    
    # Execute recommended trades
    executed = executor.execute_recommended_trades()
    
    if executed:
        print(f"\n✅ Executed {len(executed)} trades:")
        for trade in executed:
            print(f"  - {trade['symbol']}: {trade['contracts']} contracts at strike {trade['strike']}")
    else:
        print("\n No trades executed")
    
    # Disconnect
    if executor.connected:
        executor.disconnect()


if __name__ == "__main__":
    main()