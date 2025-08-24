"""
Tests for the Priority Scoring System

Verifies that trade ranking calculations work correctly.
"""

import pytest
from automation.utils.priority_scorer import PriorityScorer


class TestPriorityScorer:
    """Test suite for priority score calculations."""
    
    def test_iv_rv_score_calculation(self):
        """Test IV/RV ratio scoring."""
        # Test various IV/RV ratios
        assert PriorityScorer.calculate_iv_rv_score(0.8) == 0.0  # Below 1.0
        assert PriorityScorer.calculate_iv_rv_score(1.0) == 0.0  # Exactly 1.0
        assert PriorityScorer.calculate_iv_rv_score(1.5) == 25.0  # 1.5
        assert PriorityScorer.calculate_iv_rv_score(2.0) == 50.0  # 2.0
        assert PriorityScorer.calculate_iv_rv_score(3.0) == 100.0  # 3.0 (max)
        assert PriorityScorer.calculate_iv_rv_score(4.0) == 100.0  # Above max
    
    def test_term_slope_score_calculation(self):
        """Test term structure slope scoring."""
        # Test various slopes
        assert PriorityScorer.calculate_term_slope_score(0.1) == 0.0  # Positive slope
        assert PriorityScorer.calculate_term_slope_score(0.0) == 0.0  # Flat
        assert PriorityScorer.calculate_term_slope_score(-0.1) == 20.0  # Small negative
        assert PriorityScorer.calculate_term_slope_score(-0.3) == 60.0  # Medium negative
        assert PriorityScorer.calculate_term_slope_score(-0.5) == 100.0  # Large negative
        assert PriorityScorer.calculate_term_slope_score(-1.0) == 100.0  # Very large (capped)
    
    def test_liquidity_score_calculation(self):
        """Test liquidity/volume scoring."""
        # Test various volumes
        assert PriorityScorer.calculate_liquidity_score(500_000) == 0.0  # Below 1M
        assert PriorityScorer.calculate_liquidity_score(1_000_000) == 0.0  # Exactly 1M
        assert PriorityScorer.calculate_liquidity_score(10_000_000) == 50.0  # 10M
        assert PriorityScorer.calculate_liquidity_score(100_000_000) == 100.0  # 100M
        
        # Test with options volume bonus
        score_with_options = PriorityScorer.calculate_liquidity_score(
            10_000_000, options_volume=50_000
        )
        assert score_with_options > 50.0  # Should be higher than without options
    
    def test_market_cap_score_calculation(self):
        """Test market cap scoring."""
        # Test various market caps
        assert PriorityScorer.calculate_market_cap_score(500_000_000) == 0.0  # $500M
        assert PriorityScorer.calculate_market_cap_score(1_000_000_000) == 0.0  # $1B
        assert abs(PriorityScorer.calculate_market_cap_score(10_000_000_000) - 33.33) < 0.01  # $10B
        assert abs(PriorityScorer.calculate_market_cap_score(100_000_000_000) - 66.66) < 0.01  # $100B
        assert abs(PriorityScorer.calculate_market_cap_score(1_000_000_000_000) - 100.0) < 0.1  # $1T
    
    def test_overall_priority_score(self):
        """Test complete priority score calculation."""
        # Test a typical good trade
        scores = PriorityScorer.calculate_priority_score(
            iv_rv_ratio=1.8,      # Good IV/RV
            term_slope=-0.35,     # Good backwardation
            avg_volume_30d=25_000_000,  # Good liquidity
            market_cap=50_000_000_000   # Mid-cap
        )
        
        assert 'priority_score' in scores
        assert 'iv_rv_score' in scores
        assert 'term_slope_score' in scores
        assert 'liquidity_score' in scores
        assert 'market_cap_score' in scores
        
        # Check that priority score is weighted correctly
        expected = (
            scores['iv_rv_score'] * 0.40 +
            scores['term_slope_score'] * 0.30 +
            scores['liquidity_score'] * 0.20 +
            scores['market_cap_score'] * 0.10
        )
        assert abs(scores['priority_score'] - expected) < 0.01
    
    def test_parse_market_cap_string(self):
        """Test market cap string parsing."""
        assert PriorityScorer.parse_market_cap_string('$1.5B') == 1_500_000_000
        assert PriorityScorer.parse_market_cap_string('$500M') == 500_000_000
        assert PriorityScorer.parse_market_cap_string('$2.3T') == 2_300_000_000_000
        assert PriorityScorer.parse_market_cap_string('$1,234,567') == 1_234_567
        assert PriorityScorer.parse_market_cap_string('-') == 0
        assert PriorityScorer.parse_market_cap_string('') == 0
        assert PriorityScorer.parse_market_cap_string(None) == 0
    
    def test_ranking_order(self):
        """Test that scores produce correct ranking order."""
        # Create three trades with different characteristics
        trade_a = PriorityScorer.calculate_priority_score(
            iv_rv_ratio=2.5,  # Excellent
            term_slope=-0.4,  # Excellent
            avg_volume_30d=50_000_000,  # Good
            market_cap=100_000_000_000  # Large cap
        )
        
        trade_b = PriorityScorer.calculate_priority_score(
            iv_rv_ratio=1.3,  # Okay
            term_slope=-0.2,  # Okay
            avg_volume_30d=5_000_000,  # Low
            market_cap=10_000_000_000  # Small cap
        )
        
        trade_c = PriorityScorer.calculate_priority_score(
            iv_rv_ratio=1.8,  # Good
            term_slope=-0.3,  # Good
            avg_volume_30d=20_000_000,  # Medium
            market_cap=500_000_000_000  # Mega cap
        )
        
        # Trade A should score highest (best IV/RV and term structure)
        assert trade_a['priority_score'] > trade_c['priority_score']
        assert trade_c['priority_score'] > trade_b['priority_score']
    
    def test_edge_cases(self):
        """Test edge cases and invalid inputs."""
        # Test with zeros
        scores = PriorityScorer.calculate_priority_score(
            iv_rv_ratio=0,
            term_slope=0,
            avg_volume_30d=0,
            market_cap=0
        )
        assert scores['priority_score'] == 0.0
        
        # Test with very large values
        scores = PriorityScorer.calculate_priority_score(
            iv_rv_ratio=10.0,
            term_slope=-5.0,
            avg_volume_30d=1_000_000_000,
            market_cap=10_000_000_000_000
        )
        # All component scores should be capped at 100
        assert scores['iv_rv_score'] <= 100.0
        assert scores['term_slope_score'] <= 100.0
        assert scores['liquidity_score'] <= 100.0
        assert scores['market_cap_score'] <= 100.0
        assert scores['priority_score'] <= 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])