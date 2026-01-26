"""
Theme Registry - Unified theme storage with learned membership

Provides:
- Core theme templates (minimal hardcoding - just names and keywords)
- Learned membership, roles, and stages stored separately
- Dynamic theme discovery integration
- Self-health monitoring
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

from utils import get_logger

logger = get_logger(__name__)


class ThemeStage(Enum):
    """Theme lifecycle stages"""
    EMERGING = "emerging"      # Just discovered, high uncertainty
    EARLY = "early"            # Confirmed, building momentum
    MIDDLE = "middle"          # Peak attention, crowded
    LATE = "late"              # Momentum fading
    EXHAUSTED = "exhausted"    # Thesis played out
    RETIRED = "retired"        # No longer relevant


class MemberRole(Enum):
    """Stock roles within a theme"""
    DRIVER = "driver"              # Leaders that move first
    BENEFICIARY = "beneficiary"    # Direct beneficiaries
    PICKS_SHOVELS = "picks_shovels"  # Infrastructure/suppliers
    PERIPHERAL = "peripheral"      # Loosely related


@dataclass
class ThemeMember:
    """A stock's membership in a theme"""
    ticker: str
    role: MemberRole
    confidence: float              # 0-1, how confident we are in membership
    source: str                    # 'manual', 'correlation', 'deepseek', 'news'
    added_at: str                  # ISO timestamp
    last_validated: str            # ISO timestamp
    correlation_to_drivers: float  # Rolling correlation
    lead_lag_days: float           # Positive = lags drivers
    validation_count: int = 0      # How many times validated
    invalidation_count: int = 0    # How many times failed validation

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['role'] = self.role.value
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'ThemeMember':
        data['role'] = MemberRole(data['role'])
        return cls(**data)


