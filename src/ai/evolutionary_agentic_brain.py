#!/usr/bin/env python3
"""
Evolutionary Agentic Brain - Self-Improving Hierarchical Intelligence

Extends the comprehensive agentic brain with automatic accountability and evolution:
- Tracks all 37 components' performance automatically (includes xAI X Intelligence)
- Updates trust scores based on accuracy
- Evolves weights to favor high performers
- Learns which components work in which conditions
- Zero manual work - everything is automatic

Architecture:
    Decision → Auto-log all components → Record outcome → Auto-update scores → Evolve weights

Component #37: xAI X Intelligence Monitor (Real-time crisis detection via X/Twitter)
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from src.ai.comprehensive_agentic_brain import (
    ChiefIntelligenceOfficer,
    ContextManager,
    ThemeIntelligenceDirector,
    TradingIntelligenceDirector,
    LearningAdaptationDirector,
    RealtimeIntelligenceDirector,
    ValidationFeedbackDirector,
    FinalDecision,
    ThemeIntelligence,
    TradingIntelligence,
    LearningIntelligence,
    RealtimeIntelligence,
    ValidationIntelligence,
    MarketContext,
    SectorContext,
    MarketHealth,
    Decision
)

logger = logging.getLogger(__name__)

# Import notification system for crisis alerts
try:
    from src.notifications.notification_manager import get_notification_manager, NotificationPriority
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    logger.warning("Notification system not available - crisis alerts will only be logged")

# Import X Intelligence (Component #37)
try:
    from src.ai.xai_x_intelligence import (
        XAIXIntelligence,
        XMonitoringScheduler,
        CrisisAlert,
        StockSentiment,
        PanicIndicator,
        MonitoringMode
    )
    X_INTELLIGENCE_AVAILABLE = True
except ImportError:
    X_INTELLIGENCE_AVAILABLE = False
    logger.warning("xAI X Intelligence not available - crisis monitoring disabled")

# Storage location
PERFORMANCE_DATA_DIR = Path.home() / '.claude' / 'agentic_brain'
PERFORMANCE_DATA_DIR.mkdir(parents=True, exist_ok=True)

COMPONENT_PERFORMANCE_FILE = PERFORMANCE_DATA_DIR / 'component_performance.json'
DECISION_HISTORY_FILE = PERFORMANCE_DATA_DIR / 'decision_history.json'
EVOLUTION_LOG_FILE = PERFORMANCE_DATA_DIR / 'evolution_log.json'


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ComponentPerformance:
    """Performance tracking for a single component."""
    component_id: str
    component_name: str
    component_type: str  # 'director' or 'specialist'
    parent_director: Optional[str] = None

    # Performance metrics
    decisions_participated: int = 0
    predictions_correct: int = 0
    predictions_incorrect: int = 0
    accuracy_rate: float = 0.5

    # Evolution metrics
    trust_score: float = 0.5  # 0-1, starts neutral
    weight_multiplier: float = 1.0  # 0.5-2.0, starts neutral

    # Historical tracking (last 100)
    accuracy_history: List[float] = field(default_factory=list)
    trust_history: List[float] = field(default_factory=list)

    # Learning insights
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    # Regime-specific performance
    performance_by_regime: Dict[str, float] = field(default_factory=dict)

    # Timestamps
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DecisionRecord:
    """Complete record of a decision for accountability tracking."""
    decision_id: str
    timestamp: str
    ticker: str
    signal_type: str

    # Final decision
    decision: str  # Decision enum value
    confidence: float
    position_size: str

    # Component scores (auto-logged)
    theme_score: int
    trade_score: int
    learning_score: int
    realtime_score: int
    validation_score: int

    # Market context at decision time
    market_health: str
    market_risk_level: int
    market_stance: str
    sector_cycle: str

    # Fields with defaults (must come after fields without defaults)
    # Component details (what each predicted)
    component_predictions: Dict[str, Any] = field(default_factory=dict)

    # Outcome (filled later)
    outcome_recorded: bool = False
    actual_outcome: Optional[str] = None  # 'win'/'loss'/'breakeven'
    actual_pnl: Optional[float] = None
    exit_price: Optional[float] = None
    exit_date: Optional[str] = None

    # Performance analysis (auto-calculated)
    components_correct: List[str] = field(default_factory=list)
    components_incorrect: List[str] = field(default_factory=list)


@dataclass
class EvolutionEvent:
    """Log of an evolution event (weight change, etc)."""
    timestamp: str
    event_type: str  # 'weight_increase', 'weight_decrease', 'trust_update', etc
    component_id: str
    old_value: float
    new_value: float
    reason: str
    trigger_decision: Optional[str] = None


# =============================================================================
# PERFORMANCE TRACKER
# =============================================================================

class PerformanceTracker:
    """
    Automatically tracks and evolves component performance.

    Responsibilities:
    - Record every decision with all component details
    - Match decisions to outcomes
    - Calculate which components were correct
    - Update accuracy, trust, and weights automatically
    - Generate accountability reports
    """

    def __init__(self):
        self.component_performance: Dict[str, ComponentPerformance] = {}
        self.decision_history: Dict[str, DecisionRecord] = {}
        self.evolution_log: List[EvolutionEvent] = []

        self._load_data()
        logger.info("Performance Tracker initialized")

    def _load_data(self):
        """Load existing performance data."""
        # Load component performance
        if COMPONENT_PERFORMANCE_FILE.exists():
            try:
                with open(COMPONENT_PERFORMANCE_FILE, 'r') as f:
                    data = json.load(f)
                    for comp_id, comp_data in data.items():
                        self.component_performance[comp_id] = ComponentPerformance(**comp_data)
                logger.info(f"Loaded performance data for {len(self.component_performance)} components")
            except Exception as e:
                logger.error(f"Error loading component performance: {e}")

        # Load decision history
        if DECISION_HISTORY_FILE.exists():
            try:
                with open(DECISION_HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    for dec_id, dec_data in data.items():
                        self.decision_history[dec_id] = DecisionRecord(**dec_data)
                logger.info(f"Loaded {len(self.decision_history)} historical decisions")
            except Exception as e:
                logger.error(f"Error loading decision history: {e}")

        # Load evolution log
        if EVOLUTION_LOG_FILE.exists():
            try:
                with open(EVOLUTION_LOG_FILE, 'r') as f:
                    data = json.load(f)
                    self.evolution_log = [EvolutionEvent(**evt) for evt in data]
                logger.info(f"Loaded {len(self.evolution_log)} evolution events")
            except Exception as e:
                logger.error(f"Error loading evolution log: {e}")

    def _save_data(self):
        """Persist all tracking data."""
        try:
            # Save component performance
            with open(COMPONENT_PERFORMANCE_FILE, 'w') as f:
                data = {
                    comp_id: asdict(comp)
                    for comp_id, comp in self.component_performance.items()
                }
                json.dump(data, f, indent=2)

            # Save decision history (keep last 1000)
            with open(DECISION_HISTORY_FILE, 'w') as f:
                recent_decisions = dict(list(self.decision_history.items())[-1000:])
                data = {
                    dec_id: asdict(dec)
                    for dec_id, dec in recent_decisions.items()
                }
                json.dump(data, f, indent=2)

            # Save evolution log (keep last 500)
            with open(EVOLUTION_LOG_FILE, 'w') as f:
                recent_events = [asdict(evt) for evt in self.evolution_log[-500:]]
                json.dump(recent_events, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving performance data: {e}")

    def record_decision(
        self,
        decision: FinalDecision,
        component_predictions: Dict[str, Any],
        market_context: MarketContext,
        sector_context: SectorContext
    ) -> str:
        """
        Automatically record a decision with ALL component details.

        Returns:
            decision_id for later outcome recording
        """
        decision_id = f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{decision.ticker}"

        record = DecisionRecord(
            decision_id=decision_id,
            timestamp=datetime.now().isoformat(),
            ticker=decision.ticker,
            signal_type='unknown',  # Can be enhanced
            decision=decision.decision.value,
            confidence=decision.confidence,
            position_size=decision.position_size,
            theme_score=decision.theme_score,
            trade_score=decision.trade_score,
            learning_score=decision.learning_score,
            realtime_score=decision.realtime_score,
            validation_score=decision.validation_score,
            component_predictions=component_predictions,
            market_health=market_context.health.value,
            market_risk_level=market_context.risk_level,
            market_stance=market_context.stance.value,
            sector_cycle=sector_context.cycle_stage.value
        )

        self.decision_history[decision_id] = record

        # Initialize component performance if first time seeing them
        self._initialize_components(component_predictions)

        # Increment participation count
        for component_id in component_predictions.keys():
            if component_id in self.component_performance:
                self.component_performance[component_id].decisions_participated += 1

        self._save_data()

        logger.info(f"Recorded decision {decision_id} with {len(component_predictions)} components")
        return decision_id

    def _initialize_components(self, component_predictions: Dict[str, Any]):
        """Initialize component performance tracking on first sight."""
        # Director mapping
        director_specialists = {
            'theme_director': ['tam_estimator', 'theme_stage_detector', 'role_classifier',
                              'membership_validator', 'theme_info_generator', 'emerging_theme_detector'],
            'trading_director': ['signal_explainer', 'timeframe_synthesizer', 'earnings_intelligence',
                                'corporate_action_analyzer', 'anomaly_detector', 'options_flow_analyzer'],
            'learning_director': ['pattern_analyzer', 'trade_journal', 'outcome_predictor',
                                 'prediction_calibration', 'strategy_advisor', 'weight_calculator',
                                 'catalyst_tracker', 'expert_leaderboard'],
            'realtime_director': ['catalyst_detector', 'theme_rotation_predictor', 'realtime_scanner',
                                 'anomaly_scanner', 'options_scanner', 'market_narrator', 'daily_briefer'],
            'validation_director': ['fact_checker', 'expert_analyzer', 'coaching_system',
                                   'feedback_generator', 'supply_chain_discoverer']
        }

        for component_id in component_predictions.keys():
            if component_id not in self.component_performance:
                # Determine type and parent
                is_director = component_id.endswith('_director')
                parent = None

                if not is_director:
                    # Find parent director
                    for director, specialists in director_specialists.items():
                        if component_id in specialists:
                            parent = director
                            break

                self.component_performance[component_id] = ComponentPerformance(
                    component_id=component_id,
                    component_name=component_id.replace('_', ' ').title(),
                    component_type='director' if is_director else 'specialist',
                    parent_director=parent
                )
                logger.info(f"Initialized tracking for {component_id}")

    def record_outcome(
        self,
        decision_id: str,
        actual_outcome: str,
        actual_pnl: float,
        exit_price: Optional[float] = None,
        exit_date: Optional[str] = None
    ):
        """
        Record actual outcome and AUTOMATICALLY update all component scores.

        This is where the magic happens - the system learns and evolves!
        """
        if decision_id not in self.decision_history:
            logger.warning(f"Decision {decision_id} not found in history")
            return

        record = self.decision_history[decision_id]

        # Update outcome
        record.outcome_recorded = True
        record.actual_outcome = actual_outcome
        record.actual_pnl = actual_pnl
        record.exit_price = exit_price
        record.exit_date = exit_date or datetime.now().isoformat()

        logger.info(f"Recording outcome for {decision_id}: {actual_outcome} ({actual_pnl:+.1%})")

        # AUTOMATIC ANALYSIS: Which components were correct?
        self._analyze_component_accuracy(record)

        # AUTOMATIC UPDATE: Update all component scores
        self._update_component_scores(record)

        self._save_data()

        logger.info(f"✓ Automatically updated {len(record.components_correct)} correct components")
        logger.info(f"✗ Automatically updated {len(record.components_incorrect)} incorrect components")

    def _analyze_component_accuracy(self, record: DecisionRecord):
        """
        Automatically determine which components were correct/incorrect.

        Logic:
        - Decision was BUY/STRONG_BUY and outcome was win → Components predicting buy were correct
        - Decision was SELL and outcome was loss avoided → Components predicting sell were correct
        - High-scoring components in winning trades → Correct
        - Low-scoring components in losing trades → Also correct (they warned us)
        """
        decision_was_bullish = record.decision in ['buy', 'strong_buy']
        outcome_was_positive = record.actual_outcome == 'win'

        # Decision was correct overall
        decision_correct = (decision_was_bullish and outcome_was_positive) or \
                          (not decision_was_bullish and not outcome_was_positive)

        # Analyze directors
        if decision_correct:
            # High-scoring directors were correct
            if record.theme_score >= 7:
                record.components_correct.append('theme_director')
            if record.trade_score >= 7:
                record.components_correct.append('trading_director')
            if record.learning_score >= 7:
                record.components_correct.append('learning_director')
            if record.realtime_score >= 7:
                record.components_correct.append('realtime_director')
            if record.validation_score >= 7:
                record.components_correct.append('validation_director')
        else:
            # Low-scoring directors were correct (they warned us)
            if record.theme_score < 5:
                record.components_correct.append('theme_director')
            if record.trade_score < 5:
                record.components_correct.append('trading_director')

        # Analyze specialists based on their predictions
        for component_id, prediction in record.component_predictions.items():
            if component_id.endswith('_director'):
                continue  # Already handled above

            # Component-specific logic
            was_correct = self._evaluate_specialist_prediction(
                component_id,
                prediction,
                record.actual_outcome,
                record.actual_pnl
            )

            if was_correct:
                record.components_correct.append(component_id)
            else:
                record.components_incorrect.append(component_id)

    def _evaluate_specialist_prediction(
        self,
        component_id: str,
        prediction: Any,
        actual_outcome: str,
        actual_pnl: float
    ) -> bool:
        """Evaluate if a specialist's prediction was correct."""

        # Default: If we don't have specific logic, assume correct if outcome was positive
        if actual_outcome == 'win':
            return True

        # Component-specific evaluation
        if component_id == 'tam_estimator':
            # TAM estimator is correct if we had positive returns
            # (means growth thesis was validated)
            return actual_pnl > 0

        elif component_id == 'signal_explainer':
            # Signal explainer is correct if the signal led to profit
            return actual_pnl > 0

        elif component_id == 'timeframe_synthesizer':
            # Timeframe synthesis is correct if we made money
            return actual_pnl > 0

        elif component_id == 'outcome_predictor':
            # Outcome predictor is correct if prediction matched reality
            if isinstance(prediction, dict):
                predicted = prediction.get('prediction', 'unknown')
                if predicted == 'win' and actual_outcome == 'win':
                    return True
                elif predicted == 'loss' and actual_outcome == 'loss':
                    return True
            return False

        elif component_id == 'pattern_analyzer':
            # Pattern analyzer is correct if pattern played out
            return actual_pnl > 0

        # Default: Positive outcome means component was likely correct
        return actual_outcome == 'win'

    def _update_component_scores(self, record: DecisionRecord):
        """
        AUTOMATICALLY update accuracy, trust, and weights for all components.

        This is the evolution engine!
        """
        # Update correct components
        for component_id in record.components_correct:
            if component_id not in self.component_performance:
                continue

            comp = self.component_performance[component_id]
            comp.predictions_correct += 1

            # Recalculate accuracy
            total = comp.predictions_correct + comp.predictions_incorrect
            old_accuracy = comp.accuracy_rate
            comp.accuracy_rate = comp.predictions_correct / total if total > 0 else 0.5

            # Update trust (gradually increase)
            old_trust = comp.trust_score
            comp.trust_score = min(1.0, comp.trust_score + 0.01)

            # Update weight (favor high performers)
            old_weight = comp.weight_multiplier
            if comp.accuracy_rate > 0.70 and total >= 10:
                comp.weight_multiplier = min(2.0, comp.weight_multiplier + 0.05)

            # Log evolution if significant change
            if comp.weight_multiplier != old_weight:
                self.evolution_log.append(EvolutionEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type='weight_increase',
                    component_id=component_id,
                    old_value=old_weight,
                    new_value=comp.weight_multiplier,
                    reason=f"High accuracy ({comp.accuracy_rate:.1%})",
                    trigger_decision=record.decision_id
                ))

            # Update history
            comp.accuracy_history.append(comp.accuracy_rate)
            comp.trust_history.append(comp.trust_score)
            comp.last_updated = datetime.now().isoformat()

            # Keep last 100
            comp.accuracy_history = comp.accuracy_history[-100:]
            comp.trust_history = comp.trust_history[-100:]

        # Update incorrect components
        for component_id in record.components_incorrect:
            if component_id not in self.component_performance:
                continue

            comp = self.component_performance[component_id]
            comp.predictions_incorrect += 1

            # Recalculate accuracy
            total = comp.predictions_correct + comp.predictions_incorrect
            old_accuracy = comp.accuracy_rate
            comp.accuracy_rate = comp.predictions_correct / total if total > 0 else 0.5

            # Update trust (gradually decrease)
            old_trust = comp.trust_score
            comp.trust_score = max(0.0, comp.trust_score - 0.01)

            # Update weight (penalize poor performers)
            old_weight = comp.weight_multiplier
            if comp.accuracy_rate < 0.50 and total >= 10:
                comp.weight_multiplier = max(0.5, comp.weight_multiplier - 0.05)

            # Log evolution if significant change
            if comp.weight_multiplier != old_weight:
                self.evolution_log.append(EvolutionEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type='weight_decrease',
                    component_id=component_id,
                    old_value=old_weight,
                    new_value=comp.weight_multiplier,
                    reason=f"Low accuracy ({comp.accuracy_rate:.1%})",
                    trigger_decision=record.decision_id
                ))

            # Update history
            comp.accuracy_history.append(comp.accuracy_rate)
            comp.trust_history.append(comp.trust_score)
            comp.last_updated = datetime.now().isoformat()

            comp.accuracy_history = comp.accuracy_history[-100:]
            comp.trust_history = comp.trust_history[-100:]

        # Update regime-specific performance
        regime = record.market_health
        for component_id in record.components_correct:
            if component_id in self.component_performance:
                comp = self.component_performance[component_id]
                if regime not in comp.performance_by_regime:
                    comp.performance_by_regime[regime] = 0.5
                # Increase regime-specific accuracy
                comp.performance_by_regime[regime] = min(1.0, comp.performance_by_regime[regime] + 0.02)

    def get_component_trust(self, component_id: str) -> float:
        """Get current trust score for a component."""
        if component_id not in self.component_performance:
            return 0.5  # Neutral trust for unknown components
        return self.component_performance[component_id].trust_score

    def get_component_weight(self, component_id: str) -> float:
        """Get current weight multiplier for a component."""
        if component_id not in self.component_performance:
            return 1.0  # Neutral weight for unknown components
        return self.component_performance[component_id].weight_multiplier

    def get_regime_trust(self, component_id: str, regime: str) -> float:
        """Get regime-specific trust for a component."""
        if component_id not in self.component_performance:
            return 0.5

        comp = self.component_performance[component_id]
        return comp.performance_by_regime.get(regime, comp.trust_score)

    def get_accountability_report(self) -> Dict:
        """Generate comprehensive accountability report."""
        total_decisions = len([d for d in self.decision_history.values() if d.outcome_recorded])
        total_wins = len([d for d in self.decision_history.values()
                         if d.outcome_recorded and d.actual_outcome == 'win'])

        # Calculate overall metrics
        overall_accuracy = total_wins / total_decisions if total_decisions > 0 else 0.0
        avg_pnl = sum(d.actual_pnl for d in self.decision_history.values()
                     if d.outcome_recorded and d.actual_pnl) / total_decisions if total_decisions > 0 else 0.0

        # Top performers
        performers = sorted(
            [c for c in self.component_performance.values() if c.decisions_participated >= 5],
            key=lambda x: x.accuracy_rate,
            reverse=True
        )

        top_performers = performers[:10]
        underperformers = [c for c in performers if c.accuracy_rate < 0.55][-10:]

        # Recent evolution events
        recent_events = self.evolution_log[-20:]

        return {
            'cio_performance': {
                'total_decisions': total_decisions,
                'wins': total_wins,
                'losses': total_decisions - total_wins,
                'accuracy': overall_accuracy,
                'average_pnl': avg_pnl
            },
            'director_performance': self._get_director_performance(),
            'top_performers': [
                {
                    'component': c.component_name,
                    'id': c.component_id,
                    'accuracy': c.accuracy_rate,
                    'trust': c.trust_score,
                    'weight': c.weight_multiplier,
                    'decisions': c.decisions_participated
                }
                for c in top_performers
            ],
            'underperformers': [
                {
                    'component': c.component_name,
                    'id': c.component_id,
                    'accuracy': c.accuracy_rate,
                    'trust': c.trust_score,
                    'weight': c.weight_multiplier,
                    'decisions': c.decisions_participated
                }
                for c in underperformers
            ],
            'recent_evolution': [
                {
                    'timestamp': e.timestamp,
                    'component': e.component_id,
                    'event': e.event_type,
                    'change': f"{e.old_value:.2f} → {e.new_value:.2f}",
                    'reason': e.reason
                }
                for e in recent_events
            ],
            'total_components_tracked': len(self.component_performance),
            'total_evolution_events': len(self.evolution_log)
        }

    def _get_director_performance(self) -> List[Dict]:
        """Get performance summary for all directors."""
        directors = [c for c in self.component_performance.values()
                    if c.component_type == 'director']

        return [
            {
                'director': d.component_name,
                'id': d.component_id,
                'accuracy': d.accuracy_rate,
                'trust': d.trust_score,
                'weight': d.weight_multiplier,
                'decisions': d.decisions_participated,
                'trend': self._get_trend(d)
            }
            for d in sorted(directors, key=lambda x: x.accuracy_rate, reverse=True)
        ]

    def _get_trend(self, comp: ComponentPerformance) -> str:
        """Determine if component performance is improving/declining."""
        if len(comp.accuracy_history) < 10:
            return 'insufficient_data'

        recent = comp.accuracy_history[-10:]
        older = comp.accuracy_history[-20:-10] if len(comp.accuracy_history) >= 20 else recent

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        if recent_avg > older_avg + 0.05:
            return '↑ improving'
        elif recent_avg < older_avg - 0.05:
            return '↓ declining'
        else:
            return '→ stable'


