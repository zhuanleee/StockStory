#!/usr/bin/env python3
"""
PatentView API Integration - Track company patent activity as innovation signal.

Uses USPTO PatentView API to:
- Search patents by company/assignee
- Track recent patent filings
- Identify innovation trends
- Score patent activity for story scoring
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json

# API Configuration
PATENTVIEW_API_KEY = os.getenv('PATENTVIEW_API_KEY', 'tLA9fgBB.lAyhMSGUykSJQmJsAPRiLidRBa2Iaszi')
PATENTVIEW_BASE_URL = 'https://search.patentsview.org/api/v1'
RATE_LIMIT_PER_MIN = 45

# Company name mappings (ticker -> organization name variations)
COMPANY_MAPPINGS = {
    'AAPL': ['Apple Inc', 'Apple Computer'],
    'GOOGL': ['Google LLC', 'Alphabet Inc', 'Google Inc'],
    'GOOG': ['Google LLC', 'Alphabet Inc', 'Google Inc'],
    'MSFT': ['Microsoft Corporation', 'Microsoft Technology'],
    'AMZN': ['Amazon Technologies', 'Amazon.com'],
    'META': ['Meta Platforms', 'Facebook Inc', 'Facebook Technologies'],
    'NVDA': ['NVIDIA Corporation', 'Nvidia Corp'],
    'TSLA': ['Tesla Inc', 'Tesla Motors'],
    'AMD': ['Advanced Micro Devices', 'AMD Inc'],
    'INTC': ['Intel Corporation'],
    'IBM': ['International Business Machines', 'IBM'],
    'ORCL': ['Oracle Corporation', 'Oracle International'],
    'CRM': ['Salesforce Inc', 'Salesforce.com'],
    'ADBE': ['Adobe Inc', 'Adobe Systems'],
    'NFLX': ['Netflix Inc'],
    'QCOM': ['Qualcomm Incorporated', 'Qualcomm Inc'],
    'AVGO': ['Broadcom Inc', 'Broadcom Corporation'],
    'TXN': ['Texas Instruments'],
    'MU': ['Micron Technology'],
    'AMAT': ['Applied Materials'],
    'LRCX': ['Lam Research'],
    'KLAC': ['KLA Corporation', 'KLA-Tencor'],
    'MRVL': ['Marvell Technology', 'Marvell Semiconductor'],
    'ON': ['ON Semiconductor', 'onsemi'],
    'NXPI': ['NXP Semiconductors', 'NXP B.V.'],
}


def get_headers() -> Dict[str, str]:
    """Get API request headers with authentication."""
    return {
        'X-Api-Key': PATENTVIEW_API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }


def get_company_names(ticker: str) -> List[str]:
    """Get possible company names for a ticker."""
    if ticker.upper() in COMPANY_MAPPINGS:
        return COMPANY_MAPPINGS[ticker.upper()]

    # Try to get company name from yfinance
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        company_name = info.get('longName') or info.get('shortName')
        if company_name:
            # Clean up common suffixes
            for suffix in [', Inc.', ' Inc.', ' Inc', ' Corp.', ' Corp', ' LLC', ' Ltd.', ' Ltd', ' Co.', ' Co']:
                if company_name.endswith(suffix):
                    base_name = company_name[:-len(suffix)]
                    return [company_name, base_name]
            return [company_name]
    except Exception:
        pass

    return [ticker]


def search_patents_by_assignee(
    assignee_name: str,
    years_back: int = 3,
    max_results: int = 100
) -> Dict[str, Any]:
    """
    Search patents by assignee organization name.

    Args:
        assignee_name: Company/organization name to search
        years_back: How many years back to search
        max_results: Maximum patents to return

    Returns:
        Dict with patent data and statistics
    """
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years_back * 365)

        # Build query - search for assignee organization name
        query = {
            "_and": [
                {"_text_any": {"assignees.assignee_organization": assignee_name}},
                {"_gte": {"patent_date": start_date.strftime("%Y-%m-%d")}},
            ]
        }

        # Fields to return
        fields = [
            "patent_id",
            "patent_title",
            "patent_date",
            "patent_abstract",
            "patent_type",
            "assignees.assignee_organization",
            "cpc_current.cpc_class_id",
            "cpc_current.cpc_subclass_id",
        ]

        # API request
        url = f"{PATENTVIEW_BASE_URL}/patent/"
        params = {
            'q': json.dumps(query),
            'f': json.dumps(fields),
            's': json.dumps([{"patent_date": "desc"}]),
            'o': json.dumps({"size": max_results}),
        }

        response = requests.get(url, headers=get_headers(), params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        patents = data.get('patents', [])
        total_count = data.get('total_patent_count', len(patents))

        return {
            'success': True,
            'assignee': assignee_name,
            'total_patents': total_count,
            'patents': patents,
            'years_searched': years_back,
        }

    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': str(e),
            'assignee': assignee_name,
            'total_patents': 0,
            'patents': [],
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'assignee': assignee_name,
            'total_patents': 0,
            'patents': [],
        }


def get_patent_stats(ticker: str, years_back: int = 3) -> Dict[str, Any]:
    """
    Get patent statistics for a company.

    Args:
        ticker: Stock ticker symbol
        years_back: Years of patent history to analyze

    Returns:
        Dict with patent statistics and innovation score
    """
    company_names = get_company_names(ticker)

    all_patents = []
    total_count = 0

    # Search for all company name variations
    for name in company_names:
        result = search_patents_by_assignee(name, years_back)
        if result['success'] and result['patents']:
            all_patents.extend(result['patents'])
            total_count += result['total_patents']

    # Deduplicate by patent_id
    seen_ids = set()
    unique_patents = []
    for patent in all_patents:
        pid = patent.get('patent_id')
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            unique_patents.append(patent)

    # Calculate statistics
    stats = analyze_patent_portfolio(unique_patents, years_back)
    stats['ticker'] = ticker
    stats['company_names'] = company_names
    stats['total_patents'] = len(unique_patents)

    return stats


def analyze_patent_portfolio(patents: List[Dict], years_back: int) -> Dict[str, Any]:
    """Analyze a portfolio of patents and generate statistics."""
    if not patents:
        return {
            'total_patents': 0,
            'patents_per_year': 0,
            'recent_patents': [],
            'top_categories': [],
            'innovation_score': 0,
            'trend': 'none',
        }

    # Count patents by year
    yearly_counts = {}
    current_year = datetime.now().year

    for patent in patents:
        try:
            date_str = patent.get('patent_date', '')
            if date_str:
                year = int(date_str[:4])
                yearly_counts[year] = yearly_counts.get(year, 0) + 1
        except (ValueError, IndexError):
            pass

    # Calculate trend (comparing recent vs older)
    recent_years = [current_year, current_year - 1]
    older_years = [current_year - 2, current_year - 3]

    recent_count = sum(yearly_counts.get(y, 0) for y in recent_years)
    older_count = sum(yearly_counts.get(y, 0) for y in older_years)

    if older_count > 0:
        trend_ratio = recent_count / older_count
        if trend_ratio > 1.2:
            trend = 'accelerating'
        elif trend_ratio < 0.8:
            trend = 'declining'
        else:
            trend = 'stable'
    else:
        trend = 'new' if recent_count > 0 else 'none'

    # Get top CPC categories
    categories = {}
    for patent in patents:
        cpc_list = patent.get('cpc_current', [])
        if isinstance(cpc_list, list):
            for cpc in cpc_list:
                # Extract section from class_id (first letter, e.g., "G06" -> "G")
                class_id = cpc.get('cpc_class_id', '')
                if class_id:
                    section = class_id[0] if class_id else 'Unknown'
                    categories[section] = categories.get(section, 0) + 1

    top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]

    # CPC Section descriptions
    cpc_descriptions = {
        'A': 'Human Necessities',
        'B': 'Operations/Transport',
        'C': 'Chemistry/Metallurgy',
        'D': 'Textiles/Paper',
        'E': 'Construction',
        'F': 'Mechanical Engineering',
        'G': 'Physics/Computing',
        'H': 'Electricity/Electronics',
        'Y': 'Emerging Technologies',
    }

    top_categories_with_desc = [
        {'section': cat, 'count': count, 'description': cpc_descriptions.get(cat, 'Other')}
        for cat, count in top_categories
    ]

    # Get recent patents (last 6 months)
    six_months_ago = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    recent_patents = [
        {
            'id': p.get('patent_id'),
            'title': p.get('patent_title'),
            'date': p.get('patent_date'),
        }
        for p in patents
        if p.get('patent_date', '') >= six_months_ago
    ][:10]

    # Calculate innovation score (0-100)
    patents_per_year = len(patents) / max(years_back, 1)

    # Scoring factors:
    # - Volume: More patents = higher score (up to 50 points)
    # - Trend: Accelerating = bonus, declining = penalty
    # - Diversity: Multiple categories = bonus

    volume_score = min(patents_per_year * 2, 50)  # Max 50 points

    trend_bonus = {
        'accelerating': 20,
        'stable': 10,
        'new': 15,
        'declining': 0,
        'none': 0,
    }.get(trend, 0)

    diversity_score = min(len(categories) * 5, 20)  # Max 20 points

    # Recent activity bonus
    recent_bonus = min(len(recent_patents) * 2, 10)  # Max 10 points

    innovation_score = min(volume_score + trend_bonus + diversity_score + recent_bonus, 100)

    return {
        'patents_per_year': round(patents_per_year, 1),
        'yearly_counts': yearly_counts,
        'recent_patents': recent_patents,
        'recent_patent_count': len(recent_patents),
        'top_categories': top_categories_with_desc,
        'innovation_score': round(innovation_score),
        'trend': trend,
    }


def get_innovation_signal(ticker: str) -> Dict[str, Any]:
    """
    Get innovation signal for story scoring.

    Returns a simplified signal for integration with story scorer.
    """
    try:
        stats = get_patent_stats(ticker, years_back=3)

        # Determine signal strength
        score = stats.get('innovation_score', 0)
        trend = stats.get('trend', 'none')
        recent_count = stats.get('recent_patent_count', 0)

        if score >= 70 and trend == 'accelerating':
            signal = 'strong_innovator'
            signal_score = 25
        elif score >= 50 or (trend == 'accelerating' and recent_count > 3):
            signal = 'active_innovator'
            signal_score = 15
        elif score >= 30:
            signal = 'moderate_innovator'
            signal_score = 8
        elif score > 0:
            signal = 'some_patents'
            signal_score = 3
        else:
            signal = 'no_patents'
            signal_score = 0

        return {
            'ticker': ticker,
            'signal': signal,
            'signal_score': signal_score,
            'innovation_score': score,
            'trend': trend,
            'total_patents': stats.get('total_patents', 0),
            'recent_patents': stats.get('recent_patent_count', 0),
            'top_category': stats.get('top_categories', [{}])[0].get('description', 'N/A') if stats.get('top_categories') else 'N/A',
        }

    except Exception as e:
        return {
            'ticker': ticker,
            'signal': 'error',
            'signal_score': 0,
            'error': str(e),
        }


# Telegram command handler
def format_patent_report(ticker: str) -> str:
    """Format patent data for Telegram message."""
    stats = get_patent_stats(ticker, years_back=3)

    if stats.get('total_patents', 0) == 0:
        return f"*{ticker} Patent Activity*\n\nNo patents found for this company."

    # Build report
    lines = [
        f"*{ticker} Patent Activity*",
        f"_{', '.join(stats.get('company_names', [ticker]))}_",
        "",
        f"*Total Patents (3yr):* {stats['total_patents']}",
        f"*Patents/Year:* {stats['patents_per_year']}",
        f"*Innovation Score:* {stats['innovation_score']}/100",
        f"*Trend:* {stats['trend'].title()}",
        "",
    ]

    # Top categories
    if stats.get('top_categories'):
        lines.append("*Top Patent Categories:*")
        for cat in stats['top_categories'][:3]:
            lines.append(f"  {cat['section']}: {cat['description']} ({cat['count']})")
        lines.append("")

    # Recent patents
    if stats.get('recent_patents'):
        lines.append("*Recent Patents:*")
        for p in stats['recent_patents'][:5]:
            title = p['title'][:50] + '...' if len(p['title']) > 50 else p['title']
            lines.append(f"  - {title}")

    return '\n'.join(lines)


if __name__ == '__main__':
    # Test the integration
    test_tickers = ['NVDA', 'AAPL', 'TSLA']

    for ticker in test_tickers:
        print(f"\n{'='*50}")
        print(f"Testing {ticker}")
        print('='*50)

        signal = get_innovation_signal(ticker)
        print(f"Signal: {signal['signal']}")
        print(f"Score: {signal['innovation_score']}")
        print(f"Trend: {signal['trend']}")
        print(f"Total Patents: {signal['total_patents']}")
