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

from config import config
from utils import get_logger, APIError

logger = get_logger(__name__)

# Data storage
AI_LEARNING_DIR = Path('ai_learning_data')
AI_LEARNING_DIR.mkdir(exist_ok=True)


def call_deepseek(prompt, system_prompt=None, max_tokens=2000, timeout=25):
    """Call DeepSeek API for AI analysis."""
    if not config.ai.api_key:
        logger.debug("DeepSeek API key not configured, trying X AI...")
        return call_xai(prompt, system_prompt, max_tokens, timeout)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = requests.post(
            config.ai.api_url,
            headers={
                "Authorization": f"Bearer {config.ai.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": config.ai.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": config.ai.temperature,
            },
            timeout=timeout
        )

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            logger.error(f"DeepSeek API returned {response.status_code}: {response.text[:200]}")
            # Fallback to X AI on error
            return call_xai(prompt, system_prompt, max_tokens, timeout)
    except requests.Timeout:
        logger.error(f"DeepSeek API timeout after {timeout}s, trying X AI...")
        return call_xai(prompt, system_prompt, max_tokens, timeout)
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}, trying X AI...")
        return call_xai(prompt, system_prompt, max_tokens, timeout)

    return None


def call_xai(prompt, system_prompt=None, max_tokens=2000, timeout=25):
    """Call X AI (Grok) API for AI analysis."""
    if not config.ai.xai_api_key:
        logger.warning("X AI API key not configured")
        return None

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = requests.post(
            config.ai.xai_api_url,
            headers={
                "Authorization": f"Bearer {config.ai.xai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": config.ai.xai_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": config.ai.temperature,
            },
            timeout=timeout
        )

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            logger.error(f"X AI API returned {response.status_code}: {response.text[:200]}")
    except requests.Timeout:
        logger.error(f"X AI API timeout after {timeout}s")
    except Exception as e:
        logger.error(f"X AI API error: {e}")

    return None


def call_ai(prompt, system_prompt=None, max_tokens=2000, timeout=25, prefer_xai=False, task_type="default"):
    """
    Call AI API with intelligent routing based on task complexity.

    Routing Strategy (based on A/B stress testing):
    - DeepSeek: Faster on simple/quick tasks (sentiment, calculations, quick queries)
    - X AI (Grok): 39% faster on heavy tasks (large data, complex reasoning, portfolios)

    Args:
        prompt: The prompt to send
        system_prompt: Optional system prompt
        max_tokens: Maximum response tokens
        timeout: Request timeout in seconds
        prefer_xai: If True, force X AI first (overrides auto-routing)
        task_type: Task category for smart routing:
            - "simple": Quick sentiment, calculations (use DeepSeek)
            - "heavy": Large data, complex analysis (use X AI)
            - "news": News synthesis (use X AI)
            - "portfolio": Portfolio/trade analysis (use X AI)
            - "narrative": Market narrative (use X AI)
            - "default": Auto-detect based on max_tokens

    Returns:
        AI response text or None
    """
    # Smart routing based on task type
    use_xai_first = prefer_xai

    if not use_xai_first:
        # Auto-route based on task type
        heavy_tasks = ["heavy", "news", "portfolio", "narrative", "catalyst", "theme", "strategy"]
        simple_tasks = ["simple", "sentiment", "calculation", "quick"]

        if task_type in heavy_tasks:
            use_xai_first = True
        elif task_type in simple_tasks:
            use_xai_first = False
        elif task_type == "default":
            # Auto-detect: heavy if max_tokens > 400 (complex output expected)
            use_xai_first = max_tokens > 400

    if use_xai_first:
        result = call_xai(prompt, system_prompt, max_tokens, timeout)
        if result:
            return result
        # Fallback to DeepSeek
        return call_deepseek(prompt, system_prompt, max_tokens, timeout)
    else:
        result = call_deepseek(prompt, system_prompt, max_tokens, timeout)
        if result:
            return result
        # Fallback to X AI
        return call_xai(prompt, system_prompt, max_tokens, timeout)


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

    response = call_ai(prompt, system_prompt, task_type="simple")

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

    response = call_ai(prompt, system_prompt, task_type="portfolio")

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

    response = call_ai(prompt, system_prompt, task_type="portfolio")

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

    response = call_ai(prompt, system_prompt, task_type="portfolio")

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
    except Exception as e:
        logger.error(f"Error processing price data: {e}")
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

    response = call_ai(prompt, system_prompt, task_type="strategy")

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

    response = call_ai(prompt, system_prompt, task_type="strategy")

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
# 5. AI MARKET NARRATOR (Enhanced with Real-Time Data)
# =============================================================================

def fetch_realtime_market_data():
    """
    Fetch real-time market data for briefing.
    Returns: dict with SPY, QQQ, VIX, and market status
    """
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor
    import pandas as pd

    market_data = {
        'spy': None,
        'qqq': None,
        'vix': None,
        'market_status': 'unknown',
        'timestamp': datetime.now().isoformat()
    }

    def fetch_ticker(ticker):
        try:
            # Use Ticker object for more reliable data access
            stock = yf.Ticker(ticker)
            hist = stock.history(period='2d')

            if hist is not None and len(hist) >= 1:
                # Get close prices - hist['Close'] is always a Series with Ticker.history()
                close = hist['Close']
                current = float(close.iloc[-1])
                prev = float(close.iloc[-2]) if len(close) >= 2 else current
                change_pct = ((current - prev) / prev) * 100 if prev else 0

                return {
                    'price': round(current, 2),
                    'change_pct': round(change_pct, 2)
                }
        except Exception as e:
            logger.debug(f"Ticker fetch error for {ticker}: {e}")
        return None

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                'spy': executor.submit(fetch_ticker, 'SPY'),
                'qqq': executor.submit(fetch_ticker, 'QQQ'),
                'vix': executor.submit(fetch_ticker, '^VIX')
            }

            for key, future in futures.items():
                try:
                    result = future.result(timeout=8)
                    if result:
                        market_data[key] = result
                except Exception as e:
                    logger.debug(f"Future error for {key}: {e}")

        # Determine market status based on time (EST)
        from datetime import time as dt_time
        now = datetime.now()
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        if now.weekday() < 5 and market_open <= now.time() <= market_close:
            market_data['market_status'] = 'open'
        else:
            market_data['market_status'] = 'closed'

    except Exception as e:
        logger.debug(f"Error fetching market data: {e}")

    return market_data


