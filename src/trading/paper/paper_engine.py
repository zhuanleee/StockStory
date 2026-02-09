"""
Paper Trading Engine — Cert session, order execution, position sync.

Uses Tastytrade certification (sandbox) API with is_test=True.
All tastytrade SDK v12+ methods are async.
"""

import os
import logging
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

from .risk_manager import RiskManager, load_config, save_config
from .journal import TradeJournal

logger = logging.getLogger(__name__)

# Cert session cache (separate from production data session)
_cert_session = None
_cert_session_expiry = None
_cert_account = None


async def get_cert_session():
    """Get or create Tastytrade cert session for paper trading."""
    global _cert_session, _cert_session_expiry, _cert_account

    if _cert_session and _cert_session_expiry and datetime.now() < _cert_session_expiry:
        return _cert_session, _cert_account

    from tastytrade import Session, Account

    # Cert environment needs its own OAuth credentials (separate from production)
    client_secret = os.environ.get('TASTYTRADE_CERT_CLIENT_SECRET',
                                    os.environ.get('TASTYTRADE_CLIENT_SECRET'))
    refresh_token = os.environ.get('TASTYTRADE_CERT_REFRESH_TOKEN',
                                    os.environ.get('TASTYTRADE_REFRESH_TOKEN'))

    if not client_secret or not refresh_token:
        raise ValueError("Tastytrade credentials not configured")

    try:
        session = Session(client_secret, refresh_token, is_test=True)
        accounts = await Account.get(session)
        if not accounts:
            raise ValueError("No accounts found on cert session")
        if isinstance(accounts, list):
            account = accounts[0]
        else:
            account = accounts

        # Only cache after successful account fetch
        _cert_session = session
        _cert_session_expiry = datetime.now() + timedelta(minutes=14)
        _cert_account = account

        logger.info(f"Cert session created, account: {_cert_account.account_number}")
        return _cert_session, _cert_account
    except Exception as e:
        # Don't cache failed sessions
        _cert_session = None
        _cert_session_expiry = None
        _cert_account = None
        raise


def invalidate_cert_session():
    global _cert_session, _cert_session_expiry, _cert_account
    _cert_session = None
    _cert_session_expiry = None
    _cert_account = None


