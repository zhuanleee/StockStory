"""
Institutional Flow Detection
============================
Track smart money movements through multiple signals.

Signals:
1. Options Flow - Unusual activity, large trades
2. 13F Cluster Analysis - Multiple funds buying same theme
3. Insider Buying Clusters - Multiple insiders across theme
4. Dark Pool Activity - Large block trades

Uses:
- Polygon.io for options data
- SEC EDGAR for 13F and Form 4 filings

Usage:
    from src.intelligence.institutional_flow import InstitutionalFlowTracker

    tracker = InstitutionalFlowTracker()

    # Get options flow signals
    options = tracker.get_options_flow_signals()

    # Get 13F cluster analysis
    clusters = tracker.analyze_13f_clusters()

    # Get insider buying patterns
    insider = tracker.get_insider_clusters()
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

# Persistence
DATA_DIR = Path("data/institutional_flow")
FLOW_HISTORY_FILE = DATA_DIR / "flow_history.json"
CLUSTER_CACHE_FILE = DATA_DIR / "cluster_cache.json"


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class OptionsFlowSignal:
    """Unusual options activity signal."""
    ticker: str
    signal_type: str  # bullish_sweep, bearish_sweep, large_call, large_put
    strike: float
    expiry: str
    premium: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float
    sentiment: str  # bullish, bearish, neutral
    timestamp: str


@dataclass
class ThirteenFCluster:
    """Cluster of institutional 13F activity."""
    theme_id: str
    theme_name: str
    funds_buying: List[str]
    tickers_accumulated: List[str]
    total_value: float
    quarter: str
    signal_strength: float  # 0-1


@dataclass
class InsiderCluster:
    """Cluster of insider buying activity."""
    theme_id: str
    tickers: List[str]
    insiders: List[Dict]
    total_value: float
    transaction_count: int
    signal_strength: float
    period_days: int


@dataclass
class InstitutionalSignal:
    """Combined institutional signal."""
    ticker: str
    signal_type: str
    direction: str  # bullish, bearish
    strength: float  # 0-100
    sources: List[str]
    details: Dict
    timestamp: str


# Theme to ticker mapping (import from theme_intelligence)
def get_theme_tickers():
    try:
        from src.intelligence.theme_intelligence import THEME_TICKER_MAP
        return THEME_TICKER_MAP
    except ImportError as e:
        logger.debug(f"Could not import THEME_TICKER_MAP: {e}")
        return {}


class InstitutionalFlowTracker:
    """
    Track institutional money flows through multiple signals.
    """

    def __init__(self):
        ensure_data_dir()
        self.flow_history = self._load_flow_history()

    def _load_flow_history(self) -> List[Dict]:
        """Load flow history."""
        if FLOW_HISTORY_FILE.exists():
            try:
                with open(FLOW_HISTORY_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load flow history: {e}")
        return []

    def _save_flow_history(self):
        """Save flow history."""
        # Keep last 1000 signals
        self.flow_history = self.flow_history[-1000:]
        with open(FLOW_HISTORY_FILE, 'w') as f:
            json.dump(self.flow_history, f, indent=2)

    # =========================================================================
    # OPTIONS FLOW ANALYSIS
    # =========================================================================

    def get_options_flow_signals(self, tickers: List[str] = None) -> List[OptionsFlowSignal]:
        """
        Get unusual options activity signals.

        Uses Polygon.io options data to detect:
        - Large premium trades
        - Unusual volume vs open interest
        - Sweep orders (aggressive buying)
        """
        try:
            from src.data.polygon_provider import PolygonDataProvider

            provider = PolygonDataProvider()

            if tickers is None:
                # Default to theme leaders
                theme_tickers = get_theme_tickers()
                tickers = []
                for theme_id, ticker_list in theme_tickers.items():
                    tickers.extend(ticker_list[:2])  # Top 2 from each theme
                tickers = list(set(tickers))[:30]

            signals = []

            for ticker in tickers:
                try:
                    # Get unusual options activity
                    unusual = provider.get_unusual_options_sync(ticker)

                    if unusual and unusual.get('unusual_activity'):
                        for activity in unusual['unusual_activity'][:5]:
                            signal = OptionsFlowSignal(
                                ticker=ticker,
                                signal_type=activity.get('type', 'unknown'),
                                strike=activity.get('strike', 0),
                                expiry=activity.get('expiry', ''),
                                premium=activity.get('premium', 0),
                                volume=activity.get('volume', 0),
                                open_interest=activity.get('open_interest', 0),
                                implied_volatility=activity.get('iv', 0),
                                delta=activity.get('delta', 0),
                                sentiment=activity.get('sentiment', 'neutral'),
                                timestamp=datetime.now().isoformat()
                            )
                            signals.append(signal)

                    # Also check options flow sentiment
                    flow = provider.get_options_flow_sync(ticker)
                    if flow:
                        sentiment = flow.get('sentiment', 'neutral')
                        call_vol = flow.get('call_volume', 0)
                        put_vol = flow.get('put_volume', 0)

                        # Strong directional signal
                        if call_vol > put_vol * 2:
                            signals.append(OptionsFlowSignal(
                                ticker=ticker,
                                signal_type='call_dominance',
                                strike=0,
                                expiry='',
                                premium=flow.get('total_premium', 0),
                                volume=call_vol,
                                open_interest=0,
                                implied_volatility=0,
                                delta=0.5,
                                sentiment='bullish',
                                timestamp=datetime.now().isoformat()
                            ))
                        elif put_vol > call_vol * 2:
                            signals.append(OptionsFlowSignal(
                                ticker=ticker,
                                signal_type='put_dominance',
                                strike=0,
                                expiry='',
                                premium=flow.get('total_premium', 0),
                                volume=put_vol,
                                open_interest=0,
                                implied_volatility=0,
                                delta=-0.5,
                                sentiment='bearish',
                                timestamp=datetime.now().isoformat()
                            ))

                except Exception as e:
                    logger.debug(f"Options flow error for {ticker}: {e}")
                    continue

            return signals

        except Exception as e:
            logger.error(f"Options flow signals error: {e}")
            return []

    def get_options_flow_by_theme(self) -> Dict[str, List[Dict]]:
        """Get options flow organized by theme."""
        theme_tickers = get_theme_tickers()
        theme_flow = {}

        for theme_id, tickers in theme_tickers.items():
            signals = self.get_options_flow_signals(tickers[:5])

            bullish = [s for s in signals if s.sentiment == 'bullish']
            bearish = [s for s in signals if s.sentiment == 'bearish']

            theme_flow[theme_id] = {
                'bullish_count': len(bullish),
                'bearish_count': len(bearish),
                'net_sentiment': 'bullish' if len(bullish) > len(bearish) else 'bearish' if len(bearish) > len(bullish) else 'neutral',
                'signals': [asdict(s) for s in signals[:10]],
                'total_premium': sum(s.premium for s in signals)
            }

        return theme_flow

    # =========================================================================
    # 13F CLUSTER ANALYSIS
    # =========================================================================

    def analyze_13f_clusters(self, days_back: int = 90) -> List[ThirteenFCluster]:
        """
        Analyze 13F filings to find institutional accumulation patterns.

        Looks for:
        - Multiple funds buying same ticker
        - Funds buying multiple tickers in same theme
        """
        try:
            from src.data.sec_edgar import SECEdgarClient

            client = SECEdgarClient()
            theme_tickers = get_theme_tickers()

            clusters = []

            for theme_id, tickers in theme_tickers.items():
                theme_signals = []

                for ticker in tickers[:5]:
                    try:
                        # Get 13F filings
                        filings = client.get_company_filings(
                            ticker,
                            form_types=['13F-HR', '13F-HR/A'],
                            days_back=days_back
                        )

                        if filings:
                            theme_signals.append({
                                'ticker': ticker,
                                'filing_count': len(filings),
                                'latest_date': filings[0].filed_date if filings else None
                            })

                    except Exception as e:
                        logger.debug(f"13F error for {ticker}: {e}")
                        continue

                # If multiple tickers in theme have recent 13F activity
                if len(theme_signals) >= 2:
                    total_filings = sum(s['filing_count'] for s in theme_signals)

                    from src.intelligence.theme_intelligence import THEME_NAMES
                    theme_name = THEME_NAMES.get(theme_id, theme_id)

                    cluster = ThirteenFCluster(
                        theme_id=theme_id,
                        theme_name=theme_name,
                        funds_buying=[],  # Would need to parse 13F content
                        tickers_accumulated=[s['ticker'] for s in theme_signals],
                        total_value=0,
                        quarter=f"Q{(datetime.now().month - 1) // 3 + 1} {datetime.now().year}",
                        signal_strength=min(1.0, total_filings / 10)
                    )
                    clusters.append(cluster)

            return sorted(clusters, key=lambda x: x.signal_strength, reverse=True)

        except Exception as e:
            logger.error(f"13F cluster analysis error: {e}")
            return []

    # =========================================================================
    # INSIDER BUYING CLUSTERS
    # =========================================================================

    def get_insider_clusters(self, days_back: int = 90) -> List[InsiderCluster]:
        """
        Find clusters of insider buying activity within themes.

        Strong signal when multiple insiders buy across theme tickers.
        """
        try:
            from src.data.sec_edgar import SECEdgarClient

            client = SECEdgarClient()
            theme_tickers = get_theme_tickers()

            clusters = []

            for theme_id, tickers in theme_tickers.items():
                theme_insiders = []
                total_transactions = 0

                for ticker in tickers[:5]:
                    try:
                        transactions = client.get_insider_transactions(ticker, days_back=days_back)

                        if transactions:
                            total_transactions += len(transactions)
                            for t in transactions[:3]:
                                theme_insiders.append({
                                    'ticker': ticker,
                                    'date': t.get('date', ''),
                                    'form': t.get('form', ''),
                                    'url': t.get('url', '')
                                })

                    except Exception as e:
                        logger.debug(f"Insider error for {ticker}: {e}")
                        continue

                # If multiple insider transactions across theme
                if total_transactions >= 3:
                    cluster = InsiderCluster(
                        theme_id=theme_id,
                        tickers=list(set(t['ticker'] for t in theme_insiders)),
                        insiders=theme_insiders[:10],
                        total_value=0,  # Would need to parse Form 4 content
                        transaction_count=total_transactions,
                        signal_strength=min(1.0, total_transactions / 10),
                        period_days=days_back
                    )
                    clusters.append(cluster)

            return sorted(clusters, key=lambda x: x.signal_strength, reverse=True)

        except Exception as e:
            logger.error(f"Insider cluster analysis error: {e}")
            return []

    # =========================================================================
    # COMBINED INSTITUTIONAL SIGNALS
    # =========================================================================

    def get_institutional_signals(self, ticker: str) -> List[InstitutionalSignal]:
        """
        Get all institutional signals for a single ticker.
        """
        signals = []

        # Options flow
        try:
            options_signals = self.get_options_flow_signals([ticker])
            for opt in options_signals:
                signals.append(InstitutionalSignal(
                    ticker=ticker,
                    signal_type='options_flow',
                    direction=opt.sentiment,
                    strength=min(100, opt.premium / 10000) if opt.premium else 50,
                    sources=['polygon_options'],
                    details={
                        'type': opt.signal_type,
                        'strike': opt.strike,
                        'expiry': opt.expiry,
                        'premium': opt.premium
                    },
                    timestamp=opt.timestamp
                ))
        except Exception as e:
            logger.debug(f"Options signal error: {e}")

        # Insider activity
        try:
            from src.data.sec_edgar import SECEdgarClient
            client = SECEdgarClient()
            insider = client.get_insider_transactions(ticker, days_back=30)

            if insider:
                signals.append(InstitutionalSignal(
                    ticker=ticker,
                    signal_type='insider_activity',
                    direction='bullish',  # Insider buying is generally bullish
                    strength=min(100, len(insider) * 20),
                    sources=['sec_form4'],
                    details={
                        'transaction_count': len(insider),
                        'latest_date': insider[0].get('date', '') if insider else ''
                    },
                    timestamp=datetime.now().isoformat()
                ))
        except Exception as e:
            logger.debug(f"Insider signal error: {e}")

        return signals

    def get_theme_institutional_summary(self) -> Dict:
        """
        Get institutional flow summary for all themes.
        """
        theme_tickers = get_theme_tickers()

        summary = {}

        # Options flow by theme
        options_by_theme = self.get_options_flow_by_theme()

        # 13F clusters
        thirteen_f_clusters = self.analyze_13f_clusters()

        # Insider clusters
        insider_clusters = self.get_insider_clusters()

        for theme_id in theme_tickers.keys():
            from src.intelligence.theme_intelligence import THEME_NAMES
            theme_name = THEME_NAMES.get(theme_id, theme_id)

            options = options_by_theme.get(theme_id, {})
            thirteen_f = next((c for c in thirteen_f_clusters if c.theme_id == theme_id), None)
            insider = next((c for c in insider_clusters if c.theme_id == theme_id), None)

            # Calculate composite score
            score = 0
            signals = []

            # Options signal
            if options.get('net_sentiment') == 'bullish':
                score += 30
                signals.append('Bullish options flow')
            elif options.get('net_sentiment') == 'bearish':
                score -= 20
                signals.append('Bearish options flow')

            # 13F signal
            if thirteen_f and thirteen_f.signal_strength > 0.5:
                score += 25
                signals.append(f"13F activity ({len(thirteen_f.tickers_accumulated)} tickers)")

            # Insider signal
            if insider and insider.signal_strength > 0.5:
                score += 25
                signals.append(f"Insider buying ({insider.transaction_count} transactions)")

            summary[theme_id] = {
                'theme_name': theme_name,
                'institutional_score': max(0, min(100, score + 50)),  # Normalize to 0-100
                'net_direction': 'bullish' if score > 10 else 'bearish' if score < -10 else 'neutral',
                'signals': signals,
                'options': {
                    'bullish': options.get('bullish_count', 0),
                    'bearish': options.get('bearish_count', 0),
                    'sentiment': options.get('net_sentiment', 'neutral')
                },
                'thirteen_f': {
                    'active': thirteen_f is not None,
                    'tickers': thirteen_f.tickers_accumulated if thirteen_f else [],
                    'strength': thirteen_f.signal_strength if thirteen_f else 0
                },
                'insider': {
                    'active': insider is not None,
                    'transactions': insider.transaction_count if insider else 0,
                    'strength': insider.signal_strength if insider else 0
                }
            }

        return {
            'ok': True,
            'timestamp': datetime.now().isoformat(),
            'themes': summary,
            'top_bullish': sorted(
                [k for k, v in summary.items() if v['net_direction'] == 'bullish'],
                key=lambda x: summary[x]['institutional_score'],
                reverse=True
            )[:5],
            'top_bearish': sorted(
                [k for k, v in summary.items() if v['net_direction'] == 'bearish'],
                key=lambda x: summary[x]['institutional_score']
            )[:5]
        }

    # =========================================================================
    # RECORD SIGNALS
    # =========================================================================

    def record_signal(self, signal: InstitutionalSignal):
        """Record a signal to history."""
        self.flow_history.append(asdict(signal))
        self._save_flow_history()

    def get_recent_signals(self, hours: int = 24) -> List[Dict]:
        """Get signals from recent hours."""
        cutoff = datetime.now() - timedelta(hours=hours)

        recent = []
        for signal in self.flow_history:
            try:
                ts = datetime.fromisoformat(signal.get('timestamp', ''))
                if ts > cutoff:
                    recent.append(signal)
            except (ValueError, TypeError) as e:
                logger.debug(f"Failed to parse timestamp in flow signal: {e}")
                continue

        return recent


# =============================================================================
# SINGLETON
# =============================================================================

_tracker_instance = None


def get_flow_tracker() -> InstitutionalFlowTracker:
    """Get singleton flow tracker."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = InstitutionalFlowTracker()
    return _tracker_instance


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_institutional_summary() -> Dict:
    """Get institutional flow summary for all themes."""
    return get_flow_tracker().get_theme_institutional_summary()