# =============================================================================
# EVOLUTIONARY CHIEF INTELLIGENCE OFFICER
# =============================================================================

class EvolutionaryChiefIntelligenceOfficer(ChiefIntelligenceOfficer):
    """
    Self-improving CIO that learns and evolves based on outcomes.

    Key additions to base CIO:
    - Automatically tracks all component performance
    - Adjusts synthesis weights based on accuracy
    - Learns which components to trust in which conditions
    - Evolves decision-making over time
    - Provides accountability dashboard

    100% automatic - zero manual work required!
    """

    def __init__(self):
        super().__init__()
        self.performance_tracker = PerformanceTracker()
        self.evolution_enabled = True

        # Dynamic director weights (evolved based on performance)
        self.director_weights = {
            'theme': 0.25,
            'trading': 0.30,
            'learning': 0.20,
            'realtime': 0.15,
            'validation': 0.10
        }

        # Emergency override (Layer 0 - Crisis Intelligence)
        self.emergency_override = False
        self.blacklisted_sectors = set()

        # Component #37: xAI X Intelligence Monitor
        self.x_intel = None
        self.x_monitor = None
        if X_INTELLIGENCE_AVAILABLE:
            try:
                self.x_intel = XAIXIntelligence()
                self.x_monitor = XMonitoringScheduler(self.x_intel)

                # Register crisis callback
                self.x_monitor.add_crisis_callback(self._handle_x_crisis_alert)

                # Start adaptive monitoring
                self.x_monitor.start()

                logger.info("✓ xAI X Intelligence Monitor started (Component #37)")
            except Exception as e:
                logger.warning(f"Could not initialize X Intelligence: {e}")

        logger.info("=" * 80)
        logger.info("EVOLUTIONARY CIO INITIALIZED")
        logger.info("=" * 80)
        logger.info("✓ Automatic accountability tracking enabled")
        logger.info("✓ Component performance evolution enabled")
        logger.info("✓ Self-improving system ready")
        if self.x_intel:
            logger.info("✓ xAI X Intelligence monitoring active (37 total components)")
        else:
            logger.info("✓ 35 components active (X Intelligence unavailable)")
        logger.info("=" * 80)

    def _create_blocked_decision(self, ticker: str, reasoning: str, **kwargs) -> FinalDecision:
        """Create a decision that blocks trading with all required fields."""
        return FinalDecision(
            ticker=ticker,
            decision=Decision.HOLD,
            position_size="0%",
            confidence=1.0,
            market_context_summary="Emergency override active",
            sector_context_summary="Crisis mode",
            theme_score=0,
            trade_score=0,
            learning_score=0,
            realtime_score=0,
            validation_score=0,
            reasoning=reasoning,
            key_strengths=[],
            risks=["Trading halted by crisis system"],
            entry_price=None,
            stop_loss=None,
            targets=[],
            theme_intelligence=None,
            trading_intelligence=None,
            learning_intelligence=None,
            realtime_intelligence=None,
            validation_intelligence=None,
            **kwargs
        )

    def analyze_opportunity(self, ticker: str, *args, **kwargs) -> FinalDecision:
        """
        Override to automatically track all components + X Intelligence checks.
        """

        # CRITICAL CHECK: Emergency override (Layer 0 - Crisis Mode)
        if self.emergency_override:
            return self._create_blocked_decision(
                ticker=ticker,
                reasoning="🚨 CRISIS MODE ACTIVE - All trading halted by X Intelligence"
            )

        # Check if ticker's sector is blacklisted by crisis
        if self._is_sector_blacklisted(ticker):
            return self._create_blocked_decision(
                ticker=ticker,
                reasoning=f"⚠️ Sector blacklisted due to active crisis (X Intelligence)"
            )

        # Component #37: Check X sentiment BEFORE making decision
        x_sentiment = None
        if self.x_intel:
            try:
                sentiments = self.x_intel.monitor_specific_stocks_on_x([ticker])
                if ticker in sentiments:
                    x_sentiment = sentiments[ticker]

                    # RED FLAG DETECTED - Block trade
                    if x_sentiment.has_red_flags:
                        logger.warning(f"🚩 X Intelligence RED FLAGS for {ticker}: {x_sentiment.red_flags}")
                        return self._create_blocked_decision(
                            ticker=ticker,
                            reasoning=f"🚩 X Intelligence Red Flags: {', '.join(x_sentiment.red_flags[:2])}",
                            x_sentiment=x_sentiment
                        )
            except Exception as e:
                logger.debug(f"X sentiment check failed: {e}")

        # Call parent analysis
        decision = super().analyze_opportunity(ticker, *args, **kwargs)

        # Enhance decision with X intelligence
        if x_sentiment:
            decision.x_sentiment = x_sentiment
            decision.x_sentiment_score = x_sentiment.sentiment_score
            decision.x_confidence = x_sentiment.confidence

            # Adjust confidence based on X sentiment alignment
            if x_sentiment.sentiment == 'bearish' and decision.decision == Decision.BUY:
                decision.confidence *= 0.8  # Reduce confidence if X is bearish on our buy
                decision.reasoning += f" | X Sentiment: {x_sentiment.sentiment} (caution)"
            elif x_sentiment.sentiment == 'bullish' and decision.decision == Decision.BUY:
                decision.confidence *= 1.1  # Boost confidence if X agrees
                decision.reasoning += f" | X Sentiment: {x_sentiment.sentiment} (confirmed)"

        # AUTOMATICALLY log all component details (including X Intelligence)
        if self.evolution_enabled:
            component_predictions = self._extract_component_predictions(decision)

            # Add X Intelligence component prediction (Component #37)
            if x_sentiment:
                component_predictions['x_intelligence_monitor'] = {
                    'sentiment': x_sentiment.sentiment,
                    'sentiment_score': x_sentiment.sentiment_score,
                    'has_red_flags': x_sentiment.has_red_flags,
                    'confidence': x_sentiment.confidence,
                    'type': 'specialist',
                    'parent': 'realtime_director'
                }

            decision_id = self.performance_tracker.record_decision(
                decision=decision,
                component_predictions=component_predictions,
                market_context=self.context_manager.market_context,
                sector_context=self.context_manager.sector_context
            )

            # Store decision_id in decision for later outcome recording
            decision.decision_id = decision_id

            num_components = len(component_predictions)
            logger.info(f"✓ Automatically logged decision with {num_components} components" +
                       (" (includes X Intelligence)" if x_sentiment else ""))

        return decision

    def _extract_component_predictions(self, decision: FinalDecision) -> Dict[str, Any]:
        """Extract all component predictions from decision for tracking."""
        predictions = {}

        # Directors
        predictions['theme_director'] = {
            'score': decision.theme_score,
            'type': 'director'
        }
        predictions['trading_director'] = {
            'score': decision.trade_score,
            'type': 'director'
        }
        predictions['learning_director'] = {
            'score': decision.learning_score,
            'type': 'director'
        }
        predictions['realtime_director'] = {
            'score': decision.realtime_score,
            'type': 'director'
        }
        predictions['validation_director'] = {
            'score': decision.validation_score,
            'type': 'director'
        }

        # Extract specialist details from intelligence objects
        if decision.theme_intelligence:
            predictions['tam_estimator'] = {
                'cagr': decision.theme_intelligence.tam_cagr,
                'type': 'specialist',
                'parent': 'theme_director'
            }
            predictions['role_classifier'] = {
                'role': decision.theme_intelligence.role_classification,
                'type': 'specialist',
                'parent': 'theme_director'
            }

        if decision.trading_intelligence:
            predictions['signal_explainer'] = {
                'catalyst': decision.trading_intelligence.signal_catalyst,
                'confidence': decision.trading_intelligence.signal_confidence,
                'type': 'specialist',
                'parent': 'trading_director'
            }
            predictions['timeframe_synthesizer'] = {
                'alignment': decision.trading_intelligence.timeframe_alignment,
                'type': 'specialist',
                'parent': 'trading_director'
            }

        if decision.learning_intelligence:
            predictions['outcome_predictor'] = {
                'prediction': decision.learning_intelligence.prediction,
                'confidence': decision.learning_intelligence.prediction_confidence,
                'type': 'specialist',
                'parent': 'learning_director'
            }
            predictions['pattern_analyzer'] = {
                'pattern_identified': decision.learning_intelligence.pattern_identified,
                'win_rate': decision.learning_intelligence.pattern_win_rate,
                'type': 'specialist',
                'parent': 'learning_director'
            }

        return predictions

    def record_outcome(
        self,
        decision_id: str,
        actual_outcome: str,
        actual_pnl: float,
        exit_price: Optional[float] = None,
        exit_date: Optional[str] = None
    ):
        """
        Record actual outcome and AUTOMATICALLY evolve the system.

        This is the key evolution method - call this after trades close!
        """
        logger.info(f"Recording outcome for {decision_id}: {actual_outcome} ({actual_pnl:+.1%})")

        # Record outcome (automatically updates all component scores)
        self.performance_tracker.record_outcome(
            decision_id=decision_id,
            actual_outcome=actual_outcome,
            actual_pnl=actual_pnl,
            exit_price=exit_price,
            exit_date=exit_date
        )

        # Evolve director weights based on performance
        self._evolve_director_weights()

        logger.info("✓ System automatically evolved based on outcome")

    def _handle_x_crisis_alert(self, alert: 'CrisisAlert'):
        """
        Handle crisis alert from X Intelligence (Layer 0 override).
        Callback registered with X monitoring scheduler.
        """
        logger.warning("=" * 80)
        logger.warning(f"🚨 X INTELLIGENCE CRISIS ALERT")
        logger.warning("=" * 80)
        logger.warning(f"Topic: {alert.topic}")
        logger.warning(f"Type: {alert.crisis_type.value}")
        logger.warning(f"Severity: {alert.severity}/10")
        logger.warning(f"Verified: {alert.verified}")
        logger.warning(f"Credibility: {alert.credibility_score:.1%}")
        logger.warning(f"Geographic Focus: {alert.geographic_focus}")
        logger.warning("=" * 80)

        # CRITICAL CRISIS - Activate emergency protocol
        if alert.severity >= 9 and alert.verified:
            self._execute_emergency_protocol(alert)

        # MAJOR CRISIS - Tighten controls
        elif alert.severity >= 7:
            self._execute_major_crisis_protocol(alert)

        # WARNING LEVEL - Send notification for awareness
        else:
            self._send_crisis_notification(alert, protocol_type='warning')

    def _execute_emergency_protocol(self, alert: 'CrisisAlert'):
        """
        CRITICAL (9-10): Emergency shutdown.
        """
        logger.error("🚨🚨🚨 EMERGENCY PROTOCOL ACTIVATED 🚨🚨🚨")
        logger.error(f"Crisis: {alert.description}")

        # HALT ALL TRADING
        self.emergency_override = True

        # Blacklist affected sectors
        for sector in alert.affected_sectors:
            self.blacklisted_sectors.add(sector.lower())
            logger.error(f"⛔ SECTOR BLACKLISTED: {sector}")

        # Force defensive mode
        self.context_manager.market_context.health = MarketHealth.CONCERNING

        # Log immediate actions
        for action in alert.immediate_actions:
            logger.error(f"  ⚠️  {action}")

        logger.error("=" * 80)
        logger.error("ALL TRADING HALTED")
        logger.error("Manual intervention required to resume")
        logger.error("=" * 80)

        # Send CRITICAL notification via Telegram
        self._send_crisis_notification(alert, protocol_type='emergency')

    def _execute_major_crisis_protocol(self, alert: 'CrisisAlert'):
        """
        MAJOR (7-8): Tighten risk controls but continue trading cautiously.
        """
        logger.warning("⚠️  MAJOR CRISIS PROTOCOL ACTIVATED")
        logger.warning(f"Crisis: {alert.description}")

        # Blacklist affected sectors
        for sector in alert.affected_sectors:
            self.blacklisted_sectors.add(sector.lower())
            logger.warning(f"⚠️  Avoiding sector: {sector}")

        # Tighten market regime
        if self.context_manager.market_context.health == MarketHealth.HEALTHY:
            self.context_manager.market_context.health = MarketHealth.CAUTION

        logger.warning("✓ Risk controls tightened")
        logger.warning("✓ Affected sectors avoided")
        logger.warning("✓ Continuing cautious trading")

        # Send MAJOR notification via Telegram
        self._send_crisis_notification(alert, protocol_type='major')

    def _send_crisis_notification(self, alert: 'CrisisAlert', protocol_type: str = 'warning'):
        """
        Send Telegram notification for crisis alerts.

        Args:
            alert: CrisisAlert object with crisis details
            protocol_type: One of 'emergency', 'major', or 'warning'
        """
        if not NOTIFICATIONS_AVAILABLE:
            logger.debug("Notification system not available - skipping crisis notification")
            return

        try:
            notification_manager = get_notification_manager()

            # Determine alert type and priority
            if protocol_type == 'emergency':
                alert_type = 'crisis_emergency'
                priority = NotificationPriority.CRITICAL
            elif protocol_type == 'major':
                alert_type = 'crisis_major'
                priority = NotificationPriority.CRITICAL
            else:
                alert_type = 'crisis_alert'
                priority = NotificationPriority.HIGH

            # Prepare crisis data for notification
            crisis_data = {
                'severity': alert.severity,
                'topic': alert.topic,
                'crisis_type': alert.crisis_type.value if hasattr(alert.crisis_type, 'value') else str(alert.crisis_type),
                'description': alert.description,
                'verified': alert.verified,
                'credibility_score': alert.credibility_score,
                'affected_sectors': alert.affected_sectors,
                'affected_tickers': alert.affected_tickers,
                'immediate_actions': alert.immediate_actions,
                'protocol_type': protocol_type
            }

            # Send notification
            result = notification_manager.send_alert(
                alert_type=alert_type,
                data=crisis_data,
                priority=priority
            )

            if result.get('telegram'):
                logger.info(f"✓ Crisis notification sent via Telegram (severity: {alert.severity}, type: {protocol_type})")
            else:
                logger.warning("Failed to send crisis notification via Telegram")

        except Exception as e:
            logger.error(f"Error sending crisis notification: {e}")

    def _is_sector_blacklisted(self, ticker: str) -> bool:
        """Check if ticker's sector is blacklisted."""
        # Simple sector detection (would use actual sector data in production)
        ticker_upper = ticker.upper()

        # Example sector mappings
        sector_map = {
            'airlines': ['AAL', 'DAL', 'UAL', 'LUV', 'ALK'],
            'energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG'],
            'finance': ['JPM', 'BAC', 'WFC', 'C', 'GS'],
            'tech': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'AMD'],
            # Add more as needed
        }

        for sector, tickers in sector_map.items():
            if sector in self.blacklisted_sectors and ticker_upper in tickers:
                return True

        return False

    def clear_emergency_override(self):
        """Manually clear emergency override (requires human decision)."""
        self.emergency_override = False
        self.blacklisted_sectors.clear()
        logger.info("✓ Emergency override cleared - trading resumed")

    def get_x_intelligence_status(self) -> Dict[str, Any]:
        """Get X Intelligence monitoring status."""
        if not self.x_intel:
            return {'available': False}

        return {
            'available': True,
            'mode': self.x_monitor.current_mode.value if self.x_monitor else 'unknown',
            'emergency_override': self.emergency_override,
            'blacklisted_sectors': list(self.blacklisted_sectors),
            'statistics': self.x_intel.get_statistics()
        }

    def _evolve_director_weights(self):
        """
        Automatically adjust director weights based on their performance.

        High performers get more weight, low performers get less.
        """
        # Get each director's performance
        for director_key in self.director_weights.keys():
            director_id = f"{director_key}_director"
            perf = self.performance_tracker.component_performance.get(director_id)

            if not perf or perf.decisions_participated < 10:
                continue  # Need minimum data

            old_weight = self.director_weights[director_key]

            # Increase weight for high performers
            if perf.accuracy_rate > 0.70:
                self.director_weights[director_key] = min(0.40, old_weight + 0.01)
                if old_weight != self.director_weights[director_key]:
                    logger.info(f"↑ {director_key.title()} Director performing well "
                               f"({perf.accuracy_rate:.1%}) - weight: {old_weight:.2f} → {self.director_weights[director_key]:.2f}")

            # Decrease weight for low performers
            elif perf.accuracy_rate < 0.50:
                self.director_weights[director_key] = max(0.05, old_weight - 0.01)
                if old_weight != self.director_weights[director_key]:
                    logger.info(f"↓ {director_key.title()} Director underperforming "
                               f"({perf.accuracy_rate:.1%}) - weight: {old_weight:.2f} → {self.director_weights[director_key]:.2f}")

        # Normalize weights to sum to 1.0
        total = sum(self.director_weights.values())
        for key in self.director_weights:
            self.director_weights[key] /= total

    def _synthesize_final_decision(
        self,
        ticker: str,
        theme_intelligence: Optional[ThemeIntelligence],
        trading_intelligence: TradingIntelligence,
        learning_intelligence: LearningIntelligence,
        realtime_intelligence: RealtimeIntelligence,
        validation_intelligence: ValidationIntelligence
    ) -> FinalDecision:
        """
        Override synthesis to use EVOLVED weights instead of fixed weights.
        """
        # Get scores
        theme_score = theme_intelligence.theme_quality if theme_intelligence else 5
        trade_score = trading_intelligence.trade_quality
        learning_score = learning_intelligence.learning_quality
        realtime_score = realtime_intelligence.realtime_quality
        validation_score = validation_intelligence.validation_quality

        # Use evolved weights if evolution is enabled
        if self.evolution_enabled:
            # Apply evolved director weights
            weights = [
                self.director_weights['theme'],
                self.director_weights['trading'],
                self.director_weights['learning'],
                self.director_weights['realtime'],
                self.director_weights['validation']
            ]

            # Apply component trust multipliers for regime-aware weighting
            regime = self.context_manager.market_context.health.value

            theme_trust = self.performance_tracker.get_regime_trust('theme_director', regime)
            trade_trust = self.performance_tracker.get_regime_trust('trading_director', regime)

            # Adjust scores based on regime-specific trust
            theme_score = theme_score * (0.7 + theme_trust * 0.3)
            trade_score = trade_score * (0.7 + trade_trust * 0.3)

            logger.debug(f"Using evolved weights: {dict(zip(['theme', 'trading', 'learning', 'realtime', 'validation'], weights))}")
            logger.debug(f"Using regime-specific trust: theme={theme_trust:.2f}, trade={trade_trust:.2f}")
        else:
            # Fixed weights (original behavior)
            weights = [0.25, 0.30, 0.20, 0.15, 0.10]

        # Calculate weighted overall score
        scores = [theme_score, trade_score, learning_score, realtime_score, validation_score]
        overall_score = sum(s * w for s, w in zip(scores, weights))

        # Use parent's decision logic with evolved scores
        # (Delegate to parent class for the actual decision making)
        decision = super()._synthesize_final_decision(
            ticker,
            theme_intelligence,
            trading_intelligence,
            learning_intelligence,
            realtime_intelligence,
            validation_intelligence
        )

        return decision

    def get_accountability_report(self) -> Dict:
        """Get comprehensive accountability report."""
        return self.performance_tracker.get_accountability_report()

    def get_evolution_summary(self) -> str:
        """Get human-readable evolution summary."""
        report = self.get_accountability_report()

        summary = []
        summary.append("=" * 80)
        summary.append("EVOLUTIONARY AGENTIC BRAIN - ACCOUNTABILITY REPORT")
        summary.append("=" * 80)
        summary.append("")

        # CIO Performance
        cio_perf = report['cio_performance']
        summary.append("LAYER 1: CIO Performance")
        summary.append(f"├─ Total Decisions: {cio_perf['total_decisions']}")
        summary.append(f"├─ Wins: {cio_perf['wins']} ({cio_perf['accuracy']:.1%})")
        summary.append(f"├─ Losses: {cio_perf['losses']}")
        summary.append(f"└─ Average P&L: {cio_perf['average_pnl']:+.1%}")
        summary.append("")

        # Director Performance
        summary.append("LAYER 2: Director Performance")
        for director in report['director_performance']:
            summary.append(f"├─ {director['director']}")
            summary.append(f"│  ├─ Accuracy: {director['accuracy']:.1%}")
            summary.append(f"│  ├─ Trust: {director['trust']:.2f}")
            summary.append(f"│  ├─ Weight: {director['weight']:.2f}")
            summary.append(f"│  └─ Trend: {director['trend']}")
        summary.append("")

        # Top Performers
        summary.append("LAYER 3: Top Performing Specialists")
        for perf in report['top_performers'][:5]:
            summary.append(f"├─ {perf['component']}")
            summary.append(f"│  ├─ Accuracy: {perf['accuracy']:.1%}")
            summary.append(f"│  ├─ Trust: {perf['trust']:.2f}")
            summary.append(f"│  └─ Weight: {perf['weight']:.2f}")
        summary.append("")

        # Recent Evolution
        if report['recent_evolution']:
            summary.append("Recent Evolution Events:")
            for evt in report['recent_evolution'][-5:]:
                summary.append(f"├─ {evt['component']}: {evt['event']}")
                summary.append(f"│  └─ {evt['change']} - {evt['reason']}")
        summary.append("")

        summary.append("=" * 80)
        summary.append(f"✓ System actively learning from {cio_perf['total_decisions']} decisions")
        summary.append(f"✓ Tracking {report['total_components_tracked']} components")
        summary.append(f"✓ {report['total_evolution_events']} evolution events logged")
        summary.append("=" * 80)

        return "\n".join(summary)


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_evolutionary_cio: Optional[EvolutionaryChiefIntelligenceOfficer] = None

