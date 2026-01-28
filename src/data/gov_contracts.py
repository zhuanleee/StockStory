"""
Government Contracts Intelligence
=================================
Track federal contract awards as leading indicator for themes.

Government contracts signal future revenue 1-3 months ahead.
Large defense/infrastructure contracts → Theme tailwinds.

APIs Used:
- USAspending.gov API (FREE, no key required)
- SAM.gov API (FREE, key required for full access)

Docs:
- https://api.usaspending.gov/
- https://open.gsa.gov/api/sam-api/

Usage:
    from src.data.gov_contracts import (
        get_recent_contracts,
        get_theme_contract_activity,
        get_contract_trends,
    )

    # Get recent large contracts
    contracts = get_recent_contracts()

    # Get contract activity for a theme
    activity = get_theme_contract_activity('defense')
"""

import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import time

logger = logging.getLogger(__name__)

# API Endpoints
USASPENDING_BASE = "https://api.usaspending.gov/api/v2"

# Cache
DATA_DIR = Path("data/gov_contracts")
CACHE_FILE = DATA_DIR / "contract_cache.json"
CACHE_TTL = 43200  # 12 hours


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# Theme to contract keywords/agencies mapping
THEME_CONTRACT_KEYWORDS = {
    'defense': {
        'keywords': ['defense', 'military', 'weapon', 'missile', 'aircraft', 'navy', 'army', 'air force'],
        'agencies': ['Department of Defense', 'DEPT OF DEFENSE', 'DOD'],
        'naics': ['336411', '336414', '336415', '541715']  # Aerospace, missiles, etc.
    },
    'cybersecurity': {
        'keywords': ['cybersecurity', 'cyber', 'information security', 'network security'],
        'agencies': ['Department of Homeland Security', 'CISA', 'NSA'],
        'naics': ['541512', '541519']  # Computer systems, IT services
    },
    'infrastructure': {
        'keywords': ['construction', 'infrastructure', 'highway', 'bridge', 'building'],
        'agencies': ['Department of Transportation', 'Army Corps of Engineers'],
        'naics': ['237310', '237990', '236220']  # Highway, construction
    },
    'space': {
        'keywords': ['space', 'satellite', 'rocket', 'launch', 'NASA'],
        'agencies': ['NASA', 'Space Force', 'NOAA'],
        'naics': ['336414', '541712']  # Space vehicles, R&D
    },
    'nuclear': {
        'keywords': ['nuclear', 'reactor', 'uranium', 'atomic', 'DOE nuclear'],
        'agencies': ['Department of Energy', 'Nuclear Regulatory Commission'],
        'naics': ['221113', '541715']  # Nuclear power, R&D
    },
    'biotech': {
        'keywords': ['pharmaceutical', 'vaccine', 'medical', 'biotech', 'drug'],
        'agencies': ['HHS', 'NIH', 'FDA', 'BARDA'],
        'naics': ['325411', '325414', '541711']  # Pharma, bio R&D
    },
    'ai_chips': {
        'keywords': ['artificial intelligence', 'AI', 'semiconductor', 'chip', 'computing'],
        'agencies': ['DARPA', 'NSF'],
        'naics': ['334413', '541715']  # Semiconductors, R&D
    },
    'cloud': {
        'keywords': ['cloud', 'data center', 'cloud computing', 'AWS', 'Azure'],
        'agencies': ['GSA', 'DOD'],
        'naics': ['518210', '541512']  # Data processing, cloud
    },
    'ev': {
        'keywords': ['electric vehicle', 'EV', 'battery', 'charging station'],
        'agencies': ['Department of Energy', 'Department of Transportation'],
        'naics': ['335911', '336111']  # Batteries, vehicles
    },
    'solar': {
        'keywords': ['solar', 'renewable', 'clean energy', 'photovoltaic'],
        'agencies': ['Department of Energy'],
        'naics': ['221114', '334413']  # Solar electric, photovoltaic
    },
}

