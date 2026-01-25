#!/usr/bin/env python3
"""
Stock Scanner Bot

Features:
- AI Intelligence (briefing, predict, coach, patterns)
- Analysis (ticker, top, scan, screen)
- Stories (fast detection, news, sectors)
- Screener with custom filters
- Earnings calendar
- Backtesting
"""

import os
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import yfinance as yf
import pandas as pd
import threading

app = Flask(__name__)

# Track processed updates to prevent duplicates
processed_updates = set()
MAX_PROCESSED = 1000  # Limit memory usage

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') or os.environ.get('BOT_TOKEN', '')
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')


# =============================================================================
# TELEGRAM HELPERS
# =============================================================================

def send_message(chat_id, text, parse_mode='Markdown'):
    """Send message to Telegram."""
    try:
        # Truncate if too long
        if len(text) > 4000:
            text = text[:4000] + "\n\n_...truncated_"

        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True,
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Send error: {e}")
        return False


def send_photo(chat_id, photo_buffer, caption=''):
    """Send photo to Telegram."""
    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendPhoto",
            files={'photo': ('chart.png', photo_buffer, 'image/png')},
            data={'chat_id': chat_id, 'caption': caption[:1024], 'parse_mode': 'Markdown'},
            timeout=30
        )
        return response.status_code == 200
    except:
        return False


# =============================================================================
# HELP
# =============================================================================

def handle_help(chat_id):
    """Handle /help command."""
    msg = "🤖 *STOCK SCANNER BOT*\n\n"

    msg += "*📊 Analysis:*\n"
    msg += "• `NVDA` → Full analysis + chart\n"
    msg += "• `/scan` → Run full scanner\n"
    msg += "• `/top` → Top 10 stocks\n"
    msg += "• `/screen rs>5 vol>2` → Custom screener\n\n"

    msg += "*📈 Intelligence:*\n"
    msg += "• `/stories` → Hot themes\n"
    msg += "• `/news` → News sentiment\n"
    msg += "• `/sectors` → Sector rotation\n"
    msg += "• `/earnings` → Earnings calendar\n"
    msg += "• `/backtest NVDA` → Signal accuracy\n\n"

    msg += "*🤖 AI:*\n"
    msg += "• `/briefing` → AI market narrative\n"
    msg += "• `/predict NVDA` → AI prediction\n"
    msg += "• `/coach` → AI coaching\n"
    msg += "• `/patterns` → Best signal patterns\n"

    send_message(chat_id, msg)


# =============================================================================
# TICKER ANALYSIS (Improved with candlestick)
# =============================================================================

def handle_ticker(chat_id, ticker):
    """Handle ticker analysis with candlestick chart."""
    ticker = ticker.upper().strip()
    send_message(chat_id, f"⏳ Analyzing {ticker}...")

    try:
        df = yf.download(ticker, period='3mo', progress=False)
        if len(df) < 20:
            send_message(chat_id, f"❌ No data for `{ticker}`")
            return

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        current = float(close.iloc[-1])

        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma_20

        # RS calculation
        spy = yf.download('SPY', period='1mo', progress=False)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)

        stock_ret = (current / float(close.iloc[-20]) - 1) * 100
        spy_ret = (float(spy['Close'].iloc[-1]) / float(spy['Close'].iloc[-20]) - 1) * 100
        rs = stock_ret - spy_ret

        vol_ratio = float(df['Volume'].iloc[-1] / df['Volume'].iloc[-20:].mean())

        # ATR
        high, low = df['High'], df['Low']
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])

        # Check earnings
        try:
            from earnings import get_earnings_date
            earn_date = get_earnings_date(ticker)
            if earn_date:
                days_to_earn = (earn_date - datetime.now().date()).days
                if 0 <= days_to_earn <= 7:
                    earnings_warning = f"\n⚠️ *Earnings in {days_to_earn} days!*"
                else:
                    earnings_warning = ""
            else:
                earnings_warning = ""
        except:
            earnings_warning = ""

        msg = f"📊 *{ticker} ANALYSIS*\n\n"
        msg += f"*Price:* ${current:.2f}\n"
        msg += f"*RS vs SPY:* {rs:+.1f}%\n"
        msg += f"*Volume:* {vol_ratio:.1f}x avg{'🔥' if vol_ratio > 2 else ''}\n\n"

        msg += "*Trend:*\n"
        msg += f"• 20 SMA: {'✅' if current > sma_20 else '❌'} ${sma_20:.2f}\n"
        msg += f"• 50 SMA: {'✅' if current > sma_50 else '❌'} ${sma_50:.2f}\n"

        msg += f"\n*Levels:*\n"
        msg += f"• Stop: ${current - 2*atr:.2f} (-{2*atr/current*100:.1f}%)\n"
        msg += f"• Target: ${current + 3*atr:.2f} (+{3*atr/current*100:.1f}%)"
        msg += earnings_warning

        send_message(chat_id, msg)

        # Send candlestick chart
        try:
            from charts import generate_candlestick_chart
            chart = generate_candlestick_chart(ticker, df)
            if chart:
                send_photo(chat_id, chart, f"{ticker} Chart")
        except Exception as e:
            print(f"Chart error: {e}")

    except Exception as e:
        send_message(chat_id, f"❌ Error: {str(e)}")




