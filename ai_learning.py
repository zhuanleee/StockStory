#!/usr/bin/env python3
"""
AI-Powered Self-Learning System

Uses DeepSeek AI to provide intelligent analysis:
1. Pattern Recognition - Complex multi-factor pattern detection
2. Trade Analyst - Post-trade analysis with reasoning
3. Prediction Engine - Probability scoring for alerts
4. Strategy Advisor - Personalized recommendations
5. Market Narrator - Daily market synthesis
6. Anomaly Detector - Unusual pattern detection with explanation
7. Source Analyst - Expert accuracy tracking
8. Performance Coach - Behavioral analysis and coaching
"""

import json
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# DeepSeek API
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'

# Data storage
AI_LEARNING_DIR = Path('ai_learning_data')
AI_LEARNING_DIR.mkdir(exist_ok=True)


def call_deepseek(prompt, system_prompt=None, max_tokens=2000):
    """Call DeepSeek API for AI analysis."""
    if not DEEPSEEK_API_KEY:
        return None

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,  # Lower temperature for more consistent analysis
            },
            timeout=60
        )

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"DeepSeek API error: {e}")

    return None


# =============================================================================
# 1. AI PATTERN RECOGNITION
# =============================================================================

def load_pattern_memory():
    """Load learned patterns."""
    path = AI_LEARNING_DIR / 'pattern_memory.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'patterns': [],
        'successful_combinations': {},
        'failed_combinations': {},
    }


def save_pattern_memory(data):
    """Save pattern memory."""
    path = AI_LEARNING_DIR / 'pattern_memory.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def analyze_signal_pattern(signals, outcome=None):
    """
    Use AI to analyze a combination of signals and identify patterns.

    signals: dict of signal types and their values
    outcome: 'win', 'loss', or None (for prediction)
    """
    memory = load_pattern_memory()

    # Create signal signature
    signal_keys = sorted([k for k, v in signals.items() if v])
    signature = '+'.join(signal_keys)

    system_prompt = """You are a quantitative trading analyst specializing in pattern recognition.
Analyze trading signals and identify meaningful patterns. Be specific and actionable.
Always respond in JSON format."""

    prompt = f"""Analyze this combination of trading signals:

Signals present: {json.dumps(signals, indent=2)}

Historical data for this combination:
- Times seen: {memory['successful_combinations'].get(signature, {}).get('count', 0) + memory['failed_combinations'].get(signature, {}).get('count', 0)}
- Win rate: {calculate_pattern_win_rate(memory, signature)}%

{"Outcome: " + outcome if outcome else "Predict the likely outcome."}

Respond in JSON:
{{
    "pattern_name": "descriptive name for this pattern",
    "strength": "strong/moderate/weak",
    "key_factors": ["most important signal", "second most important"],
    "missing_confirmation": ["what would make this stronger"],
    "historical_context": "when this pattern worked/failed before",
    "prediction": "bullish/bearish/neutral",
    "confidence": 0-100,
    "reasoning": "brief explanation"
}}"""

    response = call_deepseek(prompt, system_prompt)

    if response:
        try:
            # Parse JSON response
            analysis = json.loads(response)

            # Store this pattern analysis
            memory['patterns'].append({
                'timestamp': datetime.now().isoformat(),
                'signals': signals,
                'signature': signature,
                'analysis': analysis,
                'outcome': outcome,
            })

            # Update combination tracking
            if outcome == 'win':
                if signature not in memory['successful_combinations']:
                    memory['successful_combinations'][signature] = {'count': 0, 'avg_gain': []}
                memory['successful_combinations'][signature]['count'] += 1
            elif outcome == 'loss':
                if signature not in memory['failed_combinations']:
                    memory['failed_combinations'][signature] = {'count': 0, 'avg_loss': []}
                memory['failed_combinations'][signature]['count'] += 1

            # Keep only recent patterns
            memory['patterns'] = memory['patterns'][-500:]
            save_pattern_memory(memory)

            return analysis
        except json.JSONDecodeError:
            return {'raw_analysis': response}

    return None


def calculate_pattern_win_rate(memory, signature):
    """Calculate win rate for a pattern signature."""
    wins = memory['successful_combinations'].get(signature, {}).get('count', 0)
    losses = memory['failed_combinations'].get(signature, {}).get('count', 0)
    total = wins + losses
    if total == 0:
        return 50  # Default
    return round(wins / total * 100)


