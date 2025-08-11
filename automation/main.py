"""
Main orchestrator for the automated trading system.
Coordinates all components and can be run via cron.
"""

import sys
import logging
from datetime import datetime
import argparse

from earnings_scanner import EarningsScanner
from trade_executor import IBTradeExecutor
from position_manager import PositionManager
from risk_monitor import RiskMonitor
from database.db_manager import DatabaseManager
from utils.notifications import send_notification, send_daily_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TradingSystemOrchestrator:
    """Main orchestrator for the automated trading system."""
    
    def __init__(self):
        self.scanner = EarningsScanner()
        self.executor = IBTradeExecutor()
        self.position_manager = PositionManager()
        self.risk_monitor = RiskMonitor()
        self.db = DatabaseManager()
    
    def run_daily_scan(self):
        """Run the daily earnings scan (3 PM ET)."""
        logger.info("="*60)
        logger.info("Starting daily earnings scan")
        logger.info("="*60)
        
        # Check if trading is allowed
        if not self.risk_monitor.is_trading_allowed():
            logger.warning("Trading is blocked by risk management")
            send_notification(
                "Scan Skipped",
                "Daily scan skipped - trading blocked by risk management"
            )
            return
        
        # Run the scan
        qualified_trades = self.scanner.scan_and_store()
        
        # Send notification
        if qualified_trades:
            message = f"Found {len(qualified_trades)} qualified trades:\n\n"
            for trade in qualified_trades:
                message += f"• {trade['symbol']} - {trade['recommendation']}\n"
            
            send_notification("Daily Scan Complete", message)
        else:
            send_notification("Daily Scan Complete", "No qualified trades found")
        
        logger.info("Daily scan complete")
    
    def enter_positions(self):
        """Enter positions (3:45 PM ET)."""
        logger.info("="*60)
        logger.info("Starting position entry")
        logger.info("="*60)
        
        # Check if in entry window
        if not self.position_manager.is_entry_window():
            logger.info("Not in entry window")
            return
        
        # Check risk limits
        if not self.risk_monitor.is_trading_allowed():
            logger.warning("Trading blocked by risk management")
            return
        
        # Enter positions
        trades = self.position_manager.enter_positions()
        
        logger.info(f"Entered {len(trades)} positions")
    
    def exit_positions(self):
        """Exit positions (9:45 AM ET)."""
        logger.info("="*60)
        logger.info("Starting position exit")
        logger.info("="*60)
        
        # Check if in exit window
        if not self.position_manager.is_exit_window():
            logger.info("Not in exit window")
            return
        
        # Exit positions
        closed = self.position_manager.exit_positions()
        
        logger.info(f"Closed {len(closed)} positions")
    
    def generate_daily_report(self):
        """Generate and send daily performance report."""
        logger.info("Generating daily report")
        
        # Get performance metrics
        metrics = self.db.get_performance_metrics(1)
        
        # Add additional metrics
        metrics['date'] = datetime.now().strftime('%Y-%m-%d')
        metrics['sharpe_ratio'] = self.risk_monitor.calculate_sharpe_ratio(30)
        
        drawdown = self.risk_monitor.calculate_drawdown(30)
        metrics['max_drawdown'] = drawdown['max_drawdown']
        
        # Send report
        send_daily_report(metrics)
        
        # Log risk report
        risk_report = self.risk_monitor.get_risk_report()
        logger.info(f"\n{risk_report}")
    
    def health_check(self):
        """Perform system health check."""
        checks = {
            'database': self._check_database(),
            'ib_connection': self._check_ib_connection(),
            'risk_limits': self.risk_monitor.is_trading_allowed()
        }
        
        all_ok = all(checks.values())
        
        status = "✅ All systems operational" if all_ok else "⚠️ Issues detected"
        
        message = f"System Health Check\n{'-'*30}\n"
        for component, status in checks.items():
            emoji = "✅" if status else "❌"
            message += f"{emoji} {component}: {'OK' if status else 'FAILED'}\n"
        
        logger.info(message)
        
        if not all_ok:
            send_notification("Health Check Failed", message)
        
        return all_ok
    
    def _check_database(self) -> bool:
        """Check database connectivity."""
        try:
            self.db.execute_query("SELECT 1")
            return True
        except:
            return False
    
    def _check_ib_connection(self) -> bool:
        """Check IB connection."""
        try:
            connected = self.executor.connect_to_ib()
            if connected:
                self.executor.disconnect()
            return connected
        except:
            return False


def main():
    """Main entry point for the trading system."""
    parser = argparse.ArgumentParser(description='Automated Trading System')
    parser.add_argument('--action', choices=['scan', 'enter', 'exit', 'report', 'health'],
                       help='Action to perform')
    parser.add_argument('--init-db', action='store_true',
                       help='Initialize database schema')
    
    args = parser.parse_args()
    
    # Initialize database if requested
    if args.init_db:
        from database.init_db import init_database
        if init_database():
            print("Database initialized successfully")
        else:
            print("Failed to initialize database")
        return
    
    # Create orchestrator
    orchestrator = TradingSystemOrchestrator()
    
    # Perform requested action
    if args.action == 'scan':
        orchestrator.run_daily_scan()
    elif args.action == 'enter':
        orchestrator.enter_positions()
    elif args.action == 'exit':
        orchestrator.exit_positions()
    elif args.action == 'report':
        orchestrator.generate_daily_report()
    elif args.action == 'health':
        orchestrator.health_check()
    else:
        # Default: determine action based on time
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        
        if current_hour == 15 and 0 <= current_minute < 15:
            orchestrator.run_daily_scan()
        elif current_hour == 15 and 45 <= current_minute < 60:
            orchestrator.enter_positions()
        elif current_hour == 9 and 45 <= current_minute < 60:
            orchestrator.exit_positions()
        elif current_hour == 18:
            orchestrator.generate_daily_report()
        else:
            logger.info("No scheduled action at this time")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("System stopped by user")
    except Exception as e:
        logger.error(f"System error: {e}", exc_info=True)
        from utils.notifications import send_error_alert
        send_error_alert("System Crash", str(e))