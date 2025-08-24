#!/usr/bin/env python3
"""Compare priority scores between stocks from different dates"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.main import get_quick_analysis, calculate_priority_score_components


async def analyze_stocks():
    """Compare stocks from Aug 27 (high scores) vs Aug 28 (low scores)"""
    
    aug27_stocks = {
        'FL': 40.1,
        'NVDA': 37.9,
        'HPQ': 33.8,
        'BILL': 32.2,
        'DXLG': 40.9,  # CONSIDER stock
        'LFVN': 39.3   # CONSIDER stock
    }
    
    aug28_stocks = {
        'DELL': 6.5,
        'DG': 4.7,
        'AFRM': 4.6,
        'HRL': 4.0
    }
    
    print("=" * 120)
    print("PRIORITY SCORE COMPONENT ANALYSIS")
    print("=" * 120)
    
    print("\nAUGUST 27th STOCKS (High Priority Scores):")
    print("-" * 120)
    print(f"{'Ticker':<8} {'UI Score':<10} {'IV/RV':<12} {'Term Slope':<15} {'Volume':<15} {'Market Cap':<15} {'Analysis'}")
    print("-" * 120)
    
    for ticker, ui_score in aug27_stocks.items():
        try:
            analysis = await get_quick_analysis(ticker)
            if analysis and not analysis.get('error'):
                iv_rv = analysis.get('iv_rv_ratio_raw', 1.0)
                slope = analysis.get('term_structure_slope_raw', 0.0)
                volume = analysis.get('avg_volume_raw', 0)
                
                # Try to get market cap
                market_cap = 1e9  # Default 1B
                if 'market_cap' in analysis:
                    try:
                        market_cap = float(analysis['market_cap'])
                    except:
                        pass
                
                # Calculate components
                components = calculate_priority_score_components(iv_rv, slope, volume, market_cap)
                
                print(f"{ticker:<8} {ui_score:<10.1f} "
                      f"IV/RV: {iv_rv:5.2f} "
                      f"Slope: {slope:8.4f} "
                      f"Vol: {volume/1e6:6.1f}M "
                      f"MCap: {market_cap/1e9:6.1f}B "
                      f"[Calc: {components['priority_score']:5.1f}]")
                
                # Show component breakdown
                print(f"{'':8} {'':10} "
                      f"→ {components['iv_rv_score']:5.1f}pts "
                      f"→ {components['term_slope_score']:5.1f}pts "
                      f"→ {components['liquidity_score']:5.1f}pts "
                      f"→ {components['market_cap_score']:5.1f}pts")
                
        except Exception as e:
            print(f"{ticker:<8} Error: {str(e)[:80]}")
    
    print("\n\nAUGUST 28th STOCKS (Low Priority Scores):")
    print("-" * 120)
    print(f"{'Ticker':<8} {'UI Score':<10} {'IV/RV':<12} {'Term Slope':<15} {'Volume':<15} {'Market Cap':<15} {'Analysis'}")
    print("-" * 120)
    
    for ticker, ui_score in aug28_stocks.items():
        try:
            analysis = await get_quick_analysis(ticker)
            if analysis and not analysis.get('error'):
                iv_rv = analysis.get('iv_rv_ratio_raw', 1.0)
                slope = analysis.get('term_structure_slope_raw', 0.0)
                volume = analysis.get('avg_volume_raw', 0)
                
                # Try to get market cap
                market_cap = 1e9  # Default 1B
                if 'market_cap' in analysis:
                    try:
                        market_cap = float(analysis['market_cap'])
                    except:
                        pass
                
                # Calculate components
                components = calculate_priority_score_components(iv_rv, slope, volume, market_cap)
                
                print(f"{ticker:<8} {ui_score:<10.1f} "
                      f"IV/RV: {iv_rv:5.2f} "
                      f"Slope: {slope:8.4f} "
                      f"Vol: {volume/1e6:6.1f}M "
                      f"MCap: {market_cap/1e9:6.1f}B "
                      f"[Calc: {components['priority_score']:5.1f}]")
                
                # Show component breakdown
                print(f"{'':8} {'':10} "
                      f"→ {components['iv_rv_score']:5.1f}pts "
                      f"→ {components['term_slope_score']:5.1f}pts "
                      f"→ {components['liquidity_score']:5.1f}pts "
                      f"→ {components['market_cap_score']:5.1f}pts")
                
        except Exception as e:
            print(f"{ticker:<8} Error: {str(e)[:80]}")
    
    print("\n" + "=" * 120)
    print("KEY INSIGHTS:")
    print("-" * 120)
    print("1. IV/RV Ratio (40% weight): Scores = (ratio - 1.0) * 50, capped at 100")
    print("2. Term Slope (30% weight): Scores = abs(negative_slope) * 200, capped at 100")
    print("3. Liquidity (20% weight): Based on log10(volume) transformation")
    print("4. Market Cap (10% weight): Based on log10(market_cap) transformation")
    print("\nThe August 27th stocks likely have higher scores due to:")
    print("- Higher IV/RV ratios (implied vol much higher than realized vol)")
    print("- Steeper negative term structure slopes (front month premium)")
    print("- These are market conditions that vary by earnings date")
    print("=" * 120)


if __name__ == "__main__":
    asyncio.run(analyze_stocks())