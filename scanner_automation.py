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

import os
import json
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================

# Telegram settings (set via environment variables for security)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Scoring weights
WEIGHTS = {
    'trend': 0.30,
    'squeeze': 0.20,
    'rs': 0.20,
    'sentiment': 0.15,
    'volume': 0.15,
}

# Alert thresholds
ALERT_THRESHOLDS = {
    'min_composite_score': 70,
    'min_rs': 5,
    'volume_spike': 2.0,
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
    """Send message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured. Printing to console:")
        print(message)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
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
        return df.dropna()
    except:
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


def calculate_rs(df, spy_df):
    """Calculate relative strength vs SPY."""
    if df is None or spy_df is None:
        return {'rs_composite': 0, 'rs_score': 0}

    try:
        stock_ret_5 = (df['Close'].iloc[-1] / df['Close'].iloc[-5] - 1) * 100
        stock_ret_10 = (df['Close'].iloc[-1] / df['Close'].iloc[-10] - 1) * 100
        stock_ret_20 = (df['Close'].iloc[-1] / df['Close'].iloc[-20] - 1) * 100

        spy_ret_5 = (spy_df['Close'].iloc[-1] / spy_df['Close'].iloc[-5] - 1) * 100
        spy_ret_10 = (spy_df['Close'].iloc[-1] / spy_df['Close'].iloc[-10] - 1) * 100
        spy_ret_20 = (spy_df['Close'].iloc[-1] / spy_df['Close'].iloc[-20] - 1) * 100

        rs_5 = stock_ret_5 - spy_ret_5
        rs_10 = stock_ret_10 - spy_ret_10
        rs_20 = stock_ret_20 - spy_ret_20

        rs_composite = rs_5 * 0.5 + rs_10 * 0.3 + rs_20 * 0.2

        if rs_composite > 5:
            rs_score = 3
        elif rs_composite > 2:
            rs_score = 2
        elif rs_composite > 0:
            rs_score = 1
        else:
            rs_score = 0

        return {'rs_composite': rs_composite, 'rs_score': rs_score}
    except:
        return {'rs_composite': 0, 'rs_score': 0}


def get_sector(ticker):
    """Get sector for ticker using yfinance."""
    try:
        return yf.Ticker(ticker).info.get('sector', 'Unknown')
    except:
        return 'Unknown'


def run_scan():
    """Run the full scan."""
    print(f"Starting scan at {datetime.now()}")

    # Get unique tickers
    all_tickers = list(set(SP500_TICKERS + NASDAQ100_TICKERS))
    print(f"Scanning {len(all_tickers)} tickers...")

    # Fetch data
    print("Fetching price data...")
    price_data = yf.download(all_tickers + ['SPY'], period='1y', group_by='ticker', progress=False)

    spy_df = get_ticker_df(price_data, 'SPY')

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

        rs = calculate_rs(df, spy_df)

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

    print(f"Scan complete. {len(df_results)} tickers analyzed.")

    return df_results, price_data


def detect_alerts(df_results, previous_results=None):
    """Detect alert-worthy conditions."""
    alerts = []

    # New breakouts (high score + breakout flag)
    breakouts = df_results[
        (df_results['composite_score'] >= ALERT_THRESHOLDS['min_composite_score']) &
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
        (df_results['vol_ratio'] >= ALERT_THRESHOLDS['volume_spike']) &
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
            except:
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
    except:
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

                    print(f"  🎓 PROMOTED: {sig} → {theme_id} (seen {existing['appearances']} times)")
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
            print(f"  📝 NEW CLUSTER: {', '.join(tickers[:4])} (tracking started)")

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
        print("\n📊 Generating weekly digest (Sunday)...")
        digest = generate_weekly_digest()
        if digest:
            send_telegram_message(digest)
            print("  Weekly digest sent!")
            return True
    return False


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    """Main automation function."""
    print("=" * 60)
    print("STOCK SCANNER AUTOMATION")
    print(f"Started: {datetime.now()}")
    print("=" * 60)

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
    print("\nRunning theme detection...")

    # Detect supply chain plays
    supply_plays = detect_supply_chain_plays(df_results)
    print(f"  Found {len(supply_plays)} supply chain opportunities")

    # Analyze themes
    themes = analyze_themes(df_results)
    print(f"  Analyzed {len(themes)} themes")

    # Detect unknown clusters
    unknown_clusters = detect_unknown_clusters(price_data, df_results)
    print(f"  Found {len(unknown_clusters)} unknown clusters")

    # Send theme alert
    if themes or supply_plays or unknown_clusters:
        theme_msg = format_theme_alert(themes, supply_plays, unknown_clusters)
        send_telegram_message(theme_msg)

    # ============================================================
    # SELF-LEARNING SYSTEM
    # ============================================================
    print("\nRunning self-learning system...")

    # Track unknown clusters and check for promotions
    new_emerging, learned_themes = track_unknown_clusters(unknown_clusters, df_results)

    # Alert on newly promoted themes
    if new_emerging:
        emerging_msg = format_emerging_theme_alert(new_emerging)
        send_telegram_message(emerging_msg)
        print(f"  🎓 Promoted {len(new_emerging)} new emerging themes!")

    # Analyze and report on learned themes
    if learned_themes:
        learned_analysis = analyze_learned_themes(df_results, learned_themes)
        if learned_analysis:
            learned_msg = format_learned_themes_summary(learned_analysis)
            if learned_msg:
                send_telegram_message(learned_msg)
        print(f"  📚 Tracking {len(learned_themes)} learned themes")

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
    print("\nUpdating weekly stats...")
    update_weekly_stats(df_results, themes, supply_plays)

    # Send weekly digest on Sunday
    if run_weekly_digest():
        print("  📊 Weekly digest sent!")

    print(f"\nCompleted: {datetime.now()}")
    print(f"Sent {len(new_alerts)} new breakout alerts")
    print(f"Themes analyzed: {len(themes)}")

    return df_results


if __name__ == '__main__':
    main()
