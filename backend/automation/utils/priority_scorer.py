"""
Trade Priority Scoring System

Calculates priority scores for ranking earnings trades based on:
- IV/RV ratio (40%) - How overpriced the volatility is
- Term structure slope (30%) - Steepness of backwardation
- Liquidity (20%) - Trading volume and options activity
- Market cap (10%) - Company size/stability

Higher scores indicate better trade opportunities.
"""

import math
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PriorityScorer:
    """Calculate priority scores for trade ranking."""
    
    # Component weights (must sum to 1.0)
    IV_RV_WEIGHT = 0.40
    TERM_SLOPE_WEIGHT = 0.30
    LIQUIDITY_WEIGHT = 0.20
    MARKET_CAP_WEIGHT = 0.10
    
    @staticmethod
    def calculate_iv_rv_score(iv_rv_ratio: float) -> float:
        """
        Calculate IV/RV ratio score (0-100).
        
        Higher ratios indicate more overpriced volatility.
        - 1.0 = 0 points (fairly priced)
        - 1.5 = 25 points
        - 2.0 = 50 points
        - 3.0+ = 100 points
        """
        if iv_rv_ratio <= 1.0:
            return 0.0
        
        # Scale: each 0.02 above 1.0 adds 1 point, max 100
        score = (iv_rv_ratio - 1.0) * 50
        return min(100.0, max(0.0, score))
    
    @staticmethod
    def calculate_term_slope_score(term_slope: float) -> float:
        """
        Calculate term structure slope score (0-100).
        
        More negative slopes indicate better opportunities.
        - 0.0 = 0 points (flat structure)
        - -0.3 = 60 points
        - -0.5+ = 100 points
        """
        if term_slope >= 0:
            return 0.0
        
        # Use absolute value, scale by 200
        score = abs(term_slope) * 200
        return min(100.0, max(0.0, score))
    
    @staticmethod
    def calculate_liquidity_score(avg_volume_30d: float, 
                                 options_volume: Optional[float] = None) -> float:
        """
        Calculate liquidity score (0-100).
        
        Based on 30-day average volume and optional options volume.
        - < 1M shares/day = 0 points
        - 10M shares/day = 50 points
        - 100M+ shares/day = 100 points
        """
        if avg_volume_30d < 1_000_000:
            return 0.0
        
        # Logarithmic scale for volume
        # log10(1M) = 6, log10(100M) = 8
        log_volume = math.log10(avg_volume_30d)
        score = (log_volume - 6) * 50  # Maps 6->0, 8->100
        
        # Bonus for high options volume if provided
        if options_volume and options_volume > 10000:
            options_bonus = min(10, math.log10(options_volume / 1000))
            score += options_bonus
        
        return min(100.0, max(0.0, score))
    
    @staticmethod
    def calculate_market_cap_score(market_cap: float) -> float:
        """
        Calculate market cap score (0-100).
        
        Larger companies provide more stability.
        - < $1B = 0 points
        - $10B = 20 points
        - $100B = 40 points
        - $1T+ = 100 points
        """
        if market_cap < 1_000_000_000:  # Less than $1B
            return 0.0
        
        # Logarithmic scale
        # log10(1B) = 9, log10(1T) = 12
        log_cap = math.log10(market_cap)
        score = (log_cap - 9) * 33.33  # Maps 9->0, 12->100
        
        return min(100.0, max(0.0, score))
    
    @classmethod
    def calculate_priority_score(cls, 
                                iv_rv_ratio: float,
                                term_slope: float,
                                avg_volume_30d: float,
                                market_cap: float,
                                options_volume: Optional[float] = None) -> Dict[str, float]:
        """
        Calculate overall priority score and component scores.
        
        Returns dict with:
        - priority_score: Overall score (0-100)
        - iv_rv_score: IV/RV component
        - term_slope_score: Term structure component
        - liquidity_score: Liquidity component
        - market_cap_score: Market cap component
        """
        # Calculate individual components
        iv_rv_score = cls.calculate_iv_rv_score(iv_rv_ratio)
        term_slope_score = cls.calculate_term_slope_score(term_slope)
        liquidity_score = cls.calculate_liquidity_score(avg_volume_30d, options_volume)
        market_cap_score = cls.calculate_market_cap_score(market_cap)
        
        # Calculate weighted total
        priority_score = (
            iv_rv_score * cls.IV_RV_WEIGHT +
            term_slope_score * cls.TERM_SLOPE_WEIGHT +
            liquidity_score * cls.LIQUIDITY_WEIGHT +
            market_cap_score * cls.MARKET_CAP_WEIGHT
        )
        
        # Round to 2 decimal places
        return {
            'priority_score': round(priority_score, 2),
            'iv_rv_score': round(iv_rv_score, 2),
            'term_slope_score': round(term_slope_score, 2),
            'liquidity_score': round(liquidity_score, 2),
            'market_cap_score': round(market_cap_score, 2)
        }
    
    @staticmethod
    def parse_market_cap_string(market_cap_str: str) -> float:
        """
        Parse market cap string like '$1.5B' or '$500M' to numeric value.
        """
        if not market_cap_str:
            return 0
        
        # Remove $ and commas
        clean_str = market_cap_str.replace('$', '').replace(',', '').strip()
        
        if not clean_str or clean_str == '-':
            return 0
        
        try:
            # Handle B for billions, M for millions, T for trillions
            if clean_str.endswith('T'):
                return float(clean_str[:-1]) * 1_000_000_000_000
            elif clean_str.endswith('B'):
                return float(clean_str[:-1]) * 1_000_000_000
            elif clean_str.endswith('M'):
                return float(clean_str[:-1]) * 1_000_000
            else:
                return float(clean_str)
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse market cap: {market_cap_str}")
            return 0