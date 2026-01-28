#!/usr/bin/env python3
"""
TAM (Total Addressable Market) Estimator

Smart estimation of market opportunity for sectors and themes.
Combines:
1. Industry research estimates (embedded)
2. Market cap analysis
3. Revenue growth trends
4. Penetration rate calculations
"""

import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

from utils import get_logger

logger = get_logger(__name__)


# ============================================================
# INDUSTRY TAM ESTIMATES (in billions USD)
# Sources: IDC, Gartner, McKinsey, Grand View Research, etc.
# ============================================================

TAM_DATABASE = {
    # AI & Semiconductors
    'AI_Infrastructure': {
        'tam_2024': 184,      # Billion USD
        'tam_2030': 827,      # Projected
        'cagr': 28.0,         # %
        'key_players': ['NVDA', 'AMD', 'INTC', 'AVGO', 'MRVL'],
        'description': 'AI chips, GPUs, accelerators, training/inference hardware',
        'source': 'IDC/Gartner 2024',
    },
    'HBM_Memory': {
        'tam_2024': 16,
        'tam_2030': 80,
        'cagr': 31.0,
        'key_players': ['MU', 'SKHMS', 'SSNLF'],  # SK Hynix, Samsung
        'description': 'High Bandwidth Memory for AI/HPC',
        'source': 'TrendForce 2024',
    },
    'Semiconductor_Equipment': {
        'tam_2024': 100,
        'tam_2030': 180,
        'cagr': 10.0,
        'key_players': ['ASML', 'AMAT', 'LRCX', 'KLAC', 'TER'],
        'description': 'Chip manufacturing equipment',
        'source': 'SEMI 2024',
    },
    'Data_Center': {
        'tam_2024': 350,
        'tam_2030': 650,
        'cagr': 11.0,
        'key_players': ['MSFT', 'AMZN', 'GOOGL', 'EQIX', 'DLR'],
        'description': 'Cloud infrastructure, colocation, hyperscalers',
        'source': 'Synergy Research 2024',
    },

    # Healthcare
    'GLP1_Obesity': {
        'tam_2024': 24,
        'tam_2030': 130,
        'cagr': 32.0,
        'key_players': ['LLY', 'NVO', 'AMGN', 'PFE'],
        'description': 'GLP-1 drugs for obesity and diabetes',
        'source': 'Goldman Sachs 2024',
    },
    'Gene_Therapy': {
        'tam_2024': 8,
        'tam_2030': 35,
        'cagr': 28.0,
        'key_players': ['CRSP', 'NTLA', 'BEAM', 'EDIT', 'BLUE'],
        'description': 'Gene editing, cell therapy, CRISPR',
        'source': 'EvaluatePharma 2024',
    },
    'Medical_Devices': {
        'tam_2024': 500,
        'tam_2030': 720,
        'cagr': 6.3,
        'key_players': ['MDT', 'ABT', 'SYK', 'BSX', 'ISRG'],
        'description': 'Medical devices, surgical robotics, diagnostics',
        'source': 'Fortune Business Insights',
    },

    # Energy
    'Nuclear_Energy': {
        'tam_2024': 45,
        'tam_2030': 85,
        'cagr': 11.0,
        'key_players': ['CEG', 'VST', 'CCJ', 'UEC'],
        'description': 'Nuclear power generation and uranium',
        'source': 'World Nuclear Association',
    },
    'Solar_Energy': {
        'tam_2024': 230,
        'tam_2030': 600,
        'cagr': 17.0,
        'key_players': ['FSLR', 'ENPH', 'SEDG', 'RUN'],
        'description': 'Solar panels, inverters, installation',
        'source': 'BloombergNEF 2024',
    },
    'EV_Market': {
        'tam_2024': 500,
        'tam_2030': 1300,
        'cagr': 17.3,
        'key_players': ['TSLA', 'RIVN', 'LCID', 'F', 'GM'],
        'description': 'Electric vehicles and charging',
        'source': 'IEA Global EV Outlook',
    },
    'Lithium_Battery': {
        'tam_2024': 95,
        'tam_2030': 400,
        'cagr': 27.0,
        'key_players': ['ALB', 'SQM', 'LAC', 'LTHM'],
        'description': 'Lithium mining and battery materials',
        'source': 'Benchmark Minerals',
    },

    # Software & Cloud
    'Cloud_Computing': {
        'tam_2024': 680,
        'tam_2030': 1600,
        'cagr': 15.0,
        'key_players': ['MSFT', 'AMZN', 'GOOGL', 'CRM', 'SNOW'],
        'description': 'Public cloud, SaaS, PaaS, IaaS',
        'source': 'Gartner 2024',
    },
    'Cybersecurity': {
        'tam_2024': 200,
        'tam_2030': 450,
        'cagr': 14.5,
        'key_players': ['CRWD', 'PANW', 'ZS', 'FTNT', 'S'],
        'description': 'Security software, endpoint, cloud security',
        'source': 'Cybersecurity Ventures',
    },
    'Enterprise_AI': {
        'tam_2024': 50,
        'tam_2030': 300,
        'cagr': 35.0,
        'key_players': ['MSFT', 'GOOGL', 'IBM', 'PLTR', 'AI'],
        'description': 'Enterprise AI software and services',
        'source': 'McKinsey 2024',
    },

    # Fintech & Payments
    'Digital_Payments': {
        'tam_2024': 120,
        'tam_2030': 300,
        'cagr': 16.5,
        'key_players': ['V', 'MA', 'PYPL', 'SQ', 'ADYEN'],
        'description': 'Digital payments, fintech, BNPL',
        'source': 'McKinsey Payments Report',
    },
    'Crypto_Blockchain': {
        'tam_2024': 20,
        'tam_2030': 100,
        'cagr': 30.0,
        'key_players': ['COIN', 'MSTR', 'MARA', 'RIOT'],
        'description': 'Crypto exchanges, mining, blockchain',
        'source': 'Chainalysis 2024',
    },

    # Robotics & Automation
    'Industrial_Automation': {
        'tam_2024': 180,
        'tam_2030': 350,
        'cagr': 11.7,
        'key_players': ['ROK', 'EMR', 'ABB', 'HON'],
        'description': 'Factory automation, PLCs, robotics',
        'source': 'Mordor Intelligence',
    },
    'Humanoid_Robots': {
        'tam_2024': 2,
        'tam_2030': 38,
        'cagr': 65.0,
        'key_players': ['TSLA'],  # Optimus
        'description': 'Humanoid robots for labor',
        'source': 'Goldman Sachs 2024',
    },
    'Autonomous_Vehicles': {
        'tam_2024': 75,
        'tam_2030': 400,
        'cagr': 32.0,
        'key_players': ['TSLA', 'GOOGL', 'GM', 'MBLY'],
        'description': 'Self-driving cars, robotaxis, ADAS',
        'source': 'McKinsey Mobility',
    },

    # Space & Defense
    'Space_Economy': {
        'tam_2024': 469,
        'tam_2030': 800,
        'cagr': 9.0,
        'key_players': ['RKLB', 'LMT', 'NOC', 'BA', 'ASTS'],
        'description': 'Satellites, launch, space services',
        'source': 'Morgan Stanley Space',
    },
    'Defense': {
        'tam_2024': 600,
        'tam_2030': 850,
        'cagr': 6.0,
        'key_players': ['LMT', 'RTX', 'NOC', 'GD', 'BA'],
        'description': 'Defense contractors, aerospace',
        'source': 'SIPRI 2024',
    },

    # Materials
    'Copper': {
        'tam_2024': 210,
        'tam_2030': 350,
        'cagr': 8.9,
        'key_players': ['FCX', 'SCCO', 'TECK', 'RIO'],
        'description': 'Copper mining for electrification',
        'source': 'CRU Group',
    },
    'Rare_Earths': {
        'tam_2024': 8,
        'tam_2030': 20,
        'cagr': 16.0,
        'key_players': ['MP', 'UUUU'],
        'description': 'Rare earth elements for EVs, defense',
        'source': 'Adamas Intelligence',
    },
}