def get_trending_tickers():
    """
    Auto-detect current trending/key tickers from multiple sources.
    Returns list of tickers that are moving or in the news today.
    """
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor
    import glob

    trending = set()

    def get_top_movers():
        """Get top gainers and losers."""
        try:
            # Use major indices components that are moving
            spy = yf.Ticker('SPY')
            # Get holdings - top weighted stocks
            return ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK-B', 'JPM', 'V']
        except:
            return []

    def get_from_scan_results():
        """Get tickers from latest scan results."""
        try:
            import pandas as pd
            scan_files = glob.glob('scan_*.csv')
            if scan_files:
                df = pd.read_csv(max(scan_files))
                if 'ticker' in df.columns:
                    return df['ticker'].head(10).tolist()
                elif 'Ticker' in df.columns:
                    return df['Ticker'].head(10).tolist()
        except:
            pass
        return []

    def get_volume_leaders():
        """Get high volume stocks today."""
        # These typically have news
        return ['NVDA', 'AMD', 'TSLA', 'AAPL', 'SPY', 'QQQ', 'AMZN', 'META']

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(get_top_movers),
                executor.submit(get_from_scan_results),
                executor.submit(get_volume_leaders),
            ]
            for future in futures:
                try:
                    result = future.result(timeout=5)
                    trending.update(result)
                except:
                    pass
    except:
        pass

    # Always include these market leaders
    core_tickers = {'NVDA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'JPM', 'SPY', 'QQQ'}
    trending.update(core_tickers)

    return list(trending)[:20]  # Cap at 20 tickers


def fetch_news_with_xai(tickers=None, max_headlines=80):
    """
    Comprehensive news fetching from ALL sources.

    Fetches from ALL sources (not rotating) for complete market picture:
    - Reuters, Google News, Yahoo Finance
    - All sectors, all macro topics
    - Auto-detected trending tickers
    - Commodities, crypto, geopolitical
    """
    import feedparser
    from concurrent.futures import ThreadPoolExecutor

    headlines = []
    sources_used = []

    # ==========================================================================
    # AUTO-DETECT TRENDING TICKERS
    # ==========================================================================
    if tickers is None:
        tickers = get_trending_tickers()
        logger.debug(f"Auto-detected trending tickers: {tickers}")

    # ==========================================================================
    # ALL NEWS SOURCES - Comprehensive coverage (no rotation)
    # ==========================================================================

    all_feeds = []

    # CORE NEWS SOURCES (4)
    all_feeds.extend([
        ('Reuters Business', 'https://feeds.reuters.com/reuters/businessNews'),
        ('Reuters Markets', 'https://feeds.reuters.com/reuters/marketsNews'),
        ('Google Finance', 'https://news.google.com/rss/search?q=stock+market+today&hl=en-US&gl=US&ceid=US:en'),
        ('Yahoo Markets', 'https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US'),
    ])

    # MACRO & ECONOMY - ALL (4)
    all_feeds.extend([
        ('Fed/Rates', 'https://news.google.com/rss/search?q=federal+reserve+interest+rates&hl=en-US&gl=US&ceid=US:en'),
        ('Economy', 'https://news.google.com/rss/search?q=US+economy+GDP+jobs&hl=en-US&gl=US&ceid=US:en'),
        ('Inflation', 'https://news.google.com/rss/search?q=inflation+CPI+prices&hl=en-US&gl=US&ceid=US:en'),
        ('Trade/Tariffs', 'https://news.google.com/rss/search?q=trade+tariffs+china&hl=en-US&gl=US&ceid=US:en'),
    ])

    # ALL SECTORS (8)
    all_feeds.extend([
        ('Tech Sector', 'https://feeds.finance.yahoo.com/rss/2.0/headline?s=XLK&region=US&lang=en-US'),
        ('Financials', 'https://feeds.finance.yahoo.com/rss/2.0/headline?s=XLF&region=US&lang=en-US'),
        ('Healthcare', 'https://feeds.finance.yahoo.com/rss/2.0/headline?s=XLV&region=US&lang=en-US'),
        ('Energy', 'https://feeds.finance.yahoo.com/rss/2.0/headline?s=XLE&region=US&lang=en-US'),
        ('Consumer', 'https://feeds.finance.yahoo.com/rss/2.0/headline?s=XLY&region=US&lang=en-US'),
        ('Industrials', 'https://feeds.finance.yahoo.com/rss/2.0/headline?s=XLI&region=US&lang=en-US'),
        ('Real Estate', 'https://feeds.finance.yahoo.com/rss/2.0/headline?s=XLRE&region=US&lang=en-US'),
        ('Materials', 'https://feeds.finance.yahoo.com/rss/2.0/headline?s=XLB&region=US&lang=en-US'),
    ])

    # COMMODITIES & CRYPTO - ALL (4)
    all_feeds.extend([
        ('Oil/Energy', 'https://news.google.com/rss/search?q=crude+oil+price+energy&hl=en-US&gl=US&ceid=US:en'),
        ('Gold/Metals', 'https://news.google.com/rss/search?q=gold+silver+precious+metals&hl=en-US&gl=US&ceid=US:en'),
        ('Crypto', 'https://news.google.com/rss/search?q=bitcoin+ethereum+crypto&hl=en-US&gl=US&ceid=US:en'),
        ('Commodities', 'https://news.google.com/rss/search?q=commodities+copper+wheat&hl=en-US&gl=US&ceid=US:en'),
    ])

    # GEOPOLITICAL - ALL (3)
    all_feeds.extend([
        ('Geopolitics', 'https://news.google.com/rss/search?q=geopolitical+risk+markets&hl=en-US&gl=US&ceid=US:en'),
        ('China', 'https://news.google.com/rss/search?q=china+economy+markets&hl=en-US&gl=US&ceid=US:en'),
        ('Global Markets', 'https://news.google.com/rss/search?q=global+markets+europe+asia&hl=en-US&gl=US&ceid=US:en'),
    ])

    # EARNINGS & IPO (2)
    all_feeds.extend([
        ('Earnings', 'https://news.google.com/rss/search?q=earnings+report+beat+miss&hl=en-US&gl=US&ceid=US:en'),
        ('IPO/Deals', 'https://news.google.com/rss/search?q=IPO+merger+acquisition+deal&hl=en-US&gl=US&ceid=US:en'),
    ])

    # AUTO-DETECTED TRENDING TICKERS (dynamic)
    for ticker in tickers[:15]:  # Top 15 trending
        all_feeds.append(
            (f'{ticker}', f'https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US')
        )

    def fetch_feed(feed_tuple):
        """Fetch a single feed with source tracking."""
        name, url = feed_tuple
        try:
            feed = feedparser.parse(url)
            entries = []
            for entry in feed.entries[:4]:  # 4 per feed
                entries.append({
                    'title': entry.title,
                    'source': name
                })
            return entries
        except Exception as e:
            logger.debug(f"Feed error {name}: {e}")
            return []

    try:
        # Parallel fetch ALL feeds for comprehensive coverage
        logger.debug(f"Fetching from {len(all_feeds)} news sources...")
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(fetch_feed, all_feeds))

        # Combine all headlines, remove duplicates, track sources
        seen_titles = set()
        for feed_entries in results:
            for entry in feed_entries:
                title = entry.get('title', '')
                # Skip duplicates and very short titles
                if title and title not in seen_titles and len(title) > 20:
                    seen_titles.add(title)
                    headlines.append(title)
                    if entry.get('source') not in sources_used:
                        sources_used.append(entry.get('source'))

        if not headlines:
            return {'sentiment': 'neutral', 'headlines': [], 'summary': 'No news available', 'count': 0, 'sources': []}

        # Use X AI for comprehensive interpretation of ALL news
        prompt = f"""Analyze these {len(headlines[:max_headlines])} market headlines from {len(sources_used)} diverse sources.

SOURCES ANALYZED: {', '.join(sources_used)}
TRENDING TICKERS: {', '.join(tickers[:10])}

ALL HEADLINES:
{json.dumps(headlines[:max_headlines], indent=1)}

Synthesize ALL information comprehensively. Return JSON:
{{
    "sentiment": "bullish/bearish/neutral",
    "confidence": "high/medium/low",
    "key_news": "single most market-moving headline",
    "sector_sentiment": {{
        "tech": "bullish/bearish/neutral",
        "financials": "sentiment",
        "healthcare": "sentiment",
        "energy": "sentiment",
        "consumer": "sentiment",
        "industrials": "sentiment"
    }},
    "macro_factors": ["key macro/economic factor 1", "factor 2", "factor 3"],
    "geopolitical": ["geopolitical risk or development"],
    "trending_tickers_sentiment": {{"TICKER": "bullish/bearish/neutral for top 5 mentioned"}},
    "bullish_signals": ["up to 5 bullish catalysts"],
    "bearish_signals": ["up to 5 bearish risks"],
    "commodities": {{"oil": "up/down/stable", "gold": "trend", "crypto": "trend"}},
    "market_impact": "3-4 sentence synthesis: overall direction, key drivers, what smart money should watch, and potential surprises"
}}"""

        response = call_ai(prompt, "Chief market strategist. Synthesize all sources for comprehensive market view.", max_tokens=900, timeout=30, prefer_xai=True)

        if response:
            try:
                # Strip markdown if present
                text = response.strip()
                if text.startswith('```json'):
                    text = text[7:]
                elif text.startswith('```'):
                    text = text[3:]
                if text.endswith('```'):
                    text = text[:-3]
                text = text.strip()

                result = json.loads(text)
                result['headlines'] = headlines[:15]  # Return top 15 for display
                result['total_analyzed'] = len(headlines[:max_headlines])
                result['sources'] = sources_used  # All sources used
                result['trending_tickers'] = tickers[:10]
                return result
            except json.JSONDecodeError:
                logger.debug(f"JSON parse error: {response[:200]}")
                pass

        return {
            'sentiment': 'neutral',
            'headlines': headlines[:15],
            'summary': 'Headlines fetched but AI interpretation unavailable',
            'total_analyzed': len(headlines),
            'sources': sources_used,
            'trending_tickers': tickers[:10]
        }

    except Exception as e:
        logger.error(f"News fetch error: {e}")
        return {'sentiment': 'neutral', 'headlines': [], 'summary': str(e), 'count': 0, 'sources': []}


