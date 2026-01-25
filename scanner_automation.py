#!/usr/bin/env python3
"""
Automated Stock Scanner with Telegram Alerts

Runs daily to:
1. Fetch fresh data for S&P 500 + NASDAQ 100
2. Run composite scoring
3. Detect emerging themes and niche plays
4. Send alerts via Telegram

Set up as GitHub Action or local cron job.
"""

import io
import json
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from config import config
from utils import (
    get_logger, normalize_dataframe_columns, get_spy_data_cached,
    calculate_rs, safe_float, download_stock_data, send_message, send_photo,
    TelegramClient, DataFetchError,
)

logger = get_logger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

# Scoring weights (from config)
WEIGHTS = {
    'trend': config.scanner.weight_trend,
    'squeeze': config.scanner.weight_squeeze,
    'rs': config.scanner.weight_rs,
    'sentiment': config.scanner.weight_sentiment,
    'volume': config.scanner.weight_volume,
}

# Ticker lists (embedded for reliability)
SP500_TICKERS = [
    'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'ADI', 'ADM', 'ADP', 'ADSK', 'AEE',
    'AEP', 'AES', 'AFL', 'AIG', 'AIZ', 'AJG', 'AKAM', 'ALB', 'ALGN', 'ALL',
    'ALLE', 'AMAT', 'AMCR', 'AMD', 'AME', 'AMGN', 'AMP', 'AMT', 'AMZN', 'ANET',
    'AON', 'AOS', 'APA', 'APD', 'APH', 'APTV', 'ARE', 'ATO', 'AVB', 'AVGO',
    'AVY', 'AWK', 'AXON', 'AXP', 'AZO', 'BA', 'BAC', 'BALL', 'BAX', 'BBWI',
    'BBY', 'BDX', 'BEN', 'BG', 'BIIB', 'BIO', 'BK', 'BKNG', 'BKR', 'BLDR',
    'BLK', 'BMY', 'BR', 'BRO', 'BSX', 'BWA', 'BX', 'BXP', 'C', 'CAG', 'CAH',
    'CARR', 'CAT', 'CB', 'CBOE', 'CBRE', 'CCI', 'CCL', 'CDNS', 'CDW', 'CE',
    'CEG', 'CF', 'CFG', 'CHD', 'CHRW', 'CHTR', 'CI', 'CINF', 'CL', 'CLX',
    'CMCSA', 'CME', 'CMG', 'CMI', 'CMS', 'CNC', 'CNP', 'COF', 'COO', 'COP',
    'COR', 'COST', 'CPAY', 'CPB', 'CPRT', 'CPT', 'CRL', 'CRM', 'CRWD', 'CSCO',
    'CSGP', 'CSX', 'CTAS', 'CTRA', 'CTSH', 'CTVA', 'CVS', 'CVX', 'CZR', 'D',
    'DAL', 'DAY', 'DD', 'DE', 'DECK', 'DG', 'DGX', 'DHI', 'DHR', 'DIS', 'DLR',
    'DLTR', 'DOC', 'DOV', 'DOW', 'DPZ', 'DRI', 'DTE', 'DUK', 'DVA', 'DVN',
    'DXCM', 'EA', 'EBAY', 'ECL', 'ED', 'EFX', 'EG', 'EIX', 'EL', 'ELV', 'EMN',
    'EMR', 'ENPH', 'EOG', 'EPAM', 'EQIX', 'EQR', 'EQT', 'ES', 'ESS', 'ETN',
    'ETR', 'ETSY', 'EVRG', 'EW', 'EXC', 'EXPD', 'EXPE', 'EXR', 'F', 'FANG',
    'FAST', 'FCX', 'FDS', 'FDX', 'FE', 'FFIV', 'FICO', 'FIS', 'FITB', 'FMC',
    'FOX', 'FOXA', 'FRT', 'FSLR', 'FTNT', 'FTV', 'GD', 'GDDY', 'GE', 'GEHC',
    'GEN', 'GEV', 'GILD', 'GIS', 'GL', 'GLW', 'GM', 'GNRC', 'GOOG', 'GOOGL',
    'GPC', 'GPN', 'GRMN', 'GS', 'GWW', 'HAL', 'HAS', 'HBAN', 'HCA', 'HD',
    'HIG', 'HII', 'HLT', 'HOLX', 'HON', 'HPE', 'HPQ', 'HRL', 'HSIC', 'HST',
    'HSY', 'HUBB', 'HUM', 'HWM', 'IBM', 'ICE', 'IDXX', 'IEX', 'IFF', 'ILMN',
    'INCY', 'INTC', 'INTU', 'INVH', 'IP', 'IPG', 'IQV', 'IR', 'IRM', 'ISRG',
    'IT', 'ITW', 'IVZ', 'J', 'JBHT', 'JBL', 'JCI', 'JKHY', 'JNJ', 'JPM', 'K',
    'KDP', 'KEY', 'KEYS', 'KHC', 'KIM', 'KLAC', 'KMB', 'KMI', 'KMX', 'KO',
    'KR', 'KVUE', 'L', 'LDOS', 'LEN', 'LH', 'LHX', 'LIN', 'LKQ', 'LLY', 'LMT',
    'LNT', 'LOW', 'LRCX', 'LULU', 'LUV', 'LVS', 'LW', 'LYB', 'LYV', 'MA',
    'MAA', 'MAR', 'MAS', 'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ', 'MDT', 'MET',
    'META', 'MGM', 'MHK', 'MKC', 'MKTX', 'MLM', 'MMC', 'MMM', 'MNST', 'MO',
    'MOH', 'MOS', 'MPC', 'MPWR', 'MRK', 'MRNA', 'MS', 'MSCI', 'MSFT', 'MSI',
    'MTB', 'MTCH', 'MTD', 'MU', 'NCLH', 'NDAQ', 'NDSN', 'NEE', 'NEM', 'NFLX',
    'NI', 'NKE', 'NOC', 'NOW', 'NRG', 'NSC', 'NTAP', 'NTRS', 'NUE', 'NVDA',
    'NVR', 'NWS', 'NWSA', 'NXPI', 'O', 'ODFL', 'OKE', 'OMC', 'ON', 'ORCL',
    'ORLY', 'OTIS', 'OXY', 'PANW', 'PAYC', 'PAYX', 'PCAR', 'PCG', 'PEG', 'PEP',
    'PFE', 'PFG', 'PG', 'PGR', 'PH', 'PHM', 'PKG', 'PLD', 'PM', 'PNC', 'PNR',
    'PNW', 'PODD', 'POOL', 'PPG', 'PPL', 'PRU', 'PSA', 'PSX', 'PTC', 'PWR',
    'PYPL', 'QCOM', 'QRVO', 'RCL', 'REG', 'REGN', 'RF', 'RJF', 'RL', 'RMD',
    'ROK', 'ROL', 'ROP', 'ROST', 'RSG', 'RTX', 'RVTY', 'SBAC', 'SBUX', 'SCHW',
    'SHW', 'SJM', 'SLB', 'SMCI', 'SNA', 'SNPS', 'SO', 'SOLV', 'SPG', 'SPGI',
    'SRE', 'STE', 'STLD', 'STT', 'STX', 'STZ', 'SWK', 'SWKS', 'SYF', 'SYK',
    'SYY', 'T', 'TAP', 'TDG', 'TDY', 'TECH', 'TEL', 'TER', 'TFC', 'TFX', 'TGT',
    'TJX', 'TMO', 'TMUS', 'TPR', 'TRGP', 'TRMB', 'TROW', 'TRV', 'TSCO', 'TSLA',
    'TSN', 'TT', 'TTWO', 'TXN', 'TXT', 'TYL', 'UAL', 'UBER', 'UDR', 'UHS',
    'ULTA', 'UNH', 'UNP', 'UPS', 'URI', 'USB', 'V', 'VFC', 'VICI', 'VLO',
    'VLTO', 'VMC', 'VRSK', 'VRSN', 'VRTX', 'VST', 'VTR', 'VTRS', 'VZ', 'WAB',
    'WAT', 'WBD', 'WDC', 'WEC', 'WELL', 'WFC', 'WM', 'WMB', 'WMT', 'WRB', 'WST',
    'WTW', 'WY', 'WYNN', 'XEL', 'XOM', 'XYL', 'YUM', 'ZBH', 'ZBRA', 'ZTS'
]

