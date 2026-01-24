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

    # Detect and send alerts
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

    print(f"\nCompleted: {datetime.now()}")
    print(f"Sent {len(new_alerts)} new alerts")

    return df_results


if __name__ == '__main__':
    main()