def generate_market_narrative(themes, sectors, top_stocks, news_data, market_data=None):
    """
    Generate an AI-powered market narrative with real-time data.
    """
    system_prompt = "You are an expert market analyst. Be concise and actionable."

    # Build market context from real-time data
    market_context = ""
    if market_data:
        spy = market_data.get('spy', {})
        vix = market_data.get('vix', {})
        if spy:
            market_context += f"SPY: ${spy.get('price', 'N/A')} ({spy.get('change_pct', 0):+.2f}%) "
        if vix:
            market_context += f"VIX: {vix.get('price', 'N/A')} "
        market_context += f"Market: {market_data.get('market_status', 'unknown')}"

    # Build news context
    news_context = ""
    if news_data and isinstance(news_data, dict):
        news_context = f"News sentiment: {news_data.get('sentiment', 'neutral')}"
        if news_data.get('key_news'):
            news_context += f" | Key: {news_data.get('key_news', '')[:50]}"

    prompt = f"""Real-time market briefing:

MARKET: {market_context if market_context else 'Data unavailable'}
NEWS: {news_context if news_context else 'No news'}
THEMES: {json.dumps([t.get('name', t) if isinstance(t, dict) else t for t in (themes or [])[:3]])}
TOP STOCKS: {json.dumps([s.get('ticker', s) if isinstance(s, dict) else s for s in (top_stocks or [])[:5]])}

Return JSON:
{{"headline":"5-7 words","market_mood":"bullish/bearish/neutral","main_narrative":"2 sentences with specific prices/levels","spy_view":"brief SPY outlook","key_opportunity":{{"ticker":"XXX","reason":"brief"}},"key_risk":"one sentence","tomorrow_watch":["item1","item2"]}}"""

    response = call_ai(prompt, system_prompt, max_tokens=600, task_type="narrative")

    if response:
        try:
            # Strip markdown code block if present
            text = response.strip()
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()

            result = json.loads(text)
            # Add real-time data to response
            if market_data:
                result['realtime_data'] = {
                    'spy': market_data.get('spy'),
                    'qqq': market_data.get('qqq'),
                    'vix': market_data.get('vix'),
                    'market_status': market_data.get('market_status'),
                    'timestamp': market_data.get('timestamp')
                }
            if news_data and isinstance(news_data, dict):
                result['news_sentiment'] = news_data.get('sentiment')
                result['news_confidence'] = news_data.get('confidence')
                result['total_headlines_analyzed'] = news_data.get('total_analyzed', 0)
                result['news_sources'] = news_data.get('sources', [])
                result['trending_tickers'] = news_data.get('trending_tickers', [])
                result['sector_sentiment'] = news_data.get('sector_sentiment', {})
                result['macro_factors'] = news_data.get('macro_factors', [])
                result['geopolitical'] = news_data.get('geopolitical', [])
                result['commodities'] = news_data.get('commodities', {})
                result['ticker_sentiment'] = news_data.get('trending_tickers_sentiment', {})
                result['bullish_signals'] = news_data.get('bullish_signals', [])
                result['bearish_signals'] = news_data.get('bearish_signals', [])
                result['top_headlines'] = news_data.get('headlines', [])[:10]
            return result
        except json.JSONDecodeError:
            return {'raw_narrative': response}

    return None


