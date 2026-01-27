"""
DeepSeek Sentiment Analyzer
===========================
Uses DeepSeek API for financial news sentiment analysis.
Lightweight alternative to FinBERT - no heavy ML dependencies.

Usage:
    from src.sentiment.deepseek_sentiment import analyze_sentiment, get_sentiment_signal

    # Single headline
    result = analyze_sentiment("NVIDIA beats earnings expectations")

    # Full ticker analysis
    signal = get_sentiment_signal("NVDA")
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


def _call_deepseek(prompt: str, system_prompt: str = None) -> Optional[str]:
    """Make API call to DeepSeek."""
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY not set")
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
                "temperature": 0.1,  # Low temp for consistent scoring
                "max_tokens": 500
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            logger.error(f"DeepSeek API error: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"DeepSeek request error: {e}")
        return None


def analyze_sentiment(text: str) -> Dict:
    """
    Analyze sentiment of a single text using DeepSeek.

    Returns:
        dict with 'score' (-1 to +1), 'label', 'confidence'
    """
    if not text:
        return {"score": 0.0, "label": "neutral", "confidence": 0.0}

    system_prompt = """You are a financial sentiment analyzer. Analyze the sentiment of stock news headlines.
Respond with ONLY a JSON object in this exact format:
{"score": <float from -1.0 to 1.0>, "label": "<positive/negative/neutral>", "confidence": <float from 0 to 1>}

Scoring guide:
- Strong positive (earnings beat, upgrade, acquisition): 0.7 to 1.0
- Mild positive (expansion, partnership): 0.3 to 0.6
- Neutral (routine news, no clear direction): -0.2 to 0.2
- Mild negative (miss expectations, downgrade): -0.6 to -0.3
- Strong negative (layoffs, fraud, bankruptcy): -1.0 to -0.7"""

    prompt = f"Analyze sentiment: {text[:500]}"

    response = _call_deepseek(prompt, system_prompt)

    if not response:
        return {"score": 0.0, "label": "neutral", "confidence": 0.0, "error": "API call failed"}

    try:
        # Extract JSON from response
        if '{' in response:
            json_str = response[response.find('{'):response.rfind('}')+1]
            result = json.loads(json_str)
            return {
                "score": float(result.get("score", 0)),
                "label": result.get("label", "neutral"),
                "confidence": float(result.get("confidence", 0.5))
            }
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse DeepSeek response: {e}")

    return {"score": 0.0, "label": "neutral", "confidence": 0.0}


def analyze_batch(headlines: List[str]) -> List[Dict]:
    """
    Analyze multiple headlines in a single API call (more efficient).

    Returns list of sentiment results.
    """
    if not headlines:
        return []

    # Limit to 15 headlines to keep response manageable
    headlines = headlines[:15]

    system_prompt = """You are a financial sentiment analyzer. Analyze sentiment of each headline.
