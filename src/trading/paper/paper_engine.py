"""
Paper Trading Engine — Cert session, order execution, position sync.

Uses Tastytrade certification (sandbox) API with is_test=True.
All tastytrade SDK v12+ methods are async.
"""

import os
import time
import logging
from decimal import Decimal
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from .risk_manager import RiskManager, load_config, save_config
from .journal import TradeJournal
from .strategy_builder import StrategyBuilder

logger = logging.getLogger(__name__)

# Cert session cache (separate from production data session)
_cert_session = None
_cert_session_expiry = None
_cert_account = None

# Live marks cache: prod REST API provides real marks when cert returns 0
_live_marks_cache = {}   # {occ_symbol: mark_price}
_live_marks_ts = 0       # timestamp of last fetch
_LIVE_MARKS_TTL = 60     # seconds

# Live betas cache: prod REST API provides real betas for concentration checks
_live_betas_cache = {}   # {ticker: beta}
_live_betas_ts = 0       # timestamp of last fetch
_LIVE_BETAS_TTL = 3600   # 1 hour (betas don't change intraday)


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
        self.strategy_builder = StrategyBuilder()
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

        # Auto-backfill factor scores for trades that predate the scoring code
        try:
            backfilled = self.journal.backfill_factor_scores()
            if backfilled:
                logger.info(f"Auto-backfilled {backfilled} trades with factor scores")
        except Exception as e:
            logger.warning(f"Factor score backfill failed: {e}")

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
        """Get paper account summary computed from journal trades (not sandbox balance)."""
        starting = self.config.get('starting_capital', 50000)

        # Compute P&L from journal (the source of truth for paper trading)
        closed_trades = self.journal.get_closed_trades()
        open_trades = self.journal.get_open_trades()

        # Realized P&L from closed trades
        realized_pnl = sum(t.get('pnl_dollars', 0) or 0 for t in closed_trades)

        # Unrealized P&L from open trades (requires live marks)
        unrealized_pnl = 0

        # Build OCC symbols from journal trades' leg data
        all_occ_needed = []
        for trade in open_trades:
            if trade.get('is_multi_leg') and trade.get('legs'):
                for leg in trade['legs']:
                    occ = build_occ_symbol(trade['ticker'], leg['expiration'],
                                           leg['strike'], leg['option_type'])
                    all_occ_needed.append(occ)
            else:
                occ = trade.get('occ_symbol') or build_occ_symbol(
                    trade['ticker'], trade['expiration'],
                    trade['strike'], trade['option_type'])
                all_occ_needed.append(occ)

        # Fetch live marks from prod session (works even when cert sandbox is reset)
        live_marks = {}
        if all_occ_needed:
            live_marks = await self._fetch_live_marks(all_occ_needed)

        # Also try cert positions as secondary source
        positions = await self.get_positions()
        pos_map = {p['symbol']: p for p in positions}

        def _get_mark(occ_symbol: str) -> float:
            """Get mark from live marks (prod) or cert positions, whichever is available."""
            if occ_symbol in live_marks and live_marks[occ_symbol] > 0:
                return live_marks[occ_symbol]
            pos = pos_map.get(occ_symbol)
            if pos:
                return pos.get('mark', 0) or pos.get('close_price', 0)
            return 0

        for trade in open_trades:
            entry = trade.get('entry_price', 0)
            qty = trade.get('quantity', 1)
            if trade.get('is_multi_leg') and trade.get('legs'):
                # Multi-leg: compute net mark from all legs
                net_mark = 0
                all_found = True
                for leg in trade['legs']:
                    occ = build_occ_symbol(trade['ticker'], leg['expiration'],
                                           leg['strike'], leg['option_type'])
                    lm = _get_mark(occ)
                    if lm > 0:
                        if leg['action'] == 'SELL':
                            net_mark += lm
                        else:
                            net_mark -= lm
                    else:
                        all_found = False
                if all_found and entry > 0 and net_mark > 0:
                    # Credit spread: pnl = (credit - cost_to_close) * qty * 100
                    unrealized_pnl += (entry - net_mark) * qty * 100
            else:
                occ = trade.get('occ_symbol') or build_occ_symbol(
                    trade['ticker'], trade['expiration'],
                    trade['strike'], trade['option_type']
                )
                mark = _get_mark(occ)
                if mark > 0:
                    if trade.get('direction') == 'long':
                        unrealized_pnl += (mark - entry) * qty * 100
                    else:
                        unrealized_pnl += (entry - mark) * qty * 100

        # Open trade premiums committed (credits received or debits paid)
        open_premium_committed = sum(
            (t.get('entry_price', 0) * (t.get('quantity', 1)) * 100)
            for t in open_trades
        )

        total_pnl = realized_pnl + unrealized_pnl
        equity = starting + total_pnl
        cash = starting + realized_pnl  # Cash = starting + realized (premiums settled)
        positions_value = unrealized_pnl
        total_pnl_pct = (total_pnl / starting) * 100 if starting > 0 else 0

        # Record equity snapshot (journal-based, not sandbox)
        self.journal.record_equity_snapshot(equity, cash, positions_value)

        # Daily P&L from equity curve
        daily_pnl = 0
        curve = self.journal.get_equity_curve()
        if len(curve) >= 2:
            daily_pnl = equity - curve[-2]['equity']
        elif len(curve) == 1:
            daily_pnl = equity - starting

        # Get account number from sandbox (just for display)
        account_number = 'offline'
        try:
            _, account = await get_cert_session()
            account_number = account.account_number
        except Exception:
            pass

        return {
            'equity': round(equity, 2),
            'cash': round(cash, 2),
            'buying_power': round(cash, 2),  # Simplified: buying power ≈ cash
            'positions_value': round(positions_value, 2),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_pct': round(total_pnl_pct, 2),
            'daily_pnl': round(daily_pnl, 2),
            'starting_capital': starting,
            'account_number': account_number,
            'realized_pnl': round(realized_pnl, 2),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'open_positions': len(open_trades),
            'closed_trades': len(closed_trades),
        }

    async def _fetch_live_marks(self, occ_symbols: List[str]) -> Dict[str, float]:
        """Fetch live option marks from prod session via REST batch API.

        Cert (sandbox) returns mark=0 for options. This fetches real marks
        from the production session so exit logic and P&L display work.
        Results are cached for _LIVE_MARKS_TTL seconds.
        """
        global _live_marks_cache, _live_marks_ts

        # Return cache if fresh and has all requested symbols
        if (time.time() - _live_marks_ts < _LIVE_MARKS_TTL
                and all(s in _live_marks_cache for s in occ_symbols)):
            return {s: _live_marks_cache[s] for s in occ_symbols}

        try:
            from src.data.tastytrade_provider import get_tastytrade_session
            from tastytrade.market_data import get_market_data_by_type

            session = get_tastytrade_session()
            if not session:
                logger.warning("Live marks: no prod session available")
                return {}

            # Batch limit is 100 symbols
            data = await get_market_data_by_type(session, options=occ_symbols[:100])

            marks = {}
            for item in data:
                symbol = item.symbol
                mark = float(item.mark) if item.mark else 0
                if mark <= 0:
                    # Fallback: mid, then (bid+ask)/2, then last
                    if item.mid:
                        mark = float(item.mid)
                    elif item.bid and item.ask:
                        mark = (float(item.bid) + float(item.ask)) / 2
                    elif item.last:
                        mark = float(item.last)
                if mark > 0:
                    marks[symbol] = mark
                    _live_marks_cache[symbol] = mark

            _live_marks_ts = time.time()
            logger.info(f"Live marks fetched: {len(marks)}/{len(occ_symbols)} symbols enriched")
            return marks

        except Exception as e:
            logger.warning(f"Live marks fetch failed: {e}")
            return {}

    async def _fetch_live_betas(self) -> Dict[str, float]:
        """Fetch live betas from prod session for all watched tickers.

        Betas are cached for 1 hour since they don't change intraday.
        Used by the risk manager for beta-weighted concentration checks.
        """
        global _live_betas_cache, _live_betas_ts

        if time.time() - _live_betas_ts < _LIVE_BETAS_TTL and _live_betas_cache:
            return dict(_live_betas_cache)

        try:
            from src.data.tastytrade_provider import get_tastytrade_session
            from tastytrade.market_data import get_market_data_by_type

            session = get_tastytrade_session()
            if not session:
                logger.warning("Live betas: no prod session available")
                return dict(_live_betas_cache)

            tickers = self.config.get('watched_tickers', [])
            if not tickers:
                return dict(_live_betas_cache)

            data = await get_market_data_by_type(session, equities=tickers[:100])

            betas = {}
            for item in data:
                if item.beta is not None:
                    betas[item.symbol] = float(item.beta)

            if betas:
                _live_betas_cache.update(betas)
                _live_betas_ts = time.time()
                logger.info(f"Live betas fetched: {betas}")

            return dict(_live_betas_cache)

        except Exception as e:
            logger.warning(f"Live betas fetch failed: {e}")
            return dict(_live_betas_cache)

    def _compute_factor_scores(self, signal: dict, regime_overrides: dict = None) -> dict:
        """Compute entry factor scores from signal data + optional regime overrides.

        Called by all execution paths (smart single-leg, naive single-leg, multi-leg)
        so Thompson Sampling and adaptive exits always have factor data to learn from.
        """
        rd = regime_overrides or {}
        sig_regime = signal.get('regime_data', {})

        # Extract regime fields: prefer overrides (multi-leg has richer data), fallback to signal
        iv_data = signal.get('iv_data', {})
        iv_rank = rd.get('iv_rank', iv_data.get('iv_rank', 50))
        vrp = rd.get('vrp', (iv_rank - 30) / 10)
        gex_regime = rd.get('gex_regime',
                            sig_regime.get('regime',
                                           sig_regime.get('gex_regime', 'transitional')))
        flow_toxicity = rd.get('flow_toxicity', 0.3)
        skew_ratio = rd.get('skew_ratio', 1.0)
        real_structure = rd.get('term_structure', 'contango')

        return {
            'dealer_flow': max(0, min(100, 50 + vrp * 10)),
            'squeeze': max(0, min(100, 80 if gex_regime == 'pinned' else 40 if gex_regime == 'volatile' else 55)),
            'smart_money': max(0, min(100, round((1 - flow_toxicity) * 80))),
            'price_vs_maxpain': 50,
            'skew': max(0, min(100, round(skew_ratio * 50))),
            'term': max(0, min(100, 70 if real_structure == 'contango' else 30)),
            'price_vs_walls': 50,
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

            # Enrich zero-mark option positions with live marks from prod session
            zero_mark_symbols = [
                p['symbol'] for p in result
                if p.get('mark', 0) == 0 and 'EQUITY_OPTION' in p.get('instrument_type', '').upper()
            ]
            if zero_mark_symbols:
                live_marks = await self._fetch_live_marks(zero_mark_symbols)
                for pos in result:
                    if pos['symbol'] in live_marks:
                        pos['mark'] = live_marks[pos['symbol']]
                        pos['mark_source'] = 'prod_rest'

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
        """Execute a trading signal via TT cert API.

        Dispatches to multi-leg execution when multi_leg_enabled and signal
        has a strategy_recommendation with recognized multi-leg strategy.
        Checks transition probability for halt/halve sizing.
        """
        # Reject signals with no valid price data
        if signal.get('underlying_price', 0) <= 0 or signal.get('strike', 0) <= 0:
            logger.warning(f"Rejecting signal for {signal.get('ticker')}: "
                           f"invalid price data (price={signal.get('underlying_price')}, strike={signal.get('strike')})")
            return {'ok': False, 'error': 'Signal has no valid price data (strike=0 or underlying_price=0)'}

        # Regime transition check: halt or halve position sizes
        transition = signal.get('transition', {})
        trans_prob = transition.get('transition_probability', 0)
        trans_action = transition.get('action', 'normal')

        if trans_action == 'halt_new_entries':
            logger.warning(f"Halting trade for {signal.get('ticker')}: "
                           f"transition probability {trans_prob:.1%}")
            return {
                'ok': False,
                'error': f'Regime transition probability {trans_prob:.1%} — halting new entries',
                'transition': transition,
            }

        # Check if this should be a multi-leg trade
        multi_leg_enabled = self.config.get('multi_leg_enabled', False)
        strategy_rec = signal.get('strategy_recommendation')

        if multi_leg_enabled and strategy_rec:
            strategy_name = strategy_rec.get('name', '')
            # Route to multi-leg if strategy is a recognized multi-leg type
            # Cash-secured put routes here too (built as wide credit spread for defined risk)
            multi_leg_types = ['credit spread', 'iron condor', 'iron butterfly',
                               'straddle', 'debit spread', 'ratio spread',
                               'range bound', 'event vol', 'premium harvest',
                               'skew harvest', 'vrp harvest', 'melt-up',
                               'bear put', 'backwardation credit', 'cash-secured',
                               'long gamma']
            if any(t in strategy_name.lower() for t in multi_leg_types):
                return await self._execute_multi_leg(signal, strategy_rec)

        # --- Smart single-leg path ---
        return await self._execute_smart_single_leg(signal)

    async def _execute_smart_single_leg(self, signal: dict) -> Dict:
        """Smart single-leg execution with delta targeting, Greek awareness, and quality gating."""
        ticker = signal['ticker']
        direction = signal.get('direction', 'long')

        # 1. Block naked shorts — require multi-leg mode for selling premium
        if direction == 'short':
            logger.warning(f"Blocked naked short for {ticker}: multi-leg mode required")
            return {
                'ok': False,
                'error': 'Naked short positions require multi-leg mode for defined-risk trades',
                'blocked_naked_short': True,
            }

        # Risk checks
        open_trades = self.journal.get_open_trades()
        summary = await self.get_account_summary()
        starting = self.config.get('starting_capital', 50000)
        equity = summary.get('equity', starting) or starting  # Fallback if sandbox reset
        betas = await self._fetch_live_betas()
        risk_check = self.risk_manager.check_all(signal, open_trades, equity, betas)
        if not risk_check['passed']:
            return {'ok': False, 'error': risk_check['reason'], 'risk_rejected': True}

        # 2. Fetch chain for delta-based strike selection
        try:
            from src.data.tastytrade_provider import get_options_with_greeks_tastytrade
            dte_range = signal.get('dte_range', [30, 45])
            target_dte = (dte_range[0] + dte_range[1]) // 2
            chain = await get_options_with_greeks_tastytrade(ticker, target_dte=target_dte)
        except Exception as e:
            logger.warning(f"Chain fetch failed for {ticker}, falling back to naive: {e}")
            return await self._execute_naive_single_leg(signal)

        if not isinstance(chain, dict) or not chain.get('options'):
            logger.warning(f"No chain data for {ticker}, falling back to naive")
            return await self._execute_naive_single_leg(signal)

        # 3. Delta-based strike selection
        option_type = signal.get('option_type', 'call')
        delta_target = signal.get('delta_target', 0.50)
        opts = self.strategy_builder._extract_options(chain['options'], option_type)

        if not opts:
            logger.warning(f"No {option_type} options extracted for {ticker}, falling back to naive")
            return await self._execute_naive_single_leg(signal)

        selected = self.strategy_builder._find_by_delta(opts, delta_target, prefer_liquid=True)
        if not selected:
            logger.warning(f"No strike found near {delta_target:.0%}Δ for {ticker}, falling back to naive")
            return await self._execute_naive_single_leg(signal)

        # 4. Liquidity check (warn but don't reject)
        if selected['oi'] < 50:
            logger.warning(
                f"Low OI ({selected['oi']}) for {ticker} {option_type} ${selected['strike']} "
                f"— proceeding with best available"
            )

        # 5. Quality scoring
        quality = self.strategy_builder._score_for_buying(selected)
        if quality < 15:
            logger.warning(f"Quality gate rejected {ticker} {option_type} ${selected['strike']} (score={quality:.1f})")
            return {
                'ok': False,
                'error': f'Quality too low ({quality:.1f}/100) for {option_type} ${selected["strike"]}',
                'quality_rejected': True,
            }

        # 6. Record Greeks
        greeks = self.strategy_builder._leg_greeks(selected, 'BUY', option_type)

        # 7. Override naive signal fields with chain-derived data
        expiration = chain.get('expiration', signal.get('expiration', ''))
        signal['strike'] = selected['strike']
        signal['expiration'] = expiration
        signal['entry_price'] = selected['price']
        signal['greeks'] = greeks
        signal['quality_score'] = round(quality, 1)
        signal['delta'] = selected['delta']
        signal['iv'] = selected['iv']

        # 8. Execute order — always BUY_TO_OPEN
        try:
            from tastytrade.order import (
                NewOrder, Leg, OrderAction, OrderType,
                OrderTimeInForce, InstrumentType
            )

            session, account = await get_cert_session()

            occ_symbol = build_occ_symbol(
                ticker, expiration, selected['strike'], option_type
            )

            quantity = signal.get('quantity', 1)

            leg = Leg(
                instrument_type=InstrumentType.EQUITY_OPTION,
                symbol=occ_symbol,
                quantity=Decimal(str(quantity)),
                action=OrderAction.BUY_TO_OPEN,
            )

            order = NewOrder(
                time_in_force=OrderTimeInForce.DAY,
                order_type=OrderType.MARKET,
                legs=[leg],
            )

            response = await account.place_order(session, order, dry_run=False)

            order_id = response.order.id if hasattr(response, 'order') and hasattr(response.order, 'id') else None
            fill_price = 0
            if hasattr(response, 'order') and hasattr(response.order, 'price') and response.order.price:
                fill_price = float(response.order.price)

            signal['entry_price'] = fill_price or selected['price']
            signal['occ_symbol'] = occ_symbol
            signal['entry_factor_scores'] = self._compute_factor_scores(signal)

            trade = self.journal.record_trade(
                signal,
                {'order_id': order_id},
                self.config,
            )

            logger.info(
                f"Smart single-leg: {occ_symbol} x{quantity} @ ${fill_price} "
                f"(Δ:{selected['delta']:.2f}, IV:{selected['iv']:.1%}, Q:{quality:.0f})"
            )
            return {
                'ok': True,
                'trade': trade,
                'order_id': order_id,
                'occ_symbol': occ_symbol,
            }

        except Exception as e:
            logger.error(f"Smart single-leg execute error: {e}")
            import traceback
            traceback.print_exc()
            return {'ok': False, 'error': str(e)}

    async def _execute_naive_single_leg(self, signal: dict) -> Dict:
        """Fallback naive single-leg execution (no chain data, ATM strike)."""
        from tastytrade.order import (
            NewOrder, Leg, OrderAction, OrderType,
            OrderTimeInForce, InstrumentType
        )

        # Risk checks
        open_trades = self.journal.get_open_trades()
        summary = await self.get_account_summary()
        starting = self.config.get('starting_capital', 50000)
        equity = summary.get('equity', starting) or starting  # Fallback if sandbox reset
        betas = await self._fetch_live_betas()
        risk_check = self.risk_manager.check_all(signal, open_trades, equity, betas)
        if not risk_check['passed']:
            return {'ok': False, 'error': risk_check['reason'], 'risk_rejected': True}

        try:
            session, account = await get_cert_session()

            occ_symbol = build_occ_symbol(
                signal['ticker'], signal['expiration'],
                signal['strike'], signal['option_type']
            )

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

            response = await account.place_order(session, order, dry_run=False)

            order_id = response.order.id if hasattr(response, 'order') and hasattr(response.order, 'id') else None
            fill_price = 0
            if hasattr(response, 'order') and hasattr(response.order, 'price') and response.order.price:
                fill_price = float(response.order.price)

            signal['entry_price'] = fill_price or signal.get('estimated_premium', 0)
            signal['occ_symbol'] = occ_symbol
            signal['entry_factor_scores'] = self._compute_factor_scores(signal)

            trade = self.journal.record_trade(
                signal,
                {'order_id': order_id},
                self.config,
            )

            logger.info(f"Naive fallback: {occ_symbol} x{quantity} @ ${fill_price}")
            return {
                'ok': True,
                'trade': trade,
                'order_id': order_id,
                'occ_symbol': occ_symbol,
            }

        except Exception as e:
            logger.error(f"Naive single-leg execute error: {e}")
            import traceback
            traceback.print_exc()
            return {'ok': False, 'error': str(e)}

    async def _execute_multi_leg(self, signal: dict, strategy_rec: dict) -> Dict:
        """Execute a multi-leg strategy order via TT cert API.

        Fetches real regime data in parallel, re-validates strategy selection,
        passes delta_target/iv_rank/dte to StrategyBuilder, and applies quality gate.
        """
        from tastytrade.order import (
            NewOrder, Leg, OrderAction, OrderType,
            OrderTimeInForce, InstrumentType
        )
        import asyncio

        ticker = signal['ticker']
        strategy_name = strategy_rec.get('name', 'Unknown')

        # Risk checks (multi-leg variant)
        open_trades = self.journal.get_open_trades()
        summary = await self.get_account_summary()
        starting = self.config.get('starting_capital', 50000)
        equity = summary.get('equity', starting) or starting  # Fallback if sandbox reset

        try:
            # Fetch chain + regime + term structure + skew in parallel
            from src.data.tastytrade_provider import (
                get_options_with_greeks_tastytrade,
                get_gex_regime_tastytrade,
                get_combined_regime_tastytrade,
                get_term_structure_tastytrade,
                get_iv_by_delta_tastytrade,
            )

            dte_range = strategy_rec.get('dte_range', [30, 45])
            target_dte = (dte_range[0] + dte_range[1]) // 2  # midpoint DTE

            chain, regime, combined, term_struct, skew_data = await asyncio.gather(
                get_options_with_greeks_tastytrade(ticker, target_dte=target_dte),
                get_gex_regime_tastytrade(ticker),
                get_combined_regime_tastytrade(ticker),
                get_term_structure_tastytrade(ticker),
                get_iv_by_delta_tastytrade(ticker),
                return_exceptions=True,
            )

            if not isinstance(chain, dict) or not chain.get('options'):
                return {'ok': False, 'error': f'No options chain available for {ticker}'}

            # Extract real regime data
            gex_regime = regime.get('regime', 'transitional') if isinstance(regime, dict) else 'transitional'
            combined_regime = combined.get('combined_regime', 'neutral_transitional') if isinstance(combined, dict) else 'neutral_transitional'
            underlying_price = signal.get('underlying_price', 0)
            if not underlying_price and isinstance(regime, dict):
                underlying_price = regime.get('current_price', 0)

            # Compute real IV rank and VRP from chain
            iv_rank = chain.get('iv_rank', 50)
            vrp = (iv_rank - 30) / 10  # Calibrated: IV Rank 70 → VRP 4.0

            # Flow toxicity from chain
            options = chain.get('options', [])
            toxicity_data = self.flow_analyzer.compute_toxicity(options) if self.flow_analyzer else {'toxicity': 0.3}
            flow_toxicity = toxicity_data.get('toxicity', 0.3)

            # Extract real term structure and skew
            real_structure = 'contango'
            if isinstance(term_struct, dict) and 'structure' in term_struct:
                real_structure = term_struct['structure']
            skew_ratio = 1.0
            if isinstance(skew_data, dict) and skew_data.get('skew_ratio'):
                skew_ratio = skew_data['skew_ratio']

            # Compute risk reversal from skew data
            risk_reversal = 0
            if isinstance(skew_data, dict):
                p25 = skew_data.get('put_25d_iv')
                c25 = skew_data.get('call_25d_iv')
                if p25 and c25:
                    risk_reversal = round(float(p25) - float(c25), 4)

            # Compute vanna_flow from risk reversal + regime
            vanna_flow = 0.0
            if risk_reversal:
                vanna_flow = -risk_reversal * 10  # Scale: 0.05 RR → 0.5 vanna_flow
                vanna_flow = max(-1.0, min(1.0, vanna_flow))
            if combined_regime == 'opportunity':
                vanna_flow = max(vanna_flow, 0.5)

            # Re-validate strategy with real data
            real_regime_state = {
                'vrp': vrp,
                'gex_regime': gex_regime,
                'combined_regime': combined_regime,
                'flow_toxicity': flow_toxicity,
                'term_structure': real_structure,
                'skew_steep': skew_ratio > 1.15,
                'skew_ratio': skew_ratio,
                'iv_rank': iv_rank,
                'vanna_flow': round(vanna_flow, 2),
                'macro_event_days': signal.get('event_data', {}).get('days_until', 99),
                'risk_reversal': risk_reversal,
            }

            # Re-run strategy selection with real data to verify recommendation still holds
            if self.strategy_selector:
                real_strategies = self.strategy_selector.select_strategy(real_regime_state)
                valid = [s for s in real_strategies if s.get('name') != 'Wait / Reduce Size']
                if not valid:
                    return {'ok': False, 'error': 'Strategy no longer valid with real regime data'}

                # Strategy diversification: prefer strategies not already in open positions
                open_trades = self.journal.get_open_trades()
                used_strategies = {t.get('strategy_name', '').lower() for t in open_trades}

                # Pick first strategy not already used; fall back to first valid if all used
                selected = valid[0]
                for s in valid:
                    if s['name'].lower() not in used_strategies:
                        selected = s
                        break

                strategy_rec = selected
                strategy_name = strategy_rec.get('name', strategy_name)
                if len(valid) > 1:
                    logger.info(f"Strategy diversification: {len(valid)} candidates, "
                                f"selected '{strategy_name}' (used: {used_strategies & {s['name'].lower() for s in valid}} )")

            direction = strategy_rec.get('direction', signal.get('direction', 'long'))
            delta_target = strategy_rec.get('delta_target', 0.16)
            actual_dte = chain.get('dte', target_dte)

            # Build the multi-leg structure with full context
            built = self.strategy_builder.build_legs(
                strategy_name=strategy_name,
                ticker=ticker,
                direction=direction,
                chain_data=chain,
                underlying_price=underlying_price,
                delta_target=delta_target,
                iv_rank=iv_rank,
                dte=actual_dte,
            )

            # Quality gate — reject low-quality builds
            quality = built.get('quality_score', 0)
            if quality < 20:
                logger.warning(f"Quality gate rejected {strategy_name} for {ticker} (score={quality})")
                return {'ok': False, 'error': f'Quality too low ({quality:.0f}/100) for {strategy_name}'}

            leg_defs = built.get('legs', [])
            if len(leg_defs) < 2:
                logger.warning(f"Strategy builder returned <2 legs for {strategy_name}, falling back to single-leg")
                return await self.execute_signal({**signal, 'strategy_recommendation': None})

            # Risk check with multi-leg awareness
            betas = await self._fetch_live_betas()
            risk_signal = {**signal, 'max_loss': built.get('max_loss', 0)}
            risk_check = self.risk_manager.check_all_multi_leg(risk_signal, open_trades, equity, betas)
            if not risk_check['passed']:
                return {'ok': False, 'error': risk_check['reason'], 'risk_rejected': True}

            # Position sizing based on max_loss
            quantity = self.risk_manager.compute_position_size(
                signal, equity, max_loss=built.get('max_loss')
            )

            # Halve position size if transition probability is elevated
            if signal.get('transition', {}).get('action') == 'halve_position_sizes':
                quantity = max(1, quantity // 2)
                logger.info(f"Halved position to {quantity} — elevated transition probability")

            session, account = await get_cert_session()

            # Build Tastytrade Leg objects
            tt_legs = []
            occ_symbols = []
            for leg_def in leg_defs:
                occ = build_occ_symbol(
                    ticker, leg_def['expiration'],
                    leg_def['strike'], leg_def['option_type']
                )
                occ_symbols.append(occ)

                if leg_def['action'] == 'BUY':
                    action = OrderAction.BUY_TO_OPEN
                else:
                    action = OrderAction.SELL_TO_OPEN

                leg_qty = leg_def.get('quantity', 1) * quantity

                tt_legs.append(Leg(
                    instrument_type=InstrumentType.EQUITY_OPTION,
                    symbol=occ,
                    quantity=Decimal(str(leg_qty)),
                    action=action,
                ))

            # Multi-leg orders must be Limit (Tastytrade rejects Market for spreads)
            net_premium = built.get('net_premium', 0)
            limit_price = abs(net_premium) if net_premium else 0.01
            order = NewOrder(
                time_in_force=OrderTimeInForce.DAY,
                order_type=OrderType.LIMIT,
                price=Decimal(str(round(limit_price, 2))),
                legs=tt_legs,
            )

            response = await account.place_order(session, order, dry_run=False)
            order_id = response.order.id if hasattr(response, 'order') and hasattr(response.order, 'id') else None
            fill_price = 0
            if hasattr(response, 'order') and hasattr(response.order, 'price') and response.order.price:
                fill_price = float(response.order.price)

            # Enrich signal for journal recording
            signal['is_multi_leg'] = True
            signal['legs'] = leg_defs
            signal['strategy_name'] = built['strategy_name']
            signal['net_premium'] = built['net_premium']
            signal['max_loss'] = built['max_loss']
            signal['max_profit'] = built['max_profit']
            signal['entry_price'] = fill_price or abs(built['net_premium'])
            signal['quantity'] = quantity
            signal['occ_symbols'] = occ_symbols
            signal['expiration'] = leg_defs[0]['expiration']
            built_greeks = built.get('greeks', {})
            signal['greeks'] = built_greeks
            signal['iv'] = built_greeks.get('iv', 0) or built.get('avg_iv', 0)
            signal['delta'] = built_greeks.get('delta', 0)
            signal['quality_score'] = built.get('quality_score', 0)
            signal['regime_at_entry'] = {
                'gex_regime': gex_regime,
                'combined_regime': combined_regime,
                'vrp': round(vrp, 2),
                'iv_rank': iv_rank,
                'flow_toxicity': round(flow_toxicity, 3),
            }

            # Capture factor scores for bandit learning (using rich regime data)
            signal['entry_factor_scores'] = self._compute_factor_scores(signal, {
                'vrp': vrp,
                'gex_regime': gex_regime,
                'iv_rank': iv_rank,
                'flow_toxicity': flow_toxicity,
                'skew_ratio': skew_ratio,
                'term_structure': real_structure,
            })

            trade = self.journal.record_trade(
                signal,
                {'order_id': order_id},
                self.config,
            )

            logger.info(f"Multi-leg executed: {built['strategy_name']} on {ticker} x{quantity} ({len(leg_defs)} legs)")
            return {
                'ok': True,
                'trade': trade,
                'order_id': order_id,
                'occ_symbols': occ_symbols,
                'multi_leg': True,
            }

        except Exception as e:
            logger.error(f"Multi-leg execute error: {e}")
            import traceback
            traceback.print_exc()
            return {'ok': False, 'error': str(e)}

    async def close_position(self, trade_id: str, reason: str = 'manual') -> Dict:
        """Close a position by trade ID. Routes to multi-leg close if applicable."""
        trades = self.journal.get_all_trades(status='open')
        trade = next((t for t in trades if t['id'] == trade_id), None)
        if not trade:
            return {'ok': False, 'error': f'Trade {trade_id} not found or not open'}

        # Route to multi-leg close if trade has legs
        if trade.get('is_multi_leg') and trade.get('legs'):
            return await self._close_multi_leg(trade, reason)

        from tastytrade.order import (
            NewOrder, Leg, OrderAction, OrderType,
            OrderTimeInForce, InstrumentType
        )

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

            # Reassess exit_reason based on actual fill P&L
            if fill_price > 0 and reason in ('stop_loss', 'take_profit'):
                entry = trade.get('entry_price', 0)
                if entry > 0:
                    if trade['direction'] == 'long':
                        actual_pnl = fill_price - entry
                    else:
                        actual_pnl = entry - fill_price
                    if actual_pnl > 0 and reason == 'stop_loss':
                        logger.info(f"Exit reassessed: stop_loss → take_profit (fill ${fill_price:.2f})")
                        reason = 'take_profit'
                    elif actual_pnl < 0 and reason == 'take_profit':
                        logger.info(f"Exit reassessed: take_profit → stop_loss (fill ${fill_price:.2f})")
                        reason = 'stop_loss'

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

    async def _close_multi_leg(self, trade: dict, reason: str) -> Dict:
        """Close a multi-leg position by building reverse legs atomically."""
        from tastytrade.order import (
            NewOrder, Leg, OrderAction, OrderType,
            OrderTimeInForce, InstrumentType
        )

        trade_id = trade['id']
        try:
            session, account = await get_cert_session()

            # Check actual sandbox positions to avoid quantity mismatch
            positions = await account.get_positions(session)
            pos_qty_map = {}
            for pos in positions:
                if int(pos.quantity) != 0:
                    pos_qty_map[pos.symbol] = abs(int(pos.quantity))

            tt_legs = []
            quantity = trade.get('quantity', 1)

            for leg_def in trade['legs']:
                occ = build_occ_symbol(
                    trade['ticker'], leg_def['expiration'],
                    leg_def['strike'], leg_def['option_type']
                )

                # Reverse the action: BUY→SELL_TO_CLOSE, SELL→BUY_TO_CLOSE
                if leg_def['action'] == 'BUY':
                    action = OrderAction.SELL_TO_CLOSE
                else:
                    action = OrderAction.BUY_TO_CLOSE

                leg_qty = leg_def.get('quantity', 1) * quantity
                # Cap at actual sandbox position to avoid "cannot close more than existing"
                actual_qty = pos_qty_map.get(occ, 0)
                if actual_qty > 0 and leg_qty > actual_qty:
                    logger.warning(f"Qty mismatch for {occ}: journal={leg_qty}, sandbox={actual_qty}. Using sandbox qty.")
                    leg_qty = actual_qty

                if leg_qty <= 0:
                    logger.warning(f"No position for {occ} in sandbox, skipping close leg")
                    continue

                tt_legs.append(Leg(
                    instrument_type=InstrumentType.EQUITY_OPTION,
                    symbol=occ,
                    quantity=Decimal(str(leg_qty)),
                    action=action,
                ))

            if not tt_legs:
                # No legs to close — sandbox may have reset
                closed = self.journal.close_trade(trade_id, 0, f'{reason}_no_position')
                if closed:
                    self._update_adaptive_systems(closed)
                return {'ok': True, 'trade': closed, 'multi_leg': True, 'note': 'no sandbox position'}

            # Compute limit price from live marks for proper fills
            close_price = Decimal('0.01')  # minimum fallback
            try:
                occ_symbols = []
                for leg_def in trade['legs']:
                    occ = build_occ_symbol(
                        trade['ticker'], leg_def['expiration'],
                        leg_def['strike'], leg_def['option_type']
                    )
                    occ_symbols.append((occ, leg_def['action']))
                live_marks = await self._fetch_live_marks([s[0] for s in occ_symbols])
                if live_marks:
                    # Net debit to close: sum of buy-to-close legs minus sell-to-close legs
                    net_debit = Decimal('0')
                    for occ, orig_action in occ_symbols:
                        mark = Decimal(str(live_marks.get(occ, 0)))
                        if orig_action == 'SELL':
                            # We're buying back this leg
                            net_debit += mark
                        else:
                            # We're selling this leg
                            net_debit -= mark
                    # Add 20% buffer to ensure fill, minimum $0.01
                    if net_debit > 0:
                        close_price = max(Decimal('0.01'), (net_debit * Decimal('1.20')).quantize(Decimal('0.01')))
                    else:
                        close_price = Decimal('0.01')
            except Exception as e:
                logger.warning(f"Could not compute close price from marks: {e}")

            # Multi-leg close orders must be Limit
            order = NewOrder(
                time_in_force=OrderTimeInForce.DAY,
                order_type=OrderType.LIMIT,
                price=close_price,
                legs=tt_legs,
            )

            response = await account.place_order(session, order, dry_run=False)
            fill_price = 0
            exit_net_premium = None
            if hasattr(response, 'order') and hasattr(response.order, 'price') and response.order.price:
                fill_price = float(response.order.price)
                # For closing orders: negative means debit paid to close
                exit_net_premium = -fill_price  # closing credit spreads costs money

            # Reassess exit_reason based on actual fill P&L
            # For credit spreads: P&L = entry_credit + exit_net_premium
            # If profitable close was labeled 'stop_loss', correct to 'take_profit'
            if exit_net_premium is not None and reason in ('stop_loss', 'take_profit'):
                entry_net = trade.get('net_premium', 0)
                actual_pnl = entry_net + exit_net_premium
                if actual_pnl > 0 and reason == 'stop_loss':
                    logger.info(f"Exit reassessed: stop_loss → take_profit (PnL ${actual_pnl:.4f} credit)")
                    reason = 'take_profit'
                elif actual_pnl < 0 and reason == 'take_profit':
                    logger.info(f"Exit reassessed: take_profit → stop_loss (PnL -${abs(actual_pnl):.4f})")
                    reason = 'stop_loss'

            closed = self.journal.close_trade(
                trade_id, fill_price, reason,
                exit_net_premium=exit_net_premium,
            )

            self._update_adaptive_systems(closed)

            logger.info(f"Multi-leg closed: {trade.get('strategy_name', '')} on {trade['ticker']}")
            return {'ok': True, 'trade': closed, 'multi_leg': True}

        except Exception as e:
            logger.error(f"Multi-leg close error: {e}")
            # Use computed close_price for P&L instead of 0 when order fails
            est_price = float(close_price) if close_price > Decimal('0.01') else 0
            est_net = -est_price if est_price > 0 else None
            closed = self.journal.close_trade(
                trade_id, est_price, f'{reason}_error',
                exit_net_premium=est_net,
            )
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

        # Check if marks are available (all 0 = after hours or sandbox stale)
        has_marks = any(
            (p.get('mark', 0) or p.get('close_price', 0)) > 0
            for p in positions
        )

        for trade in open_trades:
            is_multi_leg = trade.get('is_multi_leg', False)
            entry_price = trade.get('entry_price', 0)
            if entry_price <= 0:
                continue

            if is_multi_leg and trade.get('legs'):
                # Multi-leg: calculate net mark from all leg positions
                # For credit spreads: PnL = credit_received - cost_to_close
                net_mark = 0
                all_legs_found = True
                for leg in trade['legs']:
                    leg_occ = build_occ_symbol(
                        trade['ticker'], leg['expiration'],
                        leg['strike'], leg['option_type']
                    )
                    leg_pos = position_map.get(leg_occ)
                    if leg_pos:
                        leg_mark = leg_pos.get('mark', 0) or leg_pos.get('close_price', 0)
                        # SELL legs: we receive premium, so mark adds to cost-to-close
                        # BUY legs: we paid premium, mark reduces cost-to-close
                        if leg['action'] == 'SELL':
                            net_mark += leg_mark  # We'd buy back at this price
                        else:
                            net_mark -= leg_mark  # We'd sell at this price
                    else:
                        all_legs_found = False

                if not all_legs_found:
                    # Can't find all leg positions — skip exit check
                    logger.debug(f"Skipping exit check for {trade['ticker']}: not all legs found in positions")
                    continue

                # Check if ALL leg marks are zero (sandbox stale/after-hours)
                all_leg_marks_zero = True
                for leg in trade['legs']:
                    leg_occ = build_occ_symbol(
                        trade['ticker'], leg['expiration'],
                        leg['strike'], leg['option_type']
                    )
                    leg_pos = position_map.get(leg_occ)
                    if leg_pos and (leg_pos.get('mark', 0) or leg_pos.get('close_price', 0)) > 0:
                        all_leg_marks_zero = False
                        break

                # For credit spread: entry_price = net credit received
                # cost_to_close = net_mark (positive = we pay to close)
                # PnL = (credit - cost_to_close) / credit * 100
                # If net_mark is small, we keep most of credit = profit
                pnl_pct = ((entry_price - net_mark) / entry_price) * 100 if entry_price > 0 else 0
            else:
                # Single-leg trade
                occ_symbol = trade.get('occ_symbol') or build_occ_symbol(
                    trade['ticker'], trade['expiration'],
                    trade['strike'], trade['option_type']
                )

                pos = position_map.get(occ_symbol)
                current_price = 0
                if pos:
                    current_price = pos.get('mark', 0) or pos.get('close_price', 0)

                all_leg_marks_zero = current_price == 0

                # Calculate P&L %
                if trade['direction'] == 'long':
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
                else:
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100 if entry_price > 0 else 0

            # Per-trade mark validity: global has_marks AND this trade's marks are real
            trade_has_marks = has_marks and not all_leg_marks_zero

            # Minimum hold time: skip price-based exits for young positions
            min_hold = self.config.get('min_hold_minutes', 30)
            entry_time = trade.get('entry_time')
            if entry_time and trade_has_marks:
                try:
                    et = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                    age_minutes = (datetime.now(timezone.utc) - et).total_seconds() / 60
                    if age_minutes < min_hold:
                        logger.debug(f"Skipping exit for {trade['ticker']}: only {age_minutes:.0f}m old (min {min_hold}m)")
                        continue
                except (ValueError, TypeError):
                    pass

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
            # Only check price-based exits if this trade has valid marks
            # (marks=0 after hours or sandbox stale would trigger false exits)
            if trade_has_marks:
                if pnl_pct <= stop_loss:
                    exit_reason = 'stop_loss'
                elif pnl_pct >= take_profit:
                    exit_reason = 'take_profit'
            if not exit_reason and dte <= time_exit_dte:
                exit_reason = 'time_exit'

            # ---- Greeks-based exits ----

            # Exit: 50% Max Profit for credit spreads
            if not exit_reason and trade_has_marks and is_multi_leg:
                max_profit = trade.get('max_profit', 0)
                if max_profit and max_profit > 0:
                    # For credit spreads: realized profit based on PnL%
                    # pnl_pct is already (credit - cost_to_close) / credit * 100
                    # So pnl_pct >= 50 means we've captured 50% of max credit
                    if pnl_pct >= 50:
                        exit_reason = 'fifty_pct_max_profit'

            # Exit: Theta Acceleration Zone
            # Short premium with DTE <= 21 and profit >= 30% — gamma risk spikes
            if not exit_reason and trade_has_marks and dte <= 21 and pnl_pct >= 30:
                strategy = trade.get('strategy', '')
                is_short_premium = (
                    trade.get('direction') == 'short' or
                    'credit' in strategy.lower() or
                    'iron' in strategy.lower() or
                    'premium harvest' in strategy.lower() or
                    'condor' in strategy.lower() or
                    'butterfly' in strategy.lower()
                )
                if is_short_premium:
                    exit_reason = 'theta_acceleration'

            # Phase 3c: Edge-deterioration exit
            # If in profit and edge has collapsed, take profits early
            if not exit_reason and trade_has_marks and pnl_pct > 10 and self.edge_engine:
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

        # Replay closed trades through Thompson Sampling (reset state first)
        if self.adaptive_weights:
            self.adaptive_weights._cache = None
            if self.adaptive_weights.weights_file.exists():
                self.adaptive_weights.weights_file.unlink()
            weight_updates = 0
            for trade in closed:
                factor_scores = trade.get('entry_factor_scores', {})
                if factor_scores and trade.get('pnl_dollars') is not None:
                    self.adaptive_weights.update_from_trade(trade, factor_scores)
                    weight_updates += 1
            results['adaptive_weights'] = self.adaptive_weights.get_stats()
            results['adaptive_weights']['trades_replayed'] = weight_updates

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
                get_term_structure_tastytrade, get_iv_by_delta_tastytrade,
            )

            # Fetch regime + term structure + skew in parallel
            import asyncio
            regime, combined, chain, term_struct, skew_data = await asyncio.gather(
                get_gex_regime_tastytrade(ticker),
                get_combined_regime_tastytrade(ticker),
                get_options_with_greeks_tastytrade(ticker),
                get_term_structure_tastytrade(ticker),
                get_iv_by_delta_tastytrade(ticker),
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
                vrp = (iv_rank - 30) / 10  # Calibrated: IV Rank 70 → VRP 4.0

            # Extract term structure and skew
            real_structure = 'contango'
            if isinstance(term_struct, dict) and 'structure' in term_struct:
                real_structure = term_struct['structure']
            skew_ratio = 1.0
            if isinstance(skew_data, dict) and skew_data.get('skew_ratio'):
                skew_ratio = skew_data['skew_ratio']

            # Compute risk reversal for edge scoring
            risk_reversal = 0
            if isinstance(skew_data, dict):
                p25 = skew_data.get('put_25d_iv')
                c25 = skew_data.get('call_25d_iv')
                if p25 and c25:
                    risk_reversal = round(float(p25) - float(c25), 4)

            edge = self.edge_engine.compute_edge(
                composite_score=50,
                gex_regime=gex_regime,
                combined_regime=combined_regime,
                vrp=vrp,
                flow_toxicity=toxicity_data.get('toxicity', 0),
                dealer_flow_forecast={},
                signal_performance=self.perf_tracker.get_all_stats() if self.perf_tracker else {},
                adaptive_weights=self.adaptive_weights.get_weights() if self.adaptive_weights else {},
                term_structure=real_structure,
                skew_ratio=skew_ratio,
                risk_reversal=risk_reversal,
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

    async def strategy_preview(self, ticker: str) -> Dict:
        """Preview what multi-leg strategy would be built for current conditions."""
        try:
            from src.data.tastytrade_provider import (
                get_gex_regime_tastytrade, get_combined_regime_tastytrade,
                get_options_with_greeks_tastytrade,
                get_term_structure_tastytrade, get_iv_by_delta_tastytrade,
            )
            import asyncio

            regime, combined, chain, term_struct, skew_data = await asyncio.gather(
                get_gex_regime_tastytrade(ticker),
                get_combined_regime_tastytrade(ticker),
                get_options_with_greeks_tastytrade(ticker),
                get_term_structure_tastytrade(ticker),
                get_iv_by_delta_tastytrade(ticker),
                return_exceptions=True,
            )

            gex_regime = regime.get('regime', 'transitional') if isinstance(regime, dict) else 'transitional'
            combined_regime = combined.get('combined_regime', 'neutral_transitional') if isinstance(combined, dict) else 'neutral_transitional'
            underlying_price = regime.get('current_price', 0) if isinstance(regime, dict) else 0

            # Build regime state for strategy selection
            iv_rank = chain.get('iv_rank', 50) if isinstance(chain, dict) else 50
            vrp = (iv_rank - 30) / 10  # Calibrated: IV Rank 70 → VRP 4.0

            # Flow toxicity from chain
            options = chain.get('options', []) if isinstance(chain, dict) else []
            toxicity_data = self.flow_analyzer.compute_toxicity(options) if self.flow_analyzer else {'toxicity': 0.3}
            flow_toxicity = toxicity_data.get('toxicity', 0.3)

            # Real term structure and skew
            real_structure = 'contango'
            if isinstance(term_struct, dict) and 'structure' in term_struct:
                real_structure = term_struct['structure']
            skew_ratio = 1.0
            if isinstance(skew_data, dict) and skew_data.get('skew_ratio'):
                skew_ratio = skew_data['skew_ratio']

            # Compute risk reversal for strategy preview
            risk_reversal_preview = 0
            if isinstance(skew_data, dict):
                p25 = skew_data.get('put_25d_iv')
                c25 = skew_data.get('call_25d_iv')
                if p25 and c25:
                    risk_reversal_preview = round(float(p25) - float(c25), 4)

            regime_state = {
                'vrp': vrp,
                'gex_regime': gex_regime,
                'combined_regime': combined_regime,
                'flow_toxicity': flow_toxicity,
                'term_structure': real_structure,
                'skew_steep': skew_ratio > 1.15,
                'skew_ratio': skew_ratio,
                'iv_rank': iv_rank,
                'vanna_flow': 0.0,
                'macro_event_days': 99,
                'risk_reversal': risk_reversal_preview,
            }

            strategies = self.select_strategy(regime_state)
            if not strategies or strategies[0].get('name') == 'Wait / Reduce Size':
                return {
                    'ticker': ticker,
                    'strategy': None,
                    'regime_state': regime_state,
                    'message': 'No multi-leg strategy recommended for current conditions',
                }

            best = strategies[0]

            # Build preview legs if chain is available
            preview = None
            if isinstance(chain, dict) and chain.get('options'):
                dte_range = best.get('dte_range', [30, 45])
                actual_dte = chain.get('dte', (dte_range[0] + dte_range[1]) // 2)
                preview = self.strategy_builder.build_legs(
                    strategy_name=best['name'],
                    ticker=ticker,
                    direction=best.get('direction', 'neutral'),
                    chain_data=chain,
                    underlying_price=underlying_price,
                    delta_target=best.get('delta_target'),
                    iv_rank=iv_rank,
                    dte=actual_dte,
                )

            return {
                'ticker': ticker,
                'strategy': best,
                'regime_state': regime_state,
                'preview': preview,
                'underlying_price': underlying_price,
                'flow_toxicity': toxicity_data,
            }

        except Exception as e:
            logger.error(f"Strategy preview error for {ticker}: {e}")
            return {'ticker': ticker, 'error': str(e)}

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
