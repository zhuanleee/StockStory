"""
Automatic Theme Discovery
=========================
Discovers emerging investment themes automatically using multiple signals.

Discovery Methods:
1. News keyword extraction (DeepSeek AI)
2. Google Trends rising queries
3. Social/alternative source mining
4. Stock correlation clustering

Usage:
    from src.intelligence.theme_discovery import ThemeDiscoveryEngine

    engine = ThemeDiscoveryEngine()

    # Discover new themes
    new_themes = engine.discover_themes()

    # Get emerging keywords
    keywords = engine.extract_trending_keywords()
"""

import os
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import Counter

logger = logging.getLogger(__name__)

# Persistence
DATA_DIR = Path("data/theme_discovery")
DISCOVERED_THEMES_FILE = DATA_DIR / "discovered_themes.json"
KEYWORD_HISTORY_FILE = DATA_DIR / "keyword_history.json"


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DiscoveredTheme:
    """A newly discovered theme."""
    theme_id: str
    name: str
    keywords: List[str]
    source: str  # news, trends, social, correlation
    confidence: float  # 0-1
    discovered_at: str
    related_tickers: List[str]
    sample_headlines: List[str]
    trend_score: float = 0
    mention_count: int = 0
    validated: bool = False


@dataclass
class TrendingKeyword:
    """A trending keyword detected."""
    keyword: str
    source: str
    score: float
    growth_rate: float
    related_tickers: List[str]
    first_seen: str
    last_seen: str
    mention_count: int


# Known financial keywords to filter out (too generic)
GENERIC_KEYWORDS = {
    'stock', 'stocks', 'market', 'markets', 'trading', 'trade', 'invest',
    'investment', 'investor', 'investors', 'price', 'prices', 'share',
    'shares', 'earnings', 'revenue', 'profit', 'loss', 'quarter', 'year',
    'company', 'companies', 'business', 'ceo', 'analyst', 'analysts',
    'buy', 'sell', 'hold', 'rating', 'target', 'wall street', 'nyse',
    'nasdaq', 'dow', 's&p', 'index', 'etf', 'fund', 'funds', 'billion',
    'million', 'percent', 'growth', 'decline', 'rise', 'fall', 'gain',
    'drop', 'surge', 'plunge', 'rally', 'selloff', 'volatility'
}

# Theme-indicative keywords (signals a potential theme)
THEME_INDICATORS = {
    'ai', 'artificial intelligence', 'machine learning', 'gpu', 'chips',
    'semiconductor', 'nuclear', 'uranium', 'smr', 'reactor',
    'ev', 'electric vehicle', 'battery', 'lithium', 'charging',
    'bitcoin', 'crypto', 'blockchain', 'ethereum', 'defi',
    'weight loss', 'glp-1', 'ozempic', 'obesity', 'wegovy',
    'defense', 'military', 'aerospace', 'drone', 'missile',
    'cybersecurity', 'cyber', 'hack', 'security', 'ransomware',
    'cloud', 'saas', 'aws', 'azure', 'data center',
    'solar', 'renewable', 'clean energy', 'wind', 'green',
    'quantum', 'qubit', 'quantum computing',
    'space', 'satellite', 'rocket', 'launch', 'orbit',
    'robot', 'robotics', 'automation', 'humanoid',
    'biotech', 'gene', 'therapy', 'drug', 'fda',
    'fintech', 'payment', 'digital bank', 'neobank',
    'metaverse', 'vr', 'ar', 'virtual reality',
    'infrastructure', 'construction', 'bridge', 'road',
    'gold', 'silver', 'precious metal', 'mining',
    'oil', 'gas', 'energy', 'opec', 'drilling',
    'tariff', 'trade war', 'sanction', 'embargo',
    'rate cut', 'fed', 'interest rate', 'inflation',
}