NASDAQ100_TICKERS = [
    'AAPL', 'ABNB', 'ADBE', 'ADI', 'ADP', 'ADSK', 'AEP', 'AMAT', 'AMD', 'AMGN',
    'AMZN', 'ARM', 'ASML', 'AVGO', 'AZN', 'BIIB', 'BKNG', 'BKR', 'CDNS', 'CDW',
    'CEG', 'CHTR', 'CMCSA', 'COST', 'CPRT', 'CRWD', 'CSCO', 'CSGP', 'CSX', 'CTAS',
    'CTSH', 'DASH', 'DDOG', 'DLTR', 'DXCM', 'EA', 'EXC', 'FANG', 'FAST', 'FTNT',
    'GEHC', 'GFS', 'GILD', 'GOOG', 'GOOGL', 'HON', 'IDXX', 'ILMN', 'INTC', 'INTU',
    'ISRG', 'KDP', 'KHC', 'KLAC', 'LRCX', 'LULU', 'MAR', 'MCHP', 'MDB', 'MDLZ',
    'MELI', 'META', 'MNST', 'MRNA', 'MRVL', 'MSFT', 'MU', 'NFLX', 'NVDA', 'NXPI',
    'ODFL', 'ON', 'ORLY', 'PANW', 'PAYX', 'PCAR', 'PDD', 'PEP', 'PYPL', 'QCOM',
    'REGN', 'ROP', 'ROST', 'SBUX', 'SMCI', 'SNPS', 'TEAM', 'TMUS', 'TSLA', 'TTD',
    'TTWO', 'TXN', 'VRSK', 'VRTX', 'WBD', 'WDAY', 'XEL', 'ZS'
]


# ============================================================
# TELEGRAM FUNCTIONS
# ============================================================

