#!/usr/bin/env python3
"""
Comprehensive Self-Learning System

Learns from:
1. Alert Accuracy - Which signals actually work
2. Entry Timing - Optimal entry points per stock/pattern
3. Theme Lifecycle - How long themes last, peak timing
4. Stock Personalities - Individual stock behaviors
5. Sector Rotation - Which rotation signals work
6. Market Regime - What works in different conditions
7. News Impact - How quickly news gets priced in
"""

import json
from datetime import datetime
from pathlib import Path

from utils import get_logger

logger = get_logger(__name__)

# Data storage
LEARNING_DATA_DIR = Path('learning_data')
LEARNING_DATA_DIR.mkdir(exist_ok=True)

# =============================================================================
# 1. ALERT ACCURACY TRACKING
# =============================================================================

def load_alert_history():
    """Load alert tracking data."""
    path = LEARNING_DATA_DIR / 'alert_accuracy.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'alerts': [],  # Individual alerts with outcomes
        'accuracy_by_type': {},  # squeeze_breakout, rs_leader, volume_spike, etc.
        'accuracy_by_ticker': {},
        'accuracy_by_sector': {},
        'accuracy_by_market_condition': {},  # bull, bear, choppy
    }

def save_alert_history(data):
    """Save alert tracking data."""
    path = LEARNING_DATA_DIR / 'alert_accuracy.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def record_alert(ticker, alert_type, price_at_alert, context=None):
    """Record a new alert for tracking."""
    data = load_alert_history()

    alert = {
        'id': f"{ticker}_{alert_type}_{datetime.now().strftime('%Y%m%d_%H%M')}",
        'ticker': ticker,
        'alert_type': alert_type,  # squeeze_breakout, rs_leader, volume_spike, etc.
        'price_at_alert': price_at_alert,
        'timestamp': datetime.now().isoformat(),
        'context': context or {},  # sector, market_condition, etc.
        'outcome': None,  # To be filled later
        'price_after_1d': None,
        'price_after_5d': None,
        'price_after_10d': None,
    }

    data['alerts'].append(alert)
    save_alert_history(data)
    return alert['id']

def update_alert_outcome(alert_id, price_after, days_after):
    """Update an alert with its outcome."""
    data = load_alert_history()

    for alert in data['alerts']:
        if alert['id'] == alert_id:
            field = f'price_after_{days_after}d'
            if field in ['price_after_1d', 'price_after_5d', 'price_after_10d']:
                alert[field] = price_after

            # Calculate outcome if we have 5-day data
            if alert['price_after_5d'] and alert['price_at_alert']:
                pct_change = (alert['price_after_5d'] - alert['price_at_alert']) / alert['price_at_alert'] * 100
                alert['outcome'] = 'win' if pct_change > 2 else ('loss' if pct_change < -2 else 'neutral')
                alert['pct_change_5d'] = pct_change

                # Update accuracy stats
                _update_alert_accuracy_stats(data, alert)
            break

    save_alert_history(data)

def _update_alert_accuracy_stats(data, alert):
    """Update accuracy statistics from an alert outcome."""
    alert_type = alert['alert_type']
    ticker = alert['ticker']
    outcome = alert['outcome']

    # By alert type
    if alert_type not in data['accuracy_by_type']:
        data['accuracy_by_type'][alert_type] = {'wins': 0, 'losses': 0, 'neutral': 0, 'avg_gain': []}

    stats = data['accuracy_by_type'][alert_type]
    if outcome == 'win':
        stats['wins'] += 1
    elif outcome == 'loss':
        stats['losses'] += 1
    else:
        stats['neutral'] += 1
    stats['avg_gain'].append(alert.get('pct_change_5d', 0))

    # By ticker
    if ticker not in data['accuracy_by_ticker']:
        data['accuracy_by_ticker'][ticker] = {'wins': 0, 'losses': 0, 'neutral': 0, 'best_alert_type': {}}

    ticker_stats = data['accuracy_by_ticker'][ticker]
    if outcome == 'win':
        ticker_stats['wins'] += 1
    elif outcome == 'loss':
        ticker_stats['losses'] += 1
    else:
        ticker_stats['neutral'] += 1

    # Track best alert type per ticker
    if alert_type not in ticker_stats['best_alert_type']:
        ticker_stats['best_alert_type'][alert_type] = {'wins': 0, 'total': 0}
    ticker_stats['best_alert_type'][alert_type]['total'] += 1
    if outcome == 'win':
        ticker_stats['best_alert_type'][alert_type]['wins'] += 1

    # By sector
    sector = alert.get('context', {}).get('sector', 'unknown')
    if sector not in data['accuracy_by_sector']:
        data['accuracy_by_sector'][sector] = {'wins': 0, 'losses': 0, 'neutral': 0}

    sector_stats = data['accuracy_by_sector'][sector]
    if outcome == 'win':
        sector_stats['wins'] += 1
    elif outcome == 'loss':
        sector_stats['losses'] += 1
    else:
        sector_stats['neutral'] += 1

