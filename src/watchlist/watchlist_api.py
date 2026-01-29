"""
Watchlist API Endpoints

REST API for watchlist management in Railway dashboard.
Fully editable with automatic updates.
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any
import logging

from .watchlist_manager import (
    get_watchlist_manager,
    WatchlistPriority,
    SignalQuality
)

logger = logging.getLogger(__name__)

# Create Blueprint
watchlist_bp = Blueprint('watchlist', __name__, url_prefix='/api/watchlist')


@watchlist_bp.route('/', methods=['GET'])
def get_watchlist():
    """
    Get all watchlist items.

    Query params:
    - priority: Filter by priority (high/medium/low)
    - tag: Filter by tag
    - ready: Filter ready to trade (true/false)
    - search: Search query

    Returns:
        {
            "ok": true,
            "items": [...],
            "count": 10,
            "statistics": {...}
        }
    """
    try:
        wm = get_watchlist_manager()

        # Apply filters
        priority = request.args.get('priority')
        tag = request.args.get('tag')
        ready = request.args.get('ready')
        search = request.args.get('search')

        if priority:
            items = wm.get_by_priority(WatchlistPriority(priority))
        elif tag:
            items = wm.get_by_tag(tag)
        elif ready == 'true':
            items = wm.get_ready_to_trade()
        elif search:
            items = wm.search(search)
        else:
            items = wm.get_all_items()

        # Convert to dict
        items_data = [item.to_dict() for item in items]

        # Sort by priority (high -> medium -> low) then by overall score
        priority_order = {'high': 0, 'medium': 1, 'low': 2, 'archive': 3}
        items_data.sort(
            key=lambda x: (
                priority_order.get(x['priority'], 99),
                -(x['overall_score'] or 0)
            )
        )

        return jsonify({
            'ok': True,
            'items': items_data,
            'count': len(items_data),
            'statistics': wm.get_statistics()
        })

    except Exception as e:
        logger.error(f"Get watchlist error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/<ticker>', methods=['GET'])
def get_watchlist_item(ticker: str):
    """
    Get single watchlist item.

    Returns:
        {
            "ok": true,
            "item": {...}
        }
    """
    try:
        wm = get_watchlist_manager()
        item = wm.get_item(ticker)

        if not item:
            return jsonify({'ok': False, 'error': 'Item not found'}), 404

        return jsonify({
            'ok': True,
            'item': item.to_dict()
        })

    except Exception as e:
        logger.error(f"Get watchlist item error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/', methods=['POST'])
def add_watchlist_item():
    """
    Add item to watchlist.

    Request body:
    {
        "ticker": "NVDA",
        "notes": "Strong AI momentum",
        "thesis": "AI infrastructure leader",
        "catalyst": "Earnings in 2 weeks",
        "priority": "high",
        "tags": ["AI", "momentum"],
        "target_entry": 850.00,
        "stop_loss": 800.00,
        "position_size": "normal"
    }

    Returns:
        {
            "ok": true,
            "item": {...},
            "message": "Item added successfully"
        }
    """
    try:
        data = request.get_json()

        if not data or 'ticker' not in data:
            return jsonify({'ok': False, 'error': 'Ticker required'}), 400

        ticker = data['ticker']
        wm = get_watchlist_manager()

        # Create/update item
        item = wm.add_item(
            ticker=ticker,
            notes=data.get('notes', ''),
            thesis=data.get('thesis', ''),
            catalyst=data.get('catalyst', ''),
            priority=WatchlistPriority(data.get('priority', 'medium')),
            tags=data.get('tags', []),
            added_from='manual'
        )

        # Update additional fields if provided
        if 'target_entry' in data:
            item.target_entry = data['target_entry']
        if 'stop_loss' in data:
            item.stop_loss = data['stop_loss']
        if 'position_size' in data:
            item.position_size = data['position_size']

        wm._save_watchlist()

        return jsonify({
            'ok': True,
            'item': item.to_dict(),
            'message': f'{ticker} added to watchlist'
        })

    except Exception as e:
        logger.error(f"Add watchlist item error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/scan', methods=['POST'])
def add_from_scan():
    """
    Add items from scan results with automatic data population.

    Request body:
    {
        "results": [
            {
                "ticker": "NVDA",
                "price": 875.50,
                "rs": 96,
                "theme": "AI Infrastructure",
                "story_score": 9,
                ...
            },
            ...
        ]
    }

    Returns:
        {
            "ok": true,
            "added": 5,
            "updated": 3,
            "items": [...]
        }
    """
    try:
        data = request.get_json()

        if not data or 'results' not in data:
            return jsonify({'ok': False, 'error': 'Scan results required'}), 400

        wm = get_watchlist_manager()
        results = data['results']

        added = 0
        updated = 0
        items = []

        for result in results:
            ticker = result.get('ticker') or result.get('symbol')
            if not ticker:
                continue

            # Check if already in watchlist
            was_new = ticker.upper() not in wm.items

            # Add/update from scan
            item = wm.add_from_scan(ticker, result)
            items.append(item.to_dict())

            if was_new:
                added += 1
            else:
                updated += 1

        return jsonify({
            'ok': True,
            'added': added,
            'updated': updated,
            'count': len(items),
            'items': items
        })

    except Exception as e:
        logger.error(f"Add from scan error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/<ticker>', methods=['PUT', 'PATCH'])
def update_watchlist_item(ticker: str):
    """
    Update watchlist item (fully editable).

    Request body: Any field can be updated
    {
        "notes": "Updated notes",
        "priority": "high",
        "target_entry": 900.00,
        ...
    }

    Returns:
        {
            "ok": true,
            "item": {...},
            "message": "Item updated"
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'error': 'No data provided'}), 400

        wm = get_watchlist_manager()
        item = wm.update_item(ticker, **data)

        if not item:
            return jsonify({'ok': False, 'error': 'Item not found'}), 404

        return jsonify({
            'ok': True,
            'item': item.to_dict(),
            'message': f'{ticker} updated'
        })

    except Exception as e:
        logger.error(f"Update watchlist item error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/<ticker>', methods=['DELETE'])
def delete_watchlist_item(ticker: str):
    """
    Remove item from watchlist.

    Returns:
        {
            "ok": true,
            "message": "Item removed"
        }
    """
    try:
        wm = get_watchlist_manager()
        success = wm.remove_item(ticker)

        if not success:
            return jsonify({'ok': False, 'error': 'Item not found'}), 404

        return jsonify({
            'ok': True,
            'message': f'{ticker} removed from watchlist'
        })

    except Exception as e:
        logger.error(f"Delete watchlist item error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/update/prices', methods=['POST'])
def update_prices():
    """
    Update price data for all watchlist items.
    Uses real-time data from yfinance.

    Returns:
        {
            "ok": true,
            "updated": 10,
            "message": "Prices updated"
        }
    """
    try:
        wm = get_watchlist_manager()
        count = len(wm.items)

        wm.auto_update_all(include_sentiment=False, include_ai=False)

        return jsonify({
            'ok': True,
            'updated': count,
            'message': f'Prices updated for {count} items'
        })

    except Exception as e:
        logger.error(f"Update prices error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/update/sentiment/<ticker>', methods=['POST'])
def update_sentiment(ticker: str):
    """
    Update X Intelligence sentiment for a specific ticker.
    Uses Component #37 (X Intelligence Monitor).

    Returns:
        {
            "ok": true,
            "item": {...},
            "message": "Sentiment updated"
        }
    """
    try:
        wm = get_watchlist_manager()

        if ticker.upper() not in wm.items:
            return jsonify({'ok': False, 'error': 'Item not in watchlist'}), 404

        wm.update_x_sentiment(ticker)
        item = wm.get_item(ticker)

        return jsonify({
            'ok': True,
            'item': item.to_dict(),
            'message': f'X sentiment updated for {ticker}',
            'sentiment': {
                'sentiment': item.x_sentiment,
                'score': item.x_sentiment_score,
                'red_flags': item.x_red_flags,
                'catalysts': item.x_catalysts
            }
        })

    except Exception as e:
        logger.error(f"Update sentiment error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/update/ai/<ticker>', methods=['POST'])
def update_ai_analysis(ticker: str):
    """
    Update AI analysis for a specific ticker.
    Uses Evolutionary Brain (all 37 components).

    Returns:
        {
            "ok": true,
            "item": {...},
            "message": "AI analysis updated"
        }
    """
    try:
        wm = get_watchlist_manager()

        if ticker.upper() not in wm.items:
            return jsonify({'ok': False, 'error': 'Item not in watchlist'}), 404

        wm.update_ai_analysis(ticker)
        item = wm.get_item(ticker)

        return jsonify({
            'ok': True,
            'item': item.to_dict(),
            'message': f'AI analysis updated for {ticker}',
            'ai_analysis': {
                'confidence': item.ai_confidence,
                'decision': item.ai_decision,
                'reasoning': item.ai_reasoning
            }
        })

    except Exception as e:
        logger.error(f"Update AI analysis error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/update/all', methods=['POST'])
def update_all():
    """
    Full update of all watchlist items.
    Includes prices, sentiment, and AI analysis.

    Query params:
    - sentiment: Include X sentiment (true/false), default false
    - ai: Include AI analysis (true/false), default false

    Returns:
        {
            "ok": true,
            "updated": 10,
            "message": "Full update complete"
        }
    """
    try:
        include_sentiment = request.args.get('sentiment') == 'true'
        include_ai = request.args.get('ai') == 'true'

        wm = get_watchlist_manager()
        count = len(wm.items)

        wm.auto_update_all(
            include_sentiment=include_sentiment,
            include_ai=include_ai
        )

        components_updated = ['prices']
        if include_sentiment:
            components_updated.append('X sentiment')
        if include_ai:
            components_updated.append('AI analysis')

        return jsonify({
            'ok': True,
            'updated': count,
            'components': components_updated,
            'message': f'Full update complete for {count} items'
        })

    except Exception as e:
        logger.error(f"Update all error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """
    Get watchlist statistics.

    Returns:
        {
            "ok": true,
            "statistics": {...}
        }
    """
    try:
        wm = get_watchlist_manager()
        stats = wm.get_statistics()

        return jsonify({
            'ok': True,
            'statistics': stats
        })

    except Exception as e:
        logger.error(f"Get statistics error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/export', methods=['GET'])
def export_watchlist():
    """
    Export watchlist as JSON.

    Returns:
        {
            "ok": true,
            "data": {...}
        }
    """
    try:
        wm = get_watchlist_manager()
        data = {ticker: item.to_dict() for ticker, item in wm.items.items()}

        return jsonify({
            'ok': True,
            'data': data,
            'count': len(data)
        })

    except Exception as e:
        logger.error(f"Export watchlist error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/import', methods=['POST'])
def import_watchlist():
    """
    Import watchlist from JSON.

    Request body:
    {
        "data": {
            "NVDA": {...},
            "TSLA": {...}
        }
    }

    Returns:
        {
            "ok": true,
            "imported": 5
        }
    """
    try:
        data = request.get_json()

        if not data or 'data' not in data:
            return jsonify({'ok': False, 'error': 'Data required'}), 400

        wm = get_watchlist_manager()

        count = 0
        for ticker, item_data in data['data'].items():
            from .watchlist_manager import WatchlistItem
            wm.items[ticker.upper()] = WatchlistItem.from_dict(item_data)
            count += 1

        wm._save_watchlist()

        return jsonify({
            'ok': True,
            'imported': count,
            'message': f'Imported {count} items'
        })

    except Exception as e:
        logger.error(f"Import watchlist error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/clear', methods=['POST'])
def clear_watchlist():
    """
    Clear entire watchlist.
    Requires confirmation.

    Request body:
    {
        "confirm": true
    }

    Returns:
        {
            "ok": true,
            "message": "Watchlist cleared"
        }
    """
    try:
        data = request.get_json()

        if not data or not data.get('confirm'):
            return jsonify({'ok': False, 'error': 'Confirmation required'}), 400

        wm = get_watchlist_manager()
        count = len(wm.items)
        wm.clear_all()

        return jsonify({
            'ok': True,
            'cleared': count,
            'message': f'Watchlist cleared ({count} items removed)'
        })

    except Exception as e:
        logger.error(f"Clear watchlist error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@watchlist_bp.route('/update-learned-weights', methods=['POST'])
def update_learned_weights():
    """
    Update all watchlist scores using learned weights from learning system.

    Integrates with the 4-tier learning system to use weights that have been
    learned from actual trade outcomes, rather than hardcoded defaults.

    Returns:
        {
            "ok": true,
            "updated_count": 5,
            "learned_weights": {
                "theme": 0.35,
                "technical": 0.25,
                "ai": 0.23,
                "sentiment": 0.17
            },
            "message": "Updated 5 items with learned weights"
        }
    """
    try:
        wm = get_watchlist_manager()

        # Try to get learned weights
        try:
            from src.learning import get_learning_brain
            brain = get_learning_brain()
            learned_weights = brain.current_weights

            weights_dict = {
                'theme': learned_weights.theme,
                'technical': learned_weights.technical,
                'ai': learned_weights.ai,
                'sentiment': learned_weights.sentiment
            }

        except ImportError:
            return jsonify({
                'ok': False,
                'error': 'Learning system not available'
            }), 503

        # Update scores
        updated_count = wm.update_scores_with_learned_weights()

        return jsonify({
            'ok': True,
            'updated_count': updated_count,
            'learned_weights': weights_dict,
            'message': f'Updated {updated_count} items with learned weights'
        })

    except Exception as e:
        logger.error(f"Update learned weights error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500
