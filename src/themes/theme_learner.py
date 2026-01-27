"""
Theme Learner - AI-enhanced theme discovery and membership learning

Provides:
- Correlation-based member discovery
- Lead-lag relationship analysis for role classification
- News clustering for emerging theme detection
- DeepSeek integration for intelligent analysis
- Continuous validation and pruning
"""

import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
from pathlib import Path
import numpy as np

from utils import get_logger
from theme_registry import (
    ThemeRegistry, get_registry, ThemeStage, MemberRole,
    ThemeMember, LearnedTheme
)

logger = get_logger(__name__)


@dataclass
class CorrelationResult:
    """Result of correlation analysis between two stocks"""
    ticker1: str
    ticker2: str
    correlation: float
    optimal_lag: int  # Days ticker2 lags ticker1
    lag_correlation: float  # Correlation at optimal lag
    p_value: float
    is_significant: bool

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ThemeHypothesis:
    """A hypothesized new theme from learning"""
    id: str
    name: str
    category: str
    keywords: List[str]
    description: str
    discovery_method: str
    confidence: float
    evidence: List[str]
    candidate_members: Dict[str, Dict]  # ticker -> {role, confidence}
    created_at: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LearnerHealth:
    """Health status of the theme learner"""
    last_correlation_run: str
    last_news_scan: str
    last_validation_run: str
    themes_discovered_30d: int
    members_added_30d: int
    members_removed_30d: int
    avg_correlation_quality: float
    deepseek_available: bool
    health_score: float