def get_alert_accuracy_insights():
    """Get insights about alert accuracy."""
    data = load_alert_history()
    insights = {
        'best_alert_types': [],
        'worst_alert_types': [],
        'best_tickers_for_alerts': [],
        'recommendations': []
    }

    # Rank alert types by win rate
    for alert_type, stats in data.get('accuracy_by_type', {}).items():
        total = stats['wins'] + stats['losses'] + stats['neutral']
        if total >= 5:  # Minimum sample size
            win_rate = stats['wins'] / total * 100
            avg_gain = sum(stats['avg_gain']) / len(stats['avg_gain']) if stats['avg_gain'] else 0
            insights['best_alert_types'].append({
                'type': alert_type,
                'win_rate': win_rate,
                'avg_gain': avg_gain,
                'total_alerts': total
            })

    insights['best_alert_types'].sort(key=lambda x: x['win_rate'], reverse=True)
    insights['worst_alert_types'] = insights['best_alert_types'][-3:] if len(insights['best_alert_types']) > 3 else []
    insights['best_alert_types'] = insights['best_alert_types'][:3]

    # Generate recommendations
    if insights['best_alert_types']:
        best = insights['best_alert_types'][0]
        insights['recommendations'].append(
            f"Focus on {best['type']} alerts ({best['win_rate']:.0f}% win rate)"
        )

    if insights['worst_alert_types']:
        worst = insights['worst_alert_types'][-1]
        if worst['win_rate'] < 40:
            insights['recommendations'].append(
                f"Consider ignoring {worst['type']} alerts ({worst['win_rate']:.0f}% win rate)"
            )

    return insights


# =============================================================================
# 2. ENTRY TIMING OPTIMIZATION
# =============================================================================

def load_entry_timing_data():
    """Load entry timing learning data."""
    path = LEARNING_DATA_DIR / 'entry_timing.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'entries': [],
        'timing_by_strategy': {},  # breakout, pullback_20sma, pullback_50sma, vwap_bounce
        'timing_by_ticker': {},
        'timing_by_pattern': {},  # squeeze, flag, cup_handle
    }

def save_entry_timing_data(data):
    """Save entry timing data."""
    path = LEARNING_DATA_DIR / 'entry_timing.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def record_entry(ticker, entry_strategy, entry_price, pattern=None):
    """Record an entry for timing analysis."""
    data = load_entry_timing_data()

    entry = {
        'id': f"{ticker}_{entry_strategy}_{datetime.now().strftime('%Y%m%d_%H%M')}",
        'ticker': ticker,
        'entry_strategy': entry_strategy,
        'pattern': pattern,
        'entry_price': entry_price,
        'timestamp': datetime.now().isoformat(),
        'max_gain_5d': None,
        'max_drawdown_5d': None,
        'exit_price': None,
        'outcome': None,
    }

    data['entries'].append(entry)
    save_entry_timing_data(data)
    return entry['id']

def update_entry_outcome(entry_id, max_gain, max_drawdown, exit_price):
    """Update an entry with its outcome."""
    data = load_entry_timing_data()

    for entry in data['entries']:
        if entry['id'] == entry_id:
            entry['max_gain_5d'] = max_gain
            entry['max_drawdown_5d'] = max_drawdown
            entry['exit_price'] = exit_price

            # Calculate risk/reward
            if entry['entry_price'] and exit_price:
                pct_gain = (exit_price - entry['entry_price']) / entry['entry_price'] * 100
                entry['pct_gain'] = pct_gain
                entry['outcome'] = 'win' if pct_gain > 2 else ('loss' if pct_gain < -2 else 'neutral')

                # Update strategy stats
                _update_entry_timing_stats(data, entry)
            break

    save_entry_timing_data(data)

def _update_entry_timing_stats(data, entry):
    """Update entry timing statistics."""
    strategy = entry['entry_strategy']
    ticker = entry['ticker']

    # By strategy
    if strategy not in data['timing_by_strategy']:
        data['timing_by_strategy'][strategy] = {
            'wins': 0, 'losses': 0, 'neutral': 0,
            'avg_gain': [], 'avg_drawdown': [], 'risk_reward': []
        }

    stats = data['timing_by_strategy'][strategy]
    outcome = entry['outcome']
    if outcome == 'win':
        stats['wins'] += 1
    elif outcome == 'loss':
        stats['losses'] += 1
    else:
        stats['neutral'] += 1

    if entry.get('pct_gain') is not None:
        stats['avg_gain'].append(entry['pct_gain'])
    if entry.get('max_drawdown_5d') is not None:
        stats['avg_drawdown'].append(entry['max_drawdown_5d'])
    if entry.get('max_gain_5d') and entry.get('max_drawdown_5d') and entry['max_drawdown_5d'] != 0:
        stats['risk_reward'].append(abs(entry['max_gain_5d'] / entry['max_drawdown_5d']))

    # By ticker
    if ticker not in data['timing_by_ticker']:
        data['timing_by_ticker'][ticker] = {'strategies': {}}

    if strategy not in data['timing_by_ticker'][ticker]['strategies']:
        data['timing_by_ticker'][ticker]['strategies'][strategy] = {
            'wins': 0, 'losses': 0, 'avg_gain': []
        }

    ticker_strat = data['timing_by_ticker'][ticker]['strategies'][strategy]
    if outcome == 'win':
        ticker_strat['wins'] += 1
    elif outcome == 'loss':
        ticker_strat['losses'] += 1
    if entry.get('pct_gain') is not None:
        ticker_strat['avg_gain'].append(entry['pct_gain'])

