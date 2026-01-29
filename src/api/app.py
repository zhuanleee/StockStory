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
from pathlib import Path
import yfinance as yf
import pandas as pd
import threading
import time

from config import config
from utils import (
    get_logger, normalize_dataframe_columns, get_spy_data_cached,
    calculate_rs, send_message, send_photo, validate_webhook_url,
    validate_webhook_signature, ValidationError,
)

logger = get_logger(__name__)

app = Flask(__name__)

# CORS configuration for dashboard
ALLOWED_ORIGINS = [
    'https://zhuanleee.github.io',
    'https://web-production-46562.up.railway.app',
    'http://localhost:5000',
    'http://127.0.0.1:5000',
]

@app.after_request
def add_cors_headers_first(response):
    """Add CORS headers for dashboard requests."""
    origin = request.headers.get('Origin', '')
    # Allow same-origin requests (no Origin header) or explicitly allowed origins
    if not origin or origin in ALLOWED_ORIGINS or origin.endswith('.github.io') or origin.endswith('.up.railway.app'):
        if origin:
            response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# Initialize SocketIO for real-time sync
socketio = None
try:
    from src.sync.socketio_server import init_socketio
    socketio = init_socketio(app)
    logger.info("SocketIO sync enabled")
except ImportError as e:
    logger.warning(f"SocketIO not available: {e}")
except Exception as e:
    logger.warning(f"SocketIO init failed: {e}")


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

# Cache TTLs (in seconds) - increased for better performance
CACHE_TTL = {
    'health': 600,      # 10 minutes (was 5)
    'stories': 900,     # 15 minutes (was 10)
    'scan': 600,        # 10 minutes (was 5)
    'top': 600,         # 10 minutes (was 5)
    'sectors': 900,     # 15 minutes (was 10)
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
    msg += "• `/sentiment NVDA` → AI sentiment analysis\n"
    msg += "• `/sectors` → Sector rotation\n"
    msg += "• `/health` → Fear & Greed + Breadth\n"
    msg += "• `/earnings` → Earnings calendar\n"
    msg += "• `/backtest NVDA` → Signal accuracy\n\n"

    msg += "*🔄 Corporate Actions:*\n"
    msg += "• `/spinoffs` → Stock splits & spinoffs\n"
    msg += "• `/mergers` → M&A deal tracker\n"
    msg += "• `/adddeal VMW AVGO 142` → Track deal\n\n"

    msg += "*📋 SEC EDGAR:*\n"
    msg += "• `/sec NVDA` → Recent SEC filings\n"
    msg += "• `/macheck VMW` → M&A activity scan\n"
    msg += "• `/insider NVDA` → Insider transactions\n\n"

    msg += "*🤖 AI:*\n"
    msg += "• `/briefing` → AI market narrative\n"
    msg += "• `/predict NVDA` → AI prediction\n"
    msg += "• `/coach` → AI coaching\n"
    msg += "• `/patterns` → Best signal patterns\n\n"

    msg += "*🧬 Evolution:*\n"
    msg += "• `/evolution` → Learning status\n"
    msg += "• `/weights` → Adaptive weights\n"
    msg += "• `/discoveredthemes` → Auto-discovered themes\n"
    msg += "• `/accuracy` → Validation metrics\n"
    msg += "• `/correlations` → Learned relationships\n"
    msg += "• `/learningreport` → Full report\n\n"

    msg += "*⚙️ Parameters:*\n"
    msg += "• `/parameters` → 124 learned params\n"
    msg += "• `/paramhealth` → System health\n"
    msg += "• `/experiments` → A/B tests\n\n"

    msg += "*🎯 Themes & Universe:*\n"
    msg += "• `/themes` → Learned theme registry\n"
    msg += "• `/universe` → Dynamic ticker universe\n"
    msg += "• `/themehealth` → Theme system health\n\n"

    msg += "*📈 Google Trends:*\n"
    msg += "• `/trends` → Theme momentum report\n"
    msg += "• `/trends AI chips` → Single keyword trend\n"
    msg += "• `/thememomentum` → Quick theme overview\n\n"

    msg += "*🎯 Theme Intelligence:*\n"
    msg += "• `/themeintel` → Full multi-signal analysis\n"
    msg += "• `/themeradar` → Quick radar view\n"
    msg += "• `/themealerts` → Recent breakout alerts\n"
    msg += "• `/tickertheme NVDA` → Theme boost for ticker\n\n"

    msg += "*🧠 Smart Money:*\n"
    msg += "• `/conviction NVDA` → Multi-signal conviction score\n"
    msg += "• `/conviction` → High-conviction alerts\n"
    msg += "• `/supplychain` → Supply chain opportunities\n"
    msg += "• `/supplychain ai_infrastructure` → Theme supply chain\n"
    msg += "• `/smartmoney` → Combined intelligence\n"
    msg += "• `/discover` → Auto-discover themes\n"
    msg += "• `/institutional` → Institutional flow\n"
    msg += "• `/optionsflow` → Options flow signals\n"
    msg += "• `/rotation` → Rotation forecast\n"
    msg += "• `/peakwarnings` → Peak theme alerts\n\n"

    msg += "*📊 Alternative Data:*\n"
    msg += "• `/patents` → Patent filings analysis\n"
    msg += "• `/patents NVDA` → Company patent lookup\n"
    msg += "• `/contracts` → Gov contract awards\n"
    msg += "• `/contracts nuclear` → Theme contracts\n\n"

    msg += "*⚙️ System:*\n"
    msg += "• `/apistatus` → Check all API integrations\n"

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
    """Run the main scanner using AsyncScanner and save to CSV."""
    send_message(chat_id, "⏳ Running story-first scan (this may take 1-2 minutes)...")

    try:
        import concurrent.futures

        # Quick scan: top 15 theme stocks (reduced for faster completion)
        tickers = [
            'NVDA', 'AMD', 'AVGO',            # AI/Semis
            'MSFT', 'GOOGL', 'META',          # Big Tech
            'TSLA', 'VST',                    # EV/Nuclear
            'PLTR', 'CRWD',                   # Software
            'LLY',                            # Biotech/GLP-1
            'LMT', 'JPM', 'XOM',              # Defense/Finance/Energy
            'SPY',                            # Index
        ]

        def run_async_scan(ticker_list):
            """Run async scan in a separate thread with its own event loop."""
            import asyncio
            from src.core.async_scanner import AsyncScanner

            async def scan():
                scanner = AsyncScanner(max_concurrent=15)
                try:
                    return await scanner.run_scan_async(ticker_list)
                except Exception as e:
                    logger.error(f"Async scan internal error: {e}")
                    raise
                finally:
                    await scanner.close()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(scan())
            except Exception as e:
                logger.error(f"Event loop error: {e}")
                raise
            finally:
                loop.close()

        # Run in thread pool with shorter timeout for Railway
        logger.info(f"Starting scan for {len(tickers)} tickers")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_async_scan, tickers)
            results = future.result(timeout=90)  # 90 second timeout for Railway

        logger.info(f"Scan completed, processing results")

        if isinstance(results, tuple):
            df = results[0]
        else:
            df = results

        if df is not None and len(df) > 0:
            msg = "🔍 *SCAN RESULTS*\n\n"
            for i, row in df.head(15).iterrows():
                ticker = row.get('ticker', 'N/A')
                score = row.get('story_score', 0)
                strength = row.get('story_strength', 'none')
                theme = row.get('hottest_theme', '-') or '-'

                emoji = "🥇" if i < 3 else ("🥈" if i < 6 else "🥉")
                msg += f"{emoji} `{ticker:5}` Score: {score:.0f} | {strength}\n"
                if theme != '-':
                    msg += f"    └ {theme}\n"

            msg += f"\n_Scanned {len(df)} stocks. Results saved._"
            msg += "\n_Dashboard updated at zhuanleee.github.io/stock\\_scanner\\_bot/_"
            send_message(chat_id, msg)
        else:
            send_message(chat_id, "❌ No stocks scanned. Check API keys or try again.")

    except concurrent.futures.TimeoutError:
        logger.error("Scan timed out after 90 seconds")
        send_message(chat_id, "⏰ Scan timed out. Try /top for cached results instead.")
    except Exception as e:
        logger.error(f"Scan error: {e}", exc_info=True)
        send_message(chat_id, f"❌ Scan error: {str(e)[:100]}")


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


def handle_sentiment(chat_id, ticker):
    """Handle /sentiment TICKER command - DeepSeek AI sentiment analysis."""
    ticker = ticker.upper().strip()
    if not ticker:
        send_message(chat_id, "Usage: `/sentiment NVDA`")
        return

    send_message(chat_id, f"⏳ Analyzing sentiment for {ticker}...")
    try:
        from src.sentiment.deepseek_sentiment import get_sentiment_signal

        signal = get_sentiment_signal(ticker, num_articles=15)

        if signal.get('error'):
            send_message(chat_id, f"❌ {signal['error']}")
            return

        # Format response
        bias = signal.get('bias', 'neutral')
        if bias == 'bullish':
            emoji = '🟢'
            bias_text = 'BULLISH'
        elif bias == 'bearish':
            emoji = '🔴'
            bias_text = 'BEARISH'
        else:
            emoji = '⚪'
            bias_text = 'NEUTRAL'

        strength = signal.get('strength', 'weak').upper()
        score = signal.get('signal', 0)
        articles = signal.get('article_count', 0)
        pos_ratio = signal.get('positive_ratio', 0)

        msg = f"{emoji} *SENTIMENT: {ticker}*\n\n"
        msg += f"*Signal:* `{score:+.3f}` ({-1} to +1 scale)\n"
        msg += f"*Bias:* {bias_text} ({strength})\n"
        msg += f"*Articles:* {articles} analyzed\n"
        msg += f"*Positive:* {signal.get('positive_count', 0)} ({pos_ratio:.0%})\n"
        msg += f"*Negative:* {signal.get('negative_count', 0)}\n\n"

        # Show top headlines
        headlines = signal.get('headlines', [])[:5]
        if headlines:
            msg += "*Recent Headlines:*\n"
            for h in headlines:
                h_emoji = '🟢' if h.get('label') == 'positive' else '🔴' if h.get('label') == 'negative' else '⚪'
                title = h.get('title', '')[:60]
                msg += f"{h_emoji} {title}...\n"

        send_message(chat_id, msg)
    except Exception as e:
        logger.error(f"Sentiment error for {ticker}: {e}")
        send_message(chat_id, f"❌ Sentiment error: {str(e)}")


def handle_spinoffs(chat_id):
    """Handle /spinoffs command - Track spinoff opportunities."""
    send_message(chat_id, "⏳ Checking spinoffs...")
    try:
        from src.data.polygon_provider import get_stock_splits_sync

        splits = get_stock_splits_sync(limit=50)

        # Filter for recent/upcoming splits (spinoffs are included)
        msg = "🔄 *RECENT & UPCOMING STOCK SPLITS/SPINOFFS*\n\n"

        if not splits:
            msg += "_No recent splits found_\n\n"
        else:
            count = 0
            for split in splits[:15]:
                ticker = split.get('ticker', '?')
                exec_date = split.get('execution_date', 'TBD')
                ratio = split.get('split_ratio', '?')

                msg += f"• *{ticker}* - {exec_date}\n"
                msg += f"  Ratio: {ratio}\n\n"
                count += 1

            if count == 0:
                msg += "_No splits found_\n\n"

        msg += "*Why track splits/spinoffs?*\n"
        msg += "• Splits attract retail buyers (bullish)\n"
        msg += "• Spinoffs outperform by 10-15% year 1\n"
        msg += "• Index fund selling creates opportunities"

        send_message(chat_id, msg)
    except Exception as e:
        logger.error(f"Spinoffs error: {e}")
        send_message(chat_id, f"❌ Spinoffs error: {str(e)}")


def handle_mergers(chat_id):
    """Handle /mergers command - Track M&A arbitrage opportunities."""
    send_message(chat_id, "⏳ Checking M&A deals...")
    try:
        from src.analysis.corporate_actions import DealTracker

        tracker = DealTracker()
        deals = tracker.get_active_deals()

        msg = "🤝 *M&A DEAL TRACKER*\n\n"

        if not deals:
            msg += "_No deals being tracked_\n\n"
            msg += "*To add a deal:*\n"
            msg += "`/adddeal TARGET ACQUIRER PRICE`\n"
            msg += "Example: `/adddeal VMW AVGO 142.50`\n\n"
        else:
            for deal in deals[:10]:
                target = deal.get('target', '?')
                acquirer = deal.get('acquirer', '?')
                deal_price = deal.get('deal_price', 0)
                status = deal.get('status', 'pending')

                emoji = "🟢" if status == 'approved' else "🟡"
                msg += f"{emoji} *{target}* ← {acquirer}\n"
                msg += f"   Deal: ${deal_price:.2f} | Status: {status}\n\n"

        msg += "*Merger Arbitrage Strategy:*\n"
        msg += "• Spread > 5% = attractive\n"
        msg += "• Spread < 2% = deal likely closing\n"
        msg += "• Watch for regulatory risks"

        send_message(chat_id, msg)
    except Exception as e:
        logger.error(f"Mergers error: {e}")
        send_message(chat_id, f"❌ Mergers error: {str(e)}")


def handle_add_deal(chat_id, args):
    """Handle /adddeal TARGET ACQUIRER PRICE - Add M&A deal to track."""
    parts = args.strip().split()
    if len(parts) < 3:
        send_message(chat_id, "Usage: `/adddeal TARGET ACQUIRER PRICE`\nExample: `/adddeal VMW AVGO 142.50`")
        return

    try:
        target = parts[0].upper()
        acquirer = parts[1].upper()
        price = float(parts[2])

        from src.analysis.corporate_actions import DealTracker

        tracker = DealTracker()
        deal = tracker.add_deal(target, acquirer, price)

        msg = f"✅ *Deal Added*\n\n"
        msg += f"Target: *{target}*\n"
        msg += f"Acquirer: *{acquirer}*\n"
        msg += f"Deal Price: ${price:.2f}\n\n"
        msg += "Use `/mergers` to view all deals"

        send_message(chat_id, msg)
    except ValueError:
        send_message(chat_id, "❌ Invalid price. Use: `/adddeal VMW AVGO 142.50`")
    except Exception as e:
        send_message(chat_id, f"❌ Error: {str(e)}")


def handle_sec_filings(chat_id, ticker):
    """Handle /sec TICKER - Get recent SEC filings."""
    ticker = ticker.upper().strip()
    if not ticker:
        send_message(chat_id, "Usage: `/sec NVDA`")
        return

    send_message(chat_id, f"⏳ Fetching SEC filings for {ticker}...")
    try:
        from src.data.sec_edgar import SECEdgarClient, format_sec_filings_message

        client = SECEdgarClient()
        filings = client.get_company_filings(ticker, days_back=60)

        if not filings:
            send_message(chat_id, f"No recent SEC filings found for {ticker}")
            return

        msg = format_sec_filings_message(filings, f"SEC FILINGS: {ticker}")
        send_message(chat_id, msg)
    except Exception as e:
        logger.error(f"SEC filings error: {e}")
        send_message(chat_id, f"❌ Error: {str(e)}")


def handle_ma_check(chat_id, ticker):
    """Handle /macheck TICKER - Check for M&A activity."""
    ticker = ticker.upper().strip()
    if not ticker:
        send_message(chat_id, "Usage: `/macheck VMW`")
        return

    send_message(chat_id, f"⏳ Analyzing M&A activity for {ticker}...")
    try:
        from src.data.sec_edgar import detect_ma_activity, format_ma_detection_message

        result = detect_ma_activity(ticker)
        msg = format_ma_detection_message(result)
        send_message(chat_id, msg)
    except Exception as e:
        logger.error(f"M&A check error: {e}")
        send_message(chat_id, f"❌ Error: {str(e)}")


def handle_insider(chat_id, ticker):
    """Handle /insider TICKER - Get insider transactions."""
    ticker = ticker.upper().strip()
    if not ticker:
        send_message(chat_id, "Usage: `/insider NVDA`")
        return

    send_message(chat_id, f"⏳ Fetching insider transactions for {ticker}...")
    try:
        from src.data.sec_edgar import SECEdgarClient

        client = SECEdgarClient()
        transactions = client.get_insider_transactions(ticker, days_back=90)

        if not transactions:
            send_message(chat_id, f"No recent insider transactions for {ticker}")
            return

        msg = f"👤 *INSIDER TRANSACTIONS: {ticker}*\n\n"

        for t in transactions[:15]:
            msg += f"• {t['date']} - {t['description'][:40]}\n"

        msg += f"\n_Showing last {len(transactions[:15])} Form 4 filings_"
        send_message(chat_id, msg)
    except Exception as e:
        logger.error(f"Insider error: {e}")
        send_message(chat_id, f"❌ Error: {str(e)}")


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
# EVOLUTION ENGINE TELEGRAM COMMANDS
# =============================================================================

def handle_evolution(chat_id):
    """Handle /evolution command - Show learning system status."""
    send_message(chat_id, "🧬 Checking evolution status...")
    try:
        from evolution_engine import get_evolution_status

        status = get_evolution_status()

        msg = "🧬 *EVOLUTION ENGINE*\n\n"
        msg += f"*Cycle:* #{status.get('evolution_cycle', 0)}\n"
        msg += f"*Last Run:* {status.get('last_evolution', 'Never')[:16] if status.get('last_evolution') else 'Never'}\n\n"

        # Validation metrics
        metrics = status.get('validation_metrics', {})
        accuracy = metrics.get('overall_accuracy')
        if accuracy:
            msg += f"*Accuracy:* {accuracy:.1f}%\n"
            ci = metrics.get('confidence_interval_95', [])
            if ci:
                msg += f"95% CI: [{ci[0]:.1f}%, {ci[1]:.1f}%]\n"
            cal = metrics.get('calibration_score')
            if cal:
                msg += f"*Calibration:* {cal*100:.0f}%\n"

        # Weight changes
        changes = status.get('weight_changes', {})
        if changes:
            msg += "\n*Weight Changes:*\n"
            for k, v in list(changes.items())[:5]:
                arrow = "↑" if v > 0 else "↓"
                msg += f"• {k}: {arrow}{abs(v):.1f}pp\n"

        # Discovered themes
        themes_count = status.get('discovered_themes_count', 0)
        msg += f"\n*Discovered Themes:* {themes_count}\n"

        # Correlations
        corr_count = status.get('correlations_count', 0)
        msg += f"*Learned Correlations:* {corr_count}\n"

        send_message(chat_id, msg)
    except ImportError:
        send_message(chat_id, "Evolution engine not available")
    except Exception as e:
        send_message(chat_id, f"Evolution error: {str(e)}")


def handle_weights(chat_id):
    """Handle /weights command - Show adaptive weights."""
    try:
        from evolution_engine import load_learning_state, DEFAULT_WEIGHTS, AdaptiveScoringEngine

        state = load_learning_state()
        engine = AdaptiveScoringEngine()
        current = state['adaptive_weights']['current']
        changes = engine.get_weight_changes()

        msg = "⚖️ *ADAPTIVE WEIGHTS*\n\n"
        msg += "*Current vs Default:*\n"

        for key in sorted(current.keys()):
            curr_val = current.get(key, 0) * 100
            def_val = DEFAULT_WEIGHTS.get(key, 0) * 100
            change = changes.get(key, 0)

            if change > 0:
                arrow = "↑"
                indicator = "🟢"
            elif change < 0:
                arrow = "↓"
                indicator = "🔴"
            else:
                arrow = "="
                indicator = "⚪"

            msg += f"{indicator} `{key:15}` {curr_val:5.1f}% ({arrow}{abs(change):.1f}pp)\n"

        # Regime weights summary
        by_regime = state['adaptive_weights']['by_regime']
        if any(by_regime.values()):
            msg += "\n*Regime Adjustments:*\n"
            for regime, weights in by_regime.items():
                if weights:
                    msg += f"• {regime}: configured\n"

        send_message(chat_id, msg)
    except ImportError:
        send_message(chat_id, "Evolution engine not available")
    except Exception as e:
        send_message(chat_id, f"Weights error: {str(e)}")


def handle_discovered_themes(chat_id):
    """Handle /themes command for discovered themes."""
    try:
        from evolution_engine import get_discovered_themes, load_learning_state

        themes = get_discovered_themes()
        state = load_learning_state()

        msg = "🔮 *DISCOVERED THEMES*\n\n"

        if not themes:
            msg += "_No themes discovered yet._\n"
            msg += "_The system learns from news clusters and correlation patterns._"
        else:
            for theme in themes[:10]:
                stage = theme.get('lifecycle_stage', 'unknown')
                if stage == 'early':
                    emoji = "🌱"
                elif stage == 'middle':
                    emoji = "🌿"
                elif stage == 'peak':
                    emoji = "🌳"
                else:
                    emoji = "🍂"

                confidence = theme.get('confidence', 0) * 100
                msg += f"{emoji} *{theme['name']}*\n"
                msg += f"   Stage: {stage} | Conf: {confidence:.0f}%\n"
                stocks = theme.get('stocks', [])[:5]
                if stocks:
                    msg += f"   `{', '.join(stocks)}`\n"
                msg += "\n"

        # Show retired count
        retired = len(state['discovered_themes'].get('retired_themes', []))
        if retired:
            msg += f"\n_Retired themes: {retired}_"

        send_message(chat_id, msg)
    except ImportError:
        send_message(chat_id, "Evolution engine not available")
    except Exception as e:
        send_message(chat_id, f"Themes error: {str(e)}")