def get_best_patterns():
    """Get the most successful patterns from memory."""
    memory = load_pattern_memory()

    patterns = []
    all_signatures = set(list(memory['successful_combinations'].keys()) +
                        list(memory['failed_combinations'].keys()))

    for sig in all_signatures:
        wins = memory['successful_combinations'].get(sig, {}).get('count', 0)
        losses = memory['failed_combinations'].get(sig, {}).get('count', 0)
        total = wins + losses

        if total >= 5:  # Minimum sample size
            win_rate = wins / total * 100
            patterns.append({
                'pattern': sig.replace('+', ' + '),
                'win_rate': win_rate,
                'total_trades': total,
                'signals': sig.split('+'),
            })

    patterns.sort(key=lambda x: x['win_rate'], reverse=True)
    return patterns


# =============================================================================
# 2. AI TRADE ANALYST
# =============================================================================

def load_trade_journal():
    """Load trade journal."""
    path = AI_LEARNING_DIR / 'trade_journal.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {'trades': [], 'analyses': []}


def save_trade_journal(data):
    """Save trade journal."""
    path = AI_LEARNING_DIR / 'trade_journal.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def record_trade(ticker, entry_price, exit_price, entry_date, exit_date,
                signals_at_entry, market_context=None):
    """Record a completed trade for analysis."""
    journal = load_trade_journal()

    pnl_pct = (exit_price - entry_price) / entry_price * 100
    outcome = 'win' if pnl_pct > 0 else 'loss'

    trade = {
        'id': f"{ticker}_{entry_date}_{len(journal['trades'])}",
        'ticker': ticker,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'entry_date': entry_date,
        'exit_date': exit_date,
        'pnl_pct': round(pnl_pct, 2),
        'outcome': outcome,
        'signals_at_entry': signals_at_entry,
        'market_context': market_context,
        'recorded_at': datetime.now().isoformat(),
    }

    journal['trades'].append(trade)
    save_trade_journal(journal)

    # Trigger AI analysis
    analysis = analyze_trade(trade)
    if analysis:
        journal['analyses'].append({
            'trade_id': trade['id'],
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
        })
        save_trade_journal(journal)

    return trade['id'], analysis


def analyze_trade(trade):
    """Use AI to analyze why a trade worked or failed."""
    system_prompt = """You are an expert trading coach analyzing completed trades.
Provide specific, actionable insights about why trades succeeded or failed.
Focus on what can be learned and improved. Be direct and honest."""

    prompt = f"""Analyze this completed trade:

Ticker: {trade['ticker']}
Entry: ${trade['entry_price']} on {trade['entry_date']}
Exit: ${trade['exit_price']} on {trade['exit_date']}
P&L: {trade['pnl_pct']:+.2f}%
Outcome: {trade['outcome'].upper()}

Signals at entry:
{json.dumps(trade['signals_at_entry'], indent=2)}

Market context: {trade.get('market_context', 'Not provided')}

Provide analysis in JSON:
{{
    "primary_reason": "main reason for outcome",
    "signal_quality": "which signals were accurate vs misleading",
    "timing_analysis": "was entry/exit timing optimal",
    "what_worked": ["list of things done right"],
    "what_failed": ["list of mistakes or misleading signals"],
    "lesson_learned": "key takeaway from this trade",
    "improvement_suggestion": "specific action to improve",
    "similar_setups": "how to handle similar setups in future"
}}"""

    response = call_deepseek(prompt, system_prompt)

    if response:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {'raw_analysis': response}

    return None


def get_trade_lessons():
    """Get aggregated lessons from trade history."""
    journal = load_trade_journal()

    if len(journal['analyses']) < 3:
        return None

    # Aggregate recent analyses
    recent = journal['analyses'][-20:]
    lessons = [a['analysis'].get('lesson_learned', '') for a in recent if a.get('analysis')]
    mistakes = []
    successes = []

    for a in recent:
        if a.get('analysis'):
            mistakes.extend(a['analysis'].get('what_failed', []))
            successes.extend(a['analysis'].get('what_worked', []))

    system_prompt = """You are a trading performance analyst.
Synthesize trading lessons into actionable insights."""

    prompt = f"""Analyze these patterns from recent trades:

Lessons learned:
{json.dumps(lessons, indent=2)}

Common mistakes:
{json.dumps(mistakes, indent=2)}

What worked:
{json.dumps(successes, indent=2)}

Win rate: {len([t for t in journal['trades'][-20:] if t['outcome'] == 'win'])} / {len(journal['trades'][-20:])}

Synthesize into JSON:
{{
    "top_3_strengths": ["what trader does well"],
    "top_3_weaknesses": ["areas needing improvement"],
    "recurring_mistake": "most common error pattern",
    "key_insight": "most important realization",
    "action_items": ["specific things to do differently"],
    "rules_to_add": ["new trading rules based on lessons"]
}}"""

    response = call_deepseek(prompt, system_prompt)

    if response:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {'raw_analysis': response}

    return None


