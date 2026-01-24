#!/usr/bin/env python3
"""
AI News Analyzer

Fetches and analyzes news for stocks/sectors.
Uses keyword analysis + optional LLM integration.
"""

import requests
import re
from datetime import datetime, timedelta
from collections import Counter
import json
import warnings
warnings.filterwarnings('ignore')


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


def scrape_finviz_news(ticker):
    """Scrape news from Finviz."""
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        # Extract news headlines
        news_pattern = r'<a[^>]*href="([^"]*)"[^>]*class="tab-link-news"[^>]*>([^<]+)</a>'
        matches = re.findall(news_pattern, response.text)

        headlines = []
        for url, title in matches[:10]:
            headlines.append({
                'title': title.strip(),
                'url': url,
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


def analyze_ticker_news(ticker):
    """Full news analysis for a ticker."""
    headlines = scrape_finviz_news(ticker)

    if not headlines:
        return {
            'ticker': ticker,
            'headline_count': 0,
            'overall_sentiment': 'NO_DATA',
            'headlines': [],
        }

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

    msg = f"📰 *{ticker} NEWS ANALYSIS*\n\n"

    sentiment = analysis['overall_sentiment']
    msg += f"*Sentiment:* {sentiment_emoji.get(sentiment, '')} {sentiment}\n"
    msg += f"Headlines: {analysis['headline_count']}\n"

    if analysis.get('top_catalysts'):
        cats = ', '.join([f"{c[0]}({c[1]})" for c in analysis['top_catalysts']])
        msg += f"Catalysts: {cats}\n"

    msg += "\n*Recent Headlines:*\n"
    for h in analysis.get('headlines', [])[:4]:
        emoji = '📈' if h['sentiment'] == 'BULLISH' else ('📉' if h['sentiment'] == 'BEARISH' else '📄')
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
    msg = "📰 *NEWS SENTIMENT SCAN*\n\n"

    # Bullish
    bullish = [r for r in results if 'BULLISH' in r['overall_sentiment']]
    if bullish:
        msg += "*🟢 BULLISH NEWS:*\n"
        for r in bullish[:5]:
            cats = ', '.join([c[0] for c in r.get('top_catalysts', [])[:2]])
            msg += f"• `{r['ticker']}` - {r['overall_sentiment']}"
            if cats:
                msg += f" ({cats})"
            msg += "\n"

    # Bearish
    bearish = [r for r in results if 'BEARISH' in r['overall_sentiment']]
    if bearish:
        msg += "\n*🔴 BEARISH NEWS:*\n"
        for r in bearish[:5]:
            msg += f"• `{r['ticker']}` - {r['overall_sentiment']}\n"

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