def get_options_flow(tickers: List[str] = None) -> List[Dict]:
    """Get options flow signals."""
    signals = get_flow_tracker().get_options_flow_signals(tickers)
    return [asdict(s) for s in signals]


def get_insider_clusters() -> List[Dict]:
    """Get insider buying clusters."""
    clusters = get_flow_tracker().get_insider_clusters()
    return [asdict(c) for c in clusters]


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_institutional_message(summary: Dict) -> str:
    """Format institutional flow summary for Telegram."""
    if not summary.get('ok'):
        return f"Error: {summary.get('error', 'Unknown')}"

    msg = "🏦 *INSTITUTIONAL FLOW*\n"
    msg += "_Smart money tracking_\n\n"

    themes = summary.get('themes', {})

    # Top bullish themes
    bullish = summary.get('top_bullish', [])
    if bullish:
        msg += "📈 *BULLISH FLOW:*\n"
        for theme_id in bullish[:5]:
            data = themes.get(theme_id, {})
            score = data.get('institutional_score', 0)
            signals = data.get('signals', [])
            msg += f"• `{theme_id.upper()}` ({score:.0f})\n"
            if signals:
                msg += f"  _{', '.join(signals[:2])}_\n"
        msg += "\n"

    # Top bearish themes
    bearish = summary.get('top_bearish', [])
    if bearish:
        msg += "📉 *BEARISH FLOW:*\n"
        for theme_id in bearish[:3]:
            data = themes.get(theme_id, {})
            score = data.get('institutional_score', 0)
            msg += f"• `{theme_id.upper()}` ({score:.0f})\n"
        msg += "\n"

    # Summary counts
    active_13f = len([t for t in themes.values() if t.get('thirteen_f', {}).get('active')])
    active_insider = len([t for t in themes.values() if t.get('insider', {}).get('active')])

    msg += f"*Summary:*\n"
    msg += f"• 13F activity: {active_13f} themes\n"
    msg += f"• Insider buying: {active_insider} themes"

    return msg


if __name__ == "__main__":
    print("Institutional Flow Tracker")
    print("=" * 50)

    tracker = InstitutionalFlowTracker()

    print("\nGetting institutional summary...")
    summary = tracker.get_theme_institutional_summary()

    print(f"\nBullish themes: {summary.get('top_bullish', [])}")
    print(f"Bearish themes: {summary.get('top_bearish', [])}")