# =============================================================================
# 3. AI PREDICTION ENGINE
# =============================================================================

def load_prediction_history():
    """Load prediction history for calibration."""
    path = AI_LEARNING_DIR / 'predictions.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {'predictions': [], 'calibration': {}}


def save_prediction_history(data):
    """Save prediction history."""
    path = AI_LEARNING_DIR / 'predictions.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def predict_trade_outcome(ticker, signals, market_context=None, price_data=None):
    """
    Use AI to predict probability of success for a potential trade.
    Returns probability and reasoning.
    """
    history = load_prediction_history()
    patterns = load_pattern_memory()

    # Get historical win rate for similar signals
    signal_keys = sorted([k for k, v in signals.items() if v])
    signature = '+'.join(signal_keys)
    historical_win_rate = calculate_pattern_win_rate(patterns, signature)

    # Get recent prediction accuracy for calibration
    recent_predictions = history['predictions'][-50:]
    if recent_predictions:
        correct = len([p for p in recent_predictions if p.get('was_correct')])
        calibration = correct / len(recent_predictions) * 100
    else:
        calibration = 50

    system_prompt = """You are a quantitative prediction model for stock trades.
Estimate the probability of a successful trade (>2% gain in 5 days).
Be calibrated - your 70% predictions should win ~70% of the time.
Consider all factors and be specific about your reasoning."""

    prompt = f"""Predict the outcome for this potential trade:

Ticker: {ticker}
Current signals: {json.dumps(signals, indent=2)}
Market context: {market_context or 'Standard conditions'}

Historical data:
- Pattern win rate: {historical_win_rate}% (for this signal combination)
- Model calibration: {calibration}% accurate recently

Price action summary: {summarize_price_data(price_data) if price_data is not None else 'Not provided'}

Respond in JSON:
{{
    "success_probability": 0-100,
    "confidence_level": "high/medium/low",
    "expected_move": "+X% to +Y% or -X% to -Y%",
    "time_horizon": "X days",
    "key_bullish_factors": ["factor 1", "factor 2"],
    "key_risk_factors": ["risk 1", "risk 2"],
    "recommendation": "strong_buy/buy/hold/avoid/strong_avoid",
    "reasoning": "brief explanation of probability estimate",
    "stop_loss_suggestion": "price or percentage",
    "target_suggestion": "price or percentage"
}}"""

    response = call_deepseek(prompt, system_prompt)

    if response:
        try:
            prediction = json.loads(response)

            # Record prediction for calibration
            history['predictions'].append({
                'id': f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                'ticker': ticker,
                'signals': signals,
                'prediction': prediction,
                'timestamp': datetime.now().isoformat(),
                'outcome': None,  # To be filled later
                'was_correct': None,
            })

            history['predictions'] = history['predictions'][-200:]
            save_prediction_history(history)

            return prediction
        except json.JSONDecodeError:
            return {'raw_prediction': response}

    return None


def update_prediction_outcome(prediction_id, actual_outcome, actual_pnl):
    """Update a prediction with its actual outcome for calibration."""
    history = load_prediction_history()

    for pred in history['predictions']:
        if pred['id'] == prediction_id:
            pred['outcome'] = actual_outcome
            pred['actual_pnl'] = actual_pnl

            # Check if prediction was correct
            predicted_prob = pred['prediction'].get('success_probability', 50)
            was_bullish = predicted_prob > 50
            was_correct = (was_bullish and actual_outcome == 'win') or \
                         (not was_bullish and actual_outcome == 'loss')
            pred['was_correct'] = was_correct

            # Update calibration buckets
            bucket = f"{(predicted_prob // 10) * 10}-{(predicted_prob // 10) * 10 + 10}"
            if bucket not in history['calibration']:
                history['calibration'][bucket] = {'total': 0, 'wins': 0}
            history['calibration'][bucket]['total'] += 1
            if actual_outcome == 'win':
                history['calibration'][bucket]['wins'] += 1

            break

    save_prediction_history(history)


