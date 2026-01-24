#!/usr/bin/env python3
"""
Lightweight bot listener - checks for Telegram commands and responds.
Runs every 15 minutes via GitHub Actions.
"""

import os
import io
import json
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')


def send_telegram_message(message, parse_mode='Markdown'):
    """Send message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(message)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def send_telegram_photo(photo_buffer, caption=''):
    """Send a photo via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    try:
        files = {'photo': ('chart.png', photo_buffer, 'image/png')}
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'caption': caption,
            'parse_mode': 'Markdown',
        }
        response = requests.post(url, files=files, data=data, timeout=30)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram photo error: {e}")
        return False


def get_telegram_updates(offset=None):
    """Get updates from Telegram bot."""
    if not TELEGRAM_BOT_TOKEN:
        return []

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {'timeout': 1}
    if offset:
        params['offset'] = offset

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json().get('result', [])
    except:
        pass
    return []


def generate_chart(ticker):
    """Generate a candlestick chart image for a ticker."""
    try:
        df = yf.download(ticker, period='3mo', progress=False)

        if len(df) < 20:
            return None

        # Flatten columns if MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Ensure proper column names for mplfinance
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

        # Slice to last 60 days first
        df = df.iloc[-60:].copy()

        # Calculate moving averages on sliced data
        sma_20 = df['Close'].rolling(20).mean()
        sma_50 = df['Close'].rolling(50).mean()

        # Bollinger Bands
        bb_mid = df['Close'].rolling(20).mean()
        bb_std = df['Close'].rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std

        # Create additional plots
        add_plots = [
            mpf.make_addplot(sma_20, color='orange', width=1, label='20 SMA'),
            mpf.make_addplot(sma_50, color='purple', width=1, label='50 SMA'),
            mpf.make_addplot(bb_upper, color='blue', width=0.7, linestyle='--', alpha=0.5),
            mpf.make_addplot(bb_lower, color='blue', width=0.7, linestyle='--', alpha=0.5),
        ]

        # Custom style
        mc = mpf.make_marketcolors(
            up='#00b894',      # Green for up
            down='#d63031',    # Red for down
            edge='inherit',
            wick='inherit',
            volume='inherit',
        )

        style = mpf.make_mpf_style(
            base_mpf_style='nightclouds',
            marketcolors=mc,
            gridstyle='-',
            gridcolor='#2d3436',
            facecolor='#0d1117',
        )

        # Generate chart
        buf = io.BytesIO()

        fig, axes = mpf.plot(
            df,  # Already sliced to last 60 days
            type='candle',
            style=style,
            volume=True,
            addplot=add_plots,
            title=f'\n{ticker} - Daily Candlestick',
            ylabel='Price ($)',
            ylabel_lower='Volume',
            figsize=(12, 8),
            returnfig=True,
        )

        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                    facecolor='#0d1117', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        return buf
    except Exception as e:
        print(f"Chart error for {ticker}: {e}")
        return None