# =============================================================================
# SCREENER
# =============================================================================

def handle_screen(chat_id, args):
    """Run stock screener."""
    send_message(chat_id, "⏳ Screening stocks...")

    try:
        from screener import parse_screen_args, screen_stocks, format_screen_results, PRESET_SCREENS

        # Check for preset
        if args.lower() in PRESET_SCREENS:
            filters = PRESET_SCREENS[args.lower()]
        else:
            filters = parse_screen_args(args)

        if not filters:
            msg = "🔍 *SCREENER*\n\n"
            msg += "*Presets:*\n"
            msg += "• `/screen momentum` - RS leaders\n"
            msg += "• `/screen breakout` - High volume breaks\n"
            msg += "• `/screen oversold` - Pullback plays\n"
            msg += "• `/screen volume` - Volume spikes\n\n"
            msg += "*Custom:*\n"
            msg += "`/screen rs>5 vol_ratio>2`\n\n"
            msg += "*Filters:* rs, vol_ratio, ret_5d, ret_20d, above_20sma, above_50sma, atr_pct"
            send_message(chat_id, msg)
            return

        results = screen_stocks(filters)
        msg = format_screen_results(results)
        send_message(chat_id, msg)

    except Exception as e:
        send_message(chat_id, f"Screener error: {str(e)}")


# =============================================================================
# SCANNER
# =============================================================================

def handle_scan(chat_id):
    """Run the main scanner."""
    send_message(chat_id, "⏳ Running scanner (this takes ~30 sec)...")

    try:
        # Simple inline scanner
        from screener import screen_stocks

        # Run momentum screen
        filters = {'rs': '>3', 'above_20sma': True, 'vol_ratio': '>1'}
        results = screen_stocks(filters)

        if results:
            msg = "🔍 *SCAN RESULTS*\n\n"
            for i, s in enumerate(results[:15], 1):
                emoji = "🥇" if i <= 3 else ("🥈" if i <= 6 else "🥉")
                msg += f"{emoji} `{s['ticker']:5}` RS: {s['rs']:+.1f}% Vol: {s['vol_ratio']:.1f}x\n"

            msg += f"\n_Scanned {len(results)} stocks with positive RS_"
            send_message(chat_id, msg)
        else:
            send_message(chat_id, "No stocks match scan criteria")

    except Exception as e:
        send_message(chat_id, f"Scan error: {str(e)}")


# =============================================================================
# EARNINGS
# =============================================================================

def handle_earnings(chat_id):
    """Show earnings calendar."""
    send_message(chat_id, "⏳ Fetching earnings...")

    try:
        from earnings import get_upcoming_earnings, format_earnings_calendar

        earnings = get_upcoming_earnings()
        msg = format_earnings_calendar(earnings)
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Earnings error: {str(e)}")


# =============================================================================
# BACKTEST
# =============================================================================

