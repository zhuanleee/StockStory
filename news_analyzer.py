#!/usr/bin/env python3
"""
AI News Analyzer

Fetches and analyzes news for stocks/sectors.
Uses DeepSeek AI for intelligent sentiment analysis.
"""

import os
import requests
import re
from datetime import datetime, timedelta
from collections import Counter
import json
import warnings
warnings.filterwarnings('ignore')

# DeepSeek API Configuration (set via environment variable for security)
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


# Sentiment keywords with weights
BULLISH_KEYWORDS = {
    # Strong bullish
    'beats': 3, 'exceeds': 3, 'record': 3, 'soars': 3, 'surges': 3,
    'breakthrough': 3, 'approval': 3, 'upgraded': 3, 'outperform': 3,
    # Medium bullish
    'raises': 2, 'higher': 2, 'growth': 2, 'strong': 2, 'bullish': 2,
    'positive': 2, 'gains': 2, 'rally': 2, 'jumps': 2, 'rises': 2,
    # Weak bullish
    'buy': 1, 'upside': 1, 'opportunity': 1, 'optimistic': 1, 'improving': 1,
}

BEARISH_KEYWORDS = {
    # Strong bearish
    'misses': 3, 'plunges': 3, 'crashes': 3, 'downgraded': 3, 'underperform': 3,
    'investigation': 3, 'lawsuit': 3, 'recall': 3, 'fraud': 3, 'bankruptcy': 3,
    # Medium bearish
    'cuts': 2, 'lower': 2, 'weak': 2, 'bearish': 2, 'negative': 2,
    'falls': 2, 'drops': 2, 'declines': 2, 'concerns': 2, 'warning': 2,
    # Weak bearish
    'sell': 1, 'downside': 1, 'risk': 1, 'disappointing': 1, 'slowing': 1,
}

# Catalyst keywords
CATALYST_KEYWORDS = {
    'earnings': 'EARNINGS',
    'guidance': 'GUIDANCE',
    'fda': 'FDA',
    'acquisition': 'M&A',
    'merger': 'M&A',
    'buyback': 'BUYBACK',
    'dividend': 'DIVIDEND',
    'split': 'STOCK_SPLIT',
    'insider': 'INSIDER',
    'upgrade': 'ANALYST',
    'downgrade': 'ANALYST',
    'target': 'PRICE_TARGET',
    'contract': 'CONTRACT',
    'partnership': 'PARTNERSHIP',
    'launch': 'PRODUCT_LAUNCH',
}


# ============================================================
# DEEPSEEK AI ANALYSIS
# ============================================================

def analyze_with_deepseek(ticker, headlines):
    """
    Use DeepSeek AI for intelligent news analysis.
    Returns sentiment, key insights, and trading implications.
    """
    if not headlines:
        return None

    headlines_text = "\n".join([f"- {h['title']}" for h in headlines[:10]])

    prompt = f"""Analyze these news headlines for {ticker} stock and provide a trading-focused analysis.

Headlines:
{headlines_text}

Respond in this exact JSON format:
{{
    "sentiment": "STRONG_BULLISH" or "BULLISH" or "NEUTRAL" or "BEARISH" or "STRONG_BEARISH",
    "confidence": 1-100,
    "key_catalyst": "main driver (e.g., earnings beat, FDA approval, etc.)",
    "summary": "1-2 sentence summary of news sentiment",
    "trading_implication": "buy/hold/sell recommendation with brief reason",
    "risk_factors": ["risk 1", "risk 2"]
}}

Be concise. Focus on actionable trading insights."""

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a financial analyst specializing in stock news analysis. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']

            # Parse JSON from response
            # Handle potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            analysis = json.loads(content.strip())
            return analysis
        else:
            print(f"DeepSeek API error: {response.status_code}")
            return None

    except Exception as e:
        print(f"DeepSeek analysis error: {e}")
        return None


def analyze_sector_news_ai(sector, tickers):
    """
    AI-powered sector news analysis.
    Aggregates news from multiple tickers in a sector.
    """
    all_headlines = []

    for ticker in tickers[:5]:  # Limit to avoid rate limits
        headlines = scrape_finviz_news(ticker)
        for h in headlines[:3]:
            h['ticker'] = ticker
            all_headlines.append(h)

    if not all_headlines:
        return None

    headlines_text = "\n".join([f"- [{h.get('ticker', '')}] {h['title']}" for h in all_headlines])

    prompt = f"""Analyze these news headlines for the {sector} sector and identify themes.

Headlines:
{headlines_text}

Respond in this exact JSON format:
{{
    "sector_sentiment": "STRONG_BULLISH" or "BULLISH" or "NEUTRAL" or "BEARISH" or "STRONG_BEARISH",
    "confidence": 1-100,
    "main_theme": "key theme driving the sector",
    "best_positioned": ["ticker1", "ticker2"],
    "worst_positioned": ["ticker1"],
    "sector_catalyst": "what's driving sector movement",
    "outlook": "1-2 sentence sector outlook"
}}"""

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a sector analyst. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        return None

    except Exception as e:
        print(f"Sector analysis error: {e}")
        return None


