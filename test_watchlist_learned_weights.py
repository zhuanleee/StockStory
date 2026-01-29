"""
Test Watchlist + Learning System Integration (Option 1)

Demonstrates how watchlist now uses learned weights instead of hardcoded ones.
"""

from src.watchlist.watchlist_manager import get_watchlist_manager, WatchlistPriority
from src.learning import get_learning_brain

def test_learned_weights_integration():
    """Test that watchlist uses learned weights."""

    print("=" * 70)
    print("WATCHLIST + LEARNING SYSTEM INTEGRATION TEST")
    print("=" * 70)
    print()

    # Get managers
    wm = get_watchlist_manager()
    brain = get_learning_brain()

    # Display learned weights
    print("📊 Learned Weights from Trading System:")
    print(f"  Theme:     {brain.current_weights.theme:.1%} (default was 30%)")
    print(f"  Technical: {brain.current_weights.technical:.1%} (default was 25%)")
    print(f"  AI:        {brain.current_weights.ai:.1%} (default was 25%)")
    print(f"  Sentiment: {brain.current_weights.sentiment:.1%} (default was 20%)")
    print()

    # Add test item
    print("➕ Adding test item: NVDA")
    item = wm.add_item(
        ticker="NVDA",
        notes="Test item for learned weights integration",
        priority=WatchlistPriority.HIGH
    )

    # Set some scores
    item.story_score = 8
    item.technical_score = 7
    item.ai_confidence = 0.85
    item.x_sentiment_score = 0.6
    print("  Story Score: 8/10")
    print("  Technical Score: 7/10")
    print("  AI Confidence: 0.85")
    print("  X Sentiment: 0.6")
    print()

    # Calculate with default weights
    default_score = item.calculate_overall_score(learned_weights=None)
    print(f"📉 Score with DEFAULT weights: {default_score}/10")
    print("   (Using hardcoded: 30% theme, 25% tech, 25% AI, 20% sentiment)")
    print()

    # Calculate with learned weights
    learned_score = item.calculate_overall_score(learned_weights=brain.current_weights)
    print(f"📈 Score with LEARNED weights: {learned_score}/10")
    print("   (Using weights learned from real trades)")
    print()

    # Show difference
    diff = learned_score - default_score
    if diff > 0:
        print(f"✅ Learned weights INCREASED score by {diff} points!")
        print("   System has learned these components work better for your style")
    elif diff < 0:
        print(f"⚠️  Learned weights DECREASED score by {abs(diff)} points")
        print("   System has learned these components are less reliable")
    else:
        print("➡️  No difference (not enough data yet)")
    print()

    # Update all items with learned weights
    print("🔄 Updating ALL watchlist items with learned weights...")
    updated_count = wm.update_scores_with_learned_weights()
    print(f"✅ Updated {updated_count} items")
    print()

    # Show final stats
    stats = wm.get_statistics()
    print("📊 Watchlist Statistics:")
    print(f"  Total items: {stats['total_items']}")
    print(f"  Ready to trade: {stats['ready_to_trade']}")
    print(f"  By quality:")
    for quality, count in stats['by_quality'].items():
        if count > 0:
            print(f"    {quality.capitalize()}: {count}")
    print()

    # Clean up test item
    wm.remove_item("NVDA")
    print("🧹 Cleaned up test item")
    print()

    print("=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)
    print()
    print("📝 How to use in production:")
    print()
    print("   # Option 1: Update single item")
    print("   item = wm.get_item('TSLA')")
    print("   item.overall_score = item.calculate_overall_score(")
    print("       learned_weights=brain.current_weights")
    print("   )")
    print()
    print("   # Option 2: Update all items at once")
    print("   wm.update_scores_with_learned_weights()")
    print()
    print("   # Option 3: Via API")
    print("   curl -X POST http://localhost:5000/api/watchlist/update-learned-weights")
    print()


if __name__ == "__main__":
    test_learned_weights_integration()