def get_daily_briefing(fast_mode: bool = True):
    """
    Generate and return today's AI market briefing with real-time data.

    Args:
        fast_mode: If True, use fast parallel fetching (recommended)
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
    import glob
    import traceback

    market_data = None
    news_data = None
    themes = []
    top_stocks = []
    errors = []

    try:
        # Parallel fetch: market data, news, themes, stocks
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Start all fetches in parallel
            market_future = executor.submit(fetch_realtime_market_data)
            news_future = executor.submit(fetch_news_with_xai)

            # Themes from fast stories (uses cache)
            def get_themes():
                try:
                    from fast_stories import run_fast_story_detection
                    detection = run_fast_story_detection(use_cache=True)
                    return detection.get('themes', [])
                except Exception as e:
                    logger.debug(f"Theme fetch error: {e}")
                    return []

            # Top stocks from scan file
            def get_top_stocks():
                scan_files = glob.glob('scan_*.csv')
                if scan_files:
                    import pandas as pd
                    try:
                        df = pd.read_csv(max(scan_files))
                        return df.head(10).to_dict('records')
                    except Exception as e:
                        logger.debug(f"Scan file read error: {e}")
                return []

            themes_future = executor.submit(get_themes)
            stocks_future = executor.submit(get_top_stocks)

            # Collect results (with timeouts)
            try:
                market_data = market_future.result(timeout=10)
            except FuturesTimeout:
                errors.append("market_data_timeout")
                logger.warning("Market data fetch timed out")
            except Exception as e:
                errors.append(f"market_data_error: {e}")

            try:
                news_data = news_future.result(timeout=25)
            except FuturesTimeout:
                errors.append("news_timeout")
                logger.warning("News fetch timed out")
            except Exception as e:
                errors.append(f"news_error: {e}")

            try:
                themes = themes_future.result(timeout=8)
            except FuturesTimeout:
                errors.append("themes_timeout")
            except Exception as e:
                errors.append(f"themes_error: {e}")

            try:
                top_stocks = stocks_future.result(timeout=5)
            except FuturesTimeout:
                errors.append("stocks_timeout")
            except Exception as e:
                errors.append(f"stocks_error: {e}")

        # Generate narrative with available data
        narrative = generate_market_narrative(themes, [], top_stocks, news_data, market_data)

        if narrative:
            # Add any fetch errors as warnings
            if errors:
                narrative['_fetch_warnings'] = errors
            return narrative
        else:
            return {
                'error': 'AI narrative generation failed',
                'market_data': market_data,
                'news_data': news_data,
                '_fetch_warnings': errors
            }

    except Exception as e:
        logger.error(f"Briefing generation error: {e}\n{traceback.format_exc()}")
        return {
            'error': f'Briefing generation failed: {str(e)}',
            '_fetch_warnings': errors
        }


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

    response = call_ai(prompt, system_prompt, task_type="simple")

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
        except Exception as e:
            logger.error(f"Error analyzing anomalies for {ticker}: {e}")
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

    response = call_ai(prompt, system_prompt, task_type="simple")

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

    response = call_ai(prompt, system_prompt, max_tokens=2000, task_type="heavy")

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

    response = call_ai(prompt, system_prompt, max_tokens=300, task_type="simple")

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


# =============================================================================
# 9. AI CATALYST DETECTOR (Real-time)
# =============================================================================

def load_catalyst_history():
    """Load catalyst detection history."""
    path = AI_LEARNING_DIR / 'catalysts.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'catalysts': [],
        'catalyst_outcomes': {},
        'catalyst_patterns': {},
    }


def save_catalyst_history(data):
    """Save catalyst history."""
    path = AI_LEARNING_DIR / 'catalysts.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


# Catalyst type definitions
CATALYST_TYPES = {
    'earnings': {'keywords': ['earnings', 'eps', 'revenue', 'guidance', 'beat', 'miss', 'quarterly'],
                 'impact': 'high', 'typical_move': '5-15%'},
    'fda': {'keywords': ['fda', 'approval', 'drug', 'trial', 'phase', 'pdufa'],
            'impact': 'very_high', 'typical_move': '10-50%'},
    'merger_acquisition': {'keywords': ['acquire', 'merger', 'buyout', 'takeover', 'deal'],
                           'impact': 'very_high', 'typical_move': '10-30%'},
    'analyst': {'keywords': ['upgrade', 'downgrade', 'price target', 'rating', 'analyst'],
                'impact': 'medium', 'typical_move': '2-8%'},
    'insider': {'keywords': ['insider', 'ceo buy', 'director', 'form 4', '10b5-1'],
                'impact': 'medium', 'typical_move': '2-5%'},
    'macro': {'keywords': ['fed', 'rate', 'inflation', 'jobs', 'gdp', 'tariff'],
              'impact': 'varies', 'typical_move': '1-5%'},
    'sector': {'keywords': ['sector', 'industry', 'peer', 'competitor'],
               'impact': 'medium', 'typical_move': '2-5%'},
    'product': {'keywords': ['launch', 'release', 'product', 'partnership', 'contract', 'award'],
                'impact': 'medium', 'typical_move': '3-10%'},
    'legal': {'keywords': ['lawsuit', 'sec', 'investigation', 'settlement', 'regulatory'],
              'impact': 'high', 'typical_move': '5-20%'},
    'short': {'keywords': ['short report', 'citron', 'hindenburg', 'muddy waters', 'fraud'],
              'impact': 'very_high', 'typical_move': '10-40%'},
}


def detect_catalyst_type(headline, content=None):
    """Detect catalyst type from headline/content."""
    text = (headline + ' ' + (content or '')).lower()

    detected = []
    for cat_type, config in CATALYST_TYPES.items():
        for keyword in config['keywords']:
            if keyword in text:
                detected.append({
                    'type': cat_type,
                    'keyword': keyword,
                    'impact': config['impact'],
                    'typical_move': config['typical_move'],
                })
                break

    return detected


def analyze_catalyst_realtime(ticker, headline, content=None, price_data=None, related_tickers=None):
    """
    Use AI to analyze a breaking catalyst in real-time.
    Provides immediate trading implications.
    """
    # First, detect catalyst type
    detected_types = detect_catalyst_type(headline, content)

    system_prompt = """You are a real-time catalyst analyst for trading.
