#!/usr/bin/env python3
"""
Learning System API

REST API endpoints for the self-learning brain.
Provides:
- Decision making
- Learning from trades
- Statistics and monitoring
- Configuration management
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, Optional
import traceback

from .learning_brain import get_learning_brain, LearningConfig
from .rl_models import (
    ComponentScores,
    MarketContext,
    TradeRecord,
    MarketRegimeType,
    TradeOutcome,
    create_trade_id
)


# Create blueprint
learning_bp = Blueprint('learning', __name__, url_prefix='/api/learning')


# =============================================================================
# DECISION ENDPOINTS
# =============================================================================

@learning_bp.route('/decide', methods=['POST'])
def get_decision():
    """
    Get a trading decision from the learning brain.

    Request body:
    {
        "ticker": "NVDA",
        "component_scores": {
            "theme_score": 8.5,
            "technical_score": 7.2,
            "ai_confidence": 0.85,
            "x_sentiment_score": 0.6
        },
        "market_context": {
            "spy_change_pct": 2.5,
            "vix_level": 15.0,
            "stocks_above_ma50": 70.0
        },
        "portfolio_state": {  // Optional, needed for Tier 3+
            "cash_pct": 80.0,
            "num_positions": 2
        },
        "training": true  // Whether to explore (true) or exploit (false)
    }

    Response:
    {
        "ok": true,
        "decision": {
            "decision_id": "DEC_NVDA_20260129_143022",
            "ticker": "NVDA",
            "action": "buy",
            "position_size": 15.0,
            "conviction": 0.85,
            "overall_score": 8.2,
            "signal_quality": "excellent",
            "setup_complete": true,
            "regime": "bull_momentum",
            "weights": {
                "theme": 0.35,
                "technical": 0.25,
                "ai": 0.25,
                "sentiment": 0.15
            },
            "stop_loss": 10.0,
            "take_profit": 20.0
        }
    }
    """
    try:
        data = request.json
        brain = get_learning_brain()

        # Parse component scores
        scores_data = data.get('component_scores', {})
        scores = ComponentScores(
            theme_score=scores_data.get('theme_score', 0.0),
            technical_score=scores_data.get('technical_score', 0.0),
            ai_confidence=scores_data.get('ai_confidence', 0.5),
            x_sentiment_score=scores_data.get('x_sentiment_score', 0.0),
            rs_rating=scores_data.get('rs_rating'),
            momentum_score=scores_data.get('momentum_score'),
            volume_ratio=scores_data.get('volume_ratio')
        )

        # Parse market context
        context_data = data.get('market_context', {})
        context = MarketContext(
            spy_change_pct=context_data.get('spy_change_pct'),
            vix_level=context_data.get('vix_level'),
            stocks_above_ma50=context_data.get('stocks_above_ma50'),
            advance_decline=context_data.get('advance_decline'),
            crisis_active=context_data.get('crisis_active', False)
        )

        # Get decision
        decision = brain.get_trading_decision(
            ticker=data['ticker'],
            component_scores=scores,
            market_context=context,
            portfolio_state=data.get('portfolio_state'),
            training=data.get('training', True)
        )

        return jsonify({
            'ok': True,
            'decision': {
                'decision_id': decision.decision_id,
                'ticker': decision.ticker,
                'action': decision.action,
                'position_size': decision.position_size,
                'conviction': decision.conviction,
                'overall_score': decision.overall_score,
                'signal_quality': decision.signal_quality,
                'setup_complete': decision.setup_complete,
                'regime': decision.regime_at_decision.value if decision.regime_at_decision else 'unknown',
                'weights': decision.weights_used.to_dict(),
                'stop_loss': decision.stop_loss,
                'take_profit': decision.take_profit,
                'learner': decision.learner_type.value if decision.learner_type else None
            }
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# =============================================================================
# LEARNING ENDPOINTS
# =============================================================================

@learning_bp.route('/learn', methods=['POST'])
def learn_from_trade():
    """
    Submit a trade for learning.

    Request body:
    {
        "trade": {
            "ticker": "NVDA",
            "decision_id": "DEC_NVDA_20260129_143022",
            "entry_price": 850.0,
            "exit_price": 875.0,
            "entry_date": "2026-01-29T14:30:00",
            "exit_date": "2026-01-30T15:45:00",
            "shares": 100,
            "outcome": "win",  // or "loss", "breakeven"
            "component_scores": {...},
            "market_context": {...}
        },
        "portfolio_state": {
            "cash_pct": 85.0,
            "current_drawdown_pct": 2.5
        }
    }

    Response:
    {
        "ok": true,
        "learning_active": true,
        "total_trades": 25,
        "current_metrics": {
            "win_rate": 0.65,
            "sharpe_ratio": 1.2
        }
    }
    """
    try:
        data = request.json
        brain = get_learning_brain()

        trade_data = data['trade']

        # Parse component scores
        scores = ComponentScores(**trade_data.get('component_scores', {}))

        # Parse market context
        context = MarketContext(**trade_data.get('market_context', {}))

        # Create trade record
        trade = TradeRecord(
            trade_id=trade_data.get('trade_id', create_trade_id(trade_data['ticker'], datetime.now())),
            decision_id=trade_data.get('decision_id', ''),
            ticker=trade_data['ticker'],
            entry_date=datetime.fromisoformat(trade_data['entry_date']),
            exit_date=datetime.fromisoformat(trade_data['exit_date']) if trade_data.get('exit_date') else None,
            entry_price=trade_data['entry_price'],
            exit_price=trade_data.get('exit_price'),
            shares=trade_data.get('shares', 0),
            component_scores=scores,
            market_context=context,
            outcome=TradeOutcome(trade_data.get('outcome', 'open'))
        )

        # Calculate outcome if not provided
        if trade.exit_price:
            trade.calculate_outcome()

        # Learn from trade
        brain.learn_from_trade(trade, data.get('portfolio_state'))

        return jsonify({
            'ok': True,
            'learning_active': brain.learning_active,
            'total_trades': brain.total_trades,
            'current_metrics': {
                'win_rate': brain.metrics.win_rate,
                'sharpe_ratio': brain.metrics.sharpe_ratio,
                'profit_factor': brain.metrics.profit_factor
            }
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# =============================================================================
# STATISTICS ENDPOINTS
# =============================================================================

@learning_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """
    Get comprehensive learning statistics.

    Response:
    {
        "ok": true,
        "statistics": {
            "overview": {...},
            "performance": {...},
            "current_weights": {...},
            "tiers": {...}
        }
    }
    """
    try:
        brain = get_learning_brain()
        stats = brain.get_statistics()

        return jsonify({
            'ok': True,
            'statistics': stats
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@learning_bp.route('/weights', methods=['GET'])
def get_current_weights():
    """
    Get current component weights.

    Query params:
        - regime: Optional regime type (bull_momentum, bear_defensive, etc.)

    Response:
    {
        "ok": true,
        "weights": {
            "theme": 0.35,
            "technical": 0.25,
            "ai": 0.25,
            "sentiment": 0.15
        },
        "confidence": 0.85,
        "regime": "bull_momentum",
        "sample_size": 50
    }
    """
    try:
        brain = get_learning_brain()
        regime_str = request.args.get('regime')

        if regime_str and brain.bandit:
            regime = MarketRegimeType(regime_str)
            weights = brain.bandit.get_regime_weights(regime)
        else:
            weights = brain.current_weights

        return jsonify({
            'ok': True,
            'weights': weights.to_dict(),
            'confidence': weights.confidence,
            'regime': weights.regime.value if weights.regime else None,
            'sample_size': weights.sample_size
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@learning_bp.route('/regime', methods=['GET'])
def get_current_regime():
    """
    Get current market regime.

    Response:
    {
        "ok": true,
        "regime": "bull_momentum",
        "confidence": 0.85,
        "probabilities": {
            "bull_momentum": 0.7,
            "bear_defensive": 0.1,
            "choppy_range": 0.2
        }
    }
    """
    try:
        brain = get_learning_brain()

        if not brain.regime_detector:
            return jsonify({
                'ok': False,
                'error': 'Regime detection not enabled'
            }), 400

        state = brain.regime_detector.current_state

        return jsonify({
            'ok': True,
            'regime': state.current_regime.value,
            'confidence': state.confidence,
            'probabilities': {
                regime.value: prob
                for regime, prob in state.regime_probabilities.items()
            }
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@learning_bp.route('/performance', methods=['GET'])
def get_performance():
    """
    Get performance metrics.

    Response:
    {
        "ok": true,
        "metrics": {
            "total_trades": 50,
            "win_rate": 0.65,
            "sharpe_ratio": 1.2,
            "profit_factor": 2.1,
            "max_drawdown": 8.5,
            "current_drawdown": 2.3,
            "total_return": 15.7
        }
    }
    """
    try:
        brain = get_learning_brain()

        return jsonify({
            'ok': True,
            'metrics': {
                'total_trades': brain.total_trades,
                'win_rate': brain.metrics.win_rate,
                'sharpe_ratio': brain.metrics.sharpe_ratio,
                'profit_factor': brain.metrics.profit_factor,
                'max_drawdown': brain.metrics.max_drawdown_pct,
                'current_drawdown': brain.metrics.current_drawdown_pct,
                'total_return': brain.metrics.total_return_pct
            }
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


# =============================================================================
# MANAGEMENT ENDPOINTS
# =============================================================================

@learning_bp.route('/config', methods=['GET'])
def get_config():
    """
    Get current configuration.

    Response:
    {
        "ok": true,
        "config": {
            "use_tier1": true,
            "use_tier2": true,
            "use_tier3": false,
            "use_tier4": false,
            "learning_active": true,
            "circuit_breaker_active": false
        }
    }
    """
    try:
        brain = get_learning_brain()

        return jsonify({
            'ok': True,
            'config': {
                'use_tier1': brain.config.use_tier1,
                'use_tier2': brain.config.use_tier2,
                'use_tier3': brain.config.use_tier3,
                'use_tier4': brain.config.use_tier4,
                'learning_active': brain.learning_active,
                'circuit_breaker_active': brain.circuit_breaker_active,
                'min_trades_before_learning': brain.config.min_trades_before_learning,
                'max_position_size': brain.config.max_position_size,
                'max_drawdown': brain.config.max_drawdown
            }
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@learning_bp.route('/circuit-breaker', methods=['POST'])
def toggle_circuit_breaker():
    """
    Manually toggle circuit breaker.

    Request body:
    {
        "active": true  // or false
    }

    Response:
    {
        "ok": true,
        "circuit_breaker_active": true
    }
    """
    try:
        data = request.json
        brain = get_learning_brain()

        brain.circuit_breaker_active = data.get('active', False)

        return jsonify({
            'ok': True,
            'circuit_breaker_active': brain.circuit_breaker_active
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@learning_bp.route('/report', methods=['GET'])
def get_report():
    """
    Get full learning report as text.

    Response:
    {
        "ok": true,
        "report": "..."  // Full text report
    }
    """
    try:
        brain = get_learning_brain()

        # Capture print output
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        brain.print_report()

        sys.stdout = old_stdout
        report = buffer.getvalue()

        return jsonify({
            'ok': True,
            'report': report
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


# =============================================================================
# HEALTH CHECK
# =============================================================================

@learning_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.

    Response:
    {
        "ok": true,
        "status": "healthy",
        "tiers_active": {
            "tier1": true,
            "tier2": true,
            "tier3": false,
            "tier4": false
        }
    }
    """
    try:
        brain = get_learning_brain()

        return jsonify({
            'ok': True,
            'status': 'healthy',
            'tiers_active': {
                'tier1': brain.bandit is not None,
                'tier2': brain.regime_detector is not None,
                'tier3': brain.ppo_agent is not None,
                'tier4': brain.meta_learner is not None
            },
            'learning_active': brain.learning_active,
            'total_trades': brain.total_trades
        })

    except Exception as e:
        return jsonify({
            'ok': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@learning_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'ok': False,
        'error': 'Endpoint not found'
    }), 404


@learning_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'ok': False,
        'error': 'Internal server error',
        'details': str(error)
    }), 500


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    from flask import Flask

    print("Testing Learning API...")

    app = Flask(__name__)
    app.register_blueprint(learning_bp)

    print("\n✅ Learning API blueprint created")
    print("\nAvailable endpoints:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('learning'):
            print(f"  {rule.methods} {rule.rule}")

    print("\n✅ Learning API test complete!")
