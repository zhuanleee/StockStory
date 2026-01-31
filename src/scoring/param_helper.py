"""
Parameter Helper - Easy access to learned parameters for all modules.

This module provides simple functions to access parameter values
from the central registry. Import this instead of hardcoding values.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger('param_helper')

# Lazy-loaded registry
_registry = None
_registry_checked = False  # Track if we've already checked


def _get_registry():
    """Get the parameter registry (lazy load)"""
    global _registry, _registry_checked
    if not _registry_checked:
        _registry_checked = True
        try:
            from src.learning.parameter_learning import get_registry
            _registry = get_registry()
        except ImportError:
            logger.warning("Parameter learning not available, using defaults")
            _registry = None
    return _registry


def get(name: str, default: float = None) -> float:
    """
    Get a parameter value by name.
    Falls back to default if parameter system unavailable.
    """
    registry = _get_registry()
    if registry:
        try:
            return registry.get(name)
        except KeyError:
            if default is not None:
                return default
            raise
    if default is not None:
        return default
    raise ValueError(f"Parameter '{name}' not found and no default provided")


# =============================================================================
# SCORING WEIGHTS
# =============================================================================

def weight_theme_heat() -> float:
    return get('weight.theme_heat', 0.18)

def weight_catalyst() -> float:
    return get('weight.catalyst', 0.18)

def weight_social_buzz() -> float:
    return get('weight.social_buzz', 0.12)

def weight_news_momentum() -> float:
    return get('weight.news_momentum', 0.10)

def weight_sentiment() -> float:
    return get('weight.sentiment', 0.07)

def weight_ecosystem() -> float:
    return get('weight.ecosystem', 0.10)

def weight_technical() -> float:
    return get('weight.technical', 0.25)


def get_scoring_weights() -> Dict[str, float]:
    """Get all scoring weights as a dict"""
    return {
        'theme_heat': weight_theme_heat(),
        'catalyst': weight_catalyst(),
        'social_buzz': weight_social_buzz(),
        'news_momentum': weight_news_momentum(),
        'sentiment': weight_sentiment(),
        'ecosystem': weight_ecosystem(),
        'technical': weight_technical(),
    }


# =============================================================================
# ROLE & STAGE SCORES
# =============================================================================

def role_score_driver() -> float:
    return get('role.driver', 100)

def role_score_beneficiary() -> float:
    return get('role.beneficiary', 70)

def role_score_picks_shovels() -> float:
    return get('role.picks_shovels', 50)

def get_role_scores() -> Dict[str, float]:
    """Get role scores as a dict"""
    return {
        'driver': role_score_driver(),
        'beneficiary': role_score_beneficiary(),
        'picks_shovels': role_score_picks_shovels(),
    }


def stage_score_early() -> float:
    return get('stage.early', 100)

def stage_score_middle() -> float:
    return get('stage.middle', 70)

def stage_score_late() -> float:
    return get('stage.late', 30)

def stage_score_ongoing() -> float:
    return get('stage.ongoing', 60)

def stage_score_unknown() -> float:
    return get('stage.unknown', 50)

def get_stage_scores() -> Dict[str, float]:
    """Get stage scores as a dict"""
    return {
        'early': stage_score_early(),
        'middle': stage_score_middle(),
        'late': stage_score_late(),
        'ongoing': stage_score_ongoing(),
        'unknown': stage_score_unknown(),
    }


# =============================================================================
# MULTIPLIERS
# =============================================================================

def multiplier_early_stage_boost() -> float:
    return get('multiplier.early_stage_boost', 1.2)

def multiplier_catalyst_near_7d() -> float:
    return get('multiplier.catalyst_near_7d', 1.3)

def multiplier_catalyst_near_14d() -> float:
    return get('multiplier.catalyst_near_14d', 1.1)

def multiplier_strong_sentiment() -> float:
    return get('multiplier.strong_sentiment', 1.5)

def multiplier_volume_score() -> float:
    return get('multiplier.volume_score', 40)

def multiplier_rs_score() -> float:
    return get('multiplier.rs_score', 5)


# =============================================================================
# THRESHOLDS - SENTIMENT
# =============================================================================

def threshold_sentiment_bullish() -> float:
    return get('threshold.sentiment.bullish', 65)

def threshold_sentiment_bearish() -> float:
    return get('threshold.sentiment.bearish', 35)

def threshold_sentiment_strong_bullish_pct() -> float:
    return get('threshold.sentiment.strong_bullish_pct', 70)

def threshold_sentiment_bullish_pct() -> float:
    return get('threshold.sentiment.bullish_pct', 55)

def threshold_sentiment_bearish_pct() -> float:
    return get('threshold.sentiment.bearish_pct', 45)

def threshold_sentiment_strong_bearish_pct() -> float:
    return get('threshold.sentiment.strong_bearish_pct', 30)


# =============================================================================
# THRESHOLDS - NEWS MOMENTUM
# =============================================================================

def threshold_momentum_accelerating() -> float:
    return get('threshold.momentum.accelerating', 1.5)

def threshold_momentum_stable() -> float:
    return get('threshold.momentum.stable', 0.8)

def score_momentum_accelerating_base() -> float:
    return get('score.momentum.accelerating_base', 80)

def score_momentum_stable_base() -> float:
    return get('score.momentum.stable_base', 50)

def score_momentum_declining() -> float:
    return get('score.momentum.declining', 30)


# =============================================================================
# THRESHOLDS - TECHNICAL
# =============================================================================

def score_technical_trend_3() -> float:
    return get('score.technical.trend_3', 100)

def score_technical_trend_2() -> float:
    return get('score.technical.trend_2', 70)

def score_technical_trend_1() -> float:
    return get('score.technical.trend_1', 50)

def score_technical_trend_0() -> float:
    return get('score.technical.trend_0', 20)


# =============================================================================
# THRESHOLDS - SOCIAL BUZZ
# =============================================================================

def threshold_stocktwits_high() -> float:
    return get('threshold.stocktwits.high', 20)

def threshold_stocktwits_medium() -> float:
    return get('threshold.stocktwits.medium', 10)

def threshold_stocktwits_low() -> float:
    return get('threshold.stocktwits.low', 5)

def score_stocktwits_high() -> float:
    return get('score.stocktwits.high', 30)

def score_stocktwits_medium() -> float:
    return get('score.stocktwits.medium', 20)

def score_stocktwits_low() -> float:
    return get('score.stocktwits.low', 10)

def score_stocktwits_bullish_boost() -> float:
    return get('score.stocktwits.bullish_boost', 20)

def threshold_reddit_high() -> float:
    return get('threshold.reddit.high', 5)

def threshold_reddit_medium() -> float:
    return get('threshold.reddit.medium', 2)

def threshold_reddit_score_high() -> float:
    return get('threshold.reddit.score_high', 500)

def threshold_reddit_score_medium() -> float:
    return get('threshold.reddit.score_medium', 100)

def score_sec_8k() -> float:
    return get('score.sec.8k', 20)

def score_sec_insider() -> float:
    return get('score.sec.insider', 15)

def threshold_trending_reddit_mentions() -> float:
    return get('threshold.trending.reddit_mentions', 3)


# =============================================================================
# SIGNAL RANKER
# =============================================================================

def signal_initial_trust() -> float:
    return get('signal.initial_trust', 50)

def signal_consensus_4plus() -> float:
    return get('signal.consensus_4plus', 25)

def signal_consensus_2plus() -> float:
    return get('signal.consensus_2plus', 15)

def signal_consensus_1() -> float:
    return get('signal.consensus_1', 5)

def signal_tier1_bonus() -> float:
    return get('signal.tier1_bonus', 20)

def signal_tier2_bonus() -> float:
    return get('signal.tier2_bonus', 12)

def signal_multi_ticker_3plus() -> float:
    return get('signal.multi_ticker_3plus', 15)

def signal_multi_ticker_1plus() -> float:
    return get('signal.multi_ticker_1plus', 10)

def signal_catalyst_substantive() -> float:
    return get('signal.catalyst_substantive', 15)

def signal_catalyst_mentioned() -> float:
    return get('signal.catalyst_mentioned', 8)

def signal_smart_money_divergence() -> float:
    return get('signal.smart_money_divergence', 25)

def signal_weight_source_trust() -> float:
    return get('signal.weight.source_trust', 0.25)

def signal_weight_signal_strength() -> float:
    return get('signal.weight.signal_strength', 0.30)

def signal_weight_timing() -> float:
    return get('signal.weight.timing', 0.25)

def signal_weight_novelty() -> float:
    return get('signal.weight.novelty', 0.20)


# =============================================================================
# CATALYST
# =============================================================================

def catalyst_window_earnings() -> float:
    return get('catalyst.window.earnings', 14)

def catalyst_window_fda() -> float:
    return get('catalyst.window.fda', 30)

def catalyst_window_product_launch() -> float:
    return get('catalyst.window.product_launch', 30)

def catalyst_window_conference() -> float:
    return get('catalyst.window.conference', 7)

def catalyst_window_merger() -> float:
    return get('catalyst.window.merger', 90)

def catalyst_impact_very_high() -> float:
    return get('catalyst.impact.very_high', 100)

def catalyst_impact_high() -> float:
    return get('catalyst.impact.high', 75)

def catalyst_impact_medium() -> float:
    return get('catalyst.impact.medium', 50)

def catalyst_impact_low() -> float:
    return get('catalyst.impact.low', 25)

def get_catalyst_impact_scores() -> Dict[str, float]:
    """Get catalyst impact scores as a dict"""
    return {
        'very_high': catalyst_impact_very_high(),
        'high': catalyst_impact_high(),
        'medium': catalyst_impact_medium(),
        'low': catalyst_impact_low(),
    }


# =============================================================================
# KEYWORD WEIGHTS
# =============================================================================

def keyword_bullish_strong() -> float:
    return get('keyword.bullish.strong', 3)

def keyword_bullish_medium() -> float:
    return get('keyword.bullish.medium', 2)

def keyword_bullish_weak() -> float:
    return get('keyword.bullish.weak', 1)

def keyword_bearish_strong() -> float:
    return get('keyword.bearish.strong', 3)

def keyword_bearish_medium() -> float:
    return get('keyword.bearish.medium', 2)

def keyword_bearish_weak() -> float:
    return get('keyword.bearish.weak', 1)


# =============================================================================
# TECHNICAL
# =============================================================================

def technical_ma_short() -> int:
    return int(get('technical.ma.short', 20))

def technical_ma_medium() -> int:
    return int(get('technical.ma.medium', 50))

def technical_ma_long() -> int:
    return int(get('technical.ma.long', 200))

def technical_squeeze_percentile() -> float:
    return get('technical.squeeze.percentile', 20)

def technical_volume_level1() -> float:
    return get('technical.volume.level1', 1.2)

def technical_volume_level2() -> float:
    return get('technical.volume.level2', 1.5)

def technical_volume_level3() -> float:
    return get('technical.volume.level3', 2.0)


# =============================================================================
# OUTCOME
# =============================================================================

def outcome_win_threshold() -> float:
    return get('outcome.win_threshold', 2.0)

def outcome_loss_threshold() -> float:
    return get('outcome.loss_threshold', -2.0)

def outcome_win_rate_min() -> float:
    return get('outcome.win_rate_min', 40)

def outcome_promotion_threshold() -> int:
    return int(get('outcome.promotion_threshold', 3))


# =============================================================================
# OUTCOME TRACKING
# =============================================================================

def record_alert_outcome(ticker: str, score: float, score_breakdown: dict,
                          market_regime: str = 'unknown') -> str:
    """Record an alert with its parameter snapshot for learning"""
    try:
        from src.learning.parameter_learning import record_alert_with_params
        return record_alert_with_params(ticker, score, score_breakdown, market_regime)
    except ImportError:
        return None


def update_outcome(alert_id: str, outcomes: dict) -> bool:
    """Update an alert with its actual outcome"""
    try:
        from src.learning.parameter_learning import update_alert_outcome
        return update_alert_outcome(alert_id, outcomes)
    except ImportError:
        return False


# =============================================================================
# LEARNING STATUS
# =============================================================================

def get_learning_status() -> Dict[str, Any]:
    """Get comprehensive learning status"""
    try:
        # Import directly from module file to avoid loading heavy ML dependencies
        import importlib.util
        import os
        from pathlib import Path

        # Find parameter_learning.py relative to this file
        learning_dir = Path(__file__).parent.parent / "learning"
        param_learning_path = learning_dir / "parameter_learning.py"

        spec = importlib.util.spec_from_file_location("parameter_learning", param_learning_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.get_learning_status()
    except Exception as e:
        import traceback
        logger.error(f"Failed to load parameter learning: {e}\n{traceback.format_exc()}")
        return {'error': f'Parameter learning not available: {str(e)}'}


def run_health_check() -> Dict[str, Any]:
    """Run health check on parameter learning system"""
    try:
        from src.learning.parameter_learning import run_health_check as _health_check
        return _health_check()
    except ImportError:
        return {'error': 'Parameter learning not available', 'status': 'unavailable'}