def send_telegram_message(message, parse_mode='Markdown'):
    """Send message via Telegram bot using centralized client."""
    if not config.telegram.is_configured:
        logger.info("Telegram not configured. Printing to console:")
        logger.info(message)
        return False

    try:
        return send_message(config.telegram.chat_id, message, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return False


def format_alert_message(alert_type, data):
    """Format alert message for Telegram."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    if alert_type == 'DAILY_SUMMARY':
        msg = f"📊 *DAILY SCAN SUMMARY*\n_{timestamp}_\n\n"

        # Top stocks
        msg += "*🏆 TOP 5 STOCKS:*\n"
        for stock in data.get('top_stocks', [])[:5]:
            msg += f"• `{stock['ticker']}` | Score: {stock['score']:.0f} | RS: {stock['rs']:+.1f}%\n"

        # Sectors
        msg += "\n*📈 STRONGEST SECTORS:*\n"
        for sector in data.get('top_sectors', [])[:3]:
            msg += f"• {sector['name']} | RS: {sector['rs']:+.1f}%\n"

        # Breakouts
        breakouts = data.get('breakouts', [])
        if breakouts:
            msg += f"\n*🚀 BREAKOUTS ({len(breakouts)}):*\n"
            for b in breakouts[:5]:
                msg += f"• `{b['ticker']}` | Score: {b['score']:.0f}\n"

        # Squeezes
        squeezes = data.get('squeezes', [])
        if squeezes:
            msg += f"\n*⏳ IN SQUEEZE ({len(squeezes)}):*\n"
            for s in squeezes[:5]:
                msg += f"• `{s['ticker']}` | Score: {s['score']:.0f}\n"

        return msg

    elif alert_type == 'NEW_BREAKOUT':
        msg = f"🚀 *NEW BREAKOUT*\n\n"
        msg += f"*{data['ticker']}* ({data['sector']})\n"
        msg += f"Price: ${data['price']:.2f}\n"
        msg += f"Score: {data['score']:.0f} | RS: {data['rs']:+.1f}%\n"
        msg += f"Volume: {data['volume']:.1f}x avg"
        return msg

    elif alert_type == 'THEME_ALERT':
        msg = f"🎯 *EMERGING THEME*\n\n"
        msg += f"*{data['theme']}*\n"
        msg += f"{data['description']}\n\n"
        msg += f"Leader: `{data['leader']}` (Score: {data['leader_score']:.0f})\n"
        msg += f"Laggards: {', '.join(data['laggards'][:3])}"
        return msg

    elif alert_type == 'VOLUME_SURGE':
        msg = f"📢 *VOLUME SURGE*\n\n"
        msg += f"*{data['ticker']}* ({data['sector']})\n"
        msg += f"Volume: {data['volume']:.1f}x average\n"
        msg += f"RS: {data['rs']:+.1f}%"
        return msg

    return str(data)


# ============================================================
# SCANNER FUNCTIONS (simplified for automation)
# ============================================================

def get_ticker_df(data, ticker):
    """Extract single ticker dataframe."""
    try:
        if isinstance(data.columns, pd.MultiIndex):
            df = data[ticker].copy()
        else:
            df = data.copy()
        df = normalize_dataframe_columns(df)
        return df.dropna()
    except Exception as e:
        logger.debug(f"Failed to extract ticker {ticker}: {e}")
        return None


def calculate_indicators(df):
    """Calculate all technical indicators for a ticker."""
    if df is None or len(df) < 200:
        return None

    close = df['Close']
    volume = df['Volume']

    # MAs
    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()

    current_price = close.iloc[-1]

    # Trend
    above_20 = current_price > sma_20.iloc[-1]
    above_50 = current_price > sma_50.iloc[-1]
    above_200 = current_price > sma_200.iloc[-1]
    ma_aligned = sma_20.iloc[-1] > sma_50.iloc[-1] > sma_200.iloc[-1]
    trend_score = sum([above_20, above_50, above_200, ma_aligned])

    # Bollinger Bands / Squeeze
    bb_sma = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    upper_band = bb_sma + 2 * bb_std
    lower_band = bb_sma - 2 * bb_std
    bb_width = (upper_band - lower_band) / bb_sma

    current_width = bb_width.iloc[-1]
    width_pct = (bb_width.iloc[-100:] <= current_width).mean() * 100
    in_squeeze = width_pct <= 20
    breakout_up = current_price > upper_band.iloc[-1]

    squeeze_score = 0
    if in_squeeze:
        squeeze_score += 1
    if breakout_up:
        squeeze_score += 2

    # Volume
    avg_vol = volume.iloc[-20:].mean()
    vol_ratio = volume.iloc[-1] / avg_vol if avg_vol > 0 else 1

    volume_score = 0
    if vol_ratio > 1.2:
        volume_score += 1
    if vol_ratio > 1.5:
        volume_score += 1
    if vol_ratio > 2.0:
        volume_score += 1

    return {
        'price': current_price,
        'above_20': above_20,
        'above_50': above_50,
        'above_200': above_200,
        'ma_aligned': ma_aligned,
        'trend_score': trend_score,
        'in_squeeze': in_squeeze,
        'breakout_up': breakout_up,
        'squeeze_score': squeeze_score,
        'vol_ratio': vol_ratio,
        'volume_score': min(volume_score, 3),
    }


def calculate_rs_local(df, spy_returns):
    """Calculate relative strength vs SPY using centralized utility.

    This is a wrapper around the imported calculate_rs function
    for backward compatibility with existing code.
    """
    # Use the centralized calculate_rs from utils
    return calculate_rs(df, spy_returns)


def get_sector(ticker):
    """Get sector for ticker using yfinance."""
    try:
        return yf.Ticker(ticker).info.get('sector', 'Unknown')
    except Exception as e:
        logger.debug(f"Failed to get sector for {ticker}: {e}")
        return 'Unknown'


def run_scan():
    """Run the full scan."""
    logger.info(f"Starting scan at {datetime.now()}")

    # Get unique tickers
    all_tickers = list(set(SP500_TICKERS + NASDAQ100_TICKERS))
    logger.info(f"Scanning {len(all_tickers)} tickers...")

    # Fetch data
    logger.info("Fetching price data...")
    price_data = yf.download(all_tickers + ['SPY'], period='1y', group_by='ticker', progress=False)

    # Get SPY data using cached utility
    spy_df, spy_returns = get_spy_data_cached(period='1y', force_refresh=True)

    # Scan each ticker
    results = []
    sector_cache = {}

    for ticker in all_tickers:
        df = get_ticker_df(price_data, ticker)
        if df is None:
            continue

        indicators = calculate_indicators(df)
        if indicators is None:
            continue

        # Use the imported calculate_rs with spy_returns
        rs = calculate_rs(df, spy_returns)

        # Get sector (with caching)
        if ticker not in sector_cache:
            sector_cache[ticker] = get_sector(ticker)

        result = {
            'ticker': ticker,
            'sector': sector_cache[ticker],
            **indicators,
            **rs,
            'sentiment_score': 1,  # Placeholder
        }

        # Calculate composite score
        trend_norm = (result['trend_score'] / 4) * 100
        squeeze_norm = (result['squeeze_score'] / 3) * 100
        rs_norm = (result['rs_score'] / 3) * 100
        vol_norm = (result['volume_score'] / 3) * 100
        sent_norm = (result['sentiment_score'] / 3) * 100

        result['composite_score'] = (
            trend_norm * WEIGHTS['trend'] +
            squeeze_norm * WEIGHTS['squeeze'] +
            rs_norm * WEIGHTS['rs'] +
            vol_norm * WEIGHTS['volume'] +
            sent_norm * WEIGHTS['sentiment']
        )

        results.append(result)

    df_results = pd.DataFrame(results)
    df_results['rank'] = df_results['composite_score'].rank(ascending=False).astype(int)
    df_results = df_results.sort_values('composite_score', ascending=False)

    logger.info(f"Scan complete. {len(df_results)} tickers analyzed.")

    return df_results, price_data


def detect_alerts(df_results, previous_results=None):
    """Detect alert-worthy conditions."""
    alerts = []

    # New breakouts (high score + breakout flag)
    breakouts = df_results[
        (df_results['composite_score'] >= config.scanner.min_composite_score) &
        (df_results['breakout_up'] == True)
    ]

    for _, row in breakouts.iterrows():
        alerts.append({
            'type': 'NEW_BREAKOUT',
            'ticker': row['ticker'],
            'sector': row['sector'],
            'price': row['price'],
            'score': row['composite_score'],
            'rs': row['rs_composite'],
            'volume': row['vol_ratio'],
        })

    # Volume surges
    vol_surges = df_results[
        (df_results['vol_ratio'] >= config.scanner.volume_spike_threshold) &
        (df_results['rs_composite'] > 0)
    ]

    for _, row in vol_surges.iterrows():
        alerts.append({
            'type': 'VOLUME_SURGE',
            'ticker': row['ticker'],
            'sector': row['sector'],
            'volume': row['vol_ratio'],
            'rs': row['rs_composite'],
        })

    return alerts


def generate_daily_summary(df_results):
    """Generate daily summary data."""
    # Top stocks
    top_stocks = df_results.head(10).apply(
        lambda x: {'ticker': x['ticker'], 'score': x['composite_score'], 'rs': x['rs_composite']},
        axis=1
    ).tolist()

    # Top sectors
    sector_rs = df_results.groupby('sector')['rs_composite'].mean().sort_values(ascending=False)
    top_sectors = [{'name': s, 'rs': rs} for s, rs in sector_rs.head(5).items()]

    # Breakouts
    breakouts = df_results[df_results['breakout_up'] == True].apply(
        lambda x: {'ticker': x['ticker'], 'score': x['composite_score']},
        axis=1
    ).tolist()

    # Squeezes
    squeezes = df_results[df_results['in_squeeze'] == True].apply(
        lambda x: {'ticker': x['ticker'], 'score': x['composite_score']},
        axis=1
    ).tolist()

    return {
        'top_stocks': top_stocks,
        'top_sectors': top_sectors,
        'breakouts': breakouts,
        'squeezes': squeezes,
    }


# ============================================================
# NICHE THEME DETECTION (Embedded)
# ============================================================

SUPPLY_CHAIN = {
    'NVDA': {
        'theme': 'AI_Infrastructure',
        'suppliers': ['MU', 'TSM', 'AVGO', 'MRVL', 'AMAT', 'LRCX', 'KLAC', 'ASML'],
        'sub_themes': {
            'HBM': ['MU'],
            'CoWoS_Packaging': ['TSM', 'ASX'],
            'Networking': ['AVGO', 'MRVL'],
            'Power_Cooling': ['VRT', 'DELL'],
        },
    },
    'AMD': {
        'theme': 'AI_Infrastructure',
        'suppliers': ['MU', 'TSM', 'AVGO', 'AMAT', 'LRCX'],
        'sub_themes': {'HBM': ['MU'], 'Foundry': ['TSM']},
    },
    'LLY': {
        'theme': 'GLP1_Obesity',
        'suppliers': ['TMO', 'DHR', 'WST', 'CRL'],
        'sub_themes': {'Drug_Delivery': ['WST', 'BDX'], 'CDMO': ['CRL']},
    },
    'NVO': {
        'theme': 'GLP1_Obesity',
        'suppliers': ['TMO', 'DHR', 'WST'],
        'sub_themes': {'Drug_Delivery': ['WST', 'BDX']},
    },
    'TSLA': {
        'theme': 'EV_Ecosystem',
        'suppliers': ['ALB', 'SQM'],
        'sub_themes': {'Lithium': ['ALB', 'SQM'], 'Auto_Semis': ['ON', 'NXPI']},
    },
    'CEG': {
        'theme': 'Nuclear_Renaissance',
        'suppliers': ['CCJ', 'UEC', 'LEU'],
        'sub_themes': {'Uranium': ['CCJ', 'UEC', 'DNN'], 'SMR': ['SMR', 'OKLO']},
    },
    'MSFT': {
        'theme': 'Cloud_Infrastructure',
        'suppliers': ['NVDA', 'AMD'],
        'sub_themes': {
            'Servers': ['DELL', 'HPE', 'SMCI'],
            'Power': ['VRT', 'ETN', 'PWR'],
            'REITs': ['EQIX', 'DLR'],
        },
    },
    'MSTR': {
        'theme': 'Bitcoin',
        'suppliers': [],
        'sub_themes': {'Miners': ['MARA', 'RIOT', 'CLSK'], 'Exchange': ['COIN']},
    },
}

NICHE_THEMES = {
    'HBM_Memory': {'tickers': ['MU', 'WDC', 'STX'], 'drivers': ['NVDA', 'AMD']},
    'AI_Networking': {'tickers': ['AVGO', 'MRVL', 'ANET'], 'drivers': ['NVDA', 'MSFT']},
    'AI_Power_Cooling': {'tickers': ['VRT', 'ETN', 'PWR'], 'drivers': ['NVDA', 'MSFT']},
    'Uranium_Nuclear': {'tickers': ['CCJ', 'UEC', 'DNN', 'LEU'], 'drivers': ['CEG', 'VST']},
    'SMR_Nuclear': {'tickers': ['SMR', 'OKLO', 'BWX'], 'drivers': ['CEG', 'MSFT']},
    'GLP1_Delivery': {'tickers': ['WST', 'BDX', 'BAX'], 'drivers': ['LLY', 'NVO']},
    'Bitcoin_Miners': {'tickers': ['MARA', 'RIOT', 'CLSK', 'HUT'], 'drivers': ['MSTR', 'COIN']},
    'Quantum_Computing': {'tickers': ['IONQ', 'RGTI', 'QBTS'], 'drivers': ['IBM', 'GOOGL']},
    'Humanoid_Robots': {'tickers': ['ISRG', 'ROK', 'TER'], 'drivers': ['TSLA']},
    'Space_Launch': {'tickers': ['RKLB', 'LUNR', 'ASTS'], 'drivers': []},
    'Copper_Grid': {'tickers': ['FCX', 'SCCO', 'TECK'], 'drivers': []},
    'Lithium_Battery': {'tickers': ['ALB', 'SQM', 'LAC'], 'drivers': ['TSLA']},
}


def detect_supply_chain_plays(df_results, hot_threshold=70):
    """Find supply chain opportunities when a driver is hot."""
    plays = []
    hot_stocks = df_results[df_results['composite_score'] >= hot_threshold]['ticker'].tolist()

    for ticker in hot_stocks:
        if ticker in SUPPLY_CHAIN:
            chain = SUPPLY_CHAIN[ticker]
            driver_score = df_results[df_results['ticker'] == ticker]['composite_score'].values[0]

            for supplier in chain.get('suppliers', []):
                supplier_data = df_results[df_results['ticker'] == supplier]
                if len(supplier_data) > 0:
                    supplier_score = supplier_data['composite_score'].values[0]
                    if supplier_score < driver_score - 10:  # Lagging by 10+ points
                        plays.append({
                            'driver': ticker,
                            'beneficiary': supplier,
                            'theme': chain['theme'],
                            'gap': driver_score - supplier_score,
                            'in_squeeze': supplier_data['in_squeeze'].values[0],
                        })

    return sorted(plays, key=lambda x: x['gap'], reverse=True)


def analyze_themes(df_results):
    """Score each niche theme."""
    theme_scores = []

    for theme_name, theme_data in NICHE_THEMES.items():
        tickers = theme_data.get('tickers', [])
        drivers = theme_data.get('drivers', [])

        theme_stocks = df_results[df_results['ticker'].isin(tickers)]
        driver_stocks = df_results[df_results['ticker'].isin(drivers)]

        if len(theme_stocks) == 0:
            continue

        avg_score = theme_stocks['composite_score'].mean()
        avg_rs = theme_stocks['rs_composite'].mean()
        breakouts = theme_stocks['breakout_up'].sum()
        driver_score = driver_stocks['composite_score'].mean() if len(driver_stocks) > 0 else 0

        theme_scores.append({
            'theme': theme_name,
            'avg_score': avg_score,
            'avg_rs': avg_rs,
            'breakouts': int(breakouts),
            'driver_score': driver_score,
            'opportunity': max(0, driver_score - avg_score) if driver_score > 0 else avg_score,
        })

    return sorted(theme_scores, key=lambda x: x['opportunity'], reverse=True)


def detect_unknown_clusters(price_data, df_results, min_size=3, corr_threshold=0.7):
    """Auto-detect unknown themes via correlation clustering."""
    try:
        strong_tickers = df_results[df_results['composite_score'] >= 50]['ticker'].tolist()[:80]

        returns_data = {}
        for ticker in strong_tickers:
            try:
                if isinstance(price_data.columns, pd.MultiIndex):
                    df = price_data[ticker]['Close']
                else:
                    df = price_data['Close']
                if len(df) >= 20:
                    returns_data[ticker] = df.pct_change().iloc[-20:]
            except Exception as e:
                logger.debug(f"Failed to get returns for {ticker}: {e}")
                continue

        if len(returns_data) < 5:
            return []

        returns_df = pd.DataFrame(returns_data).dropna()
        if len(returns_df) < 10:
            return []

        corr_matrix = returns_df.corr()
        clusters = []
        used = set()

        for ticker in corr_matrix.columns:
            if ticker in used:
                continue
            correlated = corr_matrix[ticker][corr_matrix[ticker] >= corr_threshold].index.tolist()

            if len(correlated) >= min_size:
                # Check if NOT a known theme
                is_known = False
                for theme_data in NICHE_THEMES.values():
                    if len(set(correlated) & set(theme_data.get('tickers', []))) >= len(correlated) * 0.5:
                        is_known = True
                        break

                if not is_known:
                    cluster_data = df_results[df_results['ticker'].isin(correlated)]
                    clusters.append({
                        'tickers': correlated[:6],
                        'avg_rs': cluster_data['rs_composite'].mean(),
                        'breakouts': int(cluster_data['breakout_up'].sum()),
                    })
                    used.update(correlated)

        return sorted(clusters, key=lambda x: x['breakouts'], reverse=True)[:3]
    except Exception as e:
        logger.error(f"Failed to detect unknown clusters: {e}")
        return []


def format_theme_alert(themes, supply_plays, unknown_clusters):
    """Format theme analysis for Telegram."""
    msg = "🎯 *THEME ANALYSIS*\n\n"

    # Top themes
    msg += "*Hot Themes:*\n"
    for t in themes[:5]:
        emoji = "🔥" if t['avg_rs'] > 3 else ("📈" if t['avg_rs'] > 0 else "📉")
        msg += f"{emoji} `{t['theme']}` | RS: {t['avg_rs']:+.1f}%"
        if t['breakouts'] > 0:
            msg += f" | {t['breakouts']} breakouts"
        msg += "\n"

    # Supply chain plays
    if supply_plays:
        msg += "\n*Supply Chain Plays:*\n"
        for p in supply_plays[:3]:
            squeeze = " [SQUEEZE]" if p['in_squeeze'] else ""
            msg += f"• {p['driver']} hot → `{p['beneficiary']}` (gap: {p['gap']:.0f}){squeeze}\n"

    # Unknown clusters
    if unknown_clusters:
        msg += "\n*⚠️ Unknown Themes Detected:*\n"
        for c in unknown_clusters:
            msg += f"• {', '.join(c['tickers'][:4])} (RS: {c['avg_rs']:+.1f}%)\n"

    return msg


def load_previous_state():
    """Load previous scan state for comparison."""
    state_file = Path('scanner_state.json')
    if state_file.exists():
        with open(state_file, 'r') as f:
            return json.load(f)
    return {}


def save_current_state(df_results):
    """Save current state for next run comparison."""
    state = {
        'last_run': datetime.now().isoformat(),
        'breakouts': df_results[df_results['breakout_up'] == True]['ticker'].tolist(),
        'top_10': df_results.head(10)['ticker'].tolist(),
    }
    with open('scanner_state.json', 'w') as f:
        json.dump(state, f)
    return state


# ============================================================
# SELF-LEARNING SYSTEM
# ============================================================

LEARNED_THEMES_FILE = 'learned_themes.json'
CLUSTER_HISTORY_FILE = 'cluster_history.json'
PROMOTION_THRESHOLD = 3  # Appearances needed to promote to "emerging theme"


def load_cluster_history():
    """Load history of detected clusters."""
    if Path(CLUSTER_HISTORY_FILE).exists():
        with open(CLUSTER_HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {'clusters': [], 'promoted': []}


def save_cluster_history(history):
    """Save cluster history."""
    with open(CLUSTER_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def load_learned_themes():
    """Load themes that were auto-learned."""
    if Path(LEARNED_THEMES_FILE).exists():
        with open(LEARNED_THEMES_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_learned_themes(themes):
    """Save learned themes."""
    with open(LEARNED_THEMES_FILE, 'w') as f:
        json.dump(themes, f, indent=2)


def cluster_signature(tickers):
    """Create a unique signature for a cluster (sorted tickers)."""
    return '|'.join(sorted(tickers[:6]))


def cluster_overlap(tickers1, tickers2, threshold=0.5):
    """Check if two clusters have significant overlap."""
    set1, set2 = set(tickers1), set(tickers2)
    if len(set1) == 0 or len(set2) == 0:
        return False
    overlap = len(set1 & set2) / min(len(set1), len(set2))
    return overlap >= threshold


def track_unknown_clusters(new_clusters, df_results):
    """
    Track unknown clusters over time.
    Promote to "emerging theme" if seen repeatedly.
    """
    history = load_cluster_history()
    learned = load_learned_themes()
    today = datetime.now().strftime('%Y-%m-%d')

    new_emerging = []

    for cluster in new_clusters:
        tickers = cluster['tickers']
        sig = cluster_signature(tickers)

        # Check if this cluster matches any existing tracked cluster
        matched = False
        for existing in history['clusters']:
            if cluster_overlap(tickers, existing['tickers']):
                # Update existing cluster
                existing['appearances'] += 1
                existing['last_seen'] = today
                existing['avg_rs'] = (existing['avg_rs'] + cluster['avg_rs']) / 2
                matched = True

                # Check for promotion
                if existing['appearances'] >= PROMOTION_THRESHOLD and sig not in history['promoted']:
                    # Promote to emerging theme!
                    theme_id = f"AUTO_{len(learned) + 1}"

                    # Try to identify common sector
                    cluster_data = df_results[df_results['ticker'].isin(tickers)]
                    sectors = cluster_data['sector'].value_counts()
                    common_sector = sectors.index[0] if len(sectors) > 0 else 'Unknown'

                    learned[theme_id] = {
                        'tickers': existing['tickers'],
                        'discovered': existing['first_seen'],
                        'appearances': existing['appearances'],
                        'sector': common_sector,
                        'avg_rs': round(existing['avg_rs'], 2),
                        'status': 'EMERGING',
                        'user_name': None,  # User can name it later
                    }

                    history['promoted'].append(sig)
                    new_emerging.append({
                        'id': theme_id,
                        'tickers': existing['tickers'],
                        'sector': common_sector,
                        'appearances': existing['appearances'],
                    })

                    logger.info(f"PROMOTED: {sig} -> {theme_id} (seen {existing['appearances']} times)")
                break

        if not matched:
            # New cluster - start tracking
            history['clusters'].append({
                'tickers': tickers,
                'signature': sig,
                'first_seen': today,
                'last_seen': today,
                'appearances': 1,
                'avg_rs': cluster['avg_rs'],
            })
            logger.info(f"NEW CLUSTER: {', '.join(tickers[:4])} (tracking started)")

    # Clean up old clusters (not seen in 14 days)
    cutoff = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    history['clusters'] = [c for c in history['clusters'] if c['last_seen'] >= cutoff]

    save_cluster_history(history)
    save_learned_themes(learned)

    return new_emerging, learned


def analyze_learned_themes(df_results, learned_themes):
    """Analyze performance of learned themes."""
    results = []

    for theme_id, theme_data in learned_themes.items():
        tickers = theme_data['tickers']
        theme_stocks = df_results[df_results['ticker'].isin(tickers)]

        if len(theme_stocks) == 0:
            continue

        results.append({
            'id': theme_id,
            'user_name': theme_data.get('user_name') or theme_id,
            'tickers': tickers,
            'avg_score': theme_stocks['composite_score'].mean(),
            'avg_rs': theme_stocks['rs_composite'].mean(),
            'breakouts': int(theme_stocks['breakout_up'].sum()),
            'status': theme_data['status'],
        })

    return sorted(results, key=lambda x: x['avg_rs'], reverse=True)


def format_emerging_theme_alert(new_emerging):
    """Format alert for newly promoted themes."""
    msg = "🎓 *NEW EMERGING THEME DETECTED*\n\n"
    msg += "_The system detected a recurring pattern:_\n\n"

    for theme in new_emerging:
        msg += f"*{theme['id']}* ({theme['sector']})\n"
        msg += f"Tickers: `{', '.join(theme['tickers'][:6])}`\n"
        msg += f"Seen {theme['appearances']} times\n\n"

    msg += "_Reply with a name for this theme to track it!_"
    return msg


def format_learned_themes_summary(learned_analysis):
    """Format summary of learned themes."""
    if not learned_analysis:
        return None

    msg = "📚 *LEARNED THEMES UPDATE*\n\n"

    for t in learned_analysis[:5]:
        emoji = "🔥" if t['avg_rs'] > 3 else ("📈" if t['avg_rs'] > 0 else "📉")
        name = t['user_name'] if t['user_name'] else t['id']
        msg += f"{emoji} *{name}*\n"
        msg += f"   `{', '.join(t['tickers'][:4])}`\n"
        msg += f"   RS: {t['avg_rs']:+.1f}% | Breakouts: {t['breakouts']}\n\n"

    return msg


# ============================================================
# WEEKLY DIGEST
# ============================================================

WEEKLY_STATS_FILE = 'weekly_stats.json'


def load_weekly_stats():
    """Load weekly statistics."""
    if Path(WEEKLY_STATS_FILE).exists():
        with open(WEEKLY_STATS_FILE, 'r') as f:
            return json.load(f)
    return {'scans': [], 'week_start': None}


def save_weekly_stats(stats):
    """Save weekly statistics."""
    with open(WEEKLY_STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)


def update_weekly_stats(df_results, themes, supply_plays):
    """Add today's scan to weekly stats."""
    stats = load_weekly_stats()
    today = datetime.now().strftime('%Y-%m-%d')

    # Reset if new week (Monday)
    if datetime.now().weekday() == 0 and stats.get('week_start') != today:
        stats = {'scans': [], 'week_start': today}

    # Add today's data
    top_10 = df_results.head(10)[['ticker', 'composite_score', 'rs_composite']].to_dict('records')

    stats['scans'].append({
        'date': today,
        'top_10': top_10,
        'breakouts': df_results[df_results['breakout_up'] == True]['ticker'].tolist(),
        'top_themes': [t['theme'] for t in themes[:5]] if themes else [],
        'supply_plays': [f"{p['driver']}->{p['beneficiary']}" for p in supply_plays[:3]],
        'market_breadth': {
            'above_50': int((df_results['above_50'] == True).sum()),
            'above_200': int((df_results['above_200'] == True).sum()),
            'total': len(df_results),
        }
    })

    save_weekly_stats(stats)
    return stats


def generate_weekly_digest():
    """Generate weekly performance digest."""
    stats = load_weekly_stats()
    learned = load_learned_themes()

    if not stats.get('scans'):
        return None

    msg = "📊 *WEEKLY DIGEST*\n"
    msg += f"_{stats.get('week_start', 'This Week')}_\n\n"

    # Count appearances in top 10 across all scans
    ticker_counts = {}
    all_breakouts = []
    theme_counts = {}

    for scan in stats['scans']:
        for stock in scan.get('top_10', []):
            ticker = stock['ticker']
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

        all_breakouts.extend(scan.get('breakouts', []))

        for theme in scan.get('top_themes', []):
            theme_counts[theme] = theme_counts.get(theme, 0) + 1

    # Most consistent leaders
    msg += "*🏆 WEEKLY LEADERS (Most Consistent):*\n"
    sorted_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)
    for ticker, count in sorted_tickers[:10]:
        bars = "█" * count
        msg += f"`{ticker:5}` {bars} ({count}x in top 10)\n"

    # Most breakouts
    breakout_counts = {}
    for b in all_breakouts:
        breakout_counts[b] = breakout_counts.get(b, 0) + 1

    if breakout_counts:
        msg += "\n*🚀 MOST BREAKOUTS THIS WEEK:*\n"
        sorted_breakouts = sorted(breakout_counts.items(), key=lambda x: x[1], reverse=True)
        for ticker, count in sorted_breakouts[:5]:
            msg += f"• `{ticker}` - {count}x breakout\n"

    # Hottest themes
    if theme_counts:
        msg += "\n*🔥 HOTTEST THEMES:*\n"
        sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
        for theme, count in sorted_themes[:5]:
            msg += f"• {theme} ({count}x)\n"

    # Breadth trend
    if len(stats['scans']) >= 2:
        first_breadth = stats['scans'][0].get('market_breadth', {})
        last_breadth = stats['scans'][-1].get('market_breadth', {})

        if first_breadth and last_breadth:
            first_pct = first_breadth.get('above_50', 0) / max(first_breadth.get('total', 1), 1) * 100
            last_pct = last_breadth.get('above_50', 0) / max(last_breadth.get('total', 1), 1) * 100
            change = last_pct - first_pct

            trend = "📈 Improving" if change > 5 else ("📉 Weakening" if change < -5 else "➡️ Stable")
            msg += f"\n*📊 BREADTH TREND:* {trend}\n"
            msg += f"Start: {first_pct:.0f}% above 50 SMA\n"
            msg += f"End: {last_pct:.0f}% above 50 SMA\n"

    # Learned themes progress
    if learned:
        msg += f"\n*📚 LEARNED THEMES:* {len(learned)} tracked\n"
        emerging = [t for t in learned.values() if t.get('status') == 'EMERGING']
        if emerging:
            msg += f"• {len(emerging)} emerging (needs review)\n"

    msg += "\n_Have a great trading week!_ 📈"

    return msg


