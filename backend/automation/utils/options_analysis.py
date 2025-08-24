"""
Options chain analysis utilities for term structure and pricing.
"""

import numpy as np
from scipy.interpolate import interp1d
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf


def analyze_term_structure(ticker: yf.Ticker, expiration_dates: List[str]) -> Dict:
    """
    Analyze the implied volatility term structure.
    
    Args:
        ticker: yfinance Ticker object
        expiration_dates: List of option expiration dates
    
    Returns:
        Dictionary with term structure analysis including slope
    """
    try:
        current_price = ticker.history(period='1d')['Close'].iloc[-1]
        today = datetime.now().date()
        
        ivs = []
        days_to_expiry = []
        
        for exp_date in expiration_dates[:5]:  # Analyze first 5 expirations
            # Calculate days to expiry
            exp_dt = datetime.strptime(exp_date, '%Y-%m-%d').date()
            dte = (exp_dt - today).days
            
            if dte <= 0:
                continue
            
            # Get options chain
            try:
                options = ticker.option_chain(exp_date)
                
                # Find ATM implied volatility
                atm_iv = get_atm_iv(options, current_price)
                
                if atm_iv > 0:
                    ivs.append(atm_iv)
                    days_to_expiry.append(dte)
                    
            except Exception as e:
                print(f"Error getting options for {exp_date}: {e}")
                continue
        
        if len(ivs) < 2:
            return {'slope': 0, 'ivs': [], 'days': []}
        
        # Calculate slope between nearest and 45+ day expiration
        nearest_idx = 0
        far_idx = -1
        
        for i, dte in enumerate(days_to_expiry):
            if dte >= 45:
                far_idx = i
                break
        
        if far_idx == -1:
            far_idx = len(days_to_expiry) - 1
        
        # Calculate slope
        slope = (ivs[far_idx] - ivs[nearest_idx]) / (days_to_expiry[far_idx] - days_to_expiry[nearest_idx])
        
        return {
            'slope': slope,
            'ivs': ivs,
            'days': days_to_expiry,
            'nearest_iv': ivs[nearest_idx],
            'far_iv': ivs[far_idx] if far_idx < len(ivs) else ivs[-1]
        }
        
    except Exception as e:
        print(f"Error analyzing term structure: {e}")
        return {'slope': 0, 'ivs': [], 'days': []}


def get_atm_iv(options, current_price: float) -> float:
    """
    Get the at-the-money implied volatility.
    
    Args:
        options: Option chain from yfinance
        current_price: Current stock price
    
    Returns:
        ATM implied volatility
    """
    calls = options.calls
    puts = options.puts
    
    if calls.empty or puts.empty:
        return 0.0
    
    # Find closest call strike
    call_idx = (calls['strike'] - current_price).abs().idxmin()
    call_iv = calls.loc[call_idx, 'impliedVolatility']
    
    # Find closest put strike  
    put_idx = (puts['strike'] - current_price).abs().idxmin()
    put_iv = puts.loc[put_idx, 'impliedVolatility']
    
    # Return average of call and put IV
    return (call_iv + put_iv) / 2


def build_iv_surface(ticker: yf.Ticker, expiration_dates: List[str]) -> Dict:
    """
    Build implied volatility surface for multiple strikes and expirations.
    
    Args:
        ticker: yfinance Ticker object
        expiration_dates: List of expiration dates
    
    Returns:
        Dictionary with IV surface data
    """
    try:
        current_price = ticker.history(period='1d')['Close'].iloc[-1]
        surface = {'strikes': [], 'expirations': [], 'ivs': []}
        
        for exp_date in expiration_dates[:5]:
            options = ticker.option_chain(exp_date)
            
            # Combine calls and puts
            all_strikes = set(options.calls['strike'].tolist() + options.puts['strike'].tolist())
            
            # Filter strikes within 20% of current price
            relevant_strikes = [s for s in all_strikes 
                              if 0.8 * current_price <= s <= 1.2 * current_price]
            
            for strike in sorted(relevant_strikes):
                # Get IV for this strike
                call_iv = options.calls[options.calls['strike'] == strike]['impliedVolatility'].values
                put_iv = options.puts[options.puts['strike'] == strike]['impliedVolatility'].values
                
                if len(call_iv) > 0 and len(put_iv) > 0:
                    avg_iv = (call_iv[0] + put_iv[0]) / 2
                    surface['strikes'].append(strike)
                    surface['expirations'].append(exp_date)
                    surface['ivs'].append(avg_iv)
        
        return surface
        
    except Exception as e:
        print(f"Error building IV surface: {e}")
        return {'strikes': [], 'expirations': [], 'ivs': []}


