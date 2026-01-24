#!/usr/bin/env python3
"""
Persistent Storage Module

Handles watchlists, alerts, portfolios with file-based storage.
Can be swapped to Redis/database later.
"""

import os
import json
from datetime import datetime
from pathlib import Path

# Storage directory
STORAGE_DIR = Path('user_data')
STORAGE_DIR.mkdir(exist_ok=True)

def _get_user_file(chat_id, data_type):
    """Get user-specific data file path."""
    user_dir = STORAGE_DIR / str(chat_id)
    user_dir.mkdir(exist_ok=True)
    return user_dir / f'{data_type}.json'

def _load_data(chat_id, data_type, default=None):
    """Load user data."""
    filepath = _get_user_file(chat_id, data_type)
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            pass
    return default if default is not None else {}

def _save_data(chat_id, data_type, data):
    """Save user data."""
    filepath = _get_user_file(chat_id, data_type)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


# =============================================================================
# WATCHLIST
# =============================================================================

def get_watchlist(chat_id):
    """Get user's watchlist."""
    data = _load_data(chat_id, 'watchlist', {'tickers': []})
    return data.get('tickers', [])

def add_to_watchlist(chat_id, ticker):
    """Add ticker to watchlist."""
    data = _load_data(chat_id, 'watchlist', {'tickers': []})
    tickers = data.get('tickers', [])

    ticker = ticker.upper()
    if ticker not in tickers:
        tickers.append(ticker)
        data['tickers'] = tickers[:20]  # Max 20 tickers
        data['updated'] = datetime.now().isoformat()
        _save_data(chat_id, 'watchlist', data)
        return True
    return False

def remove_from_watchlist(chat_id, ticker):
    """Remove ticker from watchlist."""
    data = _load_data(chat_id, 'watchlist', {'tickers': []})
    tickers = data.get('tickers', [])

    ticker = ticker.upper()
    if ticker in tickers:
        tickers.remove(ticker)
        data['tickers'] = tickers
        data['updated'] = datetime.now().isoformat()
        _save_data(chat_id, 'watchlist', data)
        return True
    return False

def clear_watchlist(chat_id):
    """Clear entire watchlist."""
    _save_data(chat_id, 'watchlist', {'tickers': [], 'updated': datetime.now().isoformat()})


# =============================================================================
# PRICE ALERTS
# =============================================================================

def get_alerts(chat_id):
    """Get user's price alerts."""
    data = _load_data(chat_id, 'alerts', {'alerts': []})
    return data.get('alerts', [])

def add_alert(chat_id, ticker, price, direction='above'):
    """Add price alert."""
    data = _load_data(chat_id, 'alerts', {'alerts': []})
    alerts = data.get('alerts', [])

    alert = {
        'ticker': ticker.upper(),
        'price': float(price),
        'direction': direction,  # 'above' or 'below'
        'created': datetime.now().isoformat(),
        'triggered': False
    }

    alerts.append(alert)
    data['alerts'] = alerts[:50]  # Max 50 alerts
    _save_data(chat_id, 'alerts', data)
    return alert

def remove_alert(chat_id, ticker):
    """Remove alerts for a ticker."""
    data = _load_data(chat_id, 'alerts', {'alerts': []})
    alerts = data.get('alerts', [])

    ticker = ticker.upper()
    alerts = [a for a in alerts if a['ticker'] != ticker]
    data['alerts'] = alerts
    _save_data(chat_id, 'alerts', data)

def mark_alert_triggered(chat_id, ticker, price):
    """Mark alert as triggered."""
    data = _load_data(chat_id, 'alerts', {'alerts': []})
    alerts = data.get('alerts', [])

    ticker = ticker.upper()
    for alert in alerts:
        if alert['ticker'] == ticker and not alert['triggered']:
            alert['triggered'] = True
            alert['triggered_at'] = datetime.now().isoformat()
            alert['triggered_price'] = price

    data['alerts'] = alerts
    _save_data(chat_id, 'alerts', data)