def is_sunday():
    """Check if today is Sunday."""
    return datetime.now().weekday() == 6


def run_weekly_digest():
    """Run and send weekly digest if it's Sunday."""
    if is_sunday():
        logger.info("Generating weekly digest (Sunday)...")
        digest = generate_weekly_digest()
        if digest:
            send_telegram_message(digest)
            logger.info("Weekly digest sent!")
            return True
    return False


# ============================================================
# 1. NEWS/SENTIMENT SCANNER
# ============================================================

def scrape_finviz_news(ticker):
    """Scrape recent news headlines from Finviz."""
    import requests
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        # Simple regex-based extraction of news headlines
        import re
        html = response.text

        # Find news table
        news_pattern = r'<a[^>]*class="tab-link-news"[^>]*>([^<]+)</a>'
        headlines = re.findall(news_pattern, html)

        return headlines[:5]  # Return top 5 headlines
    except Exception as e:
        return []


def analyze_sentiment(headlines):
    """Simple keyword-based sentiment analysis."""
    bullish_keywords = [
        'upgrade', 'buy', 'outperform', 'beat', 'raises', 'higher', 'surge',
        'soar', 'jump', 'rally', 'breakthrough', 'approval', 'strong', 'record',
        'insider buy', 'bullish', 'growth', 'exceed', 'positive'
    ]
    bearish_keywords = [
        'downgrade', 'sell', 'underperform', 'miss', 'cut', 'lower', 'drop',
        'fall', 'decline', 'weak', 'warning', 'concern', 'risk', 'lawsuit',
        'investigation', 'recall', 'bearish', 'negative', 'disappointing'
    ]

    bullish_count = 0
    bearish_count = 0
    key_headlines = []

    for headline in headlines:
        headline_lower = headline.lower()

        for word in bullish_keywords:
            if word in headline_lower:
                bullish_count += 1
                key_headlines.append(('📈', headline[:60]))
                break

        for word in bearish_keywords:
            if word in headline_lower:
                bearish_count += 1
                key_headlines.append(('📉', headline[:60]))
                break

    if bullish_count > bearish_count:
        sentiment = 'BULLISH'
    elif bearish_count > bullish_count:
        sentiment = 'BEARISH'
    else:
        sentiment = 'NEUTRAL'

    return {
        'sentiment': sentiment,
        'bullish': bullish_count,
        'bearish': bearish_count,
        'key_headlines': key_headlines[:3],
    }


