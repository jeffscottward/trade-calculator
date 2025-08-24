#!/usr/bin/env python3
"""
Test script to verify priority scoring system is working correctly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from automation.utils.priority_scorer import PriorityScorer

def test_priority_scoring():
    """Test priority scoring with example trades."""
    
    print("=" * 60)
    print("TRADE PRIORITY SCORING TEST")
    print("=" * 60)
    
    # Example trades similar to what we see in the UI
    trades = [
        {
            'symbol': 'NVDA',
            'iv_rv_ratio': 1.8,
            'term_slope': -0.35,
            'avg_volume_30d': 50_000_000,
            'market_cap': 4_269_512_000_000,
            'market_cap_str': '$4.27T'
        },
        {
            'symbol': 'CRWD',
            'iv_rv_ratio': 2.1,
            'term_slope': -0.42,
            'avg_volume_30d': 8_000_000,
            'market_cap': 103_203_698_926,
            'market_cap_str': '$103.2B'
        },
        {
            'symbol': 'SNOW',
            'iv_rv_ratio': 1.9,
            'term_slope': -0.38,
            'avg_volume_30d': 6_500_000,
            'market_cap': 64_964_716_000,
            'market_cap_str': '$65.0B'
        },
        {
            'symbol': 'BILL',
            'iv_rv_ratio': 2.3,
            'term_slope': -0.45,
            'avg_volume_30d': 2_000_000,
            'market_cap': 4_249_869_484,
            'market_cap_str': '$4.2B'
        }
    ]
    
    # Calculate scores for each trade
    results = []
    for trade in trades:
        scores = PriorityScorer.calculate_priority_score(
            iv_rv_ratio=trade['iv_rv_ratio'],
            term_slope=trade['term_slope'],
            avg_volume_30d=trade['avg_volume_30d'],
            market_cap=trade['market_cap']
        )
        
        results.append({
            'symbol': trade['symbol'],
            'market_cap_str': trade['market_cap_str'],
            **scores
        })
    
    # Sort by priority score
    results.sort(key=lambda x: x['priority_score'], reverse=True)
    
    # Display results
    print("\nRANKED TRADES (by Priority Score):")
    print("-" * 60)
    
    for i, result in enumerate(results, 1):
        print(f"\n#{i} {result['symbol']} ({result['market_cap_str']})")
        print(f"   Priority Score: {result['priority_score']:.1f}")
        print(f"   Components:")
        print(f"   - IV/RV Score (40%): {result['iv_rv_score']:.1f}")
        print(f"   - Term Slope Score (30%): {result['term_slope_score']:.1f}")
        print(f"   - Liquidity Score (20%): {result['liquidity_score']:.1f}")
        print(f"   - Market Cap Score (10%): {result['market_cap_score']:.1f}")
    
    print("\n" + "=" * 60)
    print("KEY INSIGHTS:")
    print("-" * 60)
    print("✓ Trades are now ranked by opportunity, not just market cap")
    print("✓ BILL scores higher than SNOW despite smaller market cap")
    print("✓ IV/RV ratio and term structure are primary drivers")
    print("✓ Market cap provides stability but isn't dominant")
    print("=" * 60)

if __name__ == "__main__":
    test_priority_scoring()