"""
Google Trends Integration
=========================
Detect emerging themes via search volume trends.

Google Trends shows what people are searching for - often a leading
indicator of market themes before they hit mainstream news.

Usage:
    from src.data.google_trends import (
        get_trend_score,
        detect_trending_themes,
        get_breakout_searches,
    )

    # Check if "nuclear energy" is trending
    score = get_trend_score("nuclear energy stocks")

    # Detect which themes are gaining momentum
    themes = detect_trending_themes()

    # Find breakout searches
    breakouts = get_breakout_searches()

Note: Uses pytrends library (unofficial Google Trends API)
      pip install pytrends
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

# Try to import pytrends
try:
    from pytrends.request import TrendReq
    HAS_PYTRENDS = True
except ImportError:
    HAS_PYTRENDS = False
    logger.warning("pytrends not installed. Run: pip install pytrends")


# Theme keywords to monitor
THEME_KEYWORDS = {
    'ai_chips': ['AI chips', 'nvidia stock', 'AI semiconductor'],
    'nuclear': ['nuclear energy stocks', 'uranium stocks', 'nuclear power'],
    'ev': ['electric vehicle stocks', 'EV stocks', 'tesla stock'],
    'bitcoin': ['bitcoin etf', 'crypto stocks', 'bitcoin stock'],
    'weight_loss': ['weight loss drug stocks', 'GLP-1 stocks', 'ozempic stock'],
    'defense': ['defense stocks', 'military stocks', 'aerospace stocks'],
    'cybersecurity': ['cybersecurity stocks', 'cyber security etf'],
    'cloud': ['cloud computing stocks', 'cloud stock'],
    'solar': ['solar stocks', 'solar energy stocks', 'renewable energy'],
    'quantum': ['quantum computing stocks', 'quantum stock'],
    'space': ['space stocks', 'space exploration stocks'],
    'robotics': ['robotics stocks', 'automation stocks', 'robot stock'],
    'biotech': ['biotech stocks', 'pharmaceutical stocks'],
    'fintech': ['fintech stocks', 'payment stocks'],
    'metaverse': ['metaverse stocks', 'virtual reality stocks'],
    'infrastructure': ['infrastructure stocks', 'construction stocks'],
    'china': ['china stocks', 'chinese stocks', 'baba stock'],
    'gold': ['gold stocks', 'gold miners', 'precious metals'],
    'oil': ['oil stocks', 'energy stocks', 'oil price'],
    'retail': ['retail stocks', 'consumer stocks'],
}

# Cache for rate limiting
_trends_cache = {}
_cache_expiry = {}
CACHE_TTL = 3600  # 1 hour cache


class GoogleTrendsClient:
    """
    Google Trends client for market theme detection.

    Rate limits: Google may block if too many requests.
    Recommendation: Cache results, limit to 10-20 queries per session.
    """

    def __init__(self):
        if not HAS_PYTRENDS:
            raise ImportError("pytrends not installed. Run: pip install pytrends")

        self.pytrends = TrendReq(
            hl='en-US',
            tz=360,
            timeout=(10, 25),
            retries=2,
            backoff_factor=0.5
        )

    def get_interest_over_time(
        self,
        keywords: List[str],
        timeframe: str = 'today 3-m'
    ) -> Optional[Dict]:
        """
        Get search interest over time for keywords.

        Args:
            keywords: List of search terms (max 5)
            timeframe: 'today 3-m', 'today 12-m', 'now 7-d', etc.

        Returns:
            Dict with trend data and scores
        """
        try:
            # Limit to 5 keywords (Google limit)
            keywords = keywords[:5]

            self.pytrends.build_payload(
                kw_list=keywords,
                timeframe=timeframe,
                geo='US'
            )

            df = self.pytrends.interest_over_time()

            if df.empty:
                return None

            # Calculate trend metrics
            results = {}
            for keyword in keywords:
                if keyword not in df.columns:
                    continue

                series = df[keyword]
                current = float(series.iloc[-1])
                avg_30d = float(series.tail(30).mean()) if len(series) >= 30 else float(series.mean())
                avg_7d = float(series.tail(7).mean()) if len(series) >= 7 else current
                max_val = float(series.max())
                min_val = float(series.min())

                # Trend direction
                if len(series) >= 14:
                    recent = float(series.tail(7).mean())
                    prior = float(series.tail(14).head(7).mean())
                    trend_pct = ((recent - prior) / prior * 100) if prior > 0 else 0
                else:
                    trend_pct = 0

                # Momentum score (0-100)
                momentum = min(100, max(0, (current / avg_30d - 0.5) * 100)) if avg_30d > 0 else 50

                # Breakout detection
                is_breakout = current > avg_30d * 1.5 and trend_pct > 20

                results[keyword] = {
                    'current': current,
                    'avg_7d': round(avg_7d, 1),
                    'avg_30d': round(avg_30d, 1),
                    'max': max_val,
                    'min': min_val,
                    'trend_pct': round(trend_pct, 1),
                    'momentum': round(momentum, 1),
                    'is_breakout': is_breakout,
                    'status': 'breakout' if is_breakout else 'rising' if trend_pct > 10 else 'stable' if trend_pct > -10 else 'declining'
                }

            return results

        except Exception as e:
            logger.error(f"Google Trends error: {e}")
            return None

    def get_related_queries(self, keyword: str) -> Dict:
        """
        Get related/rising queries for a keyword.
        Useful for discovering emerging sub-themes.
        """
        try:
            self.pytrends.build_payload(
                kw_list=[keyword],
                timeframe='today 3-m',
                geo='US'
            )

            related = self.pytrends.related_queries()

            if keyword not in related:
                return {'top': [], 'rising': []}

            top_df = related[keyword].get('top')
            rising_df = related[keyword].get('rising')

            top = []
            if top_df is not None and not top_df.empty:
                top = top_df.head(10).to_dict('records')

            rising = []
            if rising_df is not None and not rising_df.empty:
                rising = rising_df.head(10).to_dict('records')

            return {
                'top': top,
                'rising': rising
            }

        except Exception as e:
            logger.error(f"Related queries error: {e}")
            return {'top': [], 'rising': []}

    def get_trending_searches(self, geo: str = 'united_states') -> List[str]:
        """Get today's trending searches."""
        try:
            df = self.pytrends.trending_searches(pn=geo)
            return df[0].tolist()[:20] if not df.empty else []
        except Exception as e:
            logger.error(f"Trending searches error: {e}")
            return []