# ============================================================
# 2. INSIDER BUYING ALERTS
# ============================================================

def scrape_insider_activity(ticker):
    """Scrape insider trading data from Finviz."""
    import requests
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        import re
        html = response.text

        # Look for insider trading info
        # Finviz shows insider ownership and recent transactions
        insider_own_match = re.search(r'Insider Own</td><td[^>]*>([^<]+)', html)
        insider_trans_match = re.search(r'Insider Trans</td><td[^>]*>([^<]+)', html)

        insider_own = insider_own_match.group(1) if insider_own_match else 'N/A'
        insider_trans = insider_trans_match.group(1) if insider_trans_match else 'N/A'

        # Parse transaction percentage
        trans_pct = 0
        if insider_trans != 'N/A':
            try:
                trans_pct = float(insider_trans.replace('%', '').replace('+', ''))
            except (ValueError, TypeError):
                pass

        return {
            'ownership': insider_own,
            'recent_trans': insider_trans,
            'trans_pct': trans_pct,
            'is_buying': trans_pct > 0,
        }
    except Exception as e:
        logger.debug(f"Failed to scrape insider activity for {ticker}: {e}")
        return None


def detect_insider_buying(tickers, min_buy_pct=1.0):
    """Find stocks with significant insider buying."""
    insider_buys = []

    for ticker in tickers[:50]:  # Limit to top 50 to avoid rate limiting
        activity = scrape_insider_activity(ticker)
        if activity and activity['is_buying'] and activity['trans_pct'] >= min_buy_pct:
            insider_buys.append({
                'ticker': ticker,
                'ownership': activity['ownership'],
                'recent_trans': activity['recent_trans'],
            })

    return insider_buys


