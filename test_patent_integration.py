"""
Test Patent Integration

Tests patent activity as an institutional narrative signal.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.story_scoring import StoryScorer

def test_patent_integration():
    """Test that patents enhance institutional narrative score."""

    scorer = StoryScorer()

    print("\n" + "="*70)
    print("Testing Patent Integration")
    print("="*70 + "\n")

    # Test with tech companies known for patent activity
    tech_tickers = ['NVDA', 'AMD', 'GOOGL', 'AAPL', 'MSFT']

    for ticker in tech_tickers:
        print(f"\nChecking {ticker} for patent activity...")

        # Call calculate_institutional_narrative
        news = []  # Empty news for isolated test

        score = scorer.calculate_institutional_narrative(news, ticker)

        if score > 10:  # 10 is baseline with no matches
            print(f"  ✓ {ticker}: Institutional narrative boosted by patents (score: {score})")
        else:
            print(f"  - {ticker}: No patent boost detected (score: {score})")

    print("\n" + "="*70)
    print("Testing Full Story Score with Patents")
    print("="*70 + "\n")

    # Test full story score for a tech company
    ticker = 'NVDA'

    news = [
        {'title': 'NVIDIA AI Breakthrough', 'summary': 'New GPU architecture'},
    ]

    sec_data = {'has_8k': False, 'insider_activity': False}

    theme_data = [
        {
            'theme_id': 'ai_infrastructure',
            'theme_name': 'AI Infrastructure',
            'role': 'driver',
            'stage': 'early',
            'confidence': 0.95
        }
    ]

    price_data = {
        'above_20': True,
        'above_50': True,
        'above_200': True,
        'vol_ratio': 2.0,
        'distance_from_20sma_pct': 3.0,
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
    print(f"  Total Score:              {result.total_score:.1f}/100")
    print(f"  Institutional Narrative:  {result.institutional_narrative:.1f}")
    print(f"  Story Quality:            {result.story_quality_score:.1f}")

    if result.institutional_narrative > 10:
        print("\n  ✅ Patent activity detected and contributing to score!")
    else:
        print("\n  ⚠️  No patent activity detected (may need API key)")

    print("\n" + "="*70)
    print("Patent Integration Summary")
    print("="*70)
    print("\nPatent tracking adds innovation signal to story scoring:")
    print("  • Recent patents (last 6 months) boost institutional narrative")
    print("  • 1-3 patents: +5 points")
    print("  • 4-10 patents: +10 points")
    print("  • 11+ patents: +15 points")
    print("  • Particularly valuable for tech/biotech sectors")
    print("\nNote: Requires PATENTSVIEW_API_KEY env var for live data")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_patent_integration()