class PaperEngine:
    def __init__(self, volume_path: str):
        self.volume_path = volume_path
        self.journal = TradeJournal(volume_path)
        self.risk_manager = RiskManager(volume_path)
        self.config = load_config(volume_path)
        # Phase 1a-1c, 3a-3c, 4c: Adaptive systems
        try:
            from .adaptive_engine import (
                SignalPerformanceTracker, AdaptiveWeights,
                AdaptiveExitEngine, EdgeScoreEngine,
                StrategySelector, KellyPositionSizer,
                FlowToxicityAnalyzer, LearningTierConnector,
                ABTestEngine,
            )
            self.perf_tracker = SignalPerformanceTracker(volume_path)
            self.adaptive_weights = AdaptiveWeights(volume_path)
            self.adaptive_exits = AdaptiveExitEngine(volume_path)
            self.edge_engine = EdgeScoreEngine()
            self.strategy_selector = StrategySelector()
            self.kelly_sizer = KellyPositionSizer()
            self.flow_analyzer = FlowToxicityAnalyzer()
            self.tier_connector = LearningTierConnector(volume_path)
            self.ab_engine = ABTestEngine(volume_path)
        except Exception as e:
            logger.warning(f"Adaptive systems init failed: {e}")
            self.perf_tracker = None
            self.adaptive_weights = None
            self.adaptive_exits = None
            self.edge_engine = None
            self.strategy_selector = None
            self.kelly_sizer = None
            self.flow_analyzer = None
            self.tier_connector = None
            self.ab_engine = None

    def reload_config(self):
        self.config = load_config(self.volume_path)
        self.risk_manager.reload()

    def get_config(self) -> dict:
        return load_config(self.volume_path)

    def update_config(self, updates: dict) -> dict:
        config = load_config(self.volume_path)
        config.update(updates)
        save_config(self.volume_path, config)
        self.config = config
        self.risk_manager.reload()
        return config

    # -------------------------------------------------------------------------
    # Account & Positions
    # -------------------------------------------------------------------------

    async def get_account_summary(self) -> Dict:
        """Get cert account summary: equity, cash, buying power, positions."""
        try:
            session, account = await get_cert_session()
            balances = await account.get_balances(session)

            equity = float(balances.net_liquidating_value)
            cash = float(balances.cash_balance)
            buying_power = float(balances.derivative_buying_power)

            # Record equity snapshot
            positions_value = equity - cash
            self.journal.record_equity_snapshot(equity, cash, positions_value)

            # Get starting capital for P&L calc
            starting = self.config.get('starting_capital', 50000)
            total_pnl = equity - starting
            total_pnl_pct = (total_pnl / starting) * 100 if starting > 0 else 0

            # Daily P&L from equity curve
            daily_pnl = 0
            curve = self.journal.get_equity_curve()
            if len(curve) >= 2:
                daily_pnl = equity - curve[-2]['equity']
            elif len(curve) == 1:
                daily_pnl = equity - starting

            return {
                'equity': round(equity, 2),
                'cash': round(cash, 2),
                'buying_power': round(buying_power, 2),
                'positions_value': round(positions_value, 2),
                'total_pnl': round(total_pnl, 2),
                'total_pnl_pct': round(total_pnl_pct, 2),
                'daily_pnl': round(daily_pnl, 2),
                'starting_capital': starting,
                'account_number': account.account_number,
            }
        except Exception as e:
            logger.error(f"Account summary error: {e}")
            # Fallback to journal-based data
            curve = self.journal.get_equity_curve()
            starting = self.config.get('starting_capital', 50000)
            last = curve[-1] if curve else {'equity': starting, 'cash': starting, 'positions_value': 0}
            daily_pnl = 0
            if len(curve) >= 2:
                daily_pnl = round(curve[-1]['equity'] - curve[-2]['equity'], 2)

            return {
                'equity': last['equity'],
                'cash': last['cash'],
                'buying_power': last['cash'],
                'positions_value': last['positions_value'],
                'total_pnl': round(last['equity'] - starting, 2),
                'total_pnl_pct': round((last['equity'] - starting) / starting * 100, 2) if starting > 0 else 0,
                'daily_pnl': daily_pnl,
                'starting_capital': starting,
                'account_number': 'offline',
                'error': str(e),
            }

    async def get_positions(self) -> List[Dict]:
        """Get open positions from TT cert with live marks."""
        try:
            session, account = await get_cert_session()
            positions = await account.get_positions(session)

            result = []
            for pos in positions:
                qty = int(pos.quantity)
                if qty == 0:
                    continue
                result.append({
                    'symbol': pos.symbol,
                    'instrument_type': str(pos.instrument_type),
                    'quantity': qty,
                    'direction': 'long' if qty > 0 else 'short',
                    'average_open_price': float(pos.average_open_price) if pos.average_open_price else 0,
                    'close_price': float(pos.close_price) if pos.close_price else 0,
                    'mark': float(pos.mark) if hasattr(pos, 'mark') and pos.mark else float(pos.close_price) if pos.close_price else 0,
                    'mark_price': float(pos.mark_price) if hasattr(pos, 'mark_price') and pos.mark_price else 0,
                    'cost_effect': str(pos.cost_effect) if hasattr(pos, 'cost_effect') else '',
                    'realized_day_gain': float(pos.realized_day_gain) if hasattr(pos, 'realized_day_gain') and pos.realized_day_gain else 0,
                    'unrealized_day_gain': float(pos.unrealized_day_gain) if hasattr(pos, 'unrealized_day_gain') and pos.unrealized_day_gain else 0,
                })

            return result
        except Exception as e:
            logger.error(f"Get positions error: {e}")
            return []

    async def get_orders(self, limit: int = 20) -> List[Dict]:
        """Get recent orders from TT cert."""
        try:
            session, account = await get_cert_session()
            orders = await account.get_live_orders(session)

            result = []
            for order in orders[:limit]:
                legs_info = []
                if hasattr(order, 'legs') and order.legs:
                    for leg in order.legs:
                        legs_info.append({
                            'symbol': leg.symbol if hasattr(leg, 'symbol') else '',
                            'action': str(leg.action) if hasattr(leg, 'action') else '',
                            'quantity': int(leg.quantity) if hasattr(leg, 'quantity') else 0,
                        })
                result.append({
                    'id': order.id if hasattr(order, 'id') else str(order),
                    'status': str(order.status) if hasattr(order, 'status') else 'unknown',
                    'order_type': str(order.order_type) if hasattr(order, 'order_type') else '',
                    'time_in_force': str(order.time_in_force) if hasattr(order, 'time_in_force') else '',
                    'price': float(order.price) if hasattr(order, 'price') and order.price else 0,
                    'legs': legs_info,
                    'received_at': str(order.received_at) if hasattr(order, 'received_at') else '',
                })

            return result
        except Exception as e:
            logger.error(f"Get orders error: {e}")
            return []

    # -------------------------------------------------------------------------
    # Order Execution
    # -------------------------------------------------------------------------

    async def execute_signal(self, signal: dict) -> Dict:
        """Execute a trading signal via TT cert API."""
        from tastytrade.order import (
            NewOrder, Leg, OrderAction, OrderType,
            OrderTimeInForce, InstrumentType
        )

        # Risk checks
        open_trades = self.journal.get_open_trades()
        summary = await self.get_account_summary()
        equity = summary.get('equity', 50000)
        risk_check = self.risk_manager.check_all(signal, open_trades, equity)
        if not risk_check['passed']:
            return {'ok': False, 'error': risk_check['reason'], 'risk_rejected': True}

        try:
            session, account = await get_cert_session()

            # Build OCC option symbol
            occ_symbol = build_occ_symbol(
                signal['ticker'], signal['expiration'],
                signal['strike'], signal['option_type']
            )

            # Determine action
            direction = signal.get('direction', 'long')
            if direction == 'long':
                action = OrderAction.BUY_TO_OPEN
            else:
                action = OrderAction.SELL_TO_OPEN

            quantity = signal.get('quantity', 1)

            leg = Leg(
                instrument_type=InstrumentType.EQUITY_OPTION,
                symbol=occ_symbol,
                quantity=Decimal(str(quantity)),
                action=action,
            )

            order = NewOrder(
                time_in_force=OrderTimeInForce.DAY,
                order_type=OrderType.MARKET,
                legs=[leg],
            )

            # Execute on cert (dry_run=False = real sandbox execution)
            response = await account.place_order(session, order, dry_run=False)

            order_id = response.order.id if hasattr(response, 'order') and hasattr(response.order, 'id') else None
            fill_price = 0
            if hasattr(response, 'order') and hasattr(response.order, 'price') and response.order.price:
                fill_price = float(response.order.price)

            # Update signal with execution details
            signal['entry_price'] = fill_price or signal.get('estimated_premium', 0)
            signal['occ_symbol'] = occ_symbol

            # Record in journal
            trade = self.journal.record_trade(
                signal,
                {'order_id': order_id},
                self.config,
            )

            logger.info(f"Executed: {occ_symbol} x{quantity} @ ${fill_price}")
            return {
                'ok': True,
                'trade': trade,
                'order_id': order_id,
                'occ_symbol': occ_symbol,
            }

        except Exception as e:
            logger.error(f"Execute signal error: {e}")
            import traceback
            traceback.print_exc()
            return {'ok': False, 'error': str(e)}

    async def close_position(self, trade_id: str, reason: str = 'manual') -> Dict:
        """Close a position by trade ID."""
        from tastytrade.order import (
            NewOrder, Leg, OrderAction, OrderType,
            OrderTimeInForce, InstrumentType
        )

        trades = self.journal.get_all_trades(status='open')
        trade = next((t for t in trades if t['id'] == trade_id), None)
        if not trade:
            return {'ok': False, 'error': f'Trade {trade_id} not found or not open'}

        try:
            session, account = await get_cert_session()

            occ_symbol = trade.get('occ_symbol') or build_occ_symbol(
                trade['ticker'], trade['expiration'],
                trade['strike'], trade['option_type']
            )

            direction = trade.get('direction', 'long')
            if direction == 'long':
                action = OrderAction.SELL_TO_CLOSE
            else:
                action = OrderAction.BUY_TO_CLOSE

            leg = Leg(
                instrument_type=InstrumentType.EQUITY_OPTION,
                symbol=occ_symbol,
                quantity=Decimal(str(trade['quantity'])),
                action=action,
            )

            order = NewOrder(
                time_in_force=OrderTimeInForce.DAY,
                order_type=OrderType.MARKET,
                legs=[leg],
            )

            response = await account.place_order(session, order, dry_run=False)
            fill_price = 0
            if hasattr(response, 'order') and hasattr(response.order, 'price') and response.order.price:
                fill_price = float(response.order.price)

            closed = self.journal.close_trade(trade_id, fill_price, reason)

            # Phase 1a-1c: Update all adaptive systems on trade close
            self._update_adaptive_systems(closed)

            return {'ok': True, 'trade': closed}

        except Exception as e:
            logger.error(f"Close position error: {e}")
            # Still close in journal with estimated price
            closed = self.journal.close_trade(trade_id, 0, f'{reason}_error')
            if closed:
                self._update_adaptive_systems(closed)
            return {'ok': False, 'error': str(e), 'trade': closed}

    # -------------------------------------------------------------------------
    # Exit Management
    # -------------------------------------------------------------------------

    async def check_exit_conditions(self) -> List[Dict]:
        """Check all open positions for exit conditions. Returns list of actions taken."""
        actions = []
        open_trades = self.journal.get_open_trades()
        if not open_trades:
            return actions

        positions = await self.get_positions()
        position_map = {p['symbol']: p for p in positions}

        for trade in open_trades:
            occ_symbol = trade.get('occ_symbol') or build_occ_symbol(
                trade['ticker'], trade['expiration'],
                trade['strike'], trade['option_type']
            )

            pos = position_map.get(occ_symbol)
            current_price = 0
            if pos:
                current_price = pos.get('mark', 0) or pos.get('close_price', 0)

            entry_price = trade.get('entry_price', 0)
            if entry_price <= 0:
                continue

            # Calculate P&L %
            if trade['direction'] == 'long':
                pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100 if entry_price > 0 else 0

            # Check DTE
            dte = 999
            if trade.get('expiration'):
                try:
                    exp_date = datetime.strptime(trade['expiration'], '%Y-%m-%d').date()
                    dte = (exp_date - date.today()).days
                except ValueError:
                    pass

            # Phase 1c: Use adaptive exit parameters if available
            if self.adaptive_exits:
                exit_params = self.adaptive_exits.get_exit_params(
                    strategy=trade.get('strategy'),
                    signal_type=trade.get('signal_type'),
                )
                stop_loss = exit_params.get('stop_loss_pct', trade.get('stop_loss_pct', -50))
                take_profit = exit_params.get('take_profit_pct', trade.get('take_profit_pct', 100))
                time_exit_dte = exit_params.get('time_exit_dte', self.config.get('time_exit_dte', 7))
            else:
                stop_loss = trade.get('stop_loss_pct', -50)
                take_profit = trade.get('take_profit_pct', 100)
                time_exit_dte = self.config.get('time_exit_dte', 7)

            exit_reason = None
            if pnl_pct <= stop_loss:
                exit_reason = 'stop_loss'
            elif pnl_pct >= take_profit:
                exit_reason = 'take_profit'
            elif dte <= time_exit_dte:
                exit_reason = 'time_exit'

            # Phase 3c: Edge-deterioration exit
            # If in profit and edge has collapsed, take profits early
            if not exit_reason and pnl_pct > 10 and self.edge_engine:
                try:
                    edge_data = await self.compute_edge_score(trade['ticker'])
                    current_edge = edge_data.get('edge_score', 50)
                    entry_edge = trade.get('entry_edge_score', 50)
                    # Exit if edge dropped by >25 points from entry
                    if entry_edge - current_edge > 25:
                        exit_reason = 'edge_deterioration'
                    # Exit long if regime flipped to danger
                    elif (trade['direction'] == 'long' and
                          edge_data.get('direction') == 'bearish' and
                          current_edge < 35):
                        exit_reason = 'regime_reversal'
                except Exception as e:
                    logger.debug(f"Edge exit check skipped for {trade['ticker']}: {e}")

            if exit_reason:
                result = await self.close_position(trade['id'], exit_reason)
                actions.append({
                    'trade_id': trade['id'],
                    'ticker': trade['ticker'],
                    'exit_reason': exit_reason,
                    'pnl_pct': round(pnl_pct, 2),
                    'result': result,
                })

        return actions

    # -------------------------------------------------------------------------
    # Adaptive Systems Feedback Loop
    # -------------------------------------------------------------------------

    def _update_adaptive_systems(self, closed_trade: dict):
        """Phase 1a-4b: Update all adaptive systems when a trade closes."""
        try:
            closed_trades = self.journal.get_closed_trades()

            # 1a: Update signal performance tracker
            if self.perf_tracker:
                self.perf_tracker.update_from_journal(closed_trades)
                logger.info("Updated signal performance tracker")

            # 1b: Update adaptive composite weights
            if self.adaptive_weights and closed_trade:
                factor_scores = closed_trade.get('entry_factor_scores', {})
                if factor_scores:
                    self.adaptive_weights.update_from_trade(closed_trade, factor_scores)
                    logger.info("Updated adaptive weights")

            # 1c: Update adaptive exit parameters
            if self.adaptive_exits:
                self.adaptive_exits.learn_from_trades(closed_trades)
                logger.info("Updated adaptive exit parameters")

            # 4a: Run full learning tier feedback cycle
            if self.tier_connector:
                tier_results = self.tier_connector.run_feedback_cycle(
                    self.perf_tracker, self.adaptive_weights,
                    self.adaptive_exits, closed_trades,
                )
                logger.info(f"Learning tier cycle: {tier_results.get('tier_health', {})}")

            # 4b: Record A/B test outcomes
            if self.ab_engine and closed_trade:
                ab_group = closed_trade.get('ab_group')
                ab_test_id = closed_trade.get('ab_test_id')
                if ab_group and ab_test_id:
                    self.ab_engine.record_outcome(ab_test_id, ab_group, closed_trade)
                    logger.info(f"A/B test {ab_test_id} updated ({ab_group})")

        except Exception as e:
            logger.error(f"Adaptive systems update error: {e}")

    def rebuild_adaptive_systems(self) -> Dict:
        """Force rebuild all adaptive systems from journal data."""
        closed = self.journal.get_closed_trades()
        results = {}

        if self.perf_tracker:
            results['signal_performance'] = self.perf_tracker.update_from_journal(closed)

        if self.adaptive_exits:
            results['adaptive_exits'] = self.adaptive_exits.learn_from_trades(closed)

        # Note: adaptive_weights updates incrementally per trade, not bulk
        if self.adaptive_weights:
            results['adaptive_weights'] = self.adaptive_weights.get_stats()

        return results

    def get_adaptive_stats(self) -> Dict:
        """Get all adaptive system stats for dashboard display."""
        stats = {}

        if self.perf_tracker:
            stats['signal_performance'] = self.perf_tracker.get_all_stats()

        if self.adaptive_weights:
            stats['adaptive_weights'] = self.adaptive_weights.get_stats()
            stats['current_weights'] = self.adaptive_weights.get_weights()

        if self.adaptive_exits:
            stats['adaptive_exits'] = {
                'gex_flip': self.adaptive_exits.get_exit_params(signal_type='gex_flip'),
                'regime_shift': self.adaptive_exits.get_exit_params(signal_type='regime_shift'),
                'macro_event': self.adaptive_exits.get_exit_params(signal_type='macro_event'),
                'iv_reversion': self.adaptive_exits.get_exit_params(signal_type='iv_reversion'),
            }

        if self.tier_connector:
            stats['learning_tiers'] = self.tier_connector.get_status()

        if self.ab_engine:
            stats['ab_tests'] = self.ab_engine.get_all_tests()

        return stats

    async def compute_edge_score(self, ticker: str) -> Dict:
        """Phase 3a: Compute unified edge score for a ticker."""
        if not self.edge_engine:
            return {'error': 'Edge engine not initialized'}

        try:
            from src.data.tastytrade_provider import (
                get_gex_regime_tastytrade, get_combined_regime_tastytrade,
                get_options_with_greeks_tastytrade,
            )

            # Fetch regime data in parallel
            import asyncio
            regime, combined, chain = await asyncio.gather(
                get_gex_regime_tastytrade(ticker),
                get_combined_regime_tastytrade(ticker),
                get_options_with_greeks_tastytrade(ticker),
                return_exceptions=True,
            )

            gex_regime = regime.get('regime', 'transitional') if isinstance(regime, dict) else 'transitional'
            combined_regime = combined.get('combined_regime', 'neutral_transitional') if isinstance(combined, dict) else 'neutral_transitional'

            # Flow toxicity from chain
            options = chain.get('options', []) if isinstance(chain, dict) else []
            toxicity_data = self.flow_analyzer.compute_toxicity(options) if self.flow_analyzer else {'toxicity': 0}

            # Simplified VRP (IV - RV estimate)
            vrp = 0
            if isinstance(chain, dict):
                iv_rank = chain.get('iv_rank', 50)
                vrp = max(-5, (iv_rank - 50) / 10)  # Rough proxy

            edge = self.edge_engine.compute_edge(
                composite_score=50,  # Will be replaced by actual composite when called from xray
                gex_regime=gex_regime,
                combined_regime=combined_regime,
                vrp=vrp,
                flow_toxicity=toxicity_data.get('toxicity', 0),
                dealer_flow_forecast={},
                signal_performance=self.perf_tracker.get_all_stats() if self.perf_tracker else {},
                adaptive_weights=self.adaptive_weights.get_weights() if self.adaptive_weights else {},
            )

            edge['ticker'] = ticker
            edge['flow_toxicity_detail'] = toxicity_data
            return edge

        except Exception as e:
            logger.error(f"Edge score computation error: {e}")
            return {'error': str(e)}

    def select_strategy(self, regime_state: Dict) -> List[Dict]:
        """Phase 3b: Auto-select strategy based on regime."""
        if not self.strategy_selector:
            return [{'name': 'Default', 'type': 'none', 'description': 'Strategy selector not initialized'}]
        return self.strategy_selector.select_strategy(regime_state)

    def compute_kelly_size(
        self, equity: float, premium: float,
        signal_type: str, combined_regime: str,
    ) -> Dict:
        """Phase 4c: Kelly position sizing."""
        if not self.kelly_sizer:
            return {'contracts': 1, 'rationale': 'Kelly sizer not initialized'}

        signal_stats = None
        if self.perf_tracker:
            signal_stats = self.perf_tracker.get_signal_stats(signal_type)

        return self.kelly_sizer.compute_position_size(
            equity=equity,
            premium=premium,
            signal_type=signal_type,
            combined_regime=combined_regime,
            signal_stats=signal_stats,
        )

    # -------------------------------------------------------------------------
    # Phase 4a: Learning Tier Status
    # -------------------------------------------------------------------------

    def get_learning_tier_status(self) -> Dict:
        """Phase 4a: Get learning tier health and meta adjustments."""
        if not self.tier_connector:
            return {'error': 'Learning tier connector not initialized'}
        return self.tier_connector.get_status()

    def get_meta_adjustments(self) -> Dict:
        """Phase 4a: Get meta-level adjustments (confidence scale, learning rate)."""
        if not self.tier_connector:
            return {'confidence_scale': 1.0, 'learning_rate': 0.1, 'exploration_rate': 0.2}
        return self.tier_connector.get_meta_adjustments()

    # -------------------------------------------------------------------------
    # Phase 4b: A/B Testing
    # -------------------------------------------------------------------------

    def create_ab_test(self, test_id: str, description: str,
                       control: Dict, variant: Dict,
                       min_trades: int = 20) -> Dict:
        """Phase 4b: Create a new A/B test."""
        if not self.ab_engine:
            return {'error': 'A/B test engine not initialized'}
        return self.ab_engine.create_test(test_id, description, control, variant, min_trades)

    def get_ab_tests(self) -> Dict:
        """Phase 4b: Get all A/B test results."""
        if not self.ab_engine:
            return {'tests': {}, 'completed': []}
        return self.ab_engine.get_all_tests()

    # -------------------------------------------------------------------------
    # System Status
    # -------------------------------------------------------------------------

    async def get_status(self) -> Dict:
        """System health check."""
        cert_ok = False
        account_num = None
        try:
            session, account = await get_cert_session()
            cert_ok = session is not None
            account_num = account.account_number if account else None
        except Exception as e:
            logger.error(f"Status check error: {e}")

        return {
            'cert_session_alive': cert_ok,
            'account_number': account_num,
            'auto_trade_enabled': self.config.get('auto_trade_enabled', False),
            'watched_tickers': self.config.get('watched_tickers', []),
            'open_trades': len(self.journal.get_open_trades()),
            'total_trades': len(self.journal.get_all_trades()),
        }

    def reset(self):
        """Full reset: clear journal, reset equity curve."""
        starting = self.config.get('starting_capital', 50000)
        self.journal.reset(starting)
        invalidate_cert_session()
        return {'ok': True, 'starting_capital': starting}