def analyze_ticker(ticker):
    """Quick analysis of a single ticker."""
    try:
        ticker = ticker.upper().strip()

        # Fetch data
        df = yf.download(ticker, period='1y', progress=False)
        spy = yf.download('SPY', period='1y', progress=False)

        if len(df) < 50:
            return f"❌ Not enough data for `{ticker}`"

        # Flatten columns if MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)

        close = df['Close']
        current_price = float(close.iloc[-1])

        # MAs
        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1])
        sma_200 = float(close.rolling(200).mean().iloc[-1]) if len(df) >= 200 else None

        above_20 = current_price > sma_20
        above_50 = current_price > sma_50
        above_200 = current_price > sma_200 if sma_200 else None

        # RS
        stock_ret = (float(close.iloc[-1]) / float(close.iloc[-20]) - 1) * 100
        spy_ret = (float(spy['Close'].iloc[-1]) / float(spy['Close'].iloc[-20]) - 1) * 100
        rs = stock_ret - spy_ret

        # Bollinger squeeze
        bb_std = close.rolling(20).std()
        bb_mean = close.rolling(20).mean()
        bb_width = float((bb_std / bb_mean).iloc[-1])
        width_series = bb_std.iloc[-100:] / bb_mean.iloc[-100:]
        width_pct = float((width_series <= bb_width).mean() * 100)
        in_squeeze = width_pct <= 20

        upper_bb = sma_20 + 2 * float(bb_std.iloc[-1])
        breakout = current_price > upper_bb

        # Volume
        vol_ratio = float(df['Volume'].iloc[-1]) / float(df['Volume'].iloc[-20:].mean())

        # ATR
        high = df['High']
        low = df['Low']
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])

        # Build message
        msg = f"📊 *{ticker} ANALYSIS*\n\n"
        msg += f"*Price:* ${current_price:.2f}\n"
        msg += f"*RS vs SPY (20d):* {rs:+.2f}%\n\n"

        msg += "*Trend:*\n"
        msg += f"• Above 20 SMA: {'✅' if above_20 else '❌'}\n"
        msg += f"• Above 50 SMA: {'✅' if above_50 else '❌'}\n"
        if above_200 is not None:
            msg += f"• Above 200 SMA: {'✅' if above_200 else '❌'}\n"

        if in_squeeze:
            msg += "\n⏳ *IN SQUEEZE* - Volatility contracting\n"
        if breakout:
            msg += "🚀 *BREAKOUT* - Above upper Bollinger\n"

        msg += f"\n*Volume:* {vol_ratio:.1f}x average"
        if vol_ratio > 2:
            msg += " 🔥"

        msg += f"\n\n*Entry Ideas:*\n"
        msg += f"• Current: ${current_price:.2f}\n"
        msg += f"• Stop (2 ATR): ${current_price - 2*atr:.2f}\n"
        msg += f"• Target (3 ATR): ${current_price + 3*atr:.2f}\n"

        return msg

    except Exception as e:
        return f"❌ Error analyzing `{ticker}`: {str(e)}"


def load_latest_scan():
    """Load latest scan results if available."""
    import glob
    scan_files = glob.glob('scan_*.csv')
    if scan_files:
        latest = max(scan_files)
        return pd.read_csv(latest)
    return None


