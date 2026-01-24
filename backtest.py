#!/usr/bin/env python3
"""
Backtesting Module

Tests signal accuracy on historical data.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def backtest_momentum_strategy(ticker, period='1y', holding_days=5):
    """
    Backtest simple momentum strategy.

    Entry: Price crosses above 20 SMA with volume > 1.5x average
    Exit: After holding_days

    Returns dict with stats.
    """
    try:
        df = yf.download(ticker, period=period, progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if len(df) < 60:
            return None

        close = df['Close']
        volume = df['Volume']

        # Calculate indicators
        sma_20 = close.rolling(20).mean()
        vol_avg = volume.rolling(20).mean()

        # Generate signals
        signals = (
            (close > sma_20) &
            (close.shift(1) <= sma_20.shift(1)) &
            (volume > vol_avg * 1.5)
        )

        # Calculate returns
        trades = []
        signal_indices = signals[signals].index.tolist()

        for entry_date in signal_indices:
            entry_idx = df.index.get_loc(entry_date)
            exit_idx = min(entry_idx + holding_days, len(df) - 1)

            entry_price = float(close.iloc[entry_idx])
            exit_price = float(close.iloc[exit_idx])
            ret = (exit_price - entry_price) / entry_price * 100

            trades.append({
                'entry_date': entry_date,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'return': ret,
                'win': ret > 0
            })

        if not trades:
            return None

        # Calculate stats
        returns = [t['return'] for t in trades]
        wins = [t for t in trades if t['win']]

        return {
            'ticker': ticker,
            'strategy': 'momentum_breakout',
            'total_trades': len(trades),
            'win_rate': len(wins) / len(trades) * 100,
            'avg_return': np.mean(returns),
            'max_win': max(returns),
            'max_loss': min(returns),
            'total_return': sum(returns),
            'profit_factor': abs(sum(r for r in returns if r > 0) / sum(r for r in returns if r < 0)) if any(r < 0 for r in returns) else float('inf'),
            'trades': trades[-10:]  # Last 10 trades
        }

    except Exception as e:
        print(f"Backtest error for {ticker}: {e}")
        return None


def backtest_mean_reversion(ticker, period='1y', holding_days=3):
    """
    Backtest mean reversion strategy.

    Entry: Price drops > 5% in 5 days AND RSI < 30
    Exit: After holding_days
    """
    try:
        df = yf.download(ticker, period=period, progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if len(df) < 60:
            return None

        close = df['Close']

        # Calculate RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # Calculate 5-day return
        ret_5d = (close - close.shift(5)) / close.shift(5) * 100

        # Generate signals
        signals = (ret_5d < -5) & (rsi < 30)

        # Calculate returns
        trades = []
        signal_indices = signals[signals].index.tolist()

        for entry_date in signal_indices:
            entry_idx = df.index.get_loc(entry_date)
            exit_idx = min(entry_idx + holding_days, len(df) - 1)

            entry_price = float(close.iloc[entry_idx])
            exit_price = float(close.iloc[exit_idx])
            ret = (exit_price - entry_price) / entry_price * 100

            trades.append({
                'entry_date': entry_date,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'return': ret,
                'win': ret > 0
            })

        if not trades:
            return None

        returns = [t['return'] for t in trades]
        wins = [t for t in trades if t['win']]

        return {
            'ticker': ticker,
            'strategy': 'mean_reversion',
            'total_trades': len(trades),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'avg_return': np.mean(returns),
            'max_win': max(returns),
            'max_loss': min(returns),
            'total_return': sum(returns),
            'trades': trades[-10:]
        }

    except Exception as e:
        return None


def backtest_all_strategies(ticker):
    """Run all backtests for a ticker."""
    results = []

    momentum = backtest_momentum_strategy(ticker)
    if momentum:
        results.append(momentum)

    mean_rev = backtest_mean_reversion(ticker)
    if mean_rev:
        results.append(mean_rev)

    return results


def format_backtest_results(results):
    """Format backtest results for Telegram."""
    if not results:
        return "No backtest data available."

    msg = "📈 *BACKTEST RESULTS*\n\n"

    for r in results:
        emoji = "🟢" if r['win_rate'] >= 50 else "🟡" if r['win_rate'] >= 40 else "🔴"

        msg += f"{emoji} *{r['ticker']}* - {r['strategy'].replace('_', ' ').title()}\n"
        msg += f"   Win Rate: {r['win_rate']:.0f}% ({r['total_trades']} trades)\n"
        msg += f"   Avg Return: {r['avg_return']:+.1f}%\n"
        msg += f"   Best: {r['max_win']:+.1f}% | Worst: {r['max_loss']:+.1f}%\n\n"

    msg += "_Based on 1 year of historical data_"

    return msg


def get_signal_accuracy_summary():
    """Get overall signal accuracy across key stocks."""
    tickers = ['NVDA', 'AMD', 'AAPL', 'TSLA', 'META', 'MSFT']

    all_results = []
    for ticker in tickers:
        results = backtest_all_strategies(ticker)
        all_results.extend(results)

    if not all_results:
        return None

    # Aggregate stats
    total_trades = sum(r['total_trades'] for r in all_results)
    avg_win_rate = np.mean([r['win_rate'] for r in all_results])

    momentum_results = [r for r in all_results if r['strategy'] == 'momentum_breakout']
    mean_rev_results = [r for r in all_results if r['strategy'] == 'mean_reversion']

    return {
        'total_trades': total_trades,
        'avg_win_rate': avg_win_rate,
        'momentum_win_rate': np.mean([r['win_rate'] for r in momentum_results]) if momentum_results else 0,
        'mean_rev_win_rate': np.mean([r['win_rate'] for r in mean_rev_results]) if mean_rev_results else 0,
        'best_ticker': max(all_results, key=lambda x: x['win_rate'])['ticker'] if all_results else None,
    }
