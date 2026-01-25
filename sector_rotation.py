#!/usr/bin/env python3
"""
Sector Rotation Model - Enhanced Version

Features:
- 11 S&P 500 sectors
- Sub-industry/industry group analysis
- Factor rotation (growth vs value, large vs small)
- Money flow tracking
- Sector momentum scoring
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


# Sector ETFs
SECTOR_ETFS = {
    'XLK': 'Technology',
    'XLF': 'Financials',
    'XLV': 'Healthcare',
    'XLE': 'Energy',
    'XLI': 'Industrials',
    'XLY': 'Consumer Disc',
    'XLP': 'Consumer Staples',
    'XLB': 'Materials',
    'XLU': 'Utilities',
    'XLRE': 'Real Estate',
    'XLC': 'Communication',
}

# Sub-industry ETFs for deeper analysis
SUB_INDUSTRY_ETFS = {
    # Technology sub-industries
    'SMH': 'Semiconductors',
    'IGV': 'Software',
    'CLOU': 'Cloud Computing',
    'HACK': 'Cybersecurity',
    'SOXX': 'Semis (Alt)',

    # Financials sub-industries
    'KBE': 'Banks',
    'KRE': 'Regional Banks',
    'KIE': 'Insurance',
    'IAI': 'Broker-Dealers',

    # Healthcare sub-industries
    'XBI': 'Biotech',
    'IHI': 'Medical Devices',
    'XHE': 'Healthcare Equipment',
    'IBB': 'Biotech (Nasdaq)',

    # Energy sub-industries
    'XOP': 'Oil & Gas E&P',
    'OIH': 'Oil Services',
    'AMLP': 'MLPs/Pipelines',

    # Industrials sub-industries
    'ITA': 'Aerospace & Defense',
    'XHB': 'Homebuilders',
    'ITB': 'Homebuilders (Alt)',

    # Consumer
    'XRT': 'Retail',
    'XLI': 'Industrials',
}

# Factor ETFs for factor rotation analysis
FACTOR_ETFS = {
    # Growth vs Value
    'IWF': 'Large Growth',
    'IWD': 'Large Value',
    'IWO': 'Small Growth',
    'IWN': 'Small Value',

    # Size
    'IWM': 'Small Cap',
    'IWB': 'Large Cap',
    'IJH': 'Mid Cap',

    # Quality/Momentum
    'QUAL': 'Quality Factor',
    'MTUM': 'Momentum Factor',
    'USMV': 'Low Volatility',
    'VLUE': 'Value Factor',
}

# Market cycle sectors (typical rotation pattern)
CYCLE_MAPPING = {
    'early_cycle': ['XLF', 'XLY', 'XLI', 'XLB'],      # Recovery
    'mid_cycle': ['XLK', 'XLC', 'XLI'],               # Expansion
    'late_cycle': ['XLE', 'XLB', 'XLI'],              # Peak
    'recession': ['XLV', 'XLP', 'XLU', 'XLRE'],       # Defensive
}

# Cache
CACHE_DIR = Path('cache')
CACHE_DIR.mkdir(exist_ok=True)


def calculate_sector_metrics(period='6mo'):
    """Calculate metrics for all sectors."""
    sectors = {}

    # Download SPY for relative strength
    spy = yf.download('SPY', period=period, progress=False)
    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)

    if len(spy) < 63:
        return sectors

    spy_returns = {
        '1w': (float(spy['Close'].iloc[-1]) / float(spy['Close'].iloc[-5]) - 1) * 100,
        '1m': (float(spy['Close'].iloc[-1]) / float(spy['Close'].iloc[-21]) - 1) * 100,
        '3m': (float(spy['Close'].iloc[-1]) / float(spy['Close'].iloc[-63]) - 1) * 100,
    }

    for etf, name in SECTOR_ETFS.items():
        try:
            df = yf.download(etf, period=period, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if len(df) < 63:
                continue

            close = df['Close']
            volume = df['Volume']
            current = float(close.iloc[-1])

            # Returns
            ret_1w = (current / float(close.iloc[-5]) - 1) * 100
            ret_1m = (current / float(close.iloc[-21]) - 1) * 100
            ret_3m = (current / float(close.iloc[-63]) - 1) * 100

            # Relative strength vs SPY
            rs_1w = ret_1w - spy_returns['1w']
            rs_1m = ret_1m - spy_returns['1m']
            rs_3m = ret_3m - spy_returns['3m']

            # Momentum score (weighted RS)
            momentum = rs_1w * 0.5 + rs_1m * 0.3 + rs_3m * 0.2

            # Trend (above MAs)
            sma_20 = float(close.rolling(20).mean().iloc[-1])
            sma_50 = float(close.rolling(50).mean().iloc[-1])

            trend = 'UPTREND' if current > sma_20 > sma_50 else ('DOWNTREND' if current < sma_20 < sma_50 else 'NEUTRAL')

            # Momentum change (acceleration)
            momentum_1w_ago = 0
            if len(close) > 10:
                ret_1w_prev = (float(close.iloc[-6]) / float(close.iloc[-10]) - 1) * 100
                spy_1w_prev = (float(spy['Close'].iloc[-6]) / float(spy['Close'].iloc[-10]) - 1) * 100
                momentum_1w_ago = ret_1w_prev - spy_1w_prev

            acceleration = rs_1w - momentum_1w_ago

            # Money flow (volume trend)
            vol_avg = float(volume.iloc[-20:].mean())
            vol_recent = float(volume.iloc[-5:].mean())
            vol_trend = (vol_recent / vol_avg - 1) * 100 if vol_avg > 0 else 0

            sectors[etf] = {
                'name': name,
                'etf': etf,
                'return_1w': round(ret_1w, 2),
                'return_1m': round(ret_1m, 2),
                'return_3m': round(ret_3m, 2),
                'rs_1w': round(rs_1w, 2),
                'rs_1m': round(rs_1m, 2),
                'rs_3m': round(rs_3m, 2),
                'momentum': round(momentum, 2),
                'acceleration': round(acceleration, 2),
                'trend': trend,
                'vol_trend': round(vol_trend, 1),
            }

        except Exception as e:
            continue

    return sectors


def calculate_sub_industry_metrics(period='3mo'):
    """Calculate metrics for sub-industries."""
    sub_industries = {}

    spy = yf.download('SPY', period=period, progress=False)
    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)

    if len(spy) < 21:
        return sub_industries

    spy_ret_1m = (float(spy['Close'].iloc[-1]) / float(spy['Close'].iloc[-21]) - 1) * 100

    for etf, name in SUB_INDUSTRY_ETFS.items():
        try:
            df = yf.download(etf, period=period, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if len(df) < 21:
                continue

            close = df['Close']
            current = float(close.iloc[-1])

            ret_1w = (current / float(close.iloc[-5]) - 1) * 100
            ret_1m = (current / float(close.iloc[-21]) - 1) * 100

            rs_1m = ret_1m - spy_ret_1m

            sub_industries[etf] = {
                'name': name,
                'etf': etf,
                'return_1w': round(ret_1w, 2),
                'return_1m': round(ret_1m, 2),
                'rs_1m': round(rs_1m, 2),
            }

        except:
            continue

    return sub_industries


def calculate_factor_rotation(period='3mo'):
    """Calculate factor rotation metrics."""
    factors = {}

    spy = yf.download('SPY', period=period, progress=False)
    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)

    if len(spy) < 21:
        return factors

    spy_ret = (float(spy['Close'].iloc[-1]) / float(spy['Close'].iloc[-21]) - 1) * 100

    for etf, name in FACTOR_ETFS.items():
        try:
            df = yf.download(etf, period=period, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if len(df) < 21:
                continue

            close = df['Close']
            current = float(close.iloc[-1])

            ret_1m = (current / float(close.iloc[-21]) - 1) * 100
            rs = ret_1m - spy_ret

            factors[etf] = {
                'name': name,
                'etf': etf,
                'return_1m': round(ret_1m, 2),
                'rs': round(rs, 2),
            }

        except:
            continue

    # Calculate factor spreads
    spreads = {}

    # Growth vs Value spread
    if 'IWF' in factors and 'IWD' in factors:
        spreads['growth_value'] = {
            'spread': round(factors['IWF']['return_1m'] - factors['IWD']['return_1m'], 2),
            'favors': 'Growth' if factors['IWF']['return_1m'] > factors['IWD']['return_1m'] else 'Value',
        }

    # Large vs Small spread
    if 'IWB' in factors and 'IWM' in factors:
        spreads['large_small'] = {
            'spread': round(factors['IWB']['return_1m'] - factors['IWM']['return_1m'], 2),
            'favors': 'Large Cap' if factors['IWB']['return_1m'] > factors['IWM']['return_1m'] else 'Small Cap',
        }

    # Momentum vs Value
    if 'MTUM' in factors and 'VLUE' in factors:
        spreads['momentum_value'] = {
            'spread': round(factors['MTUM']['return_1m'] - factors['VLUE']['return_1m'], 2),
            'favors': 'Momentum' if factors['MTUM']['return_1m'] > factors['VLUE']['return_1m'] else 'Value',
        }

    return {'factors': factors, 'spreads': spreads}


def rank_sectors(sectors):
    """Rank sectors by momentum."""
    ranked = sorted(sectors.values(), key=lambda x: x['momentum'], reverse=True)

    for i, sector in enumerate(ranked):
        sector['rank'] = i + 1
        sector['position'] = 'LEADING' if i < 3 else ('LAGGING' if i >= len(ranked) - 3 else 'NEUTRAL')

    return ranked


def detect_rotation(current_sectors, previous_sectors=None):
    """Detect sector rotation patterns."""
    if previous_sectors is None:
        return []

    rotations = []

    for etf, current in current_sectors.items():
        prev = previous_sectors.get(etf)
        if prev is None:
            continue

        rank_change = prev.get('rank', 0) - current['rank']

        if rank_change >= 3:
            rotations.append({
                'sector': current['name'],
                'etf': etf,
                'direction': 'GAINING',
                'rank_change': rank_change,
                'from_rank': prev.get('rank', 0),
                'to_rank': current['rank'],
            })
        elif rank_change <= -3:
            rotations.append({
                'sector': current['name'],
                'etf': etf,
                'direction': 'LOSING',
                'rank_change': rank_change,
                'from_rank': prev.get('rank', 0),
                'to_rank': current['rank'],
            })

    return rotations


def identify_cycle_phase(ranked_sectors):
    """Identify current market cycle phase based on leading sectors."""
    top_3 = [s['etf'] for s in ranked_sectors[:3]]

    scores = {
        'early_cycle': 0,
        'mid_cycle': 0,
        'late_cycle': 0,
        'recession': 0,
    }

    for phase, etfs in CYCLE_MAPPING.items():
        for etf in top_3:
            if etf in etfs:
                scores[phase] += 1

    # Determine most likely phase
    likely_phase = max(scores, key=scores.get)
    confidence = scores[likely_phase] / 3 * 100

    return {
        'phase': likely_phase,
        'confidence': round(confidence, 0),
        'scores': scores,
    }


def format_sector_rotation_report(ranked_sectors, rotations, cycle, factor_data=None):
    """Format sector rotation report for Telegram."""
    msg = "🔄 *SECTOR ROTATION REPORT*\n\n"

    # Top sectors
    msg += "*📈 LEADING SECTORS:*\n"
    for s in ranked_sectors[:3]:
        accel = "⬆️" if s['acceleration'] > 1 else ("⬇️" if s['acceleration'] < -1 else "➡️")
        vol = "📊" if s.get('vol_trend', 0) > 20 else ""
        msg += f"{s['rank']}. `{s['name']}` | RS: {s['momentum']:+.1f}% {accel} {vol}\n"

    # Bottom sectors
    msg += "\n*📉 LAGGING SECTORS:*\n"
    for s in ranked_sectors[-3:]:
        msg += f"{s['rank']}. `{s['name']}` | RS: {s['momentum']:+.1f}%\n"

    # Rotation alerts
    if rotations:
        msg += "\n*🔀 ROTATION DETECTED:*\n"
        for r in rotations[:3]:
            emoji = "🟢" if r['direction'] == 'GAINING' else "🔴"
            msg += f"{emoji} {r['sector']}: #{r['from_rank']} → #{r['to_rank']}\n"

    # Factor analysis
    if factor_data and factor_data.get('spreads'):
        msg += "\n*📊 FACTOR ROTATION:*\n"
        spreads = factor_data['spreads']

        if 'growth_value' in spreads:
            gv = spreads['growth_value']
            msg += f"• Growth vs Value: {gv['spread']:+.1f}% → _{gv['favors']}_\n"

        if 'large_small' in spreads:
            ls = spreads['large_small']
            msg += f"• Large vs Small: {ls['spread']:+.1f}% → _{ls['favors']}_\n"

        if 'momentum_value' in spreads:
            mv = spreads['momentum_value']
            msg += f"• Momentum vs Value: {mv['spread']:+.1f}% → _{mv['favors']}_\n"

    # Cycle phase
    phase_emoji = {
        'early_cycle': '🌱',
        'mid_cycle': '☀️',
        'late_cycle': '🍂',
        'recession': '❄️',
    }

    msg += f"\n*📊 CYCLE PHASE:* {phase_emoji.get(cycle['phase'], '')} {cycle['phase'].replace('_', ' ').title()}\n"
    msg += f"Confidence: {cycle['confidence']:.0f}%"

    return msg


def format_sub_industry_report(sub_industries):
    """Format sub-industry analysis."""
    if not sub_industries:
        return "No sub-industry data available."

    msg = "🔬 *SUB-INDUSTRY ANALYSIS*\n\n"

    # Sort by RS
    ranked = sorted(sub_industries.values(), key=lambda x: x['rs_1m'], reverse=True)

    msg += "*🔥 HOT INDUSTRIES:*\n"
    for s in ranked[:5]:
        emoji = "🟢" if s['rs_1m'] > 0 else "🔴"
        msg += f"{emoji} `{s['name']}` RS: {s['rs_1m']:+.1f}%\n"

    msg += "\n*❄️ COLD INDUSTRIES:*\n"
    for s in ranked[-5:]:
        emoji = "🔴" if s['rs_1m'] < 0 else "🟢"
        msg += f"{emoji} `{s['name']}` RS: {s['rs_1m']:+.1f}%\n"

    return msg


def save_sector_state(sectors):
    """Save current sector state for comparison."""
    state = {
        'timestamp': datetime.now().isoformat(),
        'sectors': sectors,
    }
    with open(CACHE_DIR / 'sector_state.json', 'w') as f:
        json.dump(state, f, indent=2)


def load_previous_sector_state():
    """Load previous sector state."""
    state_file = CACHE_DIR / 'sector_state.json'
    if state_file.exists():
        with open(state_file, 'r') as f:
            return json.load(f).get('sectors', {})
    return None


def run_sector_rotation_analysis(include_sub_industries=False, include_factors=True):
    """Run full sector rotation analysis."""
    print("Analyzing sector rotation...")

    # Calculate current metrics
    sectors = calculate_sector_metrics()

    # Load previous state
    prev_sectors = load_previous_sector_state()

    # Rank sectors
    ranked = rank_sectors(sectors)

    # Detect rotation
    rotations = detect_rotation(sectors, prev_sectors)

    # Identify cycle
    cycle = identify_cycle_phase(ranked)

    # Factor rotation
    factor_data = None
    if include_factors:
        factor_data = calculate_factor_rotation()

    # Sub-industry analysis
    sub_industries = None
    if include_sub_industries:
        sub_industries = calculate_sub_industry_metrics()

    # Save current state
    save_sector_state(sectors)

    return {
        'ranked': ranked,
        'rotations': rotations,
        'cycle': cycle,
        'factor_data': factor_data,
        'sub_industries': sub_industries,
        'timestamp': datetime.now().isoformat(),
    }


def get_best_sectors_for_regime(market_regime='bull'):
    """Get recommended sectors based on market regime."""
    recommendations = {
        'bull': ['XLK', 'XLY', 'XLF', 'XLC'],
        'bear': ['XLV', 'XLP', 'XLU'],
        'neutral': ['XLK', 'XLV', 'XLI'],
    }
    return recommendations.get(market_regime, recommendations['neutral'])


if __name__ == '__main__':
    results = run_sector_rotation_analysis(include_sub_industries=True, include_factors=True)

    print("\n" + "=" * 60)
    print(format_sector_rotation_report(
        results['ranked'],
        results['rotations'],
        results['cycle'],
        results['factor_data']
    ))

    if results['sub_industries']:
        print("\n" + "=" * 60)
        print(format_sub_industry_report(results['sub_industries']))
