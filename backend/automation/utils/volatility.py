"""
Volatility calculation utilities including Yang-Zhang estimator.
"""

import numpy as np
import pandas as pd
from typing import Optional


def calculate_yang_zhang(price_data: pd.DataFrame, window: int = 30, 
                         trading_periods: int = 252) -> float:
    """
    Calculate Yang-Zhang volatility estimator.
    
    This is more accurate than simple close-to-close volatility as it uses
    OHLC data to capture intraday price movements.
    
    Args:
        price_data: DataFrame with OHLC data
        window: Lookback window in days
        trading_periods: Number of trading periods per year
    
    Returns:
        Annualized volatility as a decimal (e.g., 0.30 for 30%)
    """
    if len(price_data) < window:
        # Use all available data if less than window
        window = len(price_data)
    
    # Calculate log returns
    log_ho = np.log(price_data['High'] / price_data['Open'])
    log_lo = np.log(price_data['Low'] / price_data['Open'])
    log_co = np.log(price_data['Close'] / price_data['Open'])
    
    log_oc = np.log(price_data['Open'] / price_data['Close'].shift(1))
    log_oc_sq = log_oc ** 2
    
    log_cc = np.log(price_data['Close'] / price_data['Close'].shift(1))
    log_cc_sq = log_cc ** 2
    
    # Rogers-Satchell volatility
    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
    
    # Calculate components
    close_vol = log_cc_sq.rolling(window=window, center=False).sum() * (1.0 / (window - 1.0))
    open_vol = log_oc_sq.rolling(window=window, center=False).sum() * (1.0 / (window - 1.0))
    window_rs = rs.rolling(window=window, center=False).sum() * (1.0 / (window - 1.0))
    
    # Yang-Zhang formula
    k = 0.34 / (1.34 + ((window + 1) / (window - 1)))
    result = np.sqrt(open_vol + k * close_vol + (1 - k) * window_rs) * np.sqrt(trading_periods)
    
    # Return the most recent value
    return result.iloc[-1] if not result.empty else 0.0


def calculate_historical_volatility(price_data: pd.DataFrame, window: int = 30,
                                   trading_periods: int = 252) -> float:
    """
    Calculate simple historical volatility using close-to-close returns.
    
    Args:
        price_data: DataFrame with at least 'Close' column
        window: Lookback window in days
        trading_periods: Number of trading periods per year
    
    Returns:
        Annualized volatility as a decimal
    """
    if len(price_data) < window:
        window = len(price_data)
    
    # Calculate log returns
    log_returns = np.log(price_data['Close'] / price_data['Close'].shift(1))
    
    # Calculate rolling standard deviation
    vol = log_returns.rolling(window=window).std() * np.sqrt(trading_periods)
    
    return vol.iloc[-1] if not vol.empty else 0.0


def calculate_iv_rv_ratio(ticker, nearest_expiry: str, realized_vol: float) -> float:
    """
    Calculate the ratio of implied volatility to realized volatility.
    
    Args:
        ticker: yfinance Ticker object
        nearest_expiry: Nearest expiration date string
        realized_vol: Realized (historical) volatility
    
    Returns:
        IV/RV ratio
    """
    try:
        # Get options chain for nearest expiry
        options = ticker.option_chain(nearest_expiry)
        
        # Get current stock price
        current_price = ticker.history(period='1d')['Close'].iloc[-1]
        
        # Find ATM options
        calls = options.calls
        puts = options.puts
        
        if calls.empty or puts.empty:
            return 0.0
        
        # Find closest strikes to current price
        call_idx = (calls['strike'] - current_price).abs().idxmin()
        put_idx = (puts['strike'] - current_price).abs().idxmin()
        
        # Get implied volatilities
        call_iv = calls.loc[call_idx, 'impliedVolatility']
        put_iv = puts.loc[put_idx, 'impliedVolatility']
        
        # Average IV of ATM call and put
        atm_iv = (call_iv + put_iv) / 2
        
        # Calculate ratio
        if realized_vol > 0:
            return atm_iv / realized_vol
        else:
            return 0.0
            
    except Exception as e:
        print(f"Error calculating IV/RV ratio: {e}")
        return 0.0


def calculate_parkinson_volatility(price_data: pd.DataFrame, window: int = 30,
                                   trading_periods: int = 252) -> float:
    """
    Calculate Parkinson volatility using high-low prices.
    
    This estimator is more efficient than close-to-close but doesn't
    account for drift or opening gaps.
    
    Args:
        price_data: DataFrame with High and Low columns
        window: Lookback window in days
        trading_periods: Number of trading periods per year
    
    Returns:
        Annualized volatility as a decimal
    """
    if len(price_data) < window:
        window = len(price_data)
    
    # Calculate log of high/low ratio
    hl_ratio = np.log(price_data['High'] / price_data['Low']) ** 2
    
    # Parkinson constant
    constant = 1.0 / (4.0 * np.log(2.0))
    
    # Calculate volatility
    vol = np.sqrt(constant * hl_ratio.rolling(window=window).mean()) * np.sqrt(trading_periods)
    
    return vol.iloc[-1] if not vol.empty else 0.0