def handle_backtest(chat_id, ticker):
    """Run backtest for ticker."""
    ticker = ticker.upper().strip()
    send_message(chat_id, f"⏳ Backtesting {ticker}...")

    try:
        from backtest import backtest_all_strategies, format_backtest_results

        results = backtest_all_strategies(ticker)
        msg = format_backtest_results(results)
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Backtest error: {str(e)}")


# =============================================================================
# STORIES, NEWS, SECTORS (existing)
# =============================================================================

def handle_stories(chat_id):
    """Handle /stories command."""
    send_message(chat_id, "⏳ Detecting stories...")
    try:
        from fast_stories import run_fast_story_detection, format_fast_stories_report
        result = run_fast_story_detection(use_cache=True)
        msg = format_fast_stories_report(result)
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Stories error: {str(e)}")


def handle_news(chat_id):
    """Handle /news command."""
    send_message(chat_id, "⏳ Scanning news...")
    try:
        from news_analyzer import scan_news_sentiment, format_news_scan_results
        results = scan_news_sentiment(['NVDA', 'AAPL', 'TSLA', 'META', 'AMD'])
        msg = format_news_scan_results(results)
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"News error: {str(e)}")


def handle_sectors(chat_id):
    """Handle /sectors command."""
    send_message(chat_id, "⏳ Analyzing sectors...")
    try:
        from sector_rotation import run_sector_rotation_analysis, format_sector_rotation_report
        results = run_sector_rotation_analysis()
        msg = format_sector_rotation_report(results['ranked'], results['rotations'], results['cycle'])
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Sectors error: {str(e)}")


# =============================================================================
# TOP STOCKS
# =============================================================================

def handle_top(chat_id):
    """Handle /top command."""
    send_message(chat_id, "⏳ Fetching top stocks...")
    try:
        import glob
        scan_files = glob.glob('scan_*.csv')
        if scan_files:
            latest = max(scan_files)
            df = pd.read_csv(latest)
            msg = "🏆 *TOP 10 STOCKS*\n\n"
            for _, row in df.head(10).iterrows():
                msg += f"`{row['ticker']:5}` | Score: {row['composite_score']:.0f} | RS: {row['rs_composite']:+.1f}%\n"
            send_message(chat_id, msg)
        else:
            # Fallback to screener
            handle_scan(chat_id)
    except Exception as e:
        send_message(chat_id, f"Error: {str(e)}")


# =============================================================================
# AI COMMANDS (with fallback)
# =============================================================================

def handle_ai(chat_id):
    """Handle /ai command."""
    try:
        from ai_learning import format_ai_insights
        msg = format_ai_insights()
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"AI module not available: {str(e)}")


def handle_briefing(chat_id):
    """Handle /briefing command."""
    send_message(chat_id, "🤖 Generating briefing...")
    try:
        from ai_learning import get_daily_briefing, DEEPSEEK_API_KEY

        if not DEEPSEEK_API_KEY:
            send_message(chat_id, "❌ DEEPSEEK_API_KEY not set in environment.")
            return

        briefing = get_daily_briefing()

        if briefing and briefing.get('headline'):
            msg = "🎯 *AI MARKET BRIEFING*\n\n"
            msg += f"*{briefing.get('headline')}*\n\n"
            msg += f"*Mood:* {briefing.get('market_mood', 'N/A').upper()}\n\n"
            if briefing.get('main_narrative'):
                msg += f"_{briefing.get('main_narrative')}_\n\n"
            opp = briefing.get('key_opportunity', {})
            if opp and opp.get('description'):
                msg += f"*Opportunity:* {opp.get('description')}\n"
                if opp.get('tickers'):
                    msg += f"Watch: `{'`, `'.join(opp['tickers'][:4])}`"
        elif briefing and briefing.get('error'):
            msg = f"Briefing error: {briefing.get('error')}"
        elif briefing and briefing.get('raw_narrative'):
            msg = f"🎯 *AI BRIEFING*\n\n{briefing.get('raw_narrative')[:1500]}"
        else:
            msg = "❌ AI returned empty response. Check API key."
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Briefing error: {str(e)}")