def get_prediction_calibration():
    """Get prediction calibration stats."""
    history = load_prediction_history()
    return history.get('calibration', {})


def summarize_price_data(price_data):
    """Create a text summary of price data for AI."""
    if price_data is None or len(price_data) < 10:
        return "Insufficient data"

    try:
        close = price_data['Close']
        current = float(close.iloc[-1])
        change_5d = (current / float(close.iloc[-5]) - 1) * 100
        change_20d = (current / float(close.iloc[-20]) - 1) * 100 if len(close) >= 20 else 0

        high_20d = float(price_data['High'].iloc[-20:].max()) if len(price_data) >= 20 else current
        low_20d = float(price_data['Low'].iloc[-20:].min()) if len(price_data) >= 20 else current

        return f"Price ${current:.2f}, 5d change {change_5d:+.1f}%, 20d change {change_20d:+.1f}%, " \
               f"20d range ${low_20d:.2f}-${high_20d:.2f}"
    except:
        return "Error processing price data"


# =============================================================================
# 4. AI STRATEGY ADVISOR
# =============================================================================

def load_strategy_history():
    """Load strategy recommendation history."""
    path = AI_LEARNING_DIR / 'strategy_advice.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {'advice': [], 'weight_history': []}


def save_strategy_history(data):
    """Save strategy history."""
    path = AI_LEARNING_DIR / 'strategy_advice.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def get_strategy_advice(performance_data, current_weights, market_regime):
    """
    Get AI-powered strategy recommendations based on recent performance.
    """
    system_prompt = """You are an elite trading strategy advisor.
Analyze performance data and recommend specific, actionable strategy adjustments.
Be direct and specific. Focus on what will improve results."""

    prompt = f"""Analyze trading performance and recommend strategy adjustments:

Recent Performance:
{json.dumps(performance_data, indent=2)}

Current Scoring Weights:
{json.dumps(current_weights, indent=2)}

Current Market Regime: {market_regime}

Provide recommendations in JSON:
{{
    "overall_assessment": "brief performance summary",
    "weight_adjustments": {{
        "trend": {{"current": X, "recommended": Y, "reason": "..."}},
        "squeeze": {{"current": X, "recommended": Y, "reason": "..."}},
        "rs": {{"current": X, "recommended": Y, "reason": "..."}},
        "volume": {{"current": X, "recommended": Y, "reason": "..."}},
        "sentiment": {{"current": X, "recommended": Y, "reason": "..."}}
    }},
    "strategy_changes": [
        {{"change": "specific change", "expected_impact": "what it will improve"}}
    ],
    "signals_to_emphasize": ["signal types working well"],
    "signals_to_deemphasize": ["signal types underperforming"],
    "new_rules_suggested": ["specific rules to add"],
    "risk_adjustment": "increase/decrease/maintain position sizing",
    "focus_areas": ["where to concentrate attention"],
    "avoid_areas": ["what to avoid in current conditions"]
}}"""

    response = call_deepseek(prompt, system_prompt)

    if response:
        try:
            advice = json.loads(response)

            # Save advice history
            history = load_strategy_history()
            history['advice'].append({
                'timestamp': datetime.now().isoformat(),
                'market_regime': market_regime,
                'advice': advice,
            })
            history['advice'] = history['advice'][-50:]
            save_strategy_history(history)

            return advice
        except json.JSONDecodeError:
            return {'raw_advice': response}

    return None


