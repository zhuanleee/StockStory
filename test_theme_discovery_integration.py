"""
Test Theme Discovery Integration

Tests the enhanced theme scoring with supply chain role detection.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.story_scoring import StoryScorer

def test_supply_chain_roles():
    """Test that supply chain roles are detected and applied correctly."""

    scorer = StoryScorer()

    # Test cases: (ticker, theme_name, expected_role)
    test_cases = [
        ('NVDA', 'AI Infrastructure', 'leader'),  # NVDA is AI leader
        ('ASML', 'AI Infrastructure', 'supplier'),  # ASML is chip equipment supplier
        ('SMCI', 'AI Infrastructure', 'equipment'),  # SMCI makes servers
        ('PLTR', 'AI Infrastructure', 'beneficiary'),  # PLTR benefits from AI
        ('EQIX', 'AI Infrastructure', 'infrastructure'),  # EQIX data centers
        ('CCJ', 'Nuclear', 'supplier'),  # CCJ is uranium supplier
        ('CEG', 'Nuclear', 'leader'),  # CEG is nuclear leader
        ('LMT', 'Defense', 'leader'),  # LMT is defense leader
    ]

    print("\n" + "="*70)
    print("Testing Supply Chain Role Detection")
    print("="*70 + "\n")

    for ticker, theme_name, expected_role in test_cases:
        role = scorer._detect_supply_chain_role(ticker, theme_name)

        if role:
            role_value = role.value
            status = "✓" if role_value == expected_role else "✗"
            print(f"{status} {ticker:6} in {theme_name:20} → {role_value:15} (expected: {expected_role})")
        else:
            status = "✗" if expected_role else "✓"
            print(f"{status} {ticker:6} in {theme_name:20} → Not found (expected: {expected_role})")

    print("\n" + "="*70)
    print("Testing Theme Tier Detection with Role Multipliers")
    print("="*70 + "\n")

    # Test tier detection with news
    news = [
        {'title': 'NVIDIA Announces New AI Chip', 'summary': 'Artificial intelligence breakthrough'},
    ]

    # Mock theme data
    theme_data = [
        {
            'theme_id': 'ai_infrastructure',
            'theme_name': 'AI Infrastructure',
            'role': 'driver',
            'stage': 'early',
            'confidence': 0.95
        }
    ]

    test_tickers = ['NVDA', 'ASML', 'SMCI', 'EQIX']

    for ticker in test_tickers:
        tier, theme, freshness, multiplier = scorer.detect_theme_tier(news, ticker, theme_data)
        print(f"{ticker:6} → Tier: {tier.value:10} | Theme: {theme:20} | Freshness: {freshness:3.0f} | Multiplier: {multiplier:.2f}")

    print("\n" + "="*70)
    print("Testing Full Story Score Calculation")
    print("="*70 + "\n")

    # Test full story score for leaders vs suppliers
    price_data = {
        'above_20': True,
        'above_50': True,
        'above_200': True,
        'vol_ratio': 2.5,
        'distance_from_20sma_pct': 3.0,
        'breakout_up': False,
        'in_squeeze': False,
    }

    sec_data = {'has_8k': False, 'insider_activity': False}

    for ticker in ['NVDA', 'ASML']:
        result = scorer.calculate_story_score(
            ticker=ticker,
            news=news,
            sec_data=sec_data,
            theme_data=theme_data,
            price_data=price_data
        )

        print(f"\n{ticker} Story Score:")
        print(f"  Total Score:      {result.total_score:.1f}/100")
        print(f"  Theme Strength:   {result.theme_strength:.1f}")
        print(f"  Story Quality:    {result.story_quality_score:.1f}")
        print(f"  Primary Theme:    {result.primary_theme}")

    print("\n" + "="*70)
    print("✓ All theme discovery integration tests complete!")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_supply_chain_roles()