def calculate_calendar_spread_price(ticker: yf.Ticker, front_expiry: str, 
                                   back_expiry: str, strike: Optional[float] = None) -> Dict:
    """
    Calculate the price of a calendar spread.
    
    Args:
        ticker: yfinance Ticker object
        front_expiry: Front month expiration date
        back_expiry: Back month expiration date
        strike: Strike price (uses ATM if not specified)
    
    Returns:
        Dictionary with spread pricing details
    """
    try:
        current_price = ticker.history(period='1d')['Close'].iloc[-1]
        
        # Use ATM strike if not specified
        if strike is None:
            strike = round(current_price / 5) * 5  # Round to nearest $5
        
        # Get options chains
        front_options = ticker.option_chain(front_expiry)
        back_options = ticker.option_chain(back_expiry)
        
        # Get call prices
        front_call = front_options.calls[front_options.calls['strike'] == strike]
        back_call = back_options.calls[back_options.calls['strike'] == strike]
        
        if front_call.empty or back_call.empty:
            return {'error': 'Strike not available'}
        
        # Calculate spread price (debit)
        front_bid = front_call['bid'].iloc[0]
        back_ask = back_call['ask'].iloc[0]
        
        spread_price = back_ask - front_bid  # Buy back, sell front
        
        # Calculate max profit (if front expires worthless)
        max_profit = front_call['ask'].iloc[0] - front_call['bid'].iloc[0]
        
        return {
            'strike': strike,
            'front_expiry': front_expiry,
            'back_expiry': back_expiry,
            'spread_price': spread_price,
            'front_price': (front_call['bid'].iloc[0] + front_call['ask'].iloc[0]) / 2,
            'back_price': (back_call['bid'].iloc[0] + back_call['ask'].iloc[0]) / 2,
            'max_profit': max_profit,
            'current_stock_price': current_price
        }
        
    except Exception as e:
        return {'error': str(e)}


def find_optimal_calendar_strikes(ticker: yf.Ticker, front_expiry: str, 
                                 back_expiry: str, num_strikes: int = 5) -> List[Dict]:
    """
    Find optimal strikes for calendar spread based on liquidity and pricing.
    
    Args:
        ticker: yfinance Ticker object
        front_expiry: Front month expiration
        back_expiry: Back month expiration
        num_strikes: Number of strikes to analyze
    
    Returns:
        List of strike analysis dictionaries
    """
    try:
        current_price = ticker.history(period='1d')['Close'].iloc[-1]
        
        # Get options chains
        front_options = ticker.option_chain(front_expiry)
        back_options = ticker.option_chain(back_expiry)
        
        # Find liquid strikes near ATM
        front_strikes = set(front_options.calls['strike'].tolist())
        back_strikes = set(back_options.calls['strike'].tolist())
        common_strikes = front_strikes.intersection(back_strikes)
        
        # Filter strikes within 10% of current price
        relevant_strikes = [s for s in common_strikes
                          if 0.9 * current_price <= s <= 1.1 * current_price]
        
        strike_analysis = []
        
        for strike in sorted(relevant_strikes)[:num_strikes]:
            # Analyze each strike
            front_call = front_options.calls[front_options.calls['strike'] == strike]
            back_call = back_options.calls[back_options.calls['strike'] == strike]
            
            if not front_call.empty and not back_call.empty:
                front_volume = front_call['volume'].iloc[0]
                back_volume = back_call['volume'].iloc[0]
                
                # Calculate spread metrics
                front_mid = (front_call['bid'].iloc[0] + front_call['ask'].iloc[0]) / 2
                back_mid = (back_call['bid'].iloc[0] + back_call['ask'].iloc[0]) / 2
                spread_price = back_mid - front_mid
                
                strike_analysis.append({
                    'strike': strike,
                    'spread_price': spread_price,
                    'front_volume': front_volume,
                    'back_volume': back_volume,
                    'total_volume': front_volume + back_volume,
                    'moneyness': (strike - current_price) / current_price
                })
        
        # Sort by total volume (liquidity)
        strike_analysis.sort(key=lambda x: x['total_volume'], reverse=True)
        
        return strike_analysis
        
    except Exception as e:
        print(f"Error finding optimal strikes: {e}")
        return []