@dataclass
class ThemeTemplate:
    """Core theme definition - minimal hardcoding"""
    id: str
    name: str
    category: str                  # 'sector', 'technology', 'event', 'macro'
    keywords: List[str]            # For news matching
    description: str
    parent_theme: Optional[str] = None  # For sub-themes

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LearnedTheme:
    """Complete learned theme with members and metrics"""
    template: ThemeTemplate
    stage: ThemeStage
    members: Dict[str, ThemeMember]  # ticker -> membership

    # Discovery info
    discovered_at: str
    discovery_method: str          # 'manual', 'correlation', 'news_cluster', 'deepseek'

    # Performance metrics
    heat_score: float = 0.0        # Current theme heat
    avg_return_7d: float = 0.0     # Theme avg return last 7 days
    news_velocity: float = 0.0     # News mentions per day
    social_velocity: float = 0.0   # Social mentions per day

    # Stage tracking
    stage_history: List[Dict] = field(default_factory=list)
    stage_changed_at: str = ""

    # Validation
    last_validated: str = ""
    validation_score: float = 1.0  # Health of the theme

    def to_dict(self) -> Dict:
        return {
            'template': self.template.to_dict(),
            'stage': self.stage.value,
            'members': {k: v.to_dict() for k, v in self.members.items()},
            'discovered_at': self.discovered_at,
            'discovery_method': self.discovery_method,
            'heat_score': self.heat_score,
            'avg_return_7d': self.avg_return_7d,
            'news_velocity': self.news_velocity,
            'social_velocity': self.social_velocity,
            'stage_history': self.stage_history,
            'stage_changed_at': self.stage_changed_at,
            'last_validated': self.last_validated,
            'validation_score': self.validation_score,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'LearnedTheme':
        return cls(
            template=ThemeTemplate(**data['template']),
            stage=ThemeStage(data['stage']),
            members={k: ThemeMember.from_dict(v) for k, v in data['members'].items()},
            discovered_at=data['discovered_at'],
            discovery_method=data['discovery_method'],
            heat_score=data.get('heat_score', 0.0),
            avg_return_7d=data.get('avg_return_7d', 0.0),
            news_velocity=data.get('news_velocity', 0.0),
            social_velocity=data.get('social_velocity', 0.0),
            stage_history=data.get('stage_history', []),
            stage_changed_at=data.get('stage_changed_at', ''),
            last_validated=data.get('last_validated', ''),
            validation_score=data.get('validation_score', 1.0),
        )

    def get_drivers(self) -> List[str]:
        """Get all driver tickers"""
        return [t for t, m in self.members.items() if m.role == MemberRole.DRIVER]

    def get_all_tickers(self) -> List[str]:
        """Get all member tickers"""
        return list(self.members.keys())

    def get_by_role(self, role: MemberRole) -> List[str]:
        """Get tickers by role"""
        return [t for t, m in self.members.items() if m.role == role]


# =============================================================================
# CORE THEME TEMPLATES
# These are minimal - just names, categories, and keywords
# Actual membership is LEARNED and stored separately
# =============================================================================

CORE_THEME_TEMPLATES = {
    # Technology themes
    'ai_infrastructure': ThemeTemplate(
        id='ai_infrastructure',
        name='AI Infrastructure',
        category='technology',
        keywords=['artificial intelligence', 'AI', 'machine learning', 'GPU', 'data center', 'chips'],
        description='Companies building AI compute, chips, and data center infrastructure'
    ),
    'ai_software': ThemeTemplate(
        id='ai_software',
        name='AI Software & Applications',
        category='technology',
        keywords=['AI software', 'generative AI', 'chatbot', 'copilot', 'AI agent'],
        description='Companies developing AI software and applications'
    ),
    'cybersecurity': ThemeTemplate(
        id='cybersecurity',
        name='Cybersecurity',
        category='technology',
        keywords=['cybersecurity', 'security', 'ransomware', 'breach', 'zero trust'],
        description='Cybersecurity software and services companies'
    ),
    'cloud_computing': ThemeTemplate(
        id='cloud_computing',
        name='Cloud Computing',
        category='technology',
        keywords=['cloud', 'AWS', 'Azure', 'GCP', 'SaaS', 'IaaS'],
        description='Cloud infrastructure and software providers'
    ),
    'quantum_computing': ThemeTemplate(
        id='quantum_computing',
        name='Quantum Computing',
        category='technology',
        keywords=['quantum', 'qubit', 'quantum supremacy', 'quantum computing'],
        description='Quantum computing hardware and software'
    ),

    # Energy themes
    'nuclear_power': ThemeTemplate(
        id='nuclear_power',
        name='Nuclear Power Renaissance',
        category='energy',
        keywords=['nuclear', 'uranium', 'SMR', 'nuclear reactor', 'fission'],
        description='Nuclear power and uranium companies'
    ),
    'ai_power': ThemeTemplate(
        id='ai_power',
        name='AI Power Infrastructure',
        category='energy',
        keywords=['power demand', 'data center power', 'grid', 'utilities', 'electricity'],
        description='Power infrastructure for AI/data centers'
    ),
    'clean_energy': ThemeTemplate(
        id='clean_energy',
        name='Clean Energy',
        category='energy',
        keywords=['solar', 'wind', 'renewable', 'clean energy', 'EV', 'battery'],
        description='Renewable energy and clean technology'
    ),

    # Sector themes
    'defense': ThemeTemplate(
        id='defense',
        name='Defense & Aerospace',
        category='sector',
        keywords=['defense', 'military', 'aerospace', 'weapons', 'drones', 'NATO'],
        description='Defense contractors and aerospace companies'
    ),
    'biotech': ThemeTemplate(
        id='biotech',
        name='Biotechnology',
        category='sector',
        keywords=['biotech', 'drug', 'FDA', 'clinical trial', 'pharma', 'GLP-1'],
        description='Biotechnology and pharmaceutical companies'
    ),
    'fintech': ThemeTemplate(
        id='fintech',
        name='Fintech & Payments',
        category='sector',
        keywords=['fintech', 'payments', 'digital banking', 'crypto', 'blockchain'],
        description='Financial technology and digital payments'
    ),
    'real_estate': ThemeTemplate(
        id='real_estate',
        name='Real Estate & REITs',
        category='sector',
        keywords=['real estate', 'REIT', 'housing', 'commercial real estate', 'data center REIT'],
        description='Real estate and REIT companies'
    ),

    # Event-driven themes
    'earnings_momentum': ThemeTemplate(
        id='earnings_momentum',
        name='Earnings Momentum',
        category='event',
        keywords=['earnings beat', 'guidance raise', 'revenue growth', 'EPS surprise'],
        description='Stocks with strong earnings momentum'
    ),
    'short_squeeze': ThemeTemplate(
        id='short_squeeze',
        name='Short Squeeze Candidates',
        category='event',
        keywords=['short squeeze', 'high short interest', 'gamma squeeze'],
        description='Stocks with short squeeze potential'
    ),

    # Macro themes
    'rate_sensitive': ThemeTemplate(
        id='rate_sensitive',
        name='Rate Sensitive',
        category='macro',
        keywords=['interest rate', 'Fed', 'rate cut', 'rate hike', 'treasury'],
        description='Stocks sensitive to interest rate changes'
    ),
    'inflation_hedge': ThemeTemplate(
        id='inflation_hedge',
        name='Inflation Hedge',
        category='macro',
        keywords=['inflation', 'commodity', 'gold', 'silver', 'oil'],
        description='Stocks that benefit from inflation'
    ),
    'china_trade': ThemeTemplate(
        id='china_trade',
        name='China Trade',
        category='macro',
        keywords=['China', 'tariff', 'trade war', 'reshoring', 'supply chain'],
        description='Stocks affected by China trade dynamics'
    ),
}


@dataclass
class RegistryHealth:
    """Health status of the theme registry"""
    total_themes: int
    active_themes: int  # Non-retired
    total_members: int
    avg_members_per_theme: float
    themes_without_drivers: List[str]
    stale_themes: List[str]  # Not validated in 7+ days
    low_confidence_members: int  # Confidence < 0.5
    discovered_themes: int  # Non-manual themes
    last_updated: str
    health_score: float  # 0-100


class ThemeRegistry:
    """
    Unified theme registry with learned membership

    Key principles:
    1. Core templates are minimal - just names and keywords
    2. All membership is LEARNED and stored in JSON
    3. Roles are determined by correlation/lead-lag analysis
    4. Stages are detected from news/social signals
    5. Regular validation prunes stale memberships
    """

    def __init__(self, data_dir: str = "theme_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.themes_file = self.data_dir / "learned_themes.json"
        self.history_file = self.data_dir / "theme_history.json"

        # Core templates (minimal hardcoding)
        self.templates = CORE_THEME_TEMPLATES.copy()

        # Learned themes (loaded from JSON)
        self.themes: Dict[str, LearnedTheme] = {}

        # Ticker -> theme lookup for fast access
        self._ticker_index: Dict[str, Set[str]] = {}

        # Load saved state
        self._load()

    def _load(self):
        """Load learned themes from JSON"""
        if self.themes_file.exists():
            try:
                with open(self.themes_file, 'r') as f:
                    data = json.load(f)

                for theme_id, theme_data in data.get('themes', {}).items():
                    self.themes[theme_id] = LearnedTheme.from_dict(theme_data)

                self._rebuild_index()
                logger.info(f"Loaded {len(self.themes)} themes from registry")

            except Exception as e:
                logger.error(f"Error loading themes: {e}")
                self._initialize_from_templates()
        else:
            self._initialize_from_templates()

    def _initialize_from_templates(self):
        """Initialize themes from core templates"""
        now = datetime.now().isoformat()

        for template_id, template in self.templates.items():
            self.themes[template_id] = LearnedTheme(
                template=template,
                stage=ThemeStage.EARLY,
                members={},
                discovered_at=now,
                discovery_method='manual',
            )

        self._save()
        logger.info(f"Initialized {len(self.themes)} themes from templates")

    def _save(self):
        """Save learned themes to JSON"""
        try:
            data = {
                'version': '2.0',
                'updated_at': datetime.now().isoformat(),
                'themes': {k: v.to_dict() for k, v in self.themes.items()},
            }

            with open(self.themes_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving themes: {e}")

    def _rebuild_index(self):
        """Rebuild ticker -> theme index"""
        self._ticker_index.clear()

        for theme_id, theme in self.themes.items():
            for ticker in theme.members.keys():
                if ticker not in self._ticker_index:
                    self._ticker_index[ticker] = set()
                self._ticker_index[ticker].add(theme_id)

    # =========================================================================
    # Theme Management
    # =========================================================================

    def add_template(self, template: ThemeTemplate) -> bool:
        """Add a new theme template"""
        if template.id in self.templates:
            logger.warning(f"Template {template.id} already exists")
            return False

        self.templates[template.id] = template

        # Create learned theme
        self.themes[template.id] = LearnedTheme(
            template=template,
            stage=ThemeStage.EMERGING,
            members={},
            discovered_at=datetime.now().isoformat(),
            discovery_method='manual',
        )

        self._save()
        return True

    def add_discovered_theme(
        self,
        theme_id: str,
        name: str,
        category: str,
        keywords: List[str],
        description: str,
        discovery_method: str,
        initial_members: Optional[Dict[str, Dict]] = None,
    ) -> LearnedTheme:
        """Add a theme discovered by the learning system"""
        template = ThemeTemplate(
            id=theme_id,
            name=name,
            category=category,
            keywords=keywords,
            description=description,
        )

        self.templates[theme_id] = template

        now = datetime.now().isoformat()
        theme = LearnedTheme(
            template=template,
            stage=ThemeStage.EMERGING,
            members={},
            discovered_at=now,
            discovery_method=discovery_method,
        )

        # Add initial members if provided
        if initial_members:
            for ticker, member_data in initial_members.items():
                member = ThemeMember(
                    ticker=ticker,
                    role=MemberRole(member_data.get('role', 'beneficiary')),
                    confidence=member_data.get('confidence', 0.7),
                    source=discovery_method,
                    added_at=now,
                    last_validated=now,
                    correlation_to_drivers=member_data.get('correlation', 0.5),
                    lead_lag_days=member_data.get('lag', 0.0),
                )
                theme.members[ticker] = member

        self.themes[theme_id] = theme
        self._rebuild_index()
        self._save()

        logger.info(f"Added discovered theme: {name} with {len(theme.members)} members")
        return theme

    def get_theme(self, theme_id: str) -> Optional[LearnedTheme]:
        """Get a theme by ID"""
        return self.themes.get(theme_id)

    def get_active_themes(self) -> List[LearnedTheme]:
        """Get all non-retired themes"""
        return [t for t in self.themes.values() if t.stage != ThemeStage.RETIRED]

    def get_themes_by_stage(self, stage: ThemeStage) -> List[LearnedTheme]:
        """Get themes in a specific stage"""
        return [t for t in self.themes.values() if t.stage == stage]

    def get_themes_by_category(self, category: str) -> List[LearnedTheme]:
        """Get themes in a category"""
        return [t for t in self.themes.values() if t.template.category == category]

    # =========================================================================
    # Membership Management
    # =========================================================================

    def add_member(
        self,
        theme_id: str,
        ticker: str,
        role: str,
        confidence: float,
        source: str,
        correlation: float = 0.0,
        lag: float = 0.0,
    ) -> bool:
        """Add a member to a theme"""
        if theme_id not in self.themes:
            logger.error(f"Theme {theme_id} not found")
            return False

        now = datetime.now().isoformat()
        member = ThemeMember(
            ticker=ticker,
            role=MemberRole(role),
            confidence=confidence,
            source=source,
            added_at=now,
            last_validated=now,
            correlation_to_drivers=correlation,
            lead_lag_days=lag,
        )

        self.themes[theme_id].members[ticker] = member

        # Update index
        if ticker not in self._ticker_index:
            self._ticker_index[ticker] = set()
        self._ticker_index[ticker].add(theme_id)

        self._save()
        return True

    def update_member(
        self,
        theme_id: str,
        ticker: str,
        **updates,
    ) -> bool:
        """Update member attributes"""
        if theme_id not in self.themes:
            return False

        if ticker not in self.themes[theme_id].members:
            return False

        member = self.themes[theme_id].members[ticker]

        for key, value in updates.items():
            if key == 'role' and isinstance(value, str):
                value = MemberRole(value)
            if hasattr(member, key):
                setattr(member, key, value)

        member.last_validated = datetime.now().isoformat()
        self._save()
        return True

    def remove_member(self, theme_id: str, ticker: str) -> bool:
        """Remove a member from a theme"""
        if theme_id not in self.themes:
            return False

        if ticker in self.themes[theme_id].members:
            del self.themes[theme_id].members[ticker]

            # Update index
            if ticker in self._ticker_index:
                self._ticker_index[ticker].discard(theme_id)
                if not self._ticker_index[ticker]:
                    del self._ticker_index[ticker]

            self._save()
            return True

        return False

    def validate_member(
        self,
        theme_id: str,
        ticker: str,
        is_valid: bool,
        new_correlation: Optional[float] = None,
        new_lag: Optional[float] = None,
    ):
        """Record validation result for a member"""
        if theme_id not in self.themes:
            return

        if ticker not in self.themes[theme_id].members:
            return

        member = self.themes[theme_id].members[ticker]

        if is_valid:
            member.validation_count += 1
            if new_correlation is not None:
                # Exponential moving average
                member.correlation_to_drivers = 0.7 * member.correlation_to_drivers + 0.3 * new_correlation
            if new_lag is not None:
                member.lead_lag_days = 0.7 * member.lead_lag_days + 0.3 * new_lag

            # Increase confidence
            member.confidence = min(1.0, member.confidence + 0.05)
        else:
            member.invalidation_count += 1
            # Decrease confidence
            member.confidence = max(0.0, member.confidence - 0.1)

        member.last_validated = datetime.now().isoformat()

        # Remove if confidence too low
        if member.confidence < 0.2 or member.invalidation_count > member.validation_count + 5:
            self.remove_member(theme_id, ticker)
            logger.info(f"Removed {ticker} from {theme_id} due to low confidence")
        else:
            self._save()

    # =========================================================================
    # Lookups
    # =========================================================================

    def get_themes_for_ticker(self, ticker: str) -> List[Dict]:
        """Get all themes a ticker belongs to"""
        result = []

        theme_ids = self._ticker_index.get(ticker, set())
        for theme_id in theme_ids:
            theme = self.themes.get(theme_id)
            if theme and ticker in theme.members:
                member = theme.members[ticker]
                result.append({
                    'theme_id': theme_id,
                    'theme_name': theme.template.name,
                    'role': member.role.value,
                    'stage': theme.stage.value,
                    'confidence': member.confidence,
                    'correlation': member.correlation_to_drivers,
                    'lag_days': member.lead_lag_days,
                    'heat_score': theme.heat_score,
                })

        return result

    def get_theme_tickers(self, theme_id: str) -> Dict[str, str]:
        """Get all tickers in a theme with their roles"""
        if theme_id not in self.themes:
            return {}

        return {
            ticker: member.role.value
            for ticker, member in self.themes[theme_id].members.items()
        }

    def get_drivers(self, theme_id: str) -> List[str]:
        """Get driver tickers for a theme"""
        if theme_id not in self.themes:
            return []

        return self.themes[theme_id].get_drivers()

    def get_all_theme_tickers(self) -> Set[str]:
        """Get all tickers across all themes"""
        return set(self._ticker_index.keys())

    # =========================================================================
    # Stage Management
    # =========================================================================

    def update_stage(self, theme_id: str, new_stage: ThemeStage, reason: str = ""):
        """Update theme lifecycle stage"""
        if theme_id not in self.themes:
            return

        theme = self.themes[theme_id]
        old_stage = theme.stage

        if old_stage == new_stage:
            return

        now = datetime.now().isoformat()

        # Record history
        theme.stage_history.append({
            'from': old_stage.value,
            'to': new_stage.value,
            'at': now,
            'reason': reason,
        })

        theme.stage = new_stage
        theme.stage_changed_at = now

        self._save()
        logger.info(f"Theme {theme_id} stage: {old_stage.value} -> {new_stage.value}")

    def update_metrics(
        self,
        theme_id: str,
        heat_score: Optional[float] = None,
        avg_return: Optional[float] = None,
        news_velocity: Optional[float] = None,
        social_velocity: Optional[float] = None,
    ):
        """Update theme performance metrics"""
        if theme_id not in self.themes:
            return

        theme = self.themes[theme_id]

        if heat_score is not None:
            theme.heat_score = heat_score
        if avg_return is not None:
            theme.avg_return_7d = avg_return
        if news_velocity is not None:
            theme.news_velocity = news_velocity
        if social_velocity is not None:
            theme.social_velocity = social_velocity

        theme.last_validated = datetime.now().isoformat()
        self._save()

    # =========================================================================
    # Keywords & Matching
    # =========================================================================

    def match_keywords(self, text: str) -> List[Tuple[str, float]]:
        """Find themes matching keywords in text"""
        text_lower = text.lower()
        matches = []

        for theme_id, theme in self.themes.items():
            if theme.stage == ThemeStage.RETIRED:
                continue

            # Count keyword matches
            match_count = 0
            for keyword in theme.template.keywords:
                if keyword.lower() in text_lower:
                    match_count += 1

            if match_count > 0:
                # Normalize by number of keywords
                score = match_count / len(theme.template.keywords)
                matches.append((theme_id, score))

        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    # =========================================================================
    # Health Check
    # =========================================================================

    def run_health_check(self) -> RegistryHealth:
        """Comprehensive health check"""
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        active_themes = [t for t in self.themes.values() if t.stage != ThemeStage.RETIRED]

        # Find themes without drivers
        themes_without_drivers = [
            t.template.id for t in active_themes
            if not t.get_drivers()
        ]

        # Find stale themes
        stale_themes = []
        for theme in active_themes:
            if theme.last_validated:
                last_val = datetime.fromisoformat(theme.last_validated)
                if last_val < week_ago:
                    stale_themes.append(theme.template.id)
            else:
                stale_themes.append(theme.template.id)

        # Count low confidence members
        low_confidence = 0
        total_members = 0
        for theme in active_themes:
            for member in theme.members.values():
                total_members += 1
                if member.confidence < 0.5:
                    low_confidence += 1

        # Count discovered themes
        discovered = len([t for t in self.themes.values() if t.discovery_method != 'manual'])

        # Calculate health score
        health_score = 100.0

        # Penalize for issues (less harsh for new installations)
        if themes_without_drivers:
            # Only penalize if we have some themes with members
            if total_members > 0:
                health_score -= min(len(themes_without_drivers) * 3, 20)
        if stale_themes:
            # Only penalize if themes have been validated before
            validated_themes = [t for t in stale_themes if any(th.last_validated for th in active_themes if th.template.id == t)]
            health_score -= len(validated_themes) * 2
        if total_members > 0 and low_confidence / total_members > 0.3:
            health_score -= 10

        # Bonus for having members
        if total_members > 0:
            health_score = min(100, health_score + 20)

        health_score = max(0, min(100, health_score))

        avg_members = total_members / len(active_themes) if active_themes else 0

        return RegistryHealth(
            total_themes=len(self.themes),
            active_themes=len(active_themes),
            total_members=total_members,
            avg_members_per_theme=round(avg_members, 1),
            themes_without_drivers=themes_without_drivers,
            stale_themes=stale_themes,
            low_confidence_members=low_confidence,
            discovered_themes=discovered,
            last_updated=datetime.now().isoformat(),
            health_score=health_score,
        )

    # =========================================================================
    # Export for Story Scorer
    # =========================================================================

    def get_theme_membership_for_scoring(self, ticker: str) -> List[Dict]:
        """
        Get theme membership formatted for story_scorer.py
        Returns format compatible with existing scoring logic
        """
        themes = self.get_themes_for_ticker(ticker)

        result = []
        for theme in themes:
            # Skip very low confidence
            if theme['confidence'] < 0.3:
                continue

            result.append({
                'theme_id': theme['theme_id'],
                'theme_name': theme['theme_name'],
                'role': theme['role'],
                'stage': theme['stage'],
                'confidence': theme['confidence'],
                'is_learned': True,
            })

        return result

    def get_summary(self) -> Dict:
        """Get registry summary for API/dashboard"""
        health = self.run_health_check()

        themes_by_stage = {}
        for stage in ThemeStage:
            themes_by_stage[stage.value] = len(self.get_themes_by_stage(stage))

        hot_themes = sorted(
            self.get_active_themes(),
            key=lambda t: t.heat_score,
            reverse=True,
        )[:5]

        return {
            'health': asdict(health),
            'themes_by_stage': themes_by_stage,
            'hot_themes': [
                {
                    'id': t.template.id,
                    'name': t.template.name,
                    'heat': t.heat_score,
                    'stage': t.stage.value,
                    'members': len(t.members),
                }
                for t in hot_themes
            ],
            'total_tracked_tickers': len(self._ticker_index),
        }


# Singleton instance
_registry = None


def get_registry() -> ThemeRegistry:
    """Get the global theme registry instance"""
    global _registry
    if _registry is None:
        _registry = ThemeRegistry()
    return _registry


# Convenience functions
def get_themes_for_ticker(ticker: str) -> List[Dict]:
    """Get all themes a ticker belongs to"""
    return get_registry().get_themes_for_ticker(ticker)


def get_theme_membership_for_scoring(ticker: str) -> List[Dict]:
    """Get theme membership for story scorer"""
    return get_registry().get_theme_membership_for_scoring(ticker)


def get_all_theme_tickers() -> Set[str]:
    """Get all tickers in any theme"""
    return get_registry().get_all_theme_tickers()


def run_health_check() -> RegistryHealth:
    """Run registry health check"""
    return get_registry().run_health_check()
