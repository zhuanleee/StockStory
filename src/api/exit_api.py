#!/usr/bin/env python3
"""
Exit Analysis API Endpoints
============================
REST API for exit strategy analysis.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import asyncio

from src.trading.exit_analyzer import ExitAnalyzer, format_exit_analysis
from src.trading.position_monitor import get_position_monitor
from src.utils import get_logger

logger = get_logger(__name__)

exit_bp = Blueprint('exit', __name__)


@exit_bp.route('/api/exit/analyze/<ticker>', methods=['GET'])
def analyze_exit(ticker):
    """
    Analyze exit for a position.

    Query params:
        entry_price: Entry price (required)
        entry_date: Entry date ISO format (required)
        current_price: Current price (optional, will fetch if missing)
        shares: Position size (optional)

    Returns:
        Exit analysis with targets, signals, and recommendations
    """
    try:
        # Get parameters
        entry_price = request.args.get('entry_price', type=float)
        entry_date_str = request.args.get('entry_date')
        current_price = request.args.get('current_price', type=float)
        shares = request.args.get('shares', type=float)

        if not entry_price or not entry_date_str:
            return jsonify({
                'ok': False,
                'error': 'Missing required parameters: entry_price, entry_date'
            }), 400

        # Parse entry date
        entry_date = datetime.fromisoformat(entry_date_str.replace('Z', '+00:00'))

        # Run analysis
        monitor = get_position_monitor()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if not current_price:
            # Fetch current price
            current_price = loop.run_until_complete(
                monitor._fetch_current_price(ticker)
            )

        analysis = loop.run_until_complete(
            monitor.monitor_position(
                ticker=ticker,
                entry_price=entry_price,
                entry_date=entry_date,
                current_price=current_price,
                position_size=shares
            )
        )

        # Format response
        return jsonify({
            'ok': True,
            'ticker': ticker,
            'analysis': {
                'current_price': analysis.current_price,
                'entry_price': analysis.entry_price,
                'current_pnl_pct': analysis.current_pnl_pct,
                'holding_days': analysis.holding_days,
                'overall_health': analysis.overall_health_score,
                'degradation_rate': analysis.degradation_rate,
                'should_exit': analysis.should_exit,
                'urgency': analysis.highest_urgency.name,
                'recommended_action': analysis.recommended_action,
                'action_timeframe': analysis.action_timeframe,
                'targets': {
                    'bull': {
                        'price': analysis.bull_target.target,
                        'confidence': analysis.bull_target.confidence,
                        'timeframe_days': analysis.bull_target.timeframe_days,
                        'reasoning': analysis.bull_target.reasoning,
                    },
                    'base': {
                        'price': analysis.base_target.target,
                        'confidence': analysis.base_target.confidence,
                        'timeframe_days': analysis.base_target.timeframe_days,
                        'reasoning': analysis.base_target.reasoning,
                    },
                    'bear': {
                        'price': analysis.bear_target.target,
                        'confidence': analysis.bear_target.confidence,
                        'timeframe_days': analysis.bear_target.timeframe_days,
                        'reasoning': analysis.bear_target.reasoning,
                    },
                    'current': analysis.current_target,
                },
                'risk': {
                    'stop_loss': analysis.stop_loss,
                    'trailing_stop': analysis.trailing_stop,
                    'max_loss_pct': analysis.max_acceptable_loss_pct,
                },
                'exit_signals': [
                    {
                        'urgency': signal.urgency.name,
                        'urgency_level': signal.urgency.value,
                        'reason': signal.reason.value,
                        'primary_reason': signal.primary_reason,
                        'detailed_analysis': signal.detailed_analysis,
                        'confidence': signal.confidence,
                        'recommended_action': signal.recommended_action,
                        'alternative_actions': signal.alternative_actions,
                        'components_degraded': signal.components_degraded,
                        'immediate_exit': signal.immediate_exit,
                    }
                    for signal in analysis.exit_signals
                ],
                'component_health': analysis.component_health,
            },
            'formatted': format_exit_analysis(analysis),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error analyzing exit for {ticker}: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@exit_bp.route('/api/exit/monitor', methods=['POST'])
def monitor_positions():
    """
    Monitor all positions and return exit analyses.

    Body (JSON):
        positions: [
            {
                ticker: str,
                entry_price: float,
                entry_date: str (ISO format),
                shares: float (optional),
                current_price: float (optional)
            },
            ...
        ]

    Returns:
        List of exit analyses sorted by urgency
    """
    try:
        data = request.get_json()
        positions = data.get('positions', [])

        if not positions:
            return jsonify({
                'ok': False,
                'error': 'No positions provided'
            }), 400

        # Parse positions
        parsed_positions = []
        for pos in positions:
            try:
                parsed_positions.append({
                    'ticker': pos['ticker'],
                    'entry_price': float(pos['entry_price']),
                    'entry_date': datetime.fromisoformat(pos['entry_date'].replace('Z', '+00:00')),
                    'shares': float(pos.get('shares', 0)),
                    'current_price': float(pos['current_price']) if 'current_price' in pos else None,
                })
            except Exception as e:
                logger.warning(f"Error parsing position {pos.get('ticker', 'unknown')}: {e}")
                continue

        # Monitor positions
        monitor = get_position_monitor()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        analyses = loop.run_until_complete(
            monitor.monitor_all_positions(parsed_positions)
        )

        # Format response
        return jsonify({
            'ok': True,
            'total_positions': len(analyses),
            'critical_positions': len([a for a in analyses if a.should_exit]),
            'analyses': [
                {
                    'ticker': a.ticker,
                    'current_pnl_pct': a.current_pnl_pct,
                    'overall_health': a.overall_health_score,
                    'should_exit': a.should_exit,
                    'urgency': a.highest_urgency.name,
                    'urgency_level': a.highest_urgency.value,
                    'recommended_action': a.recommended_action,
                    'action_timeframe': a.action_timeframe,
                    'targets': {
                        'current': a.current_target,
                        'stop_loss': a.stop_loss,
                        'trailing_stop': a.trailing_stop,
                    },
                    'exit_signal_count': len(a.exit_signals),
                    'top_signals': [
                        {
                            'reason': s.primary_reason,
                            'urgency': s.urgency.name,
                        }
                        for s in a.exit_signals[:2]
                    ],
                }
                for a in analyses
            ],
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error monitoring positions: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@exit_bp.route('/api/exit/cached/<ticker>', methods=['GET'])
def get_cached_exit(ticker):
    """Get cached exit analysis for ticker."""
    try:
        monitor = get_position_monitor()
        cached = monitor.get_cached_analysis(ticker)

        if not cached:
            return jsonify({
                'ok': False,
                'error': 'No cached analysis found'
            }), 404

        return jsonify({
            'ok': True,
            'ticker': ticker,
            'analysis': cached,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting cached exit for {ticker}: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500
