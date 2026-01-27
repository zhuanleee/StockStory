"""
Sentiment Analysis Module

DeepSeek-powered sentiment analysis for stock news.
"""

from src.sentiment.deepseek_sentiment import (
    analyze_sentiment,
    analyze_batch,
    get_sentiment_signal,
    calculate_sentiment_score,
    fetch_news_free,
)

__all__ = [
    'analyze_sentiment',
    'analyze_batch',
    'get_sentiment_signal',
    'calculate_sentiment_score',
    'fetch_news_free',
]