# ============================================================
# 3. OPTIONS FLOW (Simplified - uses Finviz data)
# ============================================================

def scrape_options_data(ticker):
    """Get options-related metrics from Finviz."""
    import requests
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return None

        import re
        html = response.text

        # Extract short float and option metrics
        short_float_match = re.search(r'Short Float</td><td[^>]*>([^<]+)', html)
        short_ratio_match = re.search(r'Short Ratio</td><td[^>]*>([^<]+)', html)

        short_float = short_float_match.group(1) if short_float_match else 'N/A'
        short_ratio = short_ratio_match.group(1) if short_ratio_match else 'N/A'

        # Parse values
        short_float_pct = 0
        if short_float != 'N/A':
            try:
                short_float_pct = float(short_float.replace('%', ''))
            except (ValueError, TypeError):
                pass

        return {
            'short_float': short_float,
            'short_ratio': short_ratio,
            'short_float_pct': short_float_pct,
            'high_short': short_float_pct > 15,  # >15% short is notable
        }
    except Exception as e:
        logger.debug(f"Failed to scrape options data for {ticker}: {e}")
        return None


# ============================================================
# 4. ENTRY SIGNALS
# ============================================================

def calculate_entry_signals(df, ticker_data):
    """Calculate suggested entry points, stops, and targets."""
    if df is None or len(df) < 50:
        return None

    close = df['Close']
    high = df['High']
    low = df['Low']

    current_price = close.iloc[-1]

    # Moving averages
    sma_20 = close.rolling(20).mean().iloc[-1]
    sma_50 = close.rolling(50).mean().iloc[-1]

    # ATR for stop calculation
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]

    # Recent swing low (for stop)
    recent_low = low.iloc[-10:].min()

    # Resistance levels (recent highs)
    recent_high = high.iloc[-20:].max()

    # Entry strategies
    entries = []

    # Strategy 1: Pullback to 20 SMA
    if current_price > sma_20 * 1.02:  # Price is 2%+ above 20 SMA
        entries.append({
            'type': 'PULLBACK_20SMA',
            'entry': round(sma_20, 2),
            'stop': round(sma_20 - 1.5 * atr, 2),
            'target': round(current_price + 2 * atr, 2),
        })

    # Strategy 2: Breakout retest
    if ticker_data.get('breakout_up'):
        entries.append({
            'type': 'BREAKOUT_RETEST',
            'entry': round(current_price, 2),
            'stop': round(recent_low, 2),
            'target': round(current_price + 3 * atr, 2),
        })

    # Strategy 3: ATR-based stop
    entries.append({
        'type': 'ATR_STOP',
        'entry': round(current_price, 2),
        'stop': round(current_price - 2 * atr, 2),
        'target': round(current_price + 3 * atr, 2),
        'risk_reward': '1:1.5',
    })

    return {
        'current_price': round(current_price, 2),
        'sma_20': round(sma_20, 2),
        'sma_50': round(sma_50, 2),
        'atr': round(atr, 2),
        'recent_low': round(recent_low, 2),
        'recent_high': round(recent_high, 2),
        'entries': entries,
    }


# ============================================================
# 8. CHARTS IN TELEGRAM
# ============================================================

def generate_chart(ticker, price_data):
    """Generate a candlestick chart image for a ticker."""
    try:
        if isinstance(price_data.columns, pd.MultiIndex):
            df = price_data[ticker].copy()
        else:
            df = price_data.copy()

        df = normalize_dataframe_columns(df)
        df = df.dropna().iloc[-60:]  # Last 60 days

        if len(df) < 20:
            return None

        # Ensure proper column names
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

        # Calculate moving averages
        sma_20 = df['Close'].rolling(20).mean()
        sma_50 = df['Close'].rolling(50).mean()

        # Bollinger Bands
        bb_mid = df['Close'].rolling(20).mean()
        bb_std = df['Close'].rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std

        # Create additional plots
        add_plots = [
            mpf.make_addplot(sma_20, color='orange', width=1),
            mpf.make_addplot(sma_50, color='purple', width=1),
            mpf.make_addplot(bb_upper, color='blue', width=0.7, linestyle='--', alpha=0.5),
            mpf.make_addplot(bb_lower, color='blue', width=0.7, linestyle='--', alpha=0.5),
        ]

        # Custom style
        mc = mpf.make_marketcolors(
            up='#00b894',
            down='#d63031',
            edge='inherit',
            wick='inherit',
            volume='inherit',
        )

        style = mpf.make_mpf_style(
            base_mpf_style='nightclouds',
            marketcolors=mc,
            gridstyle='-',
            gridcolor='#2d3436',
            facecolor='#0d1117',
        )

        # Generate chart
        buf = io.BytesIO()

        fig, axes = mpf.plot(
            df,
            type='candle',
            style=style,
            volume=True,
            addplot=add_plots,
            title=f'\n{ticker} - Daily Candlestick',
            ylabel='Price ($)',
            ylabel_lower='Volume',
            figsize=(12, 8),
            returnfig=True,
        )

        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                    facecolor='#0d1117', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        return buf
    except Exception as e:
        logger.error(f"Chart error for {ticker}: {e}")
        return None


def send_telegram_photo(photo_buffer, caption=''):
    """Send a photo via Telegram using centralized client."""
    if not config.telegram.is_configured:
        return False

    try:
        return send_photo(config.telegram.chat_id, photo_buffer, caption)
    except Exception as e:
        logger.error(f"Telegram photo error: {e}")
        return False


# ============================================================
# CORRELATION MATRIX
# ============================================================

def calculate_correlation_matrix(price_data, tickers, period=20):
    """Calculate correlation matrix for given tickers."""
    returns_data = {}

    for ticker in tickers:
        try:
            if isinstance(price_data.columns, pd.MultiIndex):
                df = price_data[ticker]['Close']
            else:
                df = price_data['Close']

            if len(df) >= period:
                returns_data[ticker] = df.pct_change().iloc[-period:]
        except Exception as e:
            logger.debug(f"Failed to calculate returns for {ticker}: {e}")
            continue

    if len(returns_data) < 2:
        return None

    returns_df = pd.DataFrame(returns_data).dropna()
    corr_matrix = returns_df.corr()

    return corr_matrix


def detect_high_correlation(corr_matrix, threshold=0.8):
    """Find highly correlated pairs."""
    high_corr_pairs = []

    tickers = corr_matrix.columns.tolist()

    for i, t1 in enumerate(tickers):
        for j, t2 in enumerate(tickers):
            if i < j:  # Avoid duplicates
                corr = corr_matrix.loc[t1, t2]
                if abs(corr) >= threshold:
                    high_corr_pairs.append({
                        'pair': (t1, t2),
                        'correlation': round(corr, 3),
                    })

    return sorted(high_corr_pairs, key=lambda x: abs(x['correlation']), reverse=True)


def format_correlation_alert(high_corr_pairs, top_n=10):
    """Format correlation alert message."""
    if not high_corr_pairs:
        return None

    msg = "🔗 *CORRELATION ALERT*\n\n"
    msg += "_Highly correlated stocks (>80%):_\n"
    msg += "_Avoid overconcentration!_\n\n"

    for pair in high_corr_pairs[:top_n]:
        t1, t2 = pair['pair']
        corr = pair['correlation']
        msg += f"• `{t1}` ↔ `{t2}`: {corr:.0%}\n"

    return msg


# ============================================================
# 5. INTERACTIVE TELEGRAM BOT
# ============================================================

def get_telegram_updates(offset=None):
    """Get updates from Telegram bot."""
    import requests
    if not config.telegram.is_configured:
        return []

    url = f"{config.telegram.api_url}/getUpdates"
    params = {'timeout': 1}
    if offset:
        params['offset'] = offset

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            return response.json().get('result', [])
    except Exception as e:
        logger.debug(f"Failed to get Telegram updates: {e}")
    return []


