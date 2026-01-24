#!/usr/bin/env python3
"""
Complete Stock Scanner Bot - All Features

Features:
- AI Intelligence (briefing, predict, coach, patterns)
- Analysis (ticker, top, regime, profile)
- Stories (fast detection, news, sectors)
- Watchlist & Alerts
- Portfolio tracking
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

app = Flask(__name__)

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

    msg += "*🎯 Watchlist & Alerts:*\n"
    msg += "• `/watch NVDA` → Add to watchlist\n"
    msg += "• `/watchlist` → View watchlist\n"
    msg += "• `/alert NVDA 150` → Price alert\n"
    msg += "• `/alerts` → View alerts\n\n"

    msg += "*💼 Portfolio:*\n"
    msg += "• `/buy NVDA 100 150` → Add position\n"
    msg += "• `/sell NVDA 160` → Close position\n"
    msg += "• `/portfolio` → View portfolio\n\n"

    msg += "*📈 Intelligence:*\n"
    msg += "• `/stories` → Hot themes\n"
    msg += "• `/earnings` → Earnings calendar\n"
    msg += "• `/backtest NVDA` → Signal accuracy\n"
    msg += "• `/regime` → Market regime\n\n"

    msg += "*🤖 AI:*\n"
    msg += "• `/briefing` → AI market narrative\n"
    msg += "• `/predict NVDA` → AI prediction\n"
    msg += "• `/coach` → AI coaching\n"

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
# WATCHLIST
# =============================================================================

def handle_watch(chat_id, ticker):
    """Add ticker to watchlist."""
    try:
        from storage import add_to_watchlist, get_watchlist

        ticker = ticker.upper().strip()
        if add_to_watchlist(chat_id, ticker):
            watchlist = get_watchlist(chat_id)
            send_message(chat_id, f"✅ Added `{ticker}` to watchlist\n\nWatchlist: `{'` `'.join(watchlist)}`")
        else:
            send_message(chat_id, f"`{ticker}` already in watchlist")
    except Exception as e:
        send_message(chat_id, f"Error: {str(e)}")


def handle_unwatch(chat_id, ticker):
    """Remove ticker from watchlist."""
    try:
        from storage import remove_from_watchlist

        ticker = ticker.upper().strip()
        if remove_from_watchlist(chat_id, ticker):
            send_message(chat_id, f"✅ Removed `{ticker}` from watchlist")
        else:
            send_message(chat_id, f"`{ticker}` not in watchlist")
    except Exception as e:
        send_message(chat_id, f"Error: {str(e)}")


def handle_watchlist(chat_id):
    """Show watchlist with prices."""
    try:
        from storage import get_watchlist

        watchlist = get_watchlist(chat_id)
        if not watchlist:
            send_message(chat_id, "📋 Watchlist empty\n\nAdd with `/watch NVDA`")
            return

        send_message(chat_id, "⏳ Fetching prices...")

        msg = "📋 *WATCHLIST*\n\n"
        for ticker in watchlist:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='5d')
                if len(hist) >= 2:
                    current = float(hist['Close'].iloc[-1])
                    prev = float(hist['Close'].iloc[-2])
                    change = (current - prev) / prev * 100
                    emoji = "🟢" if change > 0 else "🔴"
                    msg += f"{emoji} `{ticker}` ${current:.2f} ({change:+.1f}%)\n"
                else:
                    msg += f"⚪ `{ticker}` (no data)\n"
            except:
                msg += f"⚪ `{ticker}` (error)\n"

        msg += f"\n_Remove with_ `/unwatch TICKER`"
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Error: {str(e)}")


# =============================================================================
# ALERTS
# =============================================================================

def handle_alert(chat_id, args):
    """Set price alert."""
    try:
        from storage import add_alert, get_alerts

        parts = args.split()
        if len(parts) < 2:
            send_message(chat_id, "Usage: `/alert NVDA 150`\nor `/alert NVDA below 140`")
            return

        ticker = parts[0].upper()
        if parts[1].lower() in ['above', 'below']:
            direction = parts[1].lower()
            price = float(parts[2])
        else:
            price = float(parts[1])
            # Auto-detect direction based on current price
            stock = yf.Ticker(ticker)
            current = float(stock.history(period='1d')['Close'].iloc[-1])
            direction = 'above' if price > current else 'below'

        alert = add_alert(chat_id, ticker, price, direction)

        emoji = "📈" if direction == 'above' else "📉"
        send_message(chat_id, f"{emoji} Alert set: `{ticker}` {direction} ${price:.2f}")
    except Exception as e:
        send_message(chat_id, f"Error: {str(e)}")


def handle_alerts(chat_id):
    """Show active alerts."""
    try:
        from storage import get_alerts

        alerts = get_alerts(chat_id)
        active = [a for a in alerts if not a.get('triggered')]

        if not active:
            send_message(chat_id, "🔔 No active alerts\n\nSet with `/alert NVDA 150`")
            return

        msg = "🔔 *PRICE ALERTS*\n\n"
        for a in active:
            emoji = "📈" if a['direction'] == 'above' else "📉"
            msg += f"{emoji} `{a['ticker']}` {a['direction']} ${a['price']:.2f}\n"

        msg += f"\n_Remove with_ `/removealert TICKER`"
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Error: {str(e)}")


def handle_removealert(chat_id, ticker):
    """Remove alerts for ticker."""
    try:
        from storage import remove_alert

        ticker = ticker.upper().strip()
        remove_alert(chat_id, ticker)
        send_message(chat_id, f"✅ Removed alerts for `{ticker}`")
    except Exception as e:
        send_message(chat_id, f"Error: {str(e)}")


# =============================================================================
# PORTFOLIO
# =============================================================================

def handle_buy(chat_id, args):
    """Add position to portfolio."""
    try:
        from storage import add_position

        parts = args.split()
        if len(parts) < 3:
            send_message(chat_id, "Usage: `/buy NVDA 100 150`\n(ticker, shares, entry price)")
            return

        ticker = parts[0].upper()
        shares = float(parts[1])
        entry_price = float(parts[2])

        position = add_position(chat_id, ticker, shares, entry_price)
        cost = shares * entry_price

        send_message(chat_id, f"✅ *POSITION ADDED*\n\n`{ticker}` {shares:.0f} shares @ ${entry_price:.2f}\nCost: ${cost:,.2f}")
    except Exception as e:
        send_message(chat_id, f"Error: {str(e)}")


def handle_sell(chat_id, args):
    """Close position."""
    try:
        from storage import close_position

        parts = args.split()
        if len(parts) < 2:
            send_message(chat_id, "Usage: `/sell NVDA 160`\n(ticker, exit price)")
            return

        ticker = parts[0].upper()
        exit_price = float(parts[1])

        trade = close_position(chat_id, ticker, exit_price)

        if trade:
            emoji = "✅" if trade['pnl_percent'] > 0 else "❌"
            msg = f"{emoji} *POSITION CLOSED*\n\n"
            msg += f"`{ticker}` ${trade['entry_price']:.2f} → ${exit_price:.2f}\n"
            msg += f"P&L: {trade['pnl_percent']:+.1f}% (${trade['pnl_dollars']:+,.2f})"
            send_message(chat_id, msg)
        else:
            send_message(chat_id, f"No position in `{ticker}`")
    except Exception as e:
        send_message(chat_id, f"Error: {str(e)}")


def handle_portfolio(chat_id):
    """Show portfolio."""
    try:
        from storage import get_portfolio, get_closed_trades

        positions = get_portfolio(chat_id)

        if not positions:
            send_message(chat_id, "💼 Portfolio empty\n\nAdd with `/buy NVDA 100 150`")
            return

        send_message(chat_id, "⏳ Calculating P&L...")

        msg = "💼 *PORTFOLIO*\n\n"
        total_cost = 0
        total_value = 0

        for pos in positions:
            ticker = pos['ticker']
            try:
                stock = yf.Ticker(ticker)
                current = float(stock.history(period='1d')['Close'].iloc[-1])
            except:
                current = pos['entry_price']

            cost = pos['shares'] * pos['entry_price']
            value = pos['shares'] * current
            pnl_pct = (current - pos['entry_price']) / pos['entry_price'] * 100
            pnl_dollars = value - cost

            total_cost += cost
            total_value += value

            emoji = "🟢" if pnl_pct > 0 else "🔴"
            msg += f"{emoji} *{ticker}*\n"
            msg += f"   {pos['shares']:.0f} @ ${pos['entry_price']:.2f} → ${current:.2f}\n"
            msg += f"   P&L: {pnl_pct:+.1f}% (${pnl_dollars:+,.0f})\n\n"

        total_pnl_pct = (total_value - total_cost) / total_cost * 100 if total_cost > 0 else 0
        msg += f"*Total:* ${total_value:,.0f} ({total_pnl_pct:+.1f}%)"

        send_message(chat_id, msg)

        # Send chart
        try:
            from charts import generate_portfolio_chart
            prices = {}
            for pos in positions:
                try:
                    stock = yf.Ticker(pos['ticker'])
                    prices[pos['ticker']] = float(stock.history(period='1d')['Close'].iloc[-1])
                except:
                    prices[pos['ticker']] = pos['entry_price']

            chart = generate_portfolio_chart(positions, prices)
            if chart:
                send_photo(chat_id, chart, "Portfolio Allocation")
        except:
            pass

    except Exception as e:
        send_message(chat_id, f"Error: {str(e)}")


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
# REGIME, LEARNING, TOP (existing)
# =============================================================================

def handle_regime(chat_id):
    """Handle /regime command."""
    send_message(chat_id, "⏳ Analyzing regime...")
    try:
        from self_learning import detect_market_regime, get_best_strategies_for_regime

        spy = yf.download('SPY', period='3mo', progress=False)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)

        regime = detect_market_regime(spy)
        strategies = get_best_strategies_for_regime(regime)

        msg = f"🌍 *MARKET REGIME*\n\n"
        msg += f"*Current:* {regime.replace('_', ' ').title()}\n"
        msg += f"*SPY:* ${float(spy['Close'].iloc[-1]):.2f}\n\n"

        if strategies.get('strategies'):
            msg += "*Best Strategies:*\n"
            for s in strategies['strategies'][:3]:
                msg += f"• {s['strategy'].replace('_', ' ')}: {s['win_rate']:.0f}% win\n"

        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Regime error: {str(e)}")


def handle_learning(chat_id):
    """Handle /learning command."""
    try:
        from self_learning import format_learning_summary
        msg = format_learning_summary()
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Learning error: {str(e)}")


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
        briefing = get_daily_briefing()
        if briefing and not briefing.get('error'):
            msg = "🎯 *AI MARKET BRIEFING*\n\n"
            msg += f"*{briefing.get('headline', 'Market Update')}*\n\n"
            msg += f"*Mood:* {briefing.get('market_mood', 'N/A').upper()}\n\n"
            msg += f"_{briefing.get('main_narrative', '')}_\n\n"
            opp = briefing.get('key_opportunity', {})
            if opp:
                msg += f"*Opportunity:* {opp.get('description', 'N/A')}\n"
                if opp.get('tickers'):
                    msg += f"Watch: `{'`, `'.join(opp['tickers'][:4])}`"
        else:
            msg = "Briefing unavailable. Set DEEPSEEK_API_KEY for AI features."
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


def handle_profile(chat_id, ticker):
    """Handle /profile command."""
    ticker = ticker.upper().strip()
    send_message(chat_id, f"⏳ Building {ticker} profile...")
    try:
        from self_learning import auto_learn_stock_profile, get_stock_profile

        df = yf.download(ticker, period='6mo', progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        for _ in range(5):
            auto_learn_stock_profile(ticker, df)

        profile = get_stock_profile(ticker)

        if profile:
            msg = f"🎭 *{ticker} PROFILE*\n\n"
            msg += f"*Type:* {profile.get('type', 'unknown').title()}\n"
            msg += f"*Momentum:* {profile.get('momentum_score', 0):.0f}%\n"
            msg += f"*Mean Reversion:* {profile.get('mean_reversion_score', 0):.0f}%\n"
            msg += f"*Strategy:* {profile.get('recommended_strategy', 'unknown').replace('_', ' ').title()}"
        else:
            msg = f"Could not build profile for {ticker}"

        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Profile error: {str(e)}")


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

    # Analysis
    elif text_lower == '/scan':
        handle_scan(chat_id)
    elif text_lower == '/top':
        handle_top(chat_id)
    elif text_lower.startswith('/screen'):
        handle_screen(chat_id, text[7:].strip())

    # Watchlist
    elif text_lower.startswith('/watch '):
        handle_watch(chat_id, text[7:].strip())
    elif text_lower.startswith('/unwatch '):
        handle_unwatch(chat_id, text[9:].strip())
    elif text_lower == '/watchlist':
        handle_watchlist(chat_id)

    # Alerts
    elif text_lower.startswith('/alert '):
        handle_alert(chat_id, text[7:].strip())
    elif text_lower == '/alerts':
        handle_alerts(chat_id)
    elif text_lower.startswith('/removealert '):
        handle_removealert(chat_id, text[13:].strip())

    # Portfolio
    elif text_lower.startswith('/buy '):
        handle_buy(chat_id, text[5:].strip())
    elif text_lower.startswith('/sell '):
        handle_sell(chat_id, text[6:].strip())
    elif text_lower == '/portfolio':
        handle_portfolio(chat_id)

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
    elif text_lower == '/regime':
        handle_regime(chat_id)
    elif text_lower == '/learning':
        handle_learning(chat_id)

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
    elif text_lower.startswith('/profile '):
        handle_profile(chat_id, text[9:].strip())
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
    try:
        data = request.get_json()
        if data and 'message' in data:
            process_message(data['message'])
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