def handle_predict(chat_id, ticker):
    """Handle /predict command."""
    ticker = ticker.upper().strip()
    send_message(chat_id, f"🤖 Predicting {ticker}...")

    try:
        from ai_learning import predict_trade_outcome

        df = yf.download(ticker, period='3mo', progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        current = float(close.iloc[-1])
        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1])
        vol_ratio = float(df['Volume'].iloc[-1] / df['Volume'].iloc[-20:].mean())

        signals = {
            'above_20sma': current > sma_20,
            'above_50sma': current > sma_50,
            'volume_spike': vol_ratio > 1.5,
            'uptrend': sma_20 > sma_50,
        }

        prediction = predict_trade_outcome(ticker, signals, price_data=df)

        if prediction:
            prob = prediction.get('success_probability', 50)
            emoji = "🟢" if prob >= 60 else ("🟡" if prob >= 40 else "🔴")
            msg = f"🎲 *AI PREDICTION: {ticker}*\n\n"
            msg += f"{emoji} *Success:* {prob}%\n"
            msg += f"*Recommendation:* {prediction.get('recommendation', 'N/A').upper()}\n\n"
            for f in prediction.get('key_bullish_factors', [])[:2]:
                msg += f"✅ {f}\n"
            for f in prediction.get('key_risk_factors', [])[:2]:
                msg += f"⚠️ {f}\n"
        else:
            msg = f"Prediction unavailable for {ticker}"

        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Predict error: {str(e)}")


def handle_coach(chat_id):
    """Handle /coach command."""
    send_message(chat_id, "🤖 AI coaching...")
    try:
        from ai_learning import get_weekly_coaching, load_trade_journal
        from self_learning import load_alert_history

        journal = load_trade_journal()
        alerts = load_alert_history()
        recent_trades = journal.get('trades', [])[-20:]

        if recent_trades:
            wins = len([t for t in recent_trades if t.get('outcome') == 'win'])
            accuracy = wins / len(recent_trades) * 100
        else:
            accuracy = 50

        coaching = get_weekly_coaching(recent_trades, alerts.get('alerts', [])[-30:], accuracy)

        if coaching:
            msg = "🏋️ *AI COACH*\n\n"
            msg += f"*Grade:* {coaching.get('overall_grade', 'N/A')}\n"
            for s in coaching.get('strengths', [])[:2]:
                msg += f"✅ {s.get('strength', '')}\n"
            for w in coaching.get('weaknesses', [])[:2]:
                msg += f"⚠️ {w.get('weakness', '')}\n"
            focus = coaching.get('weekly_focus', {})
            if focus:
                msg += f"\n🎯 *Focus:* {focus.get('primary_goal', '')}"
        else:
            msg = "Need more trade data for coaching."

        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Coach error: {str(e)}")


def handle_patterns(chat_id):
    """Handle /patterns command."""
    try:
        from ai_learning import get_best_patterns
        patterns = get_best_patterns()
        msg = "📊 *BEST PATTERNS*\n\n"
        if patterns:
            for i, p in enumerate(patterns[:10], 1):
                emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "•"))
                msg += f"{emoji} *{p['pattern']}* - {p['win_rate']:.0f}%\n"
        else:
            msg += "_No patterns yet. AI learns from trade outcomes._"
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Patterns error: {str(e)}")


def handle_trade(chat_id, args):
    """Record a trade."""
    try:
        parts = args.split()
        if len(parts) >= 3:
            from ai_learning import record_trade

            ticker = parts[0].upper()
            entry = float(parts[1])
            exit_price = float(parts[2])

            trade_id, analysis = record_trade(
                ticker=ticker,
                entry_price=entry,
                exit_price=exit_price,
                entry_date=datetime.now().strftime('%Y-%m-%d'),
                exit_date=datetime.now().strftime('%Y-%m-%d'),
                signals_at_entry={'manual_entry': True}
            )

            pnl = (exit_price - entry) / entry * 100
            emoji = "✅" if pnl > 0 else "❌"
            msg = f"{emoji} *TRADE RECORDED*\n\n"
            msg += f"`{ticker}` ${entry} → ${exit_price} ({pnl:+.1f}%)"
            if analysis:
                msg += f"\n\n*Lesson:* {analysis.get('lesson_learned', 'N/A')}"
        else:
            msg = "Usage: `/trade NVDA 150 165`"

        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Trade error: {str(e)}")


