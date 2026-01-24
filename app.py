#!/usr/bin/env python3
"""
Minimal Instant Telegram Bot - Guaranteed to work on Render
"""

import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(chat_id, text):
    """Send message to Telegram."""
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'},
            timeout=10
        )
    except:
        pass


def analyze_ticker(ticker):
    """Quick ticker analysis."""
    try:
        import yfinance as yf
        import pandas as pd

        df = yf.download(ticker, period='1mo', progress=False)
        if len(df) < 5:
            return f"❌ No data for {ticker}"

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        current = float(close.iloc[-1])
        change = (current / float(close.iloc[-5]) - 1) * 100

        emoji = "📈" if change > 0 else "📉"

        msg = f"{emoji} *{ticker}*\n\n"
        msg += f"Price: ${current:.2f}\n"
        msg += f"5-day: {change:+.1f}%"

        return msg
    except Exception as e:
        return f"Error: {str(e)}"


@app.route('/')
def home():
    return jsonify({'status': 'running', 'time': datetime.now().isoformat()})


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()

        if data and 'message' in data:
            chat_id = data['message'].get('chat', {}).get('id')
            text = data['message'].get('text', '').strip()

            if not chat_id or not text:
                return jsonify({'ok': True})

            # Commands
            if text.lower() in ['/start', '/help']:
                msg = "🤖 *INSTANT BOT*\n\n"
                msg += "• Send ticker (NVDA) → Quick analysis\n"
                msg += "• /stories → Hot themes & momentum\n"
                msg += "• /top → Top stocks\n"
                msg += "• /help → This message\n\n"
                msg += "_Instant responses!_"
                send_message(chat_id, msg)

            elif text.lower() == '/top':
                msg = "🏆 *TOP STOCKS*\n\n"
                msg += "Run /scan in GitHub Actions first to generate data."
                send_message(chat_id, msg)

            elif text.lower() == '/stories':
                send_message(chat_id, "⏳ Detecting stories...")
                try:
                    from fast_stories import run_fast_story_detection, format_fast_stories_report
                    result = run_fast_story_detection(use_cache=True)
                    msg = format_fast_stories_report(result)
                    send_message(chat_id, msg)
                except Exception as e:
                    send_message(chat_id, f"Stories error: {str(e)}")

            elif len(text) <= 5 and text.isalpha():
                # Ticker query
                send_message(chat_id, f"⏳ Analyzing {text.upper()}...")
                result = analyze_ticker(text.upper())
                send_message(chat_id, result)

            else:
                send_message(chat_id, "Send a ticker like `NVDA` or `/help`")

        return jsonify({'ok': True})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'ok': False})


@app.route('/set_webhook')
def set_webhook():
    url = request.args.get('url')
    if url:
        r = requests.post(f"{TELEGRAM_API}/setWebhook", json={'url': f"{url}/webhook"})
        return jsonify(r.json())
    return jsonify({'error': 'Need ?url=https://your-app.onrender.com'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