Analyze breaking news and provide IMMEDIATE, ACTIONABLE trading implications.
Be specific about expected price moves, timing, and risk.
Speed matters - be concise but thorough."""

    price_context = ""
    if price_data is not None:
        try:
            current = float(price_data['Close'].iloc[-1])
            prev_close = float(price_data['Close'].iloc[-2])
            change = (current / prev_close - 1) * 100
            price_context = f"Current: ${current:.2f} ({change:+.1f}% today)"
        except Exception:
            price_context = "Price data unavailable"

    prompt = f"""BREAKING CATALYST ANALYSIS:

Ticker: {ticker}
Headline: {headline}
{f'Details: {content[:500]}' if content else ''}

Detected catalyst types: {json.dumps(detected_types, indent=2) if detected_types else 'Unknown'}
{f'Price context: {price_context}' if price_context else ''}
{f'Related tickers: {related_tickers}' if related_tickers else ''}

Provide REAL-TIME analysis in JSON:
{{
    "urgency": "immediate/today/this_week/monitor",
    "catalyst_type": "primary type",
    "catalyst_quality": "game_changer/significant/moderate/noise",

    "immediate_reaction": {{
        "expected_direction": "up/down/volatile",
        "expected_magnitude": "X-Y%",
        "confidence": "high/medium/low",
        "timeframe": "minutes/hours/days"
    }},

    "trading_action": {{
        "recommendation": "buy_now/buy_dip/sell/avoid/wait",
        "entry_zone": "price range or condition",
        "stop_loss": "price or percentage",
        "target": "price or percentage",
        "position_size": "full/half/quarter/paper"
    }},

    "key_levels": {{
        "support": "price",
        "resistance": "price",
        "breakout_trigger": "price"
    }},

    "secondary_plays": [
        {{"ticker": "SYMBOL", "relationship": "why related", "expected_move": "direction"}}
    ],

    "risks": ["risk 1", "risk 2"],
    "watch_for": ["confirmation signal", "invalidation signal"],

    "follow_up_catalyst": "what news to watch next",
    "reasoning": "brief explanation of analysis"
}}"""

    response = call_ai(prompt, system_prompt, max_tokens=1500, task_type="catalyst")

    if response:
        try:
            analysis = json.loads(response)

            # Save catalyst for learning
            history = load_catalyst_history()
            catalyst_record = {
                'id': f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'ticker': ticker,
                'headline': headline,
                'detected_types': detected_types,
                'analysis': analysis,
                'timestamp': datetime.now().isoformat(),
                'outcome': None,  # To be filled later
            }
            history['catalysts'].append(catalyst_record)
            history['catalysts'] = history['catalysts'][-200:]
            save_catalyst_history(history)

            return analysis
        except json.JSONDecodeError:
            return {'raw_analysis': response, 'detected_types': detected_types}

    return {'detected_types': detected_types}


def update_catalyst_outcome(catalyst_id, actual_move_pct, was_profitable):
    """Update catalyst with actual outcome for learning."""
    history = load_catalyst_history()

    for catalyst in history['catalysts']:
        if catalyst['id'] == catalyst_id:
            catalyst['outcome'] = {
                'actual_move': actual_move_pct,
                'was_profitable': was_profitable,
                'verified_at': datetime.now().isoformat(),
            }

            # Update catalyst patterns
            cat_type = catalyst['analysis'].get('catalyst_type', 'unknown')
            if cat_type not in history['catalyst_patterns']:
                history['catalyst_patterns'][cat_type] = {'total': 0, 'profitable': 0, 'avg_move': []}

            history['catalyst_patterns'][cat_type]['total'] += 1
            if was_profitable:
                history['catalyst_patterns'][cat_type]['profitable'] += 1
            history['catalyst_patterns'][cat_type]['avg_move'].append(actual_move_pct)

            # Keep only recent moves
            history['catalyst_patterns'][cat_type]['avg_move'] = \
                history['catalyst_patterns'][cat_type]['avg_move'][-50:]
            break

    save_catalyst_history(history)


def get_catalyst_stats():
    """Get catalyst type performance statistics."""
    history = load_catalyst_history()

    stats = []
    for cat_type, data in history.get('catalyst_patterns', {}).items():
        if data['total'] >= 3:
            win_rate = data['profitable'] / data['total'] * 100
            avg_move = sum(data['avg_move']) / len(data['avg_move']) if data['avg_move'] else 0
            stats.append({
                'type': cat_type,
                'win_rate': round(win_rate, 1),
                'avg_move': round(avg_move, 2),
                'total_trades': data['total'],
            })

    stats.sort(key=lambda x: x['win_rate'], reverse=True)
    return stats


# =============================================================================
# 10. AI THEME LIFECYCLE PREDICTOR
# =============================================================================

def load_theme_lifecycle_data():
    """Load theme lifecycle tracking data."""
    path = AI_LEARNING_DIR / 'theme_lifecycle.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'themes': {},
        'lifecycle_history': [],
        'predictions': [],
    }


def save_theme_lifecycle_data(data):
    """Save theme lifecycle data."""
    path = AI_LEARNING_DIR / 'theme_lifecycle.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


THEME_LIFECYCLE_STAGES = {
    'nascent': {'description': 'Just emerging, few aware', 'typical_duration': '1-4 weeks', 'opportunity': 'very_high'},
    'emerging': {'description': 'Gaining traction, early adopters', 'typical_duration': '2-8 weeks', 'opportunity': 'high'},
    'growth': {'description': 'Broad awareness, momentum building', 'typical_duration': '4-12 weeks', 'opportunity': 'medium'},
    'peak': {'description': 'Maximum hype, everyone talking', 'typical_duration': '1-4 weeks', 'opportunity': 'low_risk'},
    'mature': {'description': 'Established, less volatility', 'typical_duration': 'ongoing', 'opportunity': 'selective'},
    'fading': {'description': 'Interest declining, rotation out', 'typical_duration': '2-6 weeks', 'opportunity': 'avoid'},
    'dead': {'description': 'No longer relevant', 'typical_duration': 'n/a', 'opportunity': 'none'},
}


def analyze_theme_lifecycle(theme_name, theme_data, historical_performance=None):
    """
    Use AI to analyze a theme's lifecycle stage and predict trajectory.
    """
    system_prompt = """You are a thematic investment analyst specializing in lifecycle analysis.
