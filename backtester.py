#!/usr/bin/env python3
"""
Backtesting Module - Test how well scanner signals perform historically.

Tests:
1. Breakout signals (buy on breakout, sell after X days)
2. Squeeze signals (buy on squeeze fire, sell after X days)
3. High composite score (buy top ranked, sell after X days)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


def calculate_signals(df):
    """Calculate all signals for a given dataframe."""
    if len(df) < 200:
        return None

    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']

    # MAs
    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()

    # Bollinger Bands
    bb_std = close.rolling(20).std()
    bb_upper = sma_20 + 2 * bb_std
    bb_lower = sma_20 - 2 * bb_std
    bb_width = (bb_upper - bb_lower) / sma_20

    # Squeeze detection (width in bottom 20% of last 100 days)
    squeeze = bb_width.rolling(100).apply(lambda x: (x.iloc[-1] <= np.percentile(x, 20)) if len(x) >= 100 else False)

    # Breakout (close above upper BB)
    breakout = close > bb_upper

    # Trend alignment
    trend_aligned = (sma_20 > sma_50) & (sma_50 > sma_200)
    above_all_ma = (close > sma_20) & (close > sma_50) & (close > sma_200)

    # Volume surge
    vol_sma = volume.rolling(20).mean()
    vol_surge = volume > (vol_sma * 1.5)

    # RS vs SPY
    spy = yf.download('SPY', start=df.index[0], end=df.index[-1], progress=False)
    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)

    # Align indexes
    spy = spy.reindex(df.index, method='ffill')

    stock_ret_20 = close.pct_change(20) * 100
    spy_ret_20 = spy['Close'].pct_change(20) * 100
    rs = stock_ret_20 - spy_ret_20
    strong_rs = rs > 5

    return pd.DataFrame({
        'close': close,
        'breakout': breakout,
        'squeeze': squeeze > 0,
        'squeeze_fire': (squeeze.shift(1) > 0) & (close > bb_upper),  # Squeeze then breakout
        'trend_aligned': trend_aligned,
        'above_all_ma': above_all_ma,
        'vol_surge': vol_surge,
        'strong_rs': strong_rs,
        'rs': rs,
    })


def backtest_signal(df, signal_name, hold_days=10, stop_loss_pct=None, take_profit_pct=None):
    """
    Backtest a specific signal.

    Args:
        df: DataFrame with signals
        signal_name: Column name of signal to test
        hold_days: Days to hold after signal
        stop_loss_pct: Stop loss percentage (e.g., 5 for 5%)
        take_profit_pct: Take profit percentage

    Returns:
        Dictionary with backtest results
    """
    if signal_name not in df.columns:
        return None

    signals = df[df[signal_name] == True].index.tolist()

    trades = []

    for entry_date in signals:
        try:
            entry_idx = df.index.get_loc(entry_date)
            entry_price = df['close'].iloc[entry_idx]

            # Track trade
            exit_idx = min(entry_idx + hold_days, len(df) - 1)
            exit_price = df['close'].iloc[exit_idx]
            exit_date = df.index[exit_idx]
            exit_reason = 'hold_period'

            # Check for stop loss / take profit during hold period
            if stop_loss_pct or take_profit_pct:
                for i in range(entry_idx + 1, exit_idx + 1):
                    price = df['close'].iloc[i]
                    pct_change = (price - entry_price) / entry_price * 100

                    if stop_loss_pct and pct_change <= -stop_loss_pct:
                        exit_price = price
                        exit_date = df.index[i]
                        exit_reason = 'stop_loss'
                        break

                    if take_profit_pct and pct_change >= take_profit_pct:
                        exit_price = price
                        exit_date = df.index[i]
                        exit_reason = 'take_profit'
                        break

            pnl_pct = (exit_price - entry_price) / entry_price * 100

            trades.append({
                'entry_date': entry_date,
                'exit_date': exit_date,
                'entry_price': round(entry_price, 2),
                'exit_price': round(exit_price, 2),
                'pnl_pct': round(pnl_pct, 2),
                'exit_reason': exit_reason,
            })

        except Exception as e:
            continue

    if not trades:
        return None

    # Calculate statistics
    trades_df = pd.DataFrame(trades)

    winners = trades_df[trades_df['pnl_pct'] > 0]
    losers = trades_df[trades_df['pnl_pct'] <= 0]

    return {
        'signal': signal_name,
        'total_trades': len(trades),
        'winners': len(winners),
        'losers': len(losers),
        'win_rate': round(len(winners) / len(trades) * 100, 1),
        'avg_win': round(winners['pnl_pct'].mean(), 2) if len(winners) > 0 else 0,
        'avg_loss': round(losers['pnl_pct'].mean(), 2) if len(losers) > 0 else 0,
        'avg_pnl': round(trades_df['pnl_pct'].mean(), 2),
        'total_pnl': round(trades_df['pnl_pct'].sum(), 2),
        'max_win': round(trades_df['pnl_pct'].max(), 2),
        'max_loss': round(trades_df['pnl_pct'].min(), 2),
        'profit_factor': round(abs(winners['pnl_pct'].sum() / losers['pnl_pct'].sum()), 2) if len(losers) > 0 and losers['pnl_pct'].sum() != 0 else 0,
        'trades': trades[-10:],  # Last 10 trades
    }


def run_backtest(tickers, period='2y', hold_days=10):
    """
    Run backtest on multiple tickers.
    """
    print(f"Running backtest on {len(tickers)} tickers...")
    print(f"Period: {period}, Hold Days: {hold_days}")
    print("=" * 60)

    all_results = {
        'breakout': [],
        'squeeze_fire': [],
        'trend_aligned': [],
        'strong_rs': [],
    }

    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if len(df) < 200:
                continue

            signals_df = calculate_signals(df)
            if signals_df is None:
                continue

            for signal in all_results.keys():
                result = backtest_signal(signals_df, signal, hold_days=hold_days)
                if result:
                    result['ticker'] = ticker
                    all_results[signal].append(result)

        except Exception as e:
            continue

    # Aggregate results
    summary = {}

    for signal, results in all_results.items():
        if not results:
            continue

        total_trades = sum(r['total_trades'] for r in results)
        total_winners = sum(r['winners'] for r in results)
        total_pnl = sum(r['total_pnl'] for r in results)

        if total_trades == 0:
            continue

        summary[signal] = {
            'total_trades': total_trades,
            'win_rate': round(total_winners / total_trades * 100, 1),
            'avg_pnl_per_trade': round(total_pnl / total_trades, 2),
            'total_pnl': round(total_pnl, 2),
            'tickers_tested': len(results),
        }

        print(f"\n{signal.upper()}")
        print(f"  Trades: {total_trades}")
        print(f"  Win Rate: {summary[signal]['win_rate']}%")
        print(f"  Avg PnL/Trade: {summary[signal]['avg_pnl_per_trade']}%")
        print(f"  Total PnL: {summary[signal]['total_pnl']}%")

    return summary, all_results


def format_backtest_report(summary):
    """Format backtest results for Telegram."""
    msg = "📈 *BACKTEST RESULTS*\n"
    msg += f"_Period: 2 Years | Hold: 10 Days_\n\n"

    for signal, data in summary.items():
        emoji = "✅" if data['avg_pnl_per_trade'] > 0 else "❌"
        msg += f"{emoji} *{signal.replace('_', ' ').title()}*\n"
        msg += f"   Trades: {data['total_trades']} | Win: {data['win_rate']}%\n"
        msg += f"   Avg PnL: {data['avg_pnl_per_trade']:+.2f}%\n\n"

    # Recommendation
    best_signal = max(summary.items(), key=lambda x: x[1]['avg_pnl_per_trade'])
    msg += f"🏆 *Best Signal:* {best_signal[0].replace('_', ' ').title()}\n"
    msg += f"   ({best_signal[1]['avg_pnl_per_trade']:+.2f}% avg per trade)"

    return msg


# Test tickers
TEST_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'AVGO', 'CRM',
    'NFLX', 'ADBE', 'ORCL', 'CSCO', 'INTC', 'QCOM', 'TXN', 'MU', 'AMAT', 'LRCX',
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'V', 'MA', 'PYPL', 'AXP', 'BLK',
    'UNH', 'JNJ', 'PFE', 'ABBV', 'MRK', 'LLY', 'TMO', 'DHR', 'BMY', 'AMGN',
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'VLO', 'PSX', 'OXY', 'DVN',
]


if __name__ == '__main__':
    summary, details = run_backtest(TEST_TICKERS, period='2y', hold_days=10)

    print("\n" + "=" * 60)
    print("TELEGRAM MESSAGE:")
    print("=" * 60)
    print(format_backtest_report(summary))

    # Save results
    with open('backtest_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print("\nResults saved to backtest_results.json")
