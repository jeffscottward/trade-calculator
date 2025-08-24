"""
Risk management system that monitors portfolio exposure and enforces limits.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np

from database.db_manager import DatabaseManager
from config import RISK_CONFIG, STRATEGY_CONFIG
from utils.notifications import send_alert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskMonitor:
    """Monitors and enforces risk management rules."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.risk_config = RISK_CONFIG
        self.emergency_stop = False
        
    def check_all_limits(self) -> Dict[str, Dict]:
        """Perform comprehensive risk check."""
        checks = {
            'position_limits': self.check_position_limits(),
            'loss_limits': self.check_loss_limits(),
            'exposure_limits': self.check_exposure_limits(),
            'consecutive_losses': self.check_consecutive_losses()
        }
        
        # Set emergency stop if critical limits breached
        critical_breaches = []
        
        if not checks['loss_limits']['daily_loss_ok']:
            critical_breaches.append("Daily loss limit exceeded")
        
        if not checks['consecutive_losses']['ok']:
            critical_breaches.append("Max consecutive losses reached")
        
        if checks['loss_limits'].get('emergency_stop_triggered', False):
            critical_breaches.append("Emergency stop loss triggered")
        
        if critical_breaches:
            self.trigger_emergency_stop(critical_breaches)
        
        return checks
    
    def check_position_limits(self) -> Dict:
        """Check position count limits."""
        open_trades = self.db.get_open_trades()
        
        return {
            'current_positions': len(open_trades),
            'max_positions': STRATEGY_CONFIG['max_concurrent_positions'],
            'ok': len(open_trades) < STRATEGY_CONFIG['max_concurrent_positions'],
            'available_slots': STRATEGY_CONFIG['max_concurrent_positions'] - len(open_trades)
        }
    
    def check_loss_limits(self) -> Dict:
        """Check daily and total loss limits."""
        # Get today's closed trades
        query = """
            SELECT SUM(pnl) as daily_pnl, COUNT(*) as trade_count
            FROM trades
            WHERE DATE(exit_time) = CURRENT_DATE
            AND status = 'closed'
        """
        
        result = self.db.execute_query(query)
        daily_pnl = result[0]['daily_pnl'] if result and result[0]['daily_pnl'] else 0
        
        # Calculate as percentage (assuming $100k account for now)
        account_value = 100000
        daily_loss_pct = abs(daily_pnl / account_value) if daily_pnl < 0 else 0
        
        # Check emergency stop
        emergency_triggered = daily_loss_pct > self.risk_config['emergency_stop_loss_pct']
        
        return {
            'daily_pnl': daily_pnl,
            'daily_loss_pct': daily_loss_pct,
            'max_daily_loss_pct': self.risk_config['max_daily_loss_pct'],
            'daily_loss_ok': daily_loss_pct < self.risk_config['max_daily_loss_pct'],
            'emergency_stop_triggered': emergency_triggered
        }
    
    def check_exposure_limits(self) -> Dict:
        """Check total portfolio exposure."""
        # Get all open positions
        open_trades = self.db.get_open_trades()
        
        # Calculate total exposure
        total_exposure = 0
        account_value = 100000  # Placeholder
        
        for trade in open_trades:
            # Estimate position value
            position_value = float(trade['entry_price']) * trade['contracts'] * 100
            total_exposure += position_value
        
        exposure_pct = total_exposure / account_value if account_value > 0 else 0
        
        return {
            'total_exposure': total_exposure,
            'exposure_pct': exposure_pct,
            'max_exposure_pct': self.risk_config['max_portfolio_exposure'],
            'ok': exposure_pct <= self.risk_config['max_portfolio_exposure']
        }
    
    def check_consecutive_losses(self) -> Dict:
        """Check for consecutive losing trades."""
        query = """
            SELECT symbol, pnl 
            FROM trades 
            WHERE status = 'closed'
            ORDER BY exit_time DESC
            LIMIT %s
        """
        
        recent_trades = self.db.execute_query(
            query, 
            (self.risk_config['max_consecutive_losses'],)
        )
        
        if not recent_trades:
            return {'consecutive_losses': 0, 'ok': True}
        
        consecutive_losses = 0
        for trade in recent_trades:
            if trade['pnl'] < 0:
                consecutive_losses += 1
            else:
                break
        
        return {
            'consecutive_losses': consecutive_losses,
            'max_allowed': self.risk_config['max_consecutive_losses'],
            'ok': consecutive_losses < self.risk_config['max_consecutive_losses'],
            'recent_trades': [(t['symbol'], float(t['pnl'])) for t in recent_trades]
        }
    
    def calculate_drawdown(self, days: int = 30) -> Dict:
        """Calculate maximum drawdown over specified period."""
        query = """
            SELECT DATE(exit_time) as date, SUM(pnl) as daily_pnl
            FROM trades
            WHERE status = 'closed'
            AND exit_time >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY DATE(exit_time)
            ORDER BY date
        """
        
        daily_pnls = self.db.execute_query(query, (days,))
        
        if not daily_pnls:
            return {'max_drawdown': 0, 'current_drawdown': 0}
        
        # Calculate cumulative returns
        cumulative = []
        total = 0
        
        for day in daily_pnls:
            total += float(day['daily_pnl'])
            cumulative.append(total)
        
        # Calculate drawdown
        peak = cumulative[0]
        max_drawdown = 0
        current_drawdown = 0
        
        for value in cumulative:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
            
            if value == cumulative[-1]:  # Current value
                current_drawdown = drawdown
        
        return {
            'max_drawdown': max_drawdown,
            'current_drawdown': current_drawdown,
            'peak_value': peak,
            'current_value': cumulative[-1] if cumulative else 0
        }
    
    def calculate_sharpe_ratio(self, days: int = 30) -> float:
        """Calculate Sharpe ratio for recent performance."""
        query = """
            SELECT pnl FROM trades
            WHERE status = 'closed'
            AND exit_time >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY exit_time
        """
        
        trades = self.db.execute_query(query, (days,))
        
        if len(trades) < 2:
            return 0.0
        
        returns = [float(t['pnl']) for t in trades]
        
        # Assume risk-free rate of 5% annually
        risk_free_daily = 0.05 / 252
        
        # Calculate excess returns
        excess_returns = [r - risk_free_daily for r in returns]
        
        # Calculate Sharpe ratio
        if np.std(excess_returns) > 0:
            sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        else:
            sharpe = 0.0
        
        return sharpe
    
    def trigger_emergency_stop(self, reasons: List[str]):
        """Trigger emergency stop to halt all trading."""
        self.emergency_stop = True
        
        message = "🚨 EMERGENCY STOP TRIGGERED 🚨\n\n"
        message += "Reasons:\n"
        for reason in reasons:
            message += f"- {reason}\n"
        
        message += "\nAll trading has been halted. Manual review required."
        
        # Send alert
        send_alert("EMERGENCY STOP", message, priority="high")
        
        # Log to database
        query = """
            INSERT INTO performance_metrics (date, total_trades, winning_trades, total_pnl, notes)
            VALUES (CURRENT_DATE, 0, 0, 0, %s)
            ON CONFLICT (date) DO UPDATE SET notes = EXCLUDED.notes
        """
        
        self.db.execute_update(query, (f"EMERGENCY STOP: {', '.join(reasons)}",))
        
        logger.critical(f"Emergency stop triggered: {reasons}")
    
    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed."""
        if self.emergency_stop:
            return False
        
        # Check all limits
        checks = self.check_all_limits()
        
        # Trading allowed if all checks pass
        for category, results in checks.items():
            if isinstance(results, dict) and 'ok' in results:
                if not results['ok']:
                    logger.warning(f"Trading blocked: {category} check failed")
                    return False
        
        return True
    
    def get_risk_report(self) -> str:
        """Generate comprehensive risk report."""
        report = "="*60 + "\n"
        report += "RISK MANAGEMENT REPORT\n"
        report += "="*60 + "\n\n"
        
        # Check all limits
        checks = self.check_all_limits()
        
        # Position limits
        pos = checks['position_limits']
        report += f"POSITION LIMITS:\n"
        report += f"  Current: {pos['current_positions']}/{pos['max_positions']}\n"
        report += f"  Status: {'✅ OK' if pos['ok'] else '❌ LIMIT REACHED'}\n\n"
        
        # Loss limits
        loss = checks['loss_limits']
        report += f"LOSS LIMITS:\n"
        report += f"  Daily P&L: ${loss['daily_pnl']:.2f}\n"
        report += f"  Daily Loss %: {loss['daily_loss_pct']:.2%}\n"
        report += f"  Max Allowed: {loss['max_daily_loss_pct']:.2%}\n"
        report += f"  Status: {'✅ OK' if loss['daily_loss_ok'] else '❌ LIMIT EXCEEDED'}\n\n"
        
        # Exposure
        exp = checks['exposure_limits']
        report += f"EXPOSURE LIMITS:\n"
        report += f"  Total Exposure: ${exp['total_exposure']:,.2f}\n"
        report += f"  Exposure %: {exp['exposure_pct']:.2%}\n"
        report += f"  Max Allowed: {exp['max_exposure_pct']:.2%}\n"
        report += f"  Status: {'✅ OK' if exp['ok'] else '❌ LIMIT EXCEEDED'}\n\n"
        
        # Consecutive losses
        consec = checks['consecutive_losses']
        report += f"CONSECUTIVE LOSSES:\n"
        report += f"  Current Streak: {consec['consecutive_losses']}\n"
        report += f"  Max Allowed: {consec['max_allowed']}\n"
        report += f"  Status: {'✅ OK' if consec['ok'] else '❌ LIMIT REACHED'}\n\n"
        
        # Drawdown
        dd = self.calculate_drawdown()
        report += f"DRAWDOWN (30 days):\n"
        report += f"  Maximum: {dd['max_drawdown']:.2%}\n"
        report += f"  Current: {dd['current_drawdown']:.2%}\n\n"
        
        # Sharpe ratio
        sharpe = self.calculate_sharpe_ratio()
        report += f"SHARPE RATIO (30 days): {sharpe:.2f}\n\n"
        
        # Trading status
        report += f"TRADING STATUS: "
        if self.is_trading_allowed():
            report += "✅ ALLOWED\n"
        else:
            report += "🚨 BLOCKED\n"
        
        report += "="*60
        
        return report


def main():
    """Main function to run risk monitor."""
    monitor = RiskMonitor()
    
    # Generate and print risk report
    report = monitor.get_risk_report()
    print(report)
    
    # Check if trading is allowed
    if monitor.is_trading_allowed():
        print("\n✅ Trading is currently allowed")
    else:
        print("\n🚨 Trading is currently BLOCKED")


if __name__ == "__main__":
    main()