def scrape_finviz_news(ticker):
    """Scrape news from Finviz."""
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        # Extract news headlines - class comes before href in HTML
        news_pattern = r'class="tab-link-news"[^>]*>([^<]+)<'
        matches = re.findall(news_pattern, response.text)

        headlines = []
        for title in matches[:10]:
            headlines.append({
                'title': title.strip(),
                'url': '',
                'source': 'finviz',
            })

        return headlines
    except Exception as e:
        return []


def analyze_headline_sentiment(headline):
    """Analyze sentiment of a single headline."""
    text = headline.lower()

    bullish_score = 0
    bearish_score = 0
    catalysts = []

    # Check bullish keywords
    for word, weight in BULLISH_KEYWORDS.items():
        if word in text:
            bullish_score += weight

    # Check bearish keywords
    for word, weight in BEARISH_KEYWORDS.items():
        if word in text:
            bearish_score += weight

    # Check for catalysts
    for keyword, catalyst in CATALYST_KEYWORDS.items():
        if keyword in text:
            catalysts.append(catalyst)

    # Determine sentiment
    if bullish_score > bearish_score:
        sentiment = 'BULLISH'
    elif bearish_score > bullish_score:
        sentiment = 'BEARISH'
    else:
        sentiment = 'NEUTRAL'

    return {
        'sentiment': sentiment,
        'bullish_score': bullish_score,
        'bearish_score': bearish_score,
        'catalysts': list(set(catalysts)),
    }


def analyze_ticker_news(ticker, use_ai=True):
    """Full news analysis for a ticker using AI."""
    headlines = scrape_finviz_news(ticker)

    if not headlines:
        return {
            'ticker': ticker,
            'headline_count': 0,
            'overall_sentiment': 'NO_DATA',
            'headlines': [],
        }

    # Try AI analysis first
    ai_analysis = None
    if use_ai and DEEPSEEK_API_KEY:
        ai_analysis = analyze_with_deepseek(ticker, headlines)

    if ai_analysis:
        # Use AI analysis
        return {
            'ticker': ticker,
            'headline_count': len(headlines),
            'overall_sentiment': ai_analysis.get('sentiment', 'NEUTRAL'),
            'confidence': ai_analysis.get('confidence', 0),
            'key_catalyst': ai_analysis.get('key_catalyst', ''),
            'summary': ai_analysis.get('summary', ''),
            'trading_implication': ai_analysis.get('trading_implication', ''),
            'risk_factors': ai_analysis.get('risk_factors', []),
            'headlines': [{'title': h['title'], 'sentiment': 'AI_ANALYZED'} for h in headlines[:5]],
            'ai_powered': True,
        }

    # Fallback to keyword analysis
    analyzed_headlines = []
    total_bullish = 0
    total_bearish = 0
    all_catalysts = []

    for h in headlines:
        analysis = analyze_headline_sentiment(h['title'])
        total_bullish += analysis['bullish_score']
        total_bearish += analysis['bearish_score']
        all_catalysts.extend(analysis['catalysts'])

        analyzed_headlines.append({
            'title': h['title'],
            'sentiment': analysis['sentiment'],
            'catalysts': analysis['catalysts'],
        })

    # Overall sentiment
    if total_bullish > total_bearish * 1.5:
        overall = 'STRONG_BULLISH'
    elif total_bullish > total_bearish:
        overall = 'BULLISH'
    elif total_bearish > total_bullish * 1.5:
        overall = 'STRONG_BEARISH'
    elif total_bearish > total_bullish:
        overall = 'BEARISH'
    else:
        overall = 'NEUTRAL'

    # Most common catalysts
    catalyst_counts = Counter(all_catalysts)

    return {
        'ticker': ticker,
        'headline_count': len(headlines),
        'overall_sentiment': overall,
        'bullish_score': total_bullish,
        'bearish_score': total_bearish,
        'top_catalysts': catalyst_counts.most_common(3),
        'headlines': analyzed_headlines[:5],
        'ai_powered': False,
    }


def summarize_news(headlines):
    """
    Smart summarization of news headlines.
    Groups by theme and extracts key points.
    """
    if not headlines:
        return "No recent news found."

    # Group headlines by detected catalyst
    by_catalyst = {}
    general = []

    for h in headlines:
        if h.get('catalysts'):
            for cat in h['catalysts']:
                if cat not in by_catalyst:
                    by_catalyst[cat] = []
                by_catalyst[cat].append(h['title'])
        else:
            general.append(h['title'])

    # Build summary
    summary_parts = []

    # Prioritized catalysts
    priority = ['FDA', 'EARNINGS', 'M&A', 'ANALYST', 'GUIDANCE', 'CONTRACT']

    for cat in priority:
        if cat in by_catalyst:
            summary_parts.append(f"**{cat}:** {by_catalyst[cat][0][:80]}")

    # Add remaining catalysts
    for cat, titles in by_catalyst.items():
        if cat not in priority:
            summary_parts.append(f"**{cat}:** {titles[0][:80]}")

    # Add general news if space
    if len(summary_parts) < 3 and general:
        summary_parts.append(f"**Other:** {general[0][:80]}")

    return "\n".join(summary_parts[:5])


