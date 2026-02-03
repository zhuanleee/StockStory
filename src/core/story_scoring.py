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
import logging

logger = logging.getLogger(__name__)


class ThemeTier(Enum):
    """Theme importance tiers"""
    MEGA = "mega"           # AI, GLP-1 - transformational themes
    STRONG = "strong"       # Defense, Nuclear - clear tailwinds
    MODERATE = "moderate"   # Cybersecurity, Energy - solid themes
    WEAK = "weak"           # Fading or crowded themes
    NONE = "none"           # No clear theme


class ThemeRole(Enum):
    """Role within a theme's supply chain"""
    LEADER = "leader"               # Theme leaders (move first)
    SUPPLIER = "supplier"           # Equipment/chip suppliers
    EQUIPMENT = "equipment"         # Infrastructure providers
    MATERIAL = "material"           # Raw materials
    BENEFICIARY = "beneficiary"     # Software/service beneficiaries
    INFRASTRUCTURE = "infrastructure"  # Supporting infrastructure


# Role-based score multipliers
ROLE_MULTIPLIERS = {
    ThemeRole.LEADER: 1.0,          # Leaders get full score
    ThemeRole.SUPPLIER: 0.85,       # Suppliers lag slightly
    ThemeRole.EQUIPMENT: 0.80,      # Equipment follows
    ThemeRole.BENEFICIARY: 0.90,    # Beneficiaries closely tied
    ThemeRole.INFRASTRUCTURE: 0.75, # Infrastructure is slower
    ThemeRole.MATERIAL: 0.70,       # Materials are furthest
}


class CatalystType(Enum):
    """Catalyst types ranked by impact"""
    # Tier 1: Major catalysts (80-100 score)
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
        'themes': ['AI', 'Artificial Intelligence', 'Data Center', 'Nvidia'],
        'keywords': ['artificial intelligence', 'machine learning', 'llm', 'chatgpt', 'nvidia',
                    'data center', 'gpu', 'ai chip', 'ai infrastructure'],
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


# Supply chain maps from theme discovery engine
# Maps themes to their ecosystem (leaders, suppliers, beneficiaries, etc.)
SUPPLY_CHAIN_MAP = {
    'ai_infrastructure': {
        'leaders': ['NVDA', 'AMD', 'MSFT', 'GOOGL', 'META'],
        'suppliers': ['ASML', 'LRCX', 'AMAT', 'KLAC'],  # Chip equipment
        'equipment': ['DELL', 'HPE', 'SMCI'],  # Servers
        'materials': ['ENTG', 'MKSI', 'CRUS'],  # Materials
        'beneficiaries': ['PLTR', 'SNOW', 'MDB', 'DDOG'],  # Software
        'infrastructure': ['EQIX', 'DLR', 'AMT'],  # Data centers
    },
    'nuclear_energy': {
        'leaders': ['CEG', 'VST', 'NRG'],
        'suppliers': ['CCJ', 'UEC', 'DNN', 'UUUU'],  # Uranium
        'equipment': ['GEV', 'BWX', 'FLR'],  # Equipment/Construction
        'materials': ['NEM', 'FCX'],  # Mining
        'beneficiaries': ['ETN', 'EMR', 'ROK'],  # Grid/Electrical
        'infrastructure': ['NEE', 'DUK', 'SO'],  # Utilities
    },
    'defense_tech': {
        'leaders': ['LMT', 'RTX', 'NOC', 'GD'],
        'suppliers': ['HII', 'TXT', 'LHX'],  # Contractors
        'equipment': ['AXON', 'PLTR', 'LDOS'],  # Tech
        'materials': ['ATI', 'HWM', 'TDG'],  # Aerospace materials
        'beneficiaries': ['KTOS', 'RGR', 'SWBI'],  # Smaller defense
        'infrastructure': ['BAH', 'CACI', 'SAIC'],  # Services
    },
    'ev_battery': {
        'leaders': ['TSLA', 'RIVN', 'LCID'],
        'suppliers': ['PCRFY', 'ALB', 'SQM', 'LAC'],  # Lithium
        'equipment': ['PLUG', 'BLNK', 'CHPT'],  # Charging
        'materials': ['MP', 'LTHM'],  # Rare earth
        'beneficiaries': ['F', 'GM', 'STLA'],  # Legacy auto
        'infrastructure': ['EOSE', 'STEM', 'NOVA'],  # Energy storage
    },
    'cybersecurity': {
        'leaders': ['CRWD', 'PANW', 'ZS'],
        'suppliers': ['FTNT', 'S', 'TENB'],  # Security vendors
        'equipment': ['CSCO', 'JNPR', 'ANET'],  # Network
        'materials': ['QLYS', 'VRNS', 'RPD'],  # Tools
        'beneficiaries': ['OKTA', 'NET', 'DDOG'],  # Cloud security
        'infrastructure': ['ACN', 'IBM', 'LDOS'],  # Services
    },
}


