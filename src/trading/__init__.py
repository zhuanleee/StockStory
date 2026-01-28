"""
Trade Management System

Story-First Trading with AI-powered exit signals and professional scaling.

Components:
- models: Core data structures (Trade, Tranche, ScalingPlan)
- trade_manager: Trade CRUD and persistence
- exit_scanner: Story → AI → Technical exit signal detection
- scaling_engine: Scale-in/scale-out with AI advisor
- risk_advisor: Confidence-based risk advisory
"""

from .models import (
    Tranche,
    Trade,
    ScalingPlan,
    ExitSignal,
    RiskLevel,
    SignalSource,
    TradeStatus,
    ScalingStrategy,
)
from .trade_manager import TradeManager
from .exit_scanner import ExitScanner
from .scaling_engine import ScalingEngine
from .risk_advisor import RiskAdvisor
from .scan_integration import TradeScanIntegration, scan_positions, scan_ticker, get_daily_report
from .telegram_commands import TradeCommandHandler, handle_trade_command

__all__ = [
    # Models
    'Tranche',
    'Trade',
    'ScalingPlan',
    'ExitSignal',
    'RiskLevel',
    'SignalSource',
    'TradeStatus',
    'ScalingStrategy',
    # Managers
    'TradeManager',
    'ExitScanner',
    'ScalingEngine',
    'RiskAdvisor',
    # Integration
    'TradeScanIntegration',
    'scan_positions',
    'scan_ticker',
    'get_daily_report',
    # Telegram
    'TradeCommandHandler',
    'handle_trade_command',
]