def get_adaptive_weights(performance_by_signal, market_regime):
    """
    Use AI to calculate optimal weights based on recent signal performance.
    """
    system_prompt = """You are a quantitative weight optimizer.
Calculate optimal scoring weights based on signal performance data.
Weights must sum to 1.0. Be data-driven."""

    prompt = f"""Calculate optimal scoring weights:

Signal Performance (recent):
{json.dumps(performance_by_signal, indent=2)}

Market Regime: {market_regime}

Current standard weights: trend=0.30, squeeze=0.20, rs=0.20, volume=0.15, sentiment=0.15

Return optimized weights in JSON (must sum to 1.0):
{{
    "weights": {{
        "trend": 0.XX,
        "squeeze": 0.XX,
        "rs": 0.XX,
        "volume": 0.XX,
        "sentiment": 0.XX
    }},
    "reasoning": {{
        "trend": "why this weight",
        "squeeze": "why this weight",
        "rs": "why this weight",
        "volume": "why this weight",
        "sentiment": "why this weight"
    }},
    "confidence": "high/medium/low",
    "regime_specific": "are these weights optimized for current regime"
}}"""

    response = call_deepseek(prompt, system_prompt)

    if response:
        try:
            result = json.loads(response)

            # Validate weights sum to 1
            weights = result.get('weights', {})
            total = sum(weights.values())
            if abs(total - 1.0) > 0.01:
                # Normalize
                for k in weights:
                    weights[k] = weights[k] / total

            return result
        except json.JSONDecodeError:
            pass

    return None


# =============================================================================
# 5. AI MARKET NARRATOR
# =============================================================================

def generate_market_narrative(themes, sectors, top_stocks, news_highlights, market_data=None):
    """
    Generate an AI-powered market narrative synthesizing all information.
    """
    system_prompt = """You are an expert market analyst providing daily briefings.
Synthesize multiple data sources into a coherent narrative.
Be insightful, connect dots that others miss, and highlight actionable opportunities.
Write in a professional but engaging style."""

    prompt = f"""Create a market narrative from today's data:

HOT THEMES:
{json.dumps(themes[:5], indent=2) if themes else 'None detected'}

SECTOR PERFORMANCE:
{json.dumps(sectors[:5], indent=2) if sectors else 'Not available'}

TOP STOCKS:
{json.dumps(top_stocks[:10], indent=2) if top_stocks else 'Not available'}

KEY NEWS:
{json.dumps(news_highlights[:5], indent=2) if news_highlights else 'No significant news'}

Generate narrative in JSON:
{{
    "headline": "catchy 5-10 word summary",
    "market_mood": "bullish/bearish/uncertain/transitioning",
    "main_narrative": "2-3 sentence synthesis of what's happening",
    "theme_connections": "how themes are interconnected",
    "sector_rotation_insight": "what sector moves reveal",
    "smart_money_signal": "what institutional behavior suggests",
    "key_opportunity": {{
        "description": "the best opportunity right now",
        "tickers": ["relevant tickers"],
        "reasoning": "why this is the opportunity"
    }},
    "key_risk": {{
        "description": "biggest risk to monitor",
        "warning_signs": ["what to watch for"]
    }},
    "tomorrow_watch": ["what to focus on tomorrow"],
    "contrarian_take": "what the crowd might be missing"
}}"""

    response = call_deepseek(prompt, system_prompt, max_tokens=1500)

    if response:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {'raw_narrative': response}

    return None


def get_daily_briefing():
    """Generate and return today's AI market briefing."""
    try:
        # Load recent data
        from self_learning import load_alert_history, get_best_strategies_for_regime

        # Get themes from story detector if available
        themes = []
        try:
            from story_detector import run_story_detection
            detection = run_story_detection()
            themes = detection.get('themes', [])
        except:
            pass

        # Get sector data if available
        sectors = []
        try:
            from sector_rotation import run_sector_rotation_analysis
            rotation = run_sector_rotation_analysis()
            sectors = rotation.get('ranked', [])
        except:
            pass

        # Get top stocks from latest scan
        top_stocks = []
        import glob
        scan_files = glob.glob('scan_*.csv')
        if scan_files:
            import pandas as pd
            latest = max(scan_files)
            df = pd.read_csv(latest)
            top_stocks = df.head(10).to_dict('records')

        # Get news highlights
        news = []
        try:
            from news_analyzer import scan_news_sentiment
            results = scan_news_sentiment(['NVDA', 'AAPL', 'TSLA', 'META', 'AMD'][:3])
            news = [{'ticker': r['ticker'], 'sentiment': r['overall_sentiment']}
                   for r in results if r.get('overall_sentiment')]
        except:
            pass

        narrative = generate_market_narrative(themes, sectors, top_stocks, news)
        return narrative

    except Exception as e:
        return {'error': str(e)}


# =============================================================================
# 6. AI ANOMALY DETECTOR
# =============================================================================