def handle_accuracy(chat_id):
    """Handle /accuracy command - Show validation metrics."""
    try:
        from evolution_engine import get_accuracy_report

        report = get_accuracy_report()

        msg = "📊 *ACCURACY REPORT*\n\n"

        # Overall accuracy
        accuracy = report.get('accuracy', {})
        if accuracy.get('accuracy'):
            msg += f"*Overall:* {accuracy['accuracy']:.1f}%\n"
            ci = accuracy.get('confidence_interval_95', [])
            if ci:
                msg += f"95% CI: [{ci[0]:.1f}%, {ci[1]:.1f}%]\n"
            msg += f"Trades: {accuracy.get('total', 0)} ({accuracy.get('wins', 0)}W / {accuracy.get('losses', 0)}L)\n"

        # Calibration
        calibration = report.get('calibration', {})
        if calibration.get('calibration_score'):
            msg += f"\n*Calibration:* {calibration['calibration_score']:.0f}% ({calibration.get('interpretation', '')})\n"

            buckets = calibration.get('buckets', {})
            if buckets:
                msg += "\n*By Confidence:*\n"
                for bucket, data in list(buckets.items())[:5]:
                    msg += f"• {bucket}: pred={data['predicted']:.0f}%, actual={data['actual']:.0f}%\n"

        # Degradation check
        degradation = report.get('degradation', {})
        if degradation.get('recent_accuracy'):
            msg += f"\n*Recent vs Baseline:*\n"
            msg += f"Recent: {degradation['recent_accuracy']:.1f}%\n"
            msg += f"Baseline: {degradation['baseline_accuracy']:.1f}%\n"
            if degradation.get('degradation_detected'):
                msg += "⚠️ *Performance degradation detected*"
            else:
                msg += "✅ Performance stable"

        send_message(chat_id, msg)
    except ImportError:
        send_message(chat_id, "Evolution engine not available")
    except Exception as e:
        send_message(chat_id, f"Accuracy error: {str(e)}")


def handle_correlations(chat_id):
    """Handle /correlations command - Show learned correlations."""
    try:
        from evolution_engine import get_learned_correlations

        data = get_learned_correlations()
        pairs = data.get('pairs', {})
        patterns = data.get('propagation_patterns', {})

        msg = "🔗 *LEARNED CORRELATIONS*\n\n"

        if not pairs and not patterns:
            msg += "_No correlations learned yet._\n"
            msg += "_Run scans to build correlation data._"
        else:
            if pairs:
                msg += "*Top Pairs:*\n"
                sorted_pairs = sorted(pairs.items(), key=lambda x: abs(x[1].get('correlation', 0)), reverse=True)
                for key, data in sorted_pairs[:8]:
                    corr = data.get('correlation', 0)
                    t1 = data.get('ticker1', key.split('_')[0])
                    t2 = data.get('ticker2', key.split('_')[1] if '_' in key else '?')
                    arrow = "↔" if corr > 0.8 else "~"
                    msg += f"• `{t1}` {arrow} `{t2}`: r={corr:.2f}\n"

            if patterns:
                msg += "\n*Wave Patterns:*\n"
                for key, pattern in list(patterns.items())[:5]:
                    msg += f"• {pattern.get('driver', key)}: "
                    msg += f"T1={pattern.get('tier1_avg_lag', 0):.1f}d, "
                    msg += f"T2={pattern.get('tier2_avg_lag', 0):.1f}d\n"

        send_message(chat_id, msg)
    except ImportError:
        send_message(chat_id, "Evolution engine not available")
    except Exception as e:
        send_message(chat_id, f"Correlations error: {str(e)}")


def handle_learning_report(chat_id):
    """Handle /learningreport command - Comprehensive learning report."""
    send_message(chat_id, "📝 Generating learning report...")
    try:
        from evolution_engine import (
            get_evolution_status, get_accuracy_report,
            get_discovered_themes, get_learned_correlations
        )

        status = get_evolution_status()
        accuracy_report = get_accuracy_report()
        themes = get_discovered_themes()
        correlations = get_learned_correlations()

        msg = "📝 *LEARNING REPORT*\n\n"

        # System Status
        msg += f"*System Status:*\n"
        msg += f"• Cycle: #{status.get('evolution_cycle', 0)}\n"
        msg += f"• Last Run: {status.get('last_evolution', 'Never')[:10] if status.get('last_evolution') else 'Never'}\n\n"

        # Accuracy Summary
        accuracy = accuracy_report.get('accuracy', {})
        if accuracy.get('accuracy'):
            msg += f"*Accuracy:* {accuracy['accuracy']:.1f}%"
            ci = accuracy.get('confidence_interval_95', [])
            if ci:
                msg += f" [{ci[0]:.1f}-{ci[1]:.1f}%]"
            msg += "\n"

        # Calibration
        cal = accuracy_report.get('calibration', {})
        if cal.get('calibration_score'):
            msg += f"*Calibration:* {cal['calibration_score']:.0f}% ({cal.get('interpretation', '')})\n"

        # Degradation
        deg = accuracy_report.get('degradation', {})
        if deg.get('degradation_detected'):
            msg += "⚠️ *Performance degradation detected*\n"

        msg += "\n"

        # Weight Changes
        changes = status.get('weight_changes', {})
        if changes:
            msg += "*Weight Adjustments:*\n"
            for k, v in sorted(changes.items(), key=lambda x: abs(x[1]), reverse=True)[:3]:
                arrow = "↑" if v > 0 else "↓"
                msg += f"• {k}: {arrow}{abs(v):.1f}pp\n"
            msg += "\n"

        # Discovered Themes
        msg += f"*Discovered Themes:* {len(themes)}\n"
        for theme in themes[:3]:
            msg += f"• {theme['name']} ({theme.get('lifecycle_stage', 'unknown')})\n"

        # Correlations
        pairs = correlations.get('pairs', {})
        msg += f"\n*Learned Correlations:* {len(pairs)}\n"

        msg += "\n_Use individual commands for details._"

        send_message(chat_id, msg)
    except ImportError:
        send_message(chat_id, "Evolution engine not available")
    except Exception as e:
        send_message(chat_id, f"Report error: {str(e)}")


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
    elif text_lower.startswith('/sentiment '):
        handle_sentiment(chat_id, text[11:].strip())
    elif text_lower == '/sectors':
        handle_sectors(chat_id)
    elif text_lower == '/health':
        handle_health(chat_id)
    elif text_lower == '/earnings':
        handle_earnings(chat_id)
    elif text_lower.startswith('/backtest '):
        handle_backtest(chat_id, text[10:].strip())

    # Corporate Actions
    elif text_lower == '/spinoffs':
        handle_spinoffs(chat_id)
    elif text_lower == '/mergers':
        handle_mergers(chat_id)
    elif text_lower.startswith('/adddeal '):
        handle_add_deal(chat_id, text[9:].strip())
    elif text_lower.startswith('/sec '):
        handle_sec_filings(chat_id, text[5:].strip())
    elif text_lower.startswith('/macheck '):
        handle_ma_check(chat_id, text[9:].strip())
    elif text_lower.startswith('/insider '):
        handle_insider(chat_id, text[9:].strip())

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

    # Evolution Engine Commands
    elif text_lower == '/evolution':
        handle_evolution(chat_id)
    elif text_lower == '/weights':
        handle_weights(chat_id)
    elif text_lower == '/discoveredthemes':
        handle_discovered_themes(chat_id)
    elif text_lower == '/accuracy':
        handle_accuracy(chat_id)
    elif text_lower == '/correlations':
        handle_correlations(chat_id)
    elif text_lower == '/learningreport':
        handle_learning_report(chat_id)

    # Parameter Learning Commands
    elif text_lower == '/parameters':
        handle_parameters(chat_id)
    elif text_lower == '/paramhealth':
        handle_param_health(chat_id)
    elif text_lower == '/experiments':
        handle_experiments(chat_id)

    # Theme Registry & Universe Commands
    elif text_lower == '/themes':
        handle_themes(chat_id)
    elif text_lower == '/universe':
        handle_universe(chat_id)
    elif text_lower == '/themehealth':
        handle_themehealth(chat_id)

    # Google Trends Commands
    elif text_lower == '/trends':
        handle_trends(chat_id)
    elif text_lower.startswith('/trends '):
        handle_trends(chat_id, text[8:].strip())
    elif text_lower == '/thememomentum':
        handle_thememomentum(chat_id)

    # Theme Intelligence Hub Commands
    elif text_lower == '/themeintel':
        handle_themeintel(chat_id)
    elif text_lower == '/themealerts':
        handle_themealerts(chat_id)
    elif text_lower == '/themeradar':
        handle_themeradar(chat_id)
    elif text_lower.startswith('/tickertheme '):
        handle_tickertheme(chat_id, text[13:].strip())

    # Advanced Intelligence Commands
    elif text_lower == '/discover':
        handle_discover(chat_id)
    elif text_lower == '/institutional':
        handle_institutional(chat_id)
    elif text_lower == '/optionsflow':
        handle_optionsflow(chat_id)
    elif text_lower.startswith('/optionsflow '):
        handle_optionsflow(chat_id, text[13:].strip())
    elif text_lower == '/rotation':
        handle_rotation(chat_id)
    elif text_lower == '/peakwarnings':
        handle_peakwarnings(chat_id)
    elif text_lower == '/smartmoney':
        handle_smartmoney(chat_id)
    elif text_lower == '/conviction':
        handle_conviction(chat_id)
    elif text_lower.startswith('/conviction '):
        handle_conviction(chat_id, text[12:].strip())

    # Alternative Data Commands
    elif text_lower == '/patents':
        handle_patents(chat_id)
    elif text_lower.startswith('/patents '):
        handle_patents(chat_id, text[9:].strip())
    elif text_lower == '/contracts':
        handle_contracts(chat_id)
    elif text_lower.startswith('/contracts '):
        handle_contracts(chat_id, text[11:].strip())

    # Supply Chain Discovery
    elif text_lower == '/supplychain':
        handle_supplychain(chat_id)
    elif text_lower.startswith('/supplychain '):
        handle_supplychain(chat_id, text[13:].strip())

    # System Commands
    elif text_lower == '/apistatus':
        handle_apistatus(chat_id)

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
        'telegram_configured': bool(os.environ.get('TELEGRAM_BOT_TOKEN')),
        'chat_id_configured': bool(os.environ.get('TELEGRAM_CHAT_ID')),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/dashboard')
def serve_dashboard():
    """Serve the interactive dashboard."""
    try:
        from flask import Response
        from src.dashboard.dashboard import DASHBOARD_HTML

        # Get API base URL for the dashboard
        # Handle reverse proxy (Railway) - check X-Forwarded-Proto header
        proto = request.headers.get('X-Forwarded-Proto', request.scheme)
        host = request.host
        api_base = f"{proto}://{host}/api"

        # Replace the default API_BASE in the HTML
        html = DASHBOARD_HTML.replace(
            "const API_BASE = 'https://web-production-46562.up.railway.app/api';",
            f"const API_BASE = '{api_base}';"
        )

        # Apply template variables (double braces as used in dashboard.py)
        html = html.replace('{{BOT_USERNAME}}', 'Stocks_Story_Bot')
        html = html.replace('{{TOTAL_SCANNED}}', '0')
        html = html.replace('{{HOT_COUNT}}', '0')
        html = html.replace('{{DEVELOPING_COUNT}}', '0')
        html = html.replace('{{WATCHLIST_COUNT}}', '0')
        html = html.replace('{{THEMES_PILLS}}', '')
        html = html.replace('{{ALL_THEME_PILLS}}', '')
        html = html.replace('{{THEME_STOCKS}}', '')
        html = html.replace('{{THEME_CARDS}}', '')
        html = html.replace('{{THEME_OPTIONS}}', '')
        html = html.replace('{{SCAN_ROWS}}', '')

        return Response(html, mimetype='text/html')

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram webhook."""
    global processed_updates

    # Verify webhook signature (log but don't reject for now)
    signature = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
    if not validate_webhook_signature(request.data, signature):
        logger.warning("Webhook signature validation failed - processing anyway")
        # Don't reject - allow message processing

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
                          '/earnings', '/briefing', '/coach', '/top', '/health', '/sentiment',
                          '/thememomentum', '/trends', '/themeintel', '/themeradar',
                          '/discover', '/institutional', '/optionsflow', '/rotation', '/smartmoney',
                          '/patents', '/contracts', '/supplychain', '/conviction']

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


@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Handle CORS preflight OPTIONS requests for all API routes."""
    return '', 204


