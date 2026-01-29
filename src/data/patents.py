"""
Patent Intelligence (PatentsView API)
=====================================
Track patent filings as leading indicator for R&D themes.

Patents are filed 6-12 months before products launch.
Surge in patents → Company investing heavily in area.

API: PatentsView PatentSearch API (USPTO)
- FREE but requires API key (get from patentsview.org)
- Rate Limit: 45 requests/minute
- Docs: https://search.patentsview.org/docs/

Set PATENTSVIEW_API_KEY environment variable to enable.
Without API key, returns cached/demo data only.

Usage:
    from src.data.patents import (
        get_company_patents,
        get_theme_patent_activity,
        get_patent_trends,
    )

    # Get recent patents for a company
    patents = get_company_patents('NVDA')

    # Get patent activity for a theme
    activity = get_theme_patent_activity('ai_chips')

    # Get trending patent keywords
    trends = get_patent_trends()
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import time

logger = logging.getLogger(__name__)

# PatentsView PatentSearch API (new API as of May 2025)
PATENTSVIEW_BASE = "https://search.patentsview.org/api/v1"
PATENTSVIEW_API_KEY = os.environ.get('PATENTSVIEW_API_KEY', '')

# Cache
DATA_DIR = Path("data/patents")
CACHE_FILE = DATA_DIR / "patent_cache.json"
CACHE_TTL = 86400  # 24 hours


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# Company name to assignee mapping (for patent search)
COMPANY_ASSIGNEES = {
    'NVDA': ['NVIDIA'],
    'AMD': ['Advanced Micro Devices'],
    'INTC': ['Intel Corporation'],
    'GOOGL': ['Google', 'Alphabet'],
    'MSFT': ['Microsoft'],
    'AAPL': ['Apple Inc'],
    'META': ['Meta Platforms', 'Facebook'],
    'AMZN': ['Amazon'],
    'TSLA': ['Tesla'],
    'IBM': ['International Business Machines'],
    'QCOM': ['Qualcomm'],
    'AVGO': ['Broadcom'],
    'ARM': ['Arm Limited', 'ARM Holdings'],
    'TSM': ['Taiwan Semiconductor'],
    'SMR': ['NuScale', 'SMR'],
    'LMT': ['Lockheed Martin'],
    'RTX': ['Raytheon', 'RTX'],
    'NOC': ['Northrop Grumman'],
    'BA': ['Boeing'],
    'CRWD': ['CrowdStrike'],
    'PANW': ['Palo Alto Networks'],
    'LLY': ['Eli Lilly'],
    'NVO': ['Novo Nordisk'],
    'MRNA': ['Moderna'],
    'PFE': ['Pfizer'],
    'ISRG': ['Intuitive Surgical'],
    'IONQ': ['IonQ'],
}

# Theme to patent keywords mapping
THEME_PATENT_KEYWORDS = {
    'ai_chips': ['artificial intelligence', 'neural network', 'machine learning', 'GPU', 'tensor', 'deep learning'],
    'nuclear': ['nuclear reactor', 'small modular reactor', 'uranium', 'fission', 'nuclear fuel'],
    'ev': ['electric vehicle', 'battery', 'lithium ion', 'charging station', 'electric motor'],
    'quantum': ['quantum computing', 'qubit', 'quantum processor', 'quantum algorithm'],
    'cybersecurity': ['cybersecurity', 'encryption', 'authentication', 'intrusion detection', 'firewall'],
    'robotics': ['robot', 'autonomous', 'humanoid', 'industrial automation', 'robotic arm'],
    'biotech': ['gene therapy', 'CRISPR', 'mRNA', 'antibody', 'immunotherapy'],
    'weight_loss': ['GLP-1', 'obesity', 'weight loss', 'appetite', 'metabolic'],
    'space': ['satellite', 'spacecraft', 'rocket', 'orbital', 'space launch'],
    'solar': ['solar cell', 'photovoltaic', 'solar panel', 'renewable energy'],
    'defense': ['missile', 'radar', 'military', 'defense system', 'stealth'],
    'cloud': ['cloud computing', 'distributed computing', 'data center', 'virtualization'],
    'fintech': ['blockchain', 'cryptocurrency', 'digital payment', 'financial technology'],
    'metaverse': ['virtual reality', 'augmented reality', 'VR headset', '3D rendering'],
}


@dataclass
class Patent:
    """Patent data."""
    patent_id: str
    title: str
    abstract: str
    assignee: str
    inventors: List[str]
    grant_date: str
    application_date: str
    cpc_codes: List[str]  # Classification codes
    claims_count: int


@dataclass
class PatentActivity:
    """Patent activity summary for a theme/company."""
    entity: str  # theme_id or ticker
    entity_type: str  # 'theme' or 'company'
    patent_count: int
    recent_patents: List[Dict]
    trend: str  # 'increasing', 'stable', 'decreasing'
    yoy_change: float  # Year-over-year change
    top_keywords: List[str]
    signal_strength: float  # 0-1


class PatentIntelligence:
    """
    Patent intelligence using PatentsView PatentSearch API.

    Requires PATENTSVIEW_API_KEY environment variable.
    Get your free API key at: https://patentsview.org/
    """

    def __init__(self):
        ensure_data_dir()
        self.cache = self._load_cache()
        self.api_key = PATENTSVIEW_API_KEY
        self.session = requests.Session()
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if self.api_key:
            headers['X-Api-Key'] = self.api_key
        self.session.headers.update(headers)

    def _api_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def _load_cache(self) -> Dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load patents cache: {e}")
        return {}

    def _save_cache(self):
        with open(CACHE_FILE, 'w') as f:
            json.dump(self.cache, f, indent=2)

    def _get_cached(self, key: str) -> Optional[Dict]:
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now().timestamp() < entry.get('expires', 0):
                return entry.get('data')
        return None

    def _set_cache(self, key: str, data: Dict):
        self.cache[key] = {
            'data': data,
            'expires': datetime.now().timestamp() + CACHE_TTL
        }
        self._save_cache()

    def search_patents(
        self,
        query: str,
        years_back: int = 2,
        per_page: int = 25
    ) -> List[Patent]:
        """
        Search patents by keyword.

        Args:
            query: Search term (title/abstract)
            years_back: How many years to search
            per_page: Results per page (max 1000)
        """
        cache_key = f"search:{query}:{years_back}"
        cached = self._get_cached(cache_key)
        if cached:
            return [Patent(**p) for p in cached]

        # Check if API key is available
        if not self._api_available():
            logger.warning("PatentsView API key not set. Set PATENTSVIEW_API_KEY env var.")
            return []

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years_back * 365)

            # New PatentSearch API endpoint and format
            url = f"{PATENTSVIEW_BASE}/patent/"

            # Query format for new PatentSearch API (GET with query params)
            q_filter = {
                "_and": [
                    {"_text_phrase": {"patent_abstract": query}},
                    {"_gte": {"patent_date": start_date.strftime("%Y-%m-%d")}},
                    {"_lte": {"patent_date": end_date.strftime("%Y-%m-%d")}}
                ]
            }

            params = {
                "q": json.dumps(q_filter),
                "f": json.dumps([
                    "patent_id",
                    "patent_title",
                    "patent_abstract",
                    "patent_date",
                    "assignees",
                    "inventors"
                ]),
                "o": json.dumps({"size": per_page}),
                "s": json.dumps([{"patent_date": "desc"}])
            }

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code != 200:
                logger.error(f"PatentsView API error: {response.status_code}")
                return []

            data = response.json()
            patents_data = data.get('patents', [])

            patents = []
            for p in patents_data:
                # Extract inventors
                inventors = []
                if p.get('inventors'):
                    for inv in p['inventors'][:5]:
                        name = f"{inv.get('inventor_first_name', '')} {inv.get('inventor_last_name', '')}".strip()
                        if name:
                            inventors.append(name)

                # Extract assignee
                assignee = ''
                if p.get('assignees'):
                    assignee = p['assignees'][0].get('assignee_organization', '') if p['assignees'] else ''

                patent = Patent(
                    patent_id=p.get('patent_id', ''),
                    title=p.get('patent_title', ''),
                    abstract=p.get('patent_abstract', '')[:500] if p.get('patent_abstract') else '',
                    assignee=assignee,
                    inventors=inventors,
                    grant_date=p.get('patent_date', ''),
                    application_date='',
                    cpc_codes=[],
                    claims_count=0
                )
                patents.append(patent)

            # Cache results
            self._set_cache(cache_key, [asdict(p) for p in patents])

            return patents

        except Exception as e:
            logger.error(f"Patent search error: {e}")
            return []

    def get_company_patents(self, ticker: str, years_back: int = 2) -> PatentActivity:
        """
        Get patent activity for a company.
        """
        cache_key = f"company:{ticker}:{years_back}"
        cached = self._get_cached(cache_key)
        if cached:
            return PatentActivity(**cached)

        # Check if API key is available
        if not self._api_available():
            logger.warning("PatentsView API key not set. Returning empty activity.")
            return PatentActivity(
                entity=ticker,
                entity_type='company',
                patent_count=0,
                recent_patents=[],
                trend='unknown',
                yoy_change=0,
                top_keywords=[],
                signal_strength=0.0
            )

        assignees = COMPANY_ASSIGNEES.get(ticker.upper(), [ticker])

        all_patents = []
        for assignee in assignees:
            try:
                # New PatentSearch API endpoint
                url = f"{PATENTSVIEW_BASE}/patent/"

                end_date = datetime.now()
                start_date = end_date - timedelta(days=years_back * 365)

                q_filter = {
                    "_and": [
                        {"_contains": {"assignees.assignee_organization": assignee}},
                        {"_gte": {"patent_date": start_date.strftime("%Y-%m-%d")}}
                    ]
                }

                params = {
                    "q": json.dumps(q_filter),
                    "f": json.dumps(["patent_id", "patent_title", "patent_date", "patent_abstract"]),
                    "o": json.dumps({"size": 100}),
                    "s": json.dumps([{"patent_date": "desc"}])
                }

                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    patents = data.get('patents', [])
                    all_patents.extend(patents)

                time.sleep(1.5)  # Rate limiting (45 req/min = 1.3s/req)

            except Exception as e:
                logger.debug(f"Patent fetch error for {assignee}: {e}")
                continue

        # Calculate metrics
        patent_count = len(all_patents)

        # Calculate YoY change
        now = datetime.now()
        this_year = [p for p in all_patents if p.get('patent_date', '').startswith(str(now.year))]
        last_year = [p for p in all_patents if p.get('patent_date', '').startswith(str(now.year - 1))]

        if last_year:
            # Annualize this year's count
            days_elapsed = (now - datetime(now.year, 1, 1)).days
            annualized = len(this_year) * (365 / max(days_elapsed, 1))
            yoy_change = ((annualized - len(last_year)) / len(last_year)) * 100
        else:
            yoy_change = 0

        # Determine trend
        if yoy_change > 20:
            trend = 'increasing'
        elif yoy_change < -20:
            trend = 'decreasing'
        else:
            trend = 'stable'

        # Signal strength based on patent count and trend
        signal = min(1.0, patent_count / 100)
        if trend == 'increasing':
            signal = min(1.0, signal * 1.3)

        activity = PatentActivity(
            entity=ticker,
            entity_type='company',
            patent_count=patent_count,
            recent_patents=[
                {'title': p.get('patent_title', ''), 'date': p.get('patent_date', '')}
                for p in all_patents[:10]
            ],
            trend=trend,
            yoy_change=round(yoy_change, 1),
            top_keywords=[],
            signal_strength=round(signal, 2)
        )

        self._set_cache(cache_key, asdict(activity))

        return activity

    def get_theme_patent_activity(self, theme_id: str) -> PatentActivity:
        """
        Get patent activity for a theme based on keywords.
        """
        cache_key = f"theme:{theme_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return PatentActivity(**cached)

        keywords = THEME_PATENT_KEYWORDS.get(theme_id, [])
        if not keywords:
            return PatentActivity(
                entity=theme_id,
                entity_type='theme',
                patent_count=0,
                recent_patents=[],
                trend='unknown',
                yoy_change=0,
                top_keywords=[],
                signal_strength=0
            )

        all_patents = []

        # Search for each keyword
        for keyword in keywords[:3]:  # Limit to avoid rate limits
            patents = self.search_patents(keyword, years_back=2, per_page=50)
            all_patents.extend(patents)
            time.sleep(1)  # Rate limiting

        # Deduplicate by patent_id
        seen = set()
        unique_patents = []
        for p in all_patents:
            if p.patent_id not in seen:
                seen.add(p.patent_id)
                unique_patents.append(p)

        patent_count = len(unique_patents)

        # Calculate trend (simplified)
        now = datetime.now()
        recent = [p for p in unique_patents if p.grant_date and p.grant_date >= (now - timedelta(days=180)).strftime('%Y-%m-%d')]
        older = [p for p in unique_patents if p.grant_date and p.grant_date < (now - timedelta(days=180)).strftime('%Y-%m-%d')]

        if older:
            ratio = len(recent) / max(len(older), 1)
            if ratio > 1.2:
                trend = 'increasing'
                yoy_change = (ratio - 1) * 100
            elif ratio < 0.8:
                trend = 'decreasing'
                yoy_change = (ratio - 1) * 100
            else:
                trend = 'stable'
                yoy_change = 0
        else:
            trend = 'unknown'
            yoy_change = 0

        signal = min(1.0, patent_count / 200)
        if trend == 'increasing':
            signal = min(1.0, signal * 1.3)

        activity = PatentActivity(
            entity=theme_id,
            entity_type='theme',
            patent_count=patent_count,
            recent_patents=[
                {'title': p.title, 'date': p.grant_date, 'assignee': p.assignee}
                for p in unique_patents[:10]
            ],
            trend=trend,
            yoy_change=round(yoy_change, 1),
            top_keywords=keywords,
            signal_strength=round(signal, 2)
        )

        self._set_cache(cache_key, asdict(activity))

        return activity

    def get_all_themes_patent_activity(self) -> Dict:
        """
        Get patent activity for all tracked themes.
        """
        # Check if API key is available
        if not self._api_available():
            return {
                'ok': False,
                'error': 'API key required',
                'message': 'Set PATENTSVIEW_API_KEY env var. Get free key at patentsview.org',
                'timestamp': datetime.now().isoformat(),
                'themes': {},
                'top_patent_themes': [],
                'declining_patent_themes': []
            }

        results = {}

        for theme_id in THEME_PATENT_KEYWORDS.keys():
            try:
                activity = self.get_theme_patent_activity(theme_id)
                results[theme_id] = asdict(activity)
            except Exception as e:
                logger.error(f"Error getting patents for {theme_id}: {e}")
                continue

        # Sort by signal strength
        sorted_themes = sorted(
            results.items(),
            key=lambda x: x[1].get('signal_strength', 0),
            reverse=True
        )

        return {
            'ok': True,
            'timestamp': datetime.now().isoformat(),
            'themes': dict(sorted_themes),
            'top_patent_themes': [t[0] for t in sorted_themes[:5] if t[1].get('trend') == 'increasing'],
            'declining_patent_themes': [t[0] for t in sorted_themes if t[1].get('trend') == 'decreasing']
        }


# =============================================================================
# SINGLETON & CONVENIENCE
# =============================================================================

_patent_intel = None


def get_patent_intelligence() -> PatentIntelligence:
    global _patent_intel
    if _patent_intel is None:
        _patent_intel = PatentIntelligence()
    return _patent_intel


def get_company_patents(ticker: str) -> Dict:
    """Get patent activity for a company."""
    activity = get_patent_intelligence().get_company_patents(ticker)
    return asdict(activity)


def get_theme_patent_activity(theme_id: str) -> Dict:
    """Get patent activity for a theme."""
    activity = get_patent_intelligence().get_theme_patent_activity(theme_id)
    return asdict(activity)


def get_patent_trends() -> Dict:
    """Get patent trends for all themes."""
    return get_patent_intelligence().get_all_themes_patent_activity()


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_patent_message(data: Dict) -> str:
    """Format patent data for Telegram."""
    if not data.get('ok'):
        error = data.get('error', 'Unknown')
        if error == 'API key required':
            msg = "📜 *PATENT INTELLIGENCE*\n\n"
            msg += "⚠️ *API Key Required*\n\n"
            msg += "PatentsView API now requires a free API key.\n\n"
            msg += "*To enable:*\n"
            msg += "1. Get free key at patentsview.org\n"
            msg += "2. Set `PATENTSVIEW_API_KEY` env var\n"
            msg += "3. Restart the bot\n"
            return msg
        return f"Error: {error}"

    msg = "📜 *PATENT INTELLIGENCE*\n"
    msg += "_R&D leading indicator (6-12 months ahead)_\n\n"

    # Top patent themes
    top = data.get('top_patent_themes', [])
    if top:
        msg += "📈 *INCREASING PATENT ACTIVITY:*\n"
        themes = data.get('themes', {})
        for theme_id in top[:5]:
            theme_data = themes.get(theme_id, {})
            count = theme_data.get('patent_count', 0)
            yoy = theme_data.get('yoy_change', 0)
            msg += f"• `{theme_id.upper()}` | {count} patents | +{yoy:.0f}% YoY\n"
        msg += "\n"

    # Declining
    declining = data.get('declining_patent_themes', [])
    if declining:
        msg += "📉 *DECLINING PATENT ACTIVITY:*\n"
        themes = data.get('themes', {})
        for theme_id in declining[:3]:
            theme_data = themes.get(theme_id, {})
            yoy = theme_data.get('yoy_change', 0)
            msg += f"• `{theme_id.upper()}` | {yoy:.0f}% YoY\n"
        msg += "\n"

    msg += "_Patents filed 6-12 months before product launch_"

    return msg


if __name__ == "__main__":
    print("Patent Intelligence")
    print("=" * 50)

    intel = PatentIntelligence()

    print("\nSearching AI patents...")
    patents = intel.search_patents("artificial intelligence", years_back=1, per_page=10)
    print(f"Found {len(patents)} patents")

    for p in patents[:3]:
        print(f"  - {p.title[:60]}... ({p.grant_date})")

    print("\nGetting AI_CHIPS theme activity...")
    activity = intel.get_theme_patent_activity('ai_chips')
    print(f"  Patents: {activity.patent_count}")
    print(f"  Trend: {activity.trend}")
    print(f"  Signal: {activity.signal_strength}")