def get_trend_score(keyword: str, use_cache: bool = True) -> Dict:
    """
    Get trend score for a single keyword.

    Returns:
        Dict with score (0-100), trend direction, and status
    """
    cache_key = f"trend_{keyword}"

    # Check cache
    if use_cache and cache_key in _trends_cache:
        if datetime.now().timestamp() < _cache_expiry.get(cache_key, 0):
            return _trends_cache[cache_key]

    if not HAS_PYTRENDS:
        return {'score': 50, 'status': 'unknown', 'error': 'pytrends not installed'}

    try:
        client = GoogleTrendsClient()
        result = client.get_interest_over_time([keyword])

        if result and keyword in result:
            data = result[keyword]
            response = {
                'keyword': keyword,
                'score': data['momentum'],
                'current': data['current'],
                'avg_30d': data['avg_30d'],
                'trend_pct': data['trend_pct'],
                'status': data['status'],
                'is_breakout': data['is_breakout'],
                'timestamp': datetime.now().isoformat()
            }

            # Cache result
            _trends_cache[cache_key] = response
            _cache_expiry[cache_key] = datetime.now().timestamp() + CACHE_TTL

            return response

        return {'keyword': keyword, 'score': 50, 'status': 'no_data'}

    except Exception as e:
        logger.error(f"Trend score error for {keyword}: {e}")
        return {'keyword': keyword, 'score': 50, 'status': 'error', 'error': str(e)}


def detect_trending_themes(themes: Dict[str, List[str]] = None) -> List[Dict]:
    """
    Detect which investment themes are trending.

    Returns list of themes sorted by momentum score.
    """
    if not HAS_PYTRENDS:
        return []

    if themes is None:
        themes = THEME_KEYWORDS

    results = []
    client = GoogleTrendsClient()

    for theme_id, keywords in themes.items():
        try:
            # Use first keyword as primary
            primary_keyword = keywords[0]

            # Check cache first
            cache_key = f"theme_{theme_id}"
            if cache_key in _trends_cache:
                if datetime.now().timestamp() < _cache_expiry.get(cache_key, 0):
                    results.append(_trends_cache[cache_key])
                    continue

            # Fetch trend data
            data = client.get_interest_over_time([primary_keyword])

            if data and primary_keyword in data:
                trend = data[primary_keyword]

                result = {
                    'theme_id': theme_id,
                    'keyword': primary_keyword,
                    'score': trend['momentum'],
                    'trend_pct': trend['trend_pct'],
                    'status': trend['status'],
                    'is_breakout': trend['is_breakout'],
                    'current': trend['current'],
                    'avg_30d': trend['avg_30d']
                }

                results.append(result)

                # Cache
                _trends_cache[cache_key] = result
                _cache_expiry[cache_key] = datetime.now().timestamp() + CACHE_TTL

            # Rate limiting - be nice to Google
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error checking theme {theme_id}: {e}")
            continue

    # Sort by momentum score
    results.sort(key=lambda x: x.get('score', 0), reverse=True)

    return results