def get_company_financials(ticker):
    """Get market cap and revenue data for a company."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        market_cap = info.get('marketCap', 0) / 1e9  # Convert to billions
        revenue = info.get('totalRevenue', 0) / 1e9
        revenue_growth = info.get('revenueGrowth', 0) * 100  # %

        return {
            'market_cap': round(market_cap, 2),
            'revenue': round(revenue, 2),
            'revenue_growth': round(revenue_growth, 1),
        }
    except Exception as e:
        logger.debug(f"Failed to get financials for {ticker}: {e}")
        return None


def calculate_market_share(ticker, theme):
    """Calculate company's share of TAM."""
    theme_data = TAM_DATABASE.get(theme)
    if not theme_data:
        return None

    financials = get_company_financials(ticker)
    if not financials or financials['revenue'] == 0:
        return None

    tam = theme_data['tam_2024']
    revenue = financials['revenue']

    # Estimate market share
    market_share = (revenue / tam) * 100 if tam > 0 else 0

    return {
        'ticker': ticker,
        'theme': theme,
        'revenue': revenue,
        'tam': tam,
        'market_share': round(market_share, 2),
        'market_cap': financials['market_cap'],
    }


def analyze_theme_tam(theme):
    """Full TAM analysis for a theme."""
    theme_data = TAM_DATABASE.get(theme)
    if not theme_data:
        return None

    players = theme_data.get('key_players', [])
    player_analysis = []
    total_revenue = 0
    total_market_cap = 0

    for ticker in players:
        financials = get_company_financials(ticker)
        if financials:
            player_analysis.append({
                'ticker': ticker,
                **financials,
            })
            total_revenue += financials['revenue']
            total_market_cap += financials['market_cap']

    # Calculate penetration
    tam_current = theme_data['tam_2024']
    tam_future = theme_data['tam_2030']
    penetration = (total_revenue / tam_current * 100) if tam_current > 0 else 0

    # Calculate growth opportunity
    growth_opportunity = tam_future - tam_current

    return {
        'theme': theme,
        'description': theme_data['description'],
        'tam_2024': tam_current,
        'tam_2030': tam_future,
        'cagr': theme_data['cagr'],
        'growth_opportunity': round(growth_opportunity, 1),
        'key_players': player_analysis,
        'total_player_revenue': round(total_revenue, 2),
        'total_market_cap': round(total_market_cap, 2),
        'current_penetration': round(penetration, 1),
        'source': theme_data.get('source', 'N/A'),
    }