Determine where a market theme is in its lifecycle and predict its trajectory.
Be specific about timing and actionable implications."""

    prompt = f"""Analyze the lifecycle stage of this market theme:

Theme: {theme_name}

Current Data:
{json.dumps(theme_data, indent=2)}

Historical Performance (if available):
{json.dumps(historical_performance, indent=2) if historical_performance else 'Not available'}

Lifecycle Stages Reference:
{json.dumps(THEME_LIFECYCLE_STAGES, indent=2)}

Provide lifecycle analysis in JSON:
{{
    "current_stage": "nascent/emerging/growth/peak/mature/fading/dead",
    "stage_confidence": "high/medium/low",
    "stage_evidence": ["evidence point 1", "evidence point 2"],

    "trajectory": {{
        "direction": "accelerating/stable/decelerating",
        "next_stage": "predicted next stage",
        "time_to_transition": "estimated time",
        "transition_triggers": ["what would cause transition"]
    }},

    "opportunity_window": {{
        "status": "open/closing/closed",
        "remaining_upside": "estimated %",
        "risk_reward": "favorable/neutral/unfavorable",
        "best_entry": "now/pullback/breakout/avoid"
    }},

    "key_stocks": {{
        "leaders": ["tickers leading the theme"],
        "laggards": ["tickers that could catch up"],
        "avoid": ["overextended or problematic"]
    }},

    "rotation_signal": {{
        "rotating_from": "what money is leaving",
        "rotating_to": "what money is entering",
        "strength": "strong/moderate/weak"
    }},

    "comparable_themes": [
        {{"theme": "historical theme", "similarity": "what's similar", "outcome": "how it played out"}}
    ],

    "actionable_insight": "most important takeaway",
    "watch_list": ["signals to monitor for changes"]
}}"""

    response = call_ai(prompt, system_prompt, max_tokens=1500, task_type="theme")

    if response:
        try:
            analysis = json.loads(response)

            # Save lifecycle analysis
            data = load_theme_lifecycle_data()

            # Update theme tracking
            if theme_name not in data['themes']:
                data['themes'][theme_name] = {
                    'first_seen': datetime.now().isoformat(),
                    'stage_history': [],
                }

            data['themes'][theme_name]['stage_history'].append({
                'stage': analysis['current_stage'],
                'timestamp': datetime.now().isoformat(),
                'analysis': analysis,
            })

            # Keep only recent history
            data['themes'][theme_name]['stage_history'] = \
                data['themes'][theme_name]['stage_history'][-30:]

            save_theme_lifecycle_data(data)

            return analysis
        except json.JSONDecodeError:
            return {'raw_analysis': response}

    return None


def predict_theme_rotation(current_themes, market_regime, sector_performance):
    """
    Use AI to predict which themes will rotate in/out.
    """
    system_prompt = """You are a thematic rotation specialist.
Predict which market themes will gain or lose favor based on current conditions.
Be specific about timing and magnitude of rotations."""

    prompt = f"""Predict theme rotation based on current market conditions:

Current Hot Themes:
{json.dumps(current_themes[:10], indent=2) if current_themes else 'None identified'}

Market Regime: {market_regime}

Sector Performance:
{json.dumps(dict(list(sector_performance.items())[:10]), indent=2) if isinstance(sector_performance, dict) else json.dumps(sector_performance[:10] if sector_performance else [], indent=2)}

Predict rotation in JSON:
{{
    "rotation_outlook": "risk_on/risk_off/selective/choppy",

    "themes_gaining": [
        {{
            "theme": "theme name",
            "catalyst": "why gaining favor",
            "expected_duration": "how long",
            "confidence": "high/medium/low",
            "top_plays": ["ticker 1", "ticker 2"]
        }}
    ],

    "themes_fading": [
        {{
            "theme": "theme name",
            "reason": "why losing favor",
            "exit_urgency": "immediate/soon/gradual",
            "what_to_sell": ["ticker 1", "ticker 2"]
        }}
    ],

    "emerging_themes": [
        {{
            "theme": "potential new theme",
            "early_signals": ["signal 1", "signal 2"],
            "catalyst": "what could ignite it",
            "probability": "high/medium/low"
        }}
    ],

    "cross_theme_trades": [
        {{
            "long": "theme/ticker to buy",
            "short": "theme/ticker to sell/avoid",
            "rationale": "why this pair trade"
        }}
    ],

    "timing": {{
        "rotation_speed": "fast/gradual/slow",
        "key_dates": ["dates to watch"],
        "trigger_events": ["events that could accelerate"]
    }},

    "contrarian_view": "what the crowd is missing"
}}"""

    response = call_ai(prompt, system_prompt, max_tokens=1500, task_type="theme")

    if response:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {'raw_analysis': response}

    return None


def get_theme_lifecycle_summary():
    """Get summary of all tracked themes and their stages."""
    data = load_theme_lifecycle_data()

    summary = []
    for theme_name, theme_data in data.get('themes', {}).items():
        history = theme_data.get('stage_history', [])
        if history:
            latest = history[-1]
            summary.append({
                'theme': theme_name,
                'current_stage': latest.get('stage', 'unknown'),
                'last_updated': latest.get('timestamp'),
                'trajectory': latest.get('analysis', {}).get('trajectory', {}).get('direction', 'unknown'),
            })

    return summary


# =============================================================================
# 11. AI OPTIONS FLOW ANALYZER
# =============================================================================

def load_options_flow_data():
    """Load options flow analysis data."""
    path = AI_LEARNING_DIR / 'options_flow.json'
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'flow_analyses': [],
        'unusual_activity': [],
        'flow_accuracy': {},
    }


def save_options_flow_data(data):
    """Save options flow data."""
    path = AI_LEARNING_DIR / 'options_flow.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def analyze_options_flow(ticker, options_data, price_data=None, news_context=None):
    """
    Use AI to analyze options flow for smart money signals.

    options_data should contain:
    - unusual_volume: list of unusual options activity
    - put_call_ratio: current P/C ratio
    - iv_rank: implied volatility rank
    - large_trades: significant block trades
    """
    system_prompt = """You are an options flow analyst specializing in detecting institutional activity.
