#!/usr/bin/env python3
"""
Advanced Chart Generation

Candlestick charts with volume, moving averages, and key levels.
"""

import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import pandas as pd
import numpy as np


def generate_candlestick_chart(ticker, df, days=60):
    """
    Generate professional candlestick chart with volume.

    Args:
        ticker: Stock symbol
        df: DataFrame with OHLCV data
        days: Number of days to show

    Returns:
        BytesIO buffer with PNG image
    """
    try:
        # Prepare data
        df = df.iloc[-days:].copy()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(
            2, 1,
            figsize=(12, 8),
            gridspec_kw={'height_ratios': [3, 1]},
            facecolor='#0d1117'
        )

        ax1.set_facecolor('#0d1117')
        ax2.set_facecolor('#0d1117')

        # Convert index to numbers for plotting
        df = df.reset_index()
        df['date_num'] = range(len(df))

        # Draw candlesticks
        width = 0.6
        for idx, row in df.iterrows():
            date_num = row['date_num']
            open_p = row['Open']
            high = row['High']
            low = row['Low']
            close = row['Close']

            # Determine color
            if close >= open_p:
                color = '#00b894'  # Green
                body_bottom = open_p
                body_height = close - open_p
            else:
                color = '#e74c3c'  # Red
                body_bottom = close
                body_height = open_p - close

            # Draw wick
            ax1.plot([date_num, date_num], [low, high], color=color, linewidth=1)

            # Draw body
            rect = Rectangle(
                (date_num - width/2, body_bottom),
                width,
                body_height if body_height > 0 else 0.01,
                facecolor=color,
                edgecolor=color
            )
            ax1.add_patch(rect)

        # Add moving averages
        close = df['Close']

        if len(close) >= 20:
            sma_20 = close.rolling(20).mean()
            ax1.plot(df['date_num'], sma_20, color='#f39c12', linewidth=1.5, label='20 SMA', alpha=0.8)

        if len(close) >= 50:
            sma_50 = close.rolling(50).mean()
            ax1.plot(df['date_num'], sma_50, color='#3498db', linewidth=1.5, label='50 SMA', alpha=0.8)

        # Current price line
        current = float(close.iloc[-1])
        ax1.axhline(y=current, color='white', linestyle='--', linewidth=0.8, alpha=0.5)
        ax1.text(len(df) + 0.5, current, f'${current:.2f}', color='white', fontsize=9, va='center')

        # Volume bars
        colors = ['#00b894' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#e74c3c'
                  for i in range(len(df))]
        ax2.bar(df['date_num'], df['Volume'], color=colors, alpha=0.7, width=0.8)

        # Volume average
        vol_avg = df['Volume'].rolling(20).mean()
        ax2.plot(df['date_num'], vol_avg, color='#f39c12', linewidth=1, alpha=0.8)

        # Styling
        ax1.set_title(f'{ticker} - {days} Day Chart', color='white', fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left', facecolor='#0d1117', edgecolor='#0d1117', labelcolor='white')

        # Format x-axis with dates
        tick_positions = range(0, len(df), max(1, len(df) // 6))
        tick_labels = [df.iloc[i]['Date'].strftime('%m/%d') if 'Date' in df.columns
                       else str(i) for i in tick_positions]
        ax1.set_xticks(list(tick_positions))
        ax1.set_xticklabels([])  # Hide on top chart
        ax2.set_xticks(list(tick_positions))
        ax2.set_xticklabels(tick_labels, color='white', fontsize=8)

        # Y-axis formatting
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:.0f}'))
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))

        for ax in [ax1, ax2]:
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('#333')
            ax.spines['left'].set_color('#333')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, alpha=0.2, color='#333')

        ax2.set_xlabel('Date', color='white', fontsize=10)
        ax1.set_ylabel('Price', color='white', fontsize=10)
        ax2.set_ylabel('Volume', color='white', fontsize=10)

        plt.tight_layout()

        # Save to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#0d1117')
        buf.seek(0)
        plt.close(fig)

        return buf

    except Exception as e:
        print(f"Chart error: {e}")
        return None


def generate_portfolio_chart(positions, prices):
    """
    Generate portfolio allocation pie chart.

    Args:
        positions: List of position dicts
        prices: Dict of current prices {ticker: price}

    Returns:
        BytesIO buffer with PNG image
    """
    try:
        if not positions:
            return None

        # Calculate values
        values = []
        labels = []
        colors_list = []

        color_palette = ['#00b894', '#3498db', '#f39c12', '#e74c3c', '#9b59b6',
                        '#1abc9c', '#e67e22', '#2ecc71', '#e91e63', '#00bcd4']

        for i, pos in enumerate(positions):
            ticker = pos['ticker']
            current_price = prices.get(ticker, pos['entry_price'])
            value = pos['shares'] * current_price
            values.append(value)
            labels.append(f"{ticker}\n${value:,.0f}")
            colors_list.append(color_palette[i % len(color_palette)])

        # Create pie chart
        fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0d1117')
        ax.set_facecolor('#0d1117')

        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            colors=colors_list,
            textprops={'color': 'white'},
            wedgeprops={'edgecolor': '#0d1117', 'linewidth': 2}
        )

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)

        total = sum(values)
        ax.set_title(f'Portfolio: ${total:,.0f}', color='white', fontsize=14, fontweight='bold')

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#0d1117')
        buf.seek(0)
        plt.close(fig)

        return buf

    except Exception as e:
        print(f"Portfolio chart error: {e}")
        return None


def generate_performance_chart(trades):
    """
    Generate cumulative P&L chart from trades.

    Args:
        trades: List of closed trade dicts

    Returns:
        BytesIO buffer with PNG image
    """
    try:
        if not trades or len(trades) < 2:
            return None

        # Calculate cumulative P&L
        pnl_list = [t.get('pnl_dollars', 0) for t in trades]
        cumulative = np.cumsum(pnl_list)
        dates = range(len(trades))

        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0d1117')
        ax.set_facecolor('#0d1117')

        # Color based on positive/negative
        colors = ['#00b894' if c >= 0 else '#e74c3c' for c in cumulative]

        ax.fill_between(dates, 0, cumulative, alpha=0.3,
                       color='#00b894' if cumulative[-1] >= 0 else '#e74c3c')
        ax.plot(dates, cumulative, color='#00b894' if cumulative[-1] >= 0 else '#e74c3c',
               linewidth=2)

        ax.axhline(y=0, color='white', linestyle='--', linewidth=0.5, alpha=0.5)

        ax.set_title(f'Cumulative P&L: ${cumulative[-1]:,.0f}', color='white', fontsize=14)
        ax.set_xlabel('Trade #', color='white')
        ax.set_ylabel('P&L ($)', color='white')

        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('#333')
        ax.spines['left'].set_color('#333')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, alpha=0.2)

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#0d1117')
        buf.seek(0)
        plt.close(fig)

        return buf

    except Exception as e:
        print(f"Performance chart error: {e}")
        return None