def process_ticker_query(ticker, price_data, df_results):
    """Process a ticker query and return analysis."""
    ticker = ticker.upper().strip()

    # Get data
    ticker_row = df_results[df_results['ticker'] == ticker]
    if len(ticker_row) == 0:
        return f"❌ Ticker `{ticker}` not found in scan results."

    row = ticker_row.iloc[0]

    # Basic info
    msg = f"📊 *{ticker} ANALYSIS*\n\n"
    msg += f"*Score:* {row['composite_score']:.0f}/100 (Rank #{int(row['rank'])})\n"
    msg += f"*RS vs SPY:* {row['rs_composite']:+.2f}%\n"
    msg += f"*Price:* ${row['price']:.2f}\n\n"

    # Trend
    msg += "*Trend:*\n"
    msg += f"• Above 20 SMA: {'✅' if row['above_20'] else '❌'}\n"
    msg += f"• Above 50 SMA: {'✅' if row['above_50'] else '❌'}\n"
    msg += f"• Above 200 SMA: {'✅' if row['above_200'] else '❌'}\n"
    msg += f"• MAs Aligned: {'✅' if row['ma_aligned'] else '❌'}\n\n"

    # Squeeze/Breakout
    if row['in_squeeze']:
        msg += "⏳ *IN SQUEEZE* - Volatility contracting\n"
    if row['breakout_up']:
        msg += "🚀 *BREAKOUT* - Price above upper BB\n"

    # Volume
    msg += f"\n*Volume:* {row['vol_ratio']:.1f}x average"
    if row['vol_ratio'] > 2:
        msg += " 🔥"
    msg += "\n"

    # Entry signals
    try:
        if isinstance(price_data.columns, pd.MultiIndex):
            df = price_data[ticker].copy()
        else:
            df = price_data.copy()

        entry_signals = calculate_entry_signals(df, row.to_dict())
        if entry_signals:
            msg += f"\n*Entry Ideas:*\n"
            msg += f"• ATR: ${entry_signals['atr']:.2f}\n"
            msg += f"• Stop: ${entry_signals['entries'][0]['stop']:.2f}\n"
            msg += f"• Target: ${entry_signals['entries'][0]['target']:.2f}\n"
    except Exception as e:
        logger.debug(f"Failed to calculate entry signals for {ticker}: {e}")

    # News sentiment
    headlines = scrape_finviz_news(ticker)
    if headlines:
        sentiment = analyze_sentiment(headlines)
        msg += f"\n*Sentiment:* {sentiment['sentiment']}"
        if sentiment['key_headlines']:
            msg += "\n"
            for emoji, headline in sentiment['key_headlines'][:2]:
                msg += f"{emoji} _{headline}_\n"

    # Insider activity
    insider = scrape_insider_activity(ticker)
    if insider:
        msg += f"\n*Insider:* {insider['recent_trans']}"
        if insider['is_buying']:
            msg += " 🟢"

    return msg