def rank_themes_by_opportunity():
    """Rank all themes by growth opportunity."""
    rankings = []

    for theme in TAM_DATABASE.keys():
        data = TAM_DATABASE[theme]
        growth = data['tam_2030'] - data['tam_2024']
        growth_multiple = data['tam_2030'] / data['tam_2024'] if data['tam_2024'] > 0 else 0

        rankings.append({
            'theme': theme,
            'tam_2024': data['tam_2024'],
            'tam_2030': data['tam_2030'],
            'growth': round(growth, 1),
            'growth_multiple': round(growth_multiple, 2),
            'cagr': data['cagr'],
        })

    # Sort by CAGR
    rankings.sort(key=lambda x: x['cagr'], reverse=True)

    return rankings


def find_undervalued_in_theme(theme):
    """
    Find potentially undervalued companies in a theme.
    Compare market cap to revenue and market share.
    """
    theme_data = TAM_DATABASE.get(theme)
    if not theme_data:
        return None

    players = theme_data.get('key_players', [])
    analysis = []

    for ticker in players:
        financials = get_company_financials(ticker)
        if financials and financials['revenue'] > 0:
            # Price-to-Sales ratio
            ps_ratio = financials['market_cap'] / financials['revenue']

            # TAM-adjusted valuation
            tam = theme_data['tam_2024']
            market_share = financials['revenue'] / tam * 100
            tam_future = theme_data['tam_2030']
            potential_revenue = (market_share / 100) * tam_future

            # Upside potential (if maintains market share)
            upside = ((potential_revenue / financials['revenue']) - 1) * 100

            analysis.append({
                'ticker': ticker,
                'market_cap': financials['market_cap'],
                'revenue': financials['revenue'],
                'ps_ratio': round(ps_ratio, 2),
                'market_share': round(market_share, 2),
                'revenue_growth': financials['revenue_growth'],
                'upside_potential': round(upside, 1),
            })

    # Sort by upside potential
    analysis.sort(key=lambda x: x['upside_potential'], reverse=True)

    return analysis


