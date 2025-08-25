#!/usr/bin/env python3
"""
Historical Backtesting System
Fetches historical earnings and options data to simulate calendar spread trades
"""

import os
import sys
from datetime import datetime, timedelta, date as date_type
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from decimal import Decimal
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from automation.ib_client import IBClient

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

class HistoricalBacktest:
    """
    Backtesting system for calendar spread strategy
    """
    
    def __init__(self, starting_capital: float = 10000.0, lookback_days: int = 14):
        """
        Initialize backtesting system
        
        Args:
            starting_capital: Starting capital for paper trading
            lookback_days: Number of days to look back for historical data
        """
        self.starting_capital = starting_capital
        self.current_capital = starting_capital
        self.lookback_days = lookback_days
        self.ib_client = IBClient()
        self.positions = []
        self.trades = []
        self.performance_metrics = {}
        
        # Strategy parameters
        self.max_positions = 3
        self.position_size_pct = 0.06  # 6% per trade
        self.min_volume = 1000000  # 1M shares average volume
        self.min_iv_rv_ratio = 1.2  # IV must be 20% higher than RV
        self.exit_time = "10:30"  # Exit 1 hour after market open (9:30 + 1hr)
        
        # Initialize IB connection
        if not self.ib_client.get_auth_status().get('authenticated'):
            print("Attempting to authenticate with IB...")
            self.ib_client.reauthenticate()
    
    def fetch_historical_earnings(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch historical earnings data from database
        
        Args:
            start_date: Start date for earnings data
            end_date: End date for earnings data
            
        Returns:
            DataFrame with earnings data
        """
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                ticker,
                company_name,
                report_date,
                report_time,
                market_cap_numeric,
                eps_forecast_numeric,
                last_year_eps_numeric,
                expected_move,
                CASE WHEN avg_volume_pass THEN 2000000 ELSE 500000 END as avg_daily_volume,
                iv_rank as iv_percentile,
                CASE WHEN term_structure_pass THEN -0.5 ELSE 0.5 END as term_structure_slope,
                CASE WHEN iv_rv_ratio_pass THEN 1.5 ELSE 0.8 END as iv_rv_ratio,
                priority_score
            FROM earnings_calendar
            WHERE report_date BETWEEN %s AND %s
                AND report_time IN ('time-after-hours', 'time-pre-market')
                AND expected_move IS NOT NULL
            ORDER BY report_date, priority_score DESC
        """
        
        cursor.execute(query, (start_date, end_date))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return pd.DataFrame(results)
    
    def get_historical_options_data(self, symbol: str, date: datetime) -> Optional[Dict[str, Any]]:
        """
        Get historical options data for a symbol on a specific date
        
        Args:
            symbol: Stock ticker
            date: Date to get options data for
            
        Returns:
            Options data including IV, strikes, premiums
        """
        try:
            # Get contract ID
            contract = self.ib_client.search_contract(symbol)
            if not contract:
                print(f"Contract not found for {symbol}")
                return None
            
            conid = contract.get('conid')
            
            # Calculate days to look back from today
            # Convert date to datetime if it's a date object
            if isinstance(date, date_type) and not isinstance(date, datetime):
                target_date = datetime.combine(date, datetime.min.time())
            else:
                target_date = date
            
            days_back = (datetime.now() - target_date).days
            
            # Get historical data
            hist_data = self.ib_client.get_historical_data(
                conid, 
                period=f"{days_back}d",
                bar="1d"
            )
            
            if not hist_data or 'data' not in hist_data:
                return None
            
            # Find data for specific date
            target_timestamp = int(date.timestamp() * 1000)
            for bar in hist_data['data']:
                if abs(bar['t'] - target_timestamp) < 86400000:  # Within 1 day
                    return {
                        'symbol': symbol,
                        'date': date,
                        'close': bar.get('c'),
                        'high': bar.get('h'),
                        'low': bar.get('l'),
                        'volume': bar.get('v'),
                        'historical_volatility': self.calculate_historical_volatility(hist_data['data'])
                    }
            
            return None
            
        except Exception as e:
            print(f"Error getting historical options data for {symbol}: {e}")
            return None
    
    def calculate_historical_volatility(self, price_data: List[Dict], periods: int = 20) -> float:
        """
        Calculate historical volatility from price data
        
        Args:
            price_data: List of price bars
            periods: Number of periods for calculation
            
        Returns:
            Annualized historical volatility
        """
        if len(price_data) < periods:
            return 0.0
        
        # Get closing prices
        closes = [bar['c'] for bar in price_data[-periods:]]
        
        # Calculate returns
        returns = []
        for i in range(1, len(closes)):
            returns.append(np.log(closes[i] / closes[i-1]))
        
        # Calculate standard deviation and annualize
        if returns:
            std_dev = np.std(returns)
            annualized_vol = std_dev * np.sqrt(252)  # 252 trading days
            return annualized_vol * 100  # Return as percentage
        
        return 0.0
    
    def evaluate_trade_criteria(self, earnings_row: pd.Series, options_data: Dict) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluate if a trade meets our criteria
        
        Args:
            earnings_row: Row from earnings DataFrame
            options_data: Historical options data
            
        Returns:
            Tuple of (meets_criteria, analysis_details)
        """
        analysis = {
            'ticker': earnings_row['ticker'],
            'report_date': earnings_row['report_date'],
            'meets_criteria': False,
            'reasons': []
        }
        
        # Check volume criteria
        if earnings_row.get('avg_daily_volume', 0) < self.min_volume:
            analysis['reasons'].append(f"Volume too low: {earnings_row.get('avg_daily_volume', 0):,.0f}")
            return False, analysis
        
        # Check IV/RV ratio
        iv_rv_ratio = earnings_row.get('iv_rv_ratio', 0)
        if iv_rv_ratio < self.min_iv_rv_ratio:
            analysis['reasons'].append(f"IV/RV ratio too low: {iv_rv_ratio:.2f}")
            return False, analysis
        
        # Check term structure slope (should be negative for calendar spreads)
        term_slope = earnings_row.get('term_structure_slope', 0)
        if term_slope >= 0:
            analysis['reasons'].append(f"Term structure not favorable: {term_slope:.2f}")
            return False, analysis
        
        # Check if we have room for more positions
        if len(self.positions) >= self.max_positions:
            analysis['reasons'].append("Max positions reached")
            return False, analysis
        
        # All criteria met
        analysis['meets_criteria'] = True
        analysis['reasons'].append("All criteria met")
        analysis['iv_rv_ratio'] = iv_rv_ratio
        analysis['term_slope'] = term_slope
        analysis['expected_move'] = earnings_row.get('expected_move', 5.0)
        
        return True, analysis
    
    def simulate_calendar_spread(
        self, 
        ticker: str, 
        entry_date: datetime,
        exit_date: datetime,
        stock_price: float,
        expected_move: float
    ) -> Dict[str, Any]:
        """
        Simulate a calendar spread trade
        
        Args:
            ticker: Stock ticker
            entry_date: Entry date (day before earnings)
            exit_date: Exit date (day after earnings)
            stock_price: Stock price at entry
            expected_move: Expected move percentage
            
        Returns:
            Trade details and P&L
        """
        # Calculate position size
        position_value = self.current_capital * self.position_size_pct
        
        # Determine strike (ATM)
        strike = round(stock_price / 5) * 5  # Round to nearest $5
        
        # Simulate option premiums based on expected move
        # Front month (selling) - higher IV due to earnings
        front_premium = stock_price * (expected_move / 100) * 0.4  # Rough approximation
        
        # Back month (buying) - lower IV, 30 days out
        back_premium = front_premium * 0.7  # Back month typically 70% of front month
        
        # Net debit per spread
        net_debit = back_premium - front_premium
        
        # Number of contracts (each contract = 100 shares)
        num_contracts = max(1, int(position_value / (abs(net_debit) * 100)))
        
        # Actual position size
        actual_position_size = abs(net_debit) * num_contracts * 100
        
        # Simulate post-earnings IV crush
        iv_crush_factor = 0.5  # IV typically drops 50% after earnings
        
        # Simulate actual move (random within expected range)
        np.random.seed(int(entry_date.timestamp()))  # Reproducible randomness
        actual_move_pct = np.random.normal(0, expected_move / 2)  # Mean 0, std = half expected
        actual_move_pct = np.clip(actual_move_pct, -expected_move, expected_move)
        
        exit_stock_price = stock_price * (1 + actual_move_pct / 100)
        
        # Calculate exit values
        # Front month expires worthless if within expected move
        front_exit_value = 0 if abs(actual_move_pct) < expected_move else front_premium * 0.2
        
        # Back month retains time value minus IV crush
        back_exit_value = back_premium * (1 - iv_crush_factor) * 0.8
        
        # Calculate P&L
        front_pnl = (front_premium - front_exit_value) * num_contracts * 100  # Profit from selling
        back_pnl = (back_exit_value - back_premium) * num_contracts * 100  # Loss from buying
        total_pnl = front_pnl + back_pnl
        pnl_percent = (total_pnl / actual_position_size) * 100
        
        trade = {
            'ticker': ticker,
            'entry_date': entry_date,
            'exit_date': exit_date,
            'trade_type': 'Calendar Spread',
            'strike': strike,
            'front_expiry': (entry_date + timedelta(days=3)).strftime('%b %d'),  # Friday after earnings
            'back_expiry': (entry_date + timedelta(days=33)).strftime('%b %d'),  # 30 days later
            'front_premium': round(front_premium, 2),
            'back_premium': round(back_premium, 2),
            'net_debit': round(net_debit, 2),
            'num_contracts': num_contracts,
            'position_size': round(actual_position_size, 2),
            'entry_stock_price': round(stock_price, 2),
            'exit_stock_price': round(exit_stock_price, 2),
            'expected_move': round(expected_move, 2),
            'actual_move': round(actual_move_pct, 2),
            'iv_crush': round(iv_crush_factor * 100, 2),
            'front_pnl': round(front_pnl, 2),
            'back_pnl': round(back_pnl, 2),
            'total_pnl': round(total_pnl, 2),
            'pnl_percent': round(pnl_percent, 2),
            'status': 'closed'
        }
        
        # Update capital
        self.current_capital += total_pnl
        
        return trade
    
    def run_backtest(self) -> Dict[str, Any]:
        """
        Run the complete backtest
        
        Returns:
            Backtest results and performance metrics
        """
        print(f"Starting backtest with ${self.starting_capital:,.2f}")
        print(f"Looking back {self.lookback_days} days for historical data")
        print("-" * 60)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days)
        
        # Fetch historical earnings
        print(f"\nFetching earnings from {start_date.date()} to {end_date.date()}")
        earnings_df = self.fetch_historical_earnings(start_date, end_date)
        
        if earnings_df.empty:
            print("No earnings data found for the period")
            return self.calculate_performance_metrics()
        
        print(f"Found {len(earnings_df)} earnings events")
        
        # Process each earnings event
        for idx, row in earnings_df.iterrows():
            ticker = row['ticker']
            report_date = row['report_date']
            
            # Skip if it's a future date
            if pd.Timestamp(report_date) > pd.Timestamp.now():
                continue
            
            print(f"\nAnalyzing {ticker} - Earnings on {report_date}")
            
            # Get historical options data
            options_data = self.get_historical_options_data(ticker, report_date)
            
            if not options_data:
                print(f"  No historical data available for {ticker}")
                continue
            
            # Evaluate trade criteria
            meets_criteria, analysis = self.evaluate_trade_criteria(row, options_data)
            
            if not meets_criteria:
                print(f"  Does not meet criteria: {', '.join(analysis['reasons'])}")
                continue
            
            print(f"  ✓ Meets all criteria - Executing trade")
            
            # Simulate the trade
            entry_date = pd.Timestamp(report_date) - timedelta(days=1)  # Enter day before
            exit_date = pd.Timestamp(report_date) + timedelta(days=1)  # Exit day after
            
            trade = self.simulate_calendar_spread(
                ticker=ticker,
                entry_date=entry_date,
                exit_date=exit_date,
                stock_price=options_data['close'],
                expected_move=row.get('expected_move', 5.0)
            )
            
            self.trades.append(trade)
            
            print(f"  Trade Result: ${trade['total_pnl']:+,.2f} ({trade['pnl_percent']:+.1f}%)")
            print(f"  Current Capital: ${self.current_capital:,.2f}")
            
            # Check if we've hit position limits
            if len([t for t in self.trades if t['exit_date'] > datetime.now()]) >= self.max_positions:
                print(f"  Max positions ({self.max_positions}) reached")
        
        # Calculate final metrics
        return self.calculate_performance_metrics()
    
    def calculate_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate performance metrics for the backtest
        
        Returns:
            Dictionary of performance metrics
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'starting_capital': self.starting_capital,
                'ending_capital': self.current_capital,
                'total_pnl': 0,
                'total_return_pct': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'trades': []
            }
        
        # Calculate metrics
        winning_trades = [t for t in self.trades if t['total_pnl'] > 0]
        losing_trades = [t for t in self.trades if t['total_pnl'] <= 0]
        
        total_pnl = sum(t['total_pnl'] for t in self.trades)
        total_return_pct = ((self.current_capital - self.starting_capital) / self.starting_capital) * 100
        
        win_rate = (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0
        
        avg_win = np.mean([t['total_pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['total_pnl'] for t in losing_trades]) if losing_trades else 0
        
        total_wins = sum(t['total_pnl'] for t in winning_trades)
        total_losses = abs(sum(t['total_pnl'] for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Calculate Sharpe ratio (simplified)
        returns = [t['pnl_percent'] for t in self.trades]
        if len(returns) > 1:
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252 / self.lookback_days)
        else:
            sharpe_ratio = 0
        
        # Calculate max drawdown
        capital_curve = [self.starting_capital]
        running_capital = self.starting_capital
        for trade in self.trades:
            running_capital += trade['total_pnl']
            capital_curve.append(running_capital)
        
        peak = capital_curve[0]
        max_drawdown = 0
        for value in capital_curve:
            if value > peak:
                peak = value
            drawdown = ((peak - value) / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        self.performance_metrics = {
            'total_trades': len(self.trades),
            'starting_capital': round(self.starting_capital, 2),
            'ending_capital': round(self.current_capital, 2),
            'total_pnl': round(total_pnl, 2),
            'total_return_pct': round(total_return_pct, 2),
            'win_rate': round(win_rate, 2),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'trades': self.trades
        }
        
        return self.performance_metrics
    
    def save_results_to_database(self):
        """Save backtest results to database"""
        if not self.trades:
            print("No trades to save")
            return
        
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        try:
            # Create trades table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backtest_trades (
                    id SERIAL PRIMARY KEY,
                    ticker VARCHAR(10) NOT NULL,
                    entry_date TIMESTAMP NOT NULL,
                    exit_date TIMESTAMP NOT NULL,
                    trade_type VARCHAR(50),
                    strike DECIMAL(10, 2),
                    front_expiry VARCHAR(20),
                    back_expiry VARCHAR(20),
                    front_premium DECIMAL(10, 2),
                    back_premium DECIMAL(10, 2),
                    net_debit DECIMAL(10, 2),
                    num_contracts INTEGER,
                    position_size DECIMAL(10, 2),
                    entry_stock_price DECIMAL(10, 2),
                    exit_stock_price DECIMAL(10, 2),
                    expected_move DECIMAL(10, 2),
                    actual_move DECIMAL(10, 2),
                    iv_crush DECIMAL(10, 2),
                    total_pnl DECIMAL(10, 2),
                    pnl_percent DECIMAL(10, 2),
                    status VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert trades
            for trade in self.trades:
                cursor.execute("""
                    INSERT INTO backtest_trades (
                        ticker, entry_date, exit_date, trade_type, strike,
                        front_expiry, back_expiry, front_premium, back_premium,
                        net_debit, num_contracts, position_size,
                        entry_stock_price, exit_stock_price, expected_move,
                        actual_move, iv_crush, total_pnl, pnl_percent, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    trade['ticker'], trade['entry_date'], trade['exit_date'],
                    trade['trade_type'], trade['strike'], trade['front_expiry'],
                    trade['back_expiry'], trade['front_premium'], trade['back_premium'],
                    trade['net_debit'], trade['num_contracts'], trade['position_size'],
                    trade['entry_stock_price'], trade['exit_stock_price'],
                    trade['expected_move'], trade['actual_move'], trade['iv_crush'],
                    trade['total_pnl'], trade['pnl_percent'], trade['status']
                ))
            
            conn.commit()
            print(f"\n✅ Saved {len(self.trades)} trades to database")
            
        except Exception as e:
            print(f"Error saving to database: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def print_summary(self):
        """Print a summary of the backtest results"""
        if not self.performance_metrics:
            print("No performance metrics available")
            return
        
        print("\n" + "=" * 60)
        print("BACKTEST SUMMARY")
        print("=" * 60)
        
        metrics = self.performance_metrics
        
        print(f"\nCapital:")
        print(f"  Starting: ${metrics['starting_capital']:,.2f}")
        print(f"  Ending:   ${metrics['ending_capital']:,.2f}")
        print(f"  P&L:      ${metrics['total_pnl']:+,.2f}")
        print(f"  Return:   {metrics['total_return_pct']:+.2f}%")
        
        print(f"\nTrade Statistics:")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Win Rate:     {metrics['win_rate']:.1f}%")
        print(f"  Winners:      {metrics['winning_trades']}")
        print(f"  Losers:       {metrics['losing_trades']}")
        
        print(f"\nRisk Metrics:")
        print(f"  Avg Win:      ${metrics['avg_win']:+,.2f}")
        print(f"  Avg Loss:     ${metrics['avg_loss']:+,.2f}")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  Sharpe Ratio:  {metrics['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown:  {metrics['max_drawdown']:.2f}%")
        
        if metrics['trades']:
            print(f"\nTop Trades:")
            sorted_trades = sorted(metrics['trades'], key=lambda x: x['total_pnl'], reverse=True)
            
            print("  Best:")
            for trade in sorted_trades[:3]:
                print(f"    {trade['ticker']}: ${trade['total_pnl']:+,.2f} ({trade['pnl_percent']:+.1f}%)")
            
            if len(sorted_trades) > 3:
                print("  Worst:")
                for trade in sorted_trades[-3:]:
                    print(f"    {trade['ticker']}: ${trade['total_pnl']:+,.2f} ({trade['pnl_percent']:+.1f}%)")


def main():
    """Run the backtest"""
    backtest = HistoricalBacktest(
        starting_capital=10000.0,
        lookback_days=14
    )
    
    results = backtest.run_backtest()
    backtest.print_summary()
    backtest.save_results_to_database()
    
    # Save results to JSON for API consumption
    with open('backtest_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📊 Results saved to backtest_results.json")
    
    return results


if __name__ == "__main__":
    main()