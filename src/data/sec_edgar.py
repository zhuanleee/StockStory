"""
SEC EDGAR Integration
=====================
Fetch and parse SEC filings for M&A intelligence.

Key Filings for M&A:
- 8-K: Material events (deal announcements, terminations)
- DEFM14A: Definitive merger proxy (shareholder vote)
- S-4: Registration statement (stock-based mergers)
- SC 13D: Activist investors (>5% ownership with intent)
- SC 13G: Passive investors (>5% ownership)
- 13F-HR: Institutional holdings (quarterly)

SEC EDGAR API:
- Free, no API key required
- Rate limit: 10 requests/second
- User-Agent required (identify yourself)
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# SEC requires identification
USER_AGENT = os.environ.get('SEC_USER_AGENT', 'StockScannerBot/1.0 (contact@example.com)')
SEC_BASE_URL = "https://data.sec.gov"
SEC_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"


@dataclass
class SECFiling:
    """Represents an SEC filing."""
    form_type: str
    ticker: str
    company_name: str
    filed_date: str
    accession_number: str
    description: str
    url: str

    def to_dict(self) -> Dict:
        return {
            'form_type': self.form_type,
            'ticker': self.ticker,
            'company_name': self.company_name,
            'filed_date': self.filed_date,
            'accession_number': self.accession_number,
            'description': self.description,
            'url': self.url
        }


class SECEdgarClient:
    """
    SEC EDGAR API client for M&A intelligence.

    Usage:
        client = SECEdgarClient()

        # Get recent M&A filings
        filings = client.get_merger_filings('AAPL', days_back=30)

        # Get 8-K material events
        events = client.get_material_events('NVDA')

        # Get institutional ownership
        holders = client.get_institutional_holders('TSLA')
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'application/json'
        })

    def _get_cik(self, ticker: str) -> Optional[str]:
        """
        Get CIK (Central Index Key) for a ticker.
        CIK is SEC's unique identifier for companies.
        """
        try:
            # SEC provides a ticker->CIK mapping
            url = f"{SEC_BASE_URL}/submissions/CIK{ticker.upper()}.json"

            # Try direct lookup first
            response = self.session.get(
                f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=&dateb=&owner=include&count=1&output=json",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if 'results' in data and data['results']:
                    cik = data['results'][0].get('cik')
                    if cik:
                        return cik.zfill(10)  # CIK must be 10 digits

            # Fallback: use the company tickers JSON
            tickers_url = "https://www.sec.gov/files/company_tickers.json"
            response = self.session.get(tickers_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                for entry in data.values():
                    if entry.get('ticker', '').upper() == ticker.upper():
                        return str(entry.get('cik_str', '')).zfill(10)

            return None
        except Exception as e:
            logger.error(f"Error getting CIK for {ticker}: {e}")
            return None

    def get_company_filings(
        self,
        ticker: str,
        form_types: List[str] = None,
        days_back: int = 90
    ) -> List[SECFiling]:
        """
        Get recent filings for a company.

        Args:
            ticker: Stock symbol
            form_types: Filter by form types (e.g., ['8-K', 'DEFM14A'])
            days_back: How far back to look
        """
        cik = self._get_cik(ticker)
        if not cik:
            logger.warning(f"Could not find CIK for {ticker}")
            return []

        try:
            url = f"{SEC_BASE_URL}/submissions/CIK{cik}.json"
            response = self.session.get(url, timeout=15)

            if response.status_code != 200:
                logger.error(f"SEC API error: {response.status_code}")
                return []

            data = response.json()
            company_name = data.get('name', ticker)

            filings = []
            recent = data.get('filings', {}).get('recent', {})

            forms = recent.get('form', [])
            dates = recent.get('filingDate', [])
            accessions = recent.get('accessionNumber', [])
            descriptions = recent.get('primaryDocDescription', [])

            cutoff_date = datetime.now() - timedelta(days=days_back)

            for i in range(min(len(forms), 100)):  # Check last 100 filings
                form_type = forms[i] if i < len(forms) else ''
                filed_date = dates[i] if i < len(dates) else ''
                accession = accessions[i] if i < len(accessions) else ''
                description = descriptions[i] if i < len(descriptions) else ''

                # Filter by form type
                if form_types and form_type not in form_types:
                    continue

                # Filter by date
                try:
                    filing_date = datetime.strptime(filed_date, '%Y-%m-%d')
                    if filing_date < cutoff_date:
                        continue
                except:
                    continue

                # Build filing URL
                accession_clean = accession.replace('-', '')
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}"

                filings.append(SECFiling(
                    form_type=form_type,
                    ticker=ticker.upper(),
                    company_name=company_name,
                    filed_date=filed_date,
                    accession_number=accession,
                    description=description or form_type,
                    url=filing_url
                ))

            return filings

        except Exception as e:
            logger.error(f"Error fetching filings for {ticker}: {e}")
            return []

    def get_merger_filings(self, ticker: str, days_back: int = 90) -> List[SECFiling]:
        """
        Get merger-related filings (DEFM14A, S-4, 8-K with merger content).
        """
        merger_forms = ['DEFM14A', 'DEFM14C', 'S-4', 'S-4/A', 'PREM14A', 'SC 14D9']
        return self.get_company_filings(ticker, form_types=merger_forms, days_back=days_back)

    def get_material_events(self, ticker: str, days_back: int = 30) -> List[Dict]:
        """
        Get 8-K material event filings.

        8-K items relevant for trading:
        - 1.01: Entry into Material Agreement
        - 1.02: Termination of Material Agreement
        - 2.01: Acquisition/Disposition of Assets
        - 2.05: Costs from Exit Activities (layoffs)
        - 2.06: Material Impairments
        - 4.01: Changes in Accountant (red flag)
        - 5.02: Departure of Directors/Officers
        - 7.01: Regulation FD Disclosure
        - 8.01: Other Events
        """
        filings = self.get_company_filings(ticker, form_types=['8-K', '8-K/A'], days_back=days_back)

        events = []
        for filing in filings:
            events.append({
                'ticker': filing.ticker,
                'date': filing.filed_date,
                'form': filing.form_type,
                'description': filing.description,
                'url': filing.url,
                'is_material': True
            })

        return events

    def get_institutional_holders(self, ticker: str) -> List[Dict]:
        """
        Get institutional holders from 13F filings.

        Note: 13F data is quarterly, may be 45 days delayed.
        """
        # This would require parsing 13F-HR filings
        # For now, return placeholder
        return []

    def get_insider_transactions(self, ticker: str, days_back: int = 90) -> List[Dict]:
        """
        Get insider buy/sell transactions from Form 4 filings.
        """
        filings = self.get_company_filings(ticker, form_types=['4'], days_back=days_back)

        transactions = []
        for filing in filings:
            transactions.append({
                'ticker': filing.ticker,
                'date': filing.filed_date,
                'form': 'Form 4 (Insider)',
                'description': filing.description,
                'url': filing.url
            })

        return transactions

    def get_activist_filings(self, ticker: str, days_back: int = 365) -> List[Dict]:
        """
        Get 13D filings (activist investors with >5% stake).

        13D = Intent to influence management
        13G = Passive investment
        """
        filings = self.get_company_filings(
            ticker,
            form_types=['SC 13D', 'SC 13D/A', 'SC 13G', 'SC 13G/A'],
            days_back=days_back
        )

        activists = []
        for filing in filings:
            is_activist = '13D' in filing.form_type
            activists.append({
                'ticker': filing.ticker,
                'date': filing.filed_date,
                'form': filing.form_type,
                'is_activist': is_activist,
                'description': filing.description,
                'url': filing.url
            })

        return activists


# =============================================================================
# M&A SPECIFIC FUNCTIONS
# =============================================================================

def detect_ma_activity(ticker: str) -> Dict:
    """
    Detect M&A activity for a ticker based on SEC filings.

    Returns:
        Dict with M&A signals and confidence score
    """
    client = SECEdgarClient()

    signals = []
    score = 0

    # Check for merger proxy filings
    merger_filings = client.get_merger_filings(ticker, days_back=90)
    if merger_filings:
        defm14a = [f for f in merger_filings if 'DEFM14A' in f.form_type]
        s4 = [f for f in merger_filings if 'S-4' in f.form_type]

        if defm14a:
            signals.append(f"DEFM14A filed {defm14a[0].filed_date} - Merger vote pending")
            score += 40

        if s4:
            signals.append(f"S-4 filed {s4[0].filed_date} - Stock-based merger registration")
            score += 30

    # Check 8-K for deal announcements
    events = client.get_material_events(ticker, days_back=30)
    for event in events:
        desc = event.get('description', '').lower()
        if any(word in desc for word in ['merger', 'acquisition', 'agreement']):
            signals.append(f"8-K: {event['description'][:50]}")
            score += 20

    # Check for activist involvement
    activists = client.get_activist_filings(ticker, days_back=180)
    active_13d = [a for a in activists if a.get('is_activist')]
    if active_13d:
        signals.append(f"Activist 13D filed - Potential pressure for sale")
        score += 15

    return {
        'ticker': ticker,
        'ma_score': min(100, score),
        'signals': signals,
        'has_activity': score > 20,
        'filings_checked': len(merger_filings) + len(events) + len(activists)
    }


def get_pending_mergers_from_sec() -> List[Dict]:
    """
    Scan recent DEFM14A filings to find pending mergers.

    This searches SEC EDGAR for recent merger proxies.
    """
    try:
        # Search for recent DEFM14A filings
        url = "https://efts.sec.gov/LATEST/search-index"
        params = {
            'q': '"DEFM14A"',
            'dateRange': 'custom',
            'startdt': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
            'enddt': datetime.now().strftime('%Y-%m-%d'),
            'forms': 'DEFM14A'
        }

        response = requests.get(url, params=params, timeout=15, headers={
            'User-Agent': USER_AGENT
        })

        if response.status_code == 200:
            data = response.json()
            hits = data.get('hits', {}).get('hits', [])

            mergers = []
            for hit in hits[:20]:
                source = hit.get('_source', {})
                mergers.append({
                    'company': source.get('display_names', ['Unknown'])[0],
                    'ticker': source.get('tickers', ['?'])[0] if source.get('tickers') else '?',
                    'filed_date': source.get('file_date', ''),
                    'form': source.get('form', 'DEFM14A'),
                    'description': source.get('root_form', '')
                })

            return mergers

        return []
    except Exception as e:
        logger.error(f"Error searching SEC: {e}")
        return []


# =============================================================================
# TELEGRAM FORMATTING
# =============================================================================

def format_sec_filings_message(filings: List[SECFiling], title: str = "SEC FILINGS") -> str:
    """Format SEC filings for Telegram."""
    if not filings:
        return f"📋 *{title}*\n\n_No filings found_"

    msg = f"📋 *{title}*\n\n"

    for f in filings[:10]:
        # Form type emoji
        if 'DEFM14A' in f.form_type:
            emoji = "🔔"  # Merger vote
        elif 'S-4' in f.form_type:
            emoji = "📝"  # Registration
        elif '8-K' in f.form_type:
            emoji = "⚡"  # Material event
        elif '13D' in f.form_type:
            emoji = "🦈"  # Activist
        elif f.form_type == '4':
            emoji = "👤"  # Insider
        else:
            emoji = "📄"

        msg += f"{emoji} *{f.form_type}* - {f.ticker}\n"
        msg += f"   {f.filed_date} | {f.description[:40]}\n"
        msg += f"   [View Filing]({f.url})\n\n"

    return msg


def format_ma_detection_message(result: Dict) -> str:
    """Format M&A detection result for Telegram."""
    ticker = result.get('ticker', '?')
    score = result.get('ma_score', 0)
    signals = result.get('signals', [])

    # Score indicator
    if score >= 60:
        indicator = "🔴 HIGH"
    elif score >= 30:
        indicator = "🟡 MEDIUM"
    else:
        indicator = "🟢 LOW"

    msg = f"🔍 *M&A ACTIVITY: {ticker}*\n\n"
    msg += f"*Probability:* {indicator} ({score}/100)\n\n"

    if signals:
        msg += "*Signals Detected:*\n"
        for signal in signals:
            msg += f"• {signal}\n"
    else:
        msg += "_No M&A signals detected_\n"

    msg += f"\n_Checked {result.get('filings_checked', 0)} SEC filings_"

    return msg


# =============================================================================
# SYNC WRAPPERS
# =============================================================================

def get_merger_filings_sync(ticker: str, days_back: int = 90) -> List[Dict]:
    """Synchronous wrapper for merger filings."""
    client = SECEdgarClient()
    filings = client.get_merger_filings(ticker, days_back)
    return [f.to_dict() for f in filings]


def get_material_events_sync(ticker: str, days_back: int = 30) -> List[Dict]:
    """Synchronous wrapper for material events."""
    client = SECEdgarClient()
    return client.get_material_events(ticker, days_back)


def get_insider_transactions_sync(ticker: str, days_back: int = 90) -> List[Dict]:
    """Synchronous wrapper for insider transactions."""
    client = SECEdgarClient()
    return client.get_insider_transactions(ticker, days_back)


def detect_ma_activity_sync(ticker: str) -> Dict:
    """Synchronous wrapper for M&A detection."""
    return detect_ma_activity(ticker)


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("SEC EDGAR Integration Demo")
    print("=" * 50)

    client = SECEdgarClient()

    # Test with a known M&A target
    ticker = "VMW"  # VMware (Broadcom acquisition)

    print(f"\nChecking {ticker} for M&A activity...")

    # Get merger filings
    merger_filings = client.get_merger_filings(ticker)
    print(f"\nMerger-related filings: {len(merger_filings)}")
    for f in merger_filings[:3]:
        print(f"  - {f.form_type}: {f.filed_date} - {f.description[:50]}")

    # Get 8-K events
    events = client.get_material_events(ticker)
    print(f"\nMaterial events (8-K): {len(events)}")
    for e in events[:3]:
        print(f"  - {e['date']}: {e['description'][:50]}")

    # Full M&A detection
    result = detect_ma_activity(ticker)
    print(f"\nM&A Detection Score: {result['ma_score']}/100")
    for signal in result['signals']:
        print(f"  - {signal}")
