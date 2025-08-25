#!/usr/bin/env python3
"""
Add open positions to the database for testing
"""

import os
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

def add_open_positions():
    """Add open positions to the database"""
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Add open trades
    open_trades = [
        {
            'ticker': 'NVDA',
            'company_name': 'NVIDIA Corporation',
            'earnings_date': datetime.now() + timedelta(days=2),
            'entry_date': datetime.now() - timedelta(days=3),
            'front_strike': 120,
            'front_expiry': (datetime.now() + timedelta(days=5)).date(),
            'front_premium': 4.25,
            'front_contracts': 20,
            'back_strike': 120,
            'back_expiry': (datetime.now() + timedelta(days=35)).date(),
            'back_premium': 5.80,
            'back_contracts': 20,
            'net_debit': -1.55,
            'position_size': 3100,
            'entry_stock_price': 119.50,
            'expected_move': 8.5,
            'entry_iv': 72,
            'status': 'open',
            'recommendation': 'RECOMMENDED',
            'source': 'live'
        },
        {
            'ticker': 'TSLA',
            'company_name': 'Tesla, Inc.',
            'earnings_date': datetime.now() + timedelta(days=1),
            'entry_date': datetime.now() - timedelta(days=2),
            'front_strike': 240,
            'front_expiry': (datetime.now() + timedelta(days=5)).date(),
            'front_premium': 8.95,
            'front_contracts': 10,
            'back_strike': 240,
            'back_expiry': (datetime.now() + timedelta(days=35)).date(),
            'back_premium': 11.20,
            'back_contracts': 10,
            'net_debit': -2.25,
            'position_size': 2250,
            'entry_stock_price': 238.00,
            'expected_move': 6.2,
            'entry_iv': 61,
            'status': 'open',
            'recommendation': 'CONSIDER',
            'source': 'live'
        }
    ]
    
    try:
        for trade in open_trades:
            # Insert trade
            cursor.execute("""
                INSERT INTO trades (
                    ticker, company_name, earnings_date, entry_date,
                    front_strike, front_expiry, front_premium, front_contracts,
                    back_strike, back_expiry, back_premium, back_contracts,
                    net_debit, position_size, entry_stock_price,
                    expected_move, entry_iv, status, recommendation, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                trade['ticker'], trade['company_name'], trade['earnings_date'],
                trade['entry_date'], trade['front_strike'], trade['front_expiry'],
                trade['front_premium'], trade['front_contracts'],
                trade['back_strike'], trade['back_expiry'], trade['back_premium'],
                trade['back_contracts'], trade['net_debit'], trade['position_size'],
                trade['entry_stock_price'], trade['expected_move'], trade['entry_iv'],
                trade['status'], trade['recommendation'], trade['source']
            ))
            
            trade_id = cursor.fetchone()[0]
            
            # Add corresponding position
            cursor.execute("""
                INSERT INTO positions (
                    trade_id, ticker, company_name, position_type,
                    quantity, entry_price, current_price,
                    unrealized_pnl, unrealized_pnl_percent, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                trade_id, trade['ticker'], trade['company_name'],
                'calendar_spread', trade['front_contracts'],
                abs(trade['net_debit']), abs(trade['net_debit']) * 1.2,
                trade['position_size'] * 0.2, 20.0, 'open'
            ))
        
        # Add more portfolio history points
        for i in range(14):
            date = datetime.now() - timedelta(days=14-i)
            value = 10000 + (i * 100) + (i % 3 - 1) * 50
            cursor.execute("""
                INSERT INTO portfolio_history (
                    timestamp, total_value, cash_balance, positions_value,
                    daily_pnl, daily_pnl_percent
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp) DO UPDATE SET
                    total_value = EXCLUDED.total_value
            """, (date, value, value * 0.8, value * 0.2, 100, 1.0))
        
        conn.commit()
        print(f"✅ Added {len(open_trades)} open positions")
        print("✅ Added daily portfolio history")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    add_open_positions()