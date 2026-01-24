#!/usr/bin/env python3
"""
Instant Telegram Bot using Webhooks

Deployed on Render (free tier) for instant responses.
Telegram sends messages directly to this server - no polling delay.
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
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')


def send_message(chat_id, text, parse_mode='Markdown'):
    """Send message to Telegram."""
    try:
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
            data={'chat_id': chat_id, 'caption': caption, 'parse_mode': 'Markdown'},
            timeout=30
        )
        return response.status_code == 200
    except:
        return False


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def handle_help(chat_id):
    """Handle /help command."""
    msg = "🤖 *INSTANT BOT COMMANDS*\n\n"
    msg += "*AI Intelligence:*\n"
    msg += "• `/ai` → AI learning dashboard\n"
    msg += "• `/briefing` → AI market narrative\n"
    msg += "• `/predict NVDA` → AI trade prediction\n"
    msg += "• `/coach` → AI performance coaching\n"
    msg += "• `/strategy` → AI strategy advice\n"
    msg += "• `/patterns` → Best signal patterns\n"
    msg += "• `/trade NVDA 150 165` → Record trade\n\n"
    msg += "*Analysis:*\n"
    msg += "• `NVDA` → Quick analysis + chart\n"
    msg += "• `/top` → Top 10 stocks\n"
    msg += "• `/regime` → Market regime\n"
    msg += "• `/learning` → Self-learning insights\n"
    msg += "• `/profile NVDA` → Stock personality\n\n"
    msg += "*Stories:*\n"
    msg += "• `/stories` → Stories in play\n"
    msg += "• `/news` → News sentiment\n"
    msg += "• `/sectors` → Sector rotation\n\n"
    msg += "_Responses are now instant!_"
    send_message(chat_id, msg)


def handle_ticker(chat_id, ticker):
    """Handle ticker analysis request."""
    ticker = ticker.upper().strip()
    send_message(chat_id, f"⏳ Analyzing {ticker}...")

    try:
        # Fetch data
        df = yf.download(ticker, period='3mo', progress=False)
        if len(df) < 20:
            send_message(chat_id, f"❌ Not enough data for `{ticker}`")
            return

        # Flatten columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        current = float(close.iloc[-1])

        # Calculate indicators
        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1])

        # Relative strength vs SPY
        spy = yf.download('SPY', period='1mo', progress=False)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)

        stock_ret = (current / float(close.iloc[-20]) - 1) * 100
        spy_ret = (float(spy['Close'].iloc[-1]) / float(spy['Close'].iloc[-20]) - 1) * 100
        rs = stock_ret - spy_ret

        # Volume
        vol_ratio = float(df['Volume'].iloc[-1] / df['Volume'].iloc[-20:].mean())

        # Build message
        msg = f"📊 *{ticker} ANALYSIS*\n\n"
        msg += f"*Price:* ${current:.2f}\n"
        msg += f"*RS vs SPY:* {rs:+.2f}%\n\n"

        msg += "*Trend:*\n"
        msg += f"• Above 20 SMA: {'✅' if current > sma_20 else '❌'}\n"
        msg += f"• Above 50 SMA: {'✅' if current > sma_50 else '❌'}\n"

        msg += f"\n*Volume:* {vol_ratio:.1f}x avg"
        if vol_ratio > 2:
            msg += " 🔥"

        # ATR for stops
        high = df['High']
        low = df['Low']
        tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])

        msg += f"\n\n*Entry Ideas:*\n"
        msg += f"• Stop: ${current - 2*atr:.2f}\n"
        msg += f"• Target: ${current + 3*atr:.2f}"

        send_message(chat_id, msg)

        # Generate and send chart
        try:
            chart = generate_quick_chart(ticker, df)
            if chart:
                send_photo(chat_id, chart, f"{ticker} Chart")
        except:
            pass

    except Exception as e:
        send_message(chat_id, f"❌ Error analyzing {ticker}: {str(e)}")


def generate_quick_chart(ticker, df):
    """Generate a simple chart."""
    try:
        import io
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        df = df.iloc[-60:]
        close = df['Close']

        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0d1117')
        ax.set_facecolor('#0d1117')

        # Price line
        ax.plot(close.index, close.values, color='#00b894', linewidth=2)

        # Moving averages
        if len(close) >= 20:
            sma_20 = close.rolling(20).mean()
            ax.plot(close.index, sma_20.values, color='orange', linewidth=1, alpha=0.7)

        ax.set_title(f'{ticker} - Last 60 Days', color='white', fontsize=14)
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, alpha=0.3)

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#0d1117')
        buf.seek(0)
        plt.close(fig)

        return buf
    except:
        return None


def handle_top(chat_id):
    """Handle /top command - show top stocks."""
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
            send_message(chat_id, "No scan data available. Wait for next scheduled scan.")
    except Exception as e:
        send_message(chat_id, f"Error: {str(e)}")


def handle_regime(chat_id):
    """Handle /regime command."""
    send_message(chat_id, "⏳ Analyzing market regime...")

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


def handle_ai(chat_id):
    """Handle /ai command."""
    try:
        from ai_learning import format_ai_insights
        msg = format_ai_insights()
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"AI error: {str(e)}")


def handle_briefing(chat_id):
    """Handle /briefing command."""
    send_message(chat_id, "🤖 Generating AI briefing...")

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
                    msg += f"Watch: `{'`, `'.join(opp['tickers'][:4])}`\n"

            if briefing.get('contrarian_take'):
                msg += f"\n*Contrarian:* _{briefing['contrarian_take']}_"
        else:
            msg = "Could not generate briefing. Try again later."

        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Briefing error: {str(e)}")


def handle_predict(chat_id, ticker):
    """Handle /predict command."""
    ticker = ticker.upper().strip()
    send_message(chat_id, f"🤖 AI predicting {ticker}...")

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
            msg += f"{emoji} *Success Probability:* {prob}%\n"
            msg += f"*Confidence:* {prediction.get('confidence_level', 'N/A')}\n"
            msg += f"*Recommendation:* {prediction.get('recommendation', 'N/A').upper()}\n\n"

            for f in prediction.get('key_bullish_factors', [])[:2]:
                msg += f"✅ {f}\n"
            for f in prediction.get('key_risk_factors', [])[:2]:
                msg += f"⚠️ {f}\n"
        else:
            msg = f"Could not generate prediction for {ticker}"

        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Prediction error: {str(e)}")


def handle_profile(chat_id, ticker):
    """Handle /profile command."""
    ticker = ticker.upper().strip()
    send_message(chat_id, f"⏳ Analyzing {ticker} personality...")

    try:
        from self_learning import auto_learn_stock_profile, get_stock_profile

        df = yf.download(ticker, period='6mo', progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Build profile
        for _ in range(5):
            auto_learn_stock_profile(ticker, df)

        profile = get_stock_profile(ticker)

        if profile:
            msg = f"🎭 *{ticker} PERSONALITY*\n\n"
            msg += f"*Type:* {profile.get('type', 'unknown').title()}\n"
            msg += f"*Momentum:* {profile.get('momentum_score', 0):.0f}%\n"
            msg += f"*Mean Reversion:* {profile.get('mean_reversion_score', 0):.0f}%\n"
            msg += f"*Volume Responsive:* {'Yes' if profile.get('volume_responsive') else 'No'}\n\n"
            msg += f"*Strategy:* {profile.get('recommended_strategy', 'unknown').replace('_', ' ').title()}"
        else:
            msg = f"Could not build profile for {ticker}"

        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Profile error: {str(e)}")


def handle_patterns(chat_id):
    """Handle /patterns command."""
    try:
        from ai_learning import get_best_patterns

        patterns = get_best_patterns()

        msg = "📊 *BEST SIGNAL PATTERNS*\n\n"
        if patterns:
            for i, p in enumerate(patterns[:10], 1):
                emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "•"))
                msg += f"{emoji} *{p['pattern']}*\n"
                msg += f"   Win: {p['win_rate']:.0f}% ({p['total_trades']} trades)\n"
        else:
            msg += "_No patterns yet. AI learns from trade outcomes._"

        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Patterns error: {str(e)}")


def handle_coach(chat_id):
    """Handle /coach command."""
    send_message(chat_id, "🤖 AI coach analyzing...")

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

        coaching = get_weekly_coaching(
            recent_trades,
            alerts.get('alerts', [])[-30:],
            accuracy
        )

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
            msg = "_Need more trade data for coaching._"

        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Coach error: {str(e)}")


def handle_trade(chat_id, args):
    """Handle /trade command to record a trade."""
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
            msg += f"*{ticker}*: ${entry} → ${exit_price} ({pnl:+.1f}%)\n"

            if analysis:
                msg += f"\n*Lesson:* {analysis.get('lesson_learned', 'N/A')}"
        else:
            msg = "Usage: `/trade NVDA 150 165`"

        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Trade error: {str(e)}")


def handle_stories(chat_id):
    """Handle /stories command."""
    send_message(chat_id, "⏳ Detecting stories...")

    try:
        from story_detector import run_story_detection, format_stories_report
        result = run_story_detection()
        msg = format_stories_report(result)
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
# WEBHOOK HANDLER
# =============================================================================

def process_message(message):
    """Process incoming Telegram message."""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '').strip()

    if not chat_id or not text:
        return

    print(f"Processing: {text} from {chat_id}")

    # Route commands
    text_lower = text.lower()

    if text_lower == '/help' or text_lower == '/start':
        handle_help(chat_id)

    elif text_lower == '/top':
        handle_top(chat_id)

    elif text_lower == '/regime':
        handle_regime(chat_id)

    elif text_lower == '/learning':
        handle_learning(chat_id)

    elif text_lower == '/ai':
        handle_ai(chat_id)

    elif text_lower == '/briefing':
        handle_briefing(chat_id)

    elif text_lower == '/patterns':
        handle_patterns(chat_id)

    elif text_lower == '/coach':
        handle_coach(chat_id)

    elif text_lower == '/stories':
        handle_stories(chat_id)

    elif text_lower == '/news':
        handle_news(chat_id)

    elif text_lower == '/sectors':
        handle_sectors(chat_id)

    elif text_lower.startswith('/predict '):
        handle_predict(chat_id, text[9:])

    elif text_lower.startswith('/profile '):
        handle_profile(chat_id, text[9:])

    elif text_lower.startswith('/trade '):
        handle_trade(chat_id, text[7:])

    elif len(text) <= 5 and text.replace('.', '').isalpha():
        # Ticker query
        handle_ticker(chat_id, text)

    elif text.startswith('/'):
        send_message(chat_id, f"Unknown command. Send `/help` for options.")


@app.route('/')
def home():
    """Health check endpoint."""
    return jsonify({
        'status': 'running',
        'bot': 'Stock Scanner Bot',
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
    """Set the Telegram webhook URL."""
    webhook_url = request.args.get('url')
    if not webhook_url:
        return jsonify({'error': 'Missing url parameter'})

    response = requests.post(
        f"{TELEGRAM_API}/setWebhook",
        json={'url': f"{webhook_url}/webhook"}
    )

    return jsonify(response.json())


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