@app.route('/api', methods=['OPTIONS'])
def handle_api_options():
    """Handle OPTIONS for /api root."""
    return '', 204


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
    """Get scan results from cached CSV file (fast, no timeout)."""
    cache_key = 'scan'

    # Check cache first
    cached_data, is_cached = _endpoint_cache.get(cache_key, CACHE_TTL['scan'])
    if is_cached:
        cached_data['cached'] = True
        return jsonify(cached_data)

    try:
        # Load from latest scan CSV file (generated by scheduled scans)
        from pathlib import Path
        scan_files = list(Path('.').glob('scan_*.csv'))

        if not scan_files:
            return jsonify({
                'ok': True,
                'stocks': [],
                'total': 0,
                'message': 'No scan results available. Run scan via Telegram or CLI.',
                'timestamp': datetime.now().isoformat(),
                'cached': False
            })

        # Get most recent scan file
        latest_scan = max(scan_files, key=lambda x: x.stat().st_mtime)
        df = pd.read_csv(latest_scan)

        # Get scan timestamp from file modification time
        scan_time = datetime.fromtimestamp(latest_scan.stat().st_mtime)

        # Format stocks for dashboard (handle NaN values)
        import math
        def safe_float(val, default=0):
            try:
                f = float(val)
                return default if math.isnan(f) else f
            except (TypeError, ValueError):
                return default

        def safe_int(val, default=0):
            try:
                f = float(val)
                return default if math.isnan(f) else int(f)
            except (TypeError, ValueError):
                return default

        def safe_str(val, default=None):
            if pd.isna(val):
                return default
            return str(val) if val else default

        stocks = []
        for _, row in df.head(100).iterrows():
            stocks.append({
                'ticker': safe_str(row.get('ticker', ''), ''),
                'story_score': safe_float(row.get('story_score', 0)),
                'story_strength': safe_str(row.get('story_strength', 'none'), 'none'),
                'hottest_theme': safe_str(row.get('hottest_theme', None), None),
                'change_pct': safe_float(row.get('change_pct', 0)),
                'volume': safe_int(row.get('volume', 0)),
                'rs_rating': safe_float(row.get('rs_rating', 0)),
                'sector': safe_str(row.get('sector', 'Unknown'), 'Unknown'),
            })

        # Count by strength
        hot_count = len([s for s in stocks if s['story_strength'] == 'hot'])
        developing_count = len([s for s in stocks if s['story_strength'] == 'developing'])
        watchlist_count = len([s for s in stocks if s['story_strength'] == 'watchlist'])

        # Theme summary
        themes = {}
        for s in stocks:
            theme = s.get('hottest_theme')
            if theme:
                if theme not in themes:
                    themes[theme] = {'name': theme, 'count': 0, 'total_score': 0}
                themes[theme]['count'] += 1
                themes[theme]['total_score'] += s.get('story_score', 0)

        active_themes = sorted([
            {
                'name': t['name'],
                'stock_count': t['count'],
                'avg_score': round(t['total_score'] / t['count'], 1) if t['count'] > 0 else 0
            }
            for t in themes.values()
        ], key=lambda x: x['avg_score'], reverse=True)[:10]

        response = {
            'ok': True,
            'stocks': stocks,
            'total': len(df),
            'themes': active_themes,
            'stats': {
                'hot': hot_count,
                'developing': developing_count,
                'watchlist': watchlist_count,
            },
            'scan_file': latest_scan.name,
            'scan_time': scan_time.isoformat(),
            'timestamp': datetime.now().isoformat(),
            'cached': False
        }
        _endpoint_cache.set(cache_key, response)
        return jsonify(response)

    except Exception as e:
        logger.error(f"Scan endpoint error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/scan/trigger', methods=['POST', 'GET'])
def api_scan_trigger():
    """
    Trigger a scan and save results to CSV.

    Query params:
        tickers: Comma-separated list (custom tickers)
        mode: 'quick' (20 stocks), 'indices' (S&P500+NASDAQ100), 'full' (Polygon 300M+ mcap)
              Default: 'indices'
        min_mcap: Minimum market cap in millions (default: 300 for full mode)
    """
    import concurrent.futures

    tickers_param = request.args.get('tickers', '')
    mode = request.args.get('mode', 'indices').lower()
    min_mcap = int(request.args.get('min_mcap', 300)) * 1_000_000  # Convert to dollars

    # Legacy support: full=true -> mode=full
    if request.args.get('full', 'false').lower() == 'true':
        mode = 'full'

    try:
        # Determine tickers to scan
        if tickers_param:
            tickers = [t.strip().upper() for t in tickers_param.split(',') if t.strip()]
            logger.info(f"Custom scan: {len(tickers)} tickers")
        elif mode == 'full':
            # Full Polygon universe with market cap filter
            from src.data.universe_manager import get_universe_manager
            um = get_universe_manager()
            tickers = um.get_scan_universe(use_polygon_full=True, min_market_cap=min_mcap)
            logger.info(f"Full scan: {len(tickers)} tickers (min mcap ${min_mcap/1e6:.0f}M)")
        elif mode == 'indices':
            # S&P 500 + NASDAQ 100 (faster, ~600 stocks)
            from src.data.universe_manager import get_universe_manager
            um = get_universe_manager()
            tickers = um.get_scan_universe(use_polygon_full=False)
            logger.info(f"Indices scan: {len(tickers)} tickers (S&P500 + NASDAQ100)")
        else:
            # Quick scan: top theme stocks
            tickers = [
                'NVDA', 'AMD', 'AVGO', 'TSM', 'MSFT', 'GOOGL', 'META', 'AAPL',
                'TSLA', 'VST', 'CEG', 'PLTR', 'CRWD', 'NET', 'LLY', 'NVO',
                'LMT', 'JPM', 'XOM', 'SPY',
            ]
            logger.info(f"Quick scan: {len(tickers)} tickers")

        def run_async_scan(ticker_list):
            """Run async scan in a separate thread with its own event loop."""
            import asyncio
            from src.core.async_scanner import AsyncScanner

            async def scan():
                # Adjust concurrency based on scan size
                max_concurrent = 50 if len(ticker_list) > 100 else 25
                scanner = AsyncScanner(max_concurrent=max_concurrent)
                try:
                    return await scanner.run_scan_async(ticker_list)
                except Exception as e:
                    logger.error(f"Async scan error: {e}")
                    raise
                finally:
                    await scanner.close()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(scan())
            finally:
                loop.close()

        # Longer timeout for larger scans
        timeout = 600 if len(tickers) > 100 else 300  # 10 min for large, 5 min for small

        # Run in thread pool to avoid event loop conflicts with gunicorn
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_async_scan, tickers)
            results = future.result(timeout=timeout)

        if isinstance(results, tuple):
            df = results[0]
        else:
            df = results

        return jsonify({
            'ok': True,
            'scanned': len(df) if df is not None else 0,
            'mode': mode,
            'universe_size': len(tickers),
            'message': f'Scan complete. {len(df) if df is not None else 0} stocks saved to CSV.',
            'timestamp': datetime.now().isoformat()
        })

    except concurrent.futures.TimeoutError:
        return jsonify({'ok': False, 'error': f'Scan timed out ({len(tickers)} tickers). Try mode=quick.'})
    except Exception as e:
        logger.error(f"Scan trigger error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/ticker/<ticker>')
def api_ticker(ticker):
    """Get ticker analysis using Polygon.io."""
    try:
        ticker = ticker.upper()

        # First check if we have data in latest scan CSV
        from pathlib import Path
        scan_files = list(Path('.').glob('scan_*.csv'))

        stock_data = None
        if scan_files:
            latest_scan = max(scan_files, key=lambda x: x.stat().st_mtime)
            df_scan = pd.read_csv(latest_scan)
            match = df_scan[df_scan['ticker'] == ticker]
            if not match.empty:
                row = match.iloc[0]
                stock_data = {
                    'ticker': ticker,
                    'story_score': float(row.get('story_score', 0)),
                    'story_strength': row.get('story_strength', 'none'),
                    'hottest_theme': row.get('hottest_theme', None),
                    'change_pct': float(row.get('change_pct', 0)),
                    'volume': int(row.get('volume', 0)),
                    'rs_rating': float(row.get('rs_rating', 0)),
                    'sector': row.get('sector', 'Unknown'),
                }

        # Get real-time data from Polygon
        polygon_key = os.environ.get('POLYGON_API_KEY', '')
        if polygon_key:
            try:
                from src.data.polygon_provider import get_price_data_sync, get_ticker_details_sync
                df = get_price_data_sync(ticker, days=90)

                if df is not None and len(df) >= 20:
                    close = df['Close']
                    current = float(close.iloc[-1])
                    sma_20 = float(close.rolling(20).mean().iloc[-1])
                    sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else sma_20

                    # RS calculation using cached SPY data
                    spy_df, spy_returns = get_spy_data_cached()
                    rs_data = calculate_rs(df, spy_returns)
                    rs = rs_data['rs_composite']

                    vol_ratio = float(df['Volume'].iloc[-1] / df['Volume'].iloc[-20:].mean()) if df['Volume'].iloc[-20:].mean() > 0 else 1.0

                    result = {
                        'ok': True,
                        'stock': {
                            'ticker': ticker,
                            'price': current,
                            'sma_20': sma_20,
                            'sma_50': sma_50,
                            'rs_rating': rs,
                            'vol_ratio': vol_ratio,
                            'above_20sma': current > sma_20,
                            'above_50sma': current > sma_50,
                        },
                        'timestamp': datetime.now().isoformat()
                    }

                    # Merge with scan data if available
                    if stock_data:
                        result['stock'].update(stock_data)

                    # Get sector from Polygon details
                    try:
                        details = get_ticker_details_sync(ticker)
                        if details:
                            result['stock']['sector'] = details.get('sector', result['stock'].get('sector', 'Unknown'))
                            result['stock']['name'] = details.get('name', ticker)
                    except Exception:
                        pass

                    return jsonify(result)
            except Exception as e:
                logger.warning(f"Polygon ticker fetch failed: {e}")

        # Fallback to scan data only
        if stock_data:
            return jsonify({
                'ok': True,
                'stock': stock_data,
                'source': 'cached_scan',
                'timestamp': datetime.now().isoformat()
            })

        # Last resort: try to get basic details from Polygon
        if polygon_key:
            try:
                from src.data.polygon_provider import get_ticker_details_sync, get_previous_close_sync
                details = get_ticker_details_sync(ticker)
                prev = get_previous_close_sync(ticker)

                if details or prev:
                    result = {
                        'ok': True,
                        'stock': {
                            'ticker': ticker,
                            'name': details.get('name', ticker) if details else ticker,
                            'sector': details.get('sector', 'Unknown') if details else 'Unknown',
                            'price': prev.get('close', 0) if prev else 0,
                            'change_pct': 0,
                            'volume': prev.get('volume', 0) if prev else 0,
                        },
                        'source': 'polygon_basic',
                        'timestamp': datetime.now().isoformat()
                    }
                    return jsonify(result)
            except Exception as e:
                logger.warning(f"Polygon basic fetch failed: {e}")

        return jsonify({'ok': False, 'error': 'No data available'})

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


def _get_simple_news_sentiment(tickers):
    """Simple news sentiment using yfinance only."""
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
                    # Handle new yfinance format where content is nested
                    content = item.get('content', item)
                    title = str(content.get('title', '')).lower()
                    summary = str(content.get('summary', '')).lower()

                    # Get provider info
                    provider = content.get('provider', {})
                    source = provider.get('displayName', '') if isinstance(provider, dict) else str(provider)

                    headlines.append({
                        'title': content.get('title', ''),
                        'source': source
                    })

                    # Combine title and summary for sentiment
                    text = title + ' ' + summary

                    # Simple sentiment check
                    bullish_words = ['beat', 'surge', 'gain', 'rise', 'jump', 'high', 'record', 'growth', 'strong', 'upgrade', 'buy', 'bullish', 'trillion', 'demand']
                    bearish_words = ['miss', 'drop', 'fall', 'low', 'down', 'weak', 'concern', 'risk', 'decline', 'downgrade', 'sell', 'bearish', 'warning', 'cut']

                    if any(w in text for w in bullish_words):
                        bullish_count += 1
                    if any(w in text for w in bearish_words):
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
    """Get news sentiment with caching - using yfinance for reliability."""
    cache_key = 'news'

    # Check cache first (15 min cache)
    cached_data, is_cached = _endpoint_cache.get(cache_key, 900)
    if is_cached:
        cached_data['cached'] = True
        return jsonify(cached_data)

    tickers = ['NVDA', 'AAPL', 'TSLA', 'META', 'AMD', 'MSFT']

    # Use yfinance-based sentiment for reliability
    try:
        sentiment = _get_simple_news_sentiment(tickers)
        response = {
            'ok': True,
            'sentiment': sentiment,
            'source': 'yfinance',
            'cached': False,
            'timestamp': datetime.now().isoformat()
        }
        _endpoint_cache.set(cache_key, response)
        return jsonify(response)
    except Exception as e:
        logger.error(f"News sentiment failed: {e}")
        return jsonify({
            'ok': False,
            'sentiment': [],
            'error': str(e),
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

        if briefing is None:
            # DeepSeek API likely unavailable, return fallback
            return jsonify({
                'ok': True,
                'briefing': {
                    'headline': 'Market Analysis Unavailable',
                    'market_mood': 'unknown',
                    'main_narrative': 'AI briefing temporarily unavailable. Check back later or ensure DEEPSEEK_API_KEY is configured.',
                    'theme_connections': '',
                    'sector_rotation_insight': '',
                    'smart_money_signal': '',
                    'key_opportunity': None,
                    'key_risk': None,
                    'tomorrow_watch': [],
                    'contrarian_take': ''
                },
                'fallback': True,
                'timestamp': datetime.now().isoformat()
            })

        if isinstance(briefing, dict) and briefing.get('error'):
            return jsonify({
                'ok': False,
                'error': briefing.get('error'),
                'timestamp': datetime.now().isoformat()
            })

        return jsonify({
            'ok': True,
            'briefing': briefing,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        logger.error(f"Briefing import error: {e}")
        return jsonify({'ok': False, 'error': f'Module not available: {e}'})
    except Exception as e:
        logger.error(f"Briefing error: {e}")
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


# =============================================================================
# ECOSYSTEM API ENDPOINTS
# =============================================================================


@app.route('/api/ecosystem/<ticker>')
def api_ecosystem(ticker):
    """Get ecosystem for a stock."""
    try:
        from ecosystem_intelligence import get_ecosystem

        ticker = ticker.upper()
        depth = request.args.get('depth', 2, type=int)

        ecosystem = get_ecosystem(ticker, depth=min(depth, 3))

        return jsonify({
            'ok': True,
            'ecosystem': ecosystem,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Ecosystem endpoint error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/ecosystem/opportunities')
def api_ecosystem_opportunities():
    """Get ecosystem opportunities (lagging plays)."""
    try:
        from ecosystem_intelligence import generate_ecosystem_alerts, get_stocks_in_play

        min_gap = request.args.get('min_gap', 10, type=int)

        # Get current scores
        scores_dict = {}
        try:
            import glob
            scan_files = sorted(glob.glob('scan_*.csv'), reverse=True)
            if scan_files:
                df = pd.read_csv(scan_files[0])
                scores_dict = df.set_index('ticker')['composite_score'].to_dict()
        except Exception:
            pass

        # Get in-play stocks
        in_play = get_stocks_in_play(min_score=70, scores_dict=scores_dict)

        # Generate alerts
        alerts = generate_ecosystem_alerts(
            drivers=[s['ticker'] for s in in_play[:10]],
            scores_dict=scores_dict,
        )

        # Filter by min_gap for lagging supplier alerts
        opportunities = [
            a for a in alerts
            if a.get('type') == 'LAGGING_SUPPLIER' and a.get('gap', 0) >= min_gap
        ]

        return jsonify({
            'ok': True,
            'opportunities': opportunities,
            'in_play': in_play[:10],
            'total_alerts': len(alerts),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Opportunities endpoint error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/ecosystem/wave/<ticker>')
def api_ecosystem_wave(ticker):
    """Get wave propagation tracking for a driver."""
    try:
        from ecosystem_intelligence import calculate_wave_propagation, get_active_waves

        ticker = ticker.upper()
        event = request.args.get('event', 'catalyst')
        move_pct = request.args.get('move', 5.0, type=float)

        # Get scores
        scores_dict = {}
        try:
            import glob
            scan_files = sorted(glob.glob('scan_*.csv'), reverse=True)
            if scan_files:
                df = pd.read_csv(scan_files[0])
                scores_dict = df.set_index('ticker')['composite_score'].to_dict()
        except Exception:
            pass

        wave = calculate_wave_propagation(
            ticker,
            event=event,
            origin_move_pct=move_pct,
            scores_dict=scores_dict,
        )

        return jsonify({
            'ok': True,
            'wave': wave,
            'active_waves': get_active_waves(),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Wave endpoint error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/themes/lifecycle')
def api_themes_lifecycle():
    """Get theme lifecycle status."""
    try:
        from ecosystem_intelligence import (
            detect_emerging_subthemes, detect_rotation_signals
        )
        from story_scorer import THEMES

        # Get scores
        scores_dict = {}
        try:
            import glob
            scan_files = sorted(glob.glob('scan_*.csv'), reverse=True)
            if scan_files:
                df = pd.read_csv(scan_files[0])
                scores_dict = df.set_index('ticker')['composite_score'].to_dict()
        except Exception:
            pass

        themes_status = []
        for theme_id, theme in THEMES.items():
            # Get theme stocks scores
            all_tickers = (
                theme.get('drivers', []) +
                theme.get('beneficiaries', []) +
                theme.get('picks_shovels', [])
            )
            theme_scores = [scores_dict.get(t, 0) for t in all_tickers if t in scores_dict]
            avg_score = sum(theme_scores) / len(theme_scores) if theme_scores else 0

            themes_status.append({
                'theme_id': theme_id,
                'name': theme['name'],
                'stage': theme.get('stage', 'unknown'),
                'avg_score': round(avg_score, 1),
                'stock_count': len(all_tickers),
                'sub_themes': list(theme.get('sub_themes', {}).keys()),
            })

        themes_status.sort(key=lambda x: -x['avg_score'])

        # Get sub-theme details for top theme
        sub_themes = []
        if themes_status:
            top_theme = themes_status[0]['theme_id']
            sub_themes = detect_emerging_subthemes(top_theme, scores_dict=scores_dict)

        # Get rotation signals
        rotations = detect_rotation_signals()

        return jsonify({
            'ok': True,
            'themes': themes_status,
            'sub_themes': sub_themes,
            'rotations': rotations,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Themes lifecycle endpoint error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/watchlist/in-play')
def api_watchlist_in_play():
    """Get stocks currently in play."""
    try:
        from ecosystem_intelligence import get_stocks_in_play, calculate_ecosystem_score

        min_score = request.args.get('min_score', 70, type=int)

        # Get current scores
        scores_dict = {}
        try:
            import glob
            scan_files = sorted(glob.glob('scan_*.csv'), reverse=True)
            if scan_files:
                df = pd.read_csv(scan_files[0])
                scores_dict = df.set_index('ticker')['composite_score'].to_dict()
        except Exception:
            pass

        in_play = get_stocks_in_play(min_score=min_score, scores_dict=scores_dict)

        # Enrich with ecosystem scores
        for stock in in_play:
            try:
                eco_score = calculate_ecosystem_score(stock['ticker'], scores_dict=scores_dict)
                stock['ecosystem_strength'] = eco_score.get('score', 50)
                stock['network_size'] = eco_score.get('network_size', 0)
            except Exception:
                stock['ecosystem_strength'] = 50
                stock['network_size'] = 0

        return jsonify({
            'ok': True,
            'in_play': in_play,
            'count': len(in_play),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"In-play endpoint error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/ecosystem/refresh', methods=['POST'])
def api_ecosystem_refresh():
    """Trigger ecosystem refresh (internal)."""
    try:
        from ai_ecosystem_generator import refresh_single_ticker, refresh_hot_stocks

        data = request.get_json() or {}

        if data.get('ticker'):
            # Refresh single ticker
            ticker = data['ticker'].upper()
            result = refresh_single_ticker(ticker)
            return jsonify(result)

        elif data.get('all'):
            # Refresh all hot stocks
            scores_dict = {}
            try:
                import glob
                scan_files = sorted(glob.glob('scan_*.csv'), reverse=True)
                if scan_files:
                    df = pd.read_csv(scan_files[0])
                    scores_dict = df.set_index('ticker')['composite_score'].to_dict()
            except Exception:
                pass

            result = refresh_hot_stocks(min_score=80, scores_dict=scores_dict)
            return jsonify({
                'ok': True,
                'refreshed': result.get('success', []),
                'failed': result.get('failed', []),
            })

        else:
            return jsonify({'ok': False, 'error': 'Specify ticker or all=true'})

    except Exception as e:
        logger.error(f"Ecosystem refresh error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# EVOLUTION ENGINE API ENDPOINTS
# =============================================================================

@app.route('/api/evolution/status')
def api_evolution_status():
    """Get evolution learning system status."""
    try:
        from evolution_engine import get_evolution_status
        status = get_evolution_status()
        return jsonify({
            'ok': True,
            **status,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Evolution engine not available'})
    except Exception as e:
        logger.error(f"Evolution status error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/evolution/accuracy')
def api_evolution_accuracy():
    """Get validation metrics with confidence intervals."""
    try:
        from evolution_engine import get_accuracy_report
        report = get_accuracy_report()
        return jsonify({
            'ok': True,
            **report,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Evolution engine not available'})
    except Exception as e:
        logger.error(f"Evolution accuracy error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/evolution/weights')
def api_evolution_weights():
    """Get current vs historical adaptive weights."""
    try:
        from evolution_engine import load_learning_state, DEFAULT_WEIGHTS, AdaptiveScoringEngine

        state = load_learning_state()
        engine = AdaptiveScoringEngine()

        return jsonify({
            'ok': True,
            'current': state['adaptive_weights']['current'],
            'defaults': DEFAULT_WEIGHTS,
            'by_regime': state['adaptive_weights']['by_regime'],
            'changes': engine.get_weight_changes(),
            'history': state['adaptive_weights']['history'][-10:],
            'timestamp': datetime.now().isoformat()
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Evolution engine not available'})
    except Exception as e:
        logger.error(f"Evolution weights error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/evolution/themes')
def api_evolution_themes():
    """Get discovered themes from evolution engine."""
    try:
        from evolution_engine import get_discovered_themes, load_learning_state

        state = load_learning_state()
        themes = get_discovered_themes()

        return jsonify({
            'ok': True,
            'active_themes': themes,
            'retired_themes': state['discovered_themes'].get('retired_themes', []),
            'total_discovered': len(state['discovered_themes'].get('themes', [])),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Evolution engine not available'})
    except Exception as e:
        logger.error(f"Evolution themes error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/evolution/correlations')
def api_evolution_correlations():
    """Get learned correlations and lead-lag relationships."""
    try:
        from evolution_engine import get_learned_correlations

        correlations = get_learned_correlations()

        return jsonify({
            'ok': True,
            'pairs': correlations.get('pairs', {}),
            'propagation_patterns': correlations.get('propagation_patterns', {}),
            'total_pairs': len(correlations.get('pairs', {})),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Evolution engine not available'})
    except Exception as e:
        logger.error(f"Evolution correlations error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/evolution/run-cycle', methods=['POST'])
def api_evolution_run_cycle():
    """Trigger a learning cycle manually."""
    try:
        from evolution_engine import run_evolution_cycle

        results = run_evolution_cycle()

        return jsonify({
            'ok': True,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Evolution engine not available'})
    except Exception as e:
        logger.error(f"Evolution cycle error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/evolution/discover-themes', methods=['POST'])
def api_evolution_discover_themes():
    """Force theme discovery."""
    try:
        from evolution_engine import ThemeEvolutionEngine

        engine = ThemeEvolutionEngine()
        discovered = engine.discover_themes()

        return jsonify({
            'ok': True,
            'discovered': discovered,
            'count': len(discovered),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Evolution engine not available'})
    except Exception as e:
        logger.error(f"Theme discovery error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# PARAMETER LEARNING API ENDPOINTS
# =============================================================================

@app.route('/api/parameters/status')
def api_parameters_status():
    """Get parameter learning system status."""
    try:
        from parameter_learning import get_learning_status
        status = get_learning_status()
        return jsonify({'ok': True, **status})
    except ImportError:
        return jsonify({'ok': False, 'error': 'Parameter learning not available'})
    except Exception as e:
        logger.error(f"Parameter status error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/parameters/health')
def api_parameters_health():
    """Run health check on parameter learning system."""
    try:
        from parameter_learning import run_health_check
        health = run_health_check()
        return jsonify({'ok': True, **health})
    except ImportError:
        return jsonify({'ok': False, 'error': 'Parameter learning not available'})
    except Exception as e:
        logger.error(f"Parameter health error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/parameters/registry')
def api_parameters_registry():
    """Get all parameters with metadata."""
    try:
        from parameter_learning import get_registry
        registry = get_registry()
        params = {}
        for name, param in registry.parameters.items():
            params[name] = {
                'current': param.current_value,
                'default': param.default_value,
                'category': param.category,
                'status': param.status,
                'learned_samples': param.learned_from_samples,
                'confidence': param.confidence,
            }
        return jsonify({
            'ok': True,
            'total': len(params),
            'parameters': params
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Parameter learning not available'})
    except Exception as e:
        logger.error(f"Parameter registry error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/parameters/experiments')
def api_parameters_experiments():
    """Get active A/B experiments."""
    try:
        from parameter_learning import ABTestingFramework, get_registry
        ab = ABTestingFramework(get_registry())
        experiments = []
        for exp in ab.get_active_experiments():
            experiments.append(ab.get_experiment_status(exp.experiment_id))
        return jsonify({
            'ok': True,
            'active_count': len(experiments),
            'experiments': experiments
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Parameter learning not available'})
    except Exception as e:
        logger.error(f"Experiments error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/parameters/optimize', methods=['POST'])
def api_parameters_optimize():
    """Run optimization cycle."""
    try:
        from parameter_learning import run_optimization_cycle
        result = run_optimization_cycle()
        return jsonify({'ok': True, **result})
    except ImportError:
        return jsonify({'ok': False, 'error': 'Parameter learning not available'})
    except Exception as e:
        logger.error(f"Optimization error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# PARAMETER LEARNING TELEGRAM HANDLERS
# =============================================================================

def handle_parameters(chat_id):
    """Handle /parameters command - Show parameter learning status."""
    try:
        from parameter_learning import get_learning_status
        status = get_learning_status()

        params = status.get('parameters', {})
        health = status.get('health', {})

        msg = "📊 *PARAMETER LEARNING STATUS*\n\n"

        # Health status
        health_status = health.get('overall_status', 'unknown')
        if health_status == 'healthy':
            msg += "✅ System Status: Healthy\n"
        elif health_status == 'degraded':
            msg += "⚠️ System Status: Degraded\n"
        elif health_status == 'critical':
            msg += "🔴 System Status: Critical\n"
        else:
            msg += f"❓ System Status: {health_status}\n"

        msg += "\n*Parameters:*\n"
        msg += f"• Total: {params.get('total', 0)}\n"
        msg += f"• Learned: {params.get('learned', 0)}\n"
        msg += f"• Static: {params.get('static', 0)}\n"

        progress = params.get('learning_progress', 0)
        msg += f"• Progress: {progress:.1%}\n"
        msg += f"• Avg Confidence: {params.get('avg_confidence', 0):.1%}\n"

        # Category breakdown
        by_category = params.get('by_category', {})
        if by_category:
            msg += "\n*By Category:*\n"
            for cat, count in sorted(by_category.items()):
                msg += f"• {cat}: {count}\n"

        # Recent changes
        changes = status.get('recent_changes', [])
        if changes:
            msg += f"\n*Recent Changes:* {len(changes)} in last 7 days\n"

        # Active experiments
        exp_count = status.get('active_experiments', 0)
        if exp_count:
            msg += f"\n*Active Experiments:* {exp_count}\n"

        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "Parameter learning system not available.")
    except Exception as e:
        logger.error(f"Parameters command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_param_health(chat_id):
    """Handle /paramhealth command - Show system health."""
    try:
        from parameter_learning import run_health_check

        health = run_health_check()

        msg = "🏥 *PARAMETER SYSTEM HEALTH*\n\n"

        status = health.get('status', 'unknown')
        if status == 'healthy':
            msg += "✅ *Status: HEALTHY*\n"
        elif status == 'degraded':
            msg += "⚠️ *Status: DEGRADED*\n"
        elif status == 'critical':
            msg += "🔴 *Status: CRITICAL*\n"
        else:
            msg += f"❓ *Status: {status}*\n"

        # Metrics
        metrics = health.get('metrics', {})
        if metrics:
            msg += "\n*Metrics:*\n"
            for key, value in metrics.items():
                if isinstance(value, float):
                    msg += f"• {key}: {value:.2f}\n"
                else:
                    msg += f"• {key}: {value}\n"

        # Issues
        issues = health.get('issues', [])
        if issues:
            msg += f"\n*Issues ({len(issues)}):*\n"
            for issue in issues[:5]:  # Show first 5
                severity = issue.get('severity', 'info')
                message = issue.get('message', '')
                if severity == 'critical':
                    msg += f"🔴 {message}\n"
                elif severity == 'warning':
                    msg += f"⚠️ {message}\n"
                else:
                    msg += f"ℹ️ {message}\n"

                suggestion = issue.get('suggestion', '')
                if suggestion:
                    msg += f"   _Suggestion: {suggestion}_\n"
        else:
            msg += "\n✅ No issues detected\n"

        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "Parameter learning system not available.")
    except Exception as e:
        logger.error(f"Param health command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_experiments(chat_id):
    """Handle /experiments command - Show A/B test experiments."""
    try:
        from parameter_learning import ABTestingFramework, get_registry

        ab = ABTestingFramework(get_registry())
        active = ab.get_active_experiments()

        msg = "🧪 *A/B TEST EXPERIMENTS*\n\n"

        if not active:
            msg += "No active experiments.\n"
            msg += "\n_Experiments are created automatically when parameters need optimization._"
        else:
            msg += f"*Active: {len(active)}*\n\n"
            for exp in active:
                status = ab.get_experiment_status(exp.experiment_id)
                if status:
                    msg += f"📊 *{status['parameter']}*\n"
                    msg += f"   Variants: {status['variants']}\n"
                    msg += f"   Samples: {status['total_samples']}\n"

                    # Variant performance
                    for idx, stats in status.get('variant_stats', {}).items():
                        msg += f"   V{idx}: mean={stats['mean']:.2f} (n={stats['samples']})\n"

                    if status['winner'] is not None:
                        msg += f"   ✅ Winner: Variant {status['winner']}\n"
                    msg += "\n"

        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "Parameter learning system not available.")
    except Exception as e:
        logger.error(f"Experiments command error: {e}")
        send_message(chat_id, f"Error: {e}")


# =============================================================================
# THEME REGISTRY COMMANDS
# =============================================================================

def handle_themes(chat_id):
    """Handle /themes command - Show learned themes."""
    try:
        from theme_registry import get_registry

        registry = get_registry()
        active_themes = registry.get_active_themes()

        msg = "🎯 *THEME REGISTRY*\n\n"

        if not active_themes:
            msg += "No active themes found.\n"
            msg += "_Use /discoveredthemes to see auto-discovered themes._"
            send_message(chat_id, msg)
            return

        # Group by stage
        by_stage = {}
        for theme in active_themes:
            stage = theme.stage.value
            if stage not in by_stage:
                by_stage[stage] = []
            by_stage[stage].append(theme)

        for stage in ['early', 'middle', 'late', 'emerging']:
            themes = by_stage.get(stage, [])
            if themes:
                emoji = {'early': '🌱', 'middle': '🔥', 'late': '📉', 'emerging': '✨'}.get(stage, '📊')
                msg += f"\n*{emoji} {stage.upper()} ({len(themes)}):*\n"

                for t in sorted(themes, key=lambda x: x.heat_score, reverse=True)[:5]:
                    members = len(t.members)
                    drivers = len(t.get_drivers())
                    heat = t.heat_score if t.heat_score else 0
                    msg += f"• `{t.template.name}` | Heat: {heat:.0f} | {members} stocks ({drivers} drivers)\n"

        # Summary
        health = registry.run_health_check()
        msg += f"\n*📊 Summary:*\n"
        msg += f"• Total themes: {health.total_themes}\n"
        msg += f"• Active: {health.active_themes}\n"
        msg += f"• Total tickers: {health.total_members}\n"
        msg += f"• Discovered: {health.discovered_themes}\n"
        msg += f"• Health: {health.health_score:.0f}/100"

        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "Theme registry not available.")
    except Exception as e:
        logger.error(f"Themes command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_universe(chat_id):
    """Handle /universe command - Show universe manager status."""
    try:
        from universe_manager import get_universe_manager

        um = get_universe_manager()
        health = um.run_health_check()

        msg = "🌐 *UNIVERSE MANAGER*\n\n"

        msg += "*Current Universe:*\n"
        msg += f"• S&P 500: {health.sp500_count} tickers\n"
        msg += f"• NASDAQ 100: {health.nasdaq100_count} tickers\n"
        msg += f"• Total unique: {health.total_unique}\n"
        msg += f"• Breadth universe: {health.breadth_universe_size}\n\n"

        msg += "*Sources:*\n"
        msg += f"• SP500: {health.sp500_source}\n"
        msg += f"• NASDAQ: {health.nasdaq100_source}\n\n"

        msg += "*Cache Status:*\n"
        cache_age = health.cache_age_hours
        if cache_age:
            msg += f"• Age: {cache_age:.1f} hours\n"
            msg += f"• Valid: {'✅' if cache_age < 24 else '⚠️'}\n"
        else:
            msg += "• No cache\n"

        msg += f"\n*Health Score:* {health.health_score:.0f}/100"

        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "Universe manager not available. Using hardcoded ticker lists.")
    except Exception as e:
        logger.error(f"Universe command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_themehealth(chat_id):
    """Handle /themehealth command - Theme registry health check."""
    try:
        from theme_registry import get_registry
        from theme_learner import get_learner

        registry = get_registry()
        reg_health = registry.run_health_check()

        learner = get_learner()
        learn_health = learner.run_health_check()

        msg = "🏥 *THEME SYSTEM HEALTH*\n\n"

        # Registry health
        msg += "*📚 Theme Registry:*\n"
        msg += f"• Score: {reg_health.health_score:.0f}/100\n"
        msg += f"• Themes: {reg_health.active_themes} active\n"
        msg += f"• Members: {reg_health.total_members}\n"
        msg += f"• Avg per theme: {reg_health.avg_members_per_theme:.1f}\n"

        if reg_health.themes_without_drivers:
            msg += f"• ⚠️ No drivers: {', '.join(reg_health.themes_without_drivers[:3])}\n"
        if reg_health.stale_themes:
            msg += f"• ⚠️ Stale: {', '.join(reg_health.stale_themes[:3])}\n"

        # Learner health
        msg += f"\n*🧠 Theme Learner:*\n"
        msg += f"• Score: {learn_health.health_score:.0f}/100\n"
        msg += f"• DeepSeek: {'✅' if learn_health.deepseek_available else '❌'}\n"
        msg += f"• Discovered (30d): {learn_health.themes_discovered_30d} themes\n"
        msg += f"• Added (30d): {learn_health.members_added_30d} members\n"
        msg += f"• Removed (30d): {learn_health.members_removed_30d} members\n"
        msg += f"• Correlation quality: {learn_health.avg_correlation_quality:.2f}\n"

        if learn_health.last_correlation_run:
            msg += f"• Last correlation: {learn_health.last_correlation_run[:16]}\n"
        if learn_health.last_validation_run:
            msg += f"• Last validation: {learn_health.last_validation_run[:16]}"

        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "Theme system not available.")
    except Exception as e:
        logger.error(f"Theme health command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_trends(chat_id, keyword=None):
    """Handle /trends command - Google Trends theme detection."""
    try:
        from src.data.google_trends import (
            get_trend_score,
            get_theme_momentum_report,
            format_trends_message,
            HAS_PYTRENDS
        )

        if not HAS_PYTRENDS:
            send_message(chat_id, "❌ *GOOGLE TRENDS*\n\npytrends not installed.")
            return

        send_message(chat_id, "📊 Fetching Google Trends data...")

        if keyword:
            # Single keyword lookup
            result = get_trend_score(keyword)

            if result.get('error'):
                send_message(chat_id, f"❌ Error: {result['error']}")
                return

            score = result.get('score', 0)
            status = result.get('status', 'unknown')
            trend_pct = result.get('trend_pct', 0)

            # Status emoji
            if status == 'breakout':
                emoji = "🔥"
            elif status == 'rising':
                emoji = "📈"
            elif status == 'declining':
                emoji = "📉"
            else:
                emoji = "➡️"

            msg = f"📊 *GOOGLE TRENDS*\n\n"
            msg += f"*Keyword:* `{keyword}`\n\n"
            msg += f"• Momentum Score: *{score:.0f}/100*\n"
            msg += f"• Status: {emoji} {status.upper()}\n"
            msg += f"• 7-day Trend: {'+' if trend_pct > 0 else ''}{trend_pct:.1f}%\n"
            msg += f"• Current Index: {result.get('current', 0):.0f}\n"
            msg += f"• 30-day Avg: {result.get('avg_30d', 0):.0f}\n"

            if result.get('is_breakout'):
                msg += f"\n🚀 *BREAKOUT DETECTED!*"

            send_message(chat_id, msg)

        else:
            # Full theme momentum report
            report = get_theme_momentum_report()
            msg = format_trends_message(report)
            send_message(chat_id, msg)

    except ImportError as e:
        logger.error(f"Google Trends import error: {e}")
        send_message(chat_id, "❌ Google Trends module not available.")
    except Exception as e:
        logger.error(f"Trends command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_thememomentum(chat_id):
    """Handle /thememomentum command - Quick theme momentum overview."""
    try:
        from src.data.google_trends import (
            detect_trending_themes,
            HAS_PYTRENDS
        )

        if not HAS_PYTRENDS:
            send_message(chat_id, "❌ *THEME MOMENTUM*\n\npytrends not installed.")
            return

        send_message(chat_id, "📈 Analyzing theme momentum (this may take a minute)...")

        themes = detect_trending_themes()

        if not themes:
            send_message(chat_id, "❌ Could not fetch theme data from Google Trends.")
            return

        msg = "📈 *THEME MOMENTUM*\n"
        msg += "_Based on Google Search Trends_\n\n"

        # Top 5 by momentum
        msg += "*🔥 HOTTEST THEMES:*\n"
        for t in themes[:5]:
            emoji = "🔥" if t.get('is_breakout') else "📈" if t.get('trend_pct', 0) > 10 else "➡️"
            score = t.get('score', 0)
            trend = t.get('trend_pct', 0)
            msg += f"{emoji} `{t['theme_id'].upper()}` | Score: {score:.0f} | {'+' if trend > 0 else ''}{trend:.0f}%\n"

        # Breakouts
        breakouts = [t for t in themes if t.get('is_breakout')]
        if breakouts:
            msg += f"\n🚀 *BREAKOUT ALERT:*\n"
            for t in breakouts[:3]:
                msg += f"• {t['theme_id'].upper()} - Sudden spike in search interest!\n"

        # Declining
        declining = [t for t in themes if t.get('trend_pct', 0) < -10]
        if declining:
            msg += f"\n📉 *COOLING OFF:*\n"
            for t in declining[:3]:
                msg += f"• {t['theme_id'].upper()} ({t['trend_pct']:.0f}%)\n"

        msg += f"\n_Tracking {len(themes)} investment themes_"

        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "❌ Google Trends module not available.")
    except Exception as e:
        logger.error(f"Theme momentum command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_themeintel(chat_id):
    """Handle /themeintel command - Full Theme Intelligence Hub analysis."""
    try:
        from src.intelligence.theme_intelligence import (
            analyze_all_themes,
            format_theme_intelligence_message
        )

        send_message(chat_id, "🎯 Running Theme Intelligence analysis (this takes 1-2 minutes)...")

        report = analyze_all_themes(quick=True)
        msg = format_theme_intelligence_message(report)
        send_message(chat_id, msg)

    except ImportError as e:
        logger.error(f"Theme Intel import error: {e}")
        send_message(chat_id, "❌ Theme Intelligence module not available.")
    except Exception as e:
        logger.error(f"Theme Intel command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_themealerts(chat_id):
    """Handle /themealerts command - Recent theme alerts."""
    try:
        from src.intelligence.theme_intelligence import (
            get_breakout_alerts,
            format_alerts_message
        )

        alerts = get_breakout_alerts()
        msg = format_alerts_message(alerts)
        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "❌ Theme Intelligence module not available.")
    except Exception as e:
        logger.error(f"Theme alerts command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_themeradar(chat_id):
    """Handle /themeradar command - Quick theme radar view."""
    try:
        from src.intelligence.theme_intelligence import get_theme_radar

        radar = get_theme_radar()

        if not radar.get('ok'):
            send_message(chat_id, "❌ Could not fetch theme radar data.")
            return

        msg = "📡 *THEME RADAR*\n"
        msg += "_Quick view of all tracked themes_\n\n"

        lifecycle_emoji = {
            'emerging': '🌱',
            'accelerating': '🚀',
            'peak': '🔥',
            'declining': '📉',
            'dead': '💀'
        }

        for item in radar.get('radar', [])[:15]:
            emoji = lifecycle_emoji.get(item['lifecycle'], '⚪')
            trend_arrow = '↑' if item.get('trend', 0) > 0 else '↓' if item.get('trend', 0) < 0 else '→'
            score = item.get('score', 0)

            msg += f"{emoji} `{item['theme_id'].upper()}` | {score:.0f} {trend_arrow}\n"

        msg += f"\n_Last updated: {radar.get('timestamp', 'N/A')[:16]}_"
        msg += "\n\n_Use /themeintel for full analysis_"

        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "❌ Theme Intelligence module not available.")
    except Exception as e:
        logger.error(f"Theme radar command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_tickertheme(chat_id, ticker):
    """Handle /tickertheme command - Get theme boost for a ticker."""
    try:
        from src.intelligence.theme_intelligence import get_ticker_theme_boost

        ticker = ticker.upper()
        boost_data = get_ticker_theme_boost(ticker)

        msg = f"🎯 *THEME BOOST: {ticker}*\n\n"

        boost = boost_data.get('boost', 0)
        if boost > 0:
            msg += f"*Boost:* +{boost} points 📈\n"
        elif boost < 0:
            msg += f"*Boost:* {boost} points 📉\n"
        else:
            msg += f"*Boost:* 0 points ➡️\n"

        themes = boost_data.get('themes', [])
        if themes:
            msg += f"\n*Linked Themes:*\n"
            for t in themes:
                lifecycle_emoji = {
                    'emerging': '🌱',
                    'accelerating': '🚀',
                    'peak': '🔥',
                    'declining': '📉',
                    'dead': '💀'
                }.get(t['lifecycle'], '⚪')

                msg += f"{lifecycle_emoji} {t['theme_name']} | Score: {t['score']:.0f} | Boost: {'+' if t['boost'] > 0 else ''}{t['boost']}\n"
        else:
            msg += f"\n_{boost_data.get('reason', 'No theme mapping')}_"

        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "❌ Theme Intelligence module not available.")
    except Exception as e:
        logger.error(f"Ticker theme command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_discover(chat_id):
    """Handle /discover command - Auto-discover new themes."""
    try:
        from src.intelligence.theme_discovery import (
            get_discovery_engine,
            format_discovery_message
        )

        send_message(chat_id, "🔍 Running theme discovery (this may take 2-3 minutes)...")

        engine = get_discovery_engine()
        themes = engine.discover_themes()
        report = engine.get_discovery_report()

        msg = format_discovery_message(report)
        send_message(chat_id, msg)

    except ImportError as e:
        logger.error(f"Discovery import error: {e}")
        send_message(chat_id, "❌ Theme Discovery module not available.")
    except Exception as e:
        logger.error(f"Discovery command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_institutional(chat_id):
    """Handle /institutional command - Institutional flow analysis."""
    try:
        from src.intelligence.institutional_flow import (
            get_flow_tracker,
            format_institutional_message
        )

        send_message(chat_id, "🏦 Analyzing institutional flow...")

        tracker = get_flow_tracker()
        summary = tracker.get_theme_institutional_summary()

        msg = format_institutional_message(summary)
        send_message(chat_id, msg)

    except ImportError as e:
        logger.error(f"Institutional import error: {e}")
        send_message(chat_id, "❌ Institutional Flow module not available.")
    except Exception as e:
        logger.error(f"Institutional command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_optionsflow(chat_id, ticker=None):
    """Handle /optionsflow command - Options flow signals."""
    try:
        from src.intelligence.institutional_flow import get_flow_tracker

        tracker = get_flow_tracker()

        if ticker:
            signals = tracker.get_options_flow_signals([ticker.upper()])
            title = f"OPTIONS FLOW: {ticker.upper()}"
        else:
            signals = tracker.get_options_flow_signals()
            title = "OPTIONS FLOW SIGNALS"

        msg = f"📊 *{title}*\n\n"

        if not signals:
            msg += "_No significant options flow detected_"
            send_message(chat_id, msg)
            return

        # Group by sentiment
        bullish = [s for s in signals if s.sentiment == 'bullish']
        bearish = [s for s in signals if s.sentiment == 'bearish']

        if bullish:
            msg += "📈 *BULLISH:*\n"
            for s in bullish[:5]:
                msg += f"• `{s.ticker}` {s.signal_type}\n"
                if s.premium:
                    msg += f"  Premium: ${s.premium:,.0f}\n"

        if bearish:
            msg += "\n📉 *BEARISH:*\n"
            for s in bearish[:5]:
                msg += f"• `{s.ticker}` {s.signal_type}\n"

        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "❌ Institutional Flow module not available.")
    except Exception as e:
        logger.error(f"Options flow command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_rotation(chat_id):
    """Handle /rotation command - Theme rotation forecast."""
    try:
        from src.intelligence.rotation_predictor import (
            get_rotation_predictor,
            format_rotation_message
        )

        send_message(chat_id, "🔄 Generating rotation forecast...")

        predictor = get_rotation_predictor()
        forecast = predictor.get_rotation_forecast()

        msg = format_rotation_message(forecast)
        send_message(chat_id, msg)

    except ImportError as e:
        logger.error(f"Rotation import error: {e}")
        send_message(chat_id, "❌ Rotation Predictor module not available.")
    except Exception as e:
        logger.error(f"Rotation command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_peakwarnings(chat_id):
    """Handle /peakwarnings command - Themes at potential peak."""
    try:
        from src.intelligence.rotation_predictor import (
            get_rotation_predictor,
            format_peak_warnings_message
        )

        predictor = get_rotation_predictor()
        warnings = predictor.detect_peak_themes()

        msg = format_peak_warnings_message(warnings)
        send_message(chat_id, msg)

    except ImportError:
        send_message(chat_id, "❌ Rotation Predictor module not available.")
    except Exception as e:
        logger.error(f"Peak warnings command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_patents(chat_id, query=None):
    """Handle /patents command - Patent intelligence via PatentView API."""
    try:
        from src.patents.patent_tracker import (
            format_patent_report
        )

        if query:
            # Single ticker lookup
            ticker = query.upper().strip()
            send_message(chat_id, f"Fetching patent data for {ticker}...")

            # Get detailed patent report
            msg = format_patent_report(ticker)
            send_message(chat_id, msg)
        else:
            # Show help/usage
            msg = """*Patent Intelligence*

Search USPTO patent filings by company.

*Usage:*
`/patents NVDA` - NVIDIA patents
`/patents AAPL` - Apple patents
`/patents TSLA` - Tesla patents

*Provides:*
- Total patents (3 years)
- Innovation score (0-100)
- Filing trend (accelerating/stable/declining)
- Top patent categories
- Recent patent titles

_Powered by USPTO PatentView API_"""
            send_message(chat_id, msg)

    except ImportError as e:
        logger.error(f"Patents import error: {e}")
        send_message(chat_id, "Patent module not available.")
    except Exception as e:
        logger.error(f"Patents command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_contracts(chat_id, query=None):
    """Handle /contracts command - Government contracts intelligence."""
    try:
        from src.data.gov_contracts import (
            get_contract_intelligence,
            format_contracts_message
        )

        send_message(chat_id, "🏛️ Fetching government contract data...")

        intel = get_contract_intelligence()

        if query:
            # Single company or theme lookup
            query_upper = query.upper()
            if len(query_upper) <= 5:  # Likely a ticker
                activity = intel.get_company_contracts(query_upper)
                msg = f"🏛️ *CONTRACTS: {query_upper}*\n\n"
                msg += f"*Total Value:* ${activity.total_value/1e9:.2f}B\n"
                msg += f"*Contracts:* {activity.contract_count}\n"
                msg += f"*Signal:* {activity.signal_strength:.0%}\n\n"

                if activity.top_agencies:
                    msg += "*Top Agencies:*\n"
                    for agency in activity.top_agencies[:3]:
                        msg += f"• {agency[:40]}\n"

                if activity.recent_contracts:
                    msg += "\n*Recent Awards:*\n"
                    for c in activity.recent_contracts[:5]:
                        msg += f"• ${c.get('amount', 0)/1e6:.0f}M ({c.get('date', '')})\n"
            else:
                # Theme lookup
                activity = intel.get_theme_contract_activity(query.lower())
                msg = f"🏛️ *CONTRACTS: {query}*\n\n"
                msg += f"*Total Value:* ${activity.total_value/1e9:.2f}B\n"
                msg += f"*Contracts:* {activity.contract_count}\n"
                msg += f"*Trend:* {activity.trend} ({activity.mom_change:+.0f}% MoM)\n"

            send_message(chat_id, msg)
        else:
            # Full trends report
            data = intel.get_all_themes_contract_activity()
            msg = format_contracts_message(data)
            send_message(chat_id, msg)

    except ImportError as e:
        logger.error(f"Contracts import error: {e}")
        send_message(chat_id, "❌ Government contracts module not available.")
    except Exception as e:
        logger.error(f"Contracts command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_apistatus(chat_id):
    """Handle /apistatus command - Show all API integration status with usage stats."""
    import os
    from config import config

    msg = "⚙️ *API INTEGRATION STATUS*\n\n"

    # AI Providers with usage stats
    msg += "*🤖 AI Providers:*\n"
    try:
        from src.services.ai_service import get_ai_service
        ai_svc = get_ai_service()
        status = ai_svc.get_status()

        if status['providers']['deepseek']['configured']:
            msg += f"✅ DeepSeek (`{status['providers']['deepseek']['model']}`)\n"
        else:
            msg += "❌ DeepSeek - not configured\n"

        if status['providers']['xai']['configured']:
            msg += f"✅ xAI/Grok (`{status['providers']['xai']['model']}`)\n"
        else:
            msg += "❌ xAI/Grok - not configured\n"

        # AI usage stats
        stats = status.get('stats', {})
        if stats.get('calls_today', 0) > 0:
            msg += f"\n_Today: {stats['calls_today']} calls"
            if stats.get('deepseek_calls'):
                msg += f", DS:{stats['deepseek_calls']}"
            if stats.get('xai_calls'):
                msg += f", xAI:{stats['xai_calls']}"
            if stats.get('fallback_count'):
                msg += f", fallbacks:{stats['fallback_count']}"
            msg += "_\n"
    except ImportError:
        if config.ai.has_deepseek:
            msg += f"✅ DeepSeek (`{config.ai.model}`)\n"
        else:
            msg += "❌ DeepSeek - not configured\n"
        if config.ai.has_xai:
            msg += f"✅ xAI/Grok (`{config.ai.xai_model}`)\n"
        else:
            msg += "❌ xAI/Grok - not configured\n"
    msg += "\n"

    # Polygon
    msg += "*📊 Market Data:*\n"
    polygon_key = os.environ.get('POLYGON_API_KEY', '')
    if polygon_key and len(polygon_key) > 10:
        msg += "✅ Polygon.io (prices, options, news)\n"
    else:
        msg += "❌ Polygon.io - not configured\n"
    msg += "\n"

    # Data Providers
    msg += "*📈 Data Providers:*\n"
    try:
        from utils.data_providers import check_provider_status
        providers = check_provider_status()

        if providers.get('finnhub'):
            msg += "✅ Finnhub (quotes, news, sentiment)\n"
        else:
            msg += "❌ Finnhub - not configured\n"

        if providers.get('tiingo'):
            msg += "✅ Tiingo (EOD prices, news)\n"
        else:
            msg += "❌ Tiingo - not configured\n"

        if providers.get('alpha_vantage'):
            msg += "✅ Alpha Vantage (fundamentals)\n"
        else:
            msg += "❌ Alpha Vantage - not configured\n"

        if providers.get('fred'):
            msg += "✅ FRED (economic data)\n"
        else:
            msg += "❌ FRED - not configured\n"

        msg += "✅ SEC EDGAR (filings, always available)\n"
    except ImportError:
        msg += "⚠️ Data providers module not loaded\n"
    msg += "\n"

    # Telegram
    msg += "*📱 Telegram:*\n"
    if config.telegram.is_configured:
        msg += "✅ Bot configured\n"
    else:
        msg += "❌ Bot not configured\n"

    if config.telegram.chat_id:
        msg += "✅ Chat ID set (alerts enabled)\n"
    else:
        msg += "⚠️ Chat ID not set (no auto-alerts)\n"

    # Summary
    ai_count = (1 if config.ai.has_deepseek else 0) + (1 if config.ai.has_xai else 0)
    try:
        data_count = sum(1 for v in providers.values() if v)
    except:
        data_count = 0
    polygon_count = 1 if (polygon_key and len(polygon_key) > 10) else 0

    msg += f"\n*📋 Summary:* {ai_count + data_count + polygon_count} APIs active"

    send_message(chat_id, msg)


def handle_smartmoney(chat_id):
    """Handle /smartmoney command - Combined institutional intelligence."""
    try:
        from src.intelligence.institutional_flow import get_institutional_summary
        from src.intelligence.rotation_predictor import get_rotation_forecast, get_peak_warnings

        send_message(chat_id, "🧠 Compiling smart money intelligence...")

        msg = "🧠 *SMART MONEY INTELLIGENCE*\n"
        msg += "_Combined institutional signals_\n\n"

        # Institutional flow
        inst_summary = get_institutional_summary()
        if inst_summary.get('ok'):
            bullish = inst_summary.get('top_bullish', [])[:3]
            bearish = inst_summary.get('top_bearish', [])[:3]

            if bullish:
                msg += "📈 *Institutional Buying:*\n"
                for theme_id in bullish:
                    msg += f"• `{theme_id.upper()}`\n"
                msg += "\n"

            if bearish:
                msg += "📉 *Institutional Selling:*\n"
                for theme_id in bearish:
                    msg += f"• `{theme_id.upper()}`\n"
                msg += "\n"

        # Rotation forecast
        rotation = get_rotation_forecast()
        if rotation.get('ok'):
            rotating_in = rotation.get('rotating_in', [])[:2]
            rotating_out = rotation.get('rotating_out', [])[:2]

            if rotating_in:
                msg += "🔄 *Rotating In:*\n"
                for f in rotating_in:
                    msg += f"• `{f['theme_id'].upper()}` ({f['rotation_probability']*100:.0f}%)\n"
                msg += "\n"

            if rotating_out:
                msg += "🔄 *Rotating Out:*\n"
                for f in rotating_out:
                    msg += f"• `{f['theme_id'].upper()}` ({f['rotation_probability']*100:.0f}%)\n"
                msg += "\n"

        # Peak warnings
        peaks = get_peak_warnings()
        if peaks:
            confirmed = [p for p in peaks if p.get('warning_level') in ['confirmed', 'imminent']]
            if confirmed:
                msg += "⚠️ *Peak Warnings:*\n"
                for p in confirmed[:3]:
                    msg += f"• `{p['theme_id'].upper()}` ({p['warning_level']})\n"

        send_message(chat_id, msg)

    except ImportError as e:
        logger.error(f"Smart money import error: {e}")
        send_message(chat_id, "❌ Intelligence modules not available.")
    except Exception as e:
        logger.error(f"Smart money command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_conviction(chat_id, ticker=None):
    """
    Handle /conviction command - Multi-signal conviction scoring.

    Prioritizes hard data:
    1. Insider Activity (25%)
    2. Options Flow (25%)
    3. Patents (12%)
    4. Gov Contracts (13%)
    5. Sentiment (10%) - validation only
    6. Technical (15%) - entry timing
    """
    try:
        from src.intelligence.hard_data_scanner import get_hard_data_scanner

        scanner = get_hard_data_scanner()

        if ticker:
            # Single ticker analysis
            ticker = ticker.upper()
            send_message(chat_id, f"🎯 Analyzing {ticker} conviction signals...")

            result = scanner.scan_ticker(ticker)

            # Build detailed message
            rec_emoji = {
                'STRONG BUY': '🟢🟢',
                'BUY': '🟢',
                'WATCH': '🟡',
                'HOLD': '⚪',
                'AVOID': '🔴'
            }

            msg = f"🎯 *CONVICTION: {ticker}*\n\n"
            msg += f"*Score:* {result.conviction_score:.0f}/100 {rec_emoji.get(result.recommendation, '')}\n"
            msg += f"*Recommendation:* {result.recommendation}\n\n"

            # Signal breakdown
            msg += "*📊 Signal Breakdown:*\n"

            if result.insider and result.insider.score > 0:
                emoji = '✅' if 'bullish' in result.insider.signal else '⚪' if 'neutral' in result.insider.signal else '❌'
                msg += f"{emoji} Insider: {result.insider.score:.0f}/100 ({result.insider.signal})\n"

            if result.options and result.options.score > 0:
                emoji = '✅' if 'bullish' in result.options.signal else '⚪' if 'neutral' in result.options.signal else '❌'
                msg += f"{emoji} Options: {result.options.score:.0f}/100 ({result.options.signal})\n"

            if result.patents and result.patents.score > 0:
                emoji = '✅' if 'bullish' in result.patents.signal else '⚪'
                msg += f"{emoji} Patents: {result.patents.score:.0f}/100 ({result.patents.signal})\n"

            if result.contracts and result.contracts.score > 0:
                emoji = '✅' if 'bullish' in result.contracts.signal else '⚪'
                msg += f"{emoji} Contracts: {result.contracts.score:.0f}/100 ({result.contracts.signal})\n"

            if result.sentiment and result.sentiment.score > 0:
                if result.sentiment.is_euphoric:
                    emoji = '⚠️'
                elif 'bullish' in result.sentiment.signal:
                    emoji = '✅'
                else:
                    emoji = '⚪'
                msg += f"{emoji} Sentiment: {result.sentiment.score:.0f}/100 ({result.sentiment.signal})\n"

            if result.technical and result.technical.score > 0:
                emoji = '✅' if result.technical.signal == 'buyable' else '🟡' if result.technical.signal == 'watchable' else '⚪'
                msg += f"{emoji} Technical: {result.technical.score:.0f}/100 ({result.technical.signal})\n"

            # Warnings
            if result.warnings:
                msg += f"\n⚠️ *Warnings:*\n"
                for w in result.warnings:
                    msg += f"• {w}\n"

            # Summary
            msg += f"\n✅ Bullish signals: {result.bullish_signals}"
            msg += f"\n❌ Bearish signals: {result.bearish_signals}"

            send_message(chat_id, msg)

        else:
            # High conviction alerts
            send_message(chat_id, "🎯 Scanning for high-conviction setups...")

            results = scanner.get_high_conviction_alerts(min_score=65)

            if results:
                msg = "🎯 *HIGH CONVICTION ALERTS*\n"
                msg += "_Multi-signal alignment (Hard Data First)_\n\n"

                for r in results[:8]:
                    rec_emoji = {'STRONG BUY': '🟢🟢', 'BUY': '🟢', 'WATCH': '🟡'}.get(r.recommendation, '⚪')
                    msg += f"{rec_emoji} *{r.ticker}*: {r.conviction_score:.0f}/100\n"
                    msg += f"   {r.recommendation} • {r.bullish_signals} bullish signals\n"
                    if r.reasoning:
                        msg += f"   _{r.reasoning[0]}_\n"
                    msg += "\n"

                msg += "_Use `/conviction TICKER` for detailed breakdown_"
            else:
                msg = "🎯 *HIGH CONVICTION ALERTS*\n\n"
                msg += "No high-conviction setups found at this time.\n"
                msg += "Signals need to align (insider + options + patents/contracts)."

            send_message(chat_id, msg)

    except ImportError as e:
        logger.error(f"Conviction import error: {e}")
        send_message(chat_id, "❌ Conviction scanner not available.")
    except Exception as e:
        logger.error(f"Conviction command error: {e}")
        send_message(chat_id, f"Error: {e}")


def handle_supplychain(chat_id, theme_or_ticker=None):
    """
    Handle /supplychain command - AI-powered supply chain theme discovery.

    Uses AI to analyze real-time market data and find lagging plays.
    Key insight: Theme leaders move first, supply chain follows.

    Usage:
      /supplychain - AI-driven discovery (analyzes news, movers, social)
      /supplychain ai_infrastructure - Specific theme analysis
      /supplychain NVDA - Discover supply chain for a ticker
    """
    try:
        from src.intelligence.theme_discovery_engine import get_theme_discovery_engine

        engine = get_theme_discovery_engine()

        if theme_or_ticker:
            # Analyze specific theme or discover chain for a ticker
            theme_or_ticker = theme_or_ticker.lower().replace(' ', '_')
            send_message(chat_id, f"🔗 Analyzing supply chain for `{theme_or_ticker}`...")

            theme = engine.analyze_supply_chain(theme_or_ticker)

            if not theme:
                send_message(chat_id, f"❌ Could not analyze supply chain for `{theme_or_ticker}`")
                return

            msg = f"🔗 *SUPPLY CHAIN: {theme.theme_name}*\n"
            msg += f"_{theme.lifecycle_stage.upper()} stage_\n\n"

            # Show lagging plays (the opportunities)
            laggards = engine.find_lagging_plays(theme_or_ticker)

            if laggards:
                msg += "📈 *Lagging Opportunities:*\n"
                msg += "_These stocks haven't moved yet_\n\n"

                for node in laggards[:8]:
                    perf_emoji = '🟢' if node.price_performance_30d > 5 else '🟡' if node.price_performance_30d > 0 else '🔴'
                    msg += f"• `{node.ticker}` ({node.role})\n"
                    msg += f"  Story: {node.story_score:.0f} | 30d: {perf_emoji}{node.price_performance_30d:+.1f}%\n"
                    msg += f"  Opportunity: {node.opportunity_score:.0f}/100\n\n"
            else:
                msg += "_No lagging opportunities found - theme may be mature_\n\n"

            # Validation scores
            msg += "*📊 Validation:*\n"
            msg += f"• Patents: {theme.patent_validation:.0f}/100\n"
            msg += f"• Contracts: {theme.contract_validation:.0f}/100\n"
            msg += f"• Insider: {theme.insider_validation:.0f}/100\n\n"

            msg += f"_{theme.estimated_runway}_"

            send_message(chat_id, msg)

        else:
            # AI-driven discovery - analyze real-time market data
            send_message(chat_id, "🤖 AI analyzing real-time market data...\n_News, movers, social buzz, SEC filings_")

            # Try AI-driven analysis first
            ai_result = engine.analyze_with_ai()

            if 'error' not in ai_result and ai_result.get('emerging_themes'):
                msg = "🔗 *AI SUPPLY CHAIN DISCOVERY*\n"
                msg += "_Real-time analysis of market data_\n\n"

                # Show analysis summary
                if ai_result.get('analysis_summary'):
                    msg += f"📊 _{ai_result['analysis_summary']}_\n\n"

                # Show emerging themes
                for theme_data in ai_result.get('emerging_themes', [])[:3]:
                    confidence = theme_data.get('confidence', 50)
                    emoji = '🔥' if confidence > 75 else '🌱' if confidence > 50 else '👀'

                    msg += f"{emoji} *{theme_data.get('theme_name')}* ({confidence}% conf)\n"
                    msg += f"_{theme_data.get('reasoning', '')[:100]}_\n"

                    # Leaders
                    leaders = theme_data.get('leaders', [])[:3]
                    if leaders:
                        msg += f"Leaders: `{', '.join(leaders)}`\n"

                    # Lagging opportunities
                    laggards = theme_data.get('lagging_opportunities', [])[:3]
                    if laggards:
                        msg += "📈 *Lagging plays:*\n"
                        for opp in laggards:
                            msg += f"  • `{opp.get('ticker')}` ({opp.get('role')})\n"
                            msg += f"    _{opp.get('connection', '')[:50]}_\n"
                            if opp.get('catalyst'):
                                msg += f"    Catalyst: {opp.get('catalyst')[:40]}\n"

                    msg += "\n"

                # Top actionable ideas
                top_ideas = ai_result.get('top_actionable_ideas', [])[:2]
                if top_ideas:
                    msg += "*🎯 TOP IDEAS:*\n"
                    for idea in top_ideas:
                        msg += f"• `{idea.get('ticker')}` - {idea.get('thesis', '')[:60]}\n"
                        if idea.get('risk'):
                            msg += f"  _Risk: {idea.get('risk')[:40]}_\n"

                send_message(chat_id, msg)

            else:
                # Fallback to static analysis
                logger.info("AI analysis unavailable, using static supply chain mapping")
                summary = engine.get_discovery_summary()

                if not summary.get('themes'):
                    msg = "🔗 *SUPPLY CHAIN DISCOVERY*\n\n"
                    msg += "_No emerging themes with lagging plays found._\n"
                    msg += "Run a scan first to populate story scores."
                    send_message(chat_id, msg)
                    return

                msg = "🔗 *SUPPLY CHAIN OPPORTUNITIES*\n"
                msg += "_Find laggards before they move_\n\n"

                for theme_data in summary['themes'][:4]:
                    stage_emoji = {'emerging': '🌱', 'accelerating': '🚀', 'mainstream': '🌊', 'late': '🍂'}.get(theme_data['lifecycle_stage'], '⚪')

                    msg += f"{stage_emoji} *{theme_data['theme_name']}*\n"
                    msg += f"  Opportunity: {theme_data['opportunity_score']:.0f}/100\n"
                    msg += f"  Laggards: {theme_data['laggard_count']} stocks\n"

                    # Show top laggards
                    if theme_data.get('top_laggards'):
                        laggard_tickers = [l['ticker'] for l in theme_data['top_laggards'][:3]]
                        msg += f"  Top: `{', '.join(laggard_tickers)}`\n"

                    msg += "\n"

                msg += f"Total opportunities: {summary['total_opportunities']}\n\n"
                msg += "_Use `/supplychain THEME` for details_"

                send_message(chat_id, msg)

    except ImportError as e:
        logger.error(f"Supply chain import error: {e}")
        send_message(chat_id, "❌ Supply chain discovery not available.")
    except Exception as e:
        logger.error(f"Supply chain command error: {e}")
        send_message(chat_id, f"Error: {e}")


# =============================================================================
# THEME & UNIVERSE API ENDPOINTS
# =============================================================================

@app.route('/api/themes/registry')
def api_themes_registry():
    """Get theme registry summary."""
    try:
        from theme_registry import get_registry

        registry = get_registry()
        summary = registry.get_summary()

        return jsonify({
            'ok': True,
            'data': summary,
            'timestamp': datetime.now().isoformat(),
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Theme registry not available'}), 503
    except Exception as e:
        logger.error(f"Themes registry API error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/themes/list')
def api_themes_list():
    """Get all themes with details."""
    try:
        from theme_registry import get_registry

        registry = get_registry()
        themes = []

        for theme_id, theme in registry.themes.items():
            themes.append({
                'id': theme_id,
                'name': theme.template.name,
                'category': theme.template.category,
                'stage': theme.stage.value,
                'heat_score': theme.heat_score,
                'members': len(theme.members),
                'drivers': theme.get_drivers(),
                'discovery_method': theme.discovery_method,
                'discovered_at': theme.discovered_at,
            })

        return jsonify({
            'ok': True,
            'themes': sorted(themes, key=lambda x: x['heat_score'], reverse=True),
            'total': len(themes),
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Theme registry not available'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/themes/members/<theme_id>')
def api_theme_members(theme_id):
    """Get members of a specific theme."""
    try:
        from theme_registry import get_registry

        registry = get_registry()
        theme = registry.get_theme(theme_id)

        if not theme:
            return jsonify({'ok': False, 'error': 'Theme not found'}), 404

        members = []
        for ticker, member in theme.members.items():
            members.append({
                'ticker': ticker,
                'role': member.role.value,
                'confidence': member.confidence,
                'source': member.source,
                'correlation': member.correlation_to_drivers,
                'lag_days': member.lead_lag_days,
                'added_at': member.added_at,
            })

        return jsonify({
            'ok': True,
            'theme_id': theme_id,
            'theme_name': theme.template.name,
            'stage': theme.stage.value,
            'members': sorted(members, key=lambda x: x['confidence'], reverse=True),
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Theme registry not available'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/themes/ticker/<ticker>')
def api_ticker_themes(ticker):
    """Get all themes for a ticker."""
    try:
        from theme_registry import get_themes_for_ticker

        ticker = ticker.upper()
        themes = get_themes_for_ticker(ticker)

        return jsonify({
            'ok': True,
            'ticker': ticker,
            'themes': themes,
            'count': len(themes),
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Theme registry not available'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/themes/learn', methods=['POST'])
def api_trigger_learning():
    """Trigger a theme learning cycle."""
    try:
        from theme_learner import get_learner

        learner = get_learner()

        # Get summary before triggering
        summary = learner.get_summary()

        return jsonify({
            'ok': True,
            'message': 'Learning cycle will run on next scan',
            'current_state': summary,
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Theme learner not available'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/themes/learner/status')
def api_learner_status():
    """Get theme learner status."""
    try:
        from theme_learner import get_learner
        from dataclasses import asdict

        learner = get_learner()
        health = learner.run_health_check()

        return jsonify({
            'ok': True,
            'health': asdict(health),
            'summary': learner.get_summary(),
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Theme learner not available'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/universe/status')
def api_universe_status():
    """Get universe manager status."""
    try:
        from universe_manager import get_universe_manager
        from dataclasses import asdict

        um = get_universe_manager()
        health = um.run_health_check()

        return jsonify({
            'ok': True,
            'health': asdict(health),
            'sp500_count': health.sp500_count,
            'nasdaq100_count': health.nasdaq100_count,
            'total_unique': health.total_unique,
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Universe manager not available'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/universe/tickers')
def api_universe_tickers():
    """Get current universe tickers."""
    try:
        from universe_manager import get_universe_manager

        um = get_universe_manager()

        index = request.args.get('index', 'all')

        if index == 'sp500':
            tickers = um.fetch_sp500()
        elif index == 'nasdaq100':
            tickers = um.fetch_nasdaq100()
        elif index == 'breadth':
            tickers = um.get_breadth_universe()
        else:
            sp500 = um.fetch_sp500()
            nasdaq100 = um.fetch_nasdaq100()
            tickers = list(set(sp500 + nasdaq100))

        return jsonify({
            'ok': True,
            'index': index,
            'tickers': tickers,
            'count': len(tickers),
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Universe manager not available'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/universe/refresh', methods=['POST'])
def api_universe_refresh():
    """Force refresh universe data."""
    try:
        from universe_manager import get_universe_manager

        um = get_universe_manager()
        um.clear_cache()

        # Trigger fresh fetch
        sp500 = um.fetch_sp500()
        nasdaq100 = um.fetch_nasdaq100()

        return jsonify({
            'ok': True,
            'message': 'Universe refreshed',
            'sp500_count': len(sp500),
            'nasdaq100_count': len(nasdaq100),
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Universe manager not available'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/deepseek/status')
def api_deepseek_status():
    """Get DeepSeek AI status (legacy endpoint)."""
    # Redirect to unified AI status
    return api_ai_status()


@app.route('/api/ai/status')
def api_ai_status():
    """Get unified AI service status (DeepSeek + xAI)."""
    try:
        from src.services.ai_service import get_ai_service

        service = get_ai_service()
        status = service.get_status()

        return jsonify({
            'ok': True,
            **status,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'AI service not available'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/ai/health')
def api_ai_health():
    """Run health check on all AI providers."""
    try:
        from src.services.ai_service import get_ai_service

        service = get_ai_service()
        health = service.health_check()

        return jsonify({
            'ok': True,
            **health
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'AI service not available'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/options/<ticker>')
def api_options(ticker):
    """Get options flow data for a ticker."""
    try:
        from src.data.polygon_provider import (
            get_options_flow_summary_sync,
            analyze_unusual_options_sync
        )

        ticker = ticker.upper()

        # Get options flow summary
        flow = get_options_flow_summary_sync(ticker)
        unusual = analyze_unusual_options_sync(ticker, volume_threshold=2.0)

        return jsonify({
            'ok': True,
            'ticker': ticker,
            'flow': flow,
            'unusual_activity': unusual,
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Options data not available: {e}'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/options/unusual')
def api_options_unusual():
    """Get unusual options activity across watchlist."""
    try:
        from src.data.polygon_provider import analyze_unusual_options_sync

        # Get top tickers to check
        tickers = request.args.get('tickers', 'NVDA,AMD,AAPL,TSLA,META,GOOGL,AMZN,MSFT').split(',')
        threshold = float(request.args.get('threshold', 2.0))

        results = []
        for ticker in tickers[:20]:  # Limit to 20
            try:
                unusual = analyze_unusual_options_sync(ticker.strip().upper(), volume_threshold=threshold)
                if unusual and unusual.get('has_unusual_activity'):
                    results.append({
                        'ticker': ticker.strip().upper(),
                        **unusual
                    })
            except Exception:
                continue

        # Sort by total unusual volume
        results.sort(key=lambda x: x.get('total_unusual_volume', 0), reverse=True)

        return jsonify({
            'ok': True,
            'count': len(results),
            'unusual_activity': results[:10],
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Options data not available: {e}'}), 503
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/polygon/status')
def api_polygon_status():
    """Get Polygon.io API status and usage."""
    import os

    polygon_key = os.environ.get('POLYGON_API_KEY', '')
    has_key = bool(polygon_key and len(polygon_key) > 10)

    status = {
        'ok': True,
        'polygon_configured': has_key,
        'features': {
            'price_data': has_key,
            'options_data': has_key,
            'news': has_key,
            'financials': has_key,
            'dividends': has_key,
            'splits': has_key,
            'technical_indicators': has_key,
            'ticker_universe': has_key,
        }
    }

    if has_key:
        try:
            from src.data.polygon_provider import PolygonProvider
            import asyncio

            async def test_polygon():
                provider = PolygonProvider()
                # Quick test
                quote = await provider.get_quote('AAPL')
                await provider.close()
                return quote is not None

            status['api_working'] = asyncio.run(test_polygon())
        except Exception as e:
            status['api_working'] = False
            status['error'] = str(e)

    return jsonify(status)


@app.route('/api/status')
def api_status():
    """
    Comprehensive API status endpoint showing all integrations.

    Returns status of:
    - AI providers (DeepSeek, xAI/Grok)
    - Data providers (Polygon, Finnhub, Tiingo, Alpha Vantage, FRED)
    - SEC EDGAR (always available)
    - Telegram
    """
    import os
    from config import config

    status = {
        'ok': True,
        'timestamp': datetime.now().isoformat(),
        'services': {}
    }

    # AI Providers
    status['services']['ai'] = {
        'deepseek': {
            'configured': config.ai.has_deepseek,
            'model': config.ai.model if config.ai.has_deepseek else None,
            'description': 'Primary AI for analysis and insights'
        },
        'xai_grok': {
            'configured': config.ai.has_xai,
            'model': config.ai.xai_model if config.ai.has_xai else None,
            'description': 'Secondary AI, optimized for heavy tasks'
        }
    }

    # Polygon
    polygon_key = os.environ.get('POLYGON_API_KEY', '')
    polygon_configured = bool(polygon_key and len(polygon_key) > 10)
    status['services']['polygon'] = {
        'configured': polygon_configured,
        'features': ['price_data', 'options_flow', 'news', 'financials', 'universe'] if polygon_configured else [],
        'description': 'Premium market data and options flow'
    }

    # Data Providers from utils/data_providers.py
    try:
        from utils.data_providers import check_provider_status
        providers = check_provider_status()
        status['services']['data_providers'] = {
            'finnhub': {
                'configured': providers.get('finnhub', False),
                'rate_limit': '60 req/min' if providers.get('finnhub') else None,
                'features': ['real_time_quotes', 'news', 'sentiment', 'earnings'] if providers.get('finnhub') else [],
                'description': 'Real-time quotes, news, and sentiment'
            },
            'tiingo': {
                'configured': providers.get('tiingo', False),
                'rate_limit': '1000 req/day' if providers.get('tiingo') else None,
                'features': ['eod_prices', 'news', 'fundamentals'] if providers.get('tiingo') else [],
                'description': 'EOD prices and curated news'
            },
            'alpha_vantage': {
                'configured': providers.get('alpha_vantage', False),
                'rate_limit': '25 req/day' if providers.get('alpha_vantage') else None,
                'features': ['fundamentals', 'technical_indicators', 'earnings'] if providers.get('alpha_vantage') else [],
                'description': 'Company fundamentals and technicals'
            },
            'fred': {
                'configured': providers.get('fred', False),
                'rate_limit': 'unlimited' if providers.get('fred') else None,
                'features': ['economic_indicators', 'interest_rates', 'employment'] if providers.get('fred') else [],
                'description': 'Federal Reserve economic data'
            },
            'sec_edgar': {
                'configured': True,  # Always available, no key needed
                'rate_limit': 'unlimited',
                'features': ['filings', 'insider_trades', 'institutional_holdings'],
                'description': 'Official SEC filings and transactions'
            }
        }
    except ImportError:
        status['services']['data_providers'] = {'error': 'data_providers module not available'}

    # Telegram
    status['services']['telegram'] = {
        'configured': config.telegram.is_configured,
        'chat_id_set': bool(config.telegram.chat_id),
        'description': 'Telegram bot for alerts and commands'
    }

    # Summary counts
    ai_count = sum(1 for k, v in status['services'].get('ai', {}).items() if isinstance(v, dict) and v.get('configured'))
    data_count = sum(1 for k, v in status['services'].get('data_providers', {}).items() if isinstance(v, dict) and v.get('configured'))

    status['summary'] = {
        'ai_providers': f"{ai_count}/2 configured",
        'data_providers': f"{data_count}/5 configured",
        'polygon': 'configured' if polygon_configured else 'not configured',
        'telegram': 'configured' if config.telegram.is_configured else 'not configured',
        'total_apis': ai_count + data_count + (1 if polygon_configured else 0) + (1 if config.telegram.is_configured else 0)
    }

    return jsonify(status)


# =============================================================================
# SEC EDGAR API ENDPOINTS
# =============================================================================

@app.route('/api/sec/filings/<ticker>')
def api_sec_filings(ticker):
    """Get recent SEC filings for a ticker."""
    try:
        from src.data.sec_edgar import SECEdgarClient

        days = request.args.get('days', 60, type=int)
        client = SECEdgarClient()
        filings = client.get_company_filings(ticker.upper(), days_back=days)

        return jsonify({
            'ok': True,
            'ticker': ticker.upper(),
            'filings': [f.to_dict() for f in filings],
            'count': len(filings),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"SEC filings API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/sec/ma-check/<ticker>')
def api_sec_ma_check(ticker):
    """Check M&A activity for a ticker based on SEC filings."""
    try:
        from src.data.sec_edgar import detect_ma_activity

        result = detect_ma_activity(ticker.upper())

        return jsonify({
            'ok': True,
            **result,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"M&A check API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/sec/insider/<ticker>')
def api_sec_insider(ticker):
    """Get insider transactions (Form 4) for a ticker."""
    try:
        from src.data.sec_edgar import SECEdgarClient

        days = request.args.get('days', 90, type=int)
        client = SECEdgarClient()
        transactions = client.get_insider_transactions(ticker.upper(), days_back=days)

        return jsonify({
            'ok': True,
            'ticker': ticker.upper(),
            'transactions': transactions,
            'count': len(transactions),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Insider API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/sec/deals')
def api_sec_deals():
    """Get tracked M&A deals with current spreads."""
    try:
        from src.analysis.corporate_actions import DealTracker
        from src.data.polygon_provider import get_previous_close_sync

        tracker = DealTracker()
        deals = tracker.get_active_deals()

        # Enrich with current prices and spreads
        enriched_deals = []
        for deal in deals:
            target = deal.get('target', '')
            deal_price = deal.get('deal_price', 0)

            # Get current price
            current_price = 0
            try:
                quote = get_previous_close_sync(target)
                current_price = quote.get('close', 0) if quote else 0
            except:
                pass

            # Calculate spread
            if current_price > 0 and deal_price > 0:
                spread = deal_price - current_price
                spread_pct = (spread / current_price) * 100
            else:
                spread = 0
                spread_pct = 0

            enriched_deals.append({
                **deal,
                'current_price': round(current_price, 2),
                'spread': round(spread, 2),
                'spread_pct': round(spread_pct, 2),
                'signal': 'attractive' if spread_pct > 5 else 'fair' if spread_pct > 2 else 'tight'
            })

        return jsonify({
            'ok': True,
            'deals': enriched_deals,
            'count': len(enriched_deals),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Deals API error: {e}")
        return jsonify({'ok': False, 'error': str(e), 'deals': []})


@app.route('/api/sec/deals/add', methods=['POST'])
def api_sec_deals_add():
    """Add a new M&A deal to track."""
    try:
        from src.analysis.corporate_actions import DealTracker

        data = request.get_json() or {}
        target = data.get('target', '').upper()
        acquirer = data.get('acquirer', '').upper()
        deal_price = float(data.get('deal_price', 0))

        if not target or not acquirer or deal_price <= 0:
            return jsonify({'ok': False, 'error': 'Missing target, acquirer, or deal_price'})

        tracker = DealTracker()
        deal = tracker.add_deal(
            target=target,
            acquirer=acquirer,
            deal_price=deal_price,
            deal_type=data.get('deal_type', 'cash'),
            expected_close=data.get('expected_close'),
            notes=data.get('notes', '')
        )

        return jsonify({
            'ok': True,
            'deal': deal,
            'message': f'Deal added: {target} <- {acquirer} @ ${deal_price}'
        })
    except Exception as e:
        logger.error(f"Add deal API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/sec/ma-radar')
def api_sec_ma_radar():
    """Scan watchlist for M&A activity - used by dashboard."""
    try:
        from src.data.sec_edgar import detect_ma_activity

        # Get tickers from scan results or use defaults
        tickers = []
        try:
            from pathlib import Path
            scan_files = list(Path('.').glob('scan_*.csv'))
            if scan_files:
                import pandas as pd
                latest = max(scan_files, key=lambda x: x.stat().st_mtime)
                df = pd.read_csv(latest)
                tickers = df['ticker'].head(20).tolist()
        except:
            pass

        if not tickers:
            tickers = ['NVDA', 'AMD', 'AAPL', 'MSFT', 'GOOGL', 'META', 'TSLA', 'AMZN']

        results = []
        for ticker in tickers[:15]:
            try:
                result = detect_ma_activity(ticker)
                results.append({
                    'ticker': ticker,
                    'score': result.get('ma_score', 0),
                    'has_activity': result.get('has_activity', False),
                    'signals': result.get('signals', [])[:2]  # Limit signals
                })
            except:
                continue

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)

        return jsonify({
            'ok': True,
            'radar': results,
            'high_activity': [r for r in results if r['score'] >= 30],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"M&A radar API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# GOOGLE TRENDS API ENDPOINTS
# =============================================================================

@app.route('/api/trends/themes')
def api_trends_themes():
    """Get theme momentum report from Google Trends."""
    try:
        from src.data.google_trends import (
            get_theme_momentum_report,
            HAS_PYTRENDS
        )

        if not HAS_PYTRENDS:
            return jsonify({
                'ok': False,
                'error': 'pytrends not installed'
            })

        report = get_theme_momentum_report()
        return jsonify(report)

    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Trends themes API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trends/keyword/<keyword>')
def api_trends_keyword(keyword):
    """Get trend score for a specific keyword."""
    try:
        from src.data.google_trends import get_trend_score, HAS_PYTRENDS

        if not HAS_PYTRENDS:
            return jsonify({
                'ok': False,
                'error': 'pytrends not installed'
            })

        result = get_trend_score(keyword)
        return jsonify({
            'ok': True,
            **result
        })

    except Exception as e:
        logger.error(f"Trends keyword API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trends/breakouts')
def api_trends_breakouts():
    """Get breakout searches from Google Trends."""
    try:
        from src.data.google_trends import get_breakout_searches, HAS_PYTRENDS

        if not HAS_PYTRENDS:
            return jsonify({
                'ok': False,
                'error': 'pytrends not installed'
            })

        breakouts = get_breakout_searches()
        return jsonify({
            'ok': True,
            'breakouts': breakouts,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Trends breakouts API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# THEME INTELLIGENCE API ENDPOINTS
# =============================================================================

@app.route('/api/theme-intel/radar')
def api_theme_intel_radar():
    """Get theme radar data for dashboard visualization."""
    try:
        from src.intelligence.theme_intelligence import get_theme_radar

        radar = get_theme_radar()
        return jsonify(radar)

    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Theme radar API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/theme-intel/analyze')
def api_theme_intel_analyze():
    """Run full theme intelligence analysis."""
    try:
        from src.intelligence.theme_intelligence import analyze_all_themes

        quick = request.args.get('quick', 'true').lower() == 'true'
        report = analyze_all_themes(quick=quick)
        return jsonify(report)

    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Theme analyze API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/theme-intel/alerts')
def api_theme_intel_alerts():
    """Get recent theme alerts."""
    try:
        from src.intelligence.theme_intelligence import get_breakout_alerts
        from dataclasses import asdict

        alerts = get_breakout_alerts()
        return jsonify({
            'ok': True,
            'alerts': [asdict(a) if hasattr(a, '__dataclass_fields__') else a for a in alerts],
            'timestamp': datetime.now().isoformat()
        })

    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Theme alerts API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/theme-intel/ticker/<ticker>')
def api_theme_intel_ticker(ticker):
    """Get theme boost for a specific ticker."""
    try:
        from src.intelligence.theme_intelligence import get_ticker_theme_boost

        boost_data = get_ticker_theme_boost(ticker)
        return jsonify({
            'ok': True,
            **boost_data
        })

    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Theme ticker API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/theme-intel/theme/<theme_id>')
def api_theme_intel_theme(theme_id):
    """Get detailed history for a specific theme."""
    try:
        from src.intelligence.theme_intelligence import get_theme_hub

        hub = get_theme_hub()
        history = hub.get_theme_history(theme_id)
        return jsonify({
            'ok': True,
            **history
        })

    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Theme history API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/theme-intel/run-analysis', methods=['POST'])
def api_theme_intel_run():
    """Trigger theme intelligence analysis (for scheduled jobs)."""
    try:
        from src.intelligence.theme_intelligence import analyze_all_themes

        quick = request.json.get('quick', True) if request.json else True
        report = analyze_all_themes(quick=quick)

        return jsonify({
            'ok': True,
            'summary': report.get('summary', {}),
            'alerts_count': len(report.get('alerts', [])),
            'timestamp': datetime.now().isoformat()
        })

    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Theme run API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# THEME DISCOVERY API ENDPOINTS
# =============================================================================

@app.route('/api/discovery/report')
def api_discovery_report():
    """Get theme discovery report."""
    try:
        from src.intelligence.theme_discovery import get_discovery_report
        return jsonify(get_discovery_report())
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Discovery report API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/discovery/run', methods=['POST'])
def api_discovery_run():
    """Run theme discovery."""
    try:
        from src.intelligence.theme_discovery import discover_themes
        themes = discover_themes()
        return jsonify({
            'ok': True,
            'discovered': len(themes),
            'themes': themes,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Discovery run API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# INSTITUTIONAL FLOW API ENDPOINTS
# =============================================================================

@app.route('/api/institutional/summary')
def api_institutional_summary():
    """Get institutional flow summary for all themes."""
    try:
        from src.intelligence.institutional_flow import get_institutional_summary
        return jsonify(get_institutional_summary())
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Institutional summary API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/institutional/options-flow')
def api_options_flow():
    """Get options flow signals."""
    try:
        from src.intelligence.institutional_flow import get_options_flow
        tickers = request.args.get('tickers')
        if tickers:
            tickers = [t.strip().upper() for t in tickers.split(',')]
        signals = get_options_flow(tickers)
        return jsonify({
            'ok': True,
            'signals': signals,
            'count': len(signals),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Options flow API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/institutional/insider-clusters')
def api_insider_clusters():
    """Get insider buying clusters by theme."""
    try:
        from src.intelligence.institutional_flow import get_insider_clusters
        clusters = get_insider_clusters()
        return jsonify({
            'ok': True,
            'clusters': clusters,
            'count': len(clusters),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Insider clusters API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# ROTATION PREDICTOR API ENDPOINTS
# =============================================================================

@app.route('/api/rotation/forecast')
def api_rotation_forecast():
    """Get theme rotation forecast."""
    try:
        from src.intelligence.rotation_predictor import get_rotation_forecast
        return jsonify(get_rotation_forecast())
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Rotation forecast API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/rotation/peak-warnings')
def api_peak_warnings():
    """Get peak warning signals."""
    try:
        from src.intelligence.rotation_predictor import get_peak_warnings
        warnings = get_peak_warnings()
        return jsonify({
            'ok': True,
            'warnings': warnings,
            'count': len(warnings),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Peak warnings API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/rotation/reversions')
def api_reversions():
    """Get reversion candidates."""
    try:
        from src.intelligence.rotation_predictor import get_reversion_candidates
        candidates = get_reversion_candidates()
        return jsonify({
            'ok': True,
            'candidates': candidates,
            'count': len(candidates),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Reversions API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/rotation/alerts')
def api_rotation_alerts():
    """Get rotation alerts."""
    try:
        from src.intelligence.rotation_predictor import get_rotation_alerts
        alerts = get_rotation_alerts()
        return jsonify({
            'ok': True,
            'alerts': alerts,
            'count': len(alerts),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Rotation alerts API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# ALTERNATIVE DATA API (Patents & Government Contracts)
# =============================================================================

@app.route('/api/patents/themes')
def api_patents_themes():
    """Get patent activity for all themes."""
    try:
        from src.data.patents import get_patent_intelligence
        intel = get_patent_intelligence()
        data = intel.get_all_themes_patent_activity()
        return jsonify({
            'ok': True,
            'themes': data,
            'count': len(data),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Patents themes API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/patents/company/<ticker>')
def api_patents_company(ticker):
    """Get patent activity for a specific company."""
    try:
        from src.data.patents import get_patent_intelligence
        intel = get_patent_intelligence()
        data = intel.get_company_patents(ticker.upper())
        return jsonify({
            'ok': True,
            'ticker': ticker.upper(),
            'patents': data,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Patents company API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/patents/theme/<theme>')
def api_patents_theme(theme):
    """Get patent activity for a specific theme."""
    try:
        from src.data.patents import get_patent_intelligence
        intel = get_patent_intelligence()
        data = intel.get_theme_patent_activity(theme.lower())
        return jsonify({
            'ok': True,
            'theme': theme.lower(),
            'activity': data,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Patents theme API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/contracts/themes')
def api_contracts_themes():
    """Get government contract activity for all themes."""
    try:
        from src.data.gov_contracts import get_contract_intelligence
        intel = get_contract_intelligence()
        data = intel.get_all_themes_contract_activity()
        return jsonify({
            'ok': True,
            'themes': data,
            'count': len(data),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Contracts themes API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/contracts/company/<ticker>')
def api_contracts_company(ticker):
    """Get government contracts for a specific company."""
    try:
        from src.data.gov_contracts import get_contract_intelligence
        intel = get_contract_intelligence()
        data = intel.get_company_contracts(ticker.upper())
        return jsonify({
            'ok': True,
            'ticker': ticker.upper(),
            'contracts': data,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Contracts company API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/contracts/theme/<theme>')
def api_contracts_theme(theme):
    """Get government contracts for a specific theme."""
    try:
        from src.data.gov_contracts import get_contract_intelligence
        intel = get_contract_intelligence()
        data = intel.get_theme_contract_activity(theme.lower())
        return jsonify({
            'ok': True,
            'theme': theme.lower(),
            'activity': data,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Contracts theme API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/contracts/recent')
def api_contracts_recent():
    """Get recent large government contracts."""
    try:
        from src.data.gov_contracts import get_contract_intelligence
        intel = get_contract_intelligence()
        min_amount = float(request.args.get('min_amount', 10000000))  # Default $10M
        days_back = int(request.args.get('days_back', 30))
        data = intel.search_contracts(min_amount=min_amount, days_back=days_back)
        return jsonify({
            'ok': True,
            'contracts': data,
            'count': len(data),
            'min_amount': min_amount,
            'days_back': days_back,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Import error: {e}'})
    except Exception as e:
        logger.error(f"Recent contracts API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# HARD DATA CONVICTION SCANNER API
# =============================================================================

@app.route('/api/conviction/<ticker>')
def api_conviction_ticker(ticker):
    """
    Get conviction score for a single ticker.

    Combines:
    - Insider activity (SEC Form 4)
    - Options flow (Polygon)
    - Patents (PatentsView)
    - Gov contracts
    - Sentiment (validation)
    - Technical (entry timing)

    Returns conviction score 0-100 with recommendation.
    """
    try:
        from src.intelligence.hard_data_scanner import get_hard_data_scanner

        scanner = get_hard_data_scanner()
        result = scanner.scan_ticker(ticker.upper())

        return jsonify({
            'ok': True,
            **result.to_dict()
        })
    except ImportError as e:
        logger.error(f"Conviction scanner import error: {e}")
        return jsonify({'ok': False, 'error': f'Scanner not available: {e}'}), 503
    except Exception as e:
        logger.error(f"Conviction scan error for {ticker}: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/conviction/scan')
def api_conviction_scan():
    """
    Scan multiple tickers for conviction scores.

    Query params:
    - tickers: Comma-separated list (default: top institutional)
    - min_score: Minimum score to return (default: 50)

    Returns list sorted by conviction score descending.
    """
    try:
        from src.intelligence.hard_data_scanner import get_hard_data_scanner

        scanner = get_hard_data_scanner()

        tickers_param = request.args.get('tickers', '')
        min_score = float(request.args.get('min_score', 50))

        if tickers_param:
            tickers = [t.strip().upper() for t in tickers_param.split(',')]
        else:
            # Default watchlist
            tickers = ['NVDA', 'AMD', 'PLTR', 'LMT', 'CRWD', 'META', 'TSLA', 'LLY']

        results = scanner.scan_watchlist(tickers, min_score=min_score)

        return jsonify({
            'ok': True,
            'results': [r.to_dict() for r in results],
            'count': len(results),
            'min_score': min_score,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Scanner not available: {e}'}), 503
    except Exception as e:
        logger.error(f"Conviction scan error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/conviction/alerts')
def api_conviction_alerts():
    """
    Get high-conviction alerts (score >= 70).

    These are the best setups where multiple hard data signals align.
    """
    try:
        from src.intelligence.hard_data_scanner import get_hard_data_scanner

        scanner = get_hard_data_scanner()
        min_score = float(request.args.get('min_score', 70))

        results = scanner.get_high_conviction_alerts(min_score=min_score)

        return jsonify({
            'ok': True,
            'alerts': [r.to_dict() for r in results],
            'count': len(results),
            'threshold': min_score,
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Scanner not available: {e}'}), 503
    except Exception as e:
        logger.error(f"Conviction alerts error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


# =============================================================================
# SOCIAL SENTIMENT API
# =============================================================================

@app.route('/api/social/<ticker>')
def api_social_sentiment(ticker):
    """
    Get social sentiment for a ticker from all sources.

    Sources:
    - StockTwits: Retail trader sentiment
    - Reddit: r/wallstreetbets, r/stocks, r/investing, r/options
    - X/Twitter: Via xAI x_search (engagement-weighted) - requires XAI_API_KEY
    - SEC: 8-K filings, insider activity
    """
    try:
        from src.scoring.story_scorer import get_social_buzz_score

        ticker = ticker.upper()
        # X/Twitter enabled by default (disable with ?include_x=false)
        include_x = request.args.get('include_x', 'true').lower() == 'true'

        # Debug: Add timing
        import time
        start_time = time.time()

        result = get_social_buzz_score(ticker, include_x=include_x)

        elapsed = time.time() - start_time
        logger.info(f"Social sentiment for {ticker} completed in {elapsed:.1f}s")

        return jsonify({
            'ok': True,
            'ticker': ticker,
            'x_enabled': include_x,
            'elapsed_seconds': round(elapsed, 1),
            **result,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Social sentiment error for {ticker}: {e}\n{tb}")
        return jsonify({'ok': False, 'error': str(e), 'error_type': type(e).__name__, 'traceback': tb[:1000]}), 500


@app.route('/api/social/x/<ticker>')
def api_x_sentiment(ticker):
    """
    Get X/Twitter sentiment only for a ticker.

    Uses xAI x_search with engagement-weighted scoring.
    Requires XAI_API_KEY environment variable.
    """
    try:
        from src.scoring.story_scorer import fetch_x_sentiment
        import json

        ticker = ticker.upper()
        result = fetch_x_sentiment(ticker, days_back=7)

        # Ensure result is JSON serializable
        try:
            json.dumps(result)
        except TypeError as te:
            logger.error(f"X sentiment serialization error: {te}")
            return jsonify({'ok': False, 'error': f'Serialization error: {te}'}), 500

        return jsonify({
            'ok': True,
            'ticker': ticker,
            **result,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        import traceback
        logger.error(f"X sentiment error for {ticker}: {e}\n{traceback.format_exc()}")
        return jsonify({'ok': False, 'error': str(e), 'traceback': traceback.format_exc()[:500]}), 500


@app.route('/api/social/reddit/<ticker>')
def api_reddit_sentiment(ticker):
    """
    Get Reddit sentiment using direct API.

    Note: xAI web_search has reliability issues, using direct Reddit JSON API.
    """
    try:
        from src.scoring.story_scorer import _fetch_reddit_direct

        ticker = ticker.upper()
        result = _fetch_reddit_direct(ticker)

        return jsonify({
            'ok': True,
            'ticker': ticker,
            'source': 'direct_api',
            **result,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        import traceback
        return jsonify({
            'ok': False,
            'error': str(e),
            'traceback': traceback.format_exc()[:500]
        }), 500


# =============================================================================
# SUPPLY CHAIN DISCOVERY API
# =============================================================================

@app.route('/api/supplychain/themes')
def api_supplychain_themes():
    """
    Get discovered themes with supply chain opportunities.

    Returns themes with lagging plays that haven't moved yet.
    Key insight: Leaders move first, supply chain follows.
    """
    try:
        from src.intelligence.theme_discovery_engine import get_theme_discovery_engine

        engine = get_theme_discovery_engine()
        summary = engine.get_discovery_summary()

        return jsonify({
            'ok': True,
            'themes': summary.get('themes', []),
            'total_opportunities': summary.get('total_opportunities', 0),
            'themes_analyzed': summary.get('themes_analyzed', 0),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Supply chain engine not available: {e}'}), 503
    except Exception as e:
        logger.error(f"Supply chain themes error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/supplychain/<theme_id>')
def api_supplychain_analyze(theme_id):
    """
    Analyze supply chain for a specific theme.

    Returns full supply chain breakdown with opportunity scores.
    """
    try:
        from src.intelligence.theme_discovery_engine import get_theme_discovery_engine

        engine = get_theme_discovery_engine()
        theme = engine.analyze_supply_chain(theme_id)

        if not theme:
            return jsonify({'ok': False, 'error': f'Theme not found: {theme_id}'}), 404

        return jsonify({
            'ok': True,
            'theme': theme.to_dict(),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Supply chain engine not available: {e}'}), 503
    except Exception as e:
        logger.error(f"Supply chain analyze error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/supplychain/<theme_id>/laggards')
def api_supplychain_laggards(theme_id):
    """
    Get lagging plays for a theme.

    These are stocks that are part of a hot theme but haven't moved yet.
    """
    try:
        from src.intelligence.theme_discovery_engine import get_theme_discovery_engine
        from dataclasses import asdict

        engine = get_theme_discovery_engine()
        laggards = engine.find_lagging_plays(theme_id)

        return jsonify({
            'ok': True,
            'theme_id': theme_id,
            'laggards': [asdict(l) for l in laggards],
            'count': len(laggards),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Supply chain engine not available: {e}'}), 503
    except Exception as e:
        logger.error(f"Supply chain laggards error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/supplychain/known-themes')
def api_supplychain_known_themes():
    """
    Get list of known themes with pre-mapped supply chains.
    """
    try:
        from src.intelligence.theme_discovery_engine import get_theme_discovery_engine

        engine = get_theme_discovery_engine()
        themes = list(engine.SUPPLY_CHAIN_MAP.keys())

        return jsonify({
            'ok': True,
            'themes': [
                {
                    'id': theme_id,
                    'name': theme_id.replace('_', ' ').title(),
                    'members': sum(len(v) for v in engine.SUPPLY_CHAIN_MAP[theme_id].values())
                }
                for theme_id in themes
            ],
            'count': len(themes),
            'timestamp': datetime.now().isoformat()
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Supply chain engine not available: {e}'}), 503
    except Exception as e:
        logger.error(f"Supply chain known themes error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/supplychain/ai-debug')
def api_supplychain_ai_debug():
    """Debug endpoint to test AI discovery components step by step."""
    debug_info = {'steps': []}

    try:
        # Step 1: Import
        debug_info['steps'].append('1. Starting import...')
        from src.intelligence.theme_discovery_engine import get_theme_discovery_engine
        debug_info['steps'].append('1. Import succeeded')

        # Step 2: Get engine
        debug_info['steps'].append('2. Getting engine...')
        engine = get_theme_discovery_engine()
        debug_info['steps'].append('2. Engine created')

        # Step 3: Get story scores
        debug_info['steps'].append('3. Getting story scores...')
        story_scores = engine._get_story_scores()
        debug_info['story_score_count'] = len(story_scores)
        debug_info['steps'].append(f'3. Got {len(story_scores)} story scores')

        # Step 4: Gather realtime data (fast mode)
        debug_info['steps'].append('4. Gathering realtime data (fast mode)...')
        realtime_data = engine._gather_realtime_data(fast_mode=True)
        debug_info['realtime_keys'] = list(realtime_data.keys())
        debug_info['steps'].append(f'4. Got realtime data keys: {list(realtime_data.keys())}')

        # Step 5: Try JSON serialization
        import json
        debug_info['steps'].append('5. Testing JSON serialization...')
        json.dumps(realtime_data)
        debug_info['steps'].append('5. JSON serialization OK')

        # Step 6: Test fallback static analysis
        debug_info['steps'].append('6. Testing fallback static analysis...')
        fallback = engine._fallback_static_analysis()
        debug_info['fallback_count'] = len(fallback)
        debug_info['steps'].append(f'6. Fallback returned {len(fallback)} opportunities')

        # Step 7: Test full get_ai_opportunities
        debug_info['steps'].append('7. Testing get_ai_opportunities...')
        result = engine.get_ai_opportunities()
        debug_info['result_keys'] = list(result.keys())
        debug_info['result_source'] = result.get('source', 'unknown')
        debug_info['steps'].append(f'7. get_ai_opportunities returned source: {result.get("source")}')

        # Step 8: Serialize result
        debug_info['steps'].append('8. Serializing result...')
        json.dumps(result)
        debug_info['steps'].append('8. Result serialization OK')

        debug_info['ok'] = True
        return jsonify(debug_info)

    except Exception as e:
        import traceback
        debug_info['error'] = str(e)
        debug_info['traceback'] = traceback.format_exc()
        debug_info['ok'] = False
        return jsonify(debug_info), 500


@app.route('/api/supplychain/ai-discover')
def api_supplychain_ai_discover():
    """
    AI-driven real-time supply chain opportunity discovery.

    Uses AI to analyze:
    - Recent news and headlines
    - Price movements and volume spikes
    - Social buzz (StockTwits)
    - SEC filings
    - Sector performance

    Returns AI-reasoned opportunities with supply chain connections.
    """
    try:
        from src.intelligence.theme_discovery_engine import get_theme_discovery_engine
        import json

        engine = get_theme_discovery_engine()
        result = engine.get_ai_opportunities()

        # Ensure result is JSON serializable
        try:
            json.dumps(result)
        except TypeError as te:
            logger.error(f"AI discovery serialization error: {te}")
            return jsonify({'ok': False, 'error': f'Serialization error: {te}'}), 500

        return jsonify({
            'ok': True,
            **result
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Supply chain engine not available: {e}'}), 503
    except Exception as e:
        logger.error(f"AI discovery error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/supplychain/ai-analyze')
def api_supplychain_ai_analyze():
    """
    Full AI analysis of market data for theme discovery.

    Returns detailed AI reasoning about:
    - Emerging themes detected
    - Supply chain relationships
    - Lagging opportunities
    - Top actionable ideas
    """
    try:
        from src.intelligence.theme_discovery_engine import get_theme_discovery_engine
        import json

        engine = get_theme_discovery_engine()
        result = engine.analyze_with_ai()

        # Remove raw_data as it may contain non-serializable objects
        result.pop('raw_data', None)

        if 'error' in result:
            return jsonify({
                'ok': False,
                'error': result.get('error'),
                'raw_response': result.get('raw_response', '')[:200]
            }), 500

        # Ensure result is JSON serializable
        try:
            json.dumps(result)
        except TypeError as te:
            logger.error(f"AI analyze serialization error: {te}")
            return jsonify({'ok': False, 'error': f'Serialization error: {te}'}), 500

        return jsonify({
            'ok': True,
            **result
        })
    except ImportError as e:
        return jsonify({'ok': False, 'error': f'Supply chain engine not available: {e}'}), 503
    except Exception as e:
        logger.error(f"AI analyze error: {e}", exc_info=True)
        return jsonify({'ok': False, 'error': str(e)}), 500


# =============================================================================
# COMBINED INTELLIGENCE API
# =============================================================================

@app.route('/api/intelligence/summary')
def api_intelligence_summary():
    """Get combined intelligence summary."""
    try:
        summary = {
            'ok': True,
            'timestamp': datetime.now().isoformat()
        }

        # Theme Intelligence
        try:
            from src.intelligence.theme_intelligence import get_theme_radar
            radar = get_theme_radar()
            if radar.get('ok'):
                summary['theme_radar'] = radar.get('radar', [])[:10]
        except:
            pass

        # Institutional Flow
        try:
            from src.intelligence.institutional_flow import get_institutional_summary
            inst = get_institutional_summary()
            if inst.get('ok'):
                summary['institutional'] = {
                    'bullish': inst.get('top_bullish', [])[:5],
                    'bearish': inst.get('top_bearish', [])[:5]
                }
        except:
            pass

        # Rotation Forecast
        try:
            from src.intelligence.rotation_predictor import get_rotation_forecast
            rotation = get_rotation_forecast()
            if rotation.get('ok'):
                summary['rotation'] = {
                    'in': len(rotation.get('rotating_in', [])),
                    'out': len(rotation.get('rotating_out', [])),
                    'rotating_in': rotation.get('rotating_in', [])[:3],
                    'rotating_out': rotation.get('rotating_out', [])[:3]
                }
        except:
            pass

        # Discovery
        try:
            from src.intelligence.theme_discovery import get_discovery_report
            discovery = get_discovery_report()
            if discovery.get('ok'):
                summary['discovery'] = {
                    'total': discovery.get('summary', {}).get('total_discovered', 0),
                    'validated': discovery.get('summary', {}).get('validated', 0)
                }
        except:
            pass

        return jsonify(summary)

    except Exception as e:
        logger.error(f"Intelligence summary API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/intelligence/x-sentiment')
def api_intelligence_x_sentiment():
    """Get X/Twitter sentiment data for dashboard."""
    try:
        from src.intelligence.x_intelligence import get_x_intelligence

        x_intel = get_x_intelligence()

        # Get recent scan results to find tickers with X sentiment
        tickers_with_sentiment = []

        # Try to get from recent scan cache
        try:
            import glob
            scan_files = sorted(glob.glob('scan_*.csv'), reverse=True)
            if scan_files:
                import pandas as pd
                df = pd.read_csv(scan_files[0])
                top_tickers = df.head(20)['ticker'].tolist() if 'ticker' in df.columns else []

                for ticker in top_tickers[:10]:  # Limit to top 10
                    try:
                        sentiment = x_intel.get_ticker_sentiment(ticker)
                        tickers_with_sentiment.append({
                            'ticker': ticker,
                            'sentiment': sentiment.sentiment,
                            'sentiment_score': sentiment.sentiment_score,
                            'mentions': sentiment.mentions,
                            'viral_posts': len(sentiment.viral_posts)
                        })
                    except:
                        continue
        except:
            pass

        return jsonify({
            'ok': True,
            'tickers': tickers_with_sentiment,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"X sentiment API error: {e}")
        return jsonify({'ok': False, 'error': str(e), 'tickers': []})


@app.route('/api/intelligence/google-trends')
def api_intelligence_google_trends():
    """Get Google Trends data for dashboard."""
    try:
        from src.intelligence.google_trends import get_trends_intelligence

        trends = get_trends_intelligence()

        # Get tickers from recent scan
        tickers_with_trends = []

        try:
            import glob
            scan_files = sorted(glob.glob('scan_*.csv'), reverse=True)
            if scan_files:
                import pandas as pd
                df = pd.read_csv(scan_files[0])
                top_tickers = df.head(20)['ticker'].tolist() if 'ticker' in df.columns else []

                for ticker in top_tickers[:10]:  # Limit to top 10
                    try:
                        trend_data = trends.get_ticker_trend(ticker)
                        tickers_with_trends.append({
                            'ticker': ticker,
                            'search_interest': trend_data.search_interest,
                            'trend_direction': trend_data.trend_direction,
                            'is_breakout': trend_data.is_breakout
                        })
                    except:
                        continue
        except:
            pass

        return jsonify({
            'ok': True,
            'tickers': tickers_with_trends,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Google Trends API error: {e}")
        return jsonify({'ok': False, 'error': str(e), 'tickers': []})


@app.route('/api/intelligence/supply-chain/<theme_id>')
def api_intelligence_supply_chain(theme_id):
    """Get supply chain relationships for a theme."""
    try:
        from src.intelligence.relationship_graph import get_theme_basket

        chain = get_theme_basket(theme_id)

        return jsonify({
            'ok': True,
            'theme_id': theme_id,
            'chain': chain,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Supply chain API error: {e}")
        return jsonify({'ok': False, 'error': str(e), 'chain': {}})


@app.route('/api/intelligence/catalyst-breakdown')
def api_intelligence_catalyst_breakdown():
    """Get catalyst sources distribution."""
    try:
        # Calculate catalyst sources from recent scan data
        sources = {
            'X Sentiment': 10,
            'Google Trends': 10,
            'Contracts': 10,
            'Patents': 10,
            'Supply Chain': 10,
            'News': 15,
            'SEC': 10,
            'Social': 10,
            'Price': 10,
            'Volume': 5
        }

        # Try to get actual data from recent scans
        try:
            import glob
            scan_files = sorted(glob.glob('scan_*.csv'), reverse=True)
            if scan_files:
                import pandas as pd
                df = pd.read_csv(scan_files[0])

                # Count non-zero components
                component_counts = {}
                for col in df.columns:
                    if 'score' in col.lower() and df[col].notna().sum() > 0:
                        component_counts[col] = int((df[col] > 0).sum())

                # Normalize to percentages
                total = sum(component_counts.values()) if component_counts else 1
                sources = {
                    k.replace('_', ' ').title(): int(v / total * 100)
                    for k, v in component_counts.items()
                }
        except:
            pass

        return jsonify({
            'ok': True,
            'sources': sources,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Catalyst breakdown API error: {e}")
        return jsonify({'ok': False, 'error': str(e), 'sources': {}})


@app.route('/api/intelligence/earnings/<ticker>')
def api_intelligence_earnings(ticker):
    """Get earnings intelligence for a ticker."""
    try:
        from src.scoring.earnings_scorer import get_earnings_scorer

        scorer = get_earnings_scorer()
        features = scorer.get_features(ticker.upper())

        return jsonify({
            'ok': True,
            'ticker': ticker,
            'confidence': features.earnings_confidence,
            'has_earnings_soon': features.has_earnings_soon,
            'days_until': features.days_until_earnings,
            'days_since': features.days_since_earnings,
            'beat_rate': features.beat_rate,
            'avg_surprise': features.avg_surprise,
            'guidance_tone': features.guidance_tone,
            'risk_level': scorer.get_earnings_risk_level(ticker.upper()),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Earnings intelligence API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/intelligence/executive/<ticker>')
def api_intelligence_executive(ticker):
    """Get executive commentary for a ticker."""
    try:
        from src.intelligence.executive_commentary import get_executive_commentary

        commentary = get_executive_commentary(ticker.upper(), days_back=30)

        return jsonify({
            'ok': True,
            'ticker': ticker,
            'overall_sentiment': commentary.overall_sentiment,
            'sentiment_score': commentary.sentiment_score,
            'guidance_tone': commentary.guidance_tone,
            'key_themes': commentary.key_themes,
            'has_recent_commentary': commentary.has_recent_commentary,
            'recent_comments': [
                {
                    'source': c.source,
                    'date': c.date,
                    'sentiment': c.sentiment,
                    'content': c.content[:200]
                }
                for c in commentary.recent_comments[:5]
            ],
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Executive commentary API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# TRADE MANAGEMENT API
# =============================================================================

@app.route('/api/trades')
def api_trades():
    """Get all trades (watchlist + open + closed)."""
    try:
        from src.trading import TradeManager
        tm = TradeManager()

        include_closed = request.args.get('include_closed', 'false').lower() == 'true'

        trades = tm.export_trades(include_closed=include_closed)

        return jsonify({
            'ok': True,
            'trades': trades,
            'summary': tm.get_portfolio_summary()
        })
    except Exception as e:
        logger.error(f"Trades API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/positions')
def api_trades_positions():
    """Get open positions only."""
    try:
        from src.trading import TradeManager
        tm = TradeManager()

        positions = [t.to_dict() for t in tm.get_open_trades()]

        # Add current prices
        for pos in positions:
            try:
                ticker = pos['ticker']
                stock = yf.Ticker(ticker)
                hist = stock.history(period='1d')
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    pos['current_price'] = current_price
                    if pos['average_cost'] > 0:
                        pos['pnl_pct'] = ((current_price - pos['average_cost']) / pos['average_cost']) * 100
                        pos['pnl_value'] = (current_price - pos['average_cost']) * pos['total_shares']
            except:
                pass

        return jsonify({
            'ok': True,
            'positions': positions,
            'count': len(positions)
        })
    except Exception as e:
        logger.error(f"Positions API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/watchlist')
def api_trades_watchlist():
    """Get watchlist items."""
    try:
        from src.trading import TradeManager
        tm = TradeManager()

        watchlist = [t.to_dict() for t in tm.get_watchlist()]

        return jsonify({
            'ok': True,
            'watchlist': watchlist,
            'count': len(watchlist)
        })
    except Exception as e:
        logger.error(f"Watchlist API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/create', methods=['POST'])
def api_trades_create():
    """Create a new trade on watchlist."""
    try:
        from src.trading import TradeManager, ScalingStrategy
        tm = TradeManager()

        data = request.json or {}
        ticker = data.get('ticker', '').upper()
        thesis = data.get('thesis', '')
        theme = data.get('theme', '')
        catalyst = data.get('catalyst', '')
        strategy = data.get('strategy', 'conservative')

        if not ticker:
            return jsonify({'ok': False, 'error': 'Ticker required'})

        # Map strategy string to enum
        strategy_map = {
            'conservative': ScalingStrategy.CONSERVATIVE,
            'aggressive': ScalingStrategy.AGGRESSIVE_PYRAMID,
            'core_trade': ScalingStrategy.CORE_TRADE,
            'momentum': ScalingStrategy.MOMENTUM_RIDER,
        }
        scaling_strategy = strategy_map.get(strategy, ScalingStrategy.CONSERVATIVE)

        trade = tm.create_trade(
            ticker=ticker,
            thesis=thesis,
            theme=theme,
            catalyst=catalyst,
            scaling_strategy=scaling_strategy,
        )

        # Log activity
        _add_activity(f"Added {ticker} to watchlist", 'create')

        # Publish sync event
        _publish_sync_event('trade_created', {
            'ticker': ticker,
            'thesis': thesis,
            'theme': theme,
            'trade_id': trade.id,
        })

        return jsonify({
            'ok': True,
            'trade': trade.to_dict(),
            'message': f'Created trade for {ticker}'
        })
    except Exception as e:
        logger.error(f"Create trade API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/<trade_id>/buy', methods=['POST'])
def api_trades_buy(trade_id):
    """Add buy tranche to a trade."""
    try:
        from src.trading import TradeManager
        tm = TradeManager()

        data = request.json or {}
        shares = int(data.get('shares', 0))
        price = float(data.get('price', 0))
        reason = data.get('reason', 'Manual entry')

        if shares <= 0 or price <= 0:
            return jsonify({'ok': False, 'error': 'Invalid shares or price'})

        tranche = tm.add_buy(trade_id, shares, price, reason)

        if tranche:
            trade = tm.get_trade(trade_id)
            # Log activity
            _add_activity(f"Bought {shares} {trade.ticker} @ ${price:.2f}", 'buy')
            # Publish sync event
            _publish_sync_event('buy_executed', {
                'ticker': trade.ticker,
                'shares': shares,
                'price': price,
                'reason': reason,
                'trade_id': trade_id,
            })
            return jsonify({
                'ok': True,
                'tranche': tranche.to_dict(),
                'trade': trade.to_dict() if trade else None,
                'message': f'Bought {shares} shares @ ${price:.2f}'
            })
        return jsonify({'ok': False, 'error': 'Trade not found'})
    except Exception as e:
        logger.error(f"Buy API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/<trade_id>/sell', methods=['POST'])
def api_trades_sell(trade_id):
    """Add sell tranche to a trade."""
    try:
        from src.trading import TradeManager
        tm = TradeManager()

        data = request.json or {}
        shares = int(data.get('shares', 0))
        price = float(data.get('price', 0))
        reason = data.get('reason', 'Manual exit')

        if shares <= 0 or price <= 0:
            return jsonify({'ok': False, 'error': 'Invalid shares or price'})

        tranche = tm.add_sell(trade_id, shares, price, reason)

        if tranche:
            trade = tm.get_trade(trade_id)
            # Log activity
            _add_activity(f"Sold {shares} {trade.ticker} @ ${price:.2f}", 'sell')
            # Publish sync event
            _publish_sync_event('sell_executed', {
                'ticker': trade.ticker,
                'shares': shares,
                'price': price,
                'reason': reason,
                'trade_id': trade_id,
            })
            return jsonify({
                'ok': True,
                'tranche': tranche.to_dict(),
                'trade': trade.to_dict() if trade else None,
                'message': f'Sold {shares} shares @ ${price:.2f}'
            })
        return jsonify({'ok': False, 'error': 'Trade not found'})
    except Exception as e:
        logger.error(f"Sell API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/<trade_id>/close', methods=['POST'])
def api_trades_close(trade_id):
    """Close entire position."""
    try:
        from src.trading import TradeManager
        tm = TradeManager()

        data = request.json or {}
        price = float(data.get('price', 0))
        reason = data.get('reason', 'Manual close')

        if price <= 0:
            return jsonify({'ok': False, 'error': 'Invalid price'})

        trade = tm.get_trade(trade_id)
        if not trade:
            return jsonify({'ok': False, 'error': 'Trade not found'})

        if tm.close_trade(trade_id, price, reason):
            trade = tm.get_trade(trade_id)
            return jsonify({
                'ok': True,
                'trade': trade.to_dict() if trade else None,
                'message': f'Closed position'
            })
        return jsonify({'ok': False, 'error': 'Failed to close'})
    except Exception as e:
        logger.error(f"Close trade API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/<trade_id>')
def api_trades_get(trade_id):
    """Get single trade details."""
    try:
        from src.trading import TradeManager
        tm = TradeManager()

        trade = tm.get_trade(trade_id)
        if not trade:
            return jsonify({'ok': False, 'error': 'Trade not found'})

        # Get current price
        current_price = None
        try:
            stock = yf.Ticker(trade.ticker)
            hist = stock.history(period='1d')
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
        except:
            pass

        return jsonify({
            'ok': True,
            'trade': tm.get_trade_summary(trade_id, current_price)
        })
    except Exception as e:
        logger.error(f"Get trade API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/<trade_id>', methods=['DELETE'])
def api_trades_delete(trade_id):
    """Delete a trade."""
    try:
        from src.trading import TradeManager
        tm = TradeManager()

        # Get trade info before deleting for activity log
        trade = tm.get_trade(trade_id)
        ticker = trade.ticker if trade else 'Unknown'

        if tm.delete_trade(trade_id):
            # Log activity
            _add_activity(f"Removed {ticker} from watchlist", 'delete')
            return jsonify({'ok': True, 'message': 'Trade deleted'})
        return jsonify({'ok': False, 'error': 'Trade not found'})
    except Exception as e:
        logger.error(f"Delete trade API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/scan')
def api_trades_scan():
    """Scan all positions for exit signals."""
    try:
        from src.trading import scan_positions

        results = scan_positions()

        # Log activity
        pos_count = len(results.get('positions', []))
        _add_activity(f"Scanned {pos_count} positions for exit signals", 'scan')

        return jsonify({
            'ok': True,
            **results
        })
    except Exception as e:
        logger.error(f"Scan positions API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/scan/<ticker>')
def api_trades_scan_ticker(ticker):
    """Scan single ticker for exit signals."""
    try:
        from src.trading import scan_ticker

        result = scan_ticker(ticker.upper())

        if 'error' in result:
            return jsonify({'ok': False, 'error': result['error']})

        return jsonify({
            'ok': True,
            **result
        })
    except Exception as e:
        logger.error(f"Scan ticker API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/risk')
def api_trades_risk():
    """Get portfolio risk assessment."""
    try:
        from src.trading import TradeManager, RiskAdvisor

        tm = TradeManager()
        advisor = RiskAdvisor()

        positions = tm.get_open_trades()

        if not positions:
            return jsonify({
                'ok': True,
                'message': 'No open positions',
                'risk_level': 'none',
                'risk_score': 0
            })

        # Get current prices
        current_prices = {}
        for trade in positions:
            try:
                stock = yf.Ticker(trade.ticker)
                hist = stock.history(period='1d')
                if not hist.empty:
                    current_prices[trade.ticker] = float(hist['Close'].iloc[-1])
            except:
                pass

        # Estimate portfolio value
        portfolio_value = sum(
            trade.total_shares * current_prices.get(trade.ticker, trade.average_cost)
            for trade in positions
        )

        risk = advisor.assess_portfolio_risk(
            trades=positions,
            current_prices=current_prices,
            portfolio_value=portfolio_value
        )

        return jsonify({
            'ok': True,
            'overall_risk': risk['overall_risk'].value,
            'risk_score': risk['risk_score'],
            'high_risk_count': risk['high_risk_count'],
            'trade_count': risk['trade_count'],
            'high_risk_trades': [
                {
                    'ticker': t['ticker'],
                    'risk_level': t['risk_level'].value,
                    'confidence': t['confidence'],
                    'urgency': t['urgency']
                }
                for t in risk.get('high_risk_trades', [])
            ],
            'recommendations': risk.get('recommendations', [])
        })
    except Exception as e:
        logger.error(f"Risk API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/daily-report')
def api_trades_daily_report():
    """Generate daily position report."""
    try:
        from src.trading import get_daily_report

        report = get_daily_report()

        return jsonify({
            'ok': True,
            'report': report
        })
    except Exception as e:
        logger.error(f"Daily report API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


# =============================================================================
# TRADE JOURNAL ENDPOINTS
# =============================================================================

# In-memory journal storage (will be replaced with file-based storage)
_journal_entries = []
_activity_feed = []


@app.route('/api/trades/journal')
def api_trades_journal_get():
    """Get all journal entries."""
    try:
        # Load from file if exists
        journal_file = Path('data/trade_journal.json')
        if journal_file.exists():
            with open(journal_file, 'r') as f:
                entries = json.load(f)
        else:
            entries = _journal_entries

        # Sort by timestamp descending
        entries = sorted(entries, key=lambda x: x.get('timestamp', ''), reverse=True)

        return jsonify({
            'ok': True,
            'entries': entries,
            'count': len(entries)
        })
    except Exception as e:
        logger.error(f"Journal GET API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/journal', methods=['POST'])
def api_trades_journal_post():
    """Add a new journal entry."""
    try:
        from datetime import datetime
        import uuid

        data = request.get_json() or {}
        entry_type = data.get('entry_type', 'note')
        content = data.get('content', '')
        ticker = data.get('ticker')
        tags = data.get('tags', [])

        if not content:
            return jsonify({'ok': False, 'error': 'Content is required'})

        # Validate entry type
        valid_types = ['trade', 'note', 'lesson', 'mistake']
        if entry_type not in valid_types:
            return jsonify({'ok': False, 'error': f'Invalid entry type. Use: {", ".join(valid_types)}'})

        entry = {
            'id': str(uuid.uuid4()),
            'entry_type': entry_type,
            'content': content,
            'ticker': ticker.upper() if ticker else None,
            'tags': tags,
            'timestamp': datetime.now().isoformat()
        }

        # Load existing entries
        journal_file = Path('data/trade_journal.json')
        journal_file.parent.mkdir(parents=True, exist_ok=True)

        if journal_file.exists():
            with open(journal_file, 'r') as f:
                entries = json.load(f)
        else:
            entries = []

        entries.append(entry)

        # Save back
        with open(journal_file, 'w') as f:
            json.dump(entries, f, indent=2)

        # Also add to activity feed
        _add_activity(f"Added {entry_type} entry{f' for {ticker.upper()}' if ticker else ''}", 'journal')

        return jsonify({
            'ok': True,
            'entry': entry,
            'message': f'Journal entry added successfully'
        })
    except Exception as e:
        logger.error(f"Journal POST API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/trades/activity')
def api_trades_activity():
    """Get recent activity feed."""
    try:
        # Load from file if exists
        activity_file = Path('data/trade_activity.json')
        if activity_file.exists():
            with open(activity_file, 'r') as f:
                activities = json.load(f)
        else:
            activities = _activity_feed

        # Sort by timestamp descending and limit to 50
        activities = sorted(activities, key=lambda x: x.get('timestamp', ''), reverse=True)[:50]

        return jsonify({
            'ok': True,
            'activities': activities,
            'count': len(activities)
        })
    except Exception as e:
        logger.error(f"Activity API error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


def _add_activity(message: str, activity_type: str = 'general'):
    """Add an activity to the feed."""
    try:
        from datetime import datetime
        import uuid

        activity = {
            'id': str(uuid.uuid4()),
            'message': message,
            'type': activity_type,
            'timestamp': datetime.now().isoformat()
        }

        activity_file = Path('data/trade_activity.json')
        activity_file.parent.mkdir(parents=True, exist_ok=True)

        if activity_file.exists():
            with open(activity_file, 'r') as f:
                activities = json.load(f)
        else:
            activities = []

        activities.append(activity)

        # Keep only last 100 activities
        activities = activities[-100:]

        with open(activity_file, 'w') as f:
            json.dump(activities, f, indent=2)

    except Exception as e:
        logger.error(f"Failed to add activity: {e}")


def _publish_sync_event(event_type: str, payload: dict):
    """Publish a sync event to Telegram and connected dashboards."""
    try:
        from src.sync import get_sync_hub, EventType, SyncSource, broadcast_event
        from src.sync.socketio_server import _send_to_telegram_sync

        hub = get_sync_hub()

        # Map string to EventType
        try:
            et = EventType[event_type.upper()]
        except KeyError:
            logger.warning(f"Unknown event type: {event_type}")
            return

        event = hub.create_event(et, SyncSource.DASHBOARD, payload)

        # Store event
        hub.event_store.add(event)

        # Broadcast to connected dashboards via SocketIO
        try:
            broadcast_event(event)
        except Exception as e:
            logger.debug(f"SocketIO broadcast failed: {e}")

        # Send to Telegram
        try:
            _send_to_telegram_sync(hub, event)
        except Exception as e:
            logger.debug(f"Telegram send failed: {e}")

        logger.info(f"Published sync event: {event_type}")

    except ImportError:
        logger.debug("Sync module not available")
    except Exception as e:
        logger.debug(f"Failed to publish sync event: {e}")


# =============================================================================
# SYNC API ENDPOINTS
# =============================================================================

@app.route('/api/sync/status')
def api_sync_status():
    """Get sync system status."""
    try:
        from src.sync import get_sync_hub

        hub = get_sync_hub()
        status = hub.get_sync_status()

        return jsonify({
            'ok': True,
            **status
        })
    except ImportError:
        return jsonify({
            'ok': True,
            'connected_clients': 0,
            'total_events': 0,
            'telegram_configured': bool(os.environ.get('TELEGRAM_BOT_TOKEN')),
            'websocket_url': os.environ.get('WS_URL', 'ws://localhost:8765'),
        })
    except Exception as e:
        logger.error(f"Sync status error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/sync/events')
def api_sync_events():
    """Get recent sync events."""
    try:
        from src.sync import get_sync_hub

        hub = get_sync_hub()
        count = request.args.get('count', 50, type=int)
        events = hub.event_store.get_recent(count)

        return jsonify({
            'ok': True,
            'events': [e.to_dict() for e in events],
            'count': len(events)
        })
    except ImportError:
        # Sync module not available, return empty
        return jsonify({
            'ok': True,
            'events': [],
            'count': 0
        })
    except Exception as e:
        logger.error(f"Sync events error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/sync/publish', methods=['POST'])
def api_sync_publish():
    """Publish a sync event from dashboard."""
    try:
        import asyncio
        from src.sync import get_sync_hub, EventType, SyncSource

        data = request.get_json() or {}
        event_type = data.get('event_type', '')
        payload = data.get('payload', {})

        if not event_type:
            return jsonify({'ok': False, 'error': 'event_type required'})

        hub = get_sync_hub()

        # Create and publish event
        try:
            et = EventType[event_type.upper()]
        except KeyError:
            return jsonify({'ok': False, 'error': f'Invalid event_type: {event_type}'})

        event = hub.create_event(et, SyncSource.DASHBOARD, payload)

        # Run async publish in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(hub.publish(event))
        finally:
            loop.close()

        return jsonify({
            'ok': True,
            'event': event.to_dict(),
            'message': f'Event {event_type} published'
        })
    except ImportError:
        return jsonify({'ok': False, 'error': 'Sync module not available'})
    except Exception as e:
        logger.error(f"Sync publish error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/sync/telegram-webhook', methods=['POST'])
def api_sync_telegram_webhook():
    """Webhook endpoint for Telegram bot updates."""
    try:
        import asyncio
        from src.sync import get_sync_hub, SyncSource, EventType

        data = request.get_json() or {}

        # Extract message from update
        message = data.get('message', {})
        text = message.get('text', '')
        user = message.get('from', {}).get('username', 'unknown')
        chat_id = message.get('chat', {}).get('id', '')

        if not text:
            return jsonify({'ok': True})

        # Check if it's a command
        if text.startswith('/'):
            parts = text.split(' ', 1)
            command = parts[0][1:]  # Remove leading /
            args = parts[1] if len(parts) > 1 else ''

            hub = get_sync_hub()
            event = hub.create_event(
                EventType.COMMAND_RECEIVED,
                SyncSource.TELEGRAM,
                {
                    'command': command,
                    'args': args,
                    'user': user,
                    'chat_id': str(chat_id),
                    'raw_text': text
                }
            )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(hub.publish(event))
            finally:
                loop.close()

        return jsonify({'ok': True})

    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/sync/config')
def api_sync_config():
    """Get sync configuration for dashboard."""
    return jsonify({
        'ok': True,
        'websocket_url': os.environ.get('WS_URL', 'wss://stock-scanner-bot-ws.onrender.com'),
        'telegram_configured': bool(os.environ.get('TELEGRAM_BOT_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID')),
        'api_base': request.host_url.rstrip('/') + '/api',
    })


# =============================================================================
# WATCHLIST SYSTEM - Enhanced with Auto-Updates
# =============================================================================

# Register watchlist blueprint
try:
    from src.watchlist.watchlist_api import watchlist_bp
    app.register_blueprint(watchlist_bp)
    logger.info("✓ Watchlist API registered")
except Exception as e:
    logger.warning(f"Watchlist API not available: {e}")

# Register learning system API
try:
    from src.learning.learning_api import learning_bp
    app.register_blueprint(learning_bp)
    logger.info("✓ Learning System API registered")
except Exception as e:
    logger.warning(f"Learning System API not available: {e}")


if __name__ == '__main__':
    if socketio:
        # Run with SocketIO for real-time sync support
        socketio.run(app, host='0.0.0.0', port=config.port, debug=config.debug)
    else:
        # Fallback to regular Flask
        app.run(host='0.0.0.0', port=config.port, debug=config.debug)
