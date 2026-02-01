"""
Parameter Registry - Central Storage for All Tunable Parameters

The ParameterRegistry is the single source of truth for all 85+ learnable
parameters in the stock scanner system.
"""
import json
import logging
import statistics
from datetime import datetime
from typing import Dict, Any
from collections import defaultdict
from dataclasses import asdict

# Import from local core module
from .types import ParameterDefinition, ParameterCategory
from .paths import REGISTRY_FILE, _ensure_data_dir

# Lazy import to avoid circular dependency
def _get_audit_trail():
    """Lazy import of AuditTrail to avoid circular dependency"""
    from ..tracking.audit import AuditTrail
    return AuditTrail()


logger = logging.getLogger('parameter_learning.registry')


class ParameterRegistry:
    """
    Central registry for all tunable parameters.
    Single source of truth for parameter values.
    """

    def __init__(self):
        self.parameters: Dict[str, ParameterDefinition] = {}
        self._load_registry()
        if not self.parameters:
            self._initialize_default_parameters()
            self._save_registry()

    def _get_registry_path(self):
        return REGISTRY_FILE

    def _load_registry(self):
        """Load parameter registry from disk"""
        path = self._get_registry_path()
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                for name, param_data in data.get('parameters', {}).items():
                    self.parameters[name] = ParameterDefinition(**param_data)
                logger.info(f"Loaded {len(self.parameters)} parameters from registry")
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                self.parameters = {}

    def _save_registry(self):
        """Save parameter registry to disk"""
        _ensure_data_dir()
        path = self._get_registry_path()
        data = {
            'version': '1.0',
            'last_updated': datetime.now().isoformat(),
            'total_parameters': len(self.parameters),
            'parameters': {name: asdict(param) for name, param in self.parameters.items()}
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _initialize_default_parameters(self):
        """Initialize all 85+ parameters with their default values"""

        # ============================================
        # SCORING WEIGHTS (story_scorer.py, config.py)
        # ============================================

        scoring_weights = [
            ('weight.theme_heat', 0.18, 0.05, 0.40, 'Weight for theme heat in final score', 'story_scorer.py', 959),
            ('weight.catalyst', 0.18, 0.05, 0.40, 'Weight for catalyst score', 'story_scorer.py', 960),
            ('weight.social_buzz', 0.12, 0.05, 0.40, 'Weight for social buzz score', 'story_scorer.py', 961),
            ('weight.news_momentum', 0.10, 0.05, 0.40, 'Weight for news momentum', 'story_scorer.py', 962),
            ('weight.sentiment', 0.07, 0.05, 0.40, 'Weight for sentiment score', 'story_scorer.py', 963),
            ('weight.ecosystem', 0.10, 0.05, 0.40, 'Weight for ecosystem score', 'story_scorer.py', 964),
            ('weight.technical', 0.25, 0.05, 0.40, 'Weight for technical confirmation', 'story_scorer.py', 965),
        ]

        for name, default, min_v, max_v, desc, file, line in scoring_weights:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.SCORING_WEIGHT.value,
                description=desc, affects=['final_score'], source_file=file, source_line=line,
                mean=default, variance=0.01
            )

        # ============================================
        # THEME ROLE SCORES (story_scorer.py:522)
        # ============================================

        role_scores = [
            ('role.driver', 100, 50, 150, 'Score multiplier for theme drivers', 'story_scorer.py', 522),
            ('role.beneficiary', 70, 30, 100, 'Score multiplier for beneficiaries', 'story_scorer.py', 522),
            ('role.picks_shovels', 50, 20, 80, 'Score multiplier for picks & shovels', 'story_scorer.py', 522),
        ]

        for name, default, min_v, max_v, desc, file, line in role_scores:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.ROLE_SCORE.value,
                description=desc, affects=['theme_score'], source_file=file, source_line=line,
                mean=default, variance=100
            )

        # ============================================
        # THEME STAGE SCORES (story_scorer.py:523)
        # ============================================

        stage_scores = [
            ('stage.early', 100, 50, 150, 'Score for early stage themes', 'story_scorer.py', 523),
            ('stage.middle', 70, 40, 100, 'Score for middle stage themes', 'story_scorer.py', 523),
            ('stage.late', 30, 10, 60, 'Score for late stage themes', 'story_scorer.py', 523),
            ('stage.ongoing', 60, 30, 90, 'Score for ongoing themes', 'story_scorer.py', 523),
            ('stage.unknown', 50, 20, 80, 'Score for unknown stage themes', 'story_scorer.py', 523),
        ]

        for name, default, min_v, max_v, desc, file, line in stage_scores:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.ROLE_SCORE.value,
                description=desc, affects=['theme_score'], source_file=file, source_line=line,
                mean=default, variance=100
            )

        # ============================================
        # MULTIPLIERS (story_scorer.py)
        # ============================================

        multipliers = [
            ('multiplier.early_stage_boost', 1.2, 1.0, 1.5, 'Boost for early stage themes', 'story_scorer.py', 538),
            ('multiplier.catalyst_near_7d', 1.3, 1.0, 1.6, 'Boost for catalyst within 7 days', 'story_scorer.py', 629),
            ('multiplier.catalyst_near_14d', 1.1, 1.0, 1.3, 'Boost for catalyst within 14 days', 'story_scorer.py', 631),
            ('multiplier.strong_sentiment', 1.5, 1.0, 2.0, 'Multiplier for strong sentiment', 'news_analyzer.py', 872),
            ('multiplier.volume_score', 40, 20, 60, 'Multiplier for volume ratio to score', 'story_scorer.py', 869),
            ('multiplier.rs_score', 5, 2, 10, 'Multiplier for RS to score (50 + rs*X)', 'story_scorer.py', 882),
        ]

        for name, default, min_v, max_v, desc, file, line in multipliers:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.MULTIPLIER.value,
                description=desc, affects=['component_score'], source_file=file, source_line=line,
                mean=default, variance=(max_v - min_v) ** 2 / 12
            )

        # ============================================
        # THRESHOLDS - Sentiment (story_scorer.py, news_analyzer.py)
        # ============================================

        sentiment_thresholds = [
            ('threshold.sentiment.bullish', 65, 55, 80, 'Score threshold for bullish sentiment', 'story_scorer.py', 793),
            ('threshold.sentiment.bearish', 35, 20, 45, 'Score threshold for bearish sentiment', 'story_scorer.py', 795),
            ('threshold.sentiment.strong_bullish_pct', 70, 60, 85, 'Percentage for strong bullish', 'news_analyzer.py', 387),
            ('threshold.sentiment.bullish_pct', 55, 50, 65, 'Percentage for bullish', 'news_analyzer.py', 389),
            ('threshold.sentiment.bearish_pct', 45, 35, 50, 'Percentage for bearish', 'news_analyzer.py', 393),
            ('threshold.sentiment.strong_bearish_pct', 30, 15, 40, 'Percentage for strong bearish', 'news_analyzer.py', 391),
        ]

        for name, default, min_v, max_v, desc, file, line in sentiment_thresholds:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.THRESHOLD.value,
                description=desc, affects=['sentiment_classification'], source_file=file, source_line=line,
                mean=default, variance=25
            )

        # ============================================
        # THRESHOLDS - Confidence (story_scorer.py)
        # ============================================

        confidence_thresholds = [
            ('threshold.confidence.high_articles', 10, 5, 20, 'Min articles for high confidence', 'story_scorer.py', 800),
            ('threshold.confidence.medium_articles', 5, 2, 10, 'Min articles for medium confidence', 'story_scorer.py', 802),
        ]

        for name, default, min_v, max_v, desc, file, line in confidence_thresholds:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.THRESHOLD.value,
                description=desc, affects=['confidence_level'], source_file=file, source_line=line,
                mean=default, variance=4
            )

        # ============================================
        # THRESHOLDS - News Momentum (story_scorer.py)
        # ============================================

        momentum_thresholds = [
            ('threshold.momentum.accelerating', 1.5, 1.2, 2.0, 'Ratio for accelerating news', 'story_scorer.py', 704),
            ('threshold.momentum.stable', 0.8, 0.5, 1.0, 'Ratio for stable news', 'story_scorer.py', 707),
            ('score.momentum.accelerating_base', 80, 60, 95, 'Base score for accelerating', 'story_scorer.py', 705),
            ('score.momentum.stable_base', 50, 30, 70, 'Base score for stable', 'story_scorer.py', 708),
            ('score.momentum.declining', 30, 10, 50, 'Score for declining momentum', 'story_scorer.py', 710),
        ]

        for name, default, min_v, max_v, desc, file, line in momentum_thresholds:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.THRESHOLD.value,
                description=desc, affects=['news_momentum_score'], source_file=file, source_line=line,
                mean=default, variance=25 if 'score' in name else 0.1
            )

        # ============================================
        # THRESHOLDS - Technical (story_scorer.py)
        # ============================================

        technical_scores = [
            ('score.technical.trend_3', 100, 80, 100, 'Score when all 3 trend conditions met', 'story_scorer.py', 855),
            ('score.technical.trend_2', 70, 50, 85, 'Score when 2 trend conditions met', 'story_scorer.py', 857),
            ('score.technical.trend_1', 50, 30, 65, 'Score when 1 trend condition met', 'story_scorer.py', 859),
            ('score.technical.trend_0', 20, 0, 40, 'Score when no trend conditions met', 'story_scorer.py', 861),
        ]

        for name, default, min_v, max_v, desc, file, line in technical_scores:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.TECHNICAL.value,
                description=desc, affects=['technical_score'], source_file=file, source_line=line,
                mean=default, variance=100
            )

        # ============================================
        # THRESHOLDS - Social Buzz (story_scorer.py)
        # ============================================

        social_thresholds = [
            ('threshold.stocktwits.high', 20, 10, 40, 'High StockTwits volume threshold', 'story_scorer.py', 242),
            ('threshold.stocktwits.medium', 10, 5, 20, 'Medium StockTwits volume threshold', 'story_scorer.py', 244),
            ('threshold.stocktwits.low', 5, 2, 10, 'Low StockTwits volume threshold', 'story_scorer.py', 246),
            ('score.stocktwits.high', 30, 20, 50, 'Score for high StockTwits volume', 'story_scorer.py', 243),
            ('score.stocktwits.medium', 20, 10, 35, 'Score for medium StockTwits volume', 'story_scorer.py', 245),
            ('score.stocktwits.low', 10, 5, 20, 'Score for low StockTwits volume', 'story_scorer.py', 247),
            ('score.stocktwits.bullish_boost', 20, 10, 40, 'Boost for bullish sentiment', 'story_scorer.py', 250),
            ('threshold.reddit.high', 5, 3, 10, 'High Reddit mention threshold', 'story_scorer.py', 253),
            ('threshold.reddit.medium', 2, 1, 5, 'Medium Reddit mention threshold', 'story_scorer.py', 255),
            ('threshold.reddit.score_high', 500, 200, 1000, 'High Reddit score threshold', 'story_scorer.py', 260),
            ('threshold.reddit.score_medium', 100, 50, 300, 'Medium Reddit score threshold', 'story_scorer.py', 262),
            ('score.sec.8k', 20, 10, 40, 'Score for 8-K filing', 'story_scorer.py', 267),
            ('score.sec.insider', 15, 5, 30, 'Score for insider activity', 'story_scorer.py', 269),
            ('threshold.trending.reddit_mentions', 3, 1, 5, 'Reddit mentions for trending', 'story_scorer.py', 277),
        ]

        for name, default, min_v, max_v, desc, file, line in social_thresholds:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.THRESHOLD.value,
                description=desc, affects=['social_buzz_score'], source_file=file, source_line=line,
                mean=default, variance=(max_v - min_v) ** 2 / 12
            )

        # ============================================
        # SIGNAL RANKER (signal_ranker.py)
        # ============================================

        signal_params = [
            ('signal.initial_trust', 50, 30, 70, 'Initial trust score for new sources', 'signal_ranker.py', 31),
            ('signal.consensus_4plus', 25, 15, 40, 'Points for 4+ source consensus', 'signal_ranker.py', 156),
            ('signal.consensus_2plus', 15, 8, 25, 'Points for 2+ source consensus', 'signal_ranker.py', 158),
            ('signal.consensus_1', 5, 0, 15, 'Points for single source', 'signal_ranker.py', 160),
            ('signal.tier1_bonus', 20, 10, 35, 'Bonus for Tier 1 sources', 'signal_ranker.py', 163),
            ('signal.tier2_bonus', 12, 5, 20, 'Bonus for Tier 2 sources', 'signal_ranker.py', 165),
            ('signal.multi_ticker_3plus', 15, 8, 25, 'Bonus for 3+ tickers', 'signal_ranker.py', 168),
            ('signal.multi_ticker_1plus', 10, 5, 18, 'Bonus for 1+ ticker', 'signal_ranker.py', 170),
            ('signal.catalyst_substantive', 15, 8, 25, 'Bonus for substantive catalyst', 'signal_ranker.py', 173),
            ('signal.catalyst_mentioned', 8, 3, 15, 'Bonus for catalyst mentioned', 'signal_ranker.py', 175),
            ('signal.smart_money_divergence', 25, 15, 40, 'Bonus for smart money divergence', 'signal_ranker.py', 178),
            ('signal.weight.source_trust', 0.25, 0.10, 0.40, 'Weight for source trust in ranking', 'signal_ranker.py', 335),
            ('signal.weight.signal_strength', 0.30, 0.15, 0.45, 'Weight for signal strength', 'signal_ranker.py', 336),
            ('signal.weight.timing', 0.25, 0.10, 0.40, 'Weight for timing score', 'signal_ranker.py', 337),
            ('signal.weight.novelty', 0.20, 0.10, 0.35, 'Weight for novelty', 'signal_ranker.py', 338),
        ]

        for name, default, min_v, max_v, desc, file, line in signal_params:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v,
                category=ParameterCategory.SCORING_WEIGHT.value if 'weight' in name else ParameterCategory.THRESHOLD.value,
                description=desc, affects=['signal_rank'], source_file=file, source_line=line,
                mean=default, variance=(max_v - min_v) ** 2 / 12
            )

        # ============================================
        # TIMING THRESHOLDS (signal_ranker.py)
        # ============================================

        timing_params = [
            ('threshold.timing.early_week', 3, 1, 5, 'Max weekly move % for early signal', 'signal_ranker.py', 264),
            ('threshold.timing.early_month', 10, 5, 15, 'Max monthly move % for early signal', 'signal_ranker.py', 264),
            ('threshold.timing.confirming_week', 5, 3, 8, 'Max weekly move % for confirming', 'signal_ranker.py', 266),
            ('threshold.timing.confirming_month_min', 10, 5, 15, 'Min monthly move % for confirming', 'signal_ranker.py', 266),
            ('threshold.timing.confirming_month_max', 25, 15, 35, 'Max monthly move % for confirming', 'signal_ranker.py', 266),
            ('score.timing.early', 90, 70, 100, 'Score for early timing', 'signal_ranker.py', 265),
            ('score.timing.confirming', 60, 40, 80, 'Score for confirming timing', 'signal_ranker.py', 267),
            ('score.timing.late', 30, 10, 50, 'Score for late timing', 'signal_ranker.py', 269),
        ]

        for name, default, min_v, max_v, desc, file, line in timing_params:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.THRESHOLD.value,
                description=desc, affects=['timing_score'], source_file=file, source_line=line,
                mean=default, variance=(max_v - min_v) ** 2 / 12
            )

        # ============================================
        # NOVELTY THRESHOLDS (signal_ranker.py)
        # ============================================

        novelty_params = [
            ('threshold.novelty.very_new', 3, 1, 5, 'Max mentions for very new', 'signal_ranker.py', 323),
            ('threshold.novelty.emerging', 10, 5, 15, 'Max mentions for emerging', 'signal_ranker.py', 325),
            ('threshold.novelty.known', 25, 15, 40, 'Max mentions for known', 'signal_ranker.py', 327),
            ('score.novelty.very_new', 90, 70, 100, 'Score for very new', 'signal_ranker.py', 324),
            ('score.novelty.emerging', 70, 50, 85, 'Score for emerging', 'signal_ranker.py', 326),
            ('score.novelty.known', 50, 30, 65, 'Score for known', 'signal_ranker.py', 328),
            ('score.novelty.mainstream', 30, 10, 50, 'Score for mainstream', 'signal_ranker.py', 330),
        ]

        for name, default, min_v, max_v, desc, file, line in novelty_params:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.THRESHOLD.value,
                description=desc, affects=['novelty_score'], source_file=file, source_line=line,
                mean=default, variance=(max_v - min_v) ** 2 / 12
            )

        # ============================================
        # CATALYST PARAMETERS (story_scorer.py)
        # ============================================

        catalyst_params = [
            ('catalyst.window.earnings', 14, 7, 30, 'Days before earnings catalyst', 'story_scorer.py', 445),
            ('catalyst.window.fda', 30, 14, 60, 'Days before FDA catalyst', 'story_scorer.py', 446),
            ('catalyst.window.product_launch', 30, 14, 60, 'Days before product launch', 'story_scorer.py', 447),
            ('catalyst.window.conference', 7, 3, 14, 'Days before conference', 'story_scorer.py', 448),
            ('catalyst.window.merger', 90, 30, 180, 'Days for merger catalyst', 'story_scorer.py', 449),
            ('catalyst.impact.very_high', 100, 80, 100, 'Score for very high impact', 'story_scorer.py', 621),
            ('catalyst.impact.high', 75, 60, 90, 'Score for high impact', 'story_scorer.py', 621),
            ('catalyst.impact.medium', 50, 35, 65, 'Score for medium impact', 'story_scorer.py', 621),
            ('catalyst.impact.low', 25, 10, 40, 'Score for low impact', 'story_scorer.py', 621),
        ]

        for name, default, min_v, max_v, desc, file, line in catalyst_params:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v,
                category=ParameterCategory.TIME_WINDOW.value if 'window' in name else ParameterCategory.ROLE_SCORE.value,
                description=desc, affects=['catalyst_score'], source_file=file, source_line=line,
                mean=default, variance=(max_v - min_v) ** 2 / 12
            )

        # ============================================
        # KEYWORD WEIGHTS (news_analyzer.py)
        # ============================================

        keyword_params = [
            ('keyword.bullish.strong', 3, 2, 5, 'Weight for strong bullish keywords', 'news_analyzer.py', 41),
            ('keyword.bullish.medium', 2, 1, 3, 'Weight for medium bullish keywords', 'news_analyzer.py', 42),
            ('keyword.bullish.weak', 1, 0, 2, 'Weight for weak bullish keywords', 'news_analyzer.py', 43),
            ('keyword.bearish.strong', 3, 2, 5, 'Weight for strong bearish keywords', 'news_analyzer.py', 46),
            ('keyword.bearish.medium', 2, 1, 3, 'Weight for medium bearish keywords', 'news_analyzer.py', 47),
            ('keyword.bearish.weak', 1, 0, 2, 'Weight for weak bearish keywords', 'news_analyzer.py', 48),
        ]

        for name, default, min_v, max_v, desc, file, line in keyword_params:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.KEYWORD_WEIGHT.value,
                description=desc, affects=['sentiment_score'], source_file=file, source_line=line,
                mean=default, variance=1
            )

        # ============================================
        # TECHNICAL PARAMETERS (scanner_automation.py)
        # ============================================

        technical_params = [
            ('technical.ma.short', 20, 10, 30, 'Short moving average period', 'scanner_automation.py', 220),
            ('technical.ma.medium', 50, 30, 70, 'Medium moving average period', 'scanner_automation.py', 221),
            ('technical.ma.long', 200, 150, 250, 'Long moving average period', 'scanner_automation.py', 222),
            ('technical.squeeze.percentile', 20, 10, 35, 'Bollinger squeeze percentile', 'scanner_automation.py', 251),
            ('technical.volume.level1', 1.2, 1.0, 1.5, 'Volume ratio level 1', 'scanner_automation.py', 265),
            ('technical.volume.level2', 1.5, 1.3, 2.0, 'Volume ratio level 2', 'scanner_automation.py', 267),
            ('technical.volume.level3', 2.0, 1.5, 3.0, 'Volume ratio level 3', 'scanner_automation.py', 269),
        ]

        for name, default, min_v, max_v, desc, file, line in technical_params:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.TECHNICAL.value,
                description=desc, affects=['technical_signals'], source_file=file, source_line=line,
                mean=default, variance=(max_v - min_v) ** 2 / 12
            )

        # ============================================
        # ECOSYSTEM PARAMETERS (relationship_graph.py, ecosystem_intelligence.py)
        # ============================================

        ecosystem_params = [
            ('ecosystem.decay.supplier', 0.98, 0.90, 1.0, 'Decay rate for supplier relationships', 'relationship_graph.py', 47),
            ('ecosystem.decay.customer', 0.98, 0.90, 1.0, 'Decay rate for customer relationships', 'relationship_graph.py', 48),
            ('ecosystem.decay.competitor', 0.99, 0.95, 1.0, 'Decay rate for competitor relationships', 'relationship_graph.py', 49),
            ('ecosystem.decay.adjacent', 0.97, 0.90, 1.0, 'Decay rate for adjacent plays', 'relationship_graph.py', 50),
            ('ecosystem.default_strength', 0.7, 0.4, 0.9, 'Default edge strength', 'relationship_graph.py', 107),
            ('ecosystem.min_strength', 0.5, 0.3, 0.7, 'Minimum strength filter', 'ecosystem_intelligence.py', 140),
            ('ecosystem.in_play_threshold', 70, 50, 90, 'Score threshold for in-play', 'ecosystem_intelligence.py', 203),
            ('ecosystem.opportunity_gap', 10, 5, 20, 'Gap for lagging supplier opportunity', 'ecosystem_intelligence.py', 221),
        ]

        for name, default, min_v, max_v, desc, file, line in ecosystem_params:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.DECAY_RATE.value,
                description=desc, affects=['ecosystem_score'], source_file=file, source_line=line,
                mean=default, variance=(max_v - min_v) ** 2 / 12
            )

        # ============================================
        # OUTCOME THRESHOLDS (scanner_automation.py, self_learning.py)
        # ============================================

        outcome_params = [
            ('outcome.win_threshold', 2.0, 1.0, 5.0, 'Percent gain for win classification', 'scanner_automation.py', 88),
            ('outcome.loss_threshold', -2.0, -5.0, -1.0, 'Percent loss for loss classification', 'scanner_automation.py', 88),
            ('outcome.win_rate_min', 40, 30, 55, 'Minimum acceptable win rate %', 'self_learning.py', 184),
            ('outcome.promotion_threshold', 3, 2, 5, 'Appearances needed for theme promotion', 'scanner_automation.py', 814),
        ]

        for name, default, min_v, max_v, desc, file, line in outcome_params:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.THRESHOLD.value,
                description=desc, affects=['outcome_classification'], source_file=file, source_line=line,
                mean=default, variance=(max_v - min_v) ** 2 / 12
            )

        # ============================================
        # MARKET REGIME THRESHOLDS (sector_rotation.py)
        # ============================================

        regime_params = [
            ('regime.bull.price_vs_sma20', 2, 0, 5, 'Price vs SMA20 % for bull trending', 'sector_rotation.py', 282),
            ('regime.bull.sma20_vs_sma50', 1, 0, 3, 'SMA20 vs SMA50 % for bull trending', 'sector_rotation.py', 282),
            ('regime.bull.max_volatility', 25, 15, 35, 'Max volatility for bull trending', 'sector_rotation.py', 282),
            ('regime.bear.price_vs_sma20', -2, -5, 0, 'Price vs SMA20 % for bear volatile', 'sector_rotation.py', 284),
            ('regime.bear.min_volatility', 30, 20, 40, 'Min volatility for bear volatile', 'sector_rotation.py', 284),
            ('regime.momentum.weight_1w', 0.5, 0.3, 0.7, 'Weight for 1-week momentum', 'sector_rotation.py', 154),
            ('regime.momentum.weight_1m', 0.3, 0.1, 0.5, 'Weight for 1-month momentum', 'sector_rotation.py', 154),
            ('regime.momentum.weight_3m', 0.2, 0.05, 0.4, 'Weight for 3-month momentum', 'sector_rotation.py', 154),
        ]

        for name, default, min_v, max_v, desc, file, line in regime_params:
            self.parameters[name] = ParameterDefinition(
                name=name, current_value=default, default_value=default,
                min_value=min_v, max_value=max_v, category=ParameterCategory.THRESHOLD.value,
                description=desc, affects=['market_regime'], source_file=file, source_line=line,
                mean=default, variance=(max_v - min_v) ** 2 / 12
            )

        logger.info(f"Initialized {len(self.parameters)} parameters in registry")

    def get(self, name: str) -> float:
        """Get current value of a parameter"""
        if name in self.parameters:
            return self.parameters[name].current_value
        raise KeyError(f"Parameter '{name}' not found in registry")

    def get_with_metadata(self, name: str) -> ParameterDefinition:
        """Get parameter with all metadata"""
        if name in self.parameters:
            return self.parameters[name]
        raise KeyError(f"Parameter '{name}' not found in registry")

    def set(self, name: str, value: float, reason: str = None) -> bool:
        """Set parameter value with optional reason for audit"""
        if name not in self.parameters:
            raise KeyError(f"Parameter '{name}' not found in registry")

        param = self.parameters[name]

        # Validate bounds
        if value < param.min_value or value > param.max_value:
            logger.warning(f"Value {value} for {name} outside bounds [{param.min_value}, {param.max_value}]")
            value = max(param.min_value, min(param.max_value, value))

        old_value = param.current_value
        param.current_value = value
        param.last_updated = datetime.now().isoformat()

        self._save_registry()

        # Log to audit trail
        try:
            audit = _get_audit_trail()
            audit.log_change(name, old_value, value, reason or 'manual_update')
        except Exception as e:
            logger.warning(f"Failed to log audit trail: {e}")

        return True

    def get_all(self) -> Dict[str, float]:
        """Get all current parameter values"""
        return {name: param.current_value for name, param in self.parameters.items()}

    def get_by_category(self, category: str) -> Dict[str, ParameterDefinition]:
        """Get all parameters in a category"""
        return {name: param for name, param in self.parameters.items()
                if param.category == category}

    def get_by_status(self, status: str) -> Dict[str, ParameterDefinition]:
        """Get all parameters with a given learning status"""
        return {name: param for name, param in self.parameters.items()
                if param.status == status}

    def get_snapshot(self) -> Dict[str, float]:
        """Get snapshot of all parameter values for outcome attribution"""
        return {name: param.current_value for name, param in self.parameters.items()}

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about parameter learning status"""
        by_status = defaultdict(int)
        by_category = defaultdict(int)

        for param in self.parameters.values():
            by_status[param.status] += 1
            by_category[param.category] += 1

        learned_count = sum(1 for p in self.parameters.values() if p.learned_from_samples > 0)

        return {
            'total': len(self.parameters),
            'by_status': dict(by_status),
            'by_category': dict(by_category),
            'learned': learned_count,
            'static': len(self.parameters) - learned_count,
            'avg_samples': statistics.mean([p.learned_from_samples for p in self.parameters.values()]) if self.parameters else 0,
            'avg_confidence': statistics.mean([p.confidence for p in self.parameters.values()]) if self.parameters else 0,
        }
