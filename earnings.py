#!/usr/bin/env python3
"""
Earnings Calendar Module

Fetches upcoming earnings for tracked stocks.
"""

import yfinance as yf
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Key stocks to track earnings
EARNINGS_WATCHLIST = [
    # Mega caps
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
    # Semis
    'AMD', 'AVGO', 'MU', 'INTC', 'TSM', 'QCOM', 'AMAT',
    # Software
    'CRM', 'NOW', 'SNOW', 'PLTR', 'CRWD', 'PANW', 'ZS',
    # Healthcare
    'LLY', 'NVO', 'AMGN', 'MRNA', 'PFE', 'JNJ', 'UNH',
    # Finance
    'JPM', 'GS', 'MS', 'BAC', 'V', 'MA',
    # Energy
    'XOM', 'CVX', 'SLB',
    # Consumer
    'COST', 'WMT', 'HD', 'NKE', 'SBUX',
    # Other
    'DIS', 'NFLX', 'BA', 'CAT', 'GE'
]


def get_earnings_date(ticker):
    """Get next earnings date for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        calendar = stock.calendar

        if calendar is None or calendar.empty:
            return None

        # Try to get earnings date
        if 'Earnings Date' in calendar.index:
            dates = calendar.loc['Earnings Date']
            if isinstance(dates, list) or hasattr(dates, '__iter__'):
                next_date = dates[0] if len(dates) > 0 else None
            else:
                next_date = dates

            if next_date:
                if hasattr(next_date, 'date'):
                    return next_date.date()
                return next_date

        return None
    except Exception as e:
        return None


def get_upcoming_earnings(tickers=None, days_ahead=14):
    """
    Get upcoming earnings for watchlist.

    Returns list of (ticker, date, days_until) sorted by date.
    """
    if tickers is None:
        tickers = EARNINGS_WATCHLIST

    today = datetime.now().date()
    cutoff = today + timedelta(days=days_ahead)

    earnings = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_earnings_date, t): t for t in tickers}

        for future in as_completed(futures):
            ticker = futures[future]
            try:
                date = future.result()
                if date and today <= date <= cutoff:
                    days_until = (date - today).days
                    earnings.append({
                        'ticker': ticker,
                        'date': date,
                        'days_until': days_until
                    })
            except:
                pass

    # Sort by date
    earnings.sort(key=lambda x: x['date'])

    return earnings


def format_earnings_calendar(earnings):
    """Format earnings for Telegram message."""
    if not earnings:
        return "📅 *EARNINGS CALENDAR*\n\n_No upcoming earnings in the next 14 days._"

    msg = "📅 *EARNINGS CALENDAR*\n\n"

    current_date = None
    for e in earnings:
        date = e['date']
        days = e['days_until']

        # Group by date
        if date != current_date:
            current_date = date
            day_name = date.strftime('%A')
            date_str = date.strftime('%b %d')

            if days == 0:
                msg += f"\n🔴 *TODAY* ({date_str})\n"
            elif days == 1:
                msg += f"\n🟡 *TOMORROW* ({date_str})\n"
            else:
                msg += f"\n⚪ *{day_name}* ({date_str})\n"

        msg += f"   • `{e['ticker']}`\n"

    msg += "\n_💡 Tip: Avoid new positions before earnings_"

    return msg


def check_earnings_soon(tickers, days=3):
    """
    Check if any tickers have earnings in next N days.

    Returns dict of {ticker: days_until}
    """
    earnings_soon = {}

    for ticker in tickers:
        try:
            date = get_earnings_date(ticker)
            if date:
                days_until = (date - datetime.now().date()).days
                if 0 <= days_until <= days:
                    earnings_soon[ticker] = days_until
        except:
            pass

    return earnings_soon