# Company to contract recipient mapping
COMPANY_RECIPIENTS = {
    'LMT': ['LOCKHEED MARTIN', 'Lockheed Martin'],
    'RTX': ['RAYTHEON', 'RTX CORPORATION', 'Raytheon'],
    'NOC': ['NORTHROP GRUMMAN', 'Northrop Grumman'],
    'BA': ['BOEING', 'Boeing'],
    'GD': ['GENERAL DYNAMICS', 'General Dynamics'],
    'HII': ['HUNTINGTON INGALLS', 'Huntington Ingalls'],
    'LHX': ['L3HARRIS', 'L3 Harris'],
    'RKLB': ['ROCKET LAB', 'Rocket Lab'],
    'AMZN': ['AMAZON', 'Amazon Web Services', 'AWS'],
    'MSFT': ['MICROSOFT', 'Microsoft'],
    'GOOGL': ['GOOGLE', 'Google'],
    'ORCL': ['ORACLE', 'Oracle'],
    'CRM': ['SALESFORCE', 'Salesforce'],
    'PLTR': ['PALANTIR', 'Palantir'],
}


@dataclass
class Contract:
    """Government contract data."""
    contract_id: str
    description: str
    recipient: str
    awarding_agency: str
    amount: float
    award_date: str
    period_of_performance: str
    naics_code: str
    naics_description: str


@dataclass
class ContractActivity:
    """Contract activity summary."""
    entity: str
    entity_type: str  # 'theme' or 'company'
    total_value: float
    contract_count: int
    recent_contracts: List[Dict]
    trend: str
    mom_change: float  # Month-over-month change
    top_agencies: List[str]
    signal_strength: float