# =============================================================================
# Helpers
# =============================================================================

def build_occ_symbol(ticker: str, expiration: str, strike: float, option_type: str) -> str:
    """
    Build OCC option symbol.
    Format: 'SPY   240417C00437000'
    - 6-char left-padded ticker
    - 6-char date YYMMDD
    - C or P
    - 8-char zero-padded strike * 1000
    """
    ticker_padded = ticker.upper().ljust(6)
    try:
        exp_date = datetime.strptime(expiration, '%Y-%m-%d')
    except ValueError:
        exp_date = datetime.strptime(expiration, '%y%m%d')
    date_str = exp_date.strftime('%y%m%d')
    cp = 'C' if option_type.lower().startswith('c') else 'P'
    strike_int = int(strike * 1000)
    strike_str = str(strike_int).zfill(8)
    return f"{ticker_padded}{date_str}{cp}{strike_str}"


def parse_occ_symbol(occ: str) -> Dict:
    """Parse OCC symbol back to components."""
    ticker = occ[:6].strip()
    date_str = occ[6:12]
    option_type = 'call' if occ[12] == 'C' else 'put'
    strike = int(occ[13:21]) / 1000
    exp_date = datetime.strptime(date_str, '%y%m%d').strftime('%Y-%m-%d')
    return {
        'ticker': ticker,
        'expiration': exp_date,
        'option_type': option_type,
        'strike': strike,
    }


def calc_dte(expiration: str) -> int:
    """Calculate days to expiration."""
    try:
        exp_date = datetime.strptime(expiration, '%Y-%m-%d').date()
        return (exp_date - date.today()).days
    except ValueError:
        return 999
