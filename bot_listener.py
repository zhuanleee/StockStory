#!/usr/bin/env python3
"""
Telegram Bot Listener - Standalone script for GitHub Actions.
Processes incoming Telegram commands using cached scan results.
"""

import os
import json
import logging
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import glob

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Telegram config
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
OFFSET_FILE = Path('telegram_offset.json')


def get_telegram_api_url():
    """Get Telegram API base URL."""
    return f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_telegram_message(text: str) -> bool:
    """Send a message via Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("Telegram not configured")
        return False

    url = f"{get_telegram_api_url()}/sendMessage"
    try:
        response = requests.post(url, json={
            'chat_id': CHAT_ID,
            'text': text,
            'parse_mode': 'Markdown'
        }, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False


def get_telegram_updates(offset=None):
    """Get updates from Telegram bot."""
    if not BOT_TOKEN:
        return []

    url = f"{get_telegram_api_url()}/getUpdates"
    params = {'timeout': 1}
    if offset:
        params['offset'] = offset

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            return response.json().get('result', [])
    except Exception as e:
        logger.debug(f"Failed to get Telegram updates: {e}")
    return []


def load_latest_scan_results():
    """Load the most recent scan CSV file."""
    # Look for scan files
    scan_files = glob.glob('scan_*.csv')
    if not scan_files:
        logger.warning("No scan results found")
        return pd.DataFrame()

    # Get the most recent one
    latest = max(scan_files, key=os.path.getmtime)
    logger.info(f"Loading scan results from {latest}")

    try:
        df = pd.read_csv(latest)
        return df
    except Exception as e:
        logger.error(f"Failed to load scan results: {e}")
        return pd.DataFrame()


def process_ticker_query(ticker: str, df_results: pd.DataFrame) -> str:
    """Process a ticker query and return analysis."""
    ticker = ticker.upper().strip()

    ticker_row = df_results[df_results['ticker'] == ticker]
    if len(ticker_row) == 0:
        return f"Ticker `{ticker}` not found in scan results."

    row = ticker_row.iloc[0]

    # Basic info
    msg = f"*{ticker} ANALYSIS*\n\n"

    score = row.get('composite_score', row.get('story_score', 0))
    msg += f"*Score:* {score:.0f}/100\n"

    if 'rs_composite' in row:
        msg += f"*RS vs SPY:* {row['rs_composite']:+.2f}%\n"

    if 'price' in row:
        msg += f"*Price:* ${row['price']:.2f}\n\n"

    # Trend
    msg += "*Trend:*\n"
    if 'above_20' in row:
        msg += f"  Above 20 SMA: {'Yes' if row['above_20'] else 'No'}\n"
    if 'above_50' in row:
        msg += f"  Above 50 SMA: {'Yes' if row['above_50'] else 'No'}\n"
    if 'above_200' in row:
        msg += f"  Above 200 SMA: {'Yes' if row['above_200'] else 'No'}\n"

    # Squeeze/Breakout
    if row.get('in_squeeze'):
        msg += "\n*IN SQUEEZE* - Volatility contracting\n"
    if row.get('breakout_up'):
        msg += "*BREAKOUT* - Price above upper BB\n"

    # Volume
    if 'vol_ratio' in row:
        msg += f"\n*Volume:* {row['vol_ratio']:.1f}x average\n"

    # Theme
    if 'hottest_theme' in row and pd.notna(row['hottest_theme']):
        msg += f"*Theme:* {row['hottest_theme']}\n"

    return msg


def handle_commands():
    """Main function to check and handle Telegram commands."""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return

    # Load scan results
    df_results = load_latest_scan_results()
    if df_results.empty:
        logger.warning("No scan results available")

    # Load last processed update ID
    last_offset = 0
    if OFFSET_FILE.exists():
        try:
            with open(OFFSET_FILE, 'r') as f:
                last_offset = json.load(f).get('offset', 0)
        except Exception:
            pass

    logger.info(f"Checking for updates (offset: {last_offset})")
    updates = get_telegram_updates(offset=last_offset + 1)
    logger.info(f"Found {len(updates)} updates")

    for update in updates:
        update_id = update.get('update_id', 0)
        message = update.get('message', {})
        text = message.get('text', '').strip()

        if text:
            logger.info(f"Processing command: {text}")

            # Check if it's a ticker query (1-5 uppercase letters)
            if len(text) <= 5 and text.isalpha() and not df_results.empty:
                response = process_ticker_query(text, df_results)
                send_telegram_message(response)

            elif text.lower() == '/top' and not df_results.empty:
                # Show top 10
                msg = "*TOP 10 STOCKS*\n\n"
                score_col = 'composite_score' if 'composite_score' in df_results.columns else 'story_score'
                for _, row in df_results.head(10).iterrows():
                    score = row.get(score_col, 0)
                    rs = row.get('rs_composite', 0)
                    msg += f"`{row['ticker']:5}` | Score: {score:.0f}"
                    if rs:
                        msg += f" | RS: {rs:+.1f}%"
                    msg += "\n"
                send_telegram_message(msg)

            elif text.lower() == '/help':
                msg = "*BOT COMMANDS*\n\n"
                msg += "Send any ticker (e.g., `NVDA`) for analysis\n"
                msg += "`/top` - Show top 10 stocks\n"
                msg += "`/help` - Show this help\n"
                send_telegram_message(msg)

            elif text.lower() == '/status':
                if df_results.empty:
                    msg = "No scan results available."
                else:
                    msg = f"*Status:* {len(df_results)} stocks in database\n"
                    msg += f"Last updated: Check scan file date"
                send_telegram_message(msg)

        # Update offset
        with open(OFFSET_FILE, 'w') as f:
            json.dump({'offset': update_id}, f)

    logger.info("Done processing commands")


if __name__ == '__main__':
    handle_commands()