def main():
    """Check for Telegram commands and respond."""
    print(f"Bot listener started: {datetime.now()}")

    # Load offset
    offset_file = Path('telegram_offset.json')
    last_offset = 0
    if offset_file.exists():
        with open(offset_file, 'r') as f:
            last_offset = json.load(f).get('offset', 0)

    updates = get_telegram_updates(offset=last_offset + 1)
    print(f"Found {len(updates)} new messages")

    df_results = load_latest_scan()

    for update in updates:
        update_id = update.get('update_id', 0)
        message = update.get('message', {})
        text = message.get('text', '').strip()
        chat_id = message.get('chat', {}).get('id')

        print(f"Processing: {text}")

        if text:
            # Ticker query (1-5 letters)
            if len(text) <= 5 and text.replace('.', '').isalpha():
                ticker = text.upper()
                send_telegram_message(f"⏳ Analyzing {ticker}...")

                response = analyze_ticker(ticker)
                send_telegram_message(response)

                # Send chart
                chart = generate_chart(ticker)
                if chart:
                    send_telegram_photo(chart, caption=f"{ticker} Chart")

            elif text.lower() == '/top':
                if df_results is not None:
                    msg = "🏆 *TOP 10 STOCKS*\n\n"
                    for _, row in df_results.head(10).iterrows():
                        msg += f"`{row['ticker']:5}` | Score: {row['composite_score']:.0f} | RS: {row['rs_composite']:+.1f}%\n"
                    send_telegram_message(msg)
                else:
                    send_telegram_message("No scan data available. Wait for next scheduled scan.")

            elif text.lower() == '/mtf':
                # Multi-timeframe for top stocks
                try:
                    from multi_timeframe import scan_mtf_confluence, format_mtf_scan_results
                    send_telegram_message("⏳ Running MTF analysis...")
                    tickers = ['NVDA', 'AMD', 'AAPL', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMZN', 'AVGO', 'CRM']
                    results = scan_mtf_confluence(tickers, min_score=4)
                    msg = format_mtf_scan_results(results)
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"MTF error: {str(e)}")

            elif text.lower() == '/sectors':
                # Sector rotation
                try:
                    from sector_rotation import run_sector_rotation_analysis, format_sector_rotation_report
                    send_telegram_message("⏳ Analyzing sectors...")
                    results = run_sector_rotation_analysis()
                    msg = format_sector_rotation_report(results['ranked'], results['rotations'], results['cycle'])
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Sector error: {str(e)}")

            elif text.lower() == '/news':
                # News + social sentiment for top stocks
                try:
                    from news_analyzer import scan_news_sentiment, format_news_scan_results
                    send_telegram_message("⏳ Analyzing news + social sentiment...")
                    tickers = ['NVDA', 'AMD', 'AAPL', 'TSLA', 'META']
                    results = scan_news_sentiment(tickers)
                    msg = format_news_scan_results(results)
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"News error: {str(e)}")

            elif text.lower() == '/tam':
                # TAM rankings
                try:
                    from tam_estimator import rank_themes_by_opportunity, format_theme_rankings
                    send_telegram_message("⏳ Calculating TAM rankings...")
                    rankings = rank_themes_by_opportunity()
                    msg = format_theme_rankings(rankings)
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"TAM error: {str(e)}")

            elif text.lower().startswith('/tam '):
                # TAM for specific theme
                theme = text[5:].strip().upper().replace(' ', '_')
                try:
                    from tam_estimator import analyze_theme_tam, format_tam_analysis, TAM_DATABASE
                    if theme in TAM_DATABASE:
                        send_telegram_message(f"⏳ Analyzing {theme}...")
                        analysis = analyze_theme_tam(theme)
                        if analysis:
                            msg = format_tam_analysis(analysis)
                            send_telegram_message(msg)
                    else:
                        themes = ', '.join(list(TAM_DATABASE.keys())[:10])
                        send_telegram_message(f"Theme not found. Available: {themes}...")
                except Exception as e:
                    send_telegram_message(f"TAM error: {str(e)}")

            elif text.lower() == '/stories':
                # Story/Theme detection
                try:
                    from story_detector import run_story_detection, format_stories_report
                    send_telegram_message("⏳ Detecting market stories...")
                    result = run_story_detection()
                    msg = format_stories_report(result)
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Stories error: {str(e)}")

            elif text.lower().startswith('/story '):
                # Detailed info on specific story
                story_name = text[7:].strip()
                try:
                    from story_detector import format_single_story
                    send_telegram_message(f"⏳ Analyzing {story_name}...")
                    msg = format_single_story(story_name)
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Story error: {str(e)}")

            elif text.lower() == '/learned':
                # View all learned themes
                try:
                    from story_detector import get_all_learned_themes
                    learned = get_all_learned_themes()

                    msg = "🧠 *LEARNED THEMES*\n\n"

                    if learned['promoted']:
                        msg += "*✅ PROMOTED (confirmed themes):*\n"
                        for t in learned['promoted'][:5]:
                            msg += f"• *{t['name']}*\n"
                            if t['primary_plays']:
                                msg += f"  Primary: `{'`, `'.join(t['primary_plays'][:4])}`\n"
                        msg += "\n"

                    if learned['emerging']:
                        msg += "*📈 EMERGING (being tracked):*\n"
                        for t in learned['emerging'][:5]:
                            msg += f"• *{t['name']}* ({t['total_mentions']} mentions, {t['days_tracked']} days)\n"
                            if t['top_stocks']:
                                msg += f"  Stocks: `{'`, `'.join(t['top_stocks'][:4])}`\n"
                        msg += "\n"

                    if not learned['promoted'] and not learned['emerging']:
                        msg += "_No themes learned yet. Run /stories to start learning._\n"

                    msg += "_Themes auto-promote after 3+ days of sustained mentions_"
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Learned error: {str(e)}")

            elif text.lower() == '/help':
                msg = "🤖 *BOT COMMANDS*\n\n"
                msg += "*Story Detection:*\n"
                msg += "• `/stories` → Stories in play + emerging themes\n"
                msg += "• `/story AI` → Deep dive on specific story\n"
                msg += "• `/learned` → View auto-learned themes\n\n"
                msg += "*Analysis:*\n"
                msg += "• Send ticker (e.g., `NVDA`) → Full analysis + chart\n"
                msg += "• `/top` → Top 10 stocks\n"
                msg += "• `/mtf` → Multi-timeframe confluence\n"
                msg += "• `/sectors` → Sector rotation\n"
                msg += "• `/news` → News + social sentiment\n"
                msg += "• `/tam` → TAM growth rankings\n"
                msg += "• `/tam AI_Infrastructure` → Specific theme TAM\n\n"
                msg += "_Bot checks every 15 min during market hours_"
                send_telegram_message(msg)

            elif text.startswith('/'):
                send_telegram_message(f"Unknown command. Send `/help` for options.")

        # Update offset
        with open(offset_file, 'w') as f:
            json.dump({'offset': update_id}, f)

    print(f"Bot listener done: {datetime.now()}")


if __name__ == '__main__':
    main()