def get_best_entry_strategy(ticker=None):
    """Get the best entry strategy overall or for a specific ticker."""
    data = load_entry_timing_data()

    if ticker and ticker in data.get('timing_by_ticker', {}):
        # Return best strategy for this specific ticker
        strategies = data['timing_by_ticker'][ticker].get('strategies', {})
        best = None
        best_rate = 0

        for strat, stats in strategies.items():
            total = stats['wins'] + stats['losses']
            if total >= 3:
                win_rate = stats['wins'] / total
                if win_rate > best_rate:
                    best_rate = win_rate
                    avg = sum(stats['avg_gain']) / len(stats['avg_gain']) if stats['avg_gain'] else 0
                    best = {'strategy': strat, 'win_rate': win_rate * 100, 'avg_gain': avg}

        return best

    # Return overall best strategies
    results = []
    for strategy, stats in data.get('timing_by_strategy', {}).items():
        total = stats['wins'] + stats['losses'] + stats['neutral']
        if total >= 5:
            win_rate = stats['wins'] / total * 100
            avg_gain = sum(stats['avg_gain']) / len(stats['avg_gain']) if stats['avg_gain'] else 0
            avg_dd = sum(stats['avg_drawdown']) / len(stats['avg_drawdown']) if stats['avg_drawdown'] else 0
            avg_rr = sum(stats['risk_reward']) / len(stats['risk_reward']) if stats['risk_reward'] else 0

            results.append({
                'strategy': strategy,
                'win_rate': win_rate,
                'avg_gain': avg_gain,
                'avg_drawdown': avg_dd,
                'risk_reward': avg_rr,
                'total': total
            })

    results.sort(key=lambda x: x['win_rate'], reverse=True)
    return results


# =============================================================================
# 3. THEME LIFECYCLE LEARNING
# =============================================================================

def load_theme_lifecycle_data():
    """Load theme lifecycle data."""
    path = LEARNING_DATA_DIR / 'theme_lifecycle.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'themes': {},  # theme_name -> lifecycle data
        'avg_lifecycle_days': 45,  # Default assumption
        'peak_timing_patterns': {},
    }

def save_theme_lifecycle_data(data):
    """Save theme lifecycle data."""
    path = LEARNING_DATA_DIR / 'theme_lifecycle.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def track_theme_lifecycle(theme_name, status, top_stocks=None, momentum_score=None):
    """Track a theme's lifecycle stage."""
    data = load_theme_lifecycle_data()

    if theme_name not in data['themes']:
        data['themes'][theme_name] = {
            'first_detected': datetime.now().isoformat(),
            'timeline': [],
            'peak_date': None,
            'peak_momentum': 0,
            'fade_date': None,
            'total_days_active': 0,
            'stocks_at_peak': [],
        }

    theme = data['themes'][theme_name]

    # Record this data point
    theme['timeline'].append({
        'date': datetime.now().isoformat(),
        'status': status,  # emerging, rising, peak, fading, dead
        'momentum': momentum_score,
        'top_stocks': top_stocks or []
    })

    # Track peak
    if momentum_score and momentum_score > theme['peak_momentum']:
        theme['peak_momentum'] = momentum_score
        theme['peak_date'] = datetime.now().isoformat()
        theme['stocks_at_peak'] = top_stocks or []

    # Track fade
    if status == 'fading' and not theme['fade_date']:
        theme['fade_date'] = datetime.now().isoformat()

    # Calculate active days
    first = datetime.fromisoformat(theme['first_detected'])
    theme['total_days_active'] = (datetime.now() - first).days

    save_theme_lifecycle_data(data)