def get_breakout_searches() -> List[Dict]:
    """
    Find breakout searches - keywords with sudden spike in interest.
    These often indicate emerging themes.
    """
    if not HAS_PYTRENDS:
        return []

    try:
        client = GoogleTrendsClient()
        trending = client.get_trending_searches()

        # Filter for finance-related
        finance_keywords = [
            'stock', 'stocks', 'etf', 'invest', 'market', 'trading',
            'crypto', 'bitcoin', 'share', 'dividend', 'earnings'
        ]

        finance_trending = []
        for term in trending:
            term_lower = term.lower()
            if any(kw in term_lower for kw in finance_keywords):
                finance_trending.append({
                    'term': term,
                    'type': 'trending',
                    'source': 'google_trends'
                })

        return finance_trending[:10]

    except Exception as e:
        logger.error(f"Breakout searches error: {e}")
        return []


def get_theme_momentum_report() -> Dict:
    """
    Generate a comprehensive theme momentum report.

    Returns:
        Dict with trending, rising, and declining themes
    """
    themes = detect_trending_themes()

    if not themes:
        return {
            'ok': False,
            'error': 'Could not fetch theme data',
            'trending': [],
            'rising': [],
            'declining': []
        }

    # Categorize
    breakouts = [t for t in themes if t.get('is_breakout')]
    rising = [t for t in themes if t.get('trend_pct', 0) > 10 and not t.get('is_breakout')]
    declining = [t for t in themes if t.get('trend_pct', 0) < -10]
    stable = [t for t in themes if -10 <= t.get('trend_pct', 0) <= 10]

    return {
        'ok': True,
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_themes': len(themes),
            'breakouts': len(breakouts),
            'rising': len(rising),
            'declining': len(declining)
        },
        'breakouts': breakouts,
        'rising': rising,
        'stable': stable,
        'declining': declining,
        'all_themes': themes
    }


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_trends_message(report: Dict) -> str:
    """Format theme trends for Telegram."""
    if not report.get('ok'):
        return f"❌ *THEME TRENDS*\n\n{report.get('error', 'Error fetching data')}"

    msg = "📈 *THEME MOMENTUM REPORT*\n"
    msg += f"_Google Trends Analysis_\n\n"

    # Breakouts
    breakouts = report.get('breakouts', [])
    if breakouts:
        msg += "🚀 *BREAKOUT THEMES:*\n"
        for t in breakouts[:5]:
            msg += f"  • {t['theme_id'].upper()} +{t['trend_pct']:.0f}% 🔥\n"
        msg += "\n"

    # Rising
    rising = report.get('rising', [])
    if rising:
        msg += "📈 *RISING THEMES:*\n"
        for t in rising[:5]:
            msg += f"  • {t['theme_id'].upper()} +{t['trend_pct']:.0f}%\n"
        msg += "\n"

    # Declining
    declining = report.get('declining', [])
    if declining:
        msg += "📉 *DECLINING THEMES:*\n"
        for t in declining[:5]:
            msg += f"  • {t['theme_id'].upper()} {t['trend_pct']:.0f}%\n"
        msg += "\n"

    if not breakouts and not rising:
        msg += "_No significant theme movements detected_\n"

    msg += f"\n_Based on {report.get('summary', {}).get('total_themes', 0)} themes tracked_"

    return msg


# =============================================================================
# SYNC WRAPPERS
# =============================================================================

def get_trend_score_sync(keyword: str) -> Dict:
    """Synchronous wrapper for trend score."""
    return get_trend_score(keyword)


def detect_trending_themes_sync() -> List[Dict]:
    """Synchronous wrapper for theme detection."""
    return detect_trending_themes()


def get_theme_momentum_report_sync() -> Dict:
    """Synchronous wrapper for momentum report."""
    return get_theme_momentum_report()


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("Google Trends Theme Detector")
    print("=" * 50)

    if not HAS_PYTRENDS:
        print("ERROR: pytrends not installed")
        print("Run: pip install pytrends")
        exit(1)

    # Test single keyword
    print("\nTesting single keyword: 'AI chips'")
    result = get_trend_score("AI chips")
    print(f"  Score: {result.get('score')}")
    print(f"  Status: {result.get('status')}")
    print(f"  Trend: {result.get('trend_pct')}%")

    # Test theme detection
    print("\nDetecting trending themes...")
    themes = detect_trending_themes()

    for theme in themes[:5]:
        emoji = "🔥" if theme.get('is_breakout') else "📈" if theme.get('trend_pct', 0) > 10 else "➡️"
        print(f"  {emoji} {theme['theme_id']}: {theme['score']:.0f} ({theme['status']})")