class ThemeDiscoveryEngine:
    """
    Automatic theme discovery using multiple signal sources.
    """

    def __init__(self):
        ensure_data_dir()
        self.discovered_themes = self._load_discovered_themes()
        self.keyword_history = self._load_keyword_history()

    def _load_discovered_themes(self) -> Dict[str, DiscoveredTheme]:
        """Load previously discovered themes."""
        if DISCOVERED_THEMES_FILE.exists():
            try:
                with open(DISCOVERED_THEMES_FILE) as f:
                    data = json.load(f)
                    return {k: DiscoveredTheme(**v) for k, v in data.items()}
            except:
                pass
        return {}

    def _save_discovered_themes(self):
        """Save discovered themes to disk."""
        data = {k: asdict(v) for k, v in self.discovered_themes.items()}
        with open(DISCOVERED_THEMES_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_keyword_history(self) -> Dict[str, TrendingKeyword]:
        """Load keyword tracking history."""
        if KEYWORD_HISTORY_FILE.exists():
            try:
                with open(KEYWORD_HISTORY_FILE) as f:
                    data = json.load(f)
                    return {k: TrendingKeyword(**v) for k, v in data.items()}
            except:
                pass
        return {}

    def _save_keyword_history(self):
        """Save keyword history."""
        data = {k: asdict(v) for k, v in self.keyword_history.items()}
        with open(KEYWORD_HISTORY_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    # =========================================================================
    # NEWS KEYWORD EXTRACTION
    # =========================================================================

    def extract_keywords_from_news(self, limit: int = 50) -> List[Dict]:
        """
        Extract trending keywords from recent news using DeepSeek.
        """
        try:
            # Get news from Polygon
            from src.data.polygon_provider import PolygonDataProvider

            provider = PolygonDataProvider()

            # Get market-wide news
            news_items = []

            # Get news for major indices/ETFs to capture broad themes
            symbols = ['SPY', 'QQQ', 'IWM', 'XLF', 'XLE', 'XLK', 'XLV']

            for symbol in symbols:
                try:
                    news = provider.get_news_sync(symbol, limit=10)
                    if news:
                        news_items.extend(news)
                except:
                    continue

            if not news_items:
                logger.warning("No news items fetched")
                return []

            # Extract headlines
            headlines = []
            for item in news_items[:limit]:
                title = item.get('title', '')
                description = item.get('description', '')
                if title:
                    headlines.append(title)
                if description:
                    headlines.append(description[:200])

            # Use DeepSeek to extract themes
            keywords = self._extract_themes_with_ai(headlines)

            return keywords

        except Exception as e:
            logger.error(f"News keyword extraction error: {e}")
            return []

    def _extract_themes_with_ai(self, headlines: List[str]) -> List[Dict]:
        """Use DeepSeek to extract investment themes from headlines."""
        try:
            from src.sentiment.deepseek_sentiment import _call_deepseek

            # Combine headlines
            text = "\n".join(headlines[:30])

            prompt = f"""Analyze these financial news headlines and extract emerging investment themes.

Headlines:
{text}

For each theme found, provide:
1. Theme name (2-3 words, e.g., "AI Chips", "Nuclear Energy")
2. Key keywords associated with the theme
3. Any stock tickers mentioned
4. Confidence score (0-1) based on how strongly the theme appears

Return as JSON array:
[
  {{"theme": "Theme Name", "keywords": ["kw1", "kw2"], "tickers": ["TICK1"], "confidence": 0.8}},
  ...
]

Only include themes that appear multiple times or have strong signals.
Return empty array [] if no clear themes found.
"""

            response = _call_deepseek(prompt, max_tokens=1000)

            if response:
                # Parse JSON from response
                try:
                    # Find JSON array in response
                    match = re.search(r'\[.*\]', response, re.DOTALL)
                    if match:
                        themes = json.loads(match.group())
                        return themes
                except json.JSONDecodeError:
                    pass

            return []

        except Exception as e:
            logger.error(f"AI theme extraction error: {e}")
            return []

    # =========================================================================
    # GOOGLE TRENDS RISING QUERIES
    # =========================================================================

    def get_rising_queries(self) -> List[Dict]:
        """
        Get rising queries from Google Trends for finance-related terms.
        """
        try:
            from src.data.google_trends import GoogleTrendsClient, HAS_PYTRENDS

            if not HAS_PYTRENDS:
                return []

            client = GoogleTrendsClient()

            rising_keywords = []

            # Check rising queries for key financial terms
            seed_keywords = [
                'stock market',
                'investing',
                'stocks to buy',
                'best stocks',
            ]

            for seed in seed_keywords:
                try:
                    related = client.get_related_queries(seed)

                    rising = related.get('rising', [])
                    for item in rising[:10]:
                        query = item.get('query', '')
                        value = item.get('value', 0)

                        # Filter out generic terms
                        if query.lower() not in GENERIC_KEYWORDS:
                            rising_keywords.append({
                                'keyword': query,
                                'growth': value,
                                'source': 'google_trends',
                                'seed': seed
                            })

                    import time
                    time.sleep(1)  # Rate limiting

                except Exception as e:
                    logger.debug(f"Rising query error for {seed}: {e}")
                    continue

            # Deduplicate and sort by growth
            seen = set()
            unique = []
            for kw in sorted(rising_keywords, key=lambda x: x.get('growth', 0), reverse=True):
                if kw['keyword'].lower() not in seen:
                    seen.add(kw['keyword'].lower())
                    unique.append(kw)

            return unique[:20]

        except Exception as e:
            logger.error(f"Rising queries error: {e}")
            return []

    # =========================================================================
    # ALTERNATIVE SOURCES (PODCASTS, NEWSLETTERS)
    # =========================================================================

    def extract_from_alt_sources(self) -> List[Dict]:
        """Extract trending topics from podcasts and newsletters."""
        try:
            from src.data.alt_sources import extract_themes_from_alt_sources

            result = extract_themes_from_alt_sources()

            themes = []
            for theme_name, data in result.get('themes', {}).items():
                themes.append({
                    'theme': theme_name,
                    'keywords': data.get('keywords', []),
                    'tickers': data.get('tickers', []),
                    'mention_count': data.get('count', 0),
                    'source': 'alt_sources'
                })

            return sorted(themes, key=lambda x: x.get('mention_count', 0), reverse=True)

        except ImportError:
            logger.debug("Alt sources module not available")
            return []
        except Exception as e:
            logger.error(f"Alt sources extraction error: {e}")
            return []

    # =========================================================================
    # STOCK CORRELATION CLUSTERING
    # =========================================================================

    def find_correlated_clusters(self, min_correlation: float = 0.7) -> List[Dict]:
        """
        Find groups of stocks moving together (potential undiscovered themes).
        """
        try:
            from src.data.polygon_provider import PolygonDataProvider
            import pandas as pd
            import numpy as np

            provider = PolygonDataProvider()

            # Get top movers from recent days
            movers = provider.get_market_movers_sync()

            if not movers:
                return []

            # Get tickers from gainers
            tickers = []
            gainers = movers.get('gainers', [])
            for g in gainers[:30]:
                ticker = g.get('ticker', '')
                if ticker and len(ticker) <= 5:
                    tickers.append(ticker)

            if len(tickers) < 5:
                return []

            # Get price data for correlation
            price_data = {}
            for ticker in tickers[:20]:
                try:
                    data = provider.get_price_data_sync(ticker, days=30)
                    if data is not None and len(data) >= 20:
                        price_data[ticker] = data['close'].pct_change().dropna()
                except:
                    continue

            if len(price_data) < 5:
                return []

            # Build correlation matrix
            df = pd.DataFrame(price_data)
            corr_matrix = df.corr()

            # Find highly correlated groups
            clusters = []
            used = set()

            for ticker in corr_matrix.columns:
                if ticker in used:
                    continue

                # Find all tickers correlated > threshold
                correlated = corr_matrix[ticker][corr_matrix[ticker] > min_correlation].index.tolist()

                if len(correlated) >= 3:
                    clusters.append({
                        'tickers': correlated,
                        'avg_correlation': corr_matrix.loc[correlated, correlated].mean().mean(),
                        'size': len(correlated),
                        'source': 'correlation'
                    })
                    used.update(correlated)

            return clusters

        except Exception as e:
            logger.error(f"Correlation clustering error: {e}")
            return []

    # =========================================================================
    # MAIN DISCOVERY FUNCTION
    # =========================================================================

    def discover_themes(self) -> List[DiscoveredTheme]:
        """
        Run full theme discovery pipeline.

        Returns list of newly discovered themes.
        """
        logger.info("Starting theme discovery...")

        all_signals = []

        # 1. News keyword extraction
        logger.info("Extracting keywords from news...")
        news_themes = self.extract_keywords_from_news()
        for theme in news_themes:
            all_signals.append({
                'name': theme.get('theme', ''),
                'keywords': theme.get('keywords', []),
                'tickers': theme.get('tickers', []),
                'confidence': theme.get('confidence', 0.5),
                'source': 'news',
                'headlines': []
            })

        # 2. Google Trends rising queries
        logger.info("Checking Google Trends rising queries...")
        rising = self.get_rising_queries()
        for item in rising:
            keyword = item.get('keyword', '')
            # Check if keyword matches theme indicators
            for indicator in THEME_INDICATORS:
                if indicator in keyword.lower():
                    all_signals.append({
                        'name': keyword.title(),
                        'keywords': [keyword],
                        'tickers': [],
                        'confidence': min(0.9, item.get('growth', 0) / 1000),
                        'source': 'trends',
                        'headlines': []
                    })
                    break

        # 3. Alternative sources
        logger.info("Scanning alternative sources...")
        alt_themes = self.extract_from_alt_sources()
        for theme in alt_themes:
            if theme.get('mention_count', 0) >= 3:
                all_signals.append({
                    'name': theme.get('theme', ''),
                    'keywords': theme.get('keywords', []),
                    'tickers': theme.get('tickers', []),
                    'confidence': min(0.8, theme.get('mention_count', 0) / 10),
                    'source': 'alt_sources',
                    'headlines': []
                })

        # 4. Correlation clusters
        logger.info("Finding correlated stock clusters...")
        clusters = self.find_correlated_clusters()
        for cluster in clusters:
            if cluster.get('size', 0) >= 3:
                # Try to identify theme from ticker sectors
                theme_name = self._identify_cluster_theme(cluster.get('tickers', []))
                if theme_name:
                    all_signals.append({
                        'name': theme_name,
                        'keywords': [],
                        'tickers': cluster.get('tickers', []),
                        'confidence': cluster.get('avg_correlation', 0.5),
                        'source': 'correlation',
                        'headlines': []
                    })

        # Consolidate and validate signals
        new_themes = self._consolidate_signals(all_signals)

        # Save discoveries
        for theme in new_themes:
            self.discovered_themes[theme.theme_id] = theme

        self._save_discovered_themes()

        logger.info(f"Discovered {len(new_themes)} new themes")

        return new_themes

    def _identify_cluster_theme(self, tickers: List[str]) -> Optional[str]:
        """Try to identify a theme name from a cluster of tickers."""
        try:
            from src.data.polygon_provider import PolygonDataProvider

            provider = PolygonDataProvider()

            sectors = []
            industries = []

            for ticker in tickers[:5]:
                try:
                    details = provider.get_ticker_details_sync(ticker)
                    if details:
                        sector = details.get('sector', '')
                        industry = details.get('industry', '')
                        if sector:
                            sectors.append(sector)
                        if industry:
                            industries.append(industry)
                except:
                    continue

            # Find most common
            if industries:
                common_industry = Counter(industries).most_common(1)
                if common_industry and common_industry[0][1] >= 2:
                    return common_industry[0][0]

            if sectors:
                common_sector = Counter(sectors).most_common(1)
                if common_sector and common_sector[0][1] >= 2:
                    return f"{common_sector[0][0]} Cluster"

            return None

        except:
            return None

    def _consolidate_signals(self, signals: List[Dict]) -> List[DiscoveredTheme]:
        """Consolidate signals into validated themes."""
        # Group by similar names/keywords
        theme_groups = {}

        for signal in signals:
            name = signal.get('name', '').lower().strip()
            if not name or len(name) < 3:
                continue

            # Check if similar theme already exists
            matched = False
            for existing_name in list(theme_groups.keys()):
                if self._similar_themes(name, existing_name):
                    # Merge into existing
                    theme_groups[existing_name]['signals'].append(signal)
                    theme_groups[existing_name]['tickers'].extend(signal.get('tickers', []))
                    theme_groups[existing_name]['keywords'].extend(signal.get('keywords', []))
                    matched = True
                    break

            if not matched:
                theme_groups[name] = {
                    'signals': [signal],
                    'tickers': signal.get('tickers', []),
                    'keywords': signal.get('keywords', [])
                }

        # Create themes from groups with multiple signals
        new_themes = []

        for name, group in theme_groups.items():
            signals = group['signals']

            # Require at least 2 signals or high confidence
            total_confidence = sum(s.get('confidence', 0) for s in signals)

            if len(signals) >= 2 or total_confidence >= 0.8:
                # Check if not already in known themes
                from src.intelligence.theme_intelligence import THEME_TICKER_MAP

                existing = False
                for known_id in THEME_TICKER_MAP.keys():
                    if self._similar_themes(name, known_id):
                        existing = True
                        break

                if not existing:
                    theme_id = name.lower().replace(' ', '_').replace('-', '_')[:20]

                    theme = DiscoveredTheme(
                        theme_id=theme_id,
                        name=name.title(),
                        keywords=list(set(group['keywords']))[:10],
                        source=signals[0].get('source', 'unknown'),
                        confidence=min(1.0, total_confidence / len(signals)),
                        discovered_at=datetime.now().isoformat(),
                        related_tickers=list(set(group['tickers']))[:10],
                        sample_headlines=[],
                        trend_score=0,
                        mention_count=len(signals),
                        validated=len(signals) >= 3
                    )

                    new_themes.append(theme)

        return new_themes

    def _similar_themes(self, name1: str, name2: str) -> bool:
        """Check if two theme names are similar."""
        n1 = name1.lower().replace('_', ' ').replace('-', ' ')
        n2 = name2.lower().replace('_', ' ').replace('-', ' ')

        # Exact match
        if n1 == n2:
            return True

        # One contains the other
        if n1 in n2 or n2 in n1:
            return True

        # Word overlap
        words1 = set(n1.split())
        words2 = set(n2.split())
        overlap = len(words1 & words2)

        if overlap >= 1 and overlap >= min(len(words1), len(words2)) * 0.5:
            return True

        return False

    # =========================================================================
    # KEYWORD TRACKING
    # =========================================================================

    def track_keyword(self, keyword: str, source: str, score: float, tickers: List[str] = None):
        """Track a trending keyword over time."""
        key = keyword.lower()
        now = datetime.now().isoformat()

        if key in self.keyword_history:
            kw = self.keyword_history[key]
            kw.last_seen = now
            kw.mention_count += 1
            kw.score = max(kw.score, score)
            if tickers:
                kw.related_tickers = list(set(kw.related_tickers + tickers))[:10]
        else:
            self.keyword_history[key] = TrendingKeyword(
                keyword=keyword,
                source=source,
                score=score,
                growth_rate=0,
                related_tickers=tickers or [],
                first_seen=now,
                last_seen=now,
                mention_count=1
            )

        self._save_keyword_history()

    def get_hot_keywords(self, min_mentions: int = 3) -> List[TrendingKeyword]:
        """Get keywords that are consistently appearing."""
        hot = []

        cutoff = datetime.now() - timedelta(days=7)

        for kw in self.keyword_history.values():
            try:
                last_seen = datetime.fromisoformat(kw.last_seen)
                if last_seen > cutoff and kw.mention_count >= min_mentions:
                    hot.append(kw)
            except:
                continue

        return sorted(hot, key=lambda x: x.mention_count, reverse=True)

    # =========================================================================
    # API METHODS
    # =========================================================================

    def get_discovered_themes(self, validated_only: bool = False) -> List[Dict]:
        """Get all discovered themes."""
        themes = list(self.discovered_themes.values())

        if validated_only:
            themes = [t for t in themes if t.validated]

        return [asdict(t) for t in sorted(themes, key=lambda x: x.confidence, reverse=True)]

    def get_discovery_report(self) -> Dict:
        """Get full discovery report."""
        themes = list(self.discovered_themes.values())
        keywords = self.get_hot_keywords()

        return {
            'ok': True,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_discovered': len(themes),
                'validated': len([t for t in themes if t.validated]),
                'hot_keywords': len(keywords)
            },
            'themes': [asdict(t) for t in themes],
            'hot_keywords': [asdict(k) for k in keywords[:20]],
            'by_source': {
                'news': len([t for t in themes if t.source == 'news']),
                'trends': len([t for t in themes if t.source == 'trends']),
                'alt_sources': len([t for t in themes if t.source == 'alt_sources']),
                'correlation': len([t for t in themes if t.source == 'correlation'])
            }
        }


# =============================================================================
# SINGLETON
# =============================================================================

_discovery_engine = None


def get_discovery_engine() -> ThemeDiscoveryEngine:
    """Get singleton discovery engine."""
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = ThemeDiscoveryEngine()
    return _discovery_engine


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def discover_themes() -> List[Dict]:
    """Run theme discovery and return results."""
    engine = get_discovery_engine()
    themes = engine.discover_themes()
    return [asdict(t) for t in themes]


def get_discovery_report() -> Dict:
    """Get discovery report."""
    return get_discovery_engine().get_discovery_report()


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_discovery_message(report: Dict) -> str:
    """Format discovery report for Telegram."""
    if not report.get('ok'):
        return f"Error: {report.get('error', 'Unknown')}"

    summary = report.get('summary', {})
    themes = report.get('themes', [])
    keywords = report.get('hot_keywords', [])

    msg = "🔍 *THEME DISCOVERY REPORT*\n"
    msg += "_Auto-detected investment themes_\n\n"

    # Summary
    msg += f"*Discovered:* {summary.get('total_discovered', 0)} themes\n"
    msg += f"*Validated:* {summary.get('validated', 0)} themes\n"
    msg += f"*Hot Keywords:* {summary.get('hot_keywords', 0)}\n\n"

    # New themes
    if themes:
        msg += "🆕 *NEW THEMES:*\n"
        for t in themes[:5]:
            emoji = "✅" if t.get('validated') else "🔸"
            confidence = t.get('confidence', 0) * 100
            msg += f"{emoji} `{t['name']}` ({confidence:.0f}% conf)\n"
            if t.get('related_tickers'):
                msg += f"   Tickers: {', '.join(t['related_tickers'][:5])}\n"
        msg += "\n"

    # Hot keywords
    if keywords:
        msg += "🔥 *HOT KEYWORDS:*\n"
        for k in keywords[:5]:
            msg += f"• `{k['keyword']}` ({k['mention_count']} mentions)\n"

    return msg


if __name__ == "__main__":
    print("Theme Discovery Engine")
    print("=" * 50)

    engine = ThemeDiscoveryEngine()

    print("\nRunning discovery...")
    themes = engine.discover_themes()

    print(f"\nDiscovered {len(themes)} themes:")
    for theme in themes:
        print(f"  - {theme.name} (confidence: {theme.confidence:.2f})")
        print(f"    Source: {theme.source}")
        print(f"    Tickers: {', '.join(theme.related_tickers[:5])}")
