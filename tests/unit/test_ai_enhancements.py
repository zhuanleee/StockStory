#!/usr/bin/env python3
"""
Test AI Enhancements - All 8 Features

Tests:
2. Trading Signal Explanations
3. Earnings Call Analysis
4. Market Health Narrative
5. Sector Rotation Narrative
6. AI Fact Checking
7. Multi-Timeframe Synthesis
8. TAM Expansion Analysis
9. Corporate Actions Impact
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.ai.ai_enhancements import (
    explain_signal,
    analyze_earnings,
    generate_market_narrative,
    explain_sector_rotation,
    fact_check,
    synthesize_timeframes,
    analyze_tam,
    analyze_corporate_action
)


def test_all_features():
    """Test all 8 AI enhancement features."""
    print("\n" + "="*80)
    print("TESTING AI ENHANCEMENTS (Features 2-9)")
    print("="*80 + "\n")

    results = {}

    # =========================================================================
    # TEST #2: TRADING SIGNAL EXPLANATIONS
    # =========================================================================
    print("2. Testing Trading Signal Explanations...")
    print("-" * 80)

    signal_data = {
        'rs': 95,
        'volume_trend': '2.5x average',
        'theme': 'AI Infrastructure',
        'recent_news': 'NVIDIA announces new AI chip orders from Microsoft and Google'
    }

    explanation = explain_signal('NVDA', 'momentum_breakout', signal_data)

    if explanation:
        print(f"   ✓ Success")
        print(f"   Reasoning: {explanation.reasoning[:100]}...")
        print(f"   Catalyst: {explanation.catalyst}")
        print(f"   Risk: {explanation.key_risk}")
        print(f"   Confidence: {explanation.confidence:.2f}")
        results['signal_explanation'] = 'PASS'
    else:
        print(f"   ✗ Failed")
        results['signal_explanation'] = 'FAIL'

    print()

    # =========================================================================
    # TEST #3: EARNINGS CALL ANALYSIS
    # =========================================================================
    print("3. Testing Earnings Call Analysis...")
    print("-" * 80)

    transcript = """
    Thank you for joining us. This quarter we delivered record results with revenue
    up 265% year-over-year to $22 billion, driven by insatiable demand for our AI
    infrastructure. Data center revenue was $18.4 billion, up 409% year-over-year.
    We're raising our full-year guidance and expect continued strong growth through 2025.
    Supply constraints are easing, and we see demand visibility extending well into next year.
    """

    earnings_data = {'eps': 5.16, 'eps_estimate': 4.60, 'revenue': '22B'}

    earnings_analysis = analyze_earnings('NVDA', transcript, earnings_data)

    if earnings_analysis:
        print(f"   ✓ Success")
        print(f"   Management Tone: {earnings_analysis.management_tone}")
        print(f"   Growth Catalysts: {', '.join(earnings_analysis.growth_catalysts[:2])}")
        print(f"   Assessment: {earnings_analysis.overall_assessment[:100]}...")
        results['earnings_analysis'] = 'PASS'
    else:
        print(f"   ✗ Failed")
        results['earnings_analysis'] = 'FAIL'

    print()

    # =========================================================================
    # TEST #4: MARKET HEALTH NARRATIVE
    # =========================================================================
    print("4. Testing Market Health Narrative...")
    print("-" * 80)

    health_metrics = {
        'breadth': 65,
        'vix': 14.5,
        'new_highs': 150,
        'new_lows': 25,
        'leading_sectors': ['Technology', 'Communication Services', 'Industrials'],
        'lagging_sectors': ['Utilities', 'Real Estate', 'Consumer Staples']
    }

    market_narrative = generate_market_narrative(health_metrics)

    if market_narrative:
        print(f"   ✓ Success")
        print(f"   Health Rating: {market_narrative.health_rating}")
        print(f"   Recommended Stance: {market_narrative.recommended_stance}")
        print(f"   Narrative: {market_narrative.narrative}")
        results['market_narrative'] = 'PASS'
    else:
        print(f"   ✗ Failed")
        results['market_narrative'] = 'FAIL'

    print()

    # =========================================================================
    # TEST #5: SECTOR ROTATION NARRATIVE
    # =========================================================================
    print("5. Testing Sector Rotation Narrative...")
    print("-" * 80)

    rotation_data = {
        'top_sectors': ['Technology', 'Industrials', 'Financials'],
        'lagging_sectors': ['Utilities', 'Consumer Staples', 'Real Estate'],
        'money_flow': 'Into cyclicals and growth'
    }

    sector_narrative = explain_sector_rotation(rotation_data)

    if sector_narrative:
        print(f"   ✓ Success")
        print(f"   Market Cycle Stage: {sector_narrative.market_cycle_stage}")
        print(f"   Reasoning: {sector_narrative.reasoning[:100]}...")
        print(f"   Next Rotation: {sector_narrative.next_rotation_likely}")
        results['sector_rotation'] = 'PASS'
    else:
        print(f"   ✗ Failed")
        results['sector_rotation'] = 'FAIL'

    print()

    # =========================================================================
    # TEST #6: AI FACT CHECKING
    # =========================================================================
    print("6. Testing AI Fact Checking...")
    print("-" * 80)

    claim = "NVIDIA's Q4 revenue grew 265% year-over-year"

    sources = [
        {'source': 'Reuters', 'headline': 'NVIDIA reports Q4 revenue of $22B, up 265% YoY'},
        {'source': 'Bloomberg', 'headline': 'NVIDIA crushes estimates with 265% revenue growth'},
        {'source': 'WSJ', 'headline': 'NVIDIA Q4: Revenue surges on AI demand'}
    ]

    fact_result = fact_check(claim, sources)

    if fact_result:
        print(f"   ✓ Success")
        print(f"   Verified: {fact_result.verified}")
        print(f"   Confidence: {fact_result.confidence:.2f}")
        print(f"   Reasoning: {fact_result.reasoning[:100]}...")
        results['fact_checking'] = 'PASS'
    else:
        print(f"   ✗ Failed")
        results['fact_checking'] = 'FAIL'

    print()

    # =========================================================================
    # TEST #7: MULTI-TIMEFRAME SYNTHESIS
    # =========================================================================
    print("7. Testing Multi-Timeframe Synthesis...")
    print("-" * 80)

    timeframe_data = {
        'daily': {'trend': 'bullish', 'strength': 'strong'},
        'weekly': {'trend': 'bullish', 'strength': 'moderate'},
        'monthly': {'trend': 'bullish', 'strength': 'strong'}
    }

    timeframe_synthesis = synthesize_timeframes('NVDA', timeframe_data)

    if timeframe_synthesis:
        print(f"   ✓ Success")
        print(f"   Overall Alignment: {timeframe_synthesis.overall_alignment}")
        print(f"   Best Entry Timeframe: {timeframe_synthesis.best_entry_timeframe}")
        print(f"   Trade Quality Score: {timeframe_synthesis.trade_quality_score}/10")
        print(f"   Synthesis: {timeframe_synthesis.synthesis[:100]}...")
        results['timeframe_synthesis'] = 'PASS'
    else:
        print(f"   ✗ Failed")
        results['timeframe_synthesis'] = 'FAIL'

    print()

    # =========================================================================
    # TEST #8: TAM EXPANSION ANALYSIS
    # =========================================================================
    print("8. Testing TAM Expansion Analysis...")
    print("-" * 80)

    tam_analysis = analyze_tam(
        theme='AI Infrastructure',
        players=['NVDA', 'AMD', 'AVGO', 'SMCI', 'MRVL'],
        context='Rapid growth in AI chip demand for training and inference'
    )

    if tam_analysis:
        print(f"   ✓ Success")
        print(f"   CAGR Estimate: {tam_analysis.cagr_estimate:.1f}%")
        print(f"   Adoption Stage: {tam_analysis.adoption_stage}")
        print(f"   Growth Drivers: {', '.join(tam_analysis.growth_drivers[:2])}")
        print(f"   Competitive Intensity: {tam_analysis.competitive_intensity}")
        results['tam_analysis'] = 'PASS'
    else:
        print(f"   ✗ Failed")
        results['tam_analysis'] = 'FAIL'

    print()

    # =========================================================================
    # TEST #9: CORPORATE ACTIONS IMPACT
    # =========================================================================
    print("9. Testing Corporate Actions Impact Analysis...")
    print("-" * 80)

    action_impact = analyze_corporate_action(
        ticker='NVDA',
        action_type='stock_split',
        details='10-for-1 stock split effective June 2024'
    )

    if action_impact:
        print(f"   ✓ Success")
        print(f"   Typical Reaction: {action_impact.typical_reaction}")
        print(f"   Reasoning: {action_impact.reasoning[:100]}...")
        print(f"   Expected Impact: {action_impact.expected_impact[:100]}...")
        results['corporate_action'] = 'PASS'
    else:
        print(f"   ✗ Failed")
        results['corporate_action'] = 'FAIL'

    print()

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80 + "\n")

    passed = sum(1 for v in results.values() if v == 'PASS')
    total = len(results)

    for feature, result in results.items():
        icon = '✓' if result == 'PASS' else '✗'
        print(f"  {icon} {feature}: {result}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All AI enhancement features working correctly!")
        print("\nAll 8 features are now available for use:")
        print("  - Trading signal explanations")
        print("  - Earnings call analysis")
        print("  - Market health narratives")
        print("  - Sector rotation explanations")
        print("  - AI fact checking")
        print("  - Multi-timeframe synthesis")
        print("  - TAM expansion analysis")
        print("  - Corporate actions impact analysis")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check logs for details.")
        return False


if __name__ == "__main__":
    success = test_all_features()
    sys.exit(0 if success else 1)