def load_anomaly_history():
    """Load anomaly detection history."""
    path = AI_LEARNING_DIR / 'anomalies.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {'anomalies': [], 'resolved': []}


def save_anomaly_history(data):
    """Save anomaly history."""
    path = AI_LEARNING_DIR / 'anomalies.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def detect_anomalies(ticker, current_data, historical_behavior, stock_personality=None):
    """
    Use AI to detect and explain unusual patterns.
    """
    system_prompt = """You are an anomaly detection system for stock trading.
Identify unusual patterns and explain their potential significance.
Be specific about what's abnormal and what it might mean."""

    prompt = f"""Analyze this stock for anomalies:

Ticker: {ticker}

Current Data:
{json.dumps(current_data, indent=2)}

Historical Behavior (normal patterns):
{json.dumps(historical_behavior, indent=2)}

Stock Personality: {json.dumps(stock_personality, indent=2) if stock_personality else 'Not established'}

Detect anomalies and respond in JSON:
{{
    "anomalies_detected": [
        {{
            "type": "volume/price/volatility/correlation/behavior",
            "description": "what is unusual",
            "severity": "high/medium/low",
            "historical_comparison": "how this compares to normal"
        }}
    ],
    "is_significant": true/false,
    "potential_explanations": ["possible reason 1", "possible reason 2"],
    "historical_precedent": "similar situations in past and what happened",
    "trading_implication": "what this might mean for trading",
    "recommended_action": "what to do about it",
    "watch_for": ["follow-up signals to monitor"]
}}"""

    response = call_deepseek(prompt, system_prompt)

    if response:
        try:
            result = json.loads(response)

            # Save significant anomalies
            if result.get('is_significant'):
                history = load_anomaly_history()
                history['anomalies'].append({
                    'ticker': ticker,
                    'timestamp': datetime.now().isoformat(),
                    'analysis': result,
                })
                history['anomalies'] = history['anomalies'][-100:]
                save_anomaly_history(history)

            return result
        except json.JSONDecodeError:
            return {'raw_analysis': response}

    return None


def scan_for_anomalies(stock_data_dict, personalities=None):
    """Scan multiple stocks for anomalies."""
    anomalies = []

    for ticker, data in stock_data_dict.items():
        personality = personalities.get(ticker) if personalities else None

        # Simple anomaly detection (volume spike, unusual move)
        try:
            vol_ratio = data.get('vol_ratio', 1)
            daily_change = data.get('daily_change', 0)

            # Flag potential anomalies for AI analysis
            if vol_ratio > 3 or abs(daily_change) > 5:
                result = detect_anomalies(
                    ticker,
                    current_data=data,
                    historical_behavior={'avg_vol_ratio': 1.0, 'avg_daily_move': 1.5},
                    stock_personality=personality
                )
                if result and result.get('is_significant'):
                    anomalies.append({
                        'ticker': ticker,
                        'analysis': result,
                    })
        except:
            continue

    return anomalies


# =============================================================================
# 7. AI SOURCE ANALYST
# =============================================================================

def load_source_analysis():
    """Load source analysis data."""
    path = AI_LEARNING_DIR / 'source_analysis.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'expert_predictions': [],
        'expert_accuracy': {},
        'source_biases': {},
    }


def save_source_analysis(data):
    """Save source analysis."""
    path = AI_LEARNING_DIR / 'source_analysis.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def analyze_expert_prediction(source, expert_name, prediction_text, tickers_mentioned):
    """
    Extract and track specific predictions from experts/sources.
    """
    system_prompt = """You are an expert at extracting specific, verifiable predictions from text.
Extract clear predictions that can be verified later (price targets, directional calls, timeframes)."""

    prompt = f"""Extract specific predictions from this expert content:

Source: {source}
Expert: {expert_name}
Content: {prediction_text[:1000]}
Tickers mentioned: {tickers_mentioned}

Extract predictions in JSON:
{{
    "predictions": [
        {{
            "ticker": "SYMBOL",
            "prediction_type": "price_target/direction/timeframe/event",
            "specific_claim": "exact claim being made",
            "target": "price or direction",
            "timeframe": "when this should happen",
            "confidence_expressed": "how confident expert seemed",
            "verifiable_by": "date when we can check this"
        }}
    ],
    "overall_sentiment": "bullish/bearish/neutral on market",
    "key_themes": ["themes discussed"],
    "contrarian_to_consensus": true/false,
    "quality_score": 1-10
}}"""

    response = call_deepseek(prompt, system_prompt)

    if response:
        try:
            result = json.loads(response)

            # Save for tracking
            data = load_source_analysis()
            for pred in result.get('predictions', []):
                pred['source'] = source
                pred['expert'] = expert_name
                pred['extracted_at'] = datetime.now().isoformat()
                pred['verified'] = False
                pred['was_correct'] = None
                data['expert_predictions'].append(pred)

            data['expert_predictions'] = data['expert_predictions'][-500:]
            save_source_analysis(data)

            return result
        except json.JSONDecodeError:
            return {'raw_analysis': response}

    return None


