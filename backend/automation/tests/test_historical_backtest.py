#!/usr/bin/env python3
"""
Tests for Historical Backtesting System
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from automation.historical_backtest import HistoricalBacktest


class TestHistoricalBacktest(unittest.TestCase):
    """Test cases for historical backtesting"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.backtest = HistoricalBacktest(starting_capital=10000.0, lookback_days=14)
    
    def test_initialization(self):
        """Test backtest initialization"""
        self.assertEqual(self.backtest.starting_capital, 10000.0)
        self.assertEqual(self.backtest.current_capital, 10000.0)
        self.assertEqual(self.backtest.lookback_days, 14)
        self.assertEqual(self.backtest.max_positions, 3)
        self.assertEqual(self.backtest.position_size_pct, 0.06)
        self.assertEqual(len(self.backtest.positions), 0)
        self.assertEqual(len(self.backtest.trades), 0)
    
    def test_calculate_historical_volatility(self):
        """Test historical volatility calculation"""
        # Create sample price data
        price_data = [
            {'c': 100.0}, {'c': 101.0}, {'c': 99.5}, {'c': 102.0},
            {'c': 101.5}, {'c': 103.0}, {'c': 102.5}, {'c': 104.0},
            {'c': 103.5}, {'c': 105.0}, {'c': 104.5}, {'c': 106.0},
            {'c': 105.5}, {'c': 107.0}, {'c': 106.5}, {'c': 108.0},
            {'c': 107.5}, {'c': 109.0}, {'c': 108.5}, {'c': 110.0}
        ]
        
        volatility = self.backtest.calculate_historical_volatility(price_data, periods=20)
        
        # Should return a positive volatility value
        self.assertGreater(volatility, 0)
        self.assertLess(volatility, 100)  # Should be reasonable percentage
    
    def test_evaluate_trade_criteria_volume_fail(self):
        """Test trade criteria evaluation - volume failure"""
        earnings_row = pd.Series({
            'ticker': 'TEST',
            'report_date': datetime.now(),
            'avg_daily_volume': 500000,  # Below 1M threshold
            'iv_rv_ratio': 1.5,
            'term_structure_slope': -0.5
        })
        
        options_data = {'close': 100.0}
        
        meets_criteria, analysis = self.backtest.evaluate_trade_criteria(earnings_row, options_data)
        
        self.assertFalse(meets_criteria)
        self.assertIn("Volume too low", analysis['reasons'][0])
    
    def test_evaluate_trade_criteria_iv_rv_fail(self):
        """Test trade criteria evaluation - IV/RV ratio failure"""
        earnings_row = pd.Series({
            'ticker': 'TEST',
            'report_date': datetime.now(),
            'avg_daily_volume': 2000000,
            'iv_rv_ratio': 1.1,  # Below 1.2 threshold
            'term_structure_slope': -0.5
        })
        
        options_data = {'close': 100.0}
        
        meets_criteria, analysis = self.backtest.evaluate_trade_criteria(earnings_row, options_data)
        
        self.assertFalse(meets_criteria)
        self.assertIn("IV/RV ratio too low", analysis['reasons'][0])
    
    def test_evaluate_trade_criteria_term_structure_fail(self):
        """Test trade criteria evaluation - term structure failure"""
        earnings_row = pd.Series({
            'ticker': 'TEST',
            'report_date': datetime.now(),
            'avg_daily_volume': 2000000,
            'iv_rv_ratio': 1.5,
            'term_structure_slope': 0.5  # Positive slope (bad for calendar spreads)
        })
        
        options_data = {'close': 100.0}
        
        meets_criteria, analysis = self.backtest.evaluate_trade_criteria(earnings_row, options_data)
        
        self.assertFalse(meets_criteria)
        self.assertIn("Term structure not favorable", analysis['reasons'][0])
    
    def test_evaluate_trade_criteria_success(self):
        """Test trade criteria evaluation - success"""
        earnings_row = pd.Series({
            'ticker': 'TEST',
            'report_date': datetime.now(),
            'avg_daily_volume': 2000000,
            'iv_rv_ratio': 1.5,
            'term_structure_slope': -0.5,
            'expected_move': 5.0
        })
        
        options_data = {'close': 100.0}
        
        meets_criteria, analysis = self.backtest.evaluate_trade_criteria(earnings_row, options_data)
        
        self.assertTrue(meets_criteria)
        self.assertEqual(analysis['iv_rv_ratio'], 1.5)
        self.assertEqual(analysis['term_slope'], -0.5)
        self.assertEqual(analysis['expected_move'], 5.0)
    
    def test_simulate_calendar_spread(self):
        """Test calendar spread simulation"""
        ticker = 'TEST'
        entry_date = datetime.now() - timedelta(days=5)
        exit_date = datetime.now() - timedelta(days=3)
        stock_price = 100.0
        expected_move = 5.0
        
        trade = self.backtest.simulate_calendar_spread(
            ticker=ticker,
            entry_date=entry_date,
            exit_date=exit_date,
            stock_price=stock_price,
            expected_move=expected_move
        )
        
        # Check trade structure
        self.assertEqual(trade['ticker'], ticker)
        self.assertEqual(trade['entry_date'], entry_date)
        self.assertEqual(trade['exit_date'], exit_date)
        self.assertEqual(trade['trade_type'], 'Calendar Spread')
        self.assertIn('strike', trade)
        self.assertIn('front_premium', trade)
        self.assertIn('back_premium', trade)
        self.assertIn('net_debit', trade)
        self.assertIn('total_pnl', trade)
        self.assertIn('pnl_percent', trade)
        
        # Strike should be near stock price
        self.assertAlmostEqual(trade['strike'], stock_price, delta=5)
        
        # Net debit should be negative (we pay to enter)
        self.assertLess(trade['net_debit'], 0)
        
        # Capital should be updated
        expected_capital = 10000.0 + trade['total_pnl']
        self.assertEqual(self.backtest.current_capital, expected_capital)
    
    def test_calculate_performance_metrics_no_trades(self):
        """Test performance metrics calculation with no trades"""
        metrics = self.backtest.calculate_performance_metrics()
        
        self.assertEqual(metrics['total_trades'], 0)
        self.assertEqual(metrics['starting_capital'], 10000.0)
        self.assertEqual(metrics['ending_capital'], 10000.0)
        self.assertEqual(metrics['total_pnl'], 0)
        self.assertEqual(metrics['total_return_pct'], 0)
        self.assertEqual(metrics['win_rate'], 0)
    
    def test_calculate_performance_metrics_with_trades(self):
        """Test performance metrics calculation with trades"""
        # Add some mock trades
        self.backtest.trades = [
            {'total_pnl': 100, 'pnl_percent': 10},
            {'total_pnl': -50, 'pnl_percent': -5},
            {'total_pnl': 150, 'pnl_percent': 15},
            {'total_pnl': -25, 'pnl_percent': -2.5},
            {'total_pnl': 75, 'pnl_percent': 7.5}
        ]
        
        self.backtest.current_capital = 10250  # Starting + P&L
        
        metrics = self.backtest.calculate_performance_metrics()
        
        self.assertEqual(metrics['total_trades'], 5)
        self.assertEqual(metrics['winning_trades'], 3)
        self.assertEqual(metrics['losing_trades'], 2)
        self.assertEqual(metrics['total_pnl'], 250)
        self.assertEqual(metrics['win_rate'], 60.0)
        self.assertGreater(metrics['profit_factor'], 1.0)
        
    @patch('automation.historical_backtest.psycopg2.connect')
    def test_fetch_historical_earnings(self, mock_connect):
        """Test fetching historical earnings from database"""
        # Mock database connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'ticker': 'AAPL',
                'company_name': 'Apple Inc.',
                'report_date': datetime.now().date(),
                'report_time': 'time-after-hours',
                'expected_move': 5.0
            }
        ]
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        df = self.backtest.fetch_historical_earnings(start_date, end_date)
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['ticker'], 'AAPL')
    
    def test_exit_time_setting(self):
        """Test that exit time is set to 1 hour after market open"""
        self.assertEqual(self.backtest.exit_time, "10:30")


if __name__ == '__main__':
    unittest.main()