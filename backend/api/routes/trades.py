"""
Trades API endpoints
Provides access to trading data, positions, and portfolio history
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

router = APIRouter(prefix="/api/trades", tags=["trades"])


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


@router.get("/executed")
async def get_executed_trades(
    limit: int = Query(100, description="Maximum number of trades to return"),
    source: Optional[str] = Query(None, description="Filter by source (live, backtest, paper)")
):
    """Get executed/closed trades"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                id,
                ticker,
                company_name,
                trade_type,
                earnings_date,
                entry_date,
                exit_date,
                front_strike,
                front_expiry,
                front_premium,
                front_contracts,
                back_strike,
                back_expiry,
                back_premium,
                back_contracts,
                net_debit,
                closing_credit,
                position_size,
                entry_stock_price,
                exit_stock_price,
                expected_move,
                actual_move,
                iv_crush,
                total_pnl,
                pnl_percent,
                status,
                recommendation,
                source
            FROM trades
            WHERE status = 'closed'
        """
        
        params = []
        if source:
            query += " AND source = %s"
            params.append(source)
        
        query += " ORDER BY exit_date DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        trades = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Format dates for frontend
        for trade in trades:
            if trade['earnings_date']:
                trade['earningsDate'] = trade['earnings_date'].isoformat()
            if trade['entry_date']:
                trade['entryDate'] = trade['entry_date'].isoformat()
            if trade['exit_date']:
                trade['exitDate'] = trade['exit_date'].isoformat()
            if trade['front_expiry']:
                trade['frontExpiry'] = trade['front_expiry'].strftime('%b %d')
            if trade['back_expiry']:
                trade['backExpiry'] = trade['back_expiry'].strftime('%b %d')
            
            # Convert to frontend field names
            trade['frontStrike'] = trade.pop('front_strike')
            trade['frontPremium'] = float(trade.pop('front_premium'))
            trade['frontContracts'] = trade.pop('front_contracts')
            trade['backStrike'] = trade.pop('back_strike')
            trade['backPremium'] = float(trade.pop('back_premium'))
            trade['backContracts'] = trade.pop('back_contracts')
            trade['netDebit'] = float(trade.pop('net_debit'))
            trade['closingCredit'] = float(trade.pop('closing_credit')) if trade.get('closing_credit') else None
            trade['positionSize'] = trade.pop('position_size')
            trade['pnl'] = trade.pop('total_pnl')
            trade['pnlPercent'] = trade.pop('pnl_percent')
            trade['ivCrush'] = trade.pop('iv_crush')
            trade['actualMove'] = trade.pop('actual_move')
            trade['expectedMove'] = trade.pop('expected_move')
            trade['companyName'] = trade.pop('company_name')
            trade['tradeType'] = trade.pop('trade_type')
        
        return {"trades": trades}
        
    except Exception as e:
        print(f"Error fetching executed trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_positions():
    """Get current open positions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                t.id,
                t.ticker,
                t.company_name,
                t.trade_type,
                t.earnings_date,
                t.entry_date,
                t.front_strike,
                t.front_expiry,
                t.front_premium,
                t.front_contracts,
                t.back_strike,
                t.back_expiry,
                t.back_premium,
                t.back_contracts,
                t.net_debit,
                t.position_size,
                t.entry_stock_price,
                t.expected_move,
                t.entry_iv,
                t.status,
                t.recommendation,
                p.current_price,
                p.unrealized_pnl,
                p.unrealized_pnl_percent,
                (t.earnings_date - CURRENT_DATE) as days_to_earnings
            FROM trades t
            LEFT JOIN positions p ON t.id = p.trade_id
            WHERE t.status = 'open'
            ORDER BY t.earnings_date
        """)
        
        holdings = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Format for frontend
        for holding in holdings:
            if holding['earnings_date']:
                holding['earningsDate'] = holding['earnings_date'].isoformat()
            if holding['entry_date']:
                holding['entryDate'] = holding['entry_date'].isoformat()
            if holding['front_expiry']:
                holding['frontExpiry'] = holding['front_expiry'].strftime('%b %d')
            if holding['back_expiry']:
                holding['backExpiry'] = holding['back_expiry'].strftime('%b %d')
            
            # Convert field names
            holding['frontStrike'] = holding.pop('front_strike')
            holding['frontPremium'] = float(holding.pop('front_premium'))
            holding['frontContracts'] = holding.pop('front_contracts')
            holding['backStrike'] = holding.pop('back_strike')
            holding['backPremium'] = float(holding.pop('back_premium'))
            holding['backContracts'] = holding.pop('back_contracts')
            holding['netDebit'] = float(holding.pop('net_debit'))
            holding['positionSize'] = holding.pop('position_size')
            holding['currentValue'] = holding.pop('current_price', 0)
            holding['unrealizedPnl'] = holding.pop('unrealized_pnl', 0)
            holding['unrealizedPnlPercent'] = holding.pop('unrealized_pnl_percent', 0)
            holding['expectedMove'] = holding.pop('expected_move')
            holding['currentIV'] = holding.pop('entry_iv', 0)
            holding['entryIV'] = holding.get('currentIV', 0)
            holding['currentStockPrice'] = holding.pop('entry_stock_price')
            holding['daysToEarnings'] = holding.pop('days_to_earnings')
            holding['companyName'] = holding.pop('company_name')
            holding['tradeType'] = holding.pop('trade_type')
        
        return {"holdings": holdings}
        
    except Exception as e:
        print(f"Error fetching current positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio-history")
async def get_portfolio_history(
    days: int = Query(30, description="Number of days of history to return")
):
    """Get portfolio value history"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                timestamp as date,
                total_value as value,
                cash_balance,
                positions_value,
                daily_pnl,
                daily_pnl_percent
            FROM portfolio_history
            WHERE timestamp >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY timestamp
        """, (days,))
        
        history = cursor.fetchall()
        
        # If no history, generate mock data
        if not history:
            base_value = 10000
            history = []
            for i in range(days):
                date = datetime.now() - timedelta(days=days-i)
                # Add some random variation
                variation = (i / days) * 1000 + (i % 3 - 1) * 100
                history.append({
                    'date': date.isoformat(),
                    'value': base_value + variation
                })
        else:
            # Format dates
            for record in history:
                record['date'] = record['date'].isoformat()
        
        cursor.close()
        conn.close()
        
        return {"history": history}
        
    except Exception as e:
        print(f"Error fetching portfolio history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_metrics():
    """Get overall performance metrics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                total_trades,
                closed_trades,
                open_trades,
                winning_trades,
                losing_trades,
                win_rate,
                avg_win,
                avg_loss,
                total_realized_pnl,
                total_unrealized_pnl,
                avg_return_percent,
                return_std_dev
            FROM trade_performance_view
        """)
        
        metrics = cursor.fetchone()
        
        if not metrics:
            metrics = {
                'total_trades': 0,
                'closed_trades': 0,
                'open_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'total_realized_pnl': 0,
                'total_unrealized_pnl': 0,
                'avg_return_percent': 0,
                'return_std_dev': 0
            }
        
        # Calculate additional metrics
        if metrics['return_std_dev'] and metrics['avg_return_percent']:
            # Simplified Sharpe ratio calculation
            metrics['sharpe_ratio'] = (
                float(metrics['avg_return_percent']) / 
                float(metrics['return_std_dev'])
            ) if metrics['return_std_dev'] > 0 else 0
        else:
            metrics['sharpe_ratio'] = 0
        
        # Get current portfolio value
        cursor.execute("""
            SELECT total_value 
            FROM portfolio_history 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        current_value = cursor.fetchone()
        metrics['portfolio_value'] = current_value['total_value'] if current_value else 10000
        
        cursor.close()
        conn.close()
        
        # Convert to frontend field names
        response = {
            'totalTrades': metrics['total_trades'],
            'closedTrades': metrics['closed_trades'],
            'openTrades': metrics['open_trades'],
            'winningTrades': metrics['winning_trades'],
            'losingTrades': metrics['losing_trades'],
            'winRate': float(metrics['win_rate']) if metrics['win_rate'] else 0,
            'avgWin': float(metrics['avg_win']) if metrics['avg_win'] else 0,
            'avgLoss': float(metrics['avg_loss']) if metrics['avg_loss'] else 0,
            'totalRealizedPnl': float(metrics['total_realized_pnl']) if metrics['total_realized_pnl'] else 0,
            'totalUnrealizedPnl': float(metrics['total_unrealized_pnl']) if metrics['total_unrealized_pnl'] else 0,
            'avgReturnPercent': float(metrics['avg_return_percent']) if metrics['avg_return_percent'] else 0,
            'sharpeRatio': float(metrics['sharpe_ratio']),
            'portfolioValue': float(metrics['portfolio_value'])
        }
        
        return response
        
    except Exception as e:
        print(f"Error fetching performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest")
async def run_backtest(
    lookback_days: int = Query(14, description="Number of days to look back"),
    starting_capital: float = Query(10000, description="Starting capital for backtest")
):
    """Run a backtest with specified parameters"""
    try:
        # Import here to avoid circular imports
        from automation.historical_backtest import HistoricalBacktest
        
        # Run the backtest
        backtest = HistoricalBacktest(
            starting_capital=starting_capital,
            lookback_days=lookback_days
        )
        
        results = backtest.run_backtest()
        backtest.save_results_to_database()
        
        return {
            "success": True,
            "results": results,
            "message": f"Backtest completed with {results.get('total_trades', 0)} trades"
        }
        
    except Exception as e:
        print(f"Error running backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))