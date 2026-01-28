#!/usr/bin/env python3
"""
Auto Story Detection & Alerts

Runs periodically via GitHub Actions to detect:
- New emerging themes
- Themes "heating up" (increased mentions)
- Volume spikes on theme stocks
- Breaking catalysts

Sends alerts to Telegram when something notable happens.
"""

import json
from datetime import datetime
from pathlib import Path

from config import config
from utils import get_logger, send_message

logger = get_logger(__name__)

# Storage for previous state
STATE_FILE = Path('story_state.json')


def send_telegram_alert(message):
    """Send alert to Telegram."""
    if not config.telegram.bot_token or not config.telegram.chat_id:
        logger.info(f"[Alert] {message}")
        return False

    try:
        return send_message(config.telegram.chat_id, message)
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return False


def load_previous_state():
    """Load previous story state."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading previous state: {e}")
    return {'themes': {}, 'momentum': {}, 'last_update': None}


def save_state(state):
    """Save current state."""
    state['last_update'] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def detect_story_changes(current, previous):
    """
    Compare current stories to previous and detect changes.

    Returns list of alerts to send.
    """
    alerts = []

    current_themes = {t['name']: t for t in current.get('themes', [])}
    previous_themes = previous.get('themes', {})

    # Detect NEW themes (not seen before)
    for name, theme in current_themes.items():
        if name not in previous_themes:
            if theme['mention_count'] >= 3:  # Only alert if significant
                alerts.append({
                    'type': 'new_theme',
                    'theme': name,
                    'heat': theme.get('heat', 'WARM'),
                    'mentions': theme['mention_count'],
                    'plays': theme.get('primary_plays', [])[:4],
                    'headlines': theme.get('sample_headlines', [])[:2]
                })

    # Detect themes HEATING UP (mentions increased significantly)
    for name, theme in current_themes.items():
        if name in previous_themes:
            prev_mentions = previous_themes[name].get('mentions', 0)
            curr_mentions = theme['mention_count']

            # Alert if mentions doubled or increased by 5+
            if curr_mentions >= prev_mentions * 2 or curr_mentions >= prev_mentions + 5:
                if curr_mentions >= 5:  # Significant volume
                    alerts.append({
                        'type': 'heating_up',
                        'theme': name,
                        'prev_mentions': prev_mentions,
                        'curr_mentions': curr_mentions,
                        'plays': theme.get('primary_plays', [])[:4]
                    })

    # Detect themes going from WARM to HOT
    for name, theme in current_themes.items():
        if name in previous_themes:
            prev_heat = previous_themes[name].get('heat', 'WARM')
            curr_heat = theme.get('heat', 'WARM')

            if prev_heat != 'HOT' and curr_heat == 'HOT':
                alerts.append({
                    'type': 'now_hot',
                    'theme': name,
                    'mentions': theme['mention_count'],
                    'plays': theme.get('primary_plays', [])[:4]
                })

    # Detect momentum stocks with sentiment shift
    current_momentum = {m['ticker']: m for m in current.get('momentum_stocks', [])}
    previous_momentum = previous.get('momentum', {})

    for ticker, data in current_momentum.items():
        if ticker in previous_momentum:
            prev_sent = previous_momentum[ticker].get('sentiment', 'Neutral')
            curr_sent = data.get('sentiment', 'Neutral')

            # Alert on sentiment flip to Bullish with high mentions
            if prev_sent != 'Bullish' and curr_sent == 'Bullish' and data['mentions'] >= 5:
                alerts.append({
                    'type': 'sentiment_flip',
                    'ticker': ticker,
                    'mentions': data['mentions'],
                    'bullish': data.get('bullish', 0),
                    'bearish': data.get('bearish', 0)
                })

    return alerts


def format_alert_message(alerts):
    """Format alerts into Telegram message."""
    if not alerts:
        return None

    msg = "🚨 *STORY ALERT*\n\n"

    for alert in alerts:
        if alert['type'] == 'new_theme':
            emoji = "🔥" if alert['heat'] == 'HOT' else "📈"
            msg += f"{emoji} *NEW: {alert['theme']}*\n"
            msg += f"   {alert['mentions']} mentions\n"
            if alert['plays']:
                msg += f"   Plays: `{'` `'.join(alert['plays'])}`\n"
            if alert['headlines']:
                msg += f"   _{alert['headlines'][0][:50]}..._\n"
            msg += "\n"

        elif alert['type'] == 'heating_up':
            msg += f"🔺 *{alert['theme']}* heating up!\n"
            msg += f"   {alert['prev_mentions']} → {alert['curr_mentions']} mentions\n"
            if alert['plays']:
                msg += f"   Watch: `{'` `'.join(alert['plays'])}`\n"
            msg += "\n"

        elif alert['type'] == 'now_hot':
            msg += f"🔥 *{alert['theme']}* is now HOT!\n"
            msg += f"   {alert['mentions']} mentions\n"
            if alert['plays']:
                msg += f"   Plays: `{'` `'.join(alert['plays'])}`\n"
            msg += "\n"

        elif alert['type'] == 'sentiment_flip':
            msg += f"🟢 *{alert['ticker']}* sentiment turned BULLISH\n"
            msg += f"   {alert['mentions']} mentions ({alert['bullish']}🟢 / {alert['bearish']}🔴)\n"
            msg += "\n"

    msg += f"_Auto-detected at {datetime.now().strftime('%H:%M')}_"

    return msg


def run_story_detection():
    """Main function to run story detection and send alerts."""
    logger.info(f"[{datetime.now()}] Running story detection...")

    # Load previous state
    previous = load_previous_state()

    # Run current detection
    try:
        from fast_stories import run_fast_story_detection
        current = run_fast_story_detection(use_cache=False)  # Fresh data
    except Exception as e:
        logger.error(f"Detection error: {e}")
        return

    # Skip if no data
    if not current or not current.get('themes'):
        logger.info("No themes detected")
        return

    # Detect changes
    alerts = detect_story_changes(current, previous)

    # Send alerts if any
    if alerts:
        message = format_alert_message(alerts)
        if message:
            logger.info(f"Sending {len(alerts)} alerts...")
            send_telegram_alert(message)
    else:
        logger.info("No significant changes detected")

    # Save current state for next comparison
    new_state = {
        'themes': {t['name']: {
            'mentions': t['mention_count'],
            'heat': t.get('heat', 'WARM'),
            'plays': t.get('primary_plays', [])
        } for t in current.get('themes', [])},
        'momentum': {m['ticker']: {
            'mentions': m['mentions'],
            'sentiment': m.get('sentiment', 'Neutral'),
            'bullish': m.get('bullish', 0),
            'bearish': m.get('bearish', 0)
        } for m in current.get('momentum_stocks', [])}
    }
    save_state(new_state)

    logger.info(f"State saved. {len(current.get('themes', []))} themes tracked.")


def check_price_alerts():
    """Check and trigger price alerts for all users."""
    try:
        from storage import get_all_active_alerts, mark_alert_triggered
        import yfinance as yf

        alerts = get_all_active_alerts()
        if not alerts:
            return

        # Group by ticker to minimize API calls
        tickers = list(set(a['ticker'] for a in alerts))

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                current_price = float(stock.history(period='1d')['Close'].iloc[-1])

                for alert in alerts:
                    if alert['ticker'] != ticker:
                        continue

                    triggered = False
                    if alert['direction'] == 'above' and current_price >= alert['price']:
                        triggered = True
                    elif alert['direction'] == 'below' and current_price <= alert['price']:
                        triggered = True

                    if triggered:
                        # Send alert
                        emoji = "📈" if alert['direction'] == 'above' else "📉"
                        msg = f"{emoji} *PRICE ALERT*\n\n"
                        msg += f"`{ticker}` hit ${current_price:.2f}\n"
                        msg += f"Your alert: {alert['direction']} ${alert['price']:.2f}"

                        send_message(alert['chat_id'], msg)

                        # Mark as triggered
                        mark_alert_triggered(alert['chat_id'], ticker, current_price)
                        logger.info(f"Alert triggered: {ticker} {alert['direction']} {alert['price']}")

            except Exception as e:
                logger.error(f"Price check error for {ticker}: {e}")

    except Exception as e:
        logger.error(f"Alert check error: {e}")


def check_earnings_alerts():
    """Alert about earnings happening today/tomorrow."""
    try:
        from earnings import get_upcoming_earnings

        earnings = get_upcoming_earnings(days_ahead=2)

        today_earnings = [e for e in earnings if e['days_until'] == 0]
        tomorrow_earnings = [e for e in earnings if e['days_until'] == 1]

        if not today_earnings and not tomorrow_earnings:
            return

        msg = "📅 *EARNINGS ALERT*\n\n"

        if today_earnings:
            msg += "*TODAY:*\n"
            for e in today_earnings[:5]:
                msg += f"   • `{e['ticker']}`\n"

        if tomorrow_earnings:
            msg += "\n*TOMORROW:*\n"
            for e in tomorrow_earnings[:5]:
                msg += f"   • `{e['ticker']}`\n"

        msg += "\n_Avoid new positions before earnings!_"

        # Send to main chat
        if config.telegram.chat_id:
            send_telegram_alert(msg)

    except Exception as e:
        logger.error(f"Earnings alert error: {e}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'stories':
            run_story_detection()
        elif command == 'prices':
            check_price_alerts()
        elif command == 'earnings':
            check_earnings_alerts()
        elif command == 'all':
            run_story_detection()
            check_price_alerts()
            check_earnings_alerts()
    else:
        # Default: run all checks
        run_story_detection()
        check_price_alerts()
        check_earnings_alerts()
