"""
Database manager for PostgreSQL/Neon DB operations.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

from ..config import DATABASE_CONFIG

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.config = DATABASE_CONFIG
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = psycopg2.connect(**self.config)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a SELECT query and return results."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
    
    def insert_earnings_event(self, symbol: str, earnings_date: datetime,
                             term_structure_slope: float, avg_volume_30d: int,
                             iv_rv_ratio: float, recommendation: str) -> int:
        """Insert a new earnings event and return its ID."""
        query = """
            INSERT INTO earnings_events 
            (symbol, earnings_date, scan_date, term_structure_slope, 
             avg_volume_30d, iv_rv_ratio, recommendation)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (
                    symbol, earnings_date, datetime.now(),
                    term_structure_slope, avg_volume_30d,
                    iv_rv_ratio, recommendation
                ))
                conn.commit()
                return cursor.fetchone()[0]
    
    def insert_trade(self, symbol: str, earnings_event_id: int,
                    trade_type: str, entry_price: float,
                    contracts: int, ib_order_id: str = None) -> int:
        """Insert a new trade and return its ID."""
        query = """
            INSERT INTO trades 
            (symbol, earnings_event_id, trade_type, entry_time, 
             entry_price, contracts, status, ib_order_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (
                    symbol, earnings_event_id, trade_type,
                    datetime.now(), entry_price, contracts,
                    'open', ib_order_id
                ))
                conn.commit()
                return cursor.fetchone()[0]
    
    def update_trade_exit(self, trade_id: int, exit_price: float, pnl: float):
        """Update trade with exit information."""
        query = """
            UPDATE trades 
            SET exit_time = %s, exit_price = %s, pnl = %s, status = %s
            WHERE id = %s
        """
        
        self.execute_update(query, (
            datetime.now(), exit_price, pnl, 'closed', trade_id
        ))
    
    def get_open_trades(self) -> List[Dict]:
        """Get all open trades."""
        query = """
            SELECT t.*, e.earnings_date 
            FROM trades t
            JOIN earnings_events e ON t.earnings_event_id = e.id
            WHERE t.status = 'open'
            ORDER BY e.earnings_date
        """
        return self.execute_query(query)
    
    def get_todays_trades(self) -> List[Dict]:
        """Get all trades from today."""
        query = """
            SELECT * FROM trades 
            WHERE DATE(entry_time) = CURRENT_DATE
            ORDER BY entry_time DESC
        """
        return self.execute_query(query)
    
    def get_performance_metrics(self, days: int = 30) -> Dict:
        """Calculate performance metrics for the last N days."""
        query = """
            SELECT 
                COUNT(*) as total_trades,
                COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as max_win,
                MIN(pnl) as max_loss
            FROM trades
            WHERE status = 'closed'
            AND exit_time >= CURRENT_DATE - INTERVAL '%s days'
        """
        
        result = self.execute_query(query, (days,))
        if result:
            metrics = result[0]
            if metrics['total_trades'] > 0:
                metrics['win_rate'] = (metrics['winning_trades'] / metrics['total_trades']) * 100
            else:
                metrics['win_rate'] = 0
            return metrics
        return {}
    
    def check_risk_limits(self) -> Dict[str, bool]:
        """Check if any risk limits are exceeded."""
        checks = {}
        
        # Check concurrent positions
        open_trades = self.get_open_trades()
        checks['max_positions_ok'] = len(open_trades) < 3
        
        # Check consecutive losses
        query = """
            SELECT pnl FROM trades 
            WHERE status = 'closed'
            ORDER BY exit_time DESC
            LIMIT 3
        """
        recent_trades = self.execute_query(query)
        consecutive_losses = sum(1 for t in recent_trades if t['pnl'] < 0)
        checks['consecutive_losses_ok'] = consecutive_losses < 3
        
        # Check daily loss
        query = """
            SELECT SUM(pnl) as daily_pnl
            FROM trades
            WHERE DATE(exit_time) = CURRENT_DATE
            AND status = 'closed'
        """
        result = self.execute_query(query)
        daily_pnl = result[0]['daily_pnl'] if result and result[0]['daily_pnl'] else 0
        checks['daily_loss_ok'] = daily_pnl > -0.10  # Assuming normalized to portfolio %
        
        return checks
    
    def update_performance_metrics(self):
        """Update the performance_metrics table with latest calculations."""
        metrics = self.get_performance_metrics(1)  # Today's metrics
        
        if metrics:
            query = """
                INSERT INTO performance_metrics 
                (date, total_trades, winning_trades, total_pnl, sharpe_ratio, win_rate)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (date) DO UPDATE SET
                    total_trades = EXCLUDED.total_trades,
                    winning_trades = EXCLUDED.winning_trades,
                    total_pnl = EXCLUDED.total_pnl,
                    win_rate = EXCLUDED.win_rate,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            self.execute_update(query, (
                datetime.now().date(),
                metrics.get('total_trades', 0),
                metrics.get('winning_trades', 0),
                metrics.get('total_pnl', 0),
                None,  # Sharpe ratio calculated separately
                metrics.get('win_rate', 0)
            ))