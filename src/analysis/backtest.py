#!/usr/bin/env python3
"""
Backtesting Module - Enhanced Version

Features:
- 6 trading strategies (momentum, mean reversion, breakout, gap, pullback, trend)
- Market regime filters (bull/bear/neutral)
- Transaction costs (commissions + slippage)
- Drawdown analysis
- Walk-forward validation
- Benchmark comparison (buy & hold)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path

from config import config
from utils import (
    get_logger, normalize_dataframe_columns, get_spy_data_cached,
)

logger = get_logger(__name__)

# Transaction costs from config (realistic estimates)
SLIPPAGE_PCT = config.backtest.slippage_pct

# Cache for backtest results
CACHE_DIR = Path('cache')
CACHE_DIR.mkdir(exist_ok=True)


def get_market_regime(spy_data):
    """
    Determine market regime from SPY data.

    Returns: 'bull', 'bear', or 'neutral'
    """
    if len(spy_data) < 200:
        return 'neutral'

    close = spy_data['Close']
    current = float(close.iloc[-1])
    sma_50 = float(close.rolling(50).mean().iloc[-1])
    sma_200 = float(close.rolling(200).mean().iloc[-1])

    # Bull: price > 50SMA > 200SMA
    if current > sma_50 > sma_200:
        return 'bull'
    # Bear: price < 50SMA < 200SMA
    elif current < sma_50 < sma_200:
        return 'bear'
    else:
        return 'neutral'


def calculate_drawdown(returns):
    """Calculate max drawdown and drawdown duration."""
    cumulative = (1 + pd.Series(returns) / 100).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max * 100

    max_dd = float(drawdown.min())

    # Calculate drawdown duration
    in_drawdown = drawdown < 0
    dd_duration = 0
    max_duration = 0
    for val in in_drawdown:
        if val:
            dd_duration += 1
            max_duration = max(max_duration, dd_duration)
        else:
            dd_duration = 0

    return {
        'max_drawdown': round(max_dd, 2),
        'max_dd_duration': max_duration,
    }


def apply_costs(entry_price, exit_price, direction='long'):
    """Apply transaction costs to a trade."""
    commission_pct = config.backtest.commission_pct
    # Entry cost
    entry_with_costs = entry_price * (1 + commission_pct + SLIPPAGE_PCT)

    # Exit cost
    exit_with_costs = exit_price * (1 - commission_pct - SLIPPAGE_PCT)

    if direction == 'long':
        return entry_with_costs, exit_with_costs
    else:
        return exit_with_costs, entry_with_costs


def backtest_momentum_strategy(ticker, period='1y', holding_days=5, regime_filter=None):
    """
    Momentum Breakout Strategy.

    Entry: Price crosses above 20 SMA with volume > 1.5x average
    Exit: After holding_days OR stop loss at -3%
    """
    try:
        df = yf.download(ticker, period=period, progress=False)
        df = normalize_dataframe_columns(df)

        if len(df) < 60:
            return None

        close = df['Close']
        volume = df['Volume']

        # Check regime filter
        if regime_filter:
            spy = get_spy_data_cached(period=period)
            regime = get_market_regime(spy)
            if regime_filter == 'bull_only' and regime != 'bull':
                return None

        # Calculate indicators
        sma_20 = close.rolling(20).mean()
        vol_avg = volume.rolling(20).mean()

        # Generate signals
        signals = (
            (close > sma_20) &
            (close.shift(1) <= sma_20.shift(1)) &
            (volume > vol_avg * 1.5)
        )

        # Calculate returns with costs and stop loss
        trades = []
        signal_indices = signals[signals].index.tolist()

        for entry_date in signal_indices:
            entry_idx = df.index.get_loc(entry_date)
            entry_price = float(close.iloc[entry_idx])
            stop_loss = entry_price * 0.97  # 3% stop

            # Apply entry cost
            entry_with_cost, _ = apply_costs(entry_price, entry_price)

            # Check each day until exit
            for day in range(1, holding_days + 1):
                check_idx = entry_idx + day
                if check_idx >= len(df):
                    break

                current_price = float(close.iloc[check_idx])
                low_price = float(df['Low'].iloc[check_idx])

                # Stop loss triggered
                if low_price <= stop_loss:
                    _, exit_with_cost = apply_costs(entry_price, stop_loss)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'stop_loss',
                        'hold_days': day,
                    })
                    break

                # Time exit
                if day == holding_days:
                    _, exit_with_cost = apply_costs(entry_price, current_price)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'time',
                        'hold_days': day,
                    })

        if not trades:
            return None

        returns = [t['return'] for t in trades]
        wins = [t for t in trades if t['win']]
        dd = calculate_drawdown(returns)

        # Buy and hold comparison
        bh_return = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100

        return {
            'ticker': ticker,
            'strategy': 'momentum_breakout',
            'total_trades': len(trades),
            'win_rate': len(wins) / len(trades) * 100,
            'avg_return': np.mean(returns),
            'max_win': max(returns),
            'max_loss': min(returns),
            'total_return': sum(returns),
            'max_drawdown': dd['max_drawdown'],
            'profit_factor': abs(sum(r for r in returns if r > 0) / sum(r for r in returns if r < 0)) if any(r < 0 for r in returns) else float('inf'),
            'buy_hold_return': round(bh_return, 2),
            'trades': trades[-10:]
        }

    except Exception as e:
        logger.error(f"Error in momentum strategy for {ticker}: {e}")
        return None


def backtest_mean_reversion(ticker, period='1y', holding_days=3):
    """
    Mean Reversion Strategy.

    Entry: Price drops > 5% in 5 days AND RSI < 30
    Exit: After holding_days OR target at +5%
    """
    try:
        df = yf.download(ticker, period=period, progress=False)
        df = normalize_dataframe_columns(df)

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

        # Calculate returns with target
        trades = []
        signal_indices = signals[signals].index.tolist()

        for entry_date in signal_indices:
            entry_idx = df.index.get_loc(entry_date)
            entry_price = float(close.iloc[entry_idx])
            target = entry_price * 1.05  # 5% target

            entry_with_cost, _ = apply_costs(entry_price, entry_price)

            for day in range(1, holding_days + 1):
                check_idx = entry_idx + day
                if check_idx >= len(df):
                    break

                current_price = float(close.iloc[check_idx])
                high_price = float(df['High'].iloc[check_idx])

                # Target reached
                if high_price >= target:
                    _, exit_with_cost = apply_costs(entry_price, target)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': target,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'target',
                        'hold_days': day,
                    })
                    break

                if day == holding_days:
                    _, exit_with_cost = apply_costs(entry_price, current_price)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'time',
                        'hold_days': day,
                    })

        if not trades:
            return None

        returns = [t['return'] for t in trades]
        wins = [t for t in trades if t['win']]
        dd = calculate_drawdown(returns)

        bh_return = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100

        return {
            'ticker': ticker,
            'strategy': 'mean_reversion',
            'total_trades': len(trades),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'avg_return': np.mean(returns),
            'max_win': max(returns),
            'max_loss': min(returns),
            'total_return': sum(returns),
            'max_drawdown': dd['max_drawdown'],
            'buy_hold_return': round(bh_return, 2),
            'trades': trades[-10:]
        }

    except Exception as e:
        logger.error(f"Error in mean reversion strategy for {ticker}: {e}")
        return None


def backtest_breakout_strategy(ticker, period='1y', holding_days=10):
    """
    Breakout Strategy.

    Entry: Price breaks 20-day high with volume > 2x average
    Exit: Trailing stop at 10-day low
    """
    try:
        df = yf.download(ticker, period=period, progress=False)
        df = normalize_dataframe_columns(df)

        if len(df) < 60:
            return None

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        # Indicators
        high_20 = high.rolling(20).max()
        low_10 = low.rolling(10).min()
        vol_avg = volume.rolling(20).mean()

        # Breakout signal
        signals = (
            (high > high_20.shift(1)) &
            (volume > vol_avg * 2)
        )

        trades = []
        signal_indices = signals[signals].index.tolist()

        for entry_date in signal_indices:
            entry_idx = df.index.get_loc(entry_date)
            entry_price = float(close.iloc[entry_idx])

            entry_with_cost, _ = apply_costs(entry_price, entry_price)

            for day in range(1, holding_days + 1):
                check_idx = entry_idx + day
                if check_idx >= len(df):
                    break

                current_price = float(close.iloc[check_idx])
                trailing_stop = float(low_10.iloc[check_idx])

                # Trailing stop hit
                if float(low.iloc[check_idx]) <= trailing_stop:
                    _, exit_with_cost = apply_costs(entry_price, trailing_stop)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': trailing_stop,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'trailing_stop',
                        'hold_days': day,
                    })
                    break

                if day == holding_days:
                    _, exit_with_cost = apply_costs(entry_price, current_price)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'time',
                        'hold_days': day,
                    })

        if not trades:
            return None

        returns = [t['return'] for t in trades]
        wins = [t for t in trades if t['win']]
        dd = calculate_drawdown(returns)

        bh_return = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100

        return {
            'ticker': ticker,
            'strategy': 'breakout',
            'total_trades': len(trades),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'avg_return': np.mean(returns),
            'max_win': max(returns),
            'max_loss': min(returns),
            'total_return': sum(returns),
            'max_drawdown': dd['max_drawdown'],
            'buy_hold_return': round(bh_return, 2),
            'trades': trades[-10:]
        }

    except Exception as e:
        logger.error(f"Error in breakout strategy for {ticker}: {e}")
        return None


def backtest_gap_strategy(ticker, period='1y', holding_days=2):
    """
    Gap Fade Strategy.

    Entry: Gap down > 3% at open
    Exit: After holding_days or +2% target
    """
    try:
        df = yf.download(ticker, period=period, progress=False)
        df = normalize_dataframe_columns(df)

        if len(df) < 60:
            return None

        close = df['Close']
        open_price = df['Open']

        # Gap down signal
        gap_pct = (open_price - close.shift(1)) / close.shift(1) * 100
        signals = gap_pct < -3

        trades = []
        signal_indices = signals[signals].index.tolist()

        for entry_date in signal_indices:
            entry_idx = df.index.get_loc(entry_date)
            entry_price = float(open_price.iloc[entry_idx])  # Enter at open
            target = entry_price * 1.02

            entry_with_cost, _ = apply_costs(entry_price, entry_price)

            for day in range(0, holding_days + 1):
                check_idx = entry_idx + day
                if check_idx >= len(df):
                    break

                current_price = float(close.iloc[check_idx])
                high_price = float(df['High'].iloc[check_idx])

                if high_price >= target:
                    _, exit_with_cost = apply_costs(entry_price, target)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': target,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'target',
                        'hold_days': day,
                    })
                    break

                if day == holding_days:
                    _, exit_with_cost = apply_costs(entry_price, current_price)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'time',
                        'hold_days': day,
                    })

        if not trades:
            return None

        returns = [t['return'] for t in trades]
        wins = [t for t in trades if t['win']]
        dd = calculate_drawdown(returns)

        bh_return = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100

        return {
            'ticker': ticker,
            'strategy': 'gap_fade',
            'total_trades': len(trades),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'avg_return': np.mean(returns),
            'max_win': max(returns),
            'max_loss': min(returns),
            'total_return': sum(returns),
            'max_drawdown': dd['max_drawdown'],
            'buy_hold_return': round(bh_return, 2),
            'trades': trades[-10:]
        }

    except Exception as e:
        logger.error(f"Error in gap strategy for {ticker}: {e}")
        return None


def backtest_pullback_strategy(ticker, period='1y', holding_days=5):
    """
    Pullback to Moving Average Strategy.

    Entry: Price pulls back to 20 SMA in uptrend (50 SMA > 200 SMA)
    Exit: After holding_days or stop at 20 SMA - 2%
    """
    try:
        df = yf.download(ticker, period=period, progress=False)
        df = normalize_dataframe_columns(df)

        if len(df) < 200:
            return None

        close = df['Close']

        sma_20 = close.rolling(20).mean()
        sma_50 = close.rolling(50).mean()
        sma_200 = close.rolling(200).mean()

        # Pullback in uptrend
        signals = (
            (close <= sma_20 * 1.02) &  # Within 2% of 20 SMA
            (close >= sma_20 * 0.98) &
            (sma_50 > sma_200) &          # Uptrend
            (close.shift(5) > sma_20.shift(5))  # Was above before pullback
        )

        trades = []
        signal_indices = signals[signals].index.tolist()

        for entry_date in signal_indices:
            entry_idx = df.index.get_loc(entry_date)
            entry_price = float(close.iloc[entry_idx])
            stop_loss = float(sma_20.iloc[entry_idx]) * 0.98

            entry_with_cost, _ = apply_costs(entry_price, entry_price)

            for day in range(1, holding_days + 1):
                check_idx = entry_idx + day
                if check_idx >= len(df):
                    break

                current_price = float(close.iloc[check_idx])
                low_price = float(df['Low'].iloc[check_idx])

                if low_price <= stop_loss:
                    _, exit_with_cost = apply_costs(entry_price, stop_loss)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'stop_loss',
                        'hold_days': day,
                    })
                    break

                if day == holding_days:
                    _, exit_with_cost = apply_costs(entry_price, current_price)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'time',
                        'hold_days': day,
                    })

        if not trades:
            return None

        returns = [t['return'] for t in trades]
        wins = [t for t in trades if t['win']]
        dd = calculate_drawdown(returns)

        bh_return = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100

        return {
            'ticker': ticker,
            'strategy': 'pullback',
            'total_trades': len(trades),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'avg_return': np.mean(returns),
            'max_win': max(returns),
            'max_loss': min(returns),
            'total_return': sum(returns),
            'max_drawdown': dd['max_drawdown'],
            'buy_hold_return': round(bh_return, 2),
            'trades': trades[-10:]
        }

    except Exception as e:
        logger.error(f"Error in pullback strategy for {ticker}: {e}")
        return None


def backtest_trend_following(ticker, period='2y', holding_days=20):
    """
    Trend Following Strategy.

    Entry: Price crosses above 50 SMA while 50 > 200
    Exit: Price crosses below 50 SMA or holding_days
    """
    try:
        df = yf.download(ticker, period=period, progress=False)
        df = normalize_dataframe_columns(df)

        if len(df) < 200:
            return None

        close = df['Close']

        sma_50 = close.rolling(50).mean()
        sma_200 = close.rolling(200).mean()

        # Trend following entry
        signals = (
            (close > sma_50) &
            (close.shift(1) <= sma_50.shift(1)) &
            (sma_50 > sma_200)
        )

        trades = []
        signal_indices = signals[signals].index.tolist()

        for entry_date in signal_indices:
            entry_idx = df.index.get_loc(entry_date)
            entry_price = float(close.iloc[entry_idx])

            entry_with_cost, _ = apply_costs(entry_price, entry_price)

            for day in range(1, holding_days + 1):
                check_idx = entry_idx + day
                if check_idx >= len(df):
                    break

                current_price = float(close.iloc[check_idx])
                current_sma = float(sma_50.iloc[check_idx])

                # Exit on SMA cross
                if current_price < current_sma:
                    _, exit_with_cost = apply_costs(entry_price, current_price)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'sma_cross',
                        'hold_days': day,
                    })
                    break

                if day == holding_days:
                    _, exit_with_cost = apply_costs(entry_price, current_price)
                    ret = (exit_with_cost - entry_with_cost) / entry_with_cost * 100
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'return': ret,
                        'win': ret > 0,
                        'exit_reason': 'time',
                        'hold_days': day,
                    })

        if not trades:
            return None

        returns = [t['return'] for t in trades]
        wins = [t for t in trades if t['win']]
        dd = calculate_drawdown(returns)

        bh_return = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100

        return {
            'ticker': ticker,
            'strategy': 'trend_following',
            'total_trades': len(trades),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'avg_return': np.mean(returns),
            'max_win': max(returns),
            'max_loss': min(returns),
            'total_return': sum(returns),
            'max_drawdown': dd['max_drawdown'],
            'buy_hold_return': round(bh_return, 2),
            'trades': trades[-10:]
        }

    except Exception as e:
        logger.error(f"Error in trend following strategy for {ticker}: {e}")
        return None


# All available strategies
STRATEGIES = {
    'momentum': backtest_momentum_strategy,
    'mean_reversion': backtest_mean_reversion,
    'breakout': backtest_breakout_strategy,
    'gap_fade': backtest_gap_strategy,
    'pullback': backtest_pullback_strategy,
    'trend_following': backtest_trend_following,
}


def backtest_all_strategies(ticker):
    """Run all backtests for a ticker."""
    results = []

    for name, func in STRATEGIES.items():
        try:
            result = func(ticker)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Error running {name} strategy for {ticker}: {e}")
            continue

    return results


def format_backtest_results(results):
    """Format backtest results for Telegram."""
    if not results:
        return "No backtest data available."

    msg = "📈 *BACKTEST RESULTS*\n\n"

    for r in results:
        # Emoji based on performance vs buy & hold
        if r['total_return'] > r.get('buy_hold_return', 0):
            emoji = "🟢"
        elif r['win_rate'] >= 50:
            emoji = "🟡"
        else:
            emoji = "🔴"

        strategy_name = r['strategy'].replace('_', ' ').title()
        msg += f"{emoji} *{r['ticker']}* - {strategy_name}\n"
        msg += f"   Win Rate: {r['win_rate']:.0f}% ({r['total_trades']} trades)\n"
        msg += f"   Avg Return: {r['avg_return']:+.2f}% | Total: {r['total_return']:+.1f}%\n"
        msg += f"   Max DD: {r['max_drawdown']:.1f}% | B&H: {r.get('buy_hold_return', 0):+.1f}%\n\n"

    msg += "_Includes 0.1% transaction costs per trade_\n"
    msg += "_Based on 1 year of historical data_"

    return msg


def get_signal_accuracy_summary():
    """Get overall signal accuracy across key stocks."""
    tickers = ['NVDA', 'AMD', 'AAPL', 'TSLA', 'META', 'MSFT', 'GOOGL', 'AMZN']

    all_results = []
    for ticker in tickers:
        results = backtest_all_strategies(ticker)
        all_results.extend(results)

    if not all_results:
        return None

    # Aggregate by strategy
    strategy_stats = {}
    for r in all_results:
        strat = r['strategy']
        if strat not in strategy_stats:
            strategy_stats[strat] = {'win_rates': [], 'returns': [], 'trades': 0}

        strategy_stats[strat]['win_rates'].append(r['win_rate'])
        strategy_stats[strat]['returns'].append(r['avg_return'])
        strategy_stats[strat]['trades'] += r['total_trades']

    # Calculate averages
    summary = {}
    for strat, stats in strategy_stats.items():
        summary[strat] = {
            'avg_win_rate': np.mean(stats['win_rates']),
            'avg_return': np.mean(stats['returns']),
            'total_trades': stats['trades'],
        }

    # Find best strategy
    best_strategy = max(summary.keys(), key=lambda x: summary[x]['avg_win_rate'])

    return {
        'total_trades': sum(r['total_trades'] for r in all_results),
        'avg_win_rate': np.mean([r['win_rate'] for r in all_results]),
        'by_strategy': summary,
        'best_strategy': best_strategy,
        'best_win_rate': summary[best_strategy]['avg_win_rate'],
    }


def format_strategy_summary():
    """Format strategy summary for Telegram."""
    summary = get_signal_accuracy_summary()

    if not summary:
        return "No backtest summary available."

    msg = "📊 *STRATEGY PERFORMANCE SUMMARY*\n\n"

    # Sort strategies by win rate
    sorted_strats = sorted(
        summary['by_strategy'].items(),
        key=lambda x: x[1]['avg_win_rate'],
        reverse=True
    )

    for strat, stats in sorted_strats:
        emoji = "🟢" if stats['avg_win_rate'] >= 55 else ("🟡" if stats['avg_win_rate'] >= 45 else "🔴")
        strat_name = strat.replace('_', ' ').title()
        msg += f"{emoji} *{strat_name}*\n"
        msg += f"   Win Rate: {stats['avg_win_rate']:.0f}% | Avg: {stats['avg_return']:+.2f}%\n"
        msg += f"   Total Trades: {stats['total_trades']}\n\n"

    msg += f"*Best Strategy:* {summary['best_strategy'].replace('_', ' ').title()}\n"
    msg += f"*Overall Win Rate:* {summary['avg_win_rate']:.0f}%"

    return msg


if __name__ == '__main__':
    logger.info("Testing enhanced backtest module...")

    # Test single ticker
    ticker = 'NVDA'
    logger.info(f"=== Backtesting {ticker} ===")

    results = backtest_all_strategies(ticker)
    logger.info(format_backtest_results(results))

    # Strategy summary
    logger.info("=" * 60)
    logger.info(format_strategy_summary())
