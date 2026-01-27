"""
Intelligence Module
====================
Advanced analytics and signal fusion for institutional-grade analysis.

Components:
- ThemeIntelligenceHub: Multi-signal theme detection and lifecycle tracking
- ThemeDiscoveryEngine: Automatic theme discovery
- InstitutionalFlowTracker: Options flow, 13F, insider clusters
- RotationPredictor: Theme rotation forecasting
"""

# Theme Intelligence Hub
from .theme_intelligence import (
    ThemeIntelligenceHub,
    ThemeLifecycle,
    ThemeSignal,
    ThemeAlert,
    get_theme_hub,
    analyze_all_themes,
    get_ticker_theme_boost,
    get_breakout_alerts,
    get_theme_radar,
    THEME_TICKER_MAP,
    THEME_NAMES,
)

# Theme Discovery
from .theme_discovery import (
    ThemeDiscoveryEngine,
    DiscoveredTheme,
    TrendingKeyword,
    get_discovery_engine,
    discover_themes,
    get_discovery_report,
)

# Institutional Flow
from .institutional_flow import (
    InstitutionalFlowTracker,
    OptionsFlowSignal,
    ThirteenFCluster,
    InsiderCluster,
    InstitutionalSignal,
    get_flow_tracker,
    get_institutional_summary,
    get_options_flow,
    get_insider_clusters,
)

# Rotation Predictor
from .rotation_predictor import (
    RotationPredictor,
    RotationSignal,
    RotationForecast,
    PeakWarning,
    get_rotation_predictor,
    get_rotation_forecast,
    get_peak_warnings,
    get_reversion_candidates,
    get_rotation_alerts,
)

__all__ = [
    # Theme Intelligence
    'ThemeIntelligenceHub',
    'ThemeLifecycle',
    'ThemeSignal',
    'ThemeAlert',
    'get_theme_hub',
    'analyze_all_themes',
    'get_ticker_theme_boost',
    'get_breakout_alerts',
    'get_theme_radar',
    'THEME_TICKER_MAP',
    'THEME_NAMES',

    # Theme Discovery
    'ThemeDiscoveryEngine',
    'DiscoveredTheme',
    'TrendingKeyword',
    'get_discovery_engine',
    'discover_themes',
    'get_discovery_report',

    # Institutional Flow
    'InstitutionalFlowTracker',
    'OptionsFlowSignal',
    'ThirteenFCluster',
    'InsiderCluster',
    'InstitutionalSignal',
    'get_flow_tracker',
    'get_institutional_summary',
    'get_options_flow',
    'get_insider_clusters',

    # Rotation Predictor
    'RotationPredictor',
    'RotationSignal',
    'RotationForecast',
    'PeakWarning',
    'get_rotation_predictor',
    'get_rotation_forecast',
    'get_peak_warnings',
    'get_reversion_candidates',
    'get_rotation_alerts',
]