class GovContractIntelligence:
    """
    Government contract intelligence using USAspending API.
    """

    def __init__(self):
        ensure_data_dir()
        self.cache = self._load_cache()
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })

    def _load_cache(self) -> Dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except:
                pass
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

    def search_contracts(
        self,
        keywords: List[str] = None,
        agencies: List[str] = None,
        naics_codes: List[str] = None,
        min_amount: float = 1000000,  # $1M minimum
        days_back: int = 90
    ) -> List[Contract]:
        """
        Search for government contracts.
        """
        cache_key = f"search:{','.join(keywords or [])}:{days_back}"
        cached = self._get_cached(cache_key)
        if cached:
            return [Contract(**c) for c in cached]

        try:
            url = f"{USASPENDING_BASE}/search/spending_by_award/"

            # Date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Build filters
            filters = {
                "time_period": [
                    {
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d")
                    }
                ],
                "award_type_codes": ["A", "B", "C", "D"],  # Contracts only
            }

            if keywords:
                filters["keywords"] = keywords

            if naics_codes:
                filters["naics_codes"] = naics_codes

            payload = {
                "filters": filters,
                "fields": [
                    "Award ID",
                    "Description",
                    "Recipient Name",
                    "Awarding Agency",
                    "Award Amount",
                    "Start Date",
                    "End Date",
                    "NAICS Code",
                    "NAICS Description"
                ],
                "page": 1,
                "limit": 100,
                "sort": "Award Amount",
                "order": "desc"
            }

            response = self.session.post(url, json=payload, timeout=30)

            if response.status_code != 200:
                logger.error(f"USAspending API error: {response.status_code}")
                return []

            data = response.json()
            results = data.get('results', [])

            contracts = []
            for r in results:
                amount = r.get('Award Amount', 0)
                if amount and amount >= min_amount:
                    contract = Contract(
                        contract_id=r.get('Award ID', ''),
                        description=r.get('Description', '')[:200] if r.get('Description') else '',
                        recipient=r.get('Recipient Name', ''),
                        awarding_agency=r.get('Awarding Agency', ''),
                        amount=float(amount),
                        award_date=r.get('Start Date', ''),
                        period_of_performance=f"{r.get('Start Date', '')} to {r.get('End Date', '')}",
                        naics_code=r.get('NAICS Code', ''),
                        naics_description=r.get('NAICS Description', '')
                    )
                    contracts.append(contract)

            # Cache results
            self._set_cache(cache_key, [asdict(c) for c in contracts])

            return contracts

        except Exception as e:
            logger.error(f"Contract search error: {e}")
            return []

    def get_recent_large_contracts(self, min_amount: float = 10000000) -> List[Contract]:
        """
        Get recent large contracts (>$10M by default).
        """
        cache_key = f"large:{min_amount}"
        cached = self._get_cached(cache_key)
        if cached:
            return [Contract(**c) for c in cached]

        try:
            url = f"{USASPENDING_BASE}/search/spending_by_award/"

            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            payload = {
                "filters": {
                    "time_period": [
                        {
                            "start_date": start_date.strftime("%Y-%m-%d"),
                            "end_date": end_date.strftime("%Y-%m-%d")
                        }
                    ],
                    "award_type_codes": ["A", "B", "C", "D"],
                    "award_amounts": [
                        {"lower_bound": min_amount}
                    ]
                },
                "fields": [
                    "Award ID", "Description", "Recipient Name",
                    "Awarding Agency", "Award Amount", "Start Date",
                    "NAICS Code", "NAICS Description"
                ],
                "page": 1,
                "limit": 50,
                "sort": "Award Amount",
                "order": "desc"
            }

            response = self.session.post(url, json=payload, timeout=30)

            if response.status_code != 200:
                return []

            data = response.json()
            results = data.get('results', [])

            contracts = []
            for r in results:
                contract = Contract(
                    contract_id=r.get('Award ID', ''),
                    description=r.get('Description', '')[:200] if r.get('Description') else '',
                    recipient=r.get('Recipient Name', ''),
                    awarding_agency=r.get('Awarding Agency', ''),
                    amount=float(r.get('Award Amount', 0)),
                    award_date=r.get('Start Date', ''),
                    period_of_performance='',
                    naics_code=r.get('NAICS Code', ''),
                    naics_description=r.get('NAICS Description', '')
                )
                contracts.append(contract)

            self._set_cache(cache_key, [asdict(c) for c in contracts])

            return contracts

        except Exception as e:
            logger.error(f"Large contracts error: {e}")
            return []

    def get_theme_contract_activity(self, theme_id: str) -> ContractActivity:
        """
        Get contract activity for a theme.
        """
        cache_key = f"theme:{theme_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return ContractActivity(**cached)

        theme_config = THEME_CONTRACT_KEYWORDS.get(theme_id, {})
        keywords = theme_config.get('keywords', [])
        naics = theme_config.get('naics', [])

        if not keywords and not naics:
            return ContractActivity(
                entity=theme_id,
                entity_type='theme',
                total_value=0,
                contract_count=0,
                recent_contracts=[],
                trend='unknown',
                mom_change=0,
                top_agencies=[],
                signal_strength=0
            )

        # Get recent contracts
        contracts = self.search_contracts(
            keywords=keywords[:3],
            naics_codes=naics,
            min_amount=1000000,
            days_back=90
        )

        total_value = sum(c.amount for c in contracts)
        contract_count = len(contracts)

        # Calculate month-over-month (simplified)
        now = datetime.now()
        this_month = [c for c in contracts if c.award_date and c.award_date >= (now - timedelta(days=30)).strftime('%Y-%m-%d')]
        last_month = [c for c in contracts if c.award_date and
                      (now - timedelta(days=60)).strftime('%Y-%m-%d') <= c.award_date < (now - timedelta(days=30)).strftime('%Y-%m-%d')]

        this_month_value = sum(c.amount for c in this_month)
        last_month_value = sum(c.amount for c in last_month)

        if last_month_value > 0:
            mom_change = ((this_month_value - last_month_value) / last_month_value) * 100
        else:
            mom_change = 100 if this_month_value > 0 else 0

        if mom_change > 20:
            trend = 'increasing'
        elif mom_change < -20:
            trend = 'decreasing'
        else:
            trend = 'stable'

        # Top agencies
        agency_counts = {}
        for c in contracts:
            agency = c.awarding_agency
            if agency:
                agency_counts[agency] = agency_counts.get(agency, 0) + 1
        top_agencies = sorted(agency_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        # Signal strength
        signal = min(1.0, total_value / 1e10)  # $10B = max signal
        if trend == 'increasing':
            signal = min(1.0, signal * 1.3)

        activity = ContractActivity(
            entity=theme_id,
            entity_type='theme',
            total_value=total_value,
            contract_count=contract_count,
            recent_contracts=[
                {
                    'recipient': c.recipient,
                    'amount': c.amount,
                    'date': c.award_date,
                    'agency': c.awarding_agency
                }
                for c in contracts[:10]
            ],
            trend=trend,
            mom_change=round(mom_change, 1),
            top_agencies=[a[0] for a in top_agencies],
            signal_strength=round(signal, 2)
        )

        self._set_cache(cache_key, asdict(activity))

        return activity

    def get_company_contracts(self, ticker: str) -> ContractActivity:
        """
        Get contract activity for a company.
        """
        cache_key = f"company:{ticker}"
        cached = self._get_cached(cache_key)
        if cached:
            return ContractActivity(**cached)

        recipients = COMPANY_RECIPIENTS.get(ticker.upper(), [])
        if not recipients:
            recipients = [ticker.upper()]

        try:
            url = f"{USASPENDING_BASE}/search/spending_by_award/"

            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)

            all_contracts = []

            for recipient in recipients:
                payload = {
                    "filters": {
                        "time_period": [
                            {
                                "start_date": start_date.strftime("%Y-%m-%d"),
                                "end_date": end_date.strftime("%Y-%m-%d")
                            }
                        ],
                        "award_type_codes": ["A", "B", "C", "D"],
                        "recipient_search_text": [recipient]
                    },
                    "fields": [
                        "Award ID", "Description", "Recipient Name",
                        "Awarding Agency", "Award Amount", "Start Date"
                    ],
                    "page": 1,
                    "limit": 50,
                    "sort": "Award Amount",
                    "order": "desc"
                }

                response = self.session.post(url, json=payload, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])

                    for r in results:
                        contract = Contract(
                            contract_id=r.get('Award ID', ''),
                            description=r.get('Description', '')[:200] if r.get('Description') else '',
                            recipient=r.get('Recipient Name', ''),
                            awarding_agency=r.get('Awarding Agency', ''),
                            amount=float(r.get('Award Amount', 0) or 0),
                            award_date=r.get('Start Date', ''),
                            period_of_performance='',
                            naics_code='',
                            naics_description=''
                        )
                        all_contracts.append(contract)

                time.sleep(0.5)

            total_value = sum(c.amount for c in all_contracts)
            contract_count = len(all_contracts)

            # Agency breakdown
            agency_counts = {}
            for c in all_contracts:
                if c.awarding_agency:
                    agency_counts[c.awarding_agency] = agency_counts.get(c.awarding_agency, 0) + 1

            activity = ContractActivity(
                entity=ticker,
                entity_type='company',
                total_value=total_value,
                contract_count=contract_count,
                recent_contracts=[
                    {'amount': c.amount, 'date': c.award_date, 'agency': c.awarding_agency}
                    for c in all_contracts[:10]
                ],
                trend='unknown',
                mom_change=0,
                top_agencies=sorted(agency_counts.keys(), key=lambda x: agency_counts[x], reverse=True)[:3],
                signal_strength=min(1.0, total_value / 1e10)
            )

            self._set_cache(cache_key, asdict(activity))

            return activity

        except Exception as e:
            logger.error(f"Company contracts error: {e}")
            return ContractActivity(
                entity=ticker, entity_type='company',
                total_value=0, contract_count=0,
                recent_contracts=[], trend='unknown',
                mom_change=0, top_agencies=[], signal_strength=0
            )

    def get_all_themes_contract_activity(self) -> Dict:
        """
        Get contract activity for all tracked themes.
        """
        results = {}

        for theme_id in THEME_CONTRACT_KEYWORDS.keys():
            try:
                activity = self.get_theme_contract_activity(theme_id)
                results[theme_id] = asdict(activity)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Error getting contracts for {theme_id}: {e}")
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
            'top_contract_themes': [t[0] for t in sorted_themes[:5] if t[1].get('trend') == 'increasing'],
            'high_value_themes': [t[0] for t in sorted_themes if t[1].get('total_value', 0) > 1e9][:5]
        }


