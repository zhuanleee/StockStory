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
import time
from functools import wraps

from config import config
from utils import (
    get_logger, normalize_dataframe_columns, get_spy_data_cached,
    calculate_rs, send_message, send_photo, validate_ticker,
    validate_webhook_url, validate_webhook_signature, ValidationError,
    DataFetchError,
)

logger = get_logger(__name__)

app = Flask(__name__)


# Global error handler to return JSON instead of HTML on errors
@app.errorhandler(500)
def handle_500(error):
    """Return JSON on internal server errors."""
    return jsonify({
        'ok': False,
        'error': 'Internal server error',
        'details': str(error)
    }), 500


@app.errorhandler(Exception)
def handle_exception(error):
    """Return JSON for unhandled exceptions."""
    logger.error(f"Unhandled exception: {error}")
    return jsonify({
        'ok': False,
        'error': str(error.__class__.__name__),
        'details': str(error)
    }), 500


# Track processed updates to prevent duplicates
processed_updates = set()
MAX_PROCESSED = 1000  # Limit memory usage


# =============================================================================
# CACHING SYSTEM - Reduce load on heavy endpoints
# =============================================================================

class EndpointCache:
    """Simple in-memory cache for expensive API endpoints."""

    def __init__(self):
        self._cache = {}
        self._locks = {}
        self._computing = set()

    def get(self, key: str, ttl_seconds: int = 300):
        """Get cached value if valid."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < ttl_seconds:
                return data, True  # data, is_cached
        return None, False

    def set(self, key: str, data):
        """Store data in cache."""
        self._cache[key] = (data, time.time())

    def is_computing(self, key: str) -> bool:
        """Check if computation is in progress."""
        return key in self._computing

    def start_computing(self, key: str):
        """Mark computation as started."""
        self._computing.add(key)

    def stop_computing(self, key: str):
        """Mark computation as finished."""
        self._computing.discard(key)


# Global cache instance
_endpoint_cache = EndpointCache()

# Cache TTLs (in seconds)
CACHE_TTL = {
    'health': 300,      # 5 minutes
    'stories': 600,     # 10 minutes
    'scan': 300,        # 5 minutes
    'top': 300,         # 5 minutes
    'sectors': 600,     # 10 minutes
}

# Configuration is now loaded from config module
# Access via: config.telegram.bot_token, config.telegram.api_url, config.ai.api_key


# =============================================================================
# TELEGRAM HELPERS - Now imported from utils
# =============================================================================


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
    msg += "• `/health` → Fear & Greed + Breadth\n"
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

        df = normalize_dataframe_columns(df)

        close = df['Close']
        current = float(close.iloc[-1])

        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma_20

        # RS calculation using cached SPY data
        spy_df, spy_returns = get_spy_data_cached()
        rs_data = calculate_rs(df, spy_returns)
        rs = rs_data['rs_composite']

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
        except Exception as e:
            logger.debug(f"Earnings check failed for {ticker}: {e}")
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
            logger.error(f"Chart error for {ticker}: {e}")

    except Exception as e:
        logger.error(f"Ticker analysis error for {ticker}: {e}")
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


def handle_health(chat_id):
    """Handle /health command - Market health + Fear & Greed."""
    send_message(chat_id, "⏳ Analyzing market health...")
    try:
        from market_health import get_market_health, format_health_report
        health = get_market_health()
        msg = format_health_report(health)
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Health error: {str(e)}")


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
        from ai_learning import get_daily_briefing

        if not config.ai.api_key:
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
        df = normalize_dataframe_columns(df)

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

    logger.info(f"Message from {chat_id}: {text}")

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
    elif text_lower == '/health':
        handle_health(chat_id)
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

    # Verify webhook signature
    signature = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
    if not validate_webhook_signature(request.data, signature):
        logger.warning("Invalid webhook signature")
        return jsonify({'ok': False}), 401

    try:
        data = request.get_json()

        if not data:
            return jsonify({'ok': True})

        # Deduplicate by update_id to prevent retries
        update_id = data.get('update_id')
        if update_id:
            if update_id in processed_updates:
                logger.debug(f"Skipping duplicate update {update_id}")
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
                          '/earnings', '/briefing', '/coach', '/top', '/health']

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
        logger.error(f"Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/set_webhook')
def set_webhook():
    """Set Telegram webhook URL."""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing url parameter'}), 400
    try:
        validated_url = validate_webhook_url(url)
    except ValidationError as e:
        logger.warning(f"Invalid webhook URL rejected: {url}")
        return jsonify({'error': str(e)}), 400
    response = requests.post(f"{config.telegram.api_url}/setWebhook", json={'url': f"{validated_url}/webhook"})
    return jsonify(response.json())


# =============================================================================
# DASHBOARD API ENDPOINTS
# =============================================================================


@app.after_request
def add_cors_headers(response):
    """Add CORS headers to response based on allowed origins."""
    origin = request.headers.get('Origin', '')
    allowed = config.security.allowed_cors_origins
    if '*' in allowed or origin in allowed:
        response.headers['Access-Control-Allow-Origin'] = origin if origin else '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@app.route('/api/stories')
def api_stories():
    """Get current hot stories/themes (cached)."""
    cache_key = 'stories'

    # Check cache first
    cached_data, is_cached = _endpoint_cache.get(cache_key, CACHE_TTL['stories'])
    if is_cached:
        cached_data['cached'] = True
        return jsonify(cached_data)

    # Return stale cache if computation in progress
    if _endpoint_cache.is_computing(cache_key):
        if cached_data:
            cached_data['cached'] = True
            cached_data['computing'] = True
            return jsonify(cached_data)
        return jsonify({'ok': True, 'themes': [], 'momentum_stocks': [], 'cached': False, 'computing': True})

    try:
        _endpoint_cache.start_computing(cache_key)
        from fast_stories import run_fast_story_detection
        result = run_fast_story_detection(use_cache=True)
        response = {
            'ok': True,
            'themes': result.get('themes', [])[:10],  # Limit results
            'momentum_stocks': result.get('momentum_stocks', [])[:10],
            'timestamp': datetime.now().isoformat(),
            'cached': False
        }
        _endpoint_cache.set(cache_key, response)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Stories endpoint error: {e}")
        return jsonify({'ok': False, 'error': str(e)})
    finally:
        _endpoint_cache.stop_computing(cache_key)


@app.route('/api/scan')
def api_scan():
    """Get scan results (cached)."""
    cache_key = 'scan'

    # Check cache first
    cached_data, is_cached = _endpoint_cache.get(cache_key, CACHE_TTL['scan'])
    if is_cached:
        cached_data['cached'] = True
        return jsonify(cached_data)

    # Return stale cache if computation in progress
    if _endpoint_cache.is_computing(cache_key):
        if cached_data:
            cached_data['cached'] = True
            cached_data['computing'] = True
            return jsonify(cached_data)
        return jsonify({'ok': True, 'stocks': [], 'total': 0, 'cached': False, 'computing': True})

    try:
        _endpoint_cache.start_computing(cache_key)
        from screener import screen_stocks
        filters = {'rs': '>0', 'above_20sma': True}
        results = screen_stocks(filters)
        response = {
            'ok': True,
            'stocks': results[:20],
            'total': len(results),
            'timestamp': datetime.now().isoformat(),
            'cached': False
        }
        _endpoint_cache.set(cache_key, response)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Scan endpoint error: {e}")
        return jsonify({'ok': False, 'error': str(e)})
    finally:
        _endpoint_cache.stop_computing(cache_key)


@app.route('/api/ticker/<ticker>')
def api_ticker(ticker):
    """Get ticker analysis."""
    try:
        ticker = ticker.upper()
        df = yf.download(ticker, period='3mo', progress=False)

        if len(df) < 20:
            return jsonify({'ok': False, 'error': 'No data'})

        df = normalize_dataframe_columns(df)

        close = df['Close']
        current = float(close.iloc[-1])
        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma_20

        # RS calculation using cached SPY data
        spy_df, spy_returns = get_spy_data_cached()
        rs_data = calculate_rs(df, spy_returns)
        rs = rs_data['rs_composite']

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


def _get_simple_news_sentiment(tickers):
    """Simple news sentiment using yfinance only (fallback)."""
    results = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)

            # Try to get news - handle different yfinance versions
            news = []
            try:
                if hasattr(stock, 'news'):
                    news = stock.news or []
                elif hasattr(stock, 'get_news'):
                    news = stock.get_news() or []
            except Exception:
                news = []

            bullish_count = 0
            bearish_count = 0
            headlines = []

            for item in (news[:10] if news else []):
                try:
                    title = str(item.get('title', '')).lower()
                    headlines.append({
                        'title': item.get('title', ''),
                        'source': item.get('publisher', item.get('source', ''))
                    })

                    # Simple sentiment check
                    bullish_words = ['beat', 'surge', 'gain', 'rise', 'jump', 'high', 'record', 'growth', 'strong', 'upgrade']
                    bearish_words = ['miss', 'drop', 'fall', 'low', 'down', 'weak', 'concern', 'risk', 'decline', 'downgrade']

                    if any(w in title for w in bullish_words):
                        bullish_count += 1
                    if any(w in title for w in bearish_words):
                        bearish_count += 1
                except Exception:
                    continue

            total = bullish_count + bearish_count
            if total > 0:
                bullish_pct = int((bullish_count / total) * 100)
            else:
                bullish_pct = 50

            results.append({
                'ticker': ticker,
                'bullish': bullish_pct,
                'bearish': 100 - bullish_pct,
                'sentiment': 'BULLISH' if bullish_pct > 60 else ('BEARISH' if bullish_pct < 40 else 'NEUTRAL'),
                'headline_count': len(news) if news else 0,
                'key_headlines': headlines[:3]
            })
        except Exception as e:
            logger.warning(f"News sentiment for {ticker} failed: {e}")
            results.append({
                'ticker': ticker,
                'bullish': 50,
                'bearish': 50,
                'sentiment': 'NEUTRAL',
                'headline_count': 0,
                'key_headlines': []
            })

    return results


@app.route('/api/news')
def api_news():
    """Get news sentiment with caching."""
    cache_key = 'news'

    # Check cache first (15 min cache)
    cached_data, is_cached = _endpoint_cache.get(cache_key, 900)
    if is_cached:
        cached_data['cached'] = True
        return jsonify(cached_data)

    tickers = ['NVDA', 'AAPL', 'TSLA', 'META', 'AMD', 'MSFT']

    try:
        # Try the full news analyzer first
        from news_analyzer import scan_news_sentiment
        raw_results = scan_news_sentiment(tickers)

        # Transform results to dashboard format
        sentiment = []
        for r in raw_results:
            ticker = r.get('ticker', 'N/A')
            overall = r.get('overall_sentiment', 'NEUTRAL')

            # Convert sentiment to bullish/bearish percentages
            if overall == 'STRONG_BULLISH':
                bullish, bearish = 85, 15
            elif overall == 'BULLISH':
                bullish, bearish = 70, 30
            elif overall == 'STRONG_BEARISH':
                bullish, bearish = 15, 85
            elif overall == 'BEARISH':
                bullish, bearish = 30, 70
            else:
                bullish, bearish = 50, 50

            sentiment.append({
                'ticker': ticker,
                'bullish': bullish,
                'bearish': bearish,
                'sentiment': overall,
                'headline_count': r.get('headline_count', 0),
                'key_headlines': r.get('key_headlines', [])[:3]
            })

        response = {
            'ok': True,
            'sentiment': sentiment,
            'source': 'news_analyzer',
            'cached': False,
            'timestamp': datetime.now().isoformat()
        }
        _endpoint_cache.set(cache_key, response)
        return jsonify(response)

    except Exception as e:
        logger.error(f"News analyzer failed: {e}, falling back to yfinance")

        # Fallback to simple yfinance-based sentiment
        try:
            sentiment = _get_simple_news_sentiment(tickers)
            response = {
                'ok': True,
                'sentiment': sentiment,
                'source': 'yfinance_fallback',
                'cached': False,
                'timestamp': datetime.now().isoformat()
            }
            _endpoint_cache.set(cache_key, response)
            return jsonify(response)
        except Exception as e2:
            logger.error(f"Fallback also failed: {e2}")
            return jsonify({
                'ok': False,
                'sentiment': [],
                'error': f"Primary: {str(e)}, Fallback: {str(e2)}",
                'timestamp': datetime.now().isoformat()
            })


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


def _get_real_market_health_data():
    """Fetch real market data for health indicators with parallel processing."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def safe_download(ticker, period='6mo'):
        """Safely download and normalize data."""
        try:
            data = yf.download(ticker, period=period, progress=False)
            if data is None or len(data) == 0:
                return None
            return normalize_dataframe_columns(data)
        except Exception:
            return None

    def get_last_close(df):
        """Get last close price safely."""
        if df is None or len(df) == 0:
            return None
        try:
            return float(df['Close'].iloc[-1])
        except Exception:
            return None

    def calculate_sma(df, period):
        """Calculate SMA."""
        if df is None or len(df) < period:
            return None
        try:
            return float(df['Close'].rolling(window=period).mean().iloc[-1])
        except Exception:
            return None

    def analyze_ticker_breadth(ticker):
        """Analyze single ticker for breadth calculation."""
        try:
            df = safe_download(ticker, '1y')
            if df is None or len(df) < 200:
                return None
            close = get_last_close(df)
            sma20 = calculate_sma(df, 20)
            sma50 = calculate_sma(df, 50)
            sma200 = calculate_sma(df, 200)
            if close and sma20 and sma50 and sma200:
                return {
                    'ticker': ticker,
                    'above_20': close > sma20,
                    'above_50': close > sma50,
                    'above_200': close > sma200
                }
        except Exception:
            pass
        return None

    results = {}

    # 1. VIX - Volatility Index (lower = greed, higher = fear)
    vix_df = safe_download('^VIX', '1mo')
    vix_val = get_last_close(vix_df)
    if vix_val:
        if vix_val <= 12:
            results['vix_score'] = 100
        elif vix_val >= 35:
            results['vix_score'] = 0
        else:
            results['vix_score'] = round(100 - ((vix_val - 12) / 23 * 100), 1)
        results['vix_val'] = round(vix_val, 2)
    else:
        results['vix_score'] = 50
        results['vix_val'] = None

    # 2. Market Momentum - SPY vs 125-day MA
    spy_df = safe_download('SPY', '6mo')
    if spy_df is not None and len(spy_df) >= 125:
        spy_close = get_last_close(spy_df)
        spy_ma125 = calculate_sma(spy_df, 125)
        if spy_close and spy_ma125:
            pct_diff = ((spy_close - spy_ma125) / spy_ma125) * 100
            results['momentum_score'] = round(max(0, min(100, 50 + (pct_diff * 5))), 1)
            results['spy_price'] = round(spy_close, 2)
            results['spy_ma125'] = round(spy_ma125, 2)
        else:
            results['momentum_score'] = 50
    else:
        results['momentum_score'] = 50

    # 3. Put/Call Ratio - VIX term structure (VIX vs VIX3M)
    vix3m_df = safe_download('^VIX3M', '1mo')
    vix3m_val = get_last_close(vix3m_df)
    if vix_val and vix3m_val:
        term_ratio = vix_val / vix3m_val
        if term_ratio <= 0.8:
            results['put_call_score'] = 100
        elif term_ratio >= 1.2:
            results['put_call_score'] = 0
        else:
            results['put_call_score'] = round(100 - ((term_ratio - 0.8) / 0.4 * 100), 1)
        results['vix_term_ratio'] = round(term_ratio, 3)
    else:
        results['put_call_score'] = 50

    # 4. Safe Haven Demand - TLT vs SPY (20-day)
    tlt_df = safe_download('TLT', '2mo')
    if spy_df is not None and tlt_df is not None and len(spy_df) >= 20 and len(tlt_df) >= 20:
        try:
            spy_ret_20d = (float(spy_df['Close'].iloc[-1]) / float(spy_df['Close'].iloc[-20]) - 1) * 100
            tlt_ret_20d = (float(tlt_df['Close'].iloc[-1]) / float(tlt_df['Close'].iloc[-20]) - 1) * 100
            diff = spy_ret_20d - tlt_ret_20d
            results['safe_haven_score'] = round(max(0, min(100, 50 + (diff * 10))), 1)
            results['spy_20d_return'] = round(spy_ret_20d, 2)
            results['tlt_20d_return'] = round(tlt_ret_20d, 2)
        except Exception:
            results['safe_haven_score'] = 50
    else:
        results['safe_haven_score'] = 50

    # 5. Junk Bond Demand - HYG vs LQD (20-day)
    hyg_df = safe_download('HYG', '2mo')
    lqd_df = safe_download('LQD', '2mo')
    if hyg_df is not None and lqd_df is not None and len(hyg_df) >= 20 and len(lqd_df) >= 20:
        try:
            hyg_ret = (float(hyg_df['Close'].iloc[-1]) / float(hyg_df['Close'].iloc[-20]) - 1) * 100
            lqd_ret = (float(lqd_df['Close'].iloc[-1]) / float(lqd_df['Close'].iloc[-20]) - 1) * 100
            diff = hyg_ret - lqd_ret
            results['junk_bond_score'] = round(max(0, min(100, 50 + (diff * 15))), 1)
            results['hyg_20d_return'] = round(hyg_ret, 2)
            results['lqd_20d_return'] = round(lqd_ret, 2)
        except Exception:
            results['junk_bond_score'] = 50
    else:
        results['junk_bond_score'] = 50

    # 6. Stock Price Breadth - Full S&P 500 + NASDAQ 100 with parallel processing
    # S&P 500 components (comprehensive list)
    sp500_tickers = [
        'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'GOOG', 'META', 'TSLA', 'BRK-B', 'UNH',
        'XOM', 'JNJ', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV',
        'LLY', 'PEP', 'KO', 'COST', 'AVGO', 'WMT', 'MCD', 'CSCO', 'TMO', 'ABT',
        'CRM', 'ACN', 'DHR', 'ADBE', 'NKE', 'LIN', 'CMCSA', 'VZ', 'NEE', 'TXN',
        'PM', 'RTX', 'ORCL', 'HON', 'INTC', 'WFC', 'UNP', 'AMGN', 'IBM', 'QCOM',
        'LOW', 'BA', 'GE', 'SPGI', 'CAT', 'INTU', 'AMD', 'AMAT', 'DE', 'GS',
        'ELV', 'BKNG', 'MDLZ', 'AXP', 'ISRG', 'ADI', 'SYK', 'GILD', 'TJX', 'MMC',
        'PLD', 'REGN', 'VRTX', 'BLK', 'LMT', 'ADP', 'SBUX', 'CVS', 'CB', 'AMT',
        'MO', 'ETN', 'SCHW', 'CI', 'CME', 'SLB', 'DUK', 'BDX', 'SO', 'AON',
        'TMUS', 'ZTS', 'PNC', 'EQIX', 'ITW', 'MU', 'BSX', 'NOC', 'CL', 'LRCX',
        'ICE', 'WM', 'USB', 'CSX', 'SHW', 'EOG', 'PGR', 'GD', 'FCX', 'APD',
        'TGT', 'MMM', 'FIS', 'KLAC', 'SNPS', 'CDNS', 'CMG', 'COP', 'EMR', 'NSC',
        'MCK', 'ORLY', 'MAR', 'PXD', 'GM', 'F', 'NXPI', 'AZO', 'SRE', 'OXY',
        'HUM', 'TRV', 'MCO', 'PSA', 'ROP', 'ADSK', 'AJG', 'AFL', 'AEP', 'PCAR',
        'TFC', 'HCA', 'MET', 'MSCI', 'FDX', 'D', 'MCHP', 'APH', 'TEL', 'KMB',
        'PAYX', 'PRU', 'NEM', 'ECL', 'KDP', 'EW', 'DOW', 'ALL', 'DXCM', 'CTAS',
        'IDXX', 'MNST', 'O', 'SPG', 'A', 'FTNT', 'AIG', 'CMI', 'WELL', 'YUM',
        'IQV', 'GIS', 'DHI', 'STZ', 'BIIB', 'WBD', 'JCI', 'PSX', 'VLO', 'COF',
        'PH', 'OTIS', 'ON', 'ANET', 'BK', 'RSG', 'SYY', 'KEYS', 'ROST', 'LEN',
        'AME', 'KHC', 'HES', 'VRSK', 'DD', 'GPN', 'GWW', 'ODFL', 'ROK', 'ABC',
        'HSY', 'FAST', 'EXC', 'XEL', 'WEC', 'CTSH', 'EIX', 'MTD', 'ANSS', 'PPG',
        'VICI', 'ILMN', 'DLTR', 'CBRE', 'MLM', 'IT', 'KR', 'EA', 'CPRT', 'AWK',
        'HAL', 'GEHC', 'RMD', 'CDW', 'TROW', 'DVN', 'ALB', 'EBAY', 'STT', 'FANG',
        'FITB', 'WTW', 'EQR', 'CHD', 'IR', 'VMC', 'FTV', 'HIG', 'EFX', 'HPQ',
        'GLW', 'LYB', 'TSCO', 'DOV', 'MTB', 'SBAC', 'NDAQ', 'WAT', 'AVB', 'DTE',
        'URI', 'ES', 'DLR', 'STE', 'BALL', 'WY', 'ZBH', 'PPL', 'HRL', 'HOLX',
        'INVH', 'LUV', 'NTRS', 'BR', 'NVR', 'FE', 'AEE', 'CAG', 'TYL', 'VLTO',
        'PKI', 'J', 'EXPD', 'ALGN', 'MKC', 'AMCR', 'TER', 'K', 'TRGP', 'CINF',
        'MOH', 'OMC', 'NUE', 'CF', 'MAA', 'CNP', 'MRO', 'AKAM', 'WRB', 'ATO',
        'CLX', 'RF', 'POOL', 'SYF', 'DRI', 'IEX', 'HPE', 'PAYC', 'CMS', 'PFG',
        'JBHT', 'ETSY', 'KEY', 'SWKS', 'WAB', 'BRO', 'NTAP', 'LW', 'DAL', 'IP',
        'TDY', 'EVRG', 'DGX', 'IRM', 'MAS', 'ENPH', 'SJM', 'AES', 'CFG', 'TXT',
        'TTWO', 'VTR', 'ESS', 'GRMN', 'NI', 'KIM', 'PEAK', 'LKQ', 'CHRW', 'FMC',
        'JKHY', 'L', 'APA', 'GPC', 'UAL', 'IPG', 'CTLT', 'DPZ', 'INCY', 'CRL',
        'CBOE', 'UDR', 'HST', 'LNT', 'BBWI', 'WDC', 'AAL', 'TECH', 'BIO', 'REG',
        'CPT', 'BXP', 'TAP', 'PNR', 'EMN', 'BWA', 'QRVO', 'CPB', 'SEDG', 'AIZ',
        'HII', 'MGM', 'NRG', 'WYNN', 'GL', 'RHI', 'CE', 'PHM', 'HSIC', 'BEN',
        'PNW', 'MKTX', 'GNRC', 'XRAY', 'ROL', 'AAP', 'FRT', 'IVZ', 'LUMN', 'CZR',
        'HAS', 'SEE', 'WHR', 'NWSA', 'NWS', 'FOXA', 'FOX', 'PARA', 'DVA', 'VFC'
    ]

    # NASDAQ 100 additions (not already in S&P 500)
    nasdaq100_extra = [
        'ABNB', 'AZN', 'CRWD', 'DDOG', 'DASH', 'FSLR', 'LCID', 'LULU', 'MELI', 'MRNA',
        'PANW', 'PDD', 'RIVN', 'SIRI', 'SPLK', 'TEAM', 'WDAY', 'ZM', 'ZS', 'COIN',
        'PYPL', 'OKTA', 'DOCU', 'ROKU', 'ASML', 'ARM', 'SMCI', 'TTD', 'MRVL', 'CEG'
    ]

    all_tickers = list(set(sp500_tickers + nasdaq100_extra))

    # Parallel processing with ThreadPoolExecutor
    above_20 = 0
    above_50 = 0
    above_200 = 0
    valid_count = 0
    analyzed_tickers = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(analyze_ticker_breadth, ticker): ticker for ticker in all_tickers}

        for future in as_completed(futures, timeout=120):
            try:
                result = future.result(timeout=10)
                if result:
                    valid_count += 1
                    analyzed_tickers.append(result['ticker'])
                    if result['above_20']:
                        above_20 += 1
                    if result['above_50']:
                        above_50 += 1
                    if result['above_200']:
                        above_200 += 1
            except Exception:
                pass

    if valid_count > 0:
        results['above_20sma'] = round((above_20 / valid_count) * 100, 1)
        results['above_50sma'] = round((above_50 / valid_count) * 100, 1)
        results['above_200sma'] = round((above_200 / valid_count) * 100, 1)
        results['breadth_score'] = round((results['above_20sma'] + results['above_50sma'] + results['above_200sma']) / 3, 1)
        results['breadth_sample_size'] = valid_count
        results['above_20_count'] = above_20
        results['above_50_count'] = above_50
        results['above_200_count'] = above_200
    else:
        results['above_20sma'] = 50
        results['above_50sma'] = 50
        results['above_200sma'] = 50
        results['breadth_score'] = 50
        results['breadth_sample_size'] = 0

    # 7. Advance/Decline from actual breadth data
    above_50_pct = results.get('above_50sma', 50)
    below_50_pct = 100 - above_50_pct
    results['advance_decline_ratio'] = round(above_50_pct / max(1, below_50_pct), 2)
    results['new_highs'] = results.get('above_20_count', 0)
    results['new_lows'] = valid_count - results.get('above_20_count', 0) if valid_count > 0 else 0

    return results