# Map theme names to supply chain IDs
THEME_NAME_TO_SUPPLY_CHAIN = {
    'ai': 'ai_infrastructure',
    'artificial intelligence': 'ai_infrastructure',
    'ai infrastructure': 'ai_infrastructure',
    'nuclear': 'nuclear_energy',
    'nuclear power': 'nuclear_energy',
    'uranium': 'nuclear_energy',
    'defense': 'defense_tech',
    'defense tech': 'defense_tech',
    'military': 'defense_tech',
    'ev': 'ev_battery',
    'electric vehicle': 'ev_battery',
    'battery': 'ev_battery',
    'cybersecurity': 'cybersecurity',
    'cyber': 'cybersecurity',
}


# Catalyst scores by type
CATALYST_SCORES = {
    CatalystType.MAJOR_CONTRACT: 100,
    CatalystType.ACQUISITION_TARGET: 95,
    CatalystType.ACTIVIST_INVOLVEMENT: 90,
    CatalystType.EARNINGS_BEAT_RAISE: 85,
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
    social_buzz_score: float
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
            'social_buzz_score': round(self.social_buzz_score, 1),
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
    - Story Quality: 45%
    - Catalyst Strength: 30%
    - Social Buzz: 15% (Reddit, SEC, Google Trends)
    - Confirmation: 10%
    """

    STORY_QUALITY_WEIGHT = 0.45
    CATALYST_WEIGHT = 0.30
    SOCIAL_BUZZ_WEIGHT = 0.15
    CONFIRMATION_WEIGHT = 0.10

    def __init__(self):
        self.theme_cache = {}

    def detect_theme_tier(self, news: List[Dict], ticker: str, theme_data: List[Dict] = None) -> tuple:
        """
        Detect theme tier from news and theme registry.
        Enhanced with supply chain role detection.
        Returns (tier, theme_name, freshness_score, role_multiplier)
        """
        # Check theme registry first
        best_theme = None
        best_tier = ThemeTier.NONE
        theme_stage = None
        role_multiplier = 1.0

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

        # Check supply chain map for role-based scoring
        supply_chain_role = self._detect_supply_chain_role(ticker, best_theme)
        if supply_chain_role:
            role_multiplier = ROLE_MULTIPLIERS.get(supply_chain_role, 1.0)
            logger.debug(f"{ticker}: Theme role = {supply_chain_role.value}, multiplier = {role_multiplier}")

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
                        # Check supply chain role for keyword-detected themes too
                        supply_chain_role = self._detect_supply_chain_role(ticker, best_theme)
                        if supply_chain_role:
                            role_multiplier = ROLE_MULTIPLIERS.get(supply_chain_role, 1.0)
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

        return best_tier, best_theme, freshness, role_multiplier

    def _detect_supply_chain_role(self, ticker: str, theme_name: Optional[str]) -> Optional[ThemeRole]:
        """
        Detect ticker's role in theme supply chain.
        Returns role or None if not found.
        """
        if not theme_name:
            return None

        # Map theme name to supply chain ID
        theme_lower = theme_name.lower()
        supply_chain_id = None

        for key, sc_id in THEME_NAME_TO_SUPPLY_CHAIN.items():
            if key in theme_lower:
                supply_chain_id = sc_id
                break

        if not supply_chain_id or supply_chain_id not in SUPPLY_CHAIN_MAP:
            return None

        # Find ticker in supply chain
        supply_chain = SUPPLY_CHAIN_MAP[supply_chain_id]

        for role_name, tickers in supply_chain.items():
            if ticker in tickers:
                # Map role name to ThemeRole enum
                role_map = {
                    'leaders': ThemeRole.LEADER,
                    'suppliers': ThemeRole.SUPPLIER,
                    'equipment': ThemeRole.EQUIPMENT,
                    'materials': ThemeRole.MATERIAL,
                    'beneficiaries': ThemeRole.BENEFICIARY,
                    'infrastructure': ThemeRole.INFRASTRUCTURE,
                }
                return role_map.get(role_name)

        return None

    def detect_catalyst(self, news: List[Dict], sec_data: Dict, ticker: str = None) -> tuple:
        """
        Detect catalyst type and recency from news, SEC filings, and government contracts.
        Returns (catalyst_type, score, recency_multiplier, catalyst_description, catalyst_date)
        """
        best_catalyst = CatalystType.NO_CATALYST
        best_score = 0
        catalyst_desc = None
        catalyst_date = None

        # Check government contracts first (high-value catalyst)
        if ticker:
            try:
                from src.data.gov_contracts import get_company_contracts

                contracts = get_company_contracts(ticker)
                if contracts and contracts.get('contract_count', 0) > 0:
                    recent_contracts = contracts.get('recent_contracts', [])

                    # Check for large contracts with tiered recency
                    # - Last 180 days: Major catalyst (95 points)
                    # - Last 365 days: Strong catalyst (but older, 70 points)
                    one_year_ago = datetime.now() - timedelta(days=365)
                    six_months_ago = datetime.now() - timedelta(days=180)

                    for contract in recent_contracts:
                        contract_amount = contract.get('amount', 0)
                        award_date_str = contract.get('date', contract.get('award_date', ''))

                        if contract_amount >= 10_000_000:  # $10M+ contracts
                            try:
                                award_date = datetime.strptime(award_date_str[:10], '%Y-%m-%d')

                                # Recent contract (last 6 months) = Major catalyst
                                if award_date >= six_months_ago:
                                    best_catalyst = CatalystType.MAJOR_CONTRACT
                                    best_score = CATALYST_SCORES[CatalystType.MAJOR_CONTRACT]
                                    catalyst_desc = f"${contract_amount/1e6:.0f}M Government Contract"
                                    catalyst_date = award_date_str

                                    logger.debug(f"{ticker}: Major government contract catalyst: {catalyst_desc}")
                                    break  # Use the largest/most recent

                                # Older contract (6-12 months) = Analyst upgrade level
                                elif award_date >= one_year_ago:
                                    if best_score < CATALYST_SCORES[CatalystType.ANALYST_UPGRADE]:
                                        best_catalyst = CatalystType.ANALYST_UPGRADE
                                        best_score = CATALYST_SCORES[CatalystType.ANALYST_UPGRADE]
                                        catalyst_desc = f"${contract_amount/1e6:.0f}M Government Contract (older)"
                                        catalyst_date = award_date_str
                                        logger.debug(f"{ticker}: Older government contract catalyst: {catalyst_desc}")

                            except (ValueError, TypeError) as e:
                                logger.debug(f"Failed to parse contract date {award_date_str}: {e}")
                                continue

            except Exception as e:
                logger.debug(f"Failed to check government contracts for {ticker}: {e}")

        # Check SEC filings
        if best_score < CATALYST_SCORES[CatalystType.SEC_8K]:
            if sec_data.get('has_8k'):
                best_catalyst = CatalystType.SEC_8K
                best_score = CATALYST_SCORES[CatalystType.SEC_8K]
                catalyst_desc = "SEC 8-K Filing"
                # Recent filing
                filings = sec_data.get('filings', [])
                if filings:
                    catalyst_date = filings[0].get('date')

        if best_score < CATALYST_SCORES[CatalystType.INSIDER_BUYING]:
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
                    dt = None
                    for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%a, %d %b %Y %H:%M:%S']:
                        try:
                            dt = datetime.strptime(catalyst_date[:19], fmt)
                            break
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Date format {fmt} failed for {catalyst_date}: {e}")
                            continue

                    if dt is None:
                        logger.warning(f"Could not parse catalyst date: {catalyst_date}, assuming 7 days old")
                        dt = datetime.now() - timedelta(days=7)
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
            except Exception as e:
                logger.warning(f"Error calculating catalyst recency: {e}")
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

    def calculate_institutional_narrative(self, news: List[Dict], ticker: str = None) -> float:
        """
        Check if institutions/analysts are driving the narrative.
        Enhanced with patent activity signal for innovation tracking.
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

        base_score = 10
        if matches >= 5:
            base_score = 100
        elif matches >= 3:
            base_score = 70
        elif matches >= 1:
            base_score = 40

        # Patent activity boost (innovation signal for tech/biotech)
        patent_boost = 0
        if ticker:
            try:
                from src.data.patents import get_company_patents

                patents = get_company_patents(ticker)
                if patents and patents.get('patent_count', 0) > 0:
                    recent_patents = patents.get('recent_patents', [])

                    # Recent patents (last 180 days) boost institutional narrative
                    six_months_ago = datetime.now() - timedelta(days=180)
                    recent_count = 0

                    for patent in recent_patents:
                        grant_date_str = patent.get('grant_date', '')
                        if grant_date_str:
                            try:
                                grant_date = datetime.strptime(grant_date_str[:10], '%Y-%m-%d')
                                if grant_date >= six_months_ago:
                                    recent_count += 1
                            except (ValueError, TypeError) as e:
                                logger.debug(f"Failed to parse patent date {grant_date_str}: {e}")
                                continue

                    # Scale patent boost: 1-3 recent patents = +5, 4-10 = +10, 11+ = +15
                    if recent_count >= 11:
                        patent_boost = 15
                        logger.debug(f"{ticker}: Patent boost +15 ({recent_count} recent patents)")
                    elif recent_count >= 4:
                        patent_boost = 10
                        logger.debug(f"{ticker}: Patent boost +10 ({recent_count} recent patents)")
                    elif recent_count >= 1:
                        patent_boost = 5
                        logger.debug(f"{ticker}: Patent boost +5 ({recent_count} recent patents)")

            except Exception as e:
                logger.debug(f"Failed to check patents for {ticker}: {e}")

        # Google Trends retail momentum boost
        retail_boost = 0
        if ticker:
            try:
                from src.intelligence.google_trends import calculate_retail_momentum_score

                retail_score = calculate_retail_momentum_score(ticker)
                if retail_score >= 15:
                    retail_boost = 10
                    logger.debug(f"{ticker}: Retail momentum boost +10 (Google Trends: {retail_score})")
                elif retail_score >= 10:
                    retail_boost = 5
                    logger.debug(f"{ticker}: Retail momentum boost +5 (Google Trends: {retail_score})")

            except Exception as e:
                logger.debug(f"Failed to check Google Trends for {ticker}: {e}")

        return min(100, base_score + patent_boost + retail_boost)

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
        social_buzz: Optional[Dict] = None,
    ) -> StoryScore:
        """
        Calculate complete story-first score.

        Args:
            ticker: Stock symbol
            news: List of news articles
            sec_data: SEC filing data
            theme_data: Theme membership from registry
            price_data: Dict with technical data (above_20, above_50, etc.)
            social_buzz: Dict with social buzz data (score, status, is_breakout)

        Returns:
            StoryScore with complete breakdown
        """
        # =====================================================
        # STORY QUALITY (50%)
        # =====================================================

        # Theme strength (40% of story quality)
        theme_tier, primary_theme, theme_freshness, role_multiplier = self.detect_theme_tier(news, ticker, theme_data)
        base_theme_strength = THEME_TIERS.get(theme_tier, {}).get('score', 0)

        # Apply supply chain role multiplier
        theme_strength = base_theme_strength * role_multiplier

        if role_multiplier != 1.0:
            logger.debug(f"{ticker}: Theme strength adjusted by role: {base_theme_strength} * {role_multiplier} = {theme_strength}")

        # Story clarity (20% of story quality)
        story_clarity = self.calculate_story_clarity(news)

        # Institutional narrative (20% of story quality)
        institutional_narrative = self.calculate_institutional_narrative(news, ticker)

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
            self.detect_catalyst(news, sec_data, ticker)

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
        # SOCIAL BUZZ (15%)
        # =====================================================

        social_buzz_score = 0
        if social_buzz:
            # Base score from social buzz data (0-100)
            base_social = social_buzz.get('score', 0)
            # Breakout bonus - viral activity
            if social_buzz.get('is_breakout', False):
                base_social = min(100, base_social + 20)
            # Status modifiers
            status = social_buzz.get('status', 'unknown')
            if status in ['hot', 'bullish', 'surging']:
                base_social = min(100, base_social + 10)
            elif status in ['bearish', 'declining']:
                base_social = max(0, base_social - 10)
            social_buzz_score = base_social

        # =====================================================
        # FINAL SCORE
        # =====================================================

        total_score = (
            story_quality_score * self.STORY_QUALITY_WEIGHT +
            catalyst_score * self.CATALYST_WEIGHT +
            social_buzz_score * self.SOCIAL_BUZZ_WEIGHT +
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
            social_buzz_score=social_buzz_score,
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
    social_buzz: Optional[Dict] = None,
) -> StoryScore:
    """Convenience function to calculate story score"""
    return get_story_scorer().calculate_story_score(
        ticker, news, sec_data, theme_data, price_data, social_buzz
    )
