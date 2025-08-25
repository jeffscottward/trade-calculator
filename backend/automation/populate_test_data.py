#!/usr/bin/env python3
"""
Populate test data for backtesting demonstration
Creates historical earnings and trade data for the past 2 weeks
"""

import os
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv
import random

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

def populate_test_earnings():
    """Populate test earnings data for backtesting"""
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Test tickers with various characteristics
    test_earnings = [
        # High quality trades (meet all criteria)
        {
            'ticker': 'AAPL',
            'company_name': 'Apple Inc.',
            'report_date': datetime.now() - timedelta(days=10),
            'report_time': 'time-after-hours',
            'market_cap_numeric': 3000000000000,
            'expected_move': 4.5,
            'avg_volume_pass': True,
            'iv_rv_ratio_pass': True,
            'term_structure_pass': True,
            'iv_rank': 75,
            'priority_score': 95,
            'recommendation': 'RECOMMENDED'
        },
        {
            'ticker': 'MSFT',
            'company_name': 'Microsoft Corporation',
            'report_date': datetime.now() - timedelta(days=8),
            'report_time': 'time-pre-market',
            'market_cap_numeric': 2500000000000,
            'expected_move': 3.8,
            'avg_volume_pass': True,
            'iv_rv_ratio_pass': True,
            'term_structure_pass': True,
            'iv_rank': 68,
            'priority_score': 90,
            'recommendation': 'RECOMMENDED'
        },
        {
            'ticker': 'NVDA',
            'company_name': 'NVIDIA Corporation',
            'report_date': datetime.now() - timedelta(days=6),
            'report_time': 'time-after-hours',
            'market_cap_numeric': 1200000000000,
            'expected_move': 8.2,
            'avg_volume_pass': True,
            'iv_rv_ratio_pass': True,
            'term_structure_pass': True,
            'iv_rank': 82,
            'priority_score': 98,
            'recommendation': 'RECOMMENDED'
        },
        # Mixed quality trades
        {
            'ticker': 'TSLA',
            'company_name': 'Tesla, Inc.',
            'report_date': datetime.now() - timedelta(days=5),
            'report_time': 'time-after-hours',
            'market_cap_numeric': 800000000000,
            'expected_move': 7.5,
            'avg_volume_pass': True,
            'iv_rv_ratio_pass': False,  # Fails IV/RV ratio
            'term_structure_pass': True,
            'iv_rank': 55,
            'priority_score': 70,
            'recommendation': 'CONSIDER'
        },
        {
            'ticker': 'META',
            'company_name': 'Meta Platforms, Inc.',
            'report_date': datetime.now() - timedelta(days=4),
            'report_time': 'time-after-hours',
            'market_cap_numeric': 900000000000,
            'expected_move': 5.2,
            'avg_volume_pass': True,
            'iv_rv_ratio_pass': True,
            'term_structure_pass': False,  # Fails term structure
            'iv_rank': 62,
            'priority_score': 75,
            'recommendation': 'CONSIDER'
        },
        {
            'ticker': 'GOOGL',
            'company_name': 'Alphabet Inc.',
            'report_date': datetime.now() - timedelta(days=3),
            'report_time': 'time-after-hours',
            'market_cap_numeric': 1700000000000,
            'expected_move': 4.0,
            'avg_volume_pass': True,
            'iv_rv_ratio_pass': True,
            'term_structure_pass': True,
            'iv_rank': 70,
            'priority_score': 88,
            'recommendation': 'RECOMMENDED'
        },
        # Low quality trades (fail multiple criteria)
        {
            'ticker': 'SMALL',
            'company_name': 'Small Cap Co.',
            'report_date': datetime.now() - timedelta(days=7),
            'report_time': 'time-after-hours',
            'market_cap_numeric': 500000000,
            'expected_move': 12.0,
            'avg_volume_pass': False,  # Fails volume
            'iv_rv_ratio_pass': False,  # Fails IV/RV
            'term_structure_pass': False,  # Fails term structure
            'iv_rank': 35,
            'priority_score': 40,
            'recommendation': 'AVOID'
        }
    ]
    
    try:
        # Insert test earnings data
        for earnings in test_earnings:
            cursor.execute("""
                INSERT INTO earnings_calendar (
                    ticker, company_name, report_date, report_time,
                    market_cap_numeric, expected_move, avg_volume_pass,
                    iv_rv_ratio_pass, term_structure_pass, iv_rank,
                    priority_score, recommendation
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, report_date) DO UPDATE SET
                    expected_move = EXCLUDED.expected_move,
                    avg_volume_pass = EXCLUDED.avg_volume_pass,
                    iv_rv_ratio_pass = EXCLUDED.iv_rv_ratio_pass,
                    term_structure_pass = EXCLUDED.term_structure_pass,
                    priority_score = EXCLUDED.priority_score
            """, (
                earnings['ticker'], earnings['company_name'],
                earnings['report_date'], earnings['report_time'],
                earnings['market_cap_numeric'], earnings['expected_move'],
                earnings['avg_volume_pass'], earnings['iv_rv_ratio_pass'],
                earnings['term_structure_pass'], earnings['iv_rank'],
                earnings['priority_score'], earnings['recommendation']
            ))
        
        conn.commit()
        print(f"✅ Inserted {len(test_earnings)} test earnings records")
        
    except Exception as e:
        print(f"❌ Error inserting test data: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def populate_sample_trades():
    """Populate sample trades for UI display"""
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Sample completed trades
    completed_trades = [
        {
            'ticker': 'AAPL',
            'company_name': 'Apple Inc.',
            'earnings_date': datetime.now() - timedelta(days=10),
            'entry_date': datetime.now() - timedelta(days=11),
            'exit_date': datetime.now() - timedelta(days=9),
            'front_strike': 230,
            'front_expiry': (datetime.now() - timedelta(days=7)).date(),
            'front_premium': 5.85,
            'front_contracts': 10,
            'back_strike': 230,
            'back_expiry': (datetime.now() + timedelta(days=23)).date(),
            'back_premium': 7.20,
            'back_contracts': 10,
            'net_debit': -1.35,
            'closing_credit': 0.45,
            'position_size': 1350,
            'entry_stock_price': 228.50,
            'exit_stock_price': 231.20,
            'expected_move': 4.5,
            'actual_move': 1.2,
            'iv_crush': 35,
            'total_pnl': 900,
            'pnl_percent': 66.7,
            'status': 'closed',
            'recommendation': 'RECOMMENDED',
            'source': 'backtest'
        },
        {
            'ticker': 'MSFT',
            'company_name': 'Microsoft Corporation',
            'earnings_date': datetime.now() - timedelta(days=8),
            'entry_date': datetime.now() - timedelta(days=9),
            'exit_date': datetime.now() - timedelta(days=7),
            'front_strike': 420,
            'front_expiry': (datetime.now() - timedelta(days=5)).date(),
            'front_premium': 8.50,
            'front_contracts': 5,
            'back_strike': 420,
            'back_expiry': (datetime.now() + timedelta(days=25)).date(),
            'back_premium': 10.75,
            'back_contracts': 5,
            'net_debit': -2.25,
            'closing_credit': 0.85,
            'position_size': 1125,
            'entry_stock_price': 418.75,
            'exit_stock_price': 422.30,
            'expected_move': 3.8,
            'actual_move': 0.8,
            'iv_crush': 40,
            'total_pnl': 700,
            'pnl_percent': 62.2,
            'status': 'closed',
            'recommendation': 'RECOMMENDED',
            'source': 'backtest'
        }
    ]
    
    try:
        # Insert sample trades
        for trade in completed_trades:
            cursor.execute("""
                INSERT INTO trades (
                    ticker, company_name, earnings_date, entry_date, exit_date,
                    front_strike, front_expiry, front_premium, front_contracts,
                    back_strike, back_expiry, back_premium, back_contracts,
                    net_debit, closing_credit, position_size,
                    entry_stock_price, exit_stock_price,
                    expected_move, actual_move, iv_crush,
                    total_pnl, pnl_percent, status, recommendation, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                trade['ticker'], trade['company_name'], trade['earnings_date'],
                trade['entry_date'], trade['exit_date'],
                trade['front_strike'], trade['front_expiry'], trade['front_premium'],
                trade['front_contracts'], trade['back_strike'], trade['back_expiry'],
                trade['back_premium'], trade['back_contracts'],
                trade['net_debit'], trade['closing_credit'], trade['position_size'],
                trade['entry_stock_price'], trade['exit_stock_price'],
                trade['expected_move'], trade['actual_move'], trade['iv_crush'],
                trade['total_pnl'], trade['pnl_percent'],
                trade['status'], trade['recommendation'], trade['source']
            ))
        
        # Insert portfolio history
        portfolio_values = [
            (datetime.now() - timedelta(days=14), 10000, 10000, 0, 0, 0),
            (datetime.now() - timedelta(days=10), 10900, 9550, 1350, 900, 9.0),
            (datetime.now() - timedelta(days=7), 11600, 10475, 1125, 700, 6.4),
            (datetime.now() - timedelta(days=3), 11600, 11600, 0, 0, 0),
            (datetime.now(), 11600, 11600, 0, 0, 0)
        ]
        
        for timestamp, total, cash, positions, daily_pnl, daily_pct in portfolio_values:
            cursor.execute("""
                INSERT INTO portfolio_history (
                    timestamp, total_value, cash_balance, positions_value,
                    daily_pnl, daily_pnl_percent
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp) DO UPDATE SET
                    total_value = EXCLUDED.total_value,
                    cash_balance = EXCLUDED.cash_balance
            """, (timestamp, total, cash, positions, daily_pnl, daily_pct))
        
        conn.commit()
        print(f"✅ Inserted {len(completed_trades)} sample trades")
        print(f"✅ Inserted {len(portfolio_values)} portfolio history records")
        
    except Exception as e:
        print(f"❌ Error inserting sample trades: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("Populating test data...")
    populate_test_earnings()
    populate_sample_trades()
    print("✅ Test data population complete!")