def verify_expert_prediction(prediction_id, actual_outcome, actual_price=None):
    """Verify an expert prediction and update accuracy tracking."""
    data = load_source_analysis()

    for pred in data['expert_predictions']:
        if f"{pred['source']}_{pred['expert']}_{pred.get('ticker')}" == prediction_id:
            pred['verified'] = True
            pred['was_correct'] = actual_outcome
            pred['actual_price'] = actual_price
            pred['verified_at'] = datetime.now().isoformat()

            # Update expert accuracy
            expert = pred['expert']
            if expert not in data['expert_accuracy']:
                data['expert_accuracy'][expert] = {'correct': 0, 'incorrect': 0, 'predictions': []}

            if actual_outcome:
                data['expert_accuracy'][expert]['correct'] += 1
            else:
                data['expert_accuracy'][expert]['incorrect'] += 1

            data['expert_accuracy'][expert]['predictions'].append({
                'ticker': pred.get('ticker'),
                'was_correct': actual_outcome,
                'date': datetime.now().isoformat(),
            })
            break

    save_source_analysis(data)


def get_expert_leaderboard():
    """Get expert accuracy leaderboard."""
    data = load_source_analysis()

    leaderboard = []
    for expert, stats in data.get('expert_accuracy', {}).items():
        total = stats['correct'] + stats['incorrect']
        if total >= 3:
            accuracy = stats['correct'] / total * 100
            leaderboard.append({
                'expert': expert,
                'accuracy': accuracy,
                'total_predictions': total,
                'correct': stats['correct'],
            })

    leaderboard.sort(key=lambda x: x['accuracy'], reverse=True)
    return leaderboard


# =============================================================================
# 8. AI PERFORMANCE COACH
# =============================================================================

def load_coaching_data():
    """Load coaching history."""
    path = AI_LEARNING_DIR / 'coaching.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'sessions': [],
        'identified_biases': [],
        'improvement_tracking': {},
    }


def save_coaching_data(data):
    """Save coaching data."""
    path = AI_LEARNING_DIR / 'coaching.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def get_weekly_coaching(trade_history, alert_history, prediction_accuracy):
    """
    Generate weekly AI coaching session analyzing trading behavior.
    """
    system_prompt = """You are an elite trading performance coach.
Analyze trading patterns to identify behavioral biases and areas for improvement.
Be supportive but direct. Focus on actionable improvements.
Use psychology insights to help trader improve."""

    prompt = f"""Conduct a weekly coaching session based on this data:

Trade History (last 2 weeks):
{json.dumps(trade_history[-20:], indent=2) if trade_history else 'No trades recorded'}

Alert Response Patterns:
{json.dumps(alert_history[-30:], indent=2) if alert_history else 'No data'}

Prediction/Decision Accuracy: {prediction_accuracy}%

Provide coaching in JSON:
{{
    "overall_grade": "A/B/C/D/F",
    "grade_explanation": "why this grade",

    "behavioral_analysis": {{
        "identified_biases": [
            {{"bias": "name", "evidence": "what shows this", "impact": "how it hurts performance"}}
        ],
        "emotional_patterns": "observations about emotional trading",
        "decision_quality": "how good are the decisions being made"
    }},

    "strengths": [
        {{"strength": "what trader does well", "how_to_leverage": "how to use this more"}}
    ],

    "weaknesses": [
        {{"weakness": "area needing work", "specific_fix": "exactly what to do"}}
    ],

    "weekly_focus": {{
        "primary_goal": "one thing to focus on this week",
        "daily_practice": "daily habit to build",
        "metric_to_track": "number to measure progress"
    }},

    "mindset_advice": "psychological/mindset guidance",

    "specific_rules": [
        "new rule 1 to implement",
        "new rule 2 to implement"
    ],

    "encouragement": "motivational closing message"
}}"""

    response = call_deepseek(prompt, system_prompt, max_tokens=2000)

    if response:
        try:
            coaching = json.loads(response)

            # Save coaching session
            data = load_coaching_data()
            data['sessions'].append({
                'timestamp': datetime.now().isoformat(),
                'coaching': coaching,
            })

            # Track identified biases
            for bias in coaching.get('behavioral_analysis', {}).get('identified_biases', []):
                if bias not in data['identified_biases']:
                    data['identified_biases'].append(bias)

            data['sessions'] = data['sessions'][-20:]
            save_coaching_data(data)

            return coaching
        except json.JSONDecodeError:
            return {'raw_coaching': response}

    return None