def handle_interactive_commands(price_data, df_results):
    """Check for and handle Telegram commands."""
    try:
        # Load last processed update ID
        offset_file = Path('telegram_offset.json')
        last_offset = 0
        if offset_file.exists():
            with open(offset_file, 'r') as f:
                last_offset = json.load(f).get('offset', 0)

        updates = get_telegram_updates(offset=last_offset + 1)

        for update in updates:
            update_id = update.get('update_id', 0)
            message = update.get('message', {})
            text = message.get('text', '').strip()

            if text:
                # Check if it's a ticker query (1-5 uppercase letters)
                if len(text) <= 5 and text.isalpha():
                    response = process_ticker_query(text, price_data, df_results)
                    send_telegram_message(response)

                    # Send chart
                    chart = generate_chart(text.upper(), price_data)
                    if chart:
                        send_telegram_photo(chart, caption=f"{text.upper()} Chart")

                elif text.lower() == '/top':
                    # Show top 10
                    msg = "🏆 *TOP 10 STOCKS*\n\n"
                    for _, row in df_results.head(10).iterrows():
                        msg += f"`{row['ticker']:5}` | Score: {row['composite_score']:.0f} | RS: {row['rs_composite']:+.1f}%\n"
                    send_telegram_message(msg)

                elif text.lower() == '/themes':
                    # Show hot themes
                    themes = analyze_themes(df_results)
                    msg = "🎯 *HOT THEMES*\n\n"
                    for t in themes[:10]:
                        emoji = "🔥" if t['avg_rs'] > 3 else "📈"
                        msg += f"{emoji} `{t['theme']}` | RS: {t['avg_rs']:+.1f}%\n"
                    send_telegram_message(msg)

                elif text.lower() == '/help':
                    msg = "🤖 *BOT COMMANDS*\n\n"
                    msg += "• Send any ticker (e.g., `NVDA`) for analysis\n"
                    msg += "• `/top` - Show top 10 stocks\n"
                    msg += "• `/themes` - Show hot themes\n"
                    msg += "• `/help` - Show this help\n"
                    send_telegram_message(msg)

            # Update offset
            with open(offset_file, 'w') as f:
                json.dump({'offset': update_id}, f)

    except Exception as e:
        logger.error(f"Interactive bot error: {e}")


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    """Main automation function."""
    logger.info("=" * 60)
    logger.info("STOCK SCANNER AUTOMATION")
    logger.info(f"Started: {datetime.now()}")
    logger.info("=" * 60)

    # Load previous state
    prev_state = load_previous_state()

    # Run scan
    df_results, price_data = run_scan()

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d')
    df_results.to_csv(f'scan_{timestamp}.csv', index=False)

    # Generate daily summary
    summary = generate_daily_summary(df_results)

    # Send daily summary
    summary_msg = format_alert_message('DAILY_SUMMARY', summary)
    send_telegram_message(summary_msg)

    # ============================================================
    # THEME DETECTION
    # ============================================================
    logger.info("Running theme detection...")

    # Detect supply chain plays
    supply_plays = detect_supply_chain_plays(df_results)
    logger.info(f"Found {len(supply_plays)} supply chain opportunities")

    # Analyze themes
    themes = analyze_themes(df_results)
    logger.info(f"Analyzed {len(themes)} themes")

    # Detect unknown clusters
    unknown_clusters = detect_unknown_clusters(price_data, df_results)
    logger.info(f"Found {len(unknown_clusters)} unknown clusters")

    # Send theme alert
    if themes or supply_plays or unknown_clusters:
        theme_msg = format_theme_alert(themes, supply_plays, unknown_clusters)
        send_telegram_message(theme_msg)

    # ============================================================
    # SELF-LEARNING SYSTEM
    # ============================================================
    logger.info("Running self-learning system...")

    # Track unknown clusters and check for promotions
    new_emerging, learned_themes = track_unknown_clusters(unknown_clusters, df_results)

    # Alert on newly promoted themes
    if new_emerging:
        emerging_msg = format_emerging_theme_alert(new_emerging)
        send_telegram_message(emerging_msg)
        logger.info(f"Promoted {len(new_emerging)} new emerging themes!")

    # Analyze and report on learned themes
    if learned_themes:
        learned_analysis = analyze_learned_themes(df_results, learned_themes)
        if learned_analysis:
            learned_msg = format_learned_themes_summary(learned_analysis)
            if learned_msg:
                send_telegram_message(learned_msg)
        logger.info(f"Tracking {len(learned_themes)} learned themes")

    # ============================================================
    # BREAKOUT ALERTS
    # ============================================================
    alerts = detect_alerts(df_results, prev_state)

    # Only send new breakout alerts (not already in previous state)
    prev_breakouts = set(prev_state.get('breakouts', []))
    new_alerts = [a for a in alerts if a['ticker'] not in prev_breakouts]

    for alert in new_alerts[:5]:  # Limit to 5 alerts
        if alert['type'] == 'NEW_BREAKOUT':
            msg = format_alert_message('NEW_BREAKOUT', alert)
            send_telegram_message(msg)

    # Save current state
    save_current_state(df_results)

    # ============================================================
    # WEEKLY STATS & DIGEST
    # ============================================================
    logger.info("Updating weekly stats...")
    update_weekly_stats(df_results, themes, supply_plays)

    # Send weekly digest on Sunday
    if run_weekly_digest():
        logger.info("Weekly digest sent!")

    # ============================================================
    # INSIDER BUYING DETECTION
    # ============================================================
    logger.info("Checking insider activity...")
    top_tickers = df_results.head(30)['ticker'].tolist()
    insider_buys = detect_insider_buying(top_tickers)

    if insider_buys:
        msg = "🟢 *INSIDER BUYING DETECTED*\n\n"
        for ib in insider_buys[:5]:
            msg += f"• `{ib['ticker']}` - {ib['recent_trans']} (Own: {ib['ownership']})\n"
        send_telegram_message(msg)
        logger.info(f"Found {len(insider_buys)} stocks with insider buying")

    # ============================================================
    # CORRELATION MATRIX
    # ============================================================
    logger.info("Calculating correlations...")
    top_20 = df_results.head(20)['ticker'].tolist()
    corr_matrix = calculate_correlation_matrix(price_data, top_20)

    if corr_matrix is not None:
        high_corr = detect_high_correlation(corr_matrix, threshold=0.8)
        if high_corr:
            corr_msg = format_correlation_alert(high_corr)
            if corr_msg:
                send_telegram_message(corr_msg)
            logger.info(f"Found {len(high_corr)} highly correlated pairs")

    # ============================================================
    # SEND CHARTS FOR TOP 3
    # ============================================================
    logger.info("Generating charts for top stocks...")
    for ticker in df_results.head(3)['ticker'].tolist():
        chart = generate_chart(ticker, price_data)
        if chart:
            row = df_results[df_results['ticker'] == ticker].iloc[0]
            caption = f"*{ticker}* | Score: {row['composite_score']:.0f} | RS: {row['rs_composite']:+.1f}%"
            send_telegram_photo(chart, caption=caption)
            logger.info(f"Chart sent: {ticker}")

    # ============================================================
    # PROCESS INTERACTIVE COMMANDS
    # ============================================================
    logger.info("Checking for interactive commands...")
    handle_interactive_commands(price_data, df_results)

    # ============================================================
    # SECTOR ROTATION ANALYSIS
    # ============================================================
    logger.info("Running sector rotation analysis...")
    try:
        from sector_rotation import run_sector_rotation_analysis, format_sector_rotation_report
        rotation_results = run_sector_rotation_analysis()
        rotation_msg = format_sector_rotation_report(
            rotation_results['ranked'],
            rotation_results['rotations'],
            rotation_results['cycle']
        )
        send_telegram_message(rotation_msg)
        logger.info("Sector rotation report sent!")
    except Exception as e:
        logger.error(f"Sector rotation error: {e}")

    # ============================================================
    # MULTI-TIMEFRAME CONFLUENCE (Top 5)
    # ============================================================
    logger.info("Running multi-timeframe analysis...")
    try:
        from multi_timeframe import scan_mtf_confluence, format_mtf_scan_results
        top_tickers = df_results.head(20)['ticker'].tolist()
        mtf_results = scan_mtf_confluence(top_tickers, min_score=6)
        if mtf_results:
            mtf_msg = format_mtf_scan_results(mtf_results)
            send_telegram_message(mtf_msg)
            logger.info(f"Found {len(mtf_results)} stocks with MTF confluence")
    except Exception as e:
        logger.error(f"MTF analysis error: {e}")

    # ============================================================
    # NEWS SENTIMENT SCAN
    # ============================================================
    logger.info("Scanning news sentiment...")
    try:
        from news_analyzer import scan_news_sentiment, format_news_scan_results
        top_10 = df_results.head(10)['ticker'].tolist()
        news_results = scan_news_sentiment(top_10)
        news_msg = format_news_scan_results(news_results)
        send_telegram_message(news_msg)
        logger.info("News sentiment scan sent!")
    except Exception as e:
        logger.error(f"News scan error: {e}")

    # ============================================================
    # COMPREHENSIVE SELF-LEARNING
    # ============================================================
    logger.info("Running comprehensive self-learning...")
    try:
        from self_learning import (
            auto_learn_from_scan,
            auto_learn_stock_profile,
            detect_market_regime,
            record_regime_change,
            track_theme_lifecycle,
        )

        # Get SPY data for regime detection
        spy_df = get_ticker_df(price_data, 'SPY')

        # 1. Learn from scan results (alert accuracy, entries)
        auto_learn_from_scan(df_results, spy_df)
        logger.info("Recorded alerts for accuracy tracking")

        # 2. Detect and record market regime
        if spy_df is not None and len(spy_df) >= 50:
            regime = detect_market_regime(spy_df)
            spy_price = float(spy_df['Close'].iloc[-1])
            record_regime_change(regime, spy_price)
            logger.info(f"Market regime: {regime}")

        # 3. Learn stock personalities for top movers
        top_movers = df_results.head(20)['ticker'].tolist()
        profiles_updated = 0
        for ticker in top_movers:
            try:
                ticker_df = get_ticker_df(price_data, ticker)
                if ticker_df is not None and len(ticker_df) >= 50:
                    auto_learn_stock_profile(ticker, ticker_df)
                    profiles_updated += 1
            except Exception as e:
                logger.debug(f"Failed to update profile for {ticker}: {e}")
        logger.info(f"Updated {profiles_updated} stock personality profiles")

        # 4. Track theme lifecycles
        for theme in themes[:10]:
            theme_name = theme['theme']
            if theme['avg_rs'] > 5:
                status = 'rising'
            elif theme['avg_rs'] > 0:
                status = 'stable'
            elif theme['avg_rs'] > -3:
                status = 'fading'
            else:
                status = 'dead'

            # Get top stocks for this theme
            theme_data = NICHE_THEMES.get(theme_name, {})
            top_stocks = theme_data.get('tickers', [])[:5]

            track_theme_lifecycle(
                theme_name,
                status=status,
                top_stocks=top_stocks,
                momentum_score=theme['avg_rs']
            )
        logger.info(f"Tracked lifecycle for {min(len(themes), 10)} themes")

        logger.info("Self-learning complete!")

    except Exception as e:
        logger.error(f"Self-learning error: {e}")

    # ============================================================
    # AI-POWERED ANALYSIS
    # ============================================================
    logger.info("Running AI-powered analysis...")
    try:
        from ai_learning import (
            generate_market_narrative,
            analyze_signal_pattern,
            scan_for_anomalies,
            get_best_patterns,
        )

        # 1. Generate AI Market Narrative
        narrative = generate_market_narrative(
            themes=themes[:5],
            sectors=[{'name': s, 'rs': rs} for s, rs in
                    df_results.groupby('sector')['rs_composite'].mean().sort_values(ascending=False).head(5).items()],
            top_stocks=df_results.head(10).to_dict('records'),
            news_highlights=[],
        )

        if narrative and not narrative.get('error'):
            msg = "🤖 *AI MARKET BRIEFING*\n\n"
            msg += f"*{narrative.get('headline', 'Market Update')}*\n\n"
            msg += f"_{narrative.get('main_narrative', '')}_\n\n"

            opp = narrative.get('key_opportunity', {})
            if opp and opp.get('description'):
                msg += f"*Opportunity:* {opp['description']}\n"
                if opp.get('tickers'):
                    msg += f"Watch: `{'`, `'.join(opp['tickers'][:4])}`\n"

            risk = narrative.get('key_risk', {})
            if risk and risk.get('description'):
                msg += f"\n*Risk:* {risk['description']}"

            send_telegram_message(msg)
            logger.info("AI market narrative sent!")

        # 2. Learn patterns from top alerts
        for _, row in df_results.head(5).iterrows():
            try:
                signals = {
                    'above_20sma': row.get('above_20', False),
                    'above_50sma': row.get('above_50', False),
                    'above_200sma': row.get('above_200', False),
                    'ma_aligned': row.get('ma_aligned', False),
                    'in_squeeze': row.get('in_squeeze', False),
                    'breakout': row.get('breakout_up', False),
                    'volume_spike': row.get('vol_ratio', 1) > 1.5,
                    'rs_positive': row.get('rs_composite', 0) > 0,
                    'rs_strong': row.get('rs_composite', 0) > 5,
                }
                analyze_signal_pattern(signals)
            except Exception as e:
                logger.debug(f"Failed to analyze signal pattern: {e}")
        logger.info("Recorded signal patterns for AI learning")

        # 3. Scan for anomalies in top movers
        anomaly_data = {}
        for _, row in df_results.head(20).iterrows():
            ticker = row['ticker']
            anomaly_data[ticker] = {
                'vol_ratio': row.get('vol_ratio', 1),
                'daily_change': row.get('rs_composite', 0) / 5,  # Rough approximation
                'score': row.get('composite_score', 0),
            }

        # Only flag extreme anomalies
        extreme = {t: d for t, d in anomaly_data.items()
                  if d['vol_ratio'] > 3 or abs(d.get('daily_change', 0)) > 5}

        if extreme:
            logger.info(f"Detected {len(extreme)} potential anomalies for AI review")

        # 4. Report best patterns if we have enough data
        patterns = get_best_patterns()
        if patterns and len(patterns) >= 3:
            best = patterns[0]
            if best['win_rate'] >= 65:
                msg = f"🎯 *AI PATTERN INSIGHT*\n\n"
                msg += f"Best pattern: *{best['pattern']}*\n"
                msg += f"Win rate: {best['win_rate']:.0f}% ({best['total_trades']} trades)\n"
                msg += f"\n_Focus on setups with these signals._"
                send_telegram_message(msg)
                logger.info(f"Best pattern: {best['pattern']} ({best['win_rate']:.0f}%)")

        logger.info("AI analysis complete!")

    except Exception as e:
        logger.error(f"AI analysis error: {e}")

    logger.info(f"Completed: {datetime.now()}")
    logger.info(f"Sent {len(new_alerts)} new breakout alerts")
    logger.info(f"Themes analyzed: {len(themes)}")

    return df_results


if __name__ == '__main__':
    main()
