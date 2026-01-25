#!/usr/bin/env python3
"""
Stock Scanner Web Dashboard

Modern, interactive dashboard that displays:
- Top stocks with scores
- Hot themes/stories
- Sector rotation
- News sentiment
- Market breadth
- AI insights

Generates static HTML for GitHub Pages.
Syncs with Telegram bot data.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Try to import dependencies, fail gracefully
try:
    import pandas as pd
except ImportError:
    pd = None


DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Scanner Dashboard</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📊</text></svg>">
    <style>
        :root {
            --bg-dark: #0a0a0f;
            --bg-card: #12121a;
            --bg-card-hover: #1a1a25;
            --bg-accent: #1e1e2e;
            --border: #2a2a3a;
            --text: #e4e4e7;
            --text-dim: #71717a;
            --green: #22c55e;
            --green-dim: rgba(34, 197, 94, 0.15);
            --red: #ef4444;
            --red-dim: rgba(239, 68, 68, 0.15);
            --blue: #3b82f6;
            --blue-dim: rgba(59, 130, 246, 0.15);
            --purple: #a855f7;
            --purple-dim: rgba(168, 85, 247, 0.15);
            --orange: #f97316;
            --orange-dim: rgba(249, 115, 22, 0.15);
            --yellow: #eab308;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            line-height: 1.5;
            min-height: 100vh;
        }

        /* Navbar */
        .navbar {
            background: var(--bg-card);
            border-bottom: 1px solid var(--border);
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(10px);
        }

        .navbar-content {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.25rem;
            font-weight: 700;
        }

        .logo-icon {
            font-size: 1.5rem;
        }

        .nav-links {
            display: flex;
            gap: 8px;
        }

        .nav-link {
            padding: 8px 16px;
            border-radius: 8px;
            color: var(--text-dim);
            text-decoration: none;
            font-size: 0.875rem;
            transition: all 0.2s;
        }

        .nav-link:hover {
            background: var(--bg-accent);
            color: var(--text);
        }

        .nav-link.active {
            background: var(--blue-dim);
            color: var(--blue);
        }

        .telegram-btn {
            background: linear-gradient(135deg, #0088cc, #00a8e8);
            color: white;
            padding: 8px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .telegram-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 136, 204, 0.4);
        }

        /* Main Container */
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 24px;
        }

        /* Stats Bar */
        .stats-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: transform 0.2s, border-color 0.2s;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            border-color: var(--blue);
        }

        .stat-label {
            color: var(--text-dim);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
        }

        .stat-value.green { color: var(--green); }
        .stat-value.red { color: var(--red); }
        .stat-value.blue { color: var(--blue); }
        .stat-value.purple { color: var(--purple); }
        .stat-value.orange { color: var(--orange); }

        .stat-change {
            font-size: 0.875rem;
            margin-top: 4px;
        }

        /* Grid Layout */
        .grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 20px;
        }

        .col-8 { grid-column: span 8; }
        .col-6 { grid-column: span 6; }
        .col-4 { grid-column: span 4; }
        .col-12 { grid-column: span 12; }

        @media (max-width: 1200px) {
            .col-8, .col-6, .col-4 { grid-column: span 12; }
        }

        /* Cards */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
        }

        .card-header {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .card-title {
            font-size: 1rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .card-title-icon {
            font-size: 1.25rem;
        }

        .card-badge {
            background: var(--bg-accent);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            color: var(--text-dim);
        }

        .card-body {
            padding: 20px 24px;
        }

        /* Tables */
        .table {
            width: 100%;
            border-collapse: collapse;
        }

        .table th {
            text-align: left;
            padding: 12px 16px;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-dim);
            font-weight: 500;
            border-bottom: 1px solid var(--border);
        }

        .table td {
            padding: 16px;
            border-bottom: 1px solid var(--border);
            font-size: 0.875rem;
        }

        .table tr:last-child td {
            border-bottom: none;
        }

        .table tr:hover {
            background: var(--bg-card-hover);
        }

        .ticker {
            font-weight: 600;
            color: var(--blue);
            font-family: 'SF Mono', Monaco, monospace;
        }

        .positive { color: var(--green); }
        .negative { color: var(--red); }

        /* Score Bar */
        .score-container {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .score-bar {
            flex: 1;
            height: 6px;
            background: var(--bg-accent);
            border-radius: 3px;
            overflow: hidden;
        }

        .score-fill {
            height: 100%;
            border-radius: 3px;
            background: linear-gradient(90deg, var(--green), var(--blue));
        }

        /* Theme Tags */
        .themes-container {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .theme-tag {
            padding: 10px 16px;
            border-radius: 10px;
            font-size: 0.875rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: transform 0.2s;
            cursor: default;
        }

        .theme-tag:hover {
            transform: scale(1.05);
        }

        .theme-hot {
            background: var(--orange-dim);
            color: var(--orange);
            border: 1px solid var(--orange);
        }

        .theme-warm {
            background: var(--yellow);
            background: rgba(234, 179, 8, 0.15);
            color: var(--yellow);
            border: 1px solid var(--yellow);
        }

        .theme-neutral {
            background: var(--bg-accent);
            color: var(--text-dim);
            border: 1px solid var(--border);
        }

        .theme-count {
            background: rgba(255,255,255,0.15);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
        }

        /* Sentiment Bars */
        .sentiment-row {
            display: flex;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }

        .sentiment-row:last-child {
            border-bottom: none;
        }

        .sentiment-ticker {
            width: 60px;
            font-weight: 600;
            font-family: 'SF Mono', Monaco, monospace;
        }

        .sentiment-bar-container {
            flex: 1;
            display: flex;
            height: 24px;
            border-radius: 6px;
            overflow: hidden;
            margin: 0 16px;
        }

        .sentiment-bullish {
            background: var(--green);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .sentiment-bearish {
            background: var(--red);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .sentiment-label {
            font-size: 0.75rem;
            padding: 4px 10px;
            border-radius: 4px;
            font-weight: 600;
        }

        .sentiment-label.bullish { background: var(--green-dim); color: var(--green); }
        .sentiment-label.bearish { background: var(--red-dim); color: var(--red); }
        .sentiment-label.neutral { background: var(--bg-accent); color: var(--text-dim); }

        /* Breadth Meters */
        .breadth-item {
            margin-bottom: 16px;
        }

        .breadth-item:last-child {
            margin-bottom: 0;
        }

        .breadth-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 0.875rem;
        }

        .breadth-bar {
            height: 12px;
            background: var(--bg-accent);
            border-radius: 6px;
            overflow: hidden;
        }

        .breadth-fill {
            height: 100%;
            border-radius: 6px;
            transition: width 0.5s ease;
        }

        /* AI Insights */
        .ai-insight {
            background: linear-gradient(135deg, var(--purple-dim), var(--blue-dim));
            border: 1px solid var(--purple);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
        }

        .ai-insight:last-child {
            margin-bottom: 0;
        }

        .ai-insight-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
            font-weight: 600;
        }

        .ai-insight-text {
            color: var(--text-dim);
            font-size: 0.875rem;
            line-height: 1.6;
        }

        /* Command Card */
        .command-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
        }

        .command-item {
            background: var(--bg-accent);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            transition: all 0.2s;
        }

        .command-item:hover {
            border-color: var(--blue);
            background: var(--blue-dim);
        }

        .command-name {
            font-family: 'SF Mono', Monaco, monospace;
            font-weight: 600;
            color: var(--blue);
            margin-bottom: 6px;
        }

        .command-desc {
            font-size: 0.75rem;
            color: var(--text-dim);
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 40px 24px;
            color: var(--text-dim);
            font-size: 0.875rem;
        }

        .footer a {
            color: var(--blue);
            text-decoration: none;
        }

        /* Pulse Animation */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .live-dot {
            width: 8px;
            height: 8px;
            background: var(--green);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        /* Refresh timestamp */
        .refresh-info {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.75rem;
            color: var(--text-dim);
        }
    </style>
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar">
        <div class="navbar-content">
            <div class="logo">
                <span class="logo-icon">📊</span>
                <span>Stock Scanner</span>
            </div>
            <div class="nav-links">
                <a href="#overview" class="nav-link active">Overview</a>
                <a href="#themes" class="nav-link">Themes</a>
                <a href="#sentiment" class="nav-link">Sentiment</a>
                <a href="#commands" class="nav-link">Commands</a>
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                <div class="refresh-info">
                    <div class="live-dot"></div>
                    <span>Updated {{LAST_UPDATE}}</span>
                </div>
                <a href="https://t.me/{{BOT_USERNAME}}" class="telegram-btn" target="_blank">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18 1.897-.962 6.502-1.359 8.627-.168.9-.5 1.201-.82 1.23-.697.064-1.226-.461-1.901-.903-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.139-5.062 3.345-.479.329-.913.489-1.302.481-.428-.009-1.252-.242-1.865-.442-.752-.244-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.831-2.529 6.998-3.015 3.333-1.386 4.025-1.627 4.477-1.635.099-.002.321.023.465.141.121.1.154.234.17.33.015.097.035.311.019.48z"/>
                    </svg>
                    Open Bot
                </a>
            </div>
        </div>
    </nav>

    <div class="container">
        <!-- Stats Overview -->
        <section id="overview">
            <div class="stats-bar">
                <div class="stat-card">
                    <div class="stat-label">Stocks Scanned</div>
                    <div class="stat-value blue">{{TOTAL_SCANNED}}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Active Breakouts</div>
                    <div class="stat-value green">{{BREAKOUTS}}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">In Squeeze</div>
                    <div class="stat-value purple">{{SQUEEZES}}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Market Breadth</div>
                    <div class="stat-value {{BREADTH_CLASS}}">{{BREADTH}}%</div>
                    <div class="stat-change">Above 50 SMA</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Hot Themes</div>
                    <div class="stat-value orange">{{HOT_THEMES}}</div>
                </div>
            </div>

            <div class="grid">
                <!-- Top Stocks -->
                <div class="col-8">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <span class="card-title-icon">🏆</span>
                                Top Momentum Stocks
                            </div>
                            <span class="card-badge">Live Rankings</span>
                        </div>
                        <table class="table">
                            <thead>
                                <tr>
                                    <th style="width: 50px;">#</th>
                                    <th>Ticker</th>
                                    <th>Price</th>
                                    <th>RS vs SPY</th>
                                    <th>Volume</th>
                                    <th style="width: 150px;">Score</th>
                                    <th>Signal</th>
                                </tr>
                            </thead>
                            <tbody>
                                {{TOP_STOCKS_ROWS}}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Market Breadth -->
                <div class="col-4">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <span class="card-title-icon">📊</span>
                                Market Breadth
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="breadth-item">
                                <div class="breadth-label">
                                    <span>Above 20 SMA</span>
                                    <span class="{{ABOVE_20_CLASS}}">{{ABOVE_20}}%</span>
                                </div>
                                <div class="breadth-bar">
                                    <div class="breadth-fill" style="width: {{ABOVE_20}}%; background: var(--blue);"></div>
                                </div>
                            </div>
                            <div class="breadth-item">
                                <div class="breadth-label">
                                    <span>Above 50 SMA</span>
                                    <span class="{{ABOVE_50_CLASS}}">{{ABOVE_50}}%</span>
                                </div>
                                <div class="breadth-bar">
                                    <div class="breadth-fill" style="width: {{ABOVE_50}}%; background: var(--green);"></div>
                                </div>
                            </div>
                            <div class="breadth-item">
                                <div class="breadth-label">
                                    <span>Above 200 SMA</span>
                                    <span class="{{ABOVE_200_CLASS}}">{{ABOVE_200}}%</span>
                                </div>
                                <div class="breadth-bar">
                                    <div class="breadth-fill" style="width: {{ABOVE_200}}%; background: var(--purple);"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Sector Leaders -->
                    <div class="card" style="margin-top: 20px;">
                        <div class="card-header">
                            <div class="card-title">
                                <span class="card-title-icon">📈</span>
                                Sector Leaders
                            </div>
                        </div>
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Sector</th>
                                    <th>RS</th>
                                </tr>
                            </thead>
                            <tbody>
                                {{SECTOR_ROWS}}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </section>

        <!-- Hot Themes -->
        <section id="themes" style="margin-top: 24px;">
            <div class="grid">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <span class="card-title-icon">🔥</span>
                                Hot Themes & Stories
                            </div>
                            <span class="card-badge">Auto-detected</span>
                        </div>
                        <div class="card-body">
                            <div class="themes-container">
                                {{THEMES_HTML}}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Sentiment -->
        <section id="sentiment" style="margin-top: 24px;">
            <div class="grid">
                <div class="col-6">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <span class="card-title-icon">📰</span>
                                News Sentiment
                            </div>
                        </div>
                        <div class="card-body">
                            {{SENTIMENT_HTML}}
                        </div>
                    </div>
                </div>

                <div class="col-6">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">
                                <span class="card-title-icon">🤖</span>
                                AI Insights
                            </div>
                        </div>
                        <div class="card-body">
                            {{AI_INSIGHTS_HTML}}
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Bot Commands -->
        <section id="commands" style="margin-top: 24px;">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <span class="card-title-icon">⌨️</span>
                        Telegram Bot Commands
                    </div>
                    <a href="https://t.me/{{BOT_USERNAME}}" class="telegram-btn" target="_blank">
                        Open in Telegram
                    </a>
                </div>
                <div class="card-body">
                    <div class="command-grid">
                        <div class="command-item">
                            <div class="command-name">/scan</div>
                            <div class="command-desc">Run full momentum scanner</div>
                        </div>
                        <div class="command-item">
                            <div class="command-name">/stories</div>
                            <div class="command-desc">Detect hot themes</div>
                        </div>
                        <div class="command-item">
                            <div class="command-name">/news</div>
                            <div class="command-desc">News sentiment analysis</div>
                        </div>
                        <div class="command-item">
                            <div class="command-name">/sectors</div>
                            <div class="command-desc">Sector rotation</div>
                        </div>
                        <div class="command-item">
                            <div class="command-name">/earnings</div>
                            <div class="command-desc">Earnings calendar</div>
                        </div>
                        <div class="command-item">
                            <div class="command-name">/briefing</div>
                            <div class="command-desc">AI market narrative</div>
                        </div>
                        <div class="command-item">
                            <div class="command-name">/predict NVDA</div>
                            <div class="command-desc">AI trade prediction</div>
                        </div>
                        <div class="command-item">
                            <div class="command-name">/screen</div>
                            <div class="command-desc">Custom stock screener</div>
                        </div>
                        <div class="command-item">
                            <div class="command-name">NVDA</div>
                            <div class="command-desc">Full stock analysis</div>
                        </div>
                        <div class="command-item">
                            <div class="command-name">/backtest NVDA</div>
                            <div class="command-desc">Signal accuracy test</div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </div>

    <footer class="footer">
        <p>Stock Scanner Bot Dashboard | Auto-updates every 6 hours</p>
        <p style="margin-top: 8px;">
            <a href="https://github.com/zhuanleee/stock_scanner_bot">GitHub</a> ·
            <a href="https://t.me/{{BOT_USERNAME}}">Telegram Bot</a>
        </p>
    </footer>

    <script>
        // Smooth scroll for nav links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href.startsWith('#')) {
                    e.preventDefault();
                    document.querySelector(href).scrollIntoView({ behavior: 'smooth' });
                    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
                    this.classList.add('active');
                }
            });
        });

        // Update active nav on scroll
        window.addEventListener('scroll', () => {
            const sections = ['overview', 'themes', 'sentiment', 'commands'];
            let current = 'overview';

            sections.forEach(id => {
                const section = document.getElementById(id);
                if (section && window.scrollY >= section.offsetTop - 100) {
                    current = id;
                }
            });

            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.toggle('active', link.getAttribute('href') === '#' + current);
            });
        });
    </script>
</body>
</html>
'''


def generate_dashboard():
    """Generate the dashboard HTML with current data."""
    import glob

    # Initialize default values
    data = {
        'LAST_UPDATE': datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
        'BOT_USERNAME': os.environ.get('BOT_USERNAME', 'your_bot'),
        'TOTAL_SCANNED': '0',
        'BREAKOUTS': '0',
        'SQUEEZES': '0',
        'BREADTH': '50',
        'BREADTH_CLASS': '',
        'HOT_THEMES': '0',
        'ABOVE_20': '50',
        'ABOVE_50': '50',
        'ABOVE_200': '50',
        'ABOVE_20_CLASS': '',
        'ABOVE_50_CLASS': '',
        'ABOVE_200_CLASS': '',
        'TOP_STOCKS_ROWS': '<tr><td colspan="7" style="text-align: center; color: var(--text-dim);">Run /scan to populate data</td></tr>',
        'THEMES_HTML': '<span class="theme-tag theme-neutral">No themes detected yet</span>',
        'SECTOR_ROWS': '<tr><td colspan="2" style="color: var(--text-dim);">No data</td></tr>',
        'SENTIMENT_HTML': '<p style="color: var(--text-dim);">Run /news to get sentiment data</p>',
        'AI_INSIGHTS_HTML': '<div class="ai-insight"><div class="ai-insight-header">💡 Getting Started</div><div class="ai-insight-text">Use /briefing in Telegram to get AI-powered market insights.</div></div>',
    }

    # Try to load scan data
    scan_files = glob.glob('scan_*.csv')
    if scan_files and pd:
        try:
            latest = max(scan_files)
            df = pd.read_csv(latest)

            total = len(df)
            data['TOTAL_SCANNED'] = str(total)

            # Count breakouts and squeezes
            if 'breakout_up' in df.columns:
                data['BREAKOUTS'] = str(int(df['breakout_up'].sum()))
            if 'in_squeeze' in df.columns:
                data['SQUEEZES'] = str(int(df['in_squeeze'].sum()))

            # Calculate breadth
            if 'above_20' in df.columns:
                above_20 = int(df['above_20'].sum() / total * 100) if total > 0 else 50
                data['ABOVE_20'] = str(above_20)
                data['ABOVE_20_CLASS'] = 'positive' if above_20 > 50 else 'negative'

            if 'above_50' in df.columns:
                above_50 = int(df['above_50'].sum() / total * 100) if total > 0 else 50
                data['ABOVE_50'] = str(above_50)
                data['BREADTH'] = str(above_50)
                data['ABOVE_50_CLASS'] = 'positive' if above_50 > 50 else 'negative'
                data['BREADTH_CLASS'] = 'green' if above_50 > 60 else ('red' if above_50 < 40 else '')

            if 'above_200' in df.columns:
                above_200 = int(df['above_200'].sum() / total * 100) if total > 0 else 50
                data['ABOVE_200'] = str(above_200)
                data['ABOVE_200_CLASS'] = 'positive' if above_200 > 50 else 'negative'

            # Top stocks table
            rows = []
            for i, row in df.head(10).iterrows():
                rank = i + 1
                ticker = row.get('ticker', 'N/A')
                price = f"${row.get('price', 0):.2f}" if 'price' in row else '-'

                rs = row.get('rs_composite', 0)
                rs_class = 'positive' if rs > 0 else 'negative'
                rs_str = f"{rs:+.1f}%"

                vol = row.get('vol_ratio', 1)
                vol_str = f"{vol:.1f}x"

                score = row.get('composite_score', 0)

                signal = ''
                if row.get('breakout_up'):
                    signal = '<span style="color: var(--green);">🚀 Breakout</span>'
                elif row.get('in_squeeze'):
                    signal = '<span style="color: var(--purple);">⏳ Squeeze</span>'

                rows.append(f'''
                <tr>
                    <td>{rank}</td>
                    <td class="ticker">{ticker}</td>
                    <td>{price}</td>
                    <td class="{rs_class}">{rs_str}</td>
                    <td>{vol_str}</td>
                    <td>
                        <div class="score-container">
                            <span>{score:.0f}</span>
                            <div class="score-bar">
                                <div class="score-fill" style="width: {min(score, 100)}%;"></div>
                            </div>
                        </div>
                    </td>
                    <td>{signal}</td>
                </tr>
                ''')

            if rows:
                data['TOP_STOCKS_ROWS'] = ''.join(rows)

            # Sector data
            if 'sector' in df.columns and 'rs_composite' in df.columns:
                sector_df = df.groupby('sector').agg({
                    'rs_composite': 'mean'
                }).sort_values('rs_composite', ascending=False)

                sector_rows = []
                for sector, row in sector_df.head(6).iterrows():
                    rs = row['rs_composite']
                    rs_class = 'positive' if rs > 0 else 'negative'
                    sector_rows.append(f'''
                    <tr>
                        <td>{sector}</td>
                        <td class="{rs_class}">{rs:+.1f}%</td>
                    </tr>
                    ''')

                if sector_rows:
                    data['SECTOR_ROWS'] = ''.join(sector_rows)

        except Exception as e:
            print(f"Error loading scan data: {e}")

    # Try to load stories/themes
    try:
        from fast_stories import run_fast_story_detection
        stories = run_fast_story_detection(use_cache=True)

        themes = stories.get('themes', [])
        if themes:
            hot_count = len([t for t in themes if t.get('heat') == 'HOT'])
            data['HOT_THEMES'] = str(hot_count) if hot_count else str(len(themes))

            theme_tags = []
            for t in themes[:12]:
                name = t.get('name', 'Unknown')
                heat = t.get('heat', 'WARM')
                count = t.get('mention_count', 0)

                heat_class = 'theme-hot' if heat == 'HOT' else ('theme-warm' if heat == 'WARM' else 'theme-neutral')

                plays = t.get('primary_plays', [])[:3]
                plays_str = ' '.join([f'<span style="opacity: 0.7;">{p}</span>' for p in plays])

                theme_tags.append(f'''
                <div class="theme-tag {heat_class}">
                    <span>{'🔥' if heat == 'HOT' else '📈'} {name}</span>
                    <span class="theme-count">{count}</span>
                </div>
                ''')

            data['THEMES_HTML'] = ''.join(theme_tags)
    except Exception as e:
        print(f"Stories error: {e}")

    # Try to load sentiment
    try:
        sentiment_file = Path('dashboard_data/sentiment.json')
        if sentiment_file.exists():
            with open(sentiment_file) as f:
                sentiments = json.load(f)

            sent_rows = []
            for s in sentiments[:6]:
                ticker = s.get('ticker', '')
                bullish = s.get('bullish_pct', 50)
                bearish = 100 - bullish

                label_class = 'bullish' if bullish > 60 else ('bearish' if bullish < 40 else 'neutral')
                label_text = 'Bullish' if bullish > 60 else ('Bearish' if bullish < 40 else 'Neutral')

                sent_rows.append(f'''
                <div class="sentiment-row">
                    <span class="sentiment-ticker">{ticker}</span>
                    <div class="sentiment-bar-container">
                        <div class="sentiment-bullish" style="width: {bullish}%;">{bullish:.0f}%</div>
                        <div class="sentiment-bearish" style="width: {bearish}%;">{bearish:.0f}%</div>
                    </div>
                    <span class="sentiment-label {label_class}">{label_text}</span>
                </div>
                ''')

            if sent_rows:
                data['SENTIMENT_HTML'] = ''.join(sent_rows)
    except Exception as e:
        print(f"Sentiment error: {e}")

    # Try to load AI insights
    try:
        ai_file = Path('dashboard_data/ai_insights.json')
        if ai_file.exists():
            with open(ai_file) as f:
                insights = json.load(f)

            insight_html = []
            for ins in insights[:3]:
                title = ins.get('title', 'Insight')
                text = ins.get('text', '')
                insight_html.append(f'''
                <div class="ai-insight">
                    <div class="ai-insight-header">💡 {title}</div>
                    <div class="ai-insight-text">{text}</div>
                </div>
                ''')

            if insight_html:
                data['AI_INSIGHTS_HTML'] = ''.join(insight_html)
    except Exception as e:
        print(f"AI insights error: {e}")

    # Generate HTML
    html = DASHBOARD_HTML
    for key, value in data.items():
        html = html.replace('{{' + key + '}}', str(value))

    # Save to docs folder
    output_dir = Path('docs')
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / 'index.html'
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Dashboard generated: {output_path}")
    return output_path


def save_sentiment_data(sentiments):
    """Save sentiment data for dashboard."""
    output_dir = Path('dashboard_data')
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / 'sentiment.json', 'w') as f:
        json.dump(sentiments, f)


def save_ai_insights(insights):
    """Save AI insights for dashboard."""
    output_dir = Path('dashboard_data')
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / 'ai_insights.json', 'w') as f:
        json.dump(insights, f)


if __name__ == '__main__':
    generate_dashboard()