def get_quick_feedback(action, context, outcome=None):
    """Get quick AI feedback on a specific trading decision."""
    system_prompt = """You are a trading coach providing quick feedback.
Be concise but insightful. One key point only."""

    prompt = f"""Quick feedback on this trading decision:

Action: {action}
Context: {context}
Outcome: {outcome if outcome else 'Pending'}

Respond in JSON:
{{
    "verdict": "good/questionable/poor decision",
    "key_point": "one sentence feedback",
    "suggestion": "one thing to consider"
}}"""

    response = call_deepseek(prompt, system_prompt, max_tokens=300)

    if response:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {'feedback': response}

    return None


# =============================================================================
# UNIFIED AI INTERFACE
# =============================================================================

def format_ai_insights():
    """Format all AI insights for display."""
    msg = "🤖 *AI LEARNING INSIGHTS*\n\n"

    # Best patterns
    patterns = get_best_patterns()
    if patterns:
        msg += "*📊 Best Signal Patterns:*\n"
        for p in patterns[:3]:
            msg += f"• {p['pattern']}: {p['win_rate']:.0f}% ({p['total_trades']} trades)\n"
        msg += "\n"

    # Expert leaderboard
    experts = get_expert_leaderboard()
    if experts:
        msg += "*🎯 Expert Accuracy:*\n"
        for e in experts[:3]:
            msg += f"• {e['expert']}: {e['accuracy']:.0f}% ({e['total_predictions']} calls)\n"
        msg += "\n"

    # Trade lessons
    lessons = get_trade_lessons()
    if lessons:
        msg += "*📚 Key Lesson:*\n"
        msg += f"_{lessons.get('key_insight', 'Keep learning!')}_\n\n"

    # Prediction calibration
    calibration = get_prediction_calibration()
    if calibration:
        msg += "*🎲 Prediction Calibration:*\n"
        for bucket, stats in sorted(calibration.items()):
            if stats['total'] >= 3:
                actual = stats['wins'] / stats['total'] * 100
                msg += f"• {bucket}%: actual {actual:.0f}%\n"

    if msg == "🤖 *AI LEARNING INSIGHTS*\n\n":
        msg += "_AI is learning. More insights after more data._"

    return msg


def run_full_ai_analysis(scan_results=None, price_data=None):
    """Run comprehensive AI analysis on current market state."""
    results = {
        'narrative': None,
        'anomalies': [],
        'strategy_advice': None,
        'patterns': [],
    }

    # Generate market narrative
    try:
        results['narrative'] = get_daily_briefing()
    except Exception as e:
        results['narrative'] = {'error': str(e)}

    # Get best patterns
    results['patterns'] = get_best_patterns()[:5]

    # Get strategy advice if we have performance data
    try:
        from self_learning import get_alert_accuracy_insights, get_best_strategies_for_regime

        alert_insights = get_alert_accuracy_insights()
        regime_strategies = get_best_strategies_for_regime()

        # Build performance data
        performance_data = {
            'best_alerts': alert_insights.get('best_alert_types', []),
            'worst_alerts': alert_insights.get('worst_alert_types', []),
            'current_regime': regime_strategies.get('regime', 'unknown'),
        }

        current_weights = {
            'trend': 0.30, 'squeeze': 0.20, 'rs': 0.20,
            'volume': 0.15, 'sentiment': 0.15
        }

        results['strategy_advice'] = get_strategy_advice(
            performance_data,
            current_weights,
            regime_strategies.get('regime', 'unknown')
        )
    except Exception as e:
        results['strategy_advice'] = {'error': str(e)}

    return results
