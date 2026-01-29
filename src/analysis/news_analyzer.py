#!/usr/bin/env python3
"""
AI News Analyzer - Multi-Source Edition

Fetches news from multiple sources and uses DeepSeek AI for analysis.

Priority order (high-accuracy first):
1. Finnhub (professional news feed, 60 req/min free)
2. Tiingo (curated news, 1000 req/day free)
3. Yahoo Finance (via yfinance) - fallback
4. Google News RSS - fallback

Provides comprehensive sentiment analysis and trading insights.
"""

import os
import requests
import re
import yfinance as yf
from datetime import datetime
from collections import Counter
import json
import xml.etree.ElementTree as ET
import warnings
warnings.filterwarnings('ignore')

from config import config
from utils import get_logger
from utils.data_providers import (
    FinnhubProvider,
    TiingoProvider,
    UnifiedDataFetcher,
    check_provider_status,
)

logger = get_logger(__name__)


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
            config.ai.api_url,
            headers={
                "Authorization": f"Bearer {config.ai.api_key}",
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
            logger.error(f"DeepSeek API error: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"DeepSeek analysis error: {e}")
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
            config.ai.api_url,
            headers={
                "Authorization": f"Bearer {config.ai.api_key}",
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
        logger.error(f"Sector analysis error: {e}")
        return None


# ============================================================
# NEWS SOURCE SCRAPERS
# ============================================================

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
                'source': 'Finviz',
            })

        return headlines
    except Exception as e:
        logger.error(f"Error scraping Finviz news for {ticker}: {e}")
        return []


def scrape_yahoo_news(ticker):
    """Get news from Yahoo Finance via yfinance."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news

        if not news:
            return []

        headlines = []
        for item in news[:10]:
            title = item.get('title', '')
            publisher = item.get('publisher', 'Yahoo')
            if title:
                headlines.append({
                    'title': title,
                    'url': item.get('link', ''),
                    'source': publisher,
                    'timestamp': item.get('providerPublishTime', 0),
                })

        return headlines
    except Exception as e:
        logger.error(f"Error scraping Yahoo news for {ticker}: {e}")
        return []


def scrape_google_news(ticker):
    """Get news from Google News RSS."""
    try:
        # Search for stock ticker news
        url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        # Parse RSS
        root = ET.fromstring(response.content)
        items = root.findall('.//item')

        headlines = []
        for item in items[:10]:
            title = item.find('title')
            source = item.find('source')
            if title is not None:
                headlines.append({
                    'title': title.text,
                    'url': '',
                    'source': source.text if source is not None else 'Google News',
                })

        return headlines
    except Exception as e:
        logger.error(f"Error scraping Google news for {ticker}: {e}")
        return []


def scrape_marketwatch_news(ticker):
    """Scrape news from MarketWatch."""
    try:
        url = f"https://www.marketwatch.com/investing/stock/{ticker.lower()}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        # Extract headlines
        pattern = r'class="article__headline"[^>]*>([^<]+)<'
        matches = re.findall(pattern, response.text)

        # Alternative pattern
        if not matches:
            pattern = r'<a[^>]*class="[^"]*link[^"]*"[^>]*>([^<]{20,100})</a>'
            matches = re.findall(pattern, response.text)

        headlines = []
        for title in matches[:8]:
            clean_title = title.strip()
            if len(clean_title) > 20 and ticker.upper() in clean_title.upper():
                headlines.append({
                    'title': clean_title,
                    'url': '',
                    'source': 'MarketWatch',
                })

        return headlines
    except Exception as e:
        logger.error(f"Error scraping MarketWatch news for {ticker}: {e}")
        return []


def scrape_stocktwits(ticker):
    """Get sentiment from StockTwits (X/Twitter-like for stocks)."""
    try:
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return [], None

        data = response.json()
        messages = data.get('messages', [])

        posts = []
        bullish_count = 0
        bearish_count = 0

        for msg in messages[:20]:
            body = msg.get('body', '')
            sentiment = msg.get('entities', {}).get('sentiment', {})
            sent_label = sentiment.get('basic', 'Neutral') if sentiment else 'Neutral'

            if sent_label == 'Bullish':
                bullish_count += 1
            elif sent_label == 'Bearish':
                bearish_count += 1

            posts.append({
                'text': body[:150],
                'sentiment': sent_label,
                'source': 'StockTwits',
            })

        # Calculate overall sentiment
        total = bullish_count + bearish_count
        if total > 0:
            bullish_pct = bullish_count / total * 100
            if bullish_pct >= 70:
                overall = 'STRONG_BULLISH'
            elif bullish_pct >= 55:
                overall = 'BULLISH'
            elif bullish_pct <= 30:
                overall = 'STRONG_BEARISH'
            elif bullish_pct <= 45:
                overall = 'BEARISH'
            else:
                overall = 'NEUTRAL'
        else:
            overall = 'NEUTRAL'

        social_stats = {
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'total_posts': len(messages),
            'bullish_pct': bullish_count / total * 100 if total > 0 else 50,
            'sentiment': overall,
        }

        return posts[:10], social_stats
    except Exception as e:
        logger.error(f"Error scraping StockTwits for {ticker}: {e}")
        return [], None


def scrape_reddit_sentiment(ticker):
    """Get sentiment from Reddit (wallstreetbets, stocks, investing)."""
    try:
        subreddits = ['wallstreetbets', 'stocks', 'investing']
        all_posts = []

        for sub in subreddits:
            url = f"https://www.reddit.com/r/{sub}/search.json?q={ticker}&sort=new&t=week&limit=10"
            headers = {'User-Agent': 'StockScanner/1.0'}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', {}).get('children', [])

                for post in posts[:5]:
                    post_data = post.get('data', {})
                    title = post_data.get('title', '')
                    score = post_data.get('score', 0)
                    if title and ticker.upper() in title.upper():
                        all_posts.append({
                            'text': title[:150],
                            'score': score,
                            'source': f'r/{sub}',
                        })

        return all_posts[:10]
    except Exception as e:
        logger.error(f"Error scraping Reddit sentiment for {ticker}: {e}")
        return []


def fetch_polygon_news(ticker):
    """
    Fetch news from Polygon.io (PRIMARY - high-accuracy, structured API).

    Benefits over web scraping:
    - Structured JSON data (no HTML parsing)
    - Reliable API (no broken scrapers)
    - Includes keywords, related tickers
    - Fast response times

    Returns standardized headline format.
    """
    polygon_key = os.environ.get('POLYGON_API_KEY', '')
    if not polygon_key:
        return []

    try:
        import asyncio
        from src.data.polygon_provider import PolygonProvider

        async def fetch():
            provider = PolygonProvider(api_key=polygon_key)
            try:
                news = await provider.get_news(ticker, limit=15)
                return news
            finally:
                await provider.close()

        # Run async function
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, fetch())
                    news = future.result(timeout=15)
            else:
                news = asyncio.run(fetch())
        except RuntimeError:
            news = asyncio.run(fetch())

        if not news:
            return []

        headlines = []
        for item in news:
            headlines.append({
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'source': item.get('source', 'Polygon'),
                'summary': item.get('summary', ''),
                'timestamp': item.get('published', ''),
                'provider': 'polygon',
                'tickers': item.get('tickers', []),
                'keywords': item.get('keywords', []),
            })

        logger.info(f"Polygon: fetched {len(headlines)} headlines for {ticker}")
        return headlines
    except Exception as e:
        logger.error(f"Polygon news error for {ticker}: {e}")
        return []


def fetch_finnhub_news(ticker):
    """
    Fetch news from Finnhub (high-accuracy, professional source).

    Free tier: 60 API calls/minute
    Returns standardized headline format.
    """
    if not FinnhubProvider.is_configured():
        return []

    try:
        news = FinnhubProvider.get_company_news(ticker, days_back=7)
        headlines = []

        for item in news[:15]:
            headlines.append({
                'title': item.get('headline', ''),
                'url': item.get('url', ''),
                'source': item.get('source', 'Finnhub'),
                'summary': item.get('summary', ''),
                'timestamp': item.get('datetime', 0),
                'provider': 'finnhub',
            })

        logger.info(f"Finnhub: fetched {len(headlines)} headlines for {ticker}")
        return headlines
    except Exception as e:
        logger.error(f"Finnhub news error for {ticker}: {e}")
        return []


def fetch_tiingo_news(ticker):
    """
    Fetch news from Tiingo (high-accuracy, curated source).

    Free tier: 1000 API calls/day
    Returns standardized headline format.
    """
    if not TiingoProvider.is_configured():
        return []

    try:
        news = TiingoProvider.get_news([ticker], limit=15)
        headlines = []

        for item in news:
            headlines.append({
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'source': item.get('source', 'Tiingo'),
                'summary': item.get('description', ''),
                'timestamp': item.get('publishedDate', ''),
                'provider': 'tiingo',
            })

        logger.info(f"Tiingo: fetched {len(headlines)} headlines for {ticker}")
        return headlines
    except Exception as e:
        logger.error(f"Tiingo news error for {ticker}: {e}")
        return []


def aggregate_news_sources(ticker):
    """
    Aggregate news from all sources with priority ordering.

    Priority (high-accuracy first):
    1. Polygon.io (PRIMARY - structured API, fast, reliable)
    2. Finnhub (professional feed)
    3. Tiingo (curated news)
    4. Yahoo Finance (fallback - API-based)

    Web scrapers (Finviz, Google News, MarketWatch) have been deprecated
    in favor of reliable API-based sources.

    Deduplicates and sorts by recency.
    """
    all_headlines = []

    # Check which premium providers are available
    provider_status = check_provider_status()
    polygon_available = bool(os.environ.get('POLYGON_API_KEY', ''))
    logger.debug(f"Provider status: {provider_status}, Polygon: {polygon_available}")

    # Priority 1: Polygon.io (PRIMARY - best reliability, structured data)
    if polygon_available:
        polygon_news = fetch_polygon_news(ticker)
        all_headlines.extend(polygon_news)
        if len(polygon_news) >= 5:
            logger.info(f"Polygon provided sufficient news for {ticker}")

    # Priority 2: Finnhub (professional accuracy)
    if provider_status.get('finnhub') and len(all_headlines) < 10:
        finnhub_news = fetch_finnhub_news(ticker)
        all_headlines.extend(finnhub_news)

    # Priority 3: Tiingo (curated news)
    if provider_status.get('tiingo') and len(all_headlines) < 10:
        tiingo_news = fetch_tiingo_news(ticker)
        all_headlines.extend(tiingo_news)

    # Priority 4: Yahoo Finance API (fallback - still API-based, not scraping)
    if len(all_headlines) < 5:
        logger.info(f"Using Yahoo fallback for {ticker} (API sources returned {len(all_headlines)} items)")
        try:
            yahoo_news = scrape_yahoo_news(ticker)
            for h in yahoo_news:
                if h.get('title'):
                    h['provider'] = 'yahoo_finance'
                    all_headlines.append(h)
        except Exception as e:
            logger.error(f"Error fetching from Yahoo Finance: {e}")

    # Deduplicate by similarity
    unique_headlines = []
    seen_titles = set()

    for h in all_headlines:
        title = h.get('title', '')
        if not title:
            continue

        title_lower = title.lower()
        # Simple dedup - check if key words match
        title_words = set(title_lower.split()[:5])

        is_dupe = False
        for seen in seen_titles:
            seen_words = set(seen.split()[:5])
            if len(title_words & seen_words) >= 3:
                is_dupe = True
                break

        if not is_dupe:
            seen_titles.add(title_lower)
            unique_headlines.append(h)

    # Sort by timestamp if available (most recent first)
    def get_timestamp(h):
        ts = h.get('timestamp', 0)
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
            except (ValueError, AttributeError):
                return 0
        return ts or 0

    unique_headlines.sort(key=get_timestamp, reverse=True)

    return unique_headlines[:15]  # Limit to 15 headlines


def aggregate_social_sentiment(ticker):
    """
    Aggregate social media sentiment from multiple sources.

    Priority:
    1. Finnhub sentiment (professional, aggregated)
    2. StockTwits (retail sentiment)
    3. Reddit (social discussion)
    """
    result = {
        'finnhub': None,
        'stocktwits': {'posts': [], 'stats': None},
        'reddit': {'posts': []},
    }

    # Priority 1: Finnhub sentiment (best accuracy)
    try:
        finnhub_sentiment = UnifiedDataFetcher.get_sentiment(ticker)
        if finnhub_sentiment:
            result['finnhub'] = {
                'bullish_pct': finnhub_sentiment.get('bullish', 0) * 100,
                'bearish_pct': finnhub_sentiment.get('bearish', 0) * 100,
                'buzz_score': finnhub_sentiment.get('buzz', 0),
                'source': finnhub_sentiment.get('source', 'finnhub'),
            }
            logger.info(f"Finnhub sentiment for {ticker}: {finnhub_sentiment}")
    except Exception as e:
        logger.error(f"Error fetching Finnhub sentiment for {ticker}: {e}")

    # StockTwits (retail sentiment)
    try:
        stocktwits_posts, stocktwits_stats = scrape_stocktwits(ticker)
        result['stocktwits'] = {
            'posts': stocktwits_posts,
            'stats': stocktwits_stats,
        }
    except Exception as e:
        logger.error(f"Error fetching StockTwits for {ticker}: {e}")

    # Reddit (only if needed for more context)
    try:
        reddit_posts = scrape_reddit_sentiment(ticker)
        result['reddit'] = {'posts': reddit_posts}
    except Exception as e:
        logger.error(f"Error fetching Reddit for {ticker}: {e}")

    # Combine into overall sentiment score
    overall_bullish = 50.0  # Default neutral

    if result['finnhub']:
        # Finnhub is most reliable
        overall_bullish = result['finnhub'].get('bullish_pct', 50)
    elif result['stocktwits']['stats']:
        overall_bullish = result['stocktwits']['stats'].get('bullish_pct', 50)

    result['overall'] = {
        'bullish_pct': overall_bullish,
        'sentiment': 'BULLISH' if overall_bullish > 55 else 'BEARISH' if overall_bullish < 45 else 'NEUTRAL',
    }

    return result


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


def analyze_with_deepseek_comprehensive(ticker, headlines, social_data):
    """
    Comprehensive AI analysis of news AND social sentiment.
    """
    if not headlines and not social_data:
        return None

    # Build news section
    news_text = ""
    if headlines:
        news_text = "NEWS HEADLINES:\n"
        for h in headlines[:12]:
            source = h.get('source', 'Unknown')
            news_text += f"- [{source}] {h['title']}\n"

    # Build social section
    social_text = ""
    stocktwits = social_data.get('stocktwits', {})
    reddit = social_data.get('reddit', {})

    if stocktwits.get('stats'):
        stats = stocktwits['stats']
        social_text += f"\nSTOCKTWITS SENTIMENT:\n"
        social_text += f"- Bullish: {stats['bullish_count']}, Bearish: {stats['bearish_count']}\n"
        social_text += f"- Bullish %: {stats['bullish_pct']:.0f}%\n"

        if stocktwits.get('posts'):
            social_text += "Top posts:\n"
            for p in stocktwits['posts'][:5]:
                social_text += f"- [{p['sentiment']}] {p['text'][:100]}\n"

    if reddit.get('posts'):
        social_text += f"\nREDDIT MENTIONS:\n"
        for p in reddit['posts'][:5]:
            social_text += f"- [r/{p['source'].split('/')[-1]}] {p['text'][:100]}\n"

    prompt = f"""Analyze ALL the following data for {ticker} stock and provide comprehensive trading insights.

{news_text}
{social_text}

Respond in this exact JSON format:
{{
    "news_sentiment": "STRONG_BULLISH/BULLISH/NEUTRAL/BEARISH/STRONG_BEARISH",
    "social_sentiment": "STRONG_BULLISH/BULLISH/NEUTRAL/BEARISH/STRONG_BEARISH",
    "overall_sentiment": "STRONG_BULLISH/BULLISH/NEUTRAL/BEARISH/STRONG_BEARISH",
    "confidence": 1-100,
    "key_catalyst": "main driver from news",
    "social_buzz": "what retail traders are saying/feeling",
    "summary": "2-3 sentence comprehensive summary combining news and social",
    "trading_signal": "BUY/HOLD/SELL with brief reason",
    "risk_factors": ["risk 1", "risk 2"],
    "contrarian_view": "if social and news disagree, explain"
}}

Be concise. Focus on actionable insights. Note any divergence between news sentiment and social sentiment."""

    try:
        response = requests.post(
            config.ai.api_url,
            headers={
                "Authorization": f"Bearer {config.ai.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are an expert stock analyst who combines traditional news analysis with social sentiment from retail traders. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 600
            },
            timeout=45
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        else:
            logger.error(f"DeepSeek API error: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"DeepSeek comprehensive analysis error: {e}")
        return None


def analyze_ticker_news(ticker, use_ai=True):
    """Full news + social analysis for a ticker using AI."""
    # Get news from multiple sources
    headlines = aggregate_news_sources(ticker)

    # Get social sentiment
    social_data = aggregate_social_sentiment(ticker)

    # Check if we have any data
    has_news = len(headlines) > 0
    has_social = (
        social_data.get('stocktwits', {}).get('stats') or
        social_data.get('reddit', {}).get('posts')
    )

    if not has_news and not has_social:
        return {
            'ticker': ticker,
            'headline_count': 0,
            'overall_sentiment': 'NO_DATA',
            'headlines': [],
        }

    # Try comprehensive AI analysis
    ai_analysis = None
    if use_ai and config.ai.api_key:
        ai_analysis = analyze_with_deepseek_comprehensive(ticker, headlines, social_data)

    if ai_analysis:
        # Count sources
        sources = set(h.get('source', 'Unknown') for h in headlines)

        return {
            'ticker': ticker,
            'headline_count': len(headlines),
            'sources': list(sources),
            'overall_sentiment': ai_analysis.get('overall_sentiment', 'NEUTRAL'),
            'news_sentiment': ai_analysis.get('news_sentiment', 'NEUTRAL'),
            'social_sentiment': ai_analysis.get('social_sentiment', 'NEUTRAL'),
            'confidence': ai_analysis.get('confidence', 0),
            'key_catalyst': ai_analysis.get('key_catalyst', ''),
            'social_buzz': ai_analysis.get('social_buzz', ''),
            'summary': ai_analysis.get('summary', ''),
            'trading_signal': ai_analysis.get('trading_signal', ''),
            'risk_factors': ai_analysis.get('risk_factors', []),
            'contrarian_view': ai_analysis.get('contrarian_view', ''),
            'headlines': [{'title': h['title'], 'source': h.get('source', '')} for h in headlines[:5]],
            'stocktwits_stats': social_data.get('stocktwits', {}).get('stats'),
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
            'source': h.get('source', ''),
            'sentiment': analysis['sentiment'],
            'catalysts': analysis['catalysts'],
        })

    # Add StockTwits sentiment
    stocktwits_stats = social_data.get('stocktwits', {}).get('stats')
    if stocktwits_stats:
        # Weight social sentiment
        if stocktwits_stats['bullish_pct'] > 60:
            total_bullish += 3
        elif stocktwits_stats['bullish_pct'] < 40:
            total_bearish += 3

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
        'sources': list(set(h.get('source', '') for h in headlines)),
        'overall_sentiment': overall,
        'bullish_score': total_bullish,
        'bearish_score': total_bearish,
        'top_catalysts': catalyst_counts.most_common(3),
        'headlines': analyzed_headlines[:5],
        'stocktwits_stats': stocktwits_stats,
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

    msg = f"📰 *{ticker} SENTIMENT ANALYSIS*"
    if analysis.get('ai_powered'):
        msg += " 🤖\n\n"
    else:
        msg += "\n\n"

    # Overall sentiment
    sentiment = analysis['overall_sentiment']
    msg += f"*Overall:* {sentiment_emoji.get(sentiment, '')} {sentiment}"
    if analysis.get('confidence'):
        msg += f" ({analysis['confidence']}% confidence)"
    msg += "\n"

    # News vs Social sentiment (if available)
    if analysis.get('news_sentiment') and analysis.get('social_sentiment'):
        news_sent = analysis['news_sentiment']
        social_sent = analysis['social_sentiment']
        msg += f"• News: {sentiment_emoji.get(news_sent, '')} {news_sent}\n"
        msg += f"• Social: {sentiment_emoji.get(social_sent, '')} {social_sent}\n"

    # Sources info
    sources = analysis.get('sources', [])
    msg += f"\n📊 *Sources:* {len(sources)} ({', '.join(sources[:3])})\n"
    msg += f"Headlines analyzed: {analysis['headline_count']}\n"

    # StockTwits stats
    st_stats = analysis.get('stocktwits_stats')
    if st_stats:
        msg += f"\n🐦 *StockTwits:* {st_stats['bullish_pct']:.0f}% bullish "
        msg += f"({st_stats['bullish_count']}🟢 / {st_stats['bearish_count']}🔴)\n"

    # AI-powered insights
    if analysis.get('ai_powered'):
        if analysis.get('key_catalyst'):
            msg += f"\n*📌 Catalyst:* {analysis['key_catalyst']}\n"

        if analysis.get('social_buzz'):
            msg += f"\n*💬 Social Buzz:* {analysis['social_buzz']}\n"

        if analysis.get('summary'):
            msg += f"\n*📝 Summary:*\n_{analysis['summary']}_\n"

        if analysis.get('trading_signal'):
            msg += f"\n*🎯 Signal:* {analysis['trading_signal']}\n"

        if analysis.get('contrarian_view'):
            msg += f"\n*⚠️ Contrarian:* {analysis['contrarian_view']}\n"

        if analysis.get('risk_factors'):
            risks = ', '.join(analysis['risk_factors'][:2])
            msg += f"\n*Risks:* {risks}\n"
    else:
        # Keyword-based analysis
        if analysis.get('top_catalysts'):
            cats = ', '.join([f"{c[0]}({c[1]})" for c in analysis['top_catalysts']])
            msg += f"\nCatalysts: {cats}\n"

        msg += "\n*Recent Headlines:*\n"
        for h in analysis.get('headlines', [])[:4]:
            emoji = '📈' if h.get('sentiment') == 'BULLISH' else ('📉' if h.get('sentiment') == 'BEARISH' else '📄')
            title = h['title'][:55] + '...' if len(h['title']) > 55 else h['title']
            source = h.get('source', '')[:10]
            msg += f"{emoji} `{source}` _{title}_\n"

    return msg


def scan_news_sentiment(tickers):
    """Scan multiple tickers for news sentiment."""
    results = []

    for ticker in tickers:
        try:
            analysis = analyze_ticker_news(ticker)
            results.append(analysis)
        except Exception as e:
            results.append({'ticker': ticker, 'overall_sentiment': 'ERROR', 'headline_count': 0})

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

    # Auto-learn from news events
    try:
        from self_learning import record_news_event
        import yfinance as yf

        for result in results:
            ticker = result.get('ticker')
            sentiment = result.get('overall_sentiment', 'NEUTRAL')
            headlines = result.get('key_headlines', [])

            if ticker and headlines:
                # Get current price
                try:
                    stock = yf.Ticker(ticker)
                    price = stock.fast_info.get('lastPrice', 0)
                except Exception as e:
                    logger.debug(f"Failed to get price for {ticker}: {e}")
                    price = 0

                # Determine news type from headlines
                news_type = 'general'
                for h in headlines[:3]:
                    title = h.get('title', '').lower()
                    if any(w in title for w in ['earnings', 'revenue', 'profit', 'eps']):
                        news_type = 'earnings'
                        break
                    elif any(w in title for w in ['merger', 'acquisition', 'deal', 'buyout']):
                        news_type = 'merger'
                        break
                    elif any(w in title for w in ['launch', 'product', 'release', 'announce']):
                        news_type = 'product_launch'
                        break
                    elif any(w in title for w in ['upgrade', 'downgrade', 'analyst', 'rating']):
                        news_type = 'analyst'
                        break

                # Record the first significant headline
                if headlines:
                    record_news_event(
                        ticker=ticker,
                        news_type=news_type,
                        headline=headlines[0].get('title', '')[:100],
                        price_at_news=price,
                        sentiment=sentiment.lower().replace('strong_', '')
                    )
    except Exception as e:
        logger.debug(f"Learning from news events failed: {e}")

    return results


def format_news_scan_results(results):
    """Format news scan results for Telegram."""
    ai_powered = any(r.get('ai_powered') for r in results)

    msg = "📰 *NEWS + SOCIAL SENTIMENT*"
    if ai_powered:
        msg += " 🤖"
    msg += "\n\n"

    # Bullish
    bullish = [r for r in results if 'BULLISH' in r.get('overall_sentiment', '')]
    if bullish:
        msg += "*🟢 BULLISH:*\n"
        for r in bullish[:5]:
            msg += f"• `{r['ticker']}` {r['overall_sentiment']}"
            if r.get('confidence'):
                msg += f" ({r['confidence']}%)"

            # Show news vs social
            if r.get('news_sentiment') and r.get('social_sentiment'):
                if r['news_sentiment'] != r['social_sentiment']:
                    msg += f"\n  📰{r['news_sentiment'][:4]} vs 💬{r['social_sentiment'][:4]}"

            # Show StockTwits stats
            st = r.get('stocktwits_stats')
            if st:
                msg += f" | ST: {st['bullish_pct']:.0f}%🟢"

            if r.get('key_catalyst'):
                msg += f"\n  _{r['key_catalyst'][:60]}_"
            elif r.get('trading_signal'):
                msg += f"\n  _{r['trading_signal'][:60]}_"
            msg += "\n"

    # Bearish
    bearish = [r for r in results if 'BEARISH' in r.get('overall_sentiment', '')]
    if bearish:
        msg += "\n*🔴 BEARISH:*\n"
        for r in bearish[:5]:
            msg += f"• `{r['ticker']}` {r['overall_sentiment']}"

            st = r.get('stocktwits_stats')
            if st:
                msg += f" | ST: {st['bullish_pct']:.0f}%🟢"

            if r.get('key_catalyst'):
                msg += f"\n  _{r['key_catalyst'][:60]}_"
            msg += "\n"

    # Divergence alert (news vs social disagree)
    divergent = [r for r in results if r.get('contrarian_view')]
    if divergent:
        msg += "\n*⚠️ DIVERGENCE ALERT:*\n"
        for r in divergent[:2]:
            msg += f"• `{r['ticker']}`: _{r['contrarian_view'][:70]}_\n"

    # Neutral
    neutral = [r for r in results if r.get('overall_sentiment') == 'NEUTRAL']
    if neutral and len(bullish) + len(bearish) < 3:
        msg += "\n*🟡 NEUTRAL:*\n"
        for r in neutral[:3]:
            msg += f"• `{r['ticker']}`"
            st = r.get('stocktwits_stats')
            if st:
                msg += f" (ST: {st['bullish_pct']:.0f}%)"
            msg += "\n"

    if not bullish and not bearish and not neutral:
        msg += "_No significant sentiment detected_"

    # Source summary
    all_sources = set()
    for r in results:
        all_sources.update(r.get('sources', []))
    if all_sources:
        msg += f"\n_Sources: {', '.join(list(all_sources)[:4])}_"

    return msg


if __name__ == '__main__':
    # Test single ticker
    ticker = 'NVDA'
    logger.info(f"Analyzing news for {ticker}...")
    analysis = analyze_ticker_news(ticker)
    logger.info(format_news_analysis(ticker, analysis))

    logger.info("\n" + "=" * 60)

    # Test scan
    test_tickers = ['NVDA', 'AMD', 'AAPL', 'TSLA', 'META']
    logger.info("Scanning news sentiment...")
    results = scan_news_sentiment(test_tickers)
    logger.info(format_news_scan_results(results))