Analyze options data to identify smart money positioning and predict stock direction.
Focus on unusual activity that indicates informed trading."""

    price_context = ""
    if price_data is not None:
        try:
            current = float(price_data['Close'].iloc[-1])
            change_5d = (current / float(price_data['Close'].iloc[-5]) - 1) * 100
            price_context = f"Stock at ${current:.2f}, 5-day change: {change_5d:+.1f}%"
        except Exception:
            price_context = "Price data unavailable"

    prompt = f"""Analyze options flow for institutional signals:

Ticker: {ticker}
{f'Price Context: {price_context}' if price_context else ''}

Options Data:
{json.dumps(options_data, indent=2)}

{f'News Context: {news_context}' if news_context else ''}

Provide options flow analysis in JSON:
{{
    "smart_money_signal": "bullish/bearish/neutral/mixed",
    "signal_strength": "strong/moderate/weak",
    "confidence": "high/medium/low",

    "key_observations": [
        {{
            "observation": "what was noticed",
            "significance": "why it matters",
            "historical_accuracy": "how often this signal works"
        }}
    ],

    "institutional_positioning": {{
        "direction": "accumulating/distributing/neutral",
        "timeframe": "near_term/medium_term/long_term",
        "size_estimate": "large/medium/small",
        "evidence": ["evidence point 1", "evidence point 2"]
    }},

    "unusual_activity": [
        {{
            "type": "call_sweep/put_sweep/straddle/etc",
            "strike": "price",
            "expiry": "date",
            "premium": "amount",
            "interpretation": "what it suggests"
        }}
    ],

    "implied_move": {{
        "expected_range": "low to high price",
        "by_date": "expiration or event date",
        "probability": "% chance of move"
    }},

    "trading_implication": {{
        "stock_action": "buy/sell/hold/avoid",
        "options_play": "specific options strategy if applicable",
        "risk_level": "high/medium/low",
        "catalyst_timing": "when move expected"
    }},

    "warnings": ["red flag 1", "red flag 2"],
    "follow_flow": ["what to watch for confirmation"]
}}"""

    response = call_ai(prompt, system_prompt, max_tokens=1500, task_type="portfolio")

    if response:
        try:
            analysis = json.loads(response)

            # Save analysis
            data = load_options_flow_data()
            flow_record = {
                'id': f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                'ticker': ticker,
                'options_data': options_data,
                'analysis': analysis,
                'timestamp': datetime.now().isoformat(),
                'outcome': None,
            }
            data['flow_analyses'].append(flow_record)
            data['flow_analyses'] = data['flow_analyses'][-100:]

            # Track unusual activity
            if analysis.get('signal_strength') == 'strong':
                data['unusual_activity'].append({
                    'ticker': ticker,
                    'signal': analysis['smart_money_signal'],
                    'timestamp': datetime.now().isoformat(),
                })
                data['unusual_activity'] = data['unusual_activity'][-50:]

            save_options_flow_data(data)

            return analysis
        except json.JSONDecodeError:
            return {'raw_analysis': response}

    return None


def update_options_flow_outcome(flow_id, actual_move_pct, was_correct):
    """Update options flow analysis with actual outcome."""
    data = load_options_flow_data()

    for flow in data['flow_analyses']:
        if flow['id'] == flow_id:
            flow['outcome'] = {
                'actual_move': actual_move_pct,
                'was_correct': was_correct,
                'verified_at': datetime.now().isoformat(),
            }

            # Update accuracy tracking
            signal = flow['analysis'].get('smart_money_signal', 'unknown')
            if signal not in data['flow_accuracy']:
                data['flow_accuracy'][signal] = {'correct': 0, 'incorrect': 0}

            if was_correct:
                data['flow_accuracy'][signal]['correct'] += 1
            else:
                data['flow_accuracy'][signal]['incorrect'] += 1
            break

    save_options_flow_data(data)


def get_options_flow_accuracy():
    """Get options flow signal accuracy."""
    data = load_options_flow_data()

    accuracy = []
    for signal, stats in data.get('flow_accuracy', {}).items():
        total = stats['correct'] + stats['incorrect']
        if total >= 5:
            acc = stats['correct'] / total * 100
            accuracy.append({
                'signal': signal,
                'accuracy': round(acc, 1),
                'total': total,
            })

    accuracy.sort(key=lambda x: x['accuracy'], reverse=True)
    return accuracy


def scan_options_unusual_activity(tickers, threshold_volume_ratio=3.0):
    """
    Scan multiple tickers for unusual options activity.
    Returns tickers with significant smart money signals.
    """
    unusual = []

    for ticker in tickers[:20]:  # Limit to avoid API overload
        try:
            # Get options data (would integrate with real options data source)
            # For now, this is a placeholder structure
            options_data = get_options_data_for_ticker(ticker)

            if options_data and options_data.get('volume_ratio', 1) >= threshold_volume_ratio:
                analysis = analyze_options_flow(ticker, options_data)
                if analysis and analysis.get('signal_strength') in ['strong', 'moderate']:
                    unusual.append({
                        'ticker': ticker,
                        'signal': analysis.get('smart_money_signal'),
                        'strength': analysis.get('signal_strength'),
                        'analysis': analysis,
                    })
        except Exception as e:
            logger.debug(f"Error scanning options for {ticker}: {e}")
            continue

    # Sort by signal strength
    strength_order = {'strong': 0, 'moderate': 1, 'weak': 2}
    unusual.sort(key=lambda x: strength_order.get(x.get('strength', 'weak'), 3))

    return unusual


def get_options_data_for_ticker(ticker):
    """
    Get options data for a ticker.
    This would integrate with a real options data source.
    Returns placeholder structure for now.
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)

        # Get options chain
        try:
            expirations = stock.options
            if not expirations:
                return None

            # Get nearest expiration
            chain = stock.option_chain(expirations[0])
            calls = chain.calls
            puts = chain.puts

            if calls.empty and puts.empty:
                return None

            # Calculate basic metrics
            total_call_volume = calls['volume'].sum() if not calls.empty else 0
            total_put_volume = puts['volume'].sum() if not puts.empty else 0
            total_call_oi = calls['openInterest'].sum() if not calls.empty else 0
            total_put_oi = puts['openInterest'].sum() if not puts.empty else 0

            put_call_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else 1

            # Find unusual volume (volume > open interest)
            unusual_calls = calls[calls['volume'] > calls['openInterest'] * 2] if not calls.empty else []
            unusual_puts = puts[puts['volume'] > puts['openInterest'] * 2] if not puts.empty else []

            return {
                'put_call_ratio': round(put_call_ratio, 2),
                'total_call_volume': int(total_call_volume),
                'total_put_volume': int(total_put_volume),
                'call_oi': int(total_call_oi),
                'put_oi': int(total_put_oi),
                'unusual_call_count': len(unusual_calls) if hasattr(unusual_calls, '__len__') else 0,
                'unusual_put_count': len(unusual_puts) if hasattr(unusual_puts, '__len__') else 0,
                'volume_ratio': (total_call_volume + total_put_volume) / max(total_call_oi + total_put_oi, 1),
                'expiration': expirations[0],
            }
        except Exception:
            return None
    except Exception as e:
        logger.debug(f"Error getting options data for {ticker}: {e}")
        return None