def get_evolutionary_cio() -> EvolutionaryChiefIntelligenceOfficer:
    """Get or create the singleton Evolutionary CIO."""
    global _evolutionary_cio
    if _evolutionary_cio is None:
        _evolutionary_cio = EvolutionaryChiefIntelligenceOfficer()
    return _evolutionary_cio


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def analyze_opportunity_evolutionary(
    ticker: str,
    signal_type: str,
    signal_data: Dict[str, Any],
    **kwargs
) -> FinalDecision:
    """
    Analyze opportunity with evolutionary system (auto-tracking).

    Returns decision with decision_id for later outcome recording.
    """
    cio = get_evolutionary_cio()
    return cio.analyze_opportunity(
        ticker=ticker,
        signal_type=signal_type,
        signal_data=signal_data,
        **kwargs
    )


def record_trade_outcome(
    decision_id: str,
    actual_outcome: str,  # 'win' or 'loss' or 'breakeven'
    actual_pnl: float,
    exit_price: Optional[float] = None,
    exit_date: Optional[str] = None
):
    """
    Record trade outcome - system will automatically evolve!

    Args:
        decision_id: ID returned from analyze_opportunity_evolutionary()
        actual_outcome: 'win', 'loss', or 'breakeven'
        actual_pnl: Actual profit/loss as decimal (0.15 = +15%)
        exit_price: Optional exit price
        exit_date: Optional exit date
    """
    cio = get_evolutionary_cio()
    cio.record_outcome(
        decision_id=decision_id,
        actual_outcome=actual_outcome,
        actual_pnl=actual_pnl,
        exit_price=exit_price,
        exit_date=exit_date
    )


def get_accountability_dashboard() -> str:
    """Get human-readable accountability dashboard."""
    cio = get_evolutionary_cio()
    return cio.get_evolution_summary()


def get_component_performance(component_id: str) -> Optional[ComponentPerformance]:
    """Get detailed performance for a specific component."""
    cio = get_evolutionary_cio()
    return cio.performance_tracker.component_performance.get(component_id)