@app.route('/api/health')
def api_health():
    """Get real market health data from actual market indicators."""
    cache_key = 'health'

    # Check cache first (cache for 10 minutes due to heavy computation)
    cached_data, is_cached = _endpoint_cache.get(cache_key, 600)
    if is_cached:
        cached_data['cached'] = True
        return jsonify(cached_data)

    try:
        # Get real market data
        data = _get_real_market_health_data()

        # Calculate overall Fear & Greed score (weighted average)
        vix_score = data.get('vix_score', 50)
        momentum_score = data.get('momentum_score', 50)
        put_call_score = data.get('put_call_score', 50)
        safe_haven_score = data.get('safe_haven_score', 50)
        junk_bond_score = data.get('junk_bond_score', 50)

        # Weighted average (similar to CNN Fear & Greed)
        score = round(
            vix_score * 0.25 +           # VIX level
            momentum_score * 0.25 +       # Market momentum
            put_call_score * 0.15 +       # Put/Call (VIX term structure)
            safe_haven_score * 0.20 +     # Safe haven demand
            junk_bond_score * 0.15,       # Junk bond demand
            1
        )

        if score >= 80:
            label, color = 'Extreme Greed', '#22c55e'
        elif score >= 60:
            label, color = 'Greed', '#84cc16'
        elif score >= 40:
            label, color = 'Neutral', '#eab308'
        elif score >= 20:
            label, color = 'Fear', '#f97316'
        else:
            label, color = 'Extreme Fear', '#ef4444'

        response = {
            'ok': True,
            'fear_greed': {
                'score': score,
                'label': label,
                'color': color,
                'components': {
                    'vix': {'score': vix_score, 'label': 'VIX Level', 'value': data.get('vix_val')},
                    'momentum': {'score': momentum_score, 'label': 'Market Momentum',
                                'spy_price': data.get('spy_price'), 'spy_ma125': data.get('spy_ma125')},
                    'put_call': {'score': put_call_score, 'label': 'Put/Call Ratio',
                                'vix_term_ratio': data.get('vix_term_ratio')},
                    'safe_haven': {'score': safe_haven_score, 'label': 'Safe Haven',
                                  'spy_20d': data.get('spy_20d_return'), 'tlt_20d': data.get('tlt_20d_return')},
                    'junk_bond': {'score': junk_bond_score, 'label': 'Junk Bonds',
                                 'hyg_20d': data.get('hyg_20d_return'), 'lqd_20d': data.get('lqd_20d_return')},
                    'volatility': {'score': vix_score, 'label': 'Volatility'}
                }
            },
            'overall_score': score,
            'overall_color': color,
            'overall_label': label,
            'breadth': {
                'breadth_score': data.get('breadth_score', 50),
                'advance_decline_ratio': data.get('advance_decline_ratio', 1.0),
                'new_highs': data.get('new_highs', 100),
                'new_lows': data.get('new_lows', 100),
                'above_20sma': data.get('above_20sma', 50),
                'above_50sma': data.get('above_50sma', 50),
                'above_200sma': data.get('above_200sma', 50),
                'sample_size': data.get('breadth_sample_size', 0)
            },
            'raw_data': {
                'vix': data.get('vix_val'),
                'spy_price': data.get('spy_price'),
                'spy_ma125': data.get('spy_ma125'),
                'vix_term_ratio': data.get('vix_term_ratio'),
                'spy_20d_return': data.get('spy_20d_return'),
                'tlt_20d_return': data.get('tlt_20d_return'),
                'hyg_20d_return': data.get('hyg_20d_return'),
                'lqd_20d_return': data.get('lqd_20d_return')
            },
            'cached': False,
            'timestamp': datetime.now().isoformat()
        }
        _endpoint_cache.set(cache_key, response)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Health endpoint error: {e}")
        return jsonify({'ok': False, 'error': str(e), 'score': 50, 'label': 'Error'})


@app.route('/api/data-providers')
def api_data_providers():
    """Get data provider status and configuration."""
    try:
        from utils.data_providers import check_provider_status, get_available_providers

        status = check_provider_status()
        available = get_available_providers()

        return jsonify({
            'ok': True,
            'providers': status,
            'available': available,
            'total_configured': len(available),
            'description': {
                'finnhub': 'Real-time quotes, news, sentiment (60 req/min free)',
                'tiingo': 'EOD prices, curated news (1000 req/day free)',
                'alpha_vantage': 'Fundamentals, technicals (25 req/day free)',
                'fred': 'Economic indicators (unlimited free)',
                'sec_edgar': 'Official SEC filings (unlimited, no key needed)',
            },
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
        df = normalize_dataframe_columns(df)

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
    app.run(host='0.0.0.0', port=config.port, debug=config.debug)
