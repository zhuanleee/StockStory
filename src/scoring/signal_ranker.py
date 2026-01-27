#!/usr/bin/env python3
"""
Smart Signal Ranking System

Ranks signals based on:
1. Source Trust Score - Historical accuracy of each source
2. Signal Strength - Multiple sources, specificity, catalyst
3. Timing Score - Early vs late detection
4. Consensus Analysis - Smart money vs retail divergence

Tracks accuracy over time and adjusts rankings.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import yfinance as yf

from config import config
from utils import get_logger, normalize_dataframe_columns, safe_float
import param_helper as params  # Learned parameters

logger = get_logger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

# ALL SOURCES START EQUAL - Trust is earned through accuracy
# No preset tiers - the system learns which sources are reliable
def get_initial_trust_score():
    return params.signal_initial_trust()

# Source metadata (for display only, not scoring)
SOURCE_METADATA = {
    # Newsletters
    'SemiAnalysis': {'type': 'newsletter', 'specialty': 'semiconductors'},
    'Stratechery': {'type': 'newsletter', 'specialty': 'tech_strategy'},
    'Doomberg': {'type': 'newsletter', 'specialty': 'energy'},
    'The Diff': {'type': 'newsletter', 'specialty': 'finance'},
    'Platformer': {'type': 'newsletter', 'specialty': 'tech'},
    'Not Boring': {'type': 'newsletter', 'specialty': 'tech'},
    'The Generalist': {'type': 'newsletter', 'specialty': 'tech'},

    # Podcasts
    'All-In Podcast': {'type': 'podcast', 'specialty': 'tech_investing'},
    'Acquired': {'type': 'podcast', 'specialty': 'business'},
    'Invest Like the Best': {'type': 'podcast', 'specialty': 'investing'},
    'Bankless': {'type': 'podcast', 'specialty': 'crypto'},
    'My First Million': {'type': 'podcast', 'specialty': 'business'},
    'The Prof G Pod': {'type': 'podcast', 'specialty': 'business'},
    'Lex Fridman': {'type': 'podcast', 'specialty': 'tech'},
    'Patrick Boyle': {'type': 'podcast', 'specialty': 'finance'},

    # News
    'Finviz': {'type': 'news', 'specialty': 'general'},
    'Google News': {'type': 'news', 'specialty': 'general'},
    'Yahoo Finance': {'type': 'news', 'specialty': 'general'},
    'MarketWatch': {'type': 'news', 'specialty': 'general'},
    'Bloomberg': {'type': 'news', 'specialty': 'general'},
    'CNBC': {'type': 'news', 'specialty': 'general'},
    'Reuters': {'type': 'news', 'specialty': 'general'},

    # Social
    'StockTwits': {'type': 'social', 'specialty': 'retail'},
    'Reddit': {'type': 'social', 'specialty': 'retail'},
    'Twitter': {'type': 'social', 'specialty': 'mixed'},
    'r/wallstreetbets': {'type': 'social', 'specialty': 'retail'},
    'r/stocks': {'type': 'social', 'specialty': 'retail'},
    'r/investing': {'type': 'social', 'specialty': 'retail'},
}

# File to store accuracy tracking
ACCURACY_FILE = Path('source_accuracy.json')
SIGNAL_HISTORY_FILE = Path('signal_history.json')


# ============================================================
# SOURCE TRUST SCORING
# ============================================================

def load_accuracy_data():
    """Load historical accuracy data."""
    if ACCURACY_FILE.exists():
        with open(ACCURACY_FILE, 'r') as f:
            return json.load(f)
    return {
        'source_accuracy': {},  # source -> {correct: X, total: Y}
        'theme_accuracy': {},   # theme -> {source -> accuracy}
        'last_updated': None,
    }


def save_accuracy_data(data):
    """Save accuracy data."""
    data['last_updated'] = datetime.now().isoformat()
    with open(ACCURACY_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_source_trust_score(source_name):
    """
    Get trust score for a source.
    ALL sources start at 50 - trust is earned through accuracy.
    """
    # Try to get from fact_checker's trust system first
    try:
        from fact_checker import get_source_trust
        return get_source_trust(source_name)
    except ImportError:
        pass

    # Fallback: Use local accuracy data
    accuracy_data = load_accuracy_data()
    source_accuracy = accuracy_data.get('source_accuracy', {}).get(source_name, {})

    if source_accuracy.get('total', 0) >= 3:
        accuracy_rate = source_accuracy['correct'] / source_accuracy['total']
        # Score = 50 + (accuracy - 0.5) * 100
        return min(100, max(0, 50 + (accuracy_rate - 0.5) * 100))

    return get_initial_trust_score()  # New sources start at learned threshold


def get_source_metadata(source_name):
    """Get metadata (type, specialty) for a source."""
    return SOURCE_METADATA.get(source_name, {
        'type': 'unknown',
        'specialty': 'general'
    })


# ============================================================
# SIGNAL STRENGTH SCORING
# ============================================================

def calculate_signal_strength(signal_data):
    """
    Calculate signal strength based on multiple factors.

    signal_data = {
        'theme': str,
        'sources': [list of source names],
        'tickers_mentioned': [list of tickers],
        'catalyst': str or None,
        'mention_count': int,
        'smart_money_sentiment': str,  # BULLISH/BEARISH/NEUTRAL
        'retail_sentiment': str,       # BULLISH/BEARISH/NEUTRAL
    }
    """
    score = 0
    factors = []

    # Factor 1: Multiple sources agree (learned points)
    num_sources = len(signal_data.get('sources', []))
    if num_sources >= 4:
        score += params.signal_consensus_4plus()
        factors.append('Strong consensus (4+ sources)')
    elif num_sources >= 2:
        score += params.signal_consensus_2plus()
        factors.append(f'{num_sources} sources agree')
    elif num_sources == 1:
        score += params.signal_consensus_1()
        factors.append('Single source')

    # Factor 2: High-tier sources (learned points)
    tier1_sources = [s for s in signal_data.get('sources', [])
                     if get_source_tier(s).get('tier', 5) == 1]
    tier2_sources = [s for s in signal_data.get('sources', [])
                     if get_source_tier(s).get('tier', 5) == 2]

    if tier1_sources:
        score += params.signal_tier1_bonus()
        factors.append(f'Expert source: {tier1_sources[0]}')
    elif tier2_sources:
        score += params.signal_tier2_bonus()
        factors.append(f'Quality source: {tier2_sources[0]}')

    # Factor 3: Specific tickers mentioned (learned points)
    num_tickers = len(signal_data.get('tickers_mentioned', []))
    if num_tickers >= 3:
        score += params.signal_multi_ticker_3plus()
        factors.append(f'{num_tickers} tickers identified')
    elif num_tickers >= 1:
        score += params.signal_multi_ticker_1plus()
        factors.append('Specific ticker mentioned')

    # Factor 4: Clear catalyst (learned points)
    if signal_data.get('catalyst'):
        catalyst = signal_data['catalyst']
        if len(catalyst) > 20:  # Substantive catalyst
            score += params.signal_catalyst_substantive()
            factors.append('Clear catalyst')
        else:
            score += params.signal_catalyst_mentioned()
            factors.append('Catalyst mentioned')

    # Factor 5: Smart money vs Retail divergence (+0-25)
    smart = signal_data.get('smart_money_sentiment', 'NEUTRAL')
    retail = signal_data.get('retail_sentiment', 'NEUTRAL')

    if smart != retail and smart != 'NEUTRAL' and retail != 'NEUTRAL':
        score += 25
        factors.append(f'DIVERGENCE: Smart={smart}, Retail={retail}')
    elif smart == retail and smart != 'NEUTRAL':
        score += 10
        factors.append(f'Consensus: {smart}')

    return {
        'score': min(100, score),
        'factors': factors,
    }


# ============================================================
# TIMING SCORE
# ============================================================

def calculate_timing_score(theme_name, tickers):
    """
    Calculate timing score - is this early, confirming, or late?

    Checks if mentioned stocks have already moved significantly.
    """
    if not tickers:
        return {'score': 50, 'timing': 'UNKNOWN', 'moves': {}}

    moves = {}
    try:
        for ticker in tickers[:5]:  # Check up to 5 tickers
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='1mo')

                if len(hist) < 5:
                    continue

                # Calculate recent move (last 5 days vs previous)
                recent_price = hist['Close'].iloc[-1]
                week_ago_price = hist['Close'].iloc[-5] if len(hist) >= 5 else hist['Close'].iloc[0]
                month_ago_price = hist['Close'].iloc[0]

                week_move = (recent_price / week_ago_price - 1) * 100
                month_move = (recent_price / month_ago_price - 1) * 100

                moves[ticker] = {
                    'week': round(week_move, 1),
                    'month': round(month_move, 1),
                }
            except Exception as e:
                logger.debug(f"Failed to get timing data for {ticker}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error calculating timing score: {e}")
        pass

    if not moves:
        return {'score': 50, 'timing': 'UNKNOWN', 'moves': {}}

    # Calculate average moves
    avg_week = sum(m['week'] for m in moves.values()) / len(moves)
    avg_month = sum(m['month'] for m in moves.values()) / len(moves)

    # Determine timing
    if abs(avg_week) < 3 and abs(avg_month) < 10:
        # Stocks haven't moved much - EARLY signal
        return {
            'score': 90,
            'timing': 'EARLY',
            'moves': moves,
            'detail': 'Pre-move detection'
        }
    elif abs(avg_week) < 5 and 10 <= abs(avg_month) < 25:
        # Some movement - CONFIRMING signal
        return {
            'score': 60,
            'timing': 'CONFIRMING',
            'moves': moves,
            'detail': 'Trend confirmation'
        }
    else:
        # Big moves already happened - LATE signal
        return {
            'score': 30,
            'timing': 'LATE',
            'moves': moves,
            'detail': 'Post-move (may be priced in)'
        }


# ============================================================
# OVERALL RANKING
# ============================================================

def calculate_overall_score(signal_data):
    """
    Calculate overall signal score using weighted formula.

    Formula:
    Score = (Source Trust × 0.25) +
            (Signal Strength × 0.30) +
            (Timing × 0.25) +
            (Novelty × 0.20)
    """
    # Get source trust (average of all sources)
    sources = signal_data.get('sources', [])
    if sources:
        source_scores = [get_source_trust_score(s) for s in sources]
        source_trust = sum(source_scores) / len(source_scores)
    else:
        source_trust = DEFAULT_SOURCE_SCORE

    # Get signal strength
    strength = calculate_signal_strength(signal_data)
    signal_strength = strength['score']

    # Get timing score
    tickers = signal_data.get('tickers_mentioned', [])
    timing = calculate_timing_score(signal_data.get('theme', ''), tickers)
    timing_score = timing['score']

    # Novelty score (based on how new the theme is)
    # Higher if theme hasn't been widely discussed
    mention_count = signal_data.get('mention_count', 1)
    if mention_count <= 3:
        novelty = 90  # Very new
    elif mention_count <= 10:
        novelty = 70  # Emerging
    elif mention_count <= 25:
        novelty = 50  # Known
    else:
        novelty = 30  # Mainstream

    # Weighted calculation
    overall = (
        source_trust * 0.25 +
        signal_strength * 0.30 +
        timing_score * 0.25 +
        novelty * 0.20
    )

    return {
        'overall_score': round(overall),
        'source_trust': round(source_trust),
        'signal_strength': round(signal_strength),
        'timing_score': round(timing_score),
        'novelty_score': round(novelty),
        'timing_detail': timing.get('timing', 'UNKNOWN'),
        'strength_factors': strength.get('factors', []),
        'price_moves': timing.get('moves', {}),
    }


def rank_signals(signals_list):
    """
    Rank a list of signals by overall score.

    signals_list = [
        {
            'theme': str,
            'sources': [str],
            'tickers_mentioned': [str],
            'catalyst': str,
            'mention_count': int,
            ...
        }
    ]
    """
    ranked = []

    for signal in signals_list:
        score_data = calculate_overall_score(signal)
        ranked.append({
            **signal,
            **score_data,
        })

    # Sort by overall score descending
    ranked.sort(key=lambda x: -x['overall_score'])

    return ranked


# ============================================================
# ACCURACY TRACKING
# ============================================================

def record_signal(theme, sources, tickers, catalyst=None):
    """
    Record a signal for later accuracy checking.
    """
    history = load_signal_history()

    signal_id = f"{theme}_{datetime.now().strftime('%Y%m%d')}"

    # Get current prices
    prices = {}
    for ticker in tickers[:5]:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1d')
            if len(hist) > 0:
                prices[ticker] = float(hist['Close'].iloc[-1])
        except Exception as e:
            logger.debug(f"Failed to get price for {ticker}: {e}")
            pass

    history['signals'][signal_id] = {
        'theme': theme,
        'sources': sources,
        'tickers': tickers,
        'catalyst': catalyst,
        'recorded_date': datetime.now().isoformat(),
        'initial_prices': prices,
        'checked_1w': False,
        'checked_1m': False,
    }

    save_signal_history(history)
    return signal_id


def check_signal_accuracy():
    """
    Check accuracy of past signals and update source scores.
    """
    history = load_signal_history()
    accuracy_data = load_accuracy_data()

    now = datetime.now()

    for signal_id, signal in history.get('signals', {}).items():
        recorded = datetime.fromisoformat(signal['recorded_date'])
        days_old = (now - recorded).days

        # Check 1-week performance
        if days_old >= 7 and not signal.get('checked_1w'):
            result = evaluate_signal_performance(signal, '1w')
            if result:
                update_source_accuracy(signal['sources'], result['success'], accuracy_data)
                signal['checked_1w'] = True
                signal['result_1w'] = result

        # Check 1-month performance
        if days_old >= 30 and not signal.get('checked_1m'):
            result = evaluate_signal_performance(signal, '1m')
            if result:
                update_source_accuracy(signal['sources'], result['success'], accuracy_data)
                signal['checked_1m'] = True
                signal['result_1m'] = result

    save_signal_history(history)
    save_accuracy_data(accuracy_data)


def evaluate_signal_performance(signal, period='1w'):
    """
    Evaluate if a signal was successful.
    Success = mentioned stocks outperformed SPY by 2%+
    """
    tickers = signal.get('tickers', [])
    initial_prices = signal.get('initial_prices', {})

    if not tickers or not initial_prices:
        return None

    try:
        # Get current prices
        returns = []
        for ticker, initial in initial_prices.items():
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='1d')
                if len(hist) > 0:
                    current = float(hist['Close'].iloc[-1])
                    ret = (current / initial - 1) * 100
                    returns.append(ret)
            except Exception as e:
                logger.debug(f"Failed to get return for {ticker}: {e}")
                pass

        if not returns:
            return None

        avg_return = sum(returns) / len(returns)

        # Get SPY return for comparison
        try:
            spy = yf.Ticker('SPY')
            spy_hist = spy.history(period=period)
            if len(spy_hist) >= 2:
                spy_return = (spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[0] - 1) * 100
            else:
                spy_return = 0
        except Exception as e:
            logger.debug(f"Failed to get SPY return: {e}")
            spy_return = 0

        outperformance = avg_return - spy_return
        success = outperformance >= 2  # Beat SPY by 2%+

        return {
            'success': success,
            'avg_return': round(avg_return, 1),
            'spy_return': round(spy_return, 1),
            'outperformance': round(outperformance, 1),
        }
    except Exception as e:
        logger.error(f"Error evaluating signal performance: {e}")
        return None


def update_source_accuracy(sources, success, accuracy_data):
    """Update accuracy tracking for sources."""
    for source in sources:
        if source not in accuracy_data['source_accuracy']:
            accuracy_data['source_accuracy'][source] = {'correct': 0, 'total': 0}

        accuracy_data['source_accuracy'][source]['total'] += 1
        if success:
            accuracy_data['source_accuracy'][source]['correct'] += 1


def load_signal_history():
    """Load signal history."""
    if SIGNAL_HISTORY_FILE.exists():
        with open(SIGNAL_HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {'signals': {}}


def save_signal_history(history):
    """Save signal history."""
    with open(SIGNAL_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


# ============================================================
# FORMATTING
# ============================================================

def format_ranked_signals(ranked_signals):
    """Format ranked signals for Telegram."""
    if not ranked_signals:
        return "No signals to rank."

    msg = "🏆 *TOP RANKED SIGNALS*\n\n"

    for i, signal in enumerate(ranked_signals[:5], 1):
        score = signal.get('overall_score', 0)
        theme = signal.get('theme', signal.get('name', 'Unknown'))

        # Score emoji
        if score >= 80:
            score_emoji = "🔥🔥🔥"
        elif score >= 65:
            score_emoji = "🔥🔥"
        elif score >= 50:
            score_emoji = "🔥"
        else:
            score_emoji = "💡"

        msg += f"*{i}. {theme}* [{score}] {score_emoji}\n"

        # Score breakdown
        msg += f"   📊 Source: {signal.get('source_trust', 0)} | "
        msg += f"Strength: {signal.get('signal_strength', 0)} | "
        msg += f"Timing: {signal.get('timing_score', 0)}\n"

        # Timing detail
        timing = signal.get('timing_detail', 'UNKNOWN')
        timing_emoji = {'EARLY': '🟢', 'CONFIRMING': '🟡', 'LATE': '🔴'}.get(timing, '⚪')
        msg += f"   ⏰ {timing_emoji} {timing}"

        # Price moves if available
        moves = signal.get('price_moves', {})
        if moves:
            move_str = ', '.join([f"{t}: {m['week']:+.1f}%w" for t, m in list(moves.items())[:2]])
            msg += f" ({move_str})"
        msg += "\n"

        # Top sources
        sources = signal.get('sources', [])
        if sources:
            top_sources = sources[:3]
            source_str = ', '.join(top_sources)
            msg += f"   📡 {source_str}\n"

        # Tickers
        tickers = signal.get('tickers_mentioned', signal.get('primary_plays', []))
        if tickers:
            msg += f"   🎯 `{'`, `'.join(tickers[:4])}`\n"

        # Strength factors
        factors = signal.get('strength_factors', [])
        if factors:
            msg += f"   ✓ {factors[0]}\n"

        msg += "\n"

    msg += "_Scores: Source quality + Signal strength + Timing + Novelty_"

    return msg


def get_source_leaderboard():
    """Get leaderboard of sources by accuracy."""
    accuracy_data = load_accuracy_data()
    source_accuracy = accuracy_data.get('source_accuracy', {})

    leaderboard = []
    for source, data in source_accuracy.items():
        if data['total'] >= 3:  # At least 3 signals
            accuracy = data['correct'] / data['total'] * 100
            leaderboard.append({
                'source': source,
                'accuracy': round(accuracy, 1),
                'total': data['total'],
                'correct': data['correct'],
                'tier': get_source_tier(source).get('tier', 4),
            })

    leaderboard.sort(key=lambda x: -x['accuracy'])
    return leaderboard


def format_source_leaderboard(leaderboard):
    """Format source leaderboard for Telegram."""
    if not leaderboard:
        return "📊 *SOURCE LEADERBOARD*\n\n_Not enough data yet. Signals need 1+ weeks to evaluate._"

    msg = "📊 *SOURCE ACCURACY LEADERBOARD*\n\n"

    for i, source in enumerate(leaderboard[:10], 1):
        tier = source['tier']
        tier_emoji = {1: '👑', 2: '⭐', 3: '📰', 4: '💬'}.get(tier, '❓')

        msg += f"{i}. {tier_emoji} *{source['source']}*\n"
        msg += f"   Accuracy: {source['accuracy']}% ({source['correct']}/{source['total']})\n"

    msg += "\n_Accuracy = stocks outperformed SPY by 2%+ within 1 week_"

    return msg


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    # Test with sample signal
    test_signal = {
        'theme': 'NUCLEAR REVIVAL',
        'sources': ['SemiAnalysis', 'Doomberg', 'All-In Podcast'],
        'tickers_mentioned': ['VST', 'CEG', 'SMR'],
        'catalyst': 'Microsoft signs nuclear deal for AI data centers',
        'mention_count': 5,
        'smart_money_sentiment': 'BULLISH',
        'retail_sentiment': 'NEUTRAL',
    }

    result = calculate_overall_score(test_signal)
    logger.info(f"Signal: {test_signal['theme']}")
    logger.info(f"Overall Score: {result['overall_score']}")
    logger.info(f"Source Trust: {result['source_trust']}")
    logger.info(f"Signal Strength: {result['signal_strength']}")
    logger.info(f"Timing: {result['timing_detail']} ({result['timing_score']})")
    logger.info(f"Factors: {result['strength_factors']}")