# =============================================================================
# ENHANCED AI INTERFACE
# =============================================================================

def run_realtime_ai_scan(news_items=None, themes=None, top_stocks=None):
    """
    Run real-time AI analysis including new features.
    Returns comprehensive real-time insights.
    """
    results = {
        'catalysts': [],
        'theme_lifecycle': [],
        'options_signals': [],
        'rotation_prediction': None,
    }

    # Analyze catalysts from news
    if news_items:
        for item in news_items[:10]:
            ticker = item.get('ticker')
            headline = item.get('headline') or item.get('title')
            if ticker and headline:
                try:
                    catalyst = analyze_catalyst_realtime(ticker, headline)
                    if catalyst and catalyst.get('urgency') in ['immediate', 'today']:
                        results['catalysts'].append({
                            'ticker': ticker,
                            'headline': headline,
                            'analysis': catalyst,
                        })
                except Exception as e:
                    logger.error(f"Error analyzing catalyst: {e}")

    # Analyze theme lifecycles
    if themes:
        for theme in themes[:5]:
            theme_name = theme.get('theme') or theme.get('name')
            if theme_name:
                try:
                    lifecycle = analyze_theme_lifecycle(theme_name, theme)
                    if lifecycle:
                        results['theme_lifecycle'].append({
                            'theme': theme_name,
                            'analysis': lifecycle,
                        })
                except Exception as e:
                    logger.error(f"Error analyzing theme lifecycle: {e}")

    # Scan options for top stocks
    if top_stocks:
        tickers = [s.get('ticker') if isinstance(s, dict) else s for s in top_stocks[:10] if s]
        try:
            options_signals = scan_options_unusual_activity(tickers)
            results['options_signals'] = options_signals[:5]
        except Exception as e:
            logger.error(f"Error scanning options: {e}")

    # Predict theme rotation
    if themes:
        try:
            results['rotation_prediction'] = predict_theme_rotation(
                themes,
                'unknown',  # Would get from market_health
                []  # Would get from sector_rotation
            )
        except Exception as e:
            logger.error(f"Error predicting rotation: {e}")

    return results


def format_realtime_ai_alerts(realtime_results):
    """Format real-time AI results for Telegram."""
    msg = "🚨 *REAL-TIME AI ALERTS*\n\n"

    # Urgent catalysts
    catalysts = realtime_results.get('catalysts', [])
    if catalysts:
        msg += "*⚡ BREAKING CATALYSTS:*\n"
        for c in catalysts[:3]:
            analysis = c.get('analysis', {})
            urgency = analysis.get('urgency', 'unknown')
            direction = analysis.get('immediate_reaction', {}).get('expected_direction', '?')
            magnitude = analysis.get('immediate_reaction', {}).get('expected_magnitude', '?')
            msg += f"• *{c['ticker']}*: {c['headline'][:50]}...\n"
            msg += f"  → {direction.upper()} {magnitude} ({urgency})\n"
        msg += "\n"

    # Theme lifecycle alerts
    lifecycle = realtime_results.get('theme_lifecycle', [])
    if lifecycle:
        msg += "*📈 THEME STATUS:*\n"
        for t in lifecycle[:3]:
            analysis = t.get('analysis', {})
            stage = analysis.get('current_stage', '?')
            trajectory = analysis.get('trajectory', {}).get('direction', '?')
            msg += f"• {t['theme']}: {stage.upper()} ({trajectory})\n"
        msg += "\n"

    # Options signals
    options = realtime_results.get('options_signals', [])
    if options:
        msg += "*🎯 SMART MONEY SIGNALS:*\n"
        for o in options[:3]:
            signal = o.get('signal', '?')
            strength = o.get('strength', '?')
            msg += f"• *{o['ticker']}*: {signal.upper()} ({strength})\n"
        msg += "\n"

    # Rotation prediction
    rotation = realtime_results.get('rotation_prediction', {})
    if rotation and not rotation.get('raw_analysis'):
        gaining = rotation.get('themes_gaining', [])
        fading = rotation.get('themes_fading', [])
        if gaining or fading:
            msg += "*🔄 ROTATION OUTLOOK:*\n"
            if gaining:
                msg += f"📈 Gaining: {', '.join([t['theme'] for t in gaining[:2]])}\n"
            if fading:
                msg += f"📉 Fading: {', '.join([t['theme'] for t in fading[:2]])}\n"

    if msg == "🚨 *REAL-TIME AI ALERTS*\n\n":
        msg += "_No urgent signals detected._"

    return msg