class ThemeLearner:
    """
    AI-enhanced theme learning system

    Key capabilities:
    1. Correlation clustering - find stocks moving together
    2. Lead-lag analysis - determine driver vs beneficiary roles
    3. News clustering - discover emerging themes from news
    4. DeepSeek integration - intelligent naming, roles, stages
    5. Continuous validation - prune stale memberships
    """

    def __init__(self, registry: Optional[ThemeRegistry] = None):
        self.registry = registry or get_registry()

        self.data_dir = Path("theme_data")
        self.data_dir.mkdir(exist_ok=True)

        self.learning_log_file = self.data_dir / "learning_log.json"
        self.hypotheses_file = self.data_dir / "theme_hypotheses.json"

        # Learning state
        self.correlation_cache: Dict[Tuple[str, str], CorrelationResult] = {}
        self.hypotheses: List[ThemeHypothesis] = []

        # Metrics
        self.stats = {
            'correlations_computed': 0,
            'themes_discovered': 0,
            'members_added': 0,
            'members_removed': 0,
            'last_correlation_run': None,
            'last_news_scan': None,
            'last_validation_run': None,
        }

        # Try to import optional dependencies
        self._deepseek = None
        self._has_sklearn = False

        try:
            from deepseek_intelligence import get_deepseek_intelligence
            self._deepseek = get_deepseek_intelligence()
        except ImportError:
            logger.warning("DeepSeek intelligence not available")

        try:
            from sklearn.cluster import DBSCAN
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._has_sklearn = True
        except ImportError:
            logger.warning("sklearn not available for clustering")

    # =========================================================================
    # Correlation Analysis
    # =========================================================================

    def calculate_correlation(
        self,
        returns1: List[float],
        returns2: List[float],
        max_lag: int = 5,
    ) -> Optional[CorrelationResult]:
        """
        Calculate correlation and optimal lag between two return series

        Args:
            returns1: Daily returns for stock 1
            returns2: Daily returns for stock 2
            max_lag: Maximum lag to test (days)

        Returns:
            CorrelationResult with correlation, optimal lag, significance
        """
        if len(returns1) < 20 or len(returns2) < 20:
            return None

        # Align lengths
        min_len = min(len(returns1), len(returns2))
        r1 = np.array(returns1[-min_len:])
        r2 = np.array(returns2[-min_len:])

        # Handle NaN/Inf
        r1 = np.nan_to_num(r1, nan=0.0, posinf=0.0, neginf=0.0)
        r2 = np.nan_to_num(r2, nan=0.0, posinf=0.0, neginf=0.0)

        # Calculate base correlation
        try:
            base_corr = np.corrcoef(r1, r2)[0, 1]
        except:
            return None

        if np.isnan(base_corr):
            return None

        # Test different lags
        best_lag = 0
        best_lag_corr = base_corr

        for lag in range(-max_lag, max_lag + 1):
            if lag == 0:
                continue

            try:
                if lag > 0:
                    # r2 lags r1
                    corr = np.corrcoef(r1[:-lag], r2[lag:])[0, 1]
                else:
                    # r1 lags r2
                    corr = np.corrcoef(r1[-lag:], r2[:lag])[0, 1]

                if not np.isnan(corr) and abs(corr) > abs(best_lag_corr):
                    best_lag = lag
                    best_lag_corr = corr
            except:
                continue

        # Statistical significance (Fisher z-transform)
        n = len(r1) - abs(best_lag)
        if n < 10:
            return None

        try:
            z = 0.5 * np.log((1 + abs(best_lag_corr)) / (1 - abs(best_lag_corr) + 1e-10))
            se = 1 / np.sqrt(n - 3)
            z_score = z / se

            # Two-tailed p-value approximation
            from scipy import stats
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        except:
            p_value = 0.5  # Assume not significant if can't calculate

        is_significant = p_value < 0.05 and abs(best_lag_corr) > 0.3

        self.stats['correlations_computed'] += 1

        return CorrelationResult(
            ticker1="",  # Will be filled by caller
            ticker2="",
            correlation=round(base_corr, 4),
            optimal_lag=best_lag,
            lag_correlation=round(best_lag_corr, 4),
            p_value=round(p_value, 6),
            is_significant=is_significant,
        )

    async def analyze_correlations_for_theme(
        self,
        theme_id: str,
        price_data: Dict[str, List[float]],
        min_correlation: float = 0.5,
    ) -> List[CorrelationResult]:
        """
        Analyze correlations within a theme and with potential new members

        Args:
            theme_id: Theme to analyze
            price_data: Dict of ticker -> daily returns
            min_correlation: Minimum correlation to consider

        Returns:
            List of significant correlations
        """
        theme = self.registry.get_theme(theme_id)
        if not theme:
            return []

        drivers = theme.get_drivers()
        if not drivers:
            # Use highest confidence members as pseudo-drivers
            sorted_members = sorted(
                theme.members.items(),
                key=lambda x: x[1].confidence,
                reverse=True,
            )
            drivers = [m[0] for m in sorted_members[:3]]

        results = []

        # Calculate correlations between all members and drivers
        for ticker, returns in price_data.items():
            if ticker in drivers:
                continue

            for driver in drivers:
                if driver not in price_data:
                    continue

                cache_key = (driver, ticker)

                if cache_key in self.correlation_cache:
                    result = self.correlation_cache[cache_key]
                else:
                    result = self.calculate_correlation(
                        price_data[driver],
                        returns,
                    )

                    if result:
                        result.ticker1 = driver
                        result.ticker2 = ticker
                        self.correlation_cache[cache_key] = result

                if result and result.is_significant and abs(result.lag_correlation) >= min_correlation:
                    results.append(result)

        self.stats['last_correlation_run'] = datetime.now().isoformat()

        return results

    async def discover_members_from_correlation(
        self,
        theme_id: str,
        candidate_tickers: List[str],
        price_data: Dict[str, List[float]],
        min_correlation: float = 0.5,
    ) -> List[Dict]:
        """
        Discover new theme members from correlation analysis

        Args:
            theme_id: Theme to add members to
            candidate_tickers: Tickers to evaluate
            price_data: Dict of ticker -> daily returns
            min_correlation: Minimum correlation threshold

        Returns:
            List of discovered members with roles
        """
        theme = self.registry.get_theme(theme_id)
        if not theme:
            return []

        drivers = theme.get_drivers()
        discovered = []

        for ticker in candidate_tickers:
            if ticker in theme.members:
                continue

            if ticker not in price_data:
                continue

            # Check correlation with drivers
            best_corr = None

            for driver in drivers:
                if driver not in price_data:
                    continue

                result = self.calculate_correlation(
                    price_data[driver],
                    price_data[ticker],
                )

                if result and result.is_significant:
                    result.ticker1 = driver
                    result.ticker2 = ticker

                    if not best_corr or abs(result.lag_correlation) > abs(best_corr.lag_correlation):
                        best_corr = result

            if best_corr and abs(best_corr.lag_correlation) >= min_correlation:
                # Determine role from lag
                if best_corr.optimal_lag <= 0:
                    # Moves with or before driver
                    role = 'driver' if best_corr.optimal_lag < -1 else 'beneficiary'
                elif best_corr.optimal_lag <= 2:
                    role = 'beneficiary'
                else:
                    role = 'peripheral'

                # Calculate confidence from correlation strength
                confidence = min(0.95, abs(best_corr.lag_correlation))

                discovered.append({
                    'ticker': ticker,
                    'role': role,
                    'confidence': round(confidence, 3),
                    'correlation': best_corr.lag_correlation,
                    'lag_days': best_corr.optimal_lag,
                    'correlated_with': best_corr.ticker1,
                })

        return discovered

    # =========================================================================
    # Role Classification
    # =========================================================================

    def classify_role_from_lead_lag(
        self,
        lag_days: float,
        correlation: float,
        is_supplier: bool = False,
    ) -> str:
        """
        Classify member role from lead-lag relationship

        Args:
            lag_days: How many days the stock lags drivers (negative = leads)
            correlation: Correlation with drivers
            is_supplier: Whether known to be a supplier

        Returns:
            Role string
        """
        if is_supplier:
            return 'picks_shovels'

        if lag_days < -1:
            # Leads drivers - likely a driver itself
            return 'driver'
        elif lag_days <= 0.5:
            # Moves with drivers - direct beneficiary
            return 'beneficiary'
        elif lag_days <= 3:
            # Slightly lags - still beneficiary but tier 2
            return 'beneficiary'
        else:
            # Significantly lags - peripheral
            return 'peripheral'

    async def classify_role_with_ai(
        self,
        ticker: str,
        theme_id: str,
        lead_lag_days: float,
        correlation: float,
        company_description: Optional[str] = None,
    ) -> Dict:
        """
        Use DeepSeek to classify member role with reasoning

        Args:
            ticker: Stock ticker
            theme_id: Theme ID
            lead_lag_days: Lead-lag relationship
            correlation: Correlation with drivers
            company_description: Optional company description

        Returns:
            Dict with role, confidence, reasoning
        """
        if not self._deepseek:
            # Fallback to rule-based
            role = self.classify_role_from_lead_lag(lead_lag_days, correlation)
            return {
                'role': role,
                'confidence': abs(correlation),
                'reasoning': f"Based on lag={lead_lag_days:.1f}d, corr={correlation:.2f}",
                'source': 'rule_based',
            }

        theme = self.registry.get_theme(theme_id)
        theme_description = theme.template.description if theme else ""

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._deepseek.classify_role(
                    ticker,
                    theme_id,
                    theme_description,
                    lead_lag_days,
                ),
            )

            return {
                'role': result.get('role', 'beneficiary'),
                'confidence': result.get('confidence', 0.7),
                'reasoning': result.get('reasoning', ''),
                'source': 'deepseek',
            }
        except Exception as e:
            logger.error(f"DeepSeek role classification failed: {e}")
            role = self.classify_role_from_lead_lag(lead_lag_days, correlation)
            return {
                'role': role,
                'confidence': abs(correlation),
                'reasoning': f"Fallback: lag={lead_lag_days:.1f}d",
                'source': 'rule_based',
            }

    # =========================================================================
    # Theme Discovery from News
    # =========================================================================

    async def discover_themes_from_news(
        self,
        news_items: List[Dict],
        min_cluster_size: int = 5,
    ) -> List[ThemeHypothesis]:
        """
        Discover emerging themes from news clustering

        Args:
            news_items: List of {title, tickers, source, timestamp}
            min_cluster_size: Minimum news items to form a theme

        Returns:
            List of theme hypotheses
        """
        if not self._has_sklearn:
            logger.warning("sklearn not available for news clustering")
            return []

        if len(news_items) < min_cluster_size * 2:
            return []

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.cluster import DBSCAN

        # Prepare texts
        texts = [item.get('title', '') for item in news_items]

        # TF-IDF vectorization
        vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2),
        )

        try:
            X = vectorizer.fit_transform(texts)
        except Exception as e:
            logger.error(f"TF-IDF failed: {e}")
            return []

        # DBSCAN clustering
        clustering = DBSCAN(eps=0.5, min_samples=min_cluster_size).fit(X)

        # Extract clusters
        clusters = defaultdict(list)
        for idx, label in enumerate(clustering.labels_):
            if label >= 0:  # -1 is noise
                clusters[label].append(idx)

        hypotheses = []

        for cluster_id, indices in clusters.items():
            # Get cluster news items
            cluster_items = [news_items[i] for i in indices]
            cluster_texts = [texts[i] for i in indices]

            # Extract common keywords
            cluster_vectorizer = TfidfVectorizer(
                max_features=10,
                stop_words='english',
            )
            try:
                cluster_X = cluster_vectorizer.fit_transform(cluster_texts)
                keywords = cluster_vectorizer.get_feature_names_out().tolist()
            except:
                keywords = []

            # Extract mentioned tickers
            tickers = set()
            for item in cluster_items:
                tickers.update(item.get('tickers', []))

            # Check if matches existing theme
            existing_match = self._match_to_existing_theme(keywords)
            if existing_match:
                # This is not a new theme
                continue

            # Generate hypothesis
            hypothesis_id = f"discovered_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cluster_id}"

            # Try to name with DeepSeek
            if self._deepseek and tickers:
                try:
                    ai_result = self._deepseek.generate_theme_info(
                        list(tickers)[:10],
                        cluster_texts[:5],
                    )
                    name = ai_result.get('name', f"Emerging Theme {cluster_id}")
                    description = ai_result.get('description', '')
                    category = ai_result.get('category', 'emerging')
                except:
                    name = f"Emerging Theme: {' '.join(keywords[:3])}"
                    description = f"Stocks clustered around: {', '.join(keywords[:5])}"
                    category = 'emerging'
            else:
                name = f"Emerging Theme: {' '.join(keywords[:3])}"
                description = f"Stocks clustered around: {', '.join(keywords[:5])}"
                category = 'emerging'

            # Create candidate members
            candidate_members = {}
            for ticker in tickers:
                candidate_members[ticker] = {
                    'role': 'beneficiary',
                    'confidence': 0.6,
                }

            hypothesis = ThemeHypothesis(
                id=hypothesis_id,
                name=name,
                category=category,
                keywords=keywords,
                description=description,
                discovery_method='news_clustering',
                confidence=min(0.9, len(cluster_items) / 20),
                evidence=[item.get('title', '')[:100] for item in cluster_items[:5]],
                candidate_members=candidate_members,
                created_at=datetime.now().isoformat(),
            )

            hypotheses.append(hypothesis)

        self.hypotheses.extend(hypotheses)
        self.stats['last_news_scan'] = datetime.now().isoformat()

        # Save hypotheses
        self._save_hypotheses()

        return hypotheses

    def _match_to_existing_theme(self, keywords: List[str]) -> Optional[str]:
        """Check if keywords match an existing theme"""
        keywords_lower = set(k.lower() for k in keywords)

        for theme_id, theme in self.registry.themes.items():
            theme_keywords = set(k.lower() for k in theme.template.keywords)

            overlap = keywords_lower & theme_keywords
            if len(overlap) >= 2 or len(overlap) / len(keywords_lower) > 0.5:
                return theme_id

        return None

    async def confirm_hypothesis(
        self,
        hypothesis_id: str,
        price_data: Optional[Dict[str, List[float]]] = None,
    ) -> Optional[LearnedTheme]:
        """
        Confirm a theme hypothesis and add to registry

        Args:
            hypothesis_id: ID of hypothesis to confirm
            price_data: Optional price data for correlation analysis

        Returns:
            Created theme if confirmed
        """
        # Find hypothesis
        hypothesis = None
        for h in self.hypotheses:
            if h.id == hypothesis_id:
                hypothesis = h
                break

        if not hypothesis:
            return None

        # Add to registry
        theme = self.registry.add_discovered_theme(
            theme_id=hypothesis.id,
            name=hypothesis.name,
            category=hypothesis.category,
            keywords=hypothesis.keywords,
            description=hypothesis.description,
            discovery_method=hypothesis.discovery_method,
            initial_members=hypothesis.candidate_members,
        )

        # Remove from hypotheses
        self.hypotheses = [h for h in self.hypotheses if h.id != hypothesis_id]
        self._save_hypotheses()

        self.stats['themes_discovered'] += 1

        logger.info(f"Confirmed theme hypothesis: {hypothesis.name}")
        return theme

    # =========================================================================
    # Stage Detection
    # =========================================================================

    async def detect_theme_stage(
        self,
        theme_id: str,
        news_items: Optional[List[Dict]] = None,
        price_data: Optional[Dict[str, List[float]]] = None,
    ) -> Dict:
        """
        Detect current lifecycle stage of a theme

        Args:
            theme_id: Theme to analyze
            news_items: Recent news about the theme
            price_data: Price data for theme stocks

        Returns:
            Dict with stage, confidence, signals
        """
        theme = self.registry.get_theme(theme_id)
        if not theme:
            return {'stage': 'unknown', 'confidence': 0}

        signals = []
        stage_scores = {stage: 0.0 for stage in ThemeStage}

        # 1. Age-based signals
        discovered = datetime.fromisoformat(theme.discovered_at)
        age_days = (datetime.now() - discovered).days

        if age_days < 14:
            stage_scores[ThemeStage.EMERGING] += 0.3
            signals.append(f"Theme is {age_days} days old - still emerging")
        elif age_days < 60:
            stage_scores[ThemeStage.EARLY] += 0.2
        elif age_days < 180:
            stage_scores[ThemeStage.MIDDLE] += 0.2
        else:
            stage_scores[ThemeStage.LATE] += 0.2
            signals.append(f"Theme is {age_days} days old - may be maturing")

        # 2. News velocity signals
        if news_items:
            # Calculate news acceleration
            recent_count = len([n for n in news_items if n.get('age_hours', 0) < 24])
            older_count = len([n for n in news_items if 24 <= n.get('age_hours', 0) < 72])

            if recent_count > older_count * 1.5:
                stage_scores[ThemeStage.EARLY] += 0.3
                signals.append(f"News accelerating: {recent_count} vs {older_count}")
            elif recent_count < older_count * 0.5:
                stage_scores[ThemeStage.LATE] += 0.3
                signals.append(f"News decelerating: {recent_count} vs {older_count}")

        # 3. Price momentum signals
        if price_data:
            theme_tickers = theme.get_all_tickers()
            valid_returns = []

            for ticker in theme_tickers:
                if ticker in price_data:
                    returns = price_data[ticker]
                    if len(returns) >= 20:
                        # Calculate 20-day return
                        total_return = sum(returns[-20:])
                        valid_returns.append(total_return)

            if valid_returns:
                avg_return = np.mean(valid_returns)

                if avg_return > 0.15:  # >15% in 20 days
                    stage_scores[ThemeStage.MIDDLE] += 0.4
                    signals.append(f"Strong momentum: {avg_return:.1%} avg return")
                elif avg_return > 0.05:
                    stage_scores[ThemeStage.EARLY] += 0.3
                elif avg_return < -0.05:
                    stage_scores[ThemeStage.LATE] += 0.3
                    signals.append(f"Weakening: {avg_return:.1%} avg return")
                elif avg_return < -0.15:
                    stage_scores[ThemeStage.EXHAUSTED] += 0.4
                    signals.append(f"Exhausted: {avg_return:.1%} avg return")

        # 4. AI-based detection if available
        if self._deepseek and news_items:
            try:
                headlines = [n.get('title', '') for n in news_items[:10]]
                ai_result = self._deepseek.detect_theme_stage(
                    theme_id,
                    headlines,
                    signals,
                )

                ai_stage = ai_result.get('stage', '')
                if ai_stage:
                    try:
                        ai_stage_enum = ThemeStage(ai_stage)
                        stage_scores[ai_stage_enum] += 0.5
                        signals.append(f"AI assessment: {ai_stage}")
                    except:
                        pass
            except Exception as e:
                logger.warning(f"AI stage detection failed: {e}")

        # Determine final stage
        best_stage = max(stage_scores.items(), key=lambda x: x[1])

        result = {
            'stage': best_stage[0].value,
            'confidence': min(0.95, best_stage[1]),
            'signals': signals,
            'stage_scores': {k.value: round(v, 2) for k, v in stage_scores.items()},
        }

        # Update registry if stage changed
        if ThemeStage(result['stage']) != theme.stage and result['confidence'] > 0.6:
            self.registry.update_stage(
                theme_id,
                ThemeStage(result['stage']),
                reason='; '.join(signals[:3]),
            )

        return result

    # =========================================================================
    # Validation & Pruning
    # =========================================================================

    async def validate_memberships(
        self,
        theme_id: str,
        price_data: Dict[str, List[float]],
        min_correlation: float = 0.3,
    ) -> Dict:
        """
        Validate existing theme memberships and prune weak ones

        Args:
            theme_id: Theme to validate
            price_data: Recent price data
            min_correlation: Minimum correlation to keep membership

        Returns:
            Validation summary
        """
        theme = self.registry.get_theme(theme_id)
        if not theme:
            return {'error': 'Theme not found'}

        drivers = theme.get_drivers()
        if not drivers:
            return {'error': 'No drivers in theme'}

        validated = []
        invalidated = []

        for ticker, member in list(theme.members.items()):
            if ticker in drivers:
                # Don't validate drivers against themselves
                continue

            if ticker not in price_data:
                # Can't validate without price data
                continue

            # Calculate current correlation with drivers
            correlations = []
            for driver in drivers:
                if driver not in price_data:
                    continue

                result = self.calculate_correlation(
                    price_data[driver],
                    price_data[ticker],
                )

                if result:
                    correlations.append(result.lag_correlation)

            if not correlations:
                continue

            avg_corr = np.mean([abs(c) for c in correlations])

            if avg_corr >= min_correlation:
                self.registry.validate_member(
                    theme_id,
                    ticker,
                    is_valid=True,
                    new_correlation=avg_corr,
                )
                validated.append(ticker)
            else:
                self.registry.validate_member(
                    theme_id,
                    ticker,
                    is_valid=False,
                )
                invalidated.append(ticker)

        self.stats['last_validation_run'] = datetime.now().isoformat()
        self.stats['members_removed'] += len(invalidated)

        return {
            'theme_id': theme_id,
            'validated': len(validated),
            'invalidated': len(invalidated),
            'validated_tickers': validated,
            'invalidated_tickers': invalidated,
        }

    async def validate_all_themes(
        self,
        price_data: Dict[str, List[float]],
    ) -> Dict:
        """Validate memberships across all themes"""
        results = {}

        for theme_id in self.registry.themes.keys():
            result = await self.validate_memberships(theme_id, price_data)
            results[theme_id] = result

        total_validated = sum(r.get('validated', 0) for r in results.values())
        total_invalidated = sum(r.get('invalidated', 0) for r in results.values())

        return {
            'themes_processed': len(results),
            'total_validated': total_validated,
            'total_invalidated': total_invalidated,
            'by_theme': results,
        }

    # =========================================================================
    # Learning Cycle
    # =========================================================================

    async def run_learning_cycle(
        self,
        price_data: Dict[str, List[float]],
        news_items: Optional[List[Dict]] = None,
        candidate_tickers: Optional[List[str]] = None,
    ) -> Dict:
        """
        Run a complete learning cycle

        1. Discover new members from correlation
        2. Discover new themes from news
        3. Validate existing memberships
        4. Update theme stages

        Args:
            price_data: Dict of ticker -> daily returns
            news_items: Recent news items
            candidate_tickers: Potential new theme members

        Returns:
            Learning cycle results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'members_discovered': [],
            'themes_discovered': [],
            'validation': {},
            'stage_updates': [],
        }

        # 1. Discover new members for each active theme
        if candidate_tickers:
            for theme_id, theme in self.registry.themes.items():
                if theme.stage == ThemeStage.RETIRED:
                    continue

                discovered = await self.discover_members_from_correlation(
                    theme_id,
                    candidate_tickers,
                    price_data,
                )

                for member in discovered:
                    # Add to registry
                    success = self.registry.add_member(
                        theme_id,
                        member['ticker'],
                        member['role'],
                        member['confidence'],
                        'correlation',
                        member['correlation'],
                        member['lag_days'],
                    )

                    if success:
                        results['members_discovered'].append({
                            'theme_id': theme_id,
                            **member,
                        })
                        self.stats['members_added'] += 1

        # 2. Discover new themes from news
        if news_items:
            hypotheses = await self.discover_themes_from_news(news_items)

            for hypothesis in hypotheses:
                if hypothesis.confidence > 0.7:
                    # Auto-confirm high confidence themes
                    theme = await self.confirm_hypothesis(hypothesis.id, price_data)
                    if theme:
                        results['themes_discovered'].append({
                            'theme_id': theme.template.id,
                            'name': theme.template.name,
                            'members': len(theme.members),
                        })

        # 3. Validate existing memberships
        validation = await self.validate_all_themes(price_data)
        results['validation'] = validation

        # 4. Update theme stages
        for theme_id, theme in self.registry.themes.items():
            if theme.stage == ThemeStage.RETIRED:
                continue

            theme_news = None
            if news_items:
                # Filter news for this theme
                theme_news = [
                    n for n in news_items
                    if any(t in theme.members for t in n.get('tickers', []))
                ]

            stage_result = await self.detect_theme_stage(
                theme_id,
                theme_news,
                price_data,
            )

            if stage_result.get('confidence', 0) > 0.6:
                results['stage_updates'].append({
                    'theme_id': theme_id,
                    **stage_result,
                })

        # Log results
        self._log_learning_cycle(results)

        return results

    def _log_learning_cycle(self, results: Dict):
        """Log learning cycle results"""
        try:
            log_entry = {
                'timestamp': results['timestamp'],
                'members_discovered': len(results['members_discovered']),
                'themes_discovered': len(results['themes_discovered']),
                'members_validated': results['validation'].get('total_validated', 0),
                'members_invalidated': results['validation'].get('total_invalidated', 0),
            }

            # Append to log file
            logs = []
            if self.learning_log_file.exists():
                with open(self.learning_log_file, 'r') as f:
                    logs = json.load(f)

            logs.append(log_entry)

            # Keep last 100 entries
            logs = logs[-100:]

            with open(self.learning_log_file, 'w') as f:
                json.dump(logs, f, indent=2)

        except Exception as e:
            logger.error(f"Error logging learning cycle: {e}")

    def _save_hypotheses(self):
        """Save theme hypotheses to file"""
        try:
            data = [h.to_dict() for h in self.hypotheses]
            with open(self.hypotheses_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving hypotheses: {e}")

    # =========================================================================
    # Health Check
    # =========================================================================

    def run_health_check(self) -> LearnerHealth:
        """Run health check on the theme learner"""
        # Load recent learning logs
        themes_30d = 0
        members_added_30d = 0
        members_removed_30d = 0

        cutoff = datetime.now() - timedelta(days=30)

        if self.learning_log_file.exists():
            try:
                with open(self.learning_log_file, 'r') as f:
                    logs = json.load(f)

                for log in logs:
                    log_date = datetime.fromisoformat(log['timestamp'])
                    if log_date >= cutoff:
                        themes_30d += log.get('themes_discovered', 0)
                        members_added_30d += log.get('members_discovered', 0)
                        members_removed_30d += log.get('members_invalidated', 0)
            except:
                pass

        # Calculate average correlation quality
        if self.correlation_cache:
            valid_corrs = [
                r.lag_correlation for r in self.correlation_cache.values()
                if r.is_significant
            ]
            avg_corr_quality = np.mean([abs(c) for c in valid_corrs]) if valid_corrs else 0.0
        else:
            avg_corr_quality = 0.0

        # Check DeepSeek availability
        deepseek_available = self._deepseek is not None

        # Calculate health score
        health_score = 100.0

        if not self.stats['last_correlation_run']:
            health_score -= 20
        if not self.stats['last_validation_run']:
            health_score -= 20
        if not deepseek_available:
            health_score -= 10
        if avg_corr_quality < 0.5:
            health_score -= 10

        health_score = max(0, min(100, health_score))

        return LearnerHealth(
            last_correlation_run=self.stats.get('last_correlation_run', ''),
            last_news_scan=self.stats.get('last_news_scan', ''),
            last_validation_run=self.stats.get('last_validation_run', ''),
            themes_discovered_30d=themes_30d,
            members_added_30d=members_added_30d,
            members_removed_30d=members_removed_30d,
            avg_correlation_quality=round(avg_corr_quality, 3),
            deepseek_available=deepseek_available,
            health_score=health_score,
        )

    def get_summary(self) -> Dict:
        """Get learner summary for API/dashboard"""
        health = self.run_health_check()

        return {
            'health': asdict(health),
            'stats': self.stats,
            'pending_hypotheses': len(self.hypotheses),
            'correlation_cache_size': len(self.correlation_cache),
            'hypotheses': [h.to_dict() for h in self.hypotheses[:5]],
        }


# Singleton instance
_learner = None


def get_learner() -> ThemeLearner:
    """Get the global theme learner instance"""
    global _learner
    if _learner is None:
        _learner = ThemeLearner()
    return _learner


# Convenience functions
async def run_learning_cycle(
    price_data: Dict[str, List[float]],
    news_items: Optional[List[Dict]] = None,
    candidate_tickers: Optional[List[str]] = None,
) -> Dict:
    """Run a complete learning cycle"""
    return await get_learner().run_learning_cycle(price_data, news_items, candidate_tickers)


def run_health_check() -> LearnerHealth:
    """Run learner health check"""
    return get_learner().run_health_check()
