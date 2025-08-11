"""
Position manager for automated entry and exit timing.
Handles the 15-minute windows before close and after open.
"""

import logging
from datetime import datetime, time, timedelta
import pytz
from typing import List, Dict, Optional

from database.db_manager import DatabaseManager
from trade_executor import IBTradeExecutor
from config import TRADING_HOURS, STRATEGY_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PositionManager:
    """Manages position entry and exit timing."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.executor = IBTradeExecutor()
        self.timezone = pytz.timezone(TRADING_HOURS['timezone'])
        
    def get_current_market_time(self) -> datetime:
        """Get current time in market timezone."""
        return datetime.now(self.timezone)
    
    def is_entry_window(self) -> bool:
        """Check if we're in the 15-minute entry window before close."""
        current_time = self.get_current_market_time()
        
        # Parse market close time
        close_hour, close_minute = map(int, TRADING_HOURS['market_close'].split(':'))
        market_close = current_time.replace(hour=close_hour, minute=close_minute, second=0)
        
        # Entry window is 15 minutes before close
        entry_start = market_close - timedelta(minutes=STRATEGY_CONFIG['entry_minutes_before_close'])
        
        return entry_start <= current_time <= market_close
    
    def is_exit_window(self) -> bool:
        """Check if we're in the 15-minute exit window after open."""
        current_time = self.get_current_market_time()
        
        # Parse market open time
        open_hour, open_minute = map(int, TRADING_HOURS['market_open'].split(':'))
        market_open = current_time.replace(hour=open_hour, minute=open_minute, second=0)
        
        # Exit window is 15 minutes after open
        exit_end = market_open + timedelta(minutes=STRATEGY_CONFIG['exit_minutes_after_open'])
        
        return market_open <= current_time <= exit_end
    
    def enter_positions(self) -> List[Dict]:
        """Enter positions for today's earnings events."""
        if not self.is_entry_window():
            logger.info("Not in entry window")
            return []
        
        logger.info("Entry window active - placing trades")
        
        # Connect to IB
        if not self.executor.connect_to_ib():
            logger.error("Failed to connect to IB")
            return []
        
        # Execute recommended trades
        executed_trades = self.executor.execute_recommended_trades()
        
        # Log results
        if executed_trades:
            logger.info(f"Entered {len(executed_trades)} positions")
            
            # Send notification
            self.send_entry_notification(executed_trades)
        else:
            logger.info("No positions entered")
        
        return executed_trades
    
    def exit_positions(self) -> List[Dict]:
        """Exit positions from yesterday's earnings events."""
        if not self.is_exit_window():
            logger.info("Not in exit window")
            return []
        
        logger.info("Exit window active - closing positions")
        
        # Get open trades from yesterday's earnings
        yesterday = (datetime.now() - timedelta(days=1)).date()
        
        query = """
            SELECT t.*, e.symbol, e.earnings_date
            FROM trades t
            JOIN earnings_events e ON t.earnings_event_id = e.id
            WHERE t.status = 'open'
            AND DATE(e.earnings_date) = %s
        """
        
        open_trades = self.db.execute_query(query, (yesterday,))
        
        if not open_trades:
            logger.info("No positions to exit")
            return []
        
        # Connect to IB
        if not self.executor.connect_to_ib():
            logger.error("Failed to connect to IB")
            return []
        
        closed_positions = []
        
        for trade in open_trades:
            try:
                # Close the position
                # Note: In production, this would reverse the calendar spread
                exit_price = self.get_exit_price(trade['symbol'], trade['ib_order_id'])
                
                if exit_price:
                    # Calculate P&L
                    entry_price = float(trade['entry_price'])
                    contracts = trade['contracts']
                    pnl = (exit_price - entry_price) * contracts * 100
                    
                    # Update database
                    self.db.update_trade_exit(
                        trade_id=trade['id'],
                        exit_price=exit_price,
                        pnl=pnl
                    )
                    
                    closed_positions.append({
                        'symbol': trade['symbol'],
                        'pnl': pnl,
                        'exit_price': exit_price
                    })
                    
                    logger.info(f"Closed {trade['symbol']}: P&L ${pnl:.2f}")
                    
            except Exception as e:
                logger.error(f"Failed to close position for {trade['symbol']}: {e}")
        
        # Send exit notification
        if closed_positions:
            self.send_exit_notification(closed_positions)
        
        # Update performance metrics
        self.db.update_performance_metrics()
        
        return closed_positions
    
    def get_exit_price(self, symbol: str, ib_order_id: str) -> Optional[float]:
        """Get the current price for exiting a position."""
        # In production, this would get the actual market price from IB
        # For now, simulate with a small profit
        import random
        base_price = 3.50
        movement = random.uniform(-0.5, 1.0)  # Simulate price movement
        return base_price + movement
    
    def send_entry_notification(self, trades: List[Dict]):
        """Send notification about entered positions."""
        from utils.notifications import send_notification
        
        message = f"📈 Entered {len(trades)} positions:\n"
        for trade in trades:
            message += f"- {trade['symbol']}: {trade['contracts']} contracts\n"
        
        send_notification("Positions Entered", message)
    
    def send_exit_notification(self, positions: List[Dict]):
        """Send notification about closed positions."""
        from utils.notifications import send_notification
        
        total_pnl = sum(p['pnl'] for p in positions)
        winners = len([p for p in positions if p['pnl'] > 0])
        
        message = f"📊 Closed {len(positions)} positions:\n"
        message += f"Total P&L: ${total_pnl:,.2f}\n"
        message += f"Win Rate: {winners}/{len(positions)} ({winners/len(positions)*100:.1f}%)\n\n"
        
        for pos in positions:
            emoji = "✅" if pos['pnl'] > 0 else "❌"
            message += f"{emoji} {pos['symbol']}: ${pos['pnl']:.2f}\n"
        
        send_notification("Positions Closed", message)
    
    def monitor_positions(self):
        """Continuous monitoring of positions."""
        logger.info("Position monitor started")
        
        while True:
            try:
                current_time = self.get_current_market_time()
                
                # Check if market is open
                if not self.is_market_open():
                    logger.debug("Market closed")
                    time.sleep(60)
                    continue
                
                # Check for entry window
                if self.is_entry_window():
                    self.enter_positions()
                    # Wait until after close
                    time.sleep(900)  # 15 minutes
                
                # Check for exit window
                if self.is_exit_window():
                    self.exit_positions()
                    # Wait until after exit window
                    time.sleep(900)  # 15 minutes
                
                # Sleep for a minute before next check
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("Position monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(60)
    
    def is_market_open(self) -> bool:
        """Check if market is currently open."""
        current_time = self.get_current_market_time()
        
        # Check if weekend
        if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Parse market hours
        open_hour, open_minute = map(int, TRADING_HOURS['market_open'].split(':'))
        close_hour, close_minute = map(int, TRADING_HOURS['market_close'].split(':'))
        
        market_open = current_time.replace(hour=open_hour, minute=open_minute, second=0)
        market_close = current_time.replace(hour=close_hour, minute=close_minute, second=0)
        
        return market_open <= current_time <= market_close


def main():
    """Main function to run position manager."""
    manager = PositionManager()
    
    # Check current window
    if manager.is_entry_window():
        print("🔔 Entry window is active")
        trades = manager.enter_positions()
        print(f"Entered {len(trades)} positions")
        
    elif manager.is_exit_window():
        print("🔔 Exit window is active")
        positions = manager.exit_positions()
        print(f"Closed {len(positions)} positions")
        
    else:
        print("⏰ Outside trading windows")
        print(f"Current market time: {manager.get_current_market_time()}")


if __name__ == "__main__":
    import time
    main()