Respond with ONLY a JSON array. Each item must have: score (-1 to 1), label (positive/negative/neutral).
Example: [{"score": 0.7, "label": "positive"}, {"score": -0.3, "label": "negative"}]"""

    # Number headlines for clarity
    numbered = "\n".join([f"{i+1}. {h[:200]}" for i, h in enumerate(headlines)])
    prompt = f"Analyze sentiment for each headline:\n{numbered}"

    response = _call_deepseek(prompt, system_prompt)

    if not response:
        return [{"score": 0.0, "label": "neutral"} for _ in headlines]

    try:
        # Extract JSON array from response
        if '[' in response:
            json_str = response[response.find('['):response.rfind(']')+1]
            results = json.loads(json_str)

            # Ensure we have results for all headlines
            while len(results) < len(headlines):
                results.append({"score": 0.0, "label": "neutral"})

            return results[:len(headlines)]
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse batch response: {e}")

    return [{"score": 0.0, "label": "neutral"} for _ in headlines]


def fetch_news_free(ticker: str, limit: int = 15) -> List[Dict]:
    """
    Fetch news using free sources (Finnhub, Google News RSS).
    No yfinance or paid APIs required.
    """
    headlines = []

    # Try Finnhub first (free tier: 60 req/min)
    finnhub_key = os.environ.get('FINNHUB_API_KEY', '')
    if finnhub_key:
        try:
            from datetime import timedelta
            end = datetime.now()
            start = end - timedelta(days=7)

            url = "https://finnhub.io/api/v1/company-news"
            params = {
                'symbol': ticker.upper(),
                'from': start.strftime('%Y-%m-%d'),
                'to': end.strftime('%Y-%m-%d'),
                'token': finnhub_key
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                news = response.json()
                for item in news[:limit]:
                    headlines.append({
                        'title': item.get('headline', ''),
                        'summary': item.get('summary', ''),
                        'source': item.get('source', 'Finnhub'),
                        'url': item.get('url', ''),
                        'timestamp': item.get('datetime', 0),
                        'provider': 'finnhub'
                    })
                logger.info(f"Finnhub: {len(headlines)} headlines for {ticker}")
        except Exception as e:
            logger.error(f"Finnhub error: {e}")

    # Fallback to Google News RSS (always free)
    if len(headlines) < 5:
        try:
            import xml.etree.ElementTree as ET

            url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; StockScanner/1.0)'
            })

            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for item in root.findall('.//item')[:limit - len(headlines)]:
                    title = item.find('title')
                    pub_date = item.find('pubDate')
                    source = item.find('source')

                    if title is not None and title.text:
                        headlines.append({
                            'title': title.text,
                            'summary': '',
                            'source': source.text if source is not None else 'Google News',
                            'url': item.find('link').text if item.find('link') is not None else '',
                            'timestamp': pub_date.text if pub_date is not None else '',
                            'provider': 'google_news'
                        })

                logger.info(f"Google News: added {limit - len(headlines)} headlines for {ticker}")
        except Exception as e:
            logger.error(f"Google News error: {e}")

    return headlines


def get_sentiment_signal(ticker: str, num_articles: int = 15) -> Dict:
    """
    Get aggregated sentiment signal for a ticker.

    Args:
        ticker: Stock symbol
        num_articles: Number of articles to analyze

    Returns:
        dict with:
            - signal: float from -1 (bearish) to +1 (bullish)
            - bias: 'bullish', 'bearish', or 'neutral'
            - strength: 'strong', 'moderate', or 'weak'
            - article_count: number of articles analyzed
            - headlines: list of (title, sentiment) tuples
    """
    # Fetch news from free sources
    news = fetch_news_free(ticker, limit=num_articles)

    if not news:
        return {
            "ticker": ticker,
            "signal": 0.0,
            "bias": "no_data",
            "strength": "none",
            "article_count": 0,
            "error": "No news found"
        }

    # Extract headlines
    headlines = [n.get('title', '') for n in news if n.get('title')]

    if not headlines:
        return {
            "ticker": ticker,
            "signal": 0.0,
            "bias": "no_data",
            "strength": "none",
            "article_count": 0
        }

    # Analyze sentiment with DeepSeek
    sentiments = analyze_batch(headlines)

    # Calculate aggregate metrics
    scores = [s.get('score', 0) for s in sentiments]
    mean_signal = sum(scores) / len(scores) if scores else 0

    positive_count = sum(1 for s in scores if s > 0.1)
    negative_count = sum(1 for s in scores if s < -0.1)

    # Determine bias and strength
    if mean_signal > 0.15:
        bias = "bullish"
    elif mean_signal < -0.15:
        bias = "bearish"
    else:
        bias = "neutral"

    if abs(mean_signal) > 0.4:
        strength = "strong"
    elif abs(mean_signal) > 0.2:
        strength = "moderate"
    else:
        strength = "weak"

    # Build headline results
    headline_results = []
    for headline, sentiment in zip(headlines, sentiments):
        headline_results.append({
            'title': headline[:100],
            'score': sentiment.get('score', 0),
            'label': sentiment.get('label', 'neutral')
        })

    return {
        "ticker": ticker,
        "timestamp": datetime.now().isoformat(),
        "signal": round(mean_signal, 4),
        "bias": bias,
        "strength": strength,
        "article_count": len(headlines),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "positive_ratio": round(positive_count / len(headlines), 3) if headlines else 0,
        "headlines": headline_results
    }


def calculate_sentiment_score(ticker: str, news_data: List[Dict] = None) -> Dict:
    """
    Calculate sentiment score for story scoring integration.

    Compatible with existing story_scorer.calculate_sentiment_score() interface.

    Returns:
        dict with 'score' (0-100), 'label', 'positive_ratio', etc.
    """
    # Use provided news or fetch fresh
    if news_data:
        headlines = [n.get('title', '') for n in news_data if n.get('title')]
    else:
        news = fetch_news_free(ticker, limit=15)
        headlines = [n.get('title', '') for n in news if n.get('title')]

    if not headlines:
        return {
            "score": 50,  # Neutral default
            "label": "neutral",
            "positive_ratio": 0.5,
            "article_count": 0,
            "confidence": 0.0
        }

    # Analyze with DeepSeek
    sentiments = analyze_batch(headlines)

    # Calculate metrics
    scores = [s.get('score', 0) for s in sentiments]
    mean_score = sum(scores) / len(scores) if scores else 0

    positive_count = sum(1 for s in scores if s > 0.1)
    positive_ratio = positive_count / len(scores) if scores else 0.5

    # Convert -1 to +1 scale to 0-100 scale
    normalized_score = (mean_score + 1) * 50  # Maps -1->0, 0->50, +1->100

    # Determine label
    if mean_score > 0.15:
        label = "positive"
    elif mean_score < -0.15:
        label = "negative"
    else:
        label = "neutral"

    return {
        "score": round(normalized_score, 1),
        "raw_score": round(mean_score, 4),
        "label": label,
        "positive_ratio": round(positive_ratio, 3),
        "article_count": len(headlines),
        "confidence": 0.7 if len(headlines) >= 5 else 0.4
    }


# Demo function
if __name__ == "__main__":
    print("DeepSeek Sentiment Analyzer")
    print("=" * 50)

    # Test single analysis
    print("\nSingle headline analysis:")
    result = analyze_sentiment("NVIDIA reports record quarterly revenue, beats expectations")
    print(f"  Score: {result['score']:+.2f}")
    print(f"  Label: {result['label']}")

    # Test full signal
    print("\n" + "=" * 50)
    print("Full sentiment signal for NVDA:")
    signal = get_sentiment_signal("NVDA")
    print(f"  Signal: {signal['signal']:+.4f}")
    print(f"  Bias: {signal['bias']} ({signal['strength']})")
    print(f"  Articles: {signal['article_count']}")
    print(f"  Positive ratio: {signal.get('positive_ratio', 0):.1%}")

    if signal.get('headlines'):
        print("\n  Headlines:")
        for h in signal['headlines'][:5]:
            emoji = "🟢" if h['label'] == 'positive' else "🔴" if h['label'] == 'negative' else "⚪"
            print(f"    {emoji} [{h['score']:+.2f}] {h['title'][:60]}...")