# =============================================================================
# SINGLETON & CONVENIENCE
# =============================================================================

_contract_intel = None


def get_contract_intelligence() -> GovContractIntelligence:
    global _contract_intel
    if _contract_intel is None:
        _contract_intel = GovContractIntelligence()
    return _contract_intel


def get_recent_contracts(min_amount: float = 10000000) -> List[Dict]:
    """Get recent large contracts."""
    contracts = get_contract_intelligence().get_recent_large_contracts(min_amount)
    return [asdict(c) for c in contracts]


def get_theme_contract_activity(theme_id: str) -> Dict:
    """Get contract activity for a theme."""
    activity = get_contract_intelligence().get_theme_contract_activity(theme_id)
    return asdict(activity)


def get_contract_trends() -> Dict:
    """Get contract trends for all themes."""
    return get_contract_intelligence().get_all_themes_contract_activity()


def get_company_contracts(ticker: str) -> Dict:
    """Get contracts for a company."""
    activity = get_contract_intelligence().get_company_contracts(ticker)
    return asdict(activity)


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_contracts_message(data: Dict) -> str:
    """Format contract data for Telegram."""
    if not data.get('ok'):
        return f"Error: {data.get('error', 'Unknown')}"

    msg = "🏛️ *GOVERNMENT CONTRACTS*\n"
    msg += "_Federal spending leading indicator_\n\n"

    # Top contract themes
    top = data.get('top_contract_themes', [])
    if top:
        msg += "📈 *INCREASING CONTRACT ACTIVITY:*\n"
        themes = data.get('themes', {})
        for theme_id in top[:5]:
            theme_data = themes.get(theme_id, {})
            value = theme_data.get('total_value', 0)
            mom = theme_data.get('mom_change', 0)
            msg += f"• `{theme_id.upper()}` | ${value/1e9:.1f}B | +{mom:.0f}% MoM\n"
        msg += "\n"

    # High value themes
    high_value = data.get('high_value_themes', [])
    if high_value:
        msg += "💰 *HIGHEST CONTRACT VALUE:*\n"
        themes = data.get('themes', {})
        for theme_id in high_value[:5]:
            if theme_id not in top:  # Don't repeat
                theme_data = themes.get(theme_id, {})
                value = theme_data.get('total_value', 0)
                count = theme_data.get('contract_count', 0)
                msg += f"• `{theme_id.upper()}` | ${value/1e9:.1f}B | {count} contracts\n"

    msg += "\n_Contracts signal revenue 1-3 months ahead_"

    return msg


if __name__ == "__main__":
    print("Government Contract Intelligence")
    print("=" * 50)

    intel = GovContractIntelligence()

    print("\nGetting recent large contracts...")
    contracts = intel.get_recent_large_contracts(min_amount=50000000)
    print(f"Found {len(contracts)} contracts > $50M")

    for c in contracts[:5]:
        print(f"  - ${c.amount/1e6:.0f}M: {c.recipient[:30]} ({c.awarding_agency})")

    print("\nGetting DEFENSE theme activity...")
    activity = intel.get_theme_contract_activity('defense')
    print(f"  Total value: ${activity.total_value/1e9:.1f}B")
    print(f"  Contracts: {activity.contract_count}")
    print(f"  Trend: {activity.trend}")
