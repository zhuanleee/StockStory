"""
Core Type Definitions for Learning System

Contains all enums and dataclasses used across the learning system.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class ParameterCategory(Enum):
    """Categories of learnable parameters"""
    SCORING_WEIGHT = 'scoring_weight'
    THRESHOLD = 'threshold'
    MULTIPLIER = 'multiplier'
    ROLE_SCORE = 'role_score'
    TIME_WINDOW = 'time_window'
    KEYWORD_WEIGHT = 'keyword_weight'
    DECAY_RATE = 'decay_rate'
    TECHNICAL = 'technical'


class LearningStatus(Enum):
    """Status of a parameter's learning lifecycle"""
    STATIC = 'static'  # Never learned, using default
    LEARNING = 'learning'  # Currently collecting data
    EXPERIMENTING = 'experimenting'  # In A/B test
    SHADOW = 'shadow'  # Testing in shadow mode
    VALIDATED = 'validated'  # Passed validation, ready to deploy
    DEPLOYED = 'deployed'  # Actively learned and deployed
    ROLLED_BACK = 'rolled_back'  # Was deployed but rolled back


@dataclass
class ParameterDefinition:
    """Definition of a learnable parameter"""
    name: str
    current_value: float
    default_value: float
    min_value: float
    max_value: float
    category: str
    description: str
    affects: List[str]
    source_file: str
    source_line: int
    status: str = 'static'
    learned_from_samples: int = 0
    confidence: float = 0.0
    last_updated: Optional[str] = None
    last_optimized: Optional[str] = None

    # Bayesian posterior parameters (Beta distribution for rates, Normal for values)
    alpha: float = 1.0  # Beta prior alpha (successes + 1)
    beta: float = 1.0   # Beta prior beta (failures + 1)
    mean: float = 0.0   # Normal posterior mean
    variance: float = 1.0  # Normal posterior variance


@dataclass
class OutcomeRecord:
    """Record of an alert outcome with parameter attribution"""
    alert_id: str
    ticker: str
    timestamp: str
    score: float
    parameters_used: Dict[str, float]
    score_breakdown: Dict[str, Dict[str, float]]
    outcomes: Dict[str, float]  # {'1d': 3.2, '3d': 5.1, '5d': 2.8}
    outcome_class: str  # 'win', 'loss', 'neutral'
    market_regime: str


@dataclass
class Experiment:
    """A/B test experiment definition"""
    experiment_id: str
    parameter_name: str
    variants: List[float]
    control_value: float
    start_time: str
    end_time: Optional[str]
    status: str  # 'running', 'completed', 'cancelled'
    min_samples_per_variant: int
    assignments: Dict[str, int]  # ticker -> variant_index
    outcomes: Dict[int, List[float]]  # variant_index -> list of outcomes
    winner: Optional[int] = None
    p_value: Optional[float] = None
    improvement: Optional[float] = None
