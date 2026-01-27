#!/usr/bin/env python3
"""
Market Health Module - Enhanced Version

Calculates:
- Market Breadth indicators (expanded universe)
- Fear & Greed Index (real data sources)
- McClellan Oscillator
- Overall market health score

Data Sources:
- yfinance: VIX, SPY, TLT, HYG, LQD, individual stocks
- CBOE Put/Call Ratio (via proxy)
- NYSE Highs/Lows indicators
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

from config import config
from utils import (
    get_logger, normalize_dataframe_columns, get_spy_data_cached,
    calculate_rs, safe_float, download_stock_data,
)

logger = get_logger(__name__)

# Try to import dynamic universe manager
try:
    from universe_manager import get_universe_manager
    HAS_UNIVERSE_MANAGER = True
except ImportError:
    HAS_UNIVERSE_MANAGER = False
    logger.debug("Universe manager not available for breadth calculation")

# Full S&P 500 stock universe for breadth calculation
# Updated January 2025 - excludes recently delisted tickers
BREADTH_UNIVERSE = [
    # Information Technology (70+)
    'AAPL', 'MSFT', 'NVDA', 'AVGO', 'ORCL', 'CRM', 'CSCO', 'AMD', 'ACN', 'ADBE',
    'IBM', 'QCOM', 'TXN', 'INTU', 'AMAT', 'NOW', 'ADI', 'LRCX', 'MU', 'KLAC',
    'APH', 'MSI', 'SNPS', 'CDNS', 'FTNT', 'PANW', 'ROP', 'ADSK', 'MCHP', 'TEL',
    'NXPI', 'ON', 'HPQ', 'KEYS', 'ANSS', 'CDW', 'FSLR', 'MPWR', 'TYL', 'ZBRA',
    'NTAP', 'PTC', 'AKAM', 'EPAM', 'JNPR', 'SWKS', 'TER', 'QRVO', 'GLW', 'FFIV',
    'GEN', 'TRMB', 'JBL', 'ENPH', 'SEDG', 'CTSH', 'IT', 'VRSN', 'WDC', 'STX',
    'HPE', 'DELL', 'GDDY', 'SMCI', 'CRWD', 'PLTR', 'MRVL',
    # Financials (70+)
    'JPM', 'V', 'MA', 'BAC', 'WFC', 'GS', 'MS', 'SPGI', 'AXP', 'BLK',
    'C', 'SCHW', 'CB', 'PGR', 'MMC', 'ICE', 'CME', 'AON', 'USB', 'PNC',
    'TFC', 'AIG', 'MET', 'PRU', 'AFL', 'ALL', 'TRV', 'MCO', 'AJG', 'MSCI',
    'BK', 'COF', 'STT', 'DFS', 'FITB', 'HBAN', 'RF', 'CFG', 'NTRS', 'KEY',
    'SYF', 'WRB', 'CINF', 'L', 'RJF', 'BRO', 'EG', 'FDS', 'CBOE', 'NDAQ',
    'TROW', 'IVZ', 'BEN', 'JKHY', 'MKTX', 'ERIE', 'GL', 'AIZ', 'LNC', 'FRC',
    'ACGL', 'HIG', 'MTB', 'ZION', 'CMA', 'WBS',
    # Healthcare (65+)
    'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'TMO', 'ABT', 'PFE', 'DHR', 'AMGN',
    'ISRG', 'ELV', 'BMY', 'VRTX', 'MDT', 'GILD', 'SYK', 'CI', 'CVS', 'REGN',
    'BSX', 'ZTS', 'BDX', 'HUM', 'MCK', 'EW', 'IDXX', 'A', 'IQV', 'MTD',
    'CAH', 'GEHC', 'DXCM', 'WST', 'RMD', 'BAX', 'ALGN', 'HOLX', 'ILMN', 'COO',
    'WAT', 'ZBH', 'PODD', 'STE', 'MOH', 'CNC', 'TECH', 'LH', 'DGX', 'VTRS',
    'CRL', 'XRAY', 'HSIC', 'OGN', 'CTLT', 'RVTY', 'MRNA', 'BIIB', 'INCY',
    # Consumer Discretionary (60+)
    'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'LOW', 'SBUX', 'TJX', 'BKNG', 'CMG',
    'ORLY', 'MAR', 'AZO', 'ROST', 'DHI', 'YUM', 'GM', 'LEN', 'F', 'ABNB',
    'HLT', 'GRMN', 'DG', 'DLTR', 'EBAY', 'APTV', 'TSCO', 'BBY', 'ULTA', 'DRI',
    'LVS', 'WYNN', 'CZR', 'MGM', 'RCL', 'CCL', 'NCLH', 'EXPE', 'GPC', 'PHM',
    'NVR', 'TPR', 'POOL', 'BWA', 'KMX', 'LKQ', 'ETSY', 'RL', 'HAS', 'DECK',
    'LULU', 'NWL', 'WHR', 'MHK', 'LEG', 'PVH', 'VFC',
    # Communication Services (25+)
    'GOOGL', 'GOOG', 'META', 'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'TMUS', 'CHTR',
    'EA', 'WBD', 'TTWO', 'OMC', 'IPG', 'LYV', 'MTCH', 'FOXA', 'FOX', 'NWS',
    'NWSA', 'DISH', 'LUMN', 'PARAA', 'ATVI',
    # Industrials (75+)
    'GE', 'CAT', 'RTX', 'HON', 'UNP', 'UPS', 'BA', 'DE', 'LMT', 'ADP',
    'ETN', 'ITW', 'EMR', 'GD', 'NOC', 'FDX', 'WM', 'CSX', 'NSC', 'MMM',
    'PH', 'CTAS', 'TT', 'PCAR', 'RSG', 'JCI', 'CARR', 'OTIS', 'AME', 'CMI',
    'ROK', 'FAST', 'PAYX', 'VRSK', 'CPRT', 'ODFL', 'GWW', 'EFX', 'IR', 'XYL',
    'DOV', 'SWK', 'NDSN', 'TDG', 'HWM', 'IEX', 'WAB', 'PWR', 'HUBB', 'J',
    'MAS', 'LII', 'SNA', 'PNR', 'AOS', 'ALLE', 'CHRW', 'EXPD', 'JBHT', 'DAL',
    'UAL', 'LUV', 'AAL', 'ALK', 'LDOS', 'BAH', 'AXON', 'HII', 'TXT', 'HEI',
    'BLDR', 'URI', 'GNRC',
    # Consumer Staples (40+)
    'PG', 'KO', 'PEP', 'COST', 'WMT', 'PM', 'MO', 'MDLZ', 'CL', 'KMB',
    'GIS', 'K', 'HSY', 'STZ', 'KHC', 'SYY', 'KR', 'ADM', 'EL', 'CHD',
    'KDP', 'MNST', 'WBA', 'CLX', 'MKC', 'TSN', 'HRL', 'SJM', 'CAG', 'CPB',
    'TAP', 'BG', 'LW', 'BF-B', 'CASY',
    # Energy (25+)
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'WMB',
    'KMI', 'HAL', 'DVN', 'FANG', 'HES', 'BKR', 'TRGP', 'OKE', 'CTRA', 'APA',
    'MRO', 'EQT', 'PR',
    # Utilities (30+)
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE', 'EXC', 'XEL', 'ED', 'WEC',
    'PEG', 'CEG', 'AWK', 'DTE', 'ETR', 'FE', 'PPL', 'ES', 'AEE', 'CMS',
    'CNP', 'EVRG', 'ATO', 'NI', 'LNT', 'NRG', 'PNW',
    # Real Estate (30+)
    'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'O', 'WELL', 'SPG', 'DLR', 'AVB',
    'VICI', 'SBAC', 'EQR', 'WY', 'ARE', 'VTR', 'IRM', 'EXR', 'MAA', 'ESS',
    'INVH', 'SUI', 'REG', 'UDR', 'CPT', 'HST', 'KIM', 'BXP', 'DOC', 'FRT',
    # Materials (30+)
    'LIN', 'APD', 'SHW', 'ECL', 'FCX', 'NEM', 'NUE', 'VMC', 'MLM', 'DOW',
    'DD', 'PPG', 'CTVA', 'IP', 'CE', 'ALB', 'EMN', 'IFF', 'FMC', 'CF',
    'MOS', 'PKG', 'AVY', 'SEE', 'BALL', 'AMCR', 'WRK',
]

# Historical A/D data for McClellan Oscillator
_ad_history = []


def get_breadth_universe() -> list:
    """
    Get tickers for breadth calculation.
    Uses dynamic universe manager if available, falls back to hardcoded.
    """
    if HAS_UNIVERSE_MANAGER:
        try:
            um = get_universe_manager()
            universe = um.get_breadth_universe()
            if universe and len(universe) >= 100:
                logger.info(f"Using dynamic breadth universe: {len(universe)} tickers")
                return universe
        except Exception as e:
            logger.warning(f"Universe manager failed for breadth: {e}")

    # Fallback to hardcoded
    return BREADTH_UNIVERSE


def get_stock_data(ticker, period='3mo'):
    """
    Fetch stock data with error handling.
    Uses Polygon.io as primary, yfinance as fallback.
    """
    import os

    # Convert period to days
    period_days = {'1mo': 30, '3mo': 90, '6mo': 180, '1y': 365, '5d': 5, '1d': 1}
    days = period_days.get(period, 90)

    # Try Polygon first
    polygon_key = os.environ.get('POLYGON_API_KEY', '')
    if polygon_key:
        try:
            from src.data.polygon_provider import get_price_data_sync
            df = get_price_data_sync(ticker, days=days)
            if df is not None and len(df) > 0:
                df = normalize_dataframe_columns(df)
                return ticker, df
        except Exception as e:
            logger.debug(f"Polygon fetch failed for {ticker}: {e}")

    # Fallback to yfinance
    try:
        df = yf.download(ticker, period=period, progress=False)
        df = normalize_dataframe_columns(df)
        return ticker, df
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        return ticker, None


def safe_get_series(df, column, ticker=None):
    """Safely extract a column from yfinance dataframe."""
    if df is None:
        return None
    if not hasattr(df, 'columns'):
        return None
    if len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        try:
            result = df[column][ticker] if ticker else df[column].iloc[:, 0]
            if isinstance(result, pd.DataFrame):
                result = result.iloc[:, 0]
            return result
        except Exception as e:
            logger.error(f"Error extracting {column} for {ticker}: {e}")
            pass
    if column in df.columns:
        return df[column]
    return None


def get_last_close(df, ticker=None):
    """Get the last closing price from a yfinance dataframe."""
    if df is None:
        return None
    if not hasattr(df, 'columns'):
        return None
    if len(df) == 0:
        return None
    try:
        if isinstance(df.columns, pd.MultiIndex):
            if ('Close', ticker) in df.columns:
                val = df[('Close', ticker)].iloc[-1]
                return float(val) if not pd.isna(val) else None
            if 'Close' in df.columns.get_level_values(0):
                close_df = df['Close']
                if isinstance(close_df, pd.DataFrame):
                    if ticker and ticker in close_df.columns:
                        val = close_df[ticker].iloc[-1]
                    else:
                        val = close_df.iloc[-1, 0]
                else:
                    val = close_df.iloc[-1]
                return float(val) if not pd.isna(val) else None
        if 'Close' in df.columns:
            val = df['Close'].iloc[-1]
            return float(val) if not pd.isna(val) else None
    except Exception as e:
        logger.error(f"Error getting last close: {e}")
    return None


def get_real_put_call_ratio():
    """
    Get Put/Call ratio estimate based on VIX.

    Note: ^PCALL and ^CPCE symbols are no longer available on Yahoo Finance.
    We use VIX-based estimation instead.
    """
    try:
        # Use VIX to estimate put/call ratio
        # Higher VIX = more puts = higher P/C ratio
        vix = yf.download('^VIX', period='5d', progress=False)
        if vix is not None and len(vix) > 0:
            vix_val = get_last_close(vix, '^VIX')
            if vix_val:
                # Estimate P/C ratio from VIX
                # VIX 12 -> P/C ~0.7, VIX 20 -> P/C ~0.9, VIX 30 -> P/C ~1.1
                estimated_pcr = 0.5 + (vix_val / 50)
                return round(estimated_pcr, 2), 'VIX_ESTIMATE'
    except Exception as e:
        logger.error(f"Error estimating put/call ratio from VIX: {e}")

    return None, None


def get_nyse_highs_lows():
    """
    Get NYSE New Highs and New Lows data.
    Returns (new_highs, new_lows) or (None, None) if unavailable.

    Note: ^HIGN and ^LOWN may not be available on Yahoo Finance.
    Returns None if data unavailable.
    """
    try:
        # NYSE New Highs
        highs = yf.download('^HIGN', period='5d', progress=False)
        lows = yf.download('^LOWN', period='5d', progress=False)

        # Check if we got valid DataFrames
        if highs is None or not hasattr(highs, 'columns') or len(highs) == 0:
            return None, None
        if lows is None or not hasattr(lows, 'columns') or len(lows) == 0:
            return None, None

        nh = get_last_close(highs, '^HIGN')
        nl = get_last_close(lows, '^LOWN')

        if nh is not None and nl is not None:
            return int(nh), int(nl)
    except Exception as e:
        logger.debug(f"NYSE highs/lows not available: {e}")

    return None, None


def calculate_mcclellan_oscillator(advances, declines):
    """
    Calculate McClellan Oscillator from advance/decline data.

    McClellan = 19-day EMA of (Advances - Declines) - 39-day EMA of (Advances - Declines)

    Returns oscillator value and signal.
    """
    global _ad_history

    # Add today's data
    ad_diff = advances - declines
    _ad_history.append(ad_diff)

    # Keep last 50 days
    if len(_ad_history) > 50:
        _ad_history = _ad_history[-50:]

    if len(_ad_history) < 20:
        # Not enough history, return neutral
        return 0, 'Neutral'

    # Calculate EMAs
    ad_series = pd.Series(_ad_history)
    ema_19 = ad_series.ewm(span=19, adjust=False).mean().iloc[-1]
    ema_39 = ad_series.ewm(span=39, adjust=False).mean().iloc[-1]

    oscillator = ema_19 - ema_39

    # Signal interpretation
    if oscillator > 50:
        signal = 'Strongly Bullish'
    elif oscillator > 0:
        signal = 'Bullish'
    elif oscillator > -50:
        signal = 'Bearish'
    else:
        signal = 'Strongly Bearish'

    return round(oscillator, 1), signal


def calculate_market_breadth():
    """
    Calculate comprehensive market breadth indicators.

    Enhanced with:
    - Larger stock universe (200 stocks)
    - Real NYSE highs/lows when available
    - McClellan Oscillator
    - Price strength indicator
    """
    results = {
        'above_20sma': 0,
        'above_50sma': 0,
        'above_200sma': 0,
        'advancing': 0,
        'declining': 0,
        'unchanged': 0,
        'advance_decline_ratio': 1.0,
        'new_highs': 0,
        'new_lows': 0,
        'nyse_highs': None,
        'nyse_lows': None,
        'mcclellan_oscillator': 0,
        'mcclellan_signal': 'Neutral',
        'price_strength': 0,  # % at 50-day high
        'breadth_score': 50,
        'stocks_analyzed': 0
    }

    stocks_data = []

    # Get dynamic or hardcoded universe
    breadth_tickers = get_breadth_universe()

    # Parallel fetch with 50 workers for full universe
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(get_stock_data, t, '1y'): t for t in breadth_tickers}

        for future in as_completed(futures):
            ticker, df = future.result()
            if df is not None and len(df) >= 50:
                stocks_data.append((ticker, df))

    if not stocks_data:
        return results

    above_20 = 0
    above_50 = 0
    above_200 = 0
    advancing = 0
    declining = 0
    new_highs = 0
    new_lows = 0
    at_50day_high = 0  # Price strength

    for ticker, df in stocks_data:
        try:
            close = df['Close']
            current = float(close.iloc[-1])
            prev_close = float(close.iloc[-2])

            # SMA calculations
            sma_20 = float(close.rolling(20).mean().iloc[-1])
            sma_50 = float(close.rolling(50).mean().iloc[-1])
            sma_200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else sma_50

            if current > sma_20:
                above_20 += 1
            if current > sma_50:
                above_50 += 1
            if current > sma_200:
                above_200 += 1

            # Advance/Decline
            if current > prev_close * 1.001:
                advancing += 1
            elif current < prev_close * 0.999:
                declining += 1

            # 52-week high/low
            high_52w = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
            low_52w = float(close.tail(252).min()) if len(close) >= 252 else float(close.min())

            if current >= high_52w * 0.98:
                new_highs += 1
            if current <= low_52w * 1.02:
                new_lows += 1

            # Price Strength: at 50-day high
            high_50d = float(close.tail(50).max())
            if current >= high_50d * 0.98:
                at_50day_high += 1

        except Exception as e:
            logger.error(f"Error processing stock data for {ticker}: {e}")
            continue

    total = len(stocks_data)

    results['stocks_analyzed'] = total
    results['above_20sma'] = round(above_20 / total * 100, 1) if total > 0 else 0
    results['above_50sma'] = round(above_50 / total * 100, 1) if total > 0 else 0
    results['above_200sma'] = round(above_200 / total * 100, 1) if total > 0 else 0
    results['advancing'] = advancing
    results['declining'] = declining
    results['unchanged'] = total - advancing - declining
    results['advance_decline_ratio'] = round(advancing / declining, 2) if declining > 0 else 10.0
    results['new_highs'] = new_highs
    results['new_lows'] = new_lows
    results['price_strength'] = round(at_50day_high / total * 100, 1) if total > 0 else 0

    # Try to get real NYSE highs/lows
    nyse_h, nyse_l = get_nyse_highs_lows()
    if nyse_h is not None:
        results['nyse_highs'] = nyse_h
        results['nyse_lows'] = nyse_l

    # Calculate McClellan Oscillator
    mcclellan, mcc_signal = calculate_mcclellan_oscillator(advancing, declining)
    results['mcclellan_oscillator'] = mcclellan
    results['mcclellan_signal'] = mcc_signal

    # Calculate breadth score (0-100) - Enhanced formula
    breadth_score = 0
    breadth_score += results['above_50sma'] * 0.25  # 25% weight
    breadth_score += results['above_200sma'] * 0.20  # 20% weight
    breadth_score += min(results['advance_decline_ratio'] * 10, 20)  # 20% weight, capped
    breadth_score += (new_highs / (new_highs + new_lows + 1)) * 20  # 20% weight
    breadth_score += results['price_strength'] * 0.15  # 15% weight - new

    # McClellan contribution (normalized to 0-10 scale)
    mcc_contrib = min(max((mcclellan + 100) / 20, 0), 10)  # -100 to 100 -> 0 to 10
    breadth_score += mcc_contrib  # ~10% effective weight

    results['breadth_score'] = round(min(max(breadth_score, 0), 100), 1)

    return results


def calculate_fear_greed_index():
    """
    Calculate Fear & Greed Index (0-100) with enhanced data sources.

    Components:
    1. VIX Level (20%) - Lower VIX = More Greed
    2. Market Momentum (20%) - SPY vs 125-day MA
    3. Put/Call Ratio (15%) - Real CBOE data when available
    4. Safe Haven Demand (15%) - Stocks vs Bonds performance
    5. Junk Bond Demand (10%) - HYG vs LQD spread
    6. Market Volatility (10%) - Recent ATR of SPY
    7. Stock Price Strength (10%) - % at 50-day highs
    """
    components = {}

    try:
        # 1. VIX Level (20%)
        try:
            vix = yf.download('^VIX', period='5d', progress=False)
            vix_current = get_last_close(vix, '^VIX')
            if vix_current is None:
                raise ValueError("No VIX data")

            if vix_current <= 15:
                vix_score = 100
            elif vix_current >= 30:
                vix_score = 0
            else:
                vix_score = 100 - ((vix_current - 15) / 15 * 100)

            vix_score = max(0, min(100, vix_score))

            components['vix'] = {
                'value': round(vix_current, 1),
                'score': round(vix_score, 1),
                'weight': 0.20,
                'label': f'VIX ({vix_current:.1f})'
            }
        except Exception as e:
            components['vix'] = {'value': 20, 'score': 50, 'weight': 0.20, 'label': 'VIX Level'}

        # 2. Market Momentum (20%) - SPY vs 125-day MA
        try:
            spy, _ = get_spy_data_cached(period='6mo')
            spy_close = safe_get_series(spy, 'Close', 'SPY')
            if spy_close is None or len(spy_close) < 125:
                raise ValueError("Not enough SPY data")

            current_spy = safe_float(spy_close.iloc[-1])
            ma_125 = safe_float(spy_close.rolling(125).mean().iloc[-1])

            momentum_pct = (current_spy - ma_125) / ma_125 * 100

            if momentum_pct >= 8:
                momentum_score = 100
            elif momentum_pct <= -8:
                momentum_score = 0
            else:
                momentum_score = 50 + (momentum_pct / 8 * 50)

            components['momentum'] = {
                'value': round(momentum_pct, 1),
                'score': round(momentum_score, 1),
                'weight': 0.20,
                'label': f'Momentum ({momentum_pct:+.1f}%)'
            }
        except Exception as e:
            logger.error(f"Error calculating market momentum: {e}")
            components['momentum'] = {'value': 0, 'score': 50, 'weight': 0.20, 'label': 'Market Momentum'}

        # 3. Put/Call Ratio (15%) - Real data when available
        try:
            pc_ratio, pc_source = get_real_put_call_ratio()

            if pc_ratio is not None:
                # Real P/C ratio: <0.7 = greed, >1.0 = fear
                if pc_ratio <= 0.7:
                    pc_score = 100
                elif pc_ratio >= 1.0:
                    pc_score = 0
                else:
                    pc_score = 100 - ((pc_ratio - 0.7) / 0.3 * 100)

                components['put_call'] = {
                    'value': round(pc_ratio, 2),
                    'score': round(pc_score, 1),
                    'weight': 0.15,
                    'label': f'Put/Call ({pc_ratio:.2f})'
                }
            else:
                # Fallback to VIX-based estimate
                vix_close_series = safe_get_series(vix, 'Close', '^VIX')
                if vix_close_series is None or len(vix_close_series) < 3:
                    raise ValueError("Not enough VIX data")
                vix_ma = safe_float(vix_close_series.rolling(3, min_periods=2).mean().iloc[-1])
                if vix_ma is None or vix_ma == 0:
                    raise ValueError("Invalid VIX MA")
                pc_proxy = vix_current / vix_ma

                if pc_proxy <= 0.85:
                    pc_score = 100
                elif pc_proxy >= 1.15:
                    pc_score = 0
                else:
                    pc_score = 100 - ((pc_proxy - 0.85) / 0.3 * 100)

                components['put_call'] = {
                    'value': round(pc_proxy, 2),
                    'score': round(pc_score, 1),
                    'weight': 0.15,
                    'label': f'P/C Est ({pc_proxy:.2f})'
                }
        except Exception as e:
            logger.error(f"Error calculating put/call ratio: {e}")
            components['put_call'] = {'value': 1.0, 'score': 50, 'weight': 0.15, 'label': 'Put/Call Ratio'}

        # 4. Safe Haven Demand (15%) - SPY vs TLT (bonds)
        try:
            tlt = yf.download('TLT', period='1mo', progress=False)
            tlt_close = safe_get_series(tlt, 'Close', 'TLT')
            if tlt_close is None or len(tlt_close) < 10:
                raise ValueError("Not enough TLT data")

            spy_ret = (safe_float(spy_close.iloc[-1]) / safe_float(spy_close.iloc[-10]) - 1) * 100
            tlt_ret = (safe_float(tlt_close.iloc[-1]) / safe_float(tlt_close.iloc[-10]) - 1) * 100

            safe_haven_diff = spy_ret - tlt_ret

            if safe_haven_diff >= 3:
                sh_score = 100
            elif safe_haven_diff <= -3:
                sh_score = 0
            else:
                sh_score = 50 + (safe_haven_diff / 3 * 50)

            sh_score = max(0, min(100, sh_score))

            components['safe_haven'] = {
                'value': round(safe_haven_diff, 1),
                'score': round(sh_score, 1),
                'weight': 0.15,
                'label': f'Safe Haven ({safe_haven_diff:+.1f}%)'
            }
        except Exception as e:
            components['safe_haven'] = {'value': 0, 'score': 50, 'weight': 0.15, 'label': 'Safe Haven'}

        # 5. Junk Bond Demand (10%) - HYG vs LQD
        try:
            hyg = yf.download('HYG', period='1mo', progress=False)
            lqd = yf.download('LQD', period='1mo', progress=False)

            hyg_close = safe_get_series(hyg, 'Close', 'HYG')
            lqd_close = safe_get_series(lqd, 'Close', 'LQD')
            if hyg_close is None or lqd_close is None or len(hyg_close) < 10 or len(lqd_close) < 10:
                raise ValueError("Not enough HYG/LQD data")

            hyg_ret = (safe_float(hyg_close.iloc[-1]) / safe_float(hyg_close.iloc[-10]) - 1) * 100
            lqd_ret = (safe_float(lqd_close.iloc[-1]) / safe_float(lqd_close.iloc[-10]) - 1) * 100

            junk_diff = hyg_ret - lqd_ret

            if junk_diff >= 1.5:
                junk_score = 100
            elif junk_diff <= -1.5:
                junk_score = 0
            else:
                junk_score = 50 + (junk_diff / 1.5 * 50)

            junk_score = max(0, min(100, junk_score))

            components['junk_bond'] = {
                'value': round(junk_diff, 1),
                'score': round(junk_score, 1),
                'weight': 0.10,
                'label': f'Junk Bonds ({junk_diff:+.1f}%)'
            }
        except Exception as e:
            components['junk_bond'] = {'value': 0, 'score': 50, 'weight': 0.10, 'label': 'Junk Bonds'}

        # 6. Market Volatility (10%) - SPY ATR
        try:
            high = safe_get_series(spy, 'High', 'SPY')
            low = safe_get_series(spy, 'Low', 'SPY')
            close = safe_get_series(spy, 'Close', 'SPY')

            if high is None or low is None or close is None:
                raise ValueError("Missing SPY OHLC data")

            tr = pd.concat([
                high - low,
                abs(high - close.shift(1)),
                abs(low - close.shift(1))
            ], axis=1).max(axis=1)

            atr_14 = float(tr.rolling(14).mean().iloc[-1])
            atr_pct = atr_14 / safe_float(close.iloc[-1]) * 100

            if atr_pct <= 0.7:
                vol_score = 100
            elif atr_pct >= 2.0:
                vol_score = 0
            else:
                vol_score = 100 - ((atr_pct - 0.7) / 1.3 * 100)

            vol_score = max(0, min(100, vol_score))

            components['volatility'] = {
                'value': round(atr_pct, 2),
                'score': round(vol_score, 1),
                'weight': 0.10,
                'label': f'Volatility ({atr_pct:.1f}%)'
            }
        except Exception as e:
            components['volatility'] = {'value': 1.5, 'score': 50, 'weight': 0.10, 'label': 'Volatility'}

        # 7. Stock Price Strength (10%) - % of stocks at 50-day highs
        try:
            # This will be calculated in breadth, use estimate based on momentum
            if components.get('momentum', {}).get('value', 0) > 0:
                strength_score = min(50 + components['momentum']['value'] * 5, 100)
            else:
                strength_score = max(50 + components['momentum'].get('value', 0) * 5, 0)

            components['strength'] = {
                'value': round(strength_score, 0),
                'score': round(strength_score, 1),
                'weight': 0.10,
                'label': f'Price Strength'
            }
        except Exception as e:
            logger.error(f"Error calculating price strength: {e}")
            components['strength'] = {'value': 50, 'score': 50, 'weight': 0.10, 'label': 'Price Strength'}

        # Calculate weighted score
        total_score = 0
        for comp in components.values():
            total_score += comp['score'] * comp['weight']

        total_score = round(min(max(total_score, 0), 100), 1)

        # Label
        if total_score >= 80:
            label = 'Extreme Greed'
            color = '#22c55e'
        elif total_score >= 60:
            label = 'Greed'
            color = '#84cc16'
        elif total_score >= 40:
            label = 'Neutral'
            color = '#eab308'
        elif total_score >= 20:
            label = 'Fear'
            color = '#f97316'
        else:
            label = 'Extreme Fear'
            color = '#ef4444'

        return {
            'score': total_score,
            'label': label,
            'color': color,
            'components': components,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        return {
            'score': 50,
            'label': 'Neutral',
            'color': '#eab308',
            'components': {},
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def get_market_health_lite():
    """
    Fast market health using only VIX (for free tier / quick responses).
    """
    try:
        vix = yf.download('^VIX', period='5d', progress=False)
        vix_val = get_last_close(vix, '^VIX')

        if vix_val is None:
            return {'score': 50, 'label': 'Neutral', 'color': '#eab308', 'lite': True}

        # VIX-based score: VIX 12 = 100 (greed), VIX 35 = 0 (fear)
        if vix_val <= 12:
            score = 100
        elif vix_val >= 35:
            score = 0
        else:
            score = 100 - ((vix_val - 12) / 23 * 100)

        score = round(max(0, min(100, score)), 1)

        if score >= 80:
            label, color = 'Extreme Greed', '#22c55e'
        elif score >= 60:
            label, color = 'Greed', '#84cc16'
        elif score >= 40:
            label, color = 'Neutral', '#eab308'
        elif score >= 20:
            label, color = 'Fear', '#f97316'
        else:
            label, color = 'Extreme Fear', '#ef4444'

        return {
            'score': score,
            'label': label,
            'color': color,
            'vix': round(vix_val, 1),
            'lite': True,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Lite health check error: {e}")
        return {'score': 50, 'label': 'Neutral', 'color': '#eab308', 'lite': True, 'error': str(e)}


def get_market_health():
    """
    Get complete market health data.

    Returns combined breadth and fear/greed data with enhanced indicators.
    """
    # Calculate fear_greed FIRST to avoid yfinance cache corruption
    fear_greed = calculate_fear_greed_index()
    breadth = calculate_market_breadth()

    # Update price strength in fear_greed with actual breadth data
    if 'strength' in fear_greed.get('components', {}):
        fear_greed['components']['strength']['value'] = breadth.get('price_strength', 50)
        fear_greed['components']['strength']['score'] = breadth.get('price_strength', 50)
        fear_greed['components']['strength']['label'] = f"Strength ({breadth.get('price_strength', 0):.0f}%)"

    # Overall health score (weighted average)
    overall = (breadth['breadth_score'] * 0.4 + fear_greed['score'] * 0.6)

    if overall >= 70:
        health_label = 'Bullish'
        health_color = '#22c55e'
    elif overall >= 50:
        health_label = 'Neutral-Bullish'
        health_color = '#84cc16'
    elif overall >= 30:
        health_label = 'Neutral-Bearish'
        health_color = '#f97316'
    else:
        health_label = 'Bearish'
        health_color = '#ef4444'

    return {
        'breadth': breadth,
        'fear_greed': fear_greed,
        'overall_score': round(overall, 1),
        'overall_label': health_label,
        'overall_color': health_color,
        'timestamp': datetime.now().isoformat()
    }


def format_health_report(health):
    """Format health data for Telegram."""
    fg = health['fear_greed']
    br = health['breadth']

    # Emoji for fear/greed
    if fg['score'] >= 80:
        fg_emoji = '🟢🟢'
    elif fg['score'] >= 60:
        fg_emoji = '🟢'
    elif fg['score'] >= 40:
        fg_emoji = '🟡'
    elif fg['score'] >= 20:
        fg_emoji = '🟠'
    else:
        fg_emoji = '🔴'

    msg = "📊 *MARKET HEALTH*\n\n"

    msg += f"*Fear & Greed:* {fg_emoji} {fg['score']:.0f} ({fg['label']})\n\n"

    msg += "*Components:*\n"
    for key, comp in fg.get('components', {}).items():
        score = comp['score']
        emoji = '🟢' if score >= 60 else ('🟡' if score >= 40 else '🔴')
        msg += f"  {emoji} {comp['label']}: {score:.0f}\n"

    msg += f"\n*Market Breadth:* {br['breadth_score']:.0f}/100\n"
    msg += f"  • Stocks Analyzed: {br['stocks_analyzed']}\n"
    msg += f"  • Above 50 SMA: {br['above_50sma']:.0f}%\n"
    msg += f"  • Above 200 SMA: {br['above_200sma']:.0f}%\n"
    msg += f"  • A/D Ratio: {br['advance_decline_ratio']:.2f}\n"

    # Show NYSE data if available
    if br.get('nyse_highs') is not None:
        msg += f"  • NYSE Highs/Lows: {br['nyse_highs']}/{br['nyse_lows']}\n"
    else:
        msg += f"  • New Highs/Lows: {br['new_highs']}/{br['new_lows']}\n"

    msg += f"  • Price Strength: {br['price_strength']:.0f}%\n"
    msg += f"  • McClellan: {br['mcclellan_oscillator']} ({br['mcclellan_signal']})\n"

    msg += f"\n*Overall:* {health['overall_label']} ({health['overall_score']:.0f}/100)"

    return msg


if __name__ == '__main__':
    logger.info("Calculating market health...")
    health = get_market_health()
    logger.info(format_health_report(health))