# =============================================================================
# WEBHOOK HANDLER
# =============================================================================

def process_message(message):
    """Process incoming Telegram message."""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '').strip()

    if not chat_id or not text:
        return

    print(f"[{datetime.now()}] {chat_id}: {text}")

    text_lower = text.lower()

    # Help
    if text_lower in ['/help', '/start']:
        handle_help(chat_id)

    # Subscribe / Chat ID
    elif text_lower == '/subscribe':
        msg = "🔔 *AUTO ALERTS SETUP*\n\n"
        msg += f"Your Chat ID: `{chat_id}`\n\n"
        msg += "*To enable auto alerts:*\n"
        msg += "1. Go to GitHub repo Settings\n"
        msg += "2. Secrets → Actions\n"
        msg += f"3. Add `TELEGRAM_CHAT_ID` = `{chat_id}`\n\n"
        msg += "*You'll receive:*\n"
        msg += "• 🚨 New emerging themes\n"
        msg += "• 🔥 Themes heating up\n"
        msg += "• 📈 Price alerts\n"
        msg += "• 📅 Earnings warnings\n\n"
        msg += "_Alerts run every 30 min during market hours_"
        send_message(chat_id, msg)

    # Analysis
    elif text_lower == '/scan':
        handle_scan(chat_id)
    elif text_lower == '/top':
        handle_top(chat_id)
    elif text_lower.startswith('/screen'):
        handle_screen(chat_id, text[7:].strip())

    # Intelligence
    elif text_lower == '/stories':
        handle_stories(chat_id)
    elif text_lower == '/news':
        handle_news(chat_id)
    elif text_lower == '/sectors':
        handle_sectors(chat_id)
    elif text_lower == '/earnings':
        handle_earnings(chat_id)
    elif text_lower.startswith('/backtest '):
        handle_backtest(chat_id, text[10:].strip())

    # AI
    elif text_lower == '/ai':
        handle_ai(chat_id)
    elif text_lower == '/briefing':
        handle_briefing(chat_id)
    elif text_lower.startswith('/predict '):
        handle_predict(chat_id, text[9:].strip())
    elif text_lower == '/coach':
        handle_coach(chat_id)
    elif text_lower == '/patterns':
        handle_patterns(chat_id)
    elif text_lower.startswith('/trade '):
        handle_trade(chat_id, text[7:].strip())

    # Ticker lookup (1-5 letter word)
    elif len(text) <= 5 and text.replace('.', '').isalpha():
        handle_ticker(chat_id, text)

    # Unknown command
    elif text.startswith('/'):
        send_message(chat_id, "Unknown command. Send `/help`")


