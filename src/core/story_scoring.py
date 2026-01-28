"""
Story-First Scoring System

Philosophy: The best trades are driven by narratives, not just technicals.
Story is the PRIMARY driver (85%), technicals only CONFIRM (15%).

Score Components:
- Story Quality (50%): Theme strength, freshness, clarity
- Catalyst Strength (35%): Type, recency, magnitude
- Confirmation (15%): Technical validation (filter only)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import re


class ThemeTier(Enum):
    """Theme importance tiers"""
    MEGA = "mega"           # AI, GLP-1 - transformational themes
    STRONG = "strong"       # Defense, Nuclear - clear tailwinds
    MODERATE = "moderate"   # Cybersecurity, Energy - solid themes
    WEAK = "weak"           # Fading or crowded themes
    NONE = "none"           # No clear theme


class CatalystType(Enum):
    """Catalyst types ranked by impact"""
    # Tier 1: Major catalysts (80-100 score)
    FDA_APPROVAL = "fda_approval"
    MAJOR_CONTRACT = "major_contract"
    ACQUISITION_TARGET = "acquisition_target"
    ACTIVIST_INVOLVEMENT = "activist"
    EARNINGS_BEAT_RAISE = "earnings_beat_raise"

    # Tier 2: Strong catalysts (50-79 score)
    ANALYST_UPGRADE = "analyst_upgrade"
    INSIDER_BUYING = "insider_buying"
    NEW_PRODUCT = "new_product"
    PARTNERSHIP = "partnership"
    INDEX_INCLUSION = "index_inclusion"

    # Tier 3: Moderate catalysts (30-49 score)
    EARNINGS_BEAT = "earnings_beat"
    CONFERENCE = "conference"
    SEC_8K = "sec_8k"
    SOCIAL_BUZZ = "social_buzz"

    # Tier 4: Weak catalysts (0-29 score)
    NEWS_MENTION = "news_mention"
    NO_CATALYST = "no_catalyst"


# Theme tier definitions with keywords
THEME_TIERS = {
    ThemeTier.MEGA: {
        'themes': ['AI', 'Artificial Intelligence', 'GLP-1', 'Ozempic', 'Weight Loss Drug'],
        'keywords': ['artificial intelligence', 'machine learning', 'llm', 'chatgpt', 'nvidia',
                    'glp-1', 'ozempic', 'wegovy', 'mounjaro', 'weight loss drug', 'obesity drug'],
        'score': 100,
    },
    ThemeTier.STRONG: {
        'themes': ['Nuclear', 'Defense', 'Uranium', 'Data Centers', 'Power Infrastructure'],
        'keywords': ['nuclear', 'uranium', 'defense contract', 'military', 'data center',
                    'power grid', 'electricity demand', 'energy infrastructure'],
        'score': 80,
    },
    ThemeTier.MODERATE: {
        'themes': ['Cybersecurity', 'Reshoring', 'Energy', 'Bitcoin', 'Crypto'],
        'keywords': ['cybersecurity', 'ransomware', 'reshoring', 'onshoring', 'manufacturing usa',
                    'bitcoin', 'cryptocurrency', 'etf approval', 'clean energy'],
        'score': 60,
    },
    ThemeTier.WEAK: {
        'themes': ['EV', 'Electric Vehicle', 'Cannabis', 'SPACs', 'Metaverse'],
        'keywords': ['electric vehicle', 'ev sales', 'cannabis', 'marijuana', 'spac', 'metaverse'],
        'score': 30,
    },
}

# Catalyst scores by type
CATALYST_SCORES = {
    CatalystType.FDA_APPROVAL: 100,
    CatalystType.MAJOR_CONTRACT: 95,
    CatalystType.ACQUISITION_TARGET: 90,
    CatalystType.ACTIVIST_INVOLVEMENT: 85,
    CatalystType.EARNINGS_BEAT_RAISE: 80,
    CatalystType.ANALYST_UPGRADE: 70,
    CatalystType.INSIDER_BUYING: 65,
    CatalystType.NEW_PRODUCT: 60,
    CatalystType.PARTNERSHIP: 55,
    CatalystType.INDEX_INCLUSION: 50,
    CatalystType.EARNINGS_BEAT: 45,
    CatalystType.CONFERENCE: 40,
    CatalystType.SEC_8K: 35,
    CatalystType.SOCIAL_BUZZ: 30,
    CatalystType.NEWS_MENTION: 20,
    CatalystType.NO_CATALYST: 0,
}

# Keywords for catalyst detection
CATALYST_KEYWORDS = {
    CatalystType.FDA_APPROVAL: ['fda approval', 'fda clears', 'fda grants', 'drug approval'],
    CatalystType.MAJOR_CONTRACT: ['wins contract', 'awarded contract', 'billion contract', 'major deal', 'government contract'],
    CatalystType.ACQUISITION_TARGET: ['acquisition target', 'takeover', 'buyout', 'merger talks', 'approached by'],
    CatalystType.ACTIVIST_INVOLVEMENT: ['activist investor', 'takes stake', 'pushes for', 'board seat'],
    CatalystType.EARNINGS_BEAT_RAISE: ['beats estimates', 'raises guidance', 'raises outlook', 'record revenue'],
    CatalystType.ANALYST_UPGRADE: ['upgrade', 'price target raised', 'buy rating', 'outperform'],
    CatalystType.INSIDER_BUYING: ['insider buying', 'ceo buys', 'director purchases', 'insider purchase'],
    CatalystType.NEW_PRODUCT: ['new product', 'launches', 'unveils', 'introduces'],
    CatalystType.PARTNERSHIP: ['partnership', 'teams up', 'collaborates', 'joint venture'],
    CatalystType.INDEX_INCLUSION: ['index inclusion', 'added to s&p', 'joins index', 'russell'],
    CatalystType.EARNINGS_BEAT: ['beats', 'tops estimates', 'exceeds expectations'],
    CatalystType.CONFERENCE: ['conference', 'investor day', 'presentation'],
    CatalystType.SEC_8K: ['8-k', 'sec filing', 'material event'],
    CatalystType.SOCIAL_BUZZ: ['trending', 'viral', 'reddit', 'wallstreetbets'],
}


@dataclass
class StoryScore:
    """Complete story score breakdown"""
    # Final scores
    total_score: float
    story_strength: str  # 'hot', 'developing', 'watchlist', 'waiting', 'none'

    # Component scores (0-100 each)
    story_quality_score: float
    catalyst_score: float
    confirmation_score: float

    # Story Quality breakdown
    theme_strength: float
    theme_freshness: float
    story_clarity: float
    institutional_narrative: float

    # Catalyst breakdown
    catalyst_type: str
    catalyst_type_score: float
    catalyst_recency_multiplier: float
    catalyst_magnitude: float

    # Confirmation breakdown
    trend_score: float
    volume_score: float
    buyability_score: float

    # Metadata
    primary_theme: Optional[str]
    primary_catalyst: Optional[str]
    catalyst_date: Optional[str]
    news_count: int

    def to_dict(self) -> Dict:
        return {
            'total_score': round(self.total_score, 1),
            'story_strength': self.story_strength,
            'story_quality_score': round(self.story_quality_score, 1),
            'catalyst_score': round(self.catalyst_score, 1),
            'confirmation_score': round(self.confirmation_score, 1),
            'theme_strength': round(self.theme_strength, 1),
            'theme_freshness': round(self.theme_freshness, 1),
            'story_clarity': round(self.story_clarity, 1),
            'catalyst_type': self.catalyst_type,
            'catalyst_type_score': round(self.catalyst_type_score, 1),
            'catalyst_recency': round(self.catalyst_recency_multiplier, 2),
            'primary_theme': self.primary_theme,
            'primary_catalyst': self.primary_catalyst,
            'news_count': self.news_count,
        }


class StoryScorer:
    """
    Story-First Scoring Engine

    Weights:
    - Story Quality: 50%
    - Catalyst Strength: 35%
    - Confirmation: 15%
    """

    STORY_QUALITY_WEIGHT = 0.50
    CATALYST_WEIGHT = 0.35
    CONFIRMATION_WEIGHT = 0.15

    def __init__(self):
        self.theme_cache = {}

    def detect_theme_tier(self, news: List[Dict], ticker: str, theme_data: List[Dict] = None) -> tuple:
        """
        Detect theme tier from news and theme registry.
        Returns (tier, theme_name, freshness_score)
        """
        # Check theme registry first
        best_theme = None
        best_tier = ThemeTier.NONE
        theme_stage = None

        if theme_data:
            for theme in theme_data:
                theme_name = theme.get('theme_name', '').lower()
                role = theme.get('role', '')
                stage = theme.get('stage', '')

                # Map theme to tier based on name/keywords
                for tier, tier_data in THEME_TIERS.items():
                    for t in tier_data['themes']:
                        if t.lower() in theme_name or theme_name in t.lower():
                            if tier.value < best_tier.value or best_tier == ThemeTier.NONE:
                                best_tier = tier
                                best_theme = theme.get('theme_name')
                                theme_stage = stage
                            break

                # Driver role gets tier boost
                if role == 'driver' and best_tier != ThemeTier.MEGA:
                    # Promote by one tier
                    tier_order = [ThemeTier.NONE, ThemeTier.WEAK, ThemeTier.MODERATE, ThemeTier.STRONG, ThemeTier.MEGA]
                    idx = tier_order.index(best_tier)
                    if idx < len(tier_order) - 1:
                        best_tier = tier_order[idx + 1]

        # Also scan news for theme keywords
        all_text = ' '.join([
            (n.get('title', '') + ' ' + n.get('summary', '')).lower()
            for n in news[:20]
        ])

        for tier, tier_data in THEME_TIERS.items():
            for keyword in tier_data['keywords']:
                if keyword in all_text:
                    if tier.value < best_tier.value or best_tier == ThemeTier.NONE:
                        best_tier = tier
                        best_theme = best_theme or keyword.title()
                    break

        # Calculate freshness based on stage
        freshness = 50  # Default
        if theme_stage:
            freshness_map = {
                'emerging': 100,
                'early': 85,
                'middle': 60,
                'late': 35,
                'exhausted': 15,
            }
            freshness = freshness_map.get(theme_stage, 50)
        elif best_tier in [ThemeTier.MEGA, ThemeTier.STRONG]:
            freshness = 70  # Strong themes assumed somewhat fresh

        return best_tier, best_theme, freshness

    def detect_catalyst(self, news: List[Dict], sec_data: Dict) -> tuple:
        """
        Detect catalyst type and recency from news and SEC filings.
        Returns (catalyst_type, score, recency_multiplier, catalyst_description, catalyst_date)
        """
        best_catalyst = CatalystType.NO_CATALYST
        best_score = 0
        catalyst_desc = None
        catalyst_date = None

        # Check SEC filings first
        if sec_data.get('has_8k'):
            best_catalyst = CatalystType.SEC_8K
            best_score = CATALYST_SCORES[CatalystType.SEC_8K]
            catalyst_desc = "SEC 8-K Filing"
            # Recent filing
            filings = sec_data.get('filings', [])
            if filings:
                catalyst_date = filings[0].get('date')

        if sec_data.get('insider_activity'):
            # Check if it's buying
            best_catalyst = CatalystType.INSIDER_BUYING
            best_score = CATALYST_SCORES[CatalystType.INSIDER_BUYING]
            catalyst_desc = "Insider Activity"

        # Scan news for catalyst keywords
        for article in news[:15]:
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            text = title + ' ' + summary
            pub_date = article.get('published', article.get('date'))

            for catalyst_type, keywords in CATALYST_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in text:
                        score = CATALYST_SCORES[catalyst_type]
                        if score > best_score:
                            best_catalyst = catalyst_type
                            best_score = score
                            catalyst_desc = article.get('title', keyword.title())[:50]
                            catalyst_date = pub_date
                        break

        # Calculate recency multiplier
        recency_multiplier = 0.1  # Default for no/old catalyst
        if catalyst_date:
            try:
                if isinstance(catalyst_date, str):
                    # Try parsing various date formats
                    for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%a, %d %b %Y %H:%M:%S']:
                        try:
                            dt = datetime.strptime(catalyst_date[:19], fmt)
                            break
                        except:
                            dt = datetime.now() - timedelta(days=7)  # Assume week old
                else:
                    dt = catalyst_date

                days_ago = (datetime.now() - dt).days

                if days_ago <= 1:
                    recency_multiplier = 1.0
                elif days_ago <= 3:
                    recency_multiplier = 0.9
                elif days_ago <= 7:
                    recency_multiplier = 0.7
                elif days_ago <= 14:
                    recency_multiplier = 0.5
                elif days_ago <= 30:
                    recency_multiplier = 0.3
                else:
                    recency_multiplier = 0.1
            except:
                recency_multiplier = 0.3  # Default if parsing fails

        return best_catalyst, best_score, recency_multiplier, catalyst_desc, catalyst_date

    def calculate_story_clarity(self, news: List[Dict]) -> float:
        """
        Calculate story clarity - how consistent is the narrative?
        Clear, focused stories score higher than scattered news.
        """
        if not news:
            return 0

        # Extract key topics from titles
        titles = [n.get('title', '').lower() for n in news[:10]]

        # Look for repeated keywords/themes
        word_freq = {}
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'is', 'are', 'was', 'were'}

        for title in titles:
            words = re.findall(r'\b[a-z]{4,}\b', title)
            for word in words:
                if word not in stop_words:
                    word_freq[word] = word_freq.get(word, 0) + 1

        if not word_freq:
            return 30

        # High frequency of same keywords = clear story
        max_freq = max(word_freq.values())
        avg_freq = sum(word_freq.values()) / len(word_freq)

        # If there's a dominant keyword appearing in multiple headlines
        if max_freq >= 5:
            clarity = 100
        elif max_freq >= 3:
            clarity = 75
        elif max_freq >= 2:
            clarity = 50
        else:
            clarity = 30

        return clarity

    def calculate_institutional_narrative(self, news: List[Dict]) -> float:
        """
        Check if institutions/analysts are driving the narrative.
        Analyst mentions, fund involvement, etc.
        """
        inst_keywords = [
            'analyst', 'upgrade', 'downgrade', 'price target', 'rating',
            'institutional', 'hedge fund', 'berkshire', 'blackrock', 'vanguard',
            'wall street', 'morgan stanley', 'goldman', 'jpmorgan', 'citi',
        ]

        all_text = ' '.join([
            (n.get('title', '') + ' ' + n.get('summary', '')).lower()
            for n in news[:15]
        ])

        matches = sum(1 for kw in inst_keywords if kw in all_text)

        if matches >= 5:
            return 100
        elif matches >= 3:
            return 70
        elif matches >= 1:
            return 40
        return 10

    def calculate_confirmation(
        self,
        above_20: bool,
        above_50: bool,
        above_200: bool,
        vol_ratio: float,
        distance_from_20sma_pct: float,
        breakout: bool,
        in_squeeze: bool,
    ) -> tuple:
        """
        Calculate technical confirmation score.
        This is just a FILTER - confirms story is working.
        """
        # Trend score (40% of confirmation)
        trend_score = 0
        if above_20:
            trend_score += 30
        if above_50:
            trend_score += 40
        if above_200:
            trend_score += 30

        # Volume score (30% of confirmation)
        volume_score = 0
        if vol_ratio >= 2.0:
            volume_score = 100
        elif vol_ratio >= 1.5:
            volume_score = 70
        elif vol_ratio >= 1.0:
            volume_score = 40
        else:
            volume_score = 20

        # Buyability score (30% of confirmation)
        # Not overextended = can still buy
        buyability_score = 0
        if distance_from_20sma_pct is not None:
            if distance_from_20sma_pct < 3:
                buyability_score = 100  # Right at support
            elif distance_from_20sma_pct < 5:
                buyability_score = 80
            elif distance_from_20sma_pct < 10:
                buyability_score = 50
            else:
                buyability_score = 20  # Extended
        else:
            buyability_score = 50

        # Bonus for breakout/squeeze
        if breakout:
            trend_score = min(100, trend_score + 30)
            volume_score = min(100, volume_score + 20)
        if in_squeeze:
            buyability_score = min(100, buyability_score + 20)

        confirmation_score = (
            trend_score * 0.40 +
            volume_score * 0.30 +
            buyability_score * 0.30
        )

        return confirmation_score, trend_score, volume_score, buyability_score

    def calculate_story_score(
        self,
        ticker: str,
        news: List[Dict],
        sec_data: Dict,
        theme_data: List[Dict],
        price_data: Dict,
    ) -> StoryScore:
        """
        Calculate complete story-first score.

        Args:
            ticker: Stock symbol
            news: List of news articles
            sec_data: SEC filing data
            theme_data: Theme membership from registry
            price_data: Dict with technical data (above_20, above_50, etc.)

        Returns:
            StoryScore with complete breakdown
        """
        # =====================================================
        # STORY QUALITY (50%)
        # =====================================================

        # Theme strength (40% of story quality)
        theme_tier, primary_theme, theme_freshness = self.detect_theme_tier(news, ticker, theme_data)
        theme_strength = THEME_TIERS.get(theme_tier, {}).get('score', 0)

        # Story clarity (20% of story quality)
        story_clarity = self.calculate_story_clarity(news)

        # Institutional narrative (20% of story quality)
        institutional_narrative = self.calculate_institutional_narrative(news)

        # Theme freshness already calculated (20% of story quality)

        story_quality_score = (
            theme_strength * 0.40 +
            theme_freshness * 0.20 +
            story_clarity * 0.20 +
            institutional_narrative * 0.20
        )

        # =====================================================
        # CATALYST STRENGTH (35%)
        # =====================================================

        catalyst_type, catalyst_type_score, recency_mult, catalyst_desc, catalyst_date = \
            self.detect_catalyst(news, sec_data)

        # Multiple catalysts bonus
        catalyst_count = sum(1 for n in news[:10] if any(
            kw in (n.get('title', '') + n.get('summary', '')).lower()
            for kws in CATALYST_KEYWORDS.values() for kw in kws
        ))
        multiple_catalyst_bonus = min(20, catalyst_count * 5)

        catalyst_score = (
            (catalyst_type_score * recency_mult) * 0.60 +
            catalyst_type_score * 0.25 +  # Base type score (even if old)
            multiple_catalyst_bonus * 0.15
        )

        # =====================================================
        # CONFIRMATION (15%)
        # =====================================================

        above_20 = price_data.get('above_20', False)
        above_50 = price_data.get('above_50', False)
        above_200 = price_data.get('above_200', False)
        vol_ratio = price_data.get('vol_ratio', 1.0)
        distance_pct = price_data.get('distance_from_20sma_pct')
        breakout = price_data.get('breakout_up', False)
        in_squeeze = price_data.get('in_squeeze', False)

        confirmation_score, trend_score, volume_score, buyability_score = \
            self.calculate_confirmation(
                above_20, above_50, above_200, vol_ratio, distance_pct, breakout, in_squeeze
            )

        # =====================================================
        # FINAL SCORE
        # =====================================================

        total_score = (
            story_quality_score * self.STORY_QUALITY_WEIGHT +
            catalyst_score * self.CATALYST_WEIGHT +
            confirmation_score * self.CONFIRMATION_WEIGHT
        )

        # Clamp to 0-100
        total_score = max(0, min(100, total_score))

        # Determine strength label
        if total_score >= 75:
            story_strength = 'hot'
        elif total_score >= 55:
            story_strength = 'developing'
        elif total_score >= 40:
            story_strength = 'watchlist'
        elif total_score >= 25:
            story_strength = 'waiting'
        else:
            story_strength = 'none'

        return StoryScore(
            total_score=total_score,
            story_strength=story_strength,
            story_quality_score=story_quality_score,
            catalyst_score=catalyst_score,
            confirmation_score=confirmation_score,
            theme_strength=theme_strength,
            theme_freshness=theme_freshness,
            story_clarity=story_clarity,
            institutional_narrative=institutional_narrative,
            catalyst_type=catalyst_type.value,
            catalyst_type_score=catalyst_type_score,
            catalyst_recency_multiplier=recency_mult,
            catalyst_magnitude=catalyst_type_score * recency_mult,
            trend_score=trend_score,
            volume_score=volume_score,
            buyability_score=buyability_score,
            primary_theme=primary_theme,
            primary_catalyst=catalyst_desc,
            catalyst_date=str(catalyst_date) if catalyst_date else None,
            news_count=len(news),
        )


# Singleton instance
_scorer = None


def get_story_scorer() -> StoryScorer:
    """Get global story scorer instance"""
    global _scorer
    if _scorer is None:
        _scorer = StoryScorer()
    return _scorer


def calculate_story_score(
    ticker: str,
    news: List[Dict],
    sec_data: Dict,
    theme_data: List[Dict],
    price_data: Dict,
) -> StoryScore:
    """Convenience function to calculate story score"""
    return get_story_scorer().calculate_story_score(
        ticker, news, sec_data, theme_data, price_data
    )
