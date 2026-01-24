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

            elif text.lower() == '/podcasts':
                # Podcast & Newsletter intel
                try:
                    from alt_sources import aggregate_alt_sources, extract_themes_from_alt_sources, format_alt_sources_report
                    send_telegram_message("⏳ Scanning podcasts & newsletters...")
                    content = aggregate_alt_sources()
                    analysis = extract_themes_from_alt_sources(content)
                    msg = format_alt_sources_report(analysis)
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Podcasts error: {str(e)}")

            elif text.lower() == '/ranked':
                # Ranked signals with quality scores
                try:
                    from story_detector import run_ranked_detection
                    from signal_ranker import format_ranked_signals
                    send_telegram_message("⏳ Analyzing & ranking signals...")
                    result = run_ranked_detection()
                    ranked = result.get('ranked_signals', [])
                    if ranked:
                        msg = format_ranked_signals(ranked)
                    else:
                        msg = "No signals to rank. Try /stories first."
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Ranking error: {str(e)}")

            elif text.lower() == '/accuracy':
                # Source accuracy leaderboard
                try:
                    from fact_checker import format_source_trust_report
                    msg = format_source_trust_report()
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Accuracy error: {str(e)}")

            elif text.lower() == '/factcheck':
                # Run fact check on recent news
                try:
                    from news_analyzer import aggregate_news_sources
                    from fact_checker import run_fact_check, format_fact_check_report
                    send_telegram_message("⏳ Fact-checking recent claims...")

                    # Get headlines from multiple tickers
                    all_headlines = []
                    for ticker in ['NVDA', 'AAPL', 'TSLA', 'META', 'AMD']:
                        headlines = aggregate_news_sources(ticker)
                        for h in headlines[:5]:
                            h['ticker'] = ticker
                            all_headlines.append(h)

                    result = run_fact_check(all_headlines)
                    msg = format_fact_check_report(result)
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Fact check error: {str(e)}")

            elif text.lower() == '/insights':
                # Show learned insights
                try:
                    from fact_checker import format_learning_insights
                    msg = format_learning_insights()
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Insights error: {str(e)}")

            elif text.lower() == '/learning':
                # Comprehensive self-learning insights
                try:
                    from self_learning import format_learning_summary
                    msg = format_learning_summary()
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Learning error: {str(e)}")

            elif text.lower().startswith('/profile '):
                # Stock personality profile
                ticker = text[9:].strip().upper()
                try:
                    from self_learning import get_stock_profile, auto_learn_stock_profile
                    import yfinance as yf

                    send_telegram_message(f"⏳ Analyzing {ticker} personality...")

                    # Get price data and analyze
                    df = yf.download(ticker, period='6mo', progress=False)
                    if len(df) >= 50:
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)

                        profile = auto_learn_stock_profile(ticker, df)

                        if profile:
                            msg = f"🎭 *{ticker} PERSONALITY*\n\n"
                            msg += f"*Type:* {profile.get('type', 'unknown').replace('_', ' ').title()}\n"
                            msg += f"*Momentum Score:* {profile.get('momentum_score', 0):.0f}%\n"
                            msg += f"*Mean Reversion:* {profile.get('mean_reversion_score', 0):.0f}%\n"
                            msg += f"*Volume Responsive:* {'Yes' if profile.get('volume_responsive') else 'No'}\n"
                            msg += f"*Avg Trend Length:* {profile.get('avg_trend_length', 0):.1f} days\n\n"
                            msg += f"*Recommended Strategy:*\n"
                            msg += f"→ {profile.get('recommended_strategy', 'unknown').replace('_', ' ').title()}"
                        else:
                            msg = f"Not enough data to profile {ticker}"
                    else:
                        msg = f"Not enough price history for {ticker}"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Profile error: {str(e)}")

            elif text.lower() == '/regime':
                # Market regime and best strategies
                try:
                    from self_learning import detect_market_regime, get_best_strategies_for_regime, record_regime_change
                    import yfinance as yf

                    send_telegram_message("⏳ Analyzing market regime...")

                    spy = yf.download('SPY', period='3mo', progress=False)
                    if isinstance(spy.columns, pd.MultiIndex):
                        spy.columns = spy.columns.get_level_values(0)

                    regime = detect_market_regime(spy)
                    spy_price = float(spy['Close'].iloc[-1])
                    record_regime_change(regime, spy_price)

                    strategies = get_best_strategies_for_regime(regime)

                    msg = f"🌍 *MARKET REGIME*\n\n"
                    msg += f"*Current:* {regime.replace('_', ' ').title()}\n"
                    msg += f"*SPY:* ${spy_price:.2f}\n\n"

                    if strategies.get('strategies'):
                        msg += "*Best Strategies:*\n"
                        for s in strategies['strategies'][:3]:
                            msg += f"• {s['strategy'].replace('_', ' ')}: {s['win_rate']:.0f}% win\n"
                        msg += "\n"

                    if strategies.get('avoid'):
                        msg += "*Avoid:*\n"
                        for s in strategies['avoid']:
                            msg += f"• {s['strategy'].replace('_', ' ')}: {s['win_rate']:.0f}% win\n"

                    if not strategies.get('strategies') and not strategies.get('avoid'):
                        msg += "_Not enough data yet. System learns as you trade._"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Regime error: {str(e)}")

            elif text.lower() == '/alerts':
                # Alert accuracy insights
                try:
                    from self_learning import get_alert_accuracy_insights
                    insights = get_alert_accuracy_insights()

                    msg = "📊 *ALERT ACCURACY*\n\n"

                    if insights.get('best_alert_types'):
                        msg += "*Best Alert Types:*\n"
                        for a in insights['best_alert_types']:
                            msg += f"• {a['type'].replace('_', ' ')}: {a['win_rate']:.0f}% ({a['total_alerts']} alerts)\n"
                        msg += "\n"

                    if insights.get('worst_alert_types'):
                        worst = [w for w in insights['worst_alert_types'] if w['win_rate'] < 50]
                        if worst:
                            msg += "*Underperforming:*\n"
                            for a in worst[:2]:
                                msg += f"• {a['type'].replace('_', ' ')}: {a['win_rate']:.0f}%\n"
                            msg += "\n"

                    if insights.get('recommendations'):
                        msg += "*Recommendations:*\n"
                        for r in insights['recommendations']:
                            msg += f"→ {r}\n"

                    if not insights.get('best_alert_types'):
                        msg += "_No alert data yet. System learns from scans._"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Alerts error: {str(e)}")

            elif text.lower() == '/timing':
                # News timing insights
                try:
                    from self_learning import get_news_impact_insights
                    insights = get_news_impact_insights()

                    msg = "📰 *NEWS TIMING*\n\n"

                    if insights.get('by_news_type'):
                        msg += "*How Fast News Gets Priced In:*\n"
                        for ntype, data in insights['by_news_type'].items():
                            days = data['avg_days_to_price_in']
                            move = data['avg_move_1d']
                            msg += f"• {ntype}: ~{days:.1f} days (avg {move:.1f}% move)\n"
                        msg += "\n"

                    if insights.get('fast_pricing_tickers'):
                        msg += "*Fast Movers (act quickly):*\n"
                        for t in insights['fast_pricing_tickers'][:3]:
                            msg += f"• {t['ticker']}: priced in {t['avg_pricing_days']:.1f}d\n"
                        msg += "\n"

                    if insights.get('slow_pricing_tickers'):
                        msg += "*Slow Movers (time to position):*\n"
                        for t in insights['slow_pricing_tickers'][:3]:
                            msg += f"• {t['ticker']}: takes {t['avg_pricing_days']:.1f}d\n"

                    if not insights.get('by_news_type'):
                        msg += "_No timing data yet. System learns from news events._"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Timing error: {str(e)}")

            # ============================================================
            # AI-POWERED COMMANDS
            # ============================================================

            elif text.lower() == '/ai':
                # Full AI insights dashboard
                try:
                    from ai_learning import format_ai_insights
                    msg = format_ai_insights()
                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"AI insights error: {str(e)}")

            elif text.lower() == '/briefing':
                # AI market narrative
                try:
                    from ai_learning import get_daily_briefing
                    send_telegram_message("🤖 Generating AI market briefing...")

                    briefing = get_daily_briefing()
                    if briefing and not briefing.get('error'):
                        msg = "🎯 *AI MARKET BRIEFING*\n\n"
                        msg += f"*{briefing.get('headline', 'Market Update')}*\n\n"
                        msg += f"*Mood:* {briefing.get('market_mood', 'N/A').upper()}\n\n"
                        msg += f"_{briefing.get('main_narrative', '')}_\n\n"

                        opp = briefing.get('key_opportunity', {})
                        if opp:
                            msg += f"*Key Opportunity:*\n"
                            msg += f"{opp.get('description', 'N/A')}\n"
                            if opp.get('tickers'):
                                msg += f"Tickers: `{'`, `'.join(opp['tickers'][:4])}`\n"
                            msg += "\n"

                        risk = briefing.get('key_risk', {})
                        if risk:
                            msg += f"*Key Risk:* {risk.get('description', 'N/A')}\n\n"

                        if briefing.get('contrarian_take'):
                            msg += f"*Contrarian View:*\n_{briefing['contrarian_take']}_\n"
                    else:
                        msg = f"Could not generate briefing: {briefing.get('error', 'Unknown error')}"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Briefing error: {str(e)}")

            elif text.lower().startswith('/predict '):
                # AI prediction for a ticker
                ticker = text[9:].strip().upper()
                try:
                    from ai_learning import predict_trade_outcome
                    import yfinance as yf
                    send_telegram_message(f"🤖 AI predicting {ticker}...")

                    # Get current data
                    df = yf.download(ticker, period='3mo', progress=False)
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)

                    # Build signal summary
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

                    if prediction and not prediction.get('error'):
                        prob = prediction.get('success_probability', 50)
                        emoji = "🟢" if prob >= 60 else ("🟡" if prob >= 40 else "🔴")

                        msg = f"🎲 *AI PREDICTION: {ticker}*\n\n"
                        msg += f"{emoji} *Success Probability:* {prob}%\n"
                        msg += f"*Confidence:* {prediction.get('confidence_level', 'N/A')}\n"
                        msg += f"*Expected Move:* {prediction.get('expected_move', 'N/A')}\n"
                        msg += f"*Recommendation:* {prediction.get('recommendation', 'N/A').upper()}\n\n"

                        msg += "*Bullish Factors:*\n"
                        for f in prediction.get('key_bullish_factors', [])[:3]:
                            msg += f"• {f}\n"

                        msg += "\n*Risk Factors:*\n"
                        for f in prediction.get('key_risk_factors', [])[:3]:
                            msg += f"• {f}\n"

                        msg += f"\n*Stop:* {prediction.get('stop_loss_suggestion', 'N/A')}\n"
                        msg += f"*Target:* {prediction.get('target_suggestion', 'N/A')}\n"
                    else:
                        msg = f"Could not generate prediction for {ticker}"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Prediction error: {str(e)}")

            elif text.lower() == '/patterns':
                # Best signal patterns
                try:
                    from ai_learning import get_best_patterns
                    patterns = get_best_patterns()

                    msg = "📊 *BEST SIGNAL PATTERNS*\n\n"

                    if patterns:
                        msg += "_Patterns ranked by win rate:_\n\n"
                        for i, p in enumerate(patterns[:10], 1):
                            emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "•"))
                            msg += f"{emoji} *{p['pattern']}*\n"
                            msg += f"   Win rate: {p['win_rate']:.0f}% ({p['total_trades']} trades)\n"
                    else:
                        msg += "_No pattern data yet. AI learns from trade outcomes._"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Patterns error: {str(e)}")

            elif text.lower() == '/coach':
                # AI performance coaching
                try:
                    from ai_learning import get_weekly_coaching, load_trade_journal
                    from self_learning import load_alert_history

                    send_telegram_message("🤖 AI coach analyzing your performance...")

                    journal = load_trade_journal()
                    alerts = load_alert_history()

                    # Calculate accuracy
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

                    if coaching and not coaching.get('error'):
                        msg = "🏋️ *AI PERFORMANCE COACH*\n\n"
                        msg += f"*Grade:* {coaching.get('overall_grade', 'N/A')}\n"
                        msg += f"_{coaching.get('grade_explanation', '')}_\n\n"

                        # Strengths
                        strengths = coaching.get('strengths', [])
                        if strengths:
                            msg += "*Strengths:*\n"
                            for s in strengths[:2]:
                                msg += f"✅ {s.get('strength', 'N/A')}\n"
                            msg += "\n"

                        # Weaknesses
                        weaknesses = coaching.get('weaknesses', [])
                        if weaknesses:
                            msg += "*Areas to Improve:*\n"
                            for w in weaknesses[:2]:
                                msg += f"⚠️ {w.get('weakness', 'N/A')}\n"
                                msg += f"   → {w.get('specific_fix', '')}\n"
                            msg += "\n"

                        # Weekly focus
                        focus = coaching.get('weekly_focus', {})
                        if focus:
                            msg += f"*This Week's Focus:*\n"
                            msg += f"🎯 {focus.get('primary_goal', 'Keep improving')}\n"

                        # Rules
                        rules = coaching.get('specific_rules', [])
                        if rules:
                            msg += f"\n*New Rules:*\n"
                            for r in rules[:2]:
                                msg += f"📋 {r}\n"

                        msg += f"\n_{coaching.get('encouragement', 'Keep learning!')}_"
                    else:
                        msg = "_Need more trade data for coaching. Record trades with /trade._"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Coach error: {str(e)}")

            elif text.lower().startswith('/trade '):
                # Record a trade: /trade NVDA 150 165 win
                parts = text[7:].strip().split()
                try:
                    if len(parts) >= 4:
                        from ai_learning import record_trade

                        ticker = parts[0].upper()
                        entry = float(parts[1])
                        exit_price = float(parts[2])
                        # outcome is computed from prices

                        signals = {'manual_entry': True}  # Could enhance this

                        trade_id, analysis = record_trade(
                            ticker=ticker,
                            entry_price=entry,
                            exit_price=exit_price,
                            entry_date=datetime.now().strftime('%Y-%m-%d'),
                            exit_date=datetime.now().strftime('%Y-%m-%d'),
                            signals_at_entry=signals
                        )

                        pnl = (exit_price - entry) / entry * 100
                        emoji = "✅" if pnl > 0 else "❌"

                        msg = f"{emoji} *TRADE RECORDED*\n\n"
                        msg += f"*{ticker}*: ${entry} → ${exit_price} ({pnl:+.1f}%)\n\n"

                        if analysis:
                            msg += f"*AI Analysis:*\n"
                            msg += f"_{analysis.get('primary_reason', 'Analyzing...')}_\n\n"
                            msg += f"*Lesson:* {analysis.get('lesson_learned', 'N/A')}"
                    else:
                        msg = "Usage: `/trade NVDA 150 165`\n(ticker entry_price exit_price)"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Trade record error: {str(e)}")

            elif text.lower() == '/experts':
                # Expert accuracy leaderboard
                try:
                    from ai_learning import get_expert_leaderboard

                    experts = get_expert_leaderboard()

                    msg = "🎯 *EXPERT ACCURACY LEADERBOARD*\n\n"

                    if experts:
                        for i, e in enumerate(experts[:10], 1):
                            emoji = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
                            msg += f"{emoji} *{e['expert']}*: {e['accuracy']:.0f}%\n"
                            msg += f"   {e['correct']}/{e['total_predictions']} correct\n"
                    else:
                        msg += "_No expert predictions tracked yet._\n"
                        msg += "_AI extracts predictions from podcasts/newsletters._"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Experts error: {str(e)}")

            elif text.lower() == '/anomalies':
                # Recent anomalies
                try:
                    from ai_learning import load_anomaly_history

                    history = load_anomaly_history()
                    recent = history.get('anomalies', [])[-5:]

                    msg = "⚠️ *RECENT ANOMALIES*\n\n"

                    if recent:
                        for a in reversed(recent):
                            ticker = a.get('ticker', 'N/A')
                            analysis = a.get('analysis', {})

                            msg += f"*{ticker}*\n"
                            for anomaly in analysis.get('anomalies_detected', [])[:2]:
                                msg += f"• {anomaly.get('description', 'N/A')}\n"
                            msg += f"_{analysis.get('trading_implication', 'N/A')}_\n\n"
                    else:
                        msg += "_No significant anomalies detected recently._"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Anomalies error: {str(e)}")

            elif text.lower() == '/strategy':
                # AI strategy advice
                try:
                    from ai_learning import get_strategy_advice
                    from self_learning import get_alert_accuracy_insights, get_best_strategies_for_regime

                    send_telegram_message("🤖 AI analyzing strategy...")

                    # Get performance data
                    alerts = get_alert_accuracy_insights()
                    regime = get_best_strategies_for_regime()

                    performance = {
                        'best_alerts': alerts.get('best_alert_types', []),
                        'regime': regime.get('regime', 'unknown'),
                    }

                    weights = {'trend': 0.30, 'squeeze': 0.20, 'rs': 0.20, 'volume': 0.15, 'sentiment': 0.15}

                    advice = get_strategy_advice(performance, weights, regime.get('regime', 'unknown'))

                    if advice and not advice.get('error'):
                        msg = "📈 *AI STRATEGY ADVICE*\n\n"
                        msg += f"_{advice.get('overall_assessment', 'Analyzing...')}_\n\n"

                        # Weight changes
                        changes = advice.get('weight_adjustments', {})
                        if changes:
                            msg += "*Weight Adjustments:*\n"
                            for signal, data in changes.items():
                                if isinstance(data, dict) and data.get('recommended') != data.get('current'):
                                    msg += f"• {signal}: {data.get('current', '?')} → {data.get('recommended', '?')}\n"
                            msg += "\n"

                        # Focus areas
                        focus = advice.get('focus_areas', [])
                        if focus:
                            msg += "*Focus On:*\n"
                            for f in focus[:3]:
                                msg += f"✅ {f}\n"

                        avoid = advice.get('avoid_areas', [])
                        if avoid:
                            msg += "\n*Avoid:*\n"
                            for a in avoid[:2]:
                                msg += f"❌ {a}\n"

                        msg += f"\n*Risk:* {advice.get('risk_adjustment', 'maintain').upper()}"
                    else:
                        msg = "_Need more data for strategy advice._"

                    send_telegram_message(msg)
                except Exception as e:
                    send_telegram_message(f"Strategy error: {str(e)}")

            elif text.lower() == '/help':
                msg = "🤖 *BOT COMMANDS*\n\n"
                msg += "*AI Intelligence:*\n"
                msg += "• `/ai` → AI learning dashboard\n"
                msg += "• `/briefing` → AI market narrative\n"
                msg += "• `/predict NVDA` → AI trade prediction\n"
                msg += "• `/coach` → AI performance coaching\n"
                msg += "• `/strategy` → AI strategy advice\n"
                msg += "• `/patterns` → Best signal patterns\n"
                msg += "• `/experts` → Expert accuracy ranking\n"
                msg += "• `/trade NVDA 150 165` → Record trade\n\n"
                msg += "*Story Detection:*\n"
                msg += "• `/stories` → Stories in play\n"
                msg += "• `/ranked` → Signals ranked by quality\n"
                msg += "• `/podcasts` → Podcast/newsletter intel\n\n"
                msg += "*Self-Learning:*\n"
                msg += "• `/learning` → Learning insights\n"
                msg += "• `/profile NVDA` → Stock personality\n"
                msg += "• `/regime` → Market regime\n"
                msg += "• `/timing` → News pricing speed\n\n"
                msg += "*Analysis:*\n"
                msg += "• `NVDA` → Full analysis + chart\n"
                msg += "• `/top` → Top 10 stocks\n"
                msg += "• `/news` → News + sentiment\n"
                msg += "• `/sectors` → Sector rotation\n\n"
                msg += "_AI learns from every action you take._"
                send_telegram_message(msg)

            elif text.startswith('/'):
                send_telegram_message(f"Unknown command. Send `/help` for options.")

        # Update offset
        with open(offset_file, 'w') as f:
            json.dump({'offset': update_id}, f)

    print(f"Bot listener done: {datetime.now()}")


if __name__ == '__main__':
    main()
