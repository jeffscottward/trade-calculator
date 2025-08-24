"""
Automated earnings volatility trading system.
"""

from .earnings_scanner import EarningsScanner
from .trade_executor import IBTradeExecutor
from .position_manager import PositionManager
from .risk_monitor import RiskMonitor

__version__ = "1.0.0"
__all__ = [
    'EarningsScanner',
    'IBTradeExecutor',
    'PositionManager',
    'RiskMonitor'
]