def get_theme_lifecycle_insights():
    """Get insights about theme lifecycles."""
    data = load_theme_lifecycle_data()
    insights = {
        'completed_themes': [],
        'avg_days_to_peak': None,
        'avg_total_lifecycle': None,
        'current_stage_predictions': {},
    }

    days_to_peak = []
    total_lifecycles = []

    for theme_name, theme in data.get('themes', {}).items():
        if theme.get('fade_date'):
            # This theme has completed its cycle
            first = datetime.fromisoformat(theme['first_detected'])

            if theme.get('peak_date'):
                peak = datetime.fromisoformat(theme['peak_date'])
                days_to_peak.append((peak - first).days)

            fade = datetime.fromisoformat(theme['fade_date'])
            total_lifecycles.append((fade - first).days)

            insights['completed_themes'].append({
                'name': theme_name,
                'days_active': theme['total_days_active'],
                'peak_momentum': theme['peak_momentum']
            })
        else:
            # Active theme - predict when it might peak/fade
            if theme.get('timeline') and len(theme['timeline']) >= 3:
                recent_momentum = [t.get('momentum', 0) for t in theme['timeline'][-5:] if t.get('momentum')]
                if recent_momentum:
                    trend = recent_momentum[-1] - recent_momentum[0] if len(recent_momentum) > 1 else 0

                    days_active = theme['total_days_active']
                    avg_lifecycle = data.get('avg_lifecycle_days', 45)

                    if trend > 0:
                        stage = 'rising'
                        days_left = max(0, avg_lifecycle - days_active)
                    elif trend < 0:
                        stage = 'fading'
                        days_left = max(0, (avg_lifecycle - days_active) // 2)
                    else:
                        stage = 'stable'
                        days_left = max(0, avg_lifecycle - days_active)

                    insights['current_stage_predictions'][theme_name] = {
                        'stage': stage,
                        'days_active': days_active,
                        'estimated_days_remaining': days_left,
                        'momentum_trend': 'up' if trend > 0 else ('down' if trend < 0 else 'flat')
                    }

    if days_to_peak:
        insights['avg_days_to_peak'] = sum(days_to_peak) / len(days_to_peak)
        data['avg_days_to_peak'] = insights['avg_days_to_peak']

    if total_lifecycles:
        insights['avg_total_lifecycle'] = sum(total_lifecycles) / len(total_lifecycles)
        data['avg_lifecycle_days'] = insights['avg_total_lifecycle']
        save_theme_lifecycle_data(data)

    return insights


# =============================================================================
# 4. STOCK PERSONALITY PROFILES
# =============================================================================

def load_stock_profiles():
    """Load stock personality profiles."""
    path = LEARNING_DATA_DIR / 'stock_profiles.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {'profiles': {}}

def save_stock_profiles(data):
    """Save stock profiles."""
    path = LEARNING_DATA_DIR / 'stock_profiles.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def analyze_stock_personality(ticker, price_data):
    """
    Analyze a stock's personality based on price behavior.

    Returns personality traits:
    - momentum vs mean_reversion
    - volume_responsive
    - gap_behavior (fills vs extends)
    - volatility_regime
    - best_indicators
    """
    data = load_stock_profiles()

    if ticker not in data['profiles']:
        data['profiles'][ticker] = {
            'observations': [],
            'personality': {},
            'last_updated': None
        }

    profile = data['profiles'][ticker]

    # Analyze behavior patterns
    observations = {
        'timestamp': datetime.now().isoformat(),
        'momentum_score': 0,
        'mean_reversion_score': 0,
        'volume_correlation': 0,
        'gap_fill_rate': 0,
        'trend_persistence': 0,
    }

    if len(price_data) >= 50:
        closes = price_data['Close'].values if hasattr(price_data['Close'], 'values') else price_data['Close']

        # Momentum vs Mean Reversion
        # Check if extended moves continue or reverse
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]

        continuation_count = 0
        reversal_count = 0
        for i in range(1, len(returns)):
            if returns[i] * returns[i-1] > 0:  # Same direction
                continuation_count += 1
            else:
                reversal_count += 1

        total = continuation_count + reversal_count
        if total > 0:
            observations['momentum_score'] = continuation_count / total * 100
            observations['mean_reversion_score'] = reversal_count / total * 100

        # Trend persistence (how long trends last)
        trend_lengths = []
        current_trend = 1
        for i in range(1, len(returns)):
            if returns[i] * returns[i-1] > 0:
                current_trend += 1
            else:
                trend_lengths.append(current_trend)
                current_trend = 1
        if trend_lengths:
            observations['trend_persistence'] = sum(trend_lengths) / len(trend_lengths)

        # Volume responsiveness
        if 'Volume' in price_data.columns:
            volumes = price_data['Volume'].values if hasattr(price_data['Volume'], 'values') else price_data['Volume']
            abs_returns = [abs(r) for r in returns]

            # Simple correlation between volume spikes and price moves
            avg_vol = sum(volumes[:-1]) / len(volumes[:-1])
            high_vol_moves = []
            low_vol_moves = []

            for i in range(len(volumes) - 1):
                if volumes[i] > avg_vol * 1.5:
                    high_vol_moves.append(abs_returns[i] if i < len(abs_returns) else 0)
                else:
                    low_vol_moves.append(abs_returns[i] if i < len(abs_returns) else 0)

            if high_vol_moves and low_vol_moves:
                high_avg = sum(high_vol_moves) / len(high_vol_moves)
                low_avg = sum(low_vol_moves) / len(low_vol_moves)
                observations['volume_correlation'] = (high_avg / low_avg - 1) * 100 if low_avg > 0 else 0

    profile['observations'].append(observations)
    profile['observations'] = profile['observations'][-100:]  # Keep last 100

    # Calculate personality from observations
    if len(profile['observations']) >= 5:
        recent = profile['observations'][-10:]

        avg_momentum = sum(o['momentum_score'] for o in recent) / len(recent)
        avg_mean_rev = sum(o['mean_reversion_score'] for o in recent) / len(recent)
        avg_vol_corr = sum(o['volume_correlation'] for o in recent) / len(recent)
        avg_trend = sum(o['trend_persistence'] for o in recent) / len(recent)

        profile['personality'] = {
            'type': 'momentum' if avg_momentum > 55 else ('mean_reversion' if avg_mean_rev > 55 else 'mixed'),
            'momentum_score': avg_momentum,
            'mean_reversion_score': avg_mean_rev,
            'volume_responsive': avg_vol_corr > 20,
            'volume_impact': avg_vol_corr,
            'avg_trend_length': avg_trend,
            'recommended_strategy': _get_recommended_strategy(avg_momentum, avg_vol_corr, avg_trend)
        }

    profile['last_updated'] = datetime.now().isoformat()
    save_stock_profiles(data)

    return profile['personality']

def _get_recommended_strategy(momentum_score, volume_impact, trend_length):
    """Recommend trading strategy based on personality."""
    if momentum_score > 55 and trend_length > 2:
        return 'breakout_momentum'
    elif momentum_score < 45:
        return 'mean_reversion_pullback'
    elif volume_impact > 30:
        return 'volume_breakout'
    else:
        return 'wait_for_setup'

def get_stock_profile(ticker):
    """Get a stock's personality profile."""
    data = load_stock_profiles()
    return data['profiles'].get(ticker, {}).get('personality', {})

def get_all_stock_profiles():
    """Get all stock profiles with personalities."""
    data = load_stock_profiles()
    return {
        ticker: profile.get('personality', {})
        for ticker, profile in data['profiles'].items()
        if profile.get('personality')
    }


# =============================================================================
# 5. SECTOR ROTATION ACCURACY
# =============================================================================

def load_sector_rotation_data():
    """Load sector rotation learning data."""
    path = LEARNING_DATA_DIR / 'sector_rotation.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'rotation_signals': [],
        'accuracy_by_rotation': {},  # e.g., "defensive_to_cyclical"
        'sector_performance_after_signal': {},
    }

def save_sector_rotation_data(data):
    """Save sector rotation data."""
    path = LEARNING_DATA_DIR / 'sector_rotation.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def record_rotation_signal(from_sector, to_sector, confidence, market_context=None):
    """Record a sector rotation signal."""
    data = load_sector_rotation_data()

    signal = {
        'id': f"{from_sector}_to_{to_sector}_{datetime.now().strftime('%Y%m%d')}",
        'from_sector': from_sector,
        'to_sector': to_sector,
        'confidence': confidence,
        'timestamp': datetime.now().isoformat(),
        'market_context': market_context,  # bull, bear, etc.
        'outcome': None,
        'to_sector_return_10d': None,
        'from_sector_return_10d': None,
    }

    data['rotation_signals'].append(signal)
    save_sector_rotation_data(data)
    return signal['id']

def update_rotation_outcome(signal_id, to_sector_return, from_sector_return):
    """Update a rotation signal with its outcome."""
    data = load_sector_rotation_data()

    for signal in data['rotation_signals']:
        if signal['id'] == signal_id:
            signal['to_sector_return_10d'] = to_sector_return
            signal['from_sector_return_10d'] = from_sector_return

            # Rotation was correct if to_sector outperformed from_sector
            outperformance = to_sector_return - from_sector_return
            signal['outperformance'] = outperformance
            signal['outcome'] = 'correct' if outperformance > 2 else ('wrong' if outperformance < -2 else 'neutral')

            # Update accuracy stats
            rotation_type = f"{signal['from_sector']}_to_{signal['to_sector']}"
            if rotation_type not in data['accuracy_by_rotation']:
                data['accuracy_by_rotation'][rotation_type] = {
                    'correct': 0, 'wrong': 0, 'neutral': 0, 'avg_outperformance': []
                }

            stats = data['accuracy_by_rotation'][rotation_type]
            if signal['outcome'] == 'correct':
                stats['correct'] += 1
            elif signal['outcome'] == 'wrong':
                stats['wrong'] += 1
            else:
                stats['neutral'] += 1
            stats['avg_outperformance'].append(outperformance)
            break

    save_sector_rotation_data(data)

def get_rotation_accuracy_insights():
    """Get insights about sector rotation accuracy."""
    data = load_sector_rotation_data()
    insights = {
        'reliable_rotations': [],
        'unreliable_rotations': [],
        'recommendations': []
    }

    for rotation, stats in data.get('accuracy_by_rotation', {}).items():
        total = stats['correct'] + stats['wrong'] + stats['neutral']
        if total >= 3:
            accuracy = stats['correct'] / total * 100
            avg_out = sum(stats['avg_outperformance']) / len(stats['avg_outperformance']) if stats['avg_outperformance'] else 0

            entry = {
                'rotation': rotation,
                'accuracy': accuracy,
                'avg_outperformance': avg_out,
                'total_signals': total
            }

            if accuracy >= 60:
                insights['reliable_rotations'].append(entry)
            elif accuracy < 40:
                insights['unreliable_rotations'].append(entry)

    insights['reliable_rotations'].sort(key=lambda x: x['accuracy'], reverse=True)
    insights['unreliable_rotations'].sort(key=lambda x: x['accuracy'])

    if insights['reliable_rotations']:
        best = insights['reliable_rotations'][0]
        insights['recommendations'].append(
            f"Trust {best['rotation'].replace('_', ' ')} signals ({best['accuracy']:.0f}% accurate)"
        )

    if insights['unreliable_rotations']:
        worst = insights['unreliable_rotations'][0]
        insights['recommendations'].append(
            f"Be skeptical of {worst['rotation'].replace('_', ' ')} signals ({worst['accuracy']:.0f}% accurate)"
        )

    return insights