@app.route('/')
def home():
    """Health check endpoint."""
    return jsonify({
        'bot': 'Stock Scanner Bot',
        'status': 'running',
        'version': '2.0',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram webhook."""
    global processed_updates

    try:
        data = request.get_json()

        if not data:
            return jsonify({'ok': True})

        # Deduplicate by update_id to prevent retries
        update_id = data.get('update_id')
        if update_id:
            if update_id in processed_updates:
                print(f"Skipping duplicate update {update_id}")
                return jsonify({'ok': True})

            processed_updates.add(update_id)

            # Limit memory usage
            if len(processed_updates) > MAX_PROCESSED:
                processed_updates = set(list(processed_updates)[-500:])

        if 'message' in data:
            message = data['message']
            text = message.get('text', '').strip().lower()

            # List of slow commands that need background processing
            slow_commands = ['/news', '/sectors', '/stories', '/scan',
                          '/earnings', '/briefing', '/coach', '/top']

            # Check if this is a slow command
            is_slow = any(text.startswith(cmd) for cmd in slow_commands)

            if is_slow:
                # Process in background thread to prevent Telegram timeout
                thread = threading.Thread(target=process_message, args=(message,))
                thread.start()
            else:
                # Fast commands can run synchronously
                process_message(message)

        return jsonify({'ok': True})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/set_webhook')
def set_webhook():
    """Set Telegram webhook URL."""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing url parameter'})
    response = requests.post(f"{TELEGRAM_API}/setWebhook", json={'url': f"{url}/webhook"})
    return jsonify(response.json())


# =============================================================================
# DASHBOARD API ENDPOINTS
# =============================================================================

def add_cors_headers(response):
    """Add CORS headers to response."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@app.after_request
def after_request(response):
    """Add CORS headers to all responses."""
    return add_cors_headers(response)


@app.route('/api/stories')
def api_stories():
    """Get current hot stories/themes."""
    try:
        from fast_stories import run_fast_story_detection
        result = run_fast_story_detection(use_cache=True)
        return jsonify({
            'ok': True,
            'themes': result.get('themes', []),
            'momentum_stocks': result.get('momentum_stocks', []),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/scan')
def api_scan():
    """Get scan results."""
    try:
        from screener import screen_stocks
        filters = {'rs': '>0', 'above_20sma': True}
        results = screen_stocks(filters)
        return jsonify({
            'ok': True,
            'stocks': results[:20],
            'total': len(results),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/ticker/<ticker>')
def api_ticker(ticker):
    """Get ticker analysis."""
    try:
        ticker = ticker.upper()
        df = yf.download(ticker, period='3mo', progress=False)

        if len(df) < 20:
            return jsonify({'ok': False, 'error': 'No data'})

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        current = float(close.iloc[-1])
        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma_20

        # RS calculation
        spy = yf.download('SPY', period='1mo', progress=False)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)

        stock_ret = (current / float(close.iloc[-20]) - 1) * 100
        spy_ret = (float(spy['Close'].iloc[-1]) / float(spy['Close'].iloc[-20]) - 1) * 100
        rs = stock_ret - spy_ret

        vol_ratio = float(df['Volume'].iloc[-1] / df['Volume'].iloc[-20:].mean())

        return jsonify({
            'ok': True,
            'ticker': ticker,
            'price': current,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'rs': rs,
            'vol_ratio': vol_ratio,
            'above_20sma': current > sma_20,
            'above_50sma': current > sma_50,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/news')
def api_news():
    """Get news sentiment."""
    try:
        from news_analyzer import scan_news_sentiment
        results = scan_news_sentiment(['NVDA', 'AAPL', 'TSLA', 'META', 'AMD', 'MSFT'])
        return jsonify({
            'ok': True,
            'sentiment': results,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/sectors')
def api_sectors():
    """Get sector rotation data."""
    try:
        from sector_rotation import run_sector_rotation_analysis
        result = run_sector_rotation_analysis()
        return jsonify({
            'ok': True,
            'sectors': result.get('ranked', []),
            'rotations': result.get('rotations', []),
            'cycle': result.get('cycle', 'Unknown'),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/earnings')
def api_earnings():
    """Get upcoming earnings."""
    try:
        from earnings import get_upcoming_earnings
        earnings = get_upcoming_earnings()
        return jsonify({
            'ok': True,
            'earnings': earnings,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/briefing')
def api_briefing():
    """Get AI market briefing."""
    try:
        from ai_learning import get_daily_briefing
        briefing = get_daily_briefing()
        return jsonify({
            'ok': True,
            'briefing': briefing,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/predict/<ticker>')
def api_predict(ticker):
    """Get AI prediction for ticker."""
    try:
        from ai_learning import predict_trade_outcome

        ticker = ticker.upper()
        df = yf.download(ticker, period='3mo', progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        current = float(close.iloc[-1])
        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1])
        vol_ratio = float(df['Volume'].iloc[-1] / df['Volume'].iloc[-20:].mean())

        signals = {
            'above_20sma': current > sma_20,
            'above_50sma': current > sma_50,
            'volume_spike': vol_ratio > 1.5,
            'uptrend': sma_20 > sma_50,
        }

        prediction = predict_trade_outcome(ticker, signals, price_data=df)

        return jsonify({
            'ok': True,
            'ticker': ticker,
            'prediction': prediction,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
