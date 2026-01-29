"""
Test Government Contracts Integration

Tests the integration of government contracts as a catalyst source in story scoring.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.story_scoring import StoryScorer, CatalystType
from datetime import datetime, timedelta

def test_government_contracts_catalyst():
    """Test that government contracts are detected as catalysts."""

    scorer = StoryScorer()

    print("\n" + "="*70)
    print("Testing Government Contracts as Catalyst Source")
    print("="*70 + "\n")

    # Test with defense contractor tickers
    defense_tickers = ['LMT', 'RTX', 'NOC', 'GD']

    for ticker in defense_tickers:
        print(f"\nChecking {ticker} for government contracts...")

        # Call detect_catalyst with ticker
        news = []  # Empty news for isolated test
        sec_data = {'has_8k': False, 'insider_activity': False}

        catalyst_type, score, recency, desc, date = scorer.detect_catalyst(
            news=news,
            sec_data=sec_data,
            ticker=ticker
        )

        if catalyst_type == CatalystType.MAJOR_CONTRACT:
            print(f"  ✓ {ticker}: MAJOR_CONTRACT catalyst detected!")
            print(f"    Description: {desc}")
            print(f"    Score: {score}")
            print(f"    Date: {date}")
        else:
            print(f"  - {ticker}: No major contract catalyst (type: {catalyst_type.value})")

    print("\n" + "="*70)
    print("Testing Full Story Score with Contracts")
    print("="*70 + "\n")

    # Test full story score for a defense contractor
    ticker = 'LMT'

    news = [
        {'title': 'Lockheed Martin Defense Contract', 'summary': 'Military equipment order'},
    ]

    sec_data = {'has_8k': False, 'insider_activity': False}

    theme_data = [
        {
            'theme_id': 'defense_tech',
            'theme_name': 'Defense Tech',
            'role': 'driver',
            'stage': 'early',
            'confidence': 0.90
        }
    ]

    price_data = {
        'above_20': True,
        'above_50': True,
        'above_200': True,
        'vol_ratio': 1.5,
        'distance_from_20sma_pct': 2.0,
        'breakout_up': False,
        'in_squeeze': False,
    }

    result = scorer.calculate_story_score(
        ticker=ticker,
        news=news,
        sec_data=sec_data,
        theme_data=theme_data,
        price_data=price_data
    )

    print(f"{ticker} Story Score:")
    print(f"  Total Score:        {result.total_score:.1f}/100")
    print(f"  Catalyst Type:      {result.catalyst_type}")
    print(f"  Catalyst Score:     {result.catalyst_score:.1f}")
    print(f"  Primary Catalyst:   {result.primary_catalyst}")
    print(f"  Catalyst Type Score: {result.catalyst_type_score:.1f}")

    if result.catalyst_type_score >= 95:  # MAJOR_CONTRACT score
        print("\n  ✅ Government contract detected as major catalyst!")
    else:
        print("\n  ⚠️  Government contract may not have been detected")

    print("\n" + "="*70)
    print("✓ Government contracts integration test complete!")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_government_contracts_catalyst()