# =============================================================================
# 6. MARKET REGIME ADAPTATION
# =============================================================================

def load_market_regime_data():
    """Load market regime learning data."""
    path = LEARNING_DATA_DIR / 'market_regime.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'regime_history': [],
        'strategy_performance_by_regime': {},
        'current_regime': None,
    }

def save_market_regime_data(data):
    """Save market regime data."""
    path = LEARNING_DATA_DIR / 'market_regime.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def detect_market_regime(spy_data):
    """
    Detect current market regime.

    Regimes:
    - bull_trending: Strong uptrend, low volatility
    - bull_volatile: Uptrend but choppy
    - bear_trending: Strong downtrend
    - bear_volatile: Downtrend and choppy
    - range_bound: Sideways
    - high_volatility: VIX spike
    """
    if len(spy_data) < 50:
        return 'unknown'

    closes = spy_data['Close'].values if hasattr(spy_data['Close'], 'values') else spy_data['Close']

    # Calculate trend (using 20 and 50 SMA)
    sma_20 = sum(closes[-20:]) / 20
    sma_50 = sum(closes[-50:]) / 50
    current = closes[-1]

    # Calculate volatility (simple std dev)
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(-20, 0)]
    volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5 * 100

    # Trend direction
    trend_up = current > sma_20 > sma_50
    trend_down = current < sma_20 < sma_50

    # Volatility threshold (roughly VIX-like)
    high_vol = volatility > 1.5

    if trend_up and not high_vol:
        regime = 'bull_trending'
    elif trend_up and high_vol:
        regime = 'bull_volatile'
    elif trend_down and not high_vol:
        regime = 'bear_trending'
    elif trend_down and high_vol:
        regime = 'bear_volatile'
    elif high_vol:
        regime = 'high_volatility'
    else:
        regime = 'range_bound'

    return regime

def record_regime_change(regime, spy_price):
    """Record a regime change."""
    data = load_market_regime_data()

    data['regime_history'].append({
        'regime': regime,
        'timestamp': datetime.now().isoformat(),
        'spy_price': spy_price
    })

    data['current_regime'] = regime
    save_market_regime_data(data)

def record_strategy_performance_in_regime(strategy, regime, pct_return, ticker=None):
    """Record how a strategy performed in a specific regime."""
    data = load_market_regime_data()

    if regime not in data['strategy_performance_by_regime']:
        data['strategy_performance_by_regime'][regime] = {}

    if strategy not in data['strategy_performance_by_regime'][regime]:
        data['strategy_performance_by_regime'][regime][strategy] = {
            'returns': [],
            'win_count': 0,
            'loss_count': 0,
        }

    stats = data['strategy_performance_by_regime'][regime][strategy]
    stats['returns'].append(pct_return)
    if pct_return > 2:
        stats['win_count'] += 1
    elif pct_return < -2:
        stats['loss_count'] += 1

    save_market_regime_data(data)

def get_best_strategies_for_regime(regime=None):
    """Get best strategies for a regime (or current regime)."""
    data = load_market_regime_data()

    if regime is None:
        regime = data.get('current_regime', 'unknown')

    if regime not in data.get('strategy_performance_by_regime', {}):
        return {'regime': regime, 'strategies': [], 'message': 'Not enough data for this regime'}

    results = []
    for strategy, stats in data['strategy_performance_by_regime'][regime].items():
        if len(stats['returns']) >= 3:
            avg_return = sum(stats['returns']) / len(stats['returns'])
            total = stats['win_count'] + stats['loss_count']
            win_rate = stats['win_count'] / total * 100 if total > 0 else 50

            results.append({
                'strategy': strategy,
                'avg_return': avg_return,
                'win_rate': win_rate,
                'total_trades': len(stats['returns'])
            })

    results.sort(key=lambda x: x['avg_return'], reverse=True)

    return {
        'regime': regime,
        'strategies': results[:5],
        'avoid': results[-2:] if len(results) > 2 else []
    }


# =============================================================================
# 7. NEWS IMPACT TIMING
# =============================================================================

def load_news_impact_data():
    """Load news impact timing data."""
    path = LEARNING_DATA_DIR / 'news_impact.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'news_events': [],
        'impact_by_type': {},  # earnings, merger, product_launch, analyst, macro
        'impact_by_ticker': {},
    }

def save_news_impact_data(data):
    """Save news impact data."""
    path = LEARNING_DATA_DIR / 'news_impact.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def record_news_event(ticker, news_type, headline, price_at_news, sentiment=None):
    """Record a news event for impact tracking."""
    data = load_news_impact_data()

    event = {
        'id': f"{ticker}_{news_type}_{datetime.now().strftime('%Y%m%d_%H%M')}",
        'ticker': ticker,
        'news_type': news_type,  # earnings, merger, product_launch, analyst, macro, rumor
        'headline': headline,
        'sentiment': sentiment,  # positive, negative, neutral
        'price_at_news': price_at_news,
        'timestamp': datetime.now().isoformat(),
        'price_after_1h': None,
        'price_after_1d': None,
        'price_after_3d': None,
        'price_after_5d': None,
        'fully_priced_in_by': None,  # When did price stabilize
    }

    data['news_events'].append(event)
    save_news_impact_data(data)
    return event['id']