def format_news_analysis(ticker, analysis):
    """Format news analysis for Telegram."""
    sentiment_emoji = {
        'STRONG_BULLISH': '🟢🟢',
        'BULLISH': '🟢',
        'NEUTRAL': '🟡',
        'BEARISH': '🔴',
        'STRONG_BEARISH': '🔴🔴',
        'NO_DATA': '⚪',
    }

    msg = f"📰 *{ticker} NEWS ANALYSIS*"
    if analysis.get('ai_powered'):
        msg += " 🤖\n\n"
    else:
        msg += "\n\n"

    sentiment = analysis['overall_sentiment']
    msg += f"*Sentiment:* {sentiment_emoji.get(sentiment, '')} {sentiment}"

    if analysis.get('confidence'):
        msg += f" ({analysis['confidence']}% confidence)"
    msg += "\n"

    msg += f"Headlines: {analysis['headline_count']}\n"

    # AI-powered insights
    if analysis.get('ai_powered'):
        if analysis.get('key_catalyst'):
            msg += f"\n*Catalyst:* {analysis['key_catalyst']}\n"

        if analysis.get('summary'):
            msg += f"\n*Summary:*\n_{analysis['summary']}_\n"

        if analysis.get('trading_implication'):
            msg += f"\n*Trading:* {analysis['trading_implication']}\n"

        if analysis.get('risk_factors'):
            risks = ', '.join(analysis['risk_factors'][:2])
            msg += f"\n*Risks:* {risks}\n"
    else:
        # Keyword-based analysis
        if analysis.get('top_catalysts'):
            cats = ', '.join([f"{c[0]}({c[1]})" for c in analysis['top_catalysts']])
            msg += f"Catalysts: {cats}\n"

        msg += "\n*Recent Headlines:*\n"
        for h in analysis.get('headlines', [])[:4]:
            emoji = '📈' if h.get('sentiment') == 'BULLISH' else ('📉' if h.get('sentiment') == 'BEARISH' else '📄')
            title = h['title'][:60] + '...' if len(h['title']) > 60 else h['title']
            msg += f"{emoji} _{title}_\n"

    return msg


def scan_news_sentiment(tickers):
    """Scan multiple tickers for news sentiment."""
    results = []

    for ticker in tickers:
        analysis = analyze_ticker_news(ticker)
        results.append(analysis)

    # Sort by sentiment strength
    def sentiment_score(a):
        if a['overall_sentiment'] == 'STRONG_BULLISH':
            return 2
        elif a['overall_sentiment'] == 'BULLISH':
            return 1
        elif a['overall_sentiment'] == 'BEARISH':
            return -1
        elif a['overall_sentiment'] == 'STRONG_BEARISH':
            return -2
        return 0

    results.sort(key=sentiment_score, reverse=True)
    return results


def format_news_scan_results(results):
    """Format news scan results for Telegram."""
    ai_powered = any(r.get('ai_powered') for r in results)

    msg = "📰 *NEWS SENTIMENT SCAN*"
    if ai_powered:
        msg += " 🤖"
    msg += "\n\n"

    # Bullish
    bullish = [r for r in results if 'BULLISH' in r.get('overall_sentiment', '')]
    if bullish:
        msg += "*🟢 BULLISH NEWS:*\n"
        for r in bullish[:5]:
            msg += f"• `{r['ticker']}` - {r['overall_sentiment']}"
            if r.get('confidence'):
                msg += f" ({r['confidence']}%)"
            if r.get('key_catalyst'):
                msg += f"\n  _{r['key_catalyst']}_"
            elif r.get('top_catalysts'):
                cats = ', '.join([c[0] for c in r['top_catalysts'][:2]])
                if cats:
                    msg += f" ({cats})"
            msg += "\n"

    # Bearish
    bearish = [r for r in results if 'BEARISH' in r.get('overall_sentiment', '')]
    if bearish:
        msg += "\n*🔴 BEARISH NEWS:*\n"
        for r in bearish[:5]:
            msg += f"• `{r['ticker']}` - {r['overall_sentiment']}"
            if r.get('key_catalyst'):
                msg += f"\n  _{r['key_catalyst']}_"
            msg += "\n"

    # Neutral
    neutral = [r for r in results if r.get('overall_sentiment') == 'NEUTRAL']
    if neutral and len(bullish) + len(bearish) < 3:
        msg += "\n*🟡 NEUTRAL:*\n"
        for r in neutral[:3]:
            msg += f"• `{r['ticker']}`\n"

    if not bullish and not bearish and not neutral:
        msg += "_No significant news sentiment detected_"

    return msg


if __name__ == '__main__':
    # Test single ticker
    ticker = 'NVDA'
    print(f"Analyzing news for {ticker}...")
    analysis = analyze_ticker_news(ticker)
    print(format_news_analysis(ticker, analysis))

    print("\n" + "=" * 60)

    # Test scan
    test_tickers = ['NVDA', 'AMD', 'AAPL', 'TSLA', 'META']
    print("\nScanning news sentiment...")
    results = scan_news_sentiment(test_tickers)
    print(format_news_scan_results(results))
