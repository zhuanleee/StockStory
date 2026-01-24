#!/usr/bin/env python3
"""
Stock Scanner Web Dashboard

Generates a static HTML dashboard that can be hosted on GitHub Pages.
Run this locally or via GitHub Actions to update the dashboard.
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path

DASHBOARD_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Scanner Dashboard</title>
    <style>
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --text-primary: #f0f6fc;
            --text-secondary: #8b949e;
            --accent-green: #3fb950;
            --accent-red: #f85149;
            --accent-blue: #58a6ff;
            --accent-orange: #d29922;
            --accent-purple: #a371f7;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid var(--bg-tertiary);
            margin-bottom: 30px;
        }

        h1 {
            font-size: 1.8rem;
            font-weight: 600;
        }

        .last-update {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--bg-tertiary);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .badge {
            background: var(--bg-tertiary);
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid var(--bg-tertiary);
        }

        th {
            color: var(--text-secondary);
            font-weight: 500;
            font-size: 0.85rem;
            text-transform: uppercase;
        }

        .ticker {
            font-weight: 600;
            color: var(--accent-blue);
        }

        .positive {
            color: var(--accent-green);
        }

        .negative {
            color: var(--accent-red);
        }

        .score-bar {
            background: var(--bg-tertiary);
            border-radius: 4px;
            height: 8px;
            overflow: hidden;
        }

        .score-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }

        .theme-tag {
            display: inline-block;
            background: var(--bg-tertiary);
            padding: 4px 10px;
            border-radius: 6px;
            margin: 4px;
            font-size: 0.85rem;
        }

        .theme-hot {
            background: rgba(63, 185, 80, 0.2);
            color: var(--accent-green);
        }

        .corr-pair {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--bg-tertiary);
        }

        .breadth-meter {
            background: var(--bg-tertiary);
            border-radius: 8px;
            height: 24px;
            overflow: hidden;
            margin: 10px 0;
        }

        .breadth-fill {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid var(--bg-tertiary);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
        }

        .stat-label {
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 5px;
        }

        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            .stat-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Stock Scanner Dashboard</h1>
            <span class="last-update">Last updated: {{LAST_UPDATE}}</span>
        </header>

        <!-- Stats Overview -->
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value positive">{{TOTAL_SCANNED}}</div>
                <div class="stat-label">Stocks Scanned</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: var(--accent-orange)">{{BREAKOUTS}}</div>
                <div class="stat-label">Active Breakouts</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: var(--accent-purple)">{{SQUEEZES}}</div>
                <div class="stat-label">In Squeeze</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: var(--accent-blue)">{{BREADTH}}%</div>
                <div class="stat-label">Above 50 SMA</div>
            </div>
        </div>

        <div class="grid">
            <!-- Top 10 Stocks -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🏆 Top 10 Stocks</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Ticker</th>
                            <th>Score</th>
                            <th>RS</th>
                            <th>Signal</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{TOP_STOCKS_ROWS}}
                    </tbody>
                </table>
            </div>

            <!-- Hot Themes -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🔥 Hot Themes</span>
                </div>
                <div style="margin-top: 10px;">
                    {{THEMES_HTML}}
                </div>
            </div>

            <!-- Sector Strength -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📈 Sector Strength</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Sector</th>
                            <th>RS</th>
                            <th>Breakouts</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{SECTOR_ROWS}}
                    </tbody>
                </table>
            </div>

            <!-- Correlation Warnings -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🔗 High Correlations</span>
                    <span class="badge">Watch for overconcentration</span>
                </div>
                <div style="margin-top: 10px;">
                    {{CORRELATION_HTML}}
                </div>
            </div>

            <!-- Supply Chain Plays -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">⛓️ Supply Chain Plays</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Driver</th>
                            <th>→</th>
                            <th>Beneficiary</th>
                            <th>Gap</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{SUPPLY_CHAIN_ROWS}}
                    </tbody>
                </table>
            </div>

            <!-- Learned Themes -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📚 Learned Themes</span>
                    <span class="badge">Auto-detected</span>
                </div>
                <div style="margin-top: 10px;">
                    {{LEARNED_HTML}}
                </div>
            </div>
        </div>

        <!-- Market Breadth -->
        <div class="card" style="margin-bottom: 30px;">
            <div class="card-header">
                <span class="card-title">📊 Market Breadth</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 15px;">
                <div>
                    <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 5px;">Above 20 SMA</div>
                    <div class="breadth-meter">
                        <div class="breadth-fill" style="width: {{ABOVE_20}}%; background: var(--accent-blue);">{{ABOVE_20}}%</div>
                    </div>
                </div>
                <div>
                    <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 5px;">Above 50 SMA</div>
                    <div class="breadth-meter">
                        <div class="breadth-fill" style="width: {{ABOVE_50}}%; background: var(--accent-green);">{{ABOVE_50}}%</div>
                    </div>
                </div>
                <div>
                    <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 5px;">Above 200 SMA</div>
                    <div class="breadth-meter">
                        <div class="breadth-fill" style="width: {{ABOVE_200}}%; background: var(--accent-purple);">{{ABOVE_200}}%</div>
                    </div>
                </div>
            </div>
        </div>

        <footer style="text-align: center; color: var(--text-secondary); padding: 20px 0;">
            <p>Generated by Stock Scanner Bot | Data updates twice daily</p>
        </footer>
    </div>
</body>
</html>
'''


def generate_dashboard(scan_csv='scan_*.csv'):
    """Generate HTML dashboard from latest scan results."""
    import glob

    # Find latest scan file
    scan_files = glob.glob(scan_csv)
    if not scan_files:
        print("No scan files found")
        return None

    latest_scan = max(scan_files)
    print(f"Loading: {latest_scan}")

    df = pd.read_csv(latest_scan)

    # Load additional data
    learned = {}
    if Path('learned_themes.json').exists():
        with open('learned_themes.json', 'r') as f:
            learned = json.load(f)

    # Calculate stats
    total = len(df)
    breakouts = int((df['breakout_up'] == True).sum())
    squeezes = int((df['in_squeeze'] == True).sum())
    above_20 = int((df['above_20'] == True).sum() / total * 100)
    above_50 = int((df['above_50'] == True).sum() / total * 100)
    above_200 = int((df['above_200'] == True).sum() / total * 100)

    # Top 10 stocks HTML
    top_stocks_html = ""
    for i, (_, row) in enumerate(df.head(10).iterrows(), 1):
        signal = ""
        if row.get('breakout_up'):
            signal = "🚀"
        elif row.get('in_squeeze'):
            signal = "⏳"

        rs_class = "positive" if row['rs_composite'] > 0 else "negative"
        rs_sign = "+" if row['rs_composite'] > 0 else ""

        top_stocks_html += f'''
        <tr>
            <td>{i}</td>
            <td class="ticker">{row['ticker']}</td>
            <td>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span>{row['composite_score']:.0f}</span>
                    <div class="score-bar" style="width: 60px;">
                        <div class="score-fill" style="width: {row['composite_score']}%; background: var(--accent-green);"></div>
                    </div>
                </div>
            </td>
            <td class="{rs_class}">{rs_sign}{row['rs_composite']:.1f}%</td>
            <td>{signal}</td>
        </tr>
        '''

    # Themes HTML
    themes_html = ""
    sector_rs = df.groupby('sector').agg({
        'rs_composite': 'mean',
        'breakout_up': 'sum'
    }).sort_values('rs_composite', ascending=False)

    for sector, row in sector_rs.head(8).iterrows():
        hot_class = "theme-hot" if row['rs_composite'] > 2 else ""
        themes_html += f'<span class="theme-tag {hot_class}">{sector} ({row["rs_composite"]:+.1f}%)</span>'

    # Sector rows HTML
    sector_rows = ""
    for sector, row in sector_rs.head(8).iterrows():
        rs_class = "positive" if row['rs_composite'] > 0 else "negative"
        sector_rows += f'''
        <tr>
            <td>{sector}</td>
            <td class="{rs_class}">{row['rs_composite']:+.1f}%</td>
            <td>{int(row['breakout_up'])}</td>
        </tr>
        '''

    # Correlation HTML (placeholder - would need corr data)
    correlation_html = "<p style='color: var(--text-secondary);'>Run scan to detect correlations</p>"

    # Supply chain HTML (placeholder)
    supply_chain_html = "<tr><td colspan='4' style='color: var(--text-secondary);'>Run scan for supply chain analysis</td></tr>"

    # Learned themes HTML
    learned_html = ""
    if learned:
        for theme_id, data in list(learned.items())[:5]:
            name = data.get('user_name') or theme_id
            tickers = ', '.join(data.get('tickers', [])[:4])
            learned_html += f'''
            <div style="padding: 10px 0; border-bottom: 1px solid var(--bg-tertiary);">
                <div style="font-weight: 600;">{name}</div>
                <div style="color: var(--text-secondary); font-size: 0.85rem;">{tickers}</div>
            </div>
            '''
    else:
        learned_html = "<p style='color: var(--text-secondary);'>No themes learned yet. System will auto-detect patterns over time.</p>"

    # Fill template
    html = DASHBOARD_TEMPLATE
    html = html.replace('{{LAST_UPDATE}}', datetime.now().strftime('%Y-%m-%d %H:%M UTC'))
    html = html.replace('{{TOTAL_SCANNED}}', str(total))
    html = html.replace('{{BREAKOUTS}}', str(breakouts))
    html = html.replace('{{SQUEEZES}}', str(squeezes))
    html = html.replace('{{BREADTH}}', str(above_50))
    html = html.replace('{{ABOVE_20}}', str(above_20))
    html = html.replace('{{ABOVE_50}}', str(above_50))
    html = html.replace('{{ABOVE_200}}', str(above_200))
    html = html.replace('{{TOP_STOCKS_ROWS}}', top_stocks_html)
    html = html.replace('{{THEMES_HTML}}', themes_html)
    html = html.replace('{{SECTOR_ROWS}}', sector_rows)
    html = html.replace('{{CORRELATION_HTML}}', correlation_html)
    html = html.replace('{{SUPPLY_CHAIN_ROWS}}', supply_chain_html)
    html = html.replace('{{LEARNED_HTML}}', learned_html)

    # Save
    output_path = Path('docs/index.html')
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Dashboard saved to: {output_path}")
    return output_path


if __name__ == '__main__':
    generate_dashboard()