def update_news_impact(event_id, prices_after):
    """
    Update news event with price data after the event.
    prices_after: dict with keys like '1h', '1d', '3d', '5d'
    """
    data = load_news_impact_data()

    for event in data['news_events']:
        if event['id'] == event_id:
            price_at_news = event['price_at_news']

            for period, price in prices_after.items():
                field = f'price_after_{period}'
                if field in event:
                    event[field] = price

            # Calculate when price was fully priced in
            # (when price move from news stopped)
            changes = []
            for period in ['1h', '1d', '3d', '5d']:
                field = f'price_after_{period}'
                if event.get(field) and price_at_news:
                    pct_change = (event[field] - price_at_news) / price_at_news * 100
                    changes.append((period, pct_change))

            if len(changes) >= 2:
                # Find when the move stabilized (< 1% additional move)
                for i in range(1, len(changes)):
                    if abs(changes[i][1] - changes[i-1][1]) < 1:
                        event['fully_priced_in_by'] = changes[i-1][0]
                        break

                # Update statistics
                _update_news_impact_stats(data, event, changes)
            break

    save_news_impact_data(data)

def _update_news_impact_stats(data, event, changes):
    """Update news impact statistics."""
    news_type = event['news_type']
    ticker = event['ticker']

    # By news type
    if news_type not in data['impact_by_type']:
        data['impact_by_type'][news_type] = {
            'avg_move_1d': [],
            'avg_move_5d': [],
            'priced_in_times': [],
        }

    stats = data['impact_by_type'][news_type]
    for period, change in changes:
        if period == '1d':
            stats['avg_move_1d'].append(abs(change))
        elif period == '5d':
            stats['avg_move_5d'].append(abs(change))

    if event.get('fully_priced_in_by'):
        time_map = {'1h': 0.04, '1d': 1, '3d': 3, '5d': 5}
        stats['priced_in_times'].append(time_map.get(event['fully_priced_in_by'], 1))

    # By ticker
    if ticker not in data['impact_by_ticker']:
        data['impact_by_ticker'][ticker] = {
            'news_responsiveness': [],  # How much it moves on news
            'pricing_speed': [],  # How fast it prices in
        }

    ticker_stats = data['impact_by_ticker'][ticker]
    if changes:
        max_move = max(abs(c[1]) for _, c in enumerate(changes))
        ticker_stats['news_responsiveness'].append(max_move)

    if event.get('fully_priced_in_by'):
        time_map = {'1h': 0.04, '1d': 1, '3d': 3, '5d': 5}
        ticker_stats['pricing_speed'].append(time_map.get(event['fully_priced_in_by'], 1))

def get_news_impact_insights():
    """Get insights about news impact timing."""
    data = load_news_impact_data()
    insights = {
        'by_news_type': {},
        'fast_pricing_tickers': [],
        'slow_pricing_tickers': [],
        'recommendations': []
    }

    # Analyze by news type
    for news_type, stats in data.get('impact_by_type', {}).items():
        if stats['priced_in_times']:
            avg_pricing_time = sum(stats['priced_in_times']) / len(stats['priced_in_times'])
            avg_move_1d = sum(stats['avg_move_1d']) / len(stats['avg_move_1d']) if stats['avg_move_1d'] else 0

            insights['by_news_type'][news_type] = {
                'avg_days_to_price_in': avg_pricing_time,
                'avg_move_1d': avg_move_1d,
                'sample_size': len(stats['priced_in_times'])
            }

    # Analyze by ticker
    for ticker, stats in data.get('impact_by_ticker', {}).items():
        if stats['pricing_speed'] and len(stats['pricing_speed']) >= 3:
            avg_speed = sum(stats['pricing_speed']) / len(stats['pricing_speed'])
            avg_response = sum(stats['news_responsiveness']) / len(stats['news_responsiveness']) if stats['news_responsiveness'] else 0

            entry = {
                'ticker': ticker,
                'avg_pricing_days': avg_speed,
                'avg_move_pct': avg_response
            }

            if avg_speed <= 1:
                insights['fast_pricing_tickers'].append(entry)
            elif avg_speed >= 3:
                insights['slow_pricing_tickers'].append(entry)

    # Generate recommendations
    for news_type, stats in insights['by_news_type'].items():
        days = stats['avg_days_to_price_in']
        if days < 1:
            insights['recommendations'].append(
                f"{news_type} news: Act within hours (priced in by day 1)"
            )
        elif days < 3:
            insights['recommendations'].append(
                f"{news_type} news: You have 1-2 days to position"
            )
        else:
            insights['recommendations'].append(
                f"{news_type} news: Takes {days:.0f}+ days to fully price in"
            )

    return insights


# =============================================================================
# UNIFIED LEARNING INTERFACE
# =============================================================================

def get_all_learning_insights():
    """Get comprehensive insights from all learning systems."""
    return {
        'alert_accuracy': get_alert_accuracy_insights(),
        'entry_timing': get_best_entry_strategy(),
        'theme_lifecycle': get_theme_lifecycle_insights(),
        'stock_profiles': get_all_stock_profiles(),
        'sector_rotation': get_rotation_accuracy_insights(),
        'market_regime': get_best_strategies_for_regime(),
        'news_impact': get_news_impact_insights(),
    }