def format_tam_analysis(analysis):
    """Format TAM analysis for Telegram."""
    msg = f"📊 *TAM ANALYSIS: {analysis['theme']}*\n\n"
    msg += f"_{analysis['description']}_\n\n"

    msg += f"*Market Size:*\n"
    msg += f"• 2024: ${analysis['tam_2024']}B\n"
    msg += f"• 2030: ${analysis['tam_2030']}B\n"
    msg += f"• CAGR: {analysis['cagr']}%\n"
    msg += f"• Growth: ${analysis['growth_opportunity']}B\n\n"

    msg += f"*Key Players:*\n"
    for p in analysis['key_players'][:5]:
        msg += f"• `{p['ticker']}`: ${p['revenue']:.1f}B rev, ${p['market_cap']:.0f}B mcap\n"

    msg += f"\n*Penetration:* {analysis['current_penetration']:.1f}% of TAM captured\n"
    msg += f"_Source: {analysis['source']}_"

    return msg


def format_theme_rankings(rankings):
    """Format theme rankings for Telegram."""
    msg = "🎯 *TAM GROWTH RANKINGS*\n\n"
    msg += "_Themes by CAGR (2024-2030):_\n\n"

    for i, r in enumerate(rankings[:10], 1):
        emoji = "🚀" if r['cagr'] >= 25 else ("📈" if r['cagr'] >= 15 else "📊")
        msg += f"{i}. {emoji} *{r['theme'].replace('_', ' ')}*\n"
        msg += f"   ${r['tam_2024']}B → ${r['tam_2030']}B ({r['cagr']}% CAGR)\n\n"

    return msg


def format_undervalued(theme, analysis):
    """Format undervalued analysis for Telegram."""
    if not analysis:
        return f"No data available for {theme}"

    msg = f"💎 *UNDERVALUED IN {theme.replace('_', ' ').upper()}*\n\n"

    for p in analysis[:5]:
        msg += f"*{p['ticker']}*\n"
        msg += f"  P/S: {p['ps_ratio']}x | Share: {p['market_share']:.1f}%\n"
        msg += f"  Growth: {p['revenue_growth']:+.1f}% | Upside: {p['upside_potential']:.0f}%\n\n"

    msg += "_Upside = potential if maintains market share through 2030_"

    return msg


if __name__ == '__main__':
    # Test theme analysis
    logger.info("=" * 60)
    logger.info("TAM ANALYSIS: AI_Infrastructure")
    logger.info("=" * 60)
    analysis = analyze_theme_tam('AI_Infrastructure')
    if analysis:
        logger.info(format_tam_analysis(analysis))

    logger.info("\n" + "=" * 60)
    logger.info("THEME RANKINGS BY GROWTH")
    logger.info("=" * 60)
    rankings = rank_themes_by_opportunity()
    logger.info(format_theme_rankings(rankings))

    logger.info("\n" + "=" * 60)
    logger.info("UNDERVALUED IN GLP1_Obesity")
    logger.info("=" * 60)
    undervalued = find_undervalued_in_theme('GLP1_Obesity')
    logger.info(format_undervalued('GLP1_Obesity', undervalued))