def get_all_active_alerts():
    """Get all active alerts across all users (for background checking)."""
    all_alerts = []

    if STORAGE_DIR.exists():
        for user_dir in STORAGE_DIR.iterdir():
            if user_dir.is_dir():
                alerts_file = user_dir / 'alerts.json'
                if alerts_file.exists():
                    try:
                        with open(alerts_file, 'r') as f:
                            data = json.load(f)
                            for alert in data.get('alerts', []):
                                if not alert.get('triggered'):
                                    alert['chat_id'] = int(user_dir.name)
                                    all_alerts.append(alert)
                    except:
                        pass

    return all_alerts


# =============================================================================
# PORTFOLIO
# =============================================================================

def get_portfolio(chat_id):
    """Get user's portfolio."""
    data = _load_data(chat_id, 'portfolio', {'positions': []})
    return data.get('positions', [])

def add_position(chat_id, ticker, shares, entry_price, entry_date=None):
    """Add position to portfolio."""
    data = _load_data(chat_id, 'portfolio', {'positions': []})
    positions = data.get('positions', [])

    position = {
        'ticker': ticker.upper(),
        'shares': float(shares),
        'entry_price': float(entry_price),
        'entry_date': entry_date or datetime.now().strftime('%Y-%m-%d'),
        'added': datetime.now().isoformat()
    }

    # Check if position exists, update if so
    for i, p in enumerate(positions):
        if p['ticker'] == ticker.upper():
            # Average in
            total_shares = p['shares'] + shares
            avg_price = (p['shares'] * p['entry_price'] + shares * entry_price) / total_shares
            positions[i]['shares'] = total_shares
            positions[i]['entry_price'] = avg_price
            data['positions'] = positions
            _save_data(chat_id, 'portfolio', data)
            return positions[i]

    positions.append(position)
    data['positions'] = positions
    _save_data(chat_id, 'portfolio', data)
    return position

def remove_position(chat_id, ticker):
    """Remove position from portfolio."""
    data = _load_data(chat_id, 'portfolio', {'positions': []})
    positions = data.get('positions', [])

    ticker = ticker.upper()
    positions = [p for p in positions if p['ticker'] != ticker]
    data['positions'] = positions
    _save_data(chat_id, 'portfolio', data)

def close_position(chat_id, ticker, exit_price):
    """Close position and record the trade."""
    data = _load_data(chat_id, 'portfolio', {'positions': [], 'closed_trades': []})
    positions = data.get('positions', [])
    closed = data.get('closed_trades', [])

    ticker = ticker.upper()
    for p in positions:
        if p['ticker'] == ticker:
            # Record closed trade
            pnl = (exit_price - p['entry_price']) / p['entry_price'] * 100
            closed_trade = {
                **p,
                'exit_price': float(exit_price),
                'exit_date': datetime.now().strftime('%Y-%m-%d'),
                'pnl_percent': pnl,
                'pnl_dollars': (exit_price - p['entry_price']) * p['shares']
            }
            closed.append(closed_trade)
            positions = [pos for pos in positions if pos['ticker'] != ticker]

            data['positions'] = positions
            data['closed_trades'] = closed[-100:]  # Keep last 100
            _save_data(chat_id, 'portfolio', data)
            return closed_trade

    return None

def get_closed_trades(chat_id):
    """Get closed trades history."""
    data = _load_data(chat_id, 'portfolio', {'closed_trades': []})
    return data.get('closed_trades', [])


# =============================================================================
# GLOBAL STORAGE (for alerts checking, etc.)
# =============================================================================

def get_all_users_with_alerts():
    """Get all chat IDs that have active alerts."""
    users = []
    if STORAGE_DIR.exists():
        for user_dir in STORAGE_DIR.iterdir():
            if user_dir.is_dir():
                alerts_file = user_dir / 'alerts.json'
                if alerts_file.exists():
                    users.append(int(user_dir.name))
    return users