def format_learning_summary():
    """Format a summary of all learning insights."""
    insights = get_all_learning_insights()

    msg = "🧠 *SELF-LEARNING INSIGHTS*\n\n"

    # Alert Accuracy
    alert = insights.get('alert_accuracy', {})
    if alert.get('best_alert_types'):
        msg += "*📊 Best Alert Types:*\n"
        for a in alert['best_alert_types'][:2]:
            msg += f"• {a['type']}: {a['win_rate']:.0f}% win rate\n"
        msg += "\n"

    # Entry Timing
    entry = insights.get('entry_timing', [])
    if entry and isinstance(entry, list):
        msg += "*🎯 Best Entry Strategies:*\n"
        for e in entry[:2]:
            msg += f"• {e['strategy']}: {e['win_rate']:.0f}% win, {e['avg_gain']:.1f}% avg\n"
        msg += "\n"

    # Theme Lifecycle
    theme = insights.get('theme_lifecycle', {})
    if theme.get('current_stage_predictions'):
        msg += "*📈 Theme Status:*\n"
        for name, pred in list(theme['current_stage_predictions'].items())[:3]:
            msg += f"• {name}: {pred['stage']} (~{pred['estimated_days_remaining']}d left)\n"
        msg += "\n"

    # Stock Profiles
    profiles = insights.get('stock_profiles', {})
    if profiles:
        msg += "*🎭 Stock Personalities:*\n"
        for ticker, profile in list(profiles.items())[:3]:
            ptype = profile.get('type', 'unknown')
            strat = profile.get('recommended_strategy', 'unknown')
            msg += f"• {ticker}: {ptype} → {strat.replace('_', ' ')}\n"
        msg += "\n"

    # Market Regime
    regime = insights.get('market_regime', {})
    if regime.get('regime') and regime['regime'] != 'unknown':
        msg += f"*🌍 Market Regime:* {regime['regime'].replace('_', ' ')}\n"
        if regime.get('strategies'):
            best = regime['strategies'][0]
            msg += f"• Best strategy: {best['strategy']} ({best['win_rate']:.0f}% win)\n"
        msg += "\n"

    # News Impact
    news = insights.get('news_impact', {})
    if news.get('recommendations'):
        msg += "*📰 News Timing:*\n"
        for rec in news['recommendations'][:2]:
            msg += f"• {rec}\n"
        msg += "\n"

    # Sector Rotation
    rotation = insights.get('sector_rotation', {})
    if rotation.get('recommendations'):
        msg += "*🔄 Rotation Signals:*\n"
        for rec in rotation['recommendations'][:2]:
            msg += f"• {rec}\n"

    if msg == "🧠 *SELF-LEARNING INSIGHTS*\n\n":
        msg += "_No insights yet. The system learns as you trade and use commands._\n"
        msg += "_Run /stories, /news, /sectors to start collecting data._"

    return msg


# =============================================================================
# AUTO-LEARNING HOOKS
# =============================================================================

def auto_learn_from_scan(scan_results, market_data=None):
    """
    Automatically learn from a scan run.
    Call this after each scheduled scan.
    """
    if market_data is not None:
        # Update market regime
        try:
            regime = detect_market_regime(market_data)
            if market_data is not None and len(market_data) > 0:
                spy_price = float(market_data['Close'].iloc[-1])
                record_regime_change(regime, spy_price)
        except Exception as e:
            logger.error(f"Error updating market regime: {e}")

    # Record alerts from scan results
    for _, row in scan_results.iterrows() if hasattr(scan_results, 'iterrows') else []:
        ticker = row.get('ticker', '')
        score = row.get('composite_score', 0)

        if score >= 80:  # High conviction alert
            try:
                price = row.get('close', row.get('price', 0))
                alert_type = 'high_score_scan'

                if row.get('in_squeeze'):
                    alert_type = 'squeeze_setup'
                elif row.get('rs_composite', 0) > 10:
                    alert_type = 'rs_leader'
                elif row.get('volume_ratio', 0) > 2:
                    alert_type = 'volume_spike'

                record_alert(ticker, alert_type, price, context={
                    'score': score,
                    'sector': row.get('sector', 'unknown')
                })
            except Exception as e:
                logger.error(f"Error recording alert for {ticker}: {e}")

def auto_learn_from_news(news_results):
    """
    Automatically learn from news analysis.
    Call this after news aggregation.
    """
    for item in news_results:
        try:
            ticker = item.get('ticker', '')
            news_type = item.get('type', 'general')
            headline = item.get('headline', item.get('title', ''))
            sentiment = item.get('sentiment', 'neutral')
            price = item.get('price', 0)

            if ticker and headline:
                record_news_event(ticker, news_type, headline, price, sentiment)
        except Exception as e:
            logger.error(f"Error learning from news: {e}")

def auto_learn_stock_profile(ticker, price_data):
    """
    Automatically analyze and update a stock's personality profile.
    """
    try:
        return analyze_stock_personality(ticker, price_data)
    except Exception as e:
        logger.error(f"Error analyzing stock profile for {ticker}: {e}")
        return {}
