"""
Theme Discovery Engine
======================

Uses story scores + supply chain analysis to discover emerging themes
BEFORE they become mainstream.

Discovery Flow:
1. Identify high story-score stocks (leaders)
2. Analyze their supply chains using AI
3. Find lagging plays (suppliers, beneficiaries)
4. Validate with hard data (patents, contracts, insider)
5. Generate "emerging theme" alerts

Key Insight: Theme leaders move first, supply chain follows.
The alpha is in finding the supply chain BEFORE it moves.

Usage:
    from src.intelligence.theme_discovery_engine import get_theme_discovery_engine

    engine = get_theme_discovery_engine()

    # Discover emerging themes from current leaders
    discoveries = engine.discover_emerging_themes()

    # Analyze supply chain for specific theme
    chain = engine.analyze_supply_chain('ai_infrastructure')

    # Find lagging plays in hot theme
    laggards = engine.find_lagging_plays('nuclear')
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Cache directory
DISCOVERY_CACHE_DIR = Path('cache/theme_discovery')
DISCOVERY_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SupplyChainNode:
    """A node in the supply chain graph."""
    ticker: str
    company_name: str
    role: str  # 'leader', 'supplier', 'equipment', 'materials', 'beneficiary', 'infrastructure'
    relationship: str  # How it relates to the theme
    story_score: float = 0
    price_performance_30d: float = 0  # % change last 30 days
    has_moved: bool = False  # Has the stock already run?
    opportunity_score: float = 0  # Higher = better opportunity (hasn't moved yet)
    validation: Dict = field(default_factory=dict)  # Hard data validation


@dataclass
class EmergingTheme:
    """An emerging theme discovered from analysis."""
    theme_id: str
    theme_name: str
    description: str

    # Discovery source
    discovered_from: List[str]  # Tickers that led to discovery
    discovery_method: str  # 'supply_chain', 'patent_cluster', 'contract_cluster', 'news_cooccurrence'

    # Theme members by role
    leaders: List[SupplyChainNode] = field(default_factory=list)
    suppliers: List[SupplyChainNode] = field(default_factory=list)
    equipment: List[SupplyChainNode] = field(default_factory=list)
    materials: List[SupplyChainNode] = field(default_factory=list)
    beneficiaries: List[SupplyChainNode] = field(default_factory=list)
    infrastructure: List[SupplyChainNode] = field(default_factory=list)

    # Scoring
    theme_strength: float = 0  # Overall theme strength
    opportunity_score: float = 0  # How much opportunity remains
    laggard_count: int = 0  # How many plays haven't moved

    # Validation
    patent_validation: float = 0  # 0-100
    contract_validation: float = 0  # 0-100
    insider_validation: float = 0  # 0-100

    # Timing
    lifecycle_stage: str = 'emerging'  # emerging, accelerating, mainstream, late
    estimated_runway: str = ''  # How much upside remains

    timestamp: str = ''

    def to_dict(self) -> Dict:
        return {
            'theme_id': self.theme_id,
            'theme_name': self.theme_name,
            'description': self.description,
            'discovered_from': self.discovered_from,
            'discovery_method': self.discovery_method,
            'leaders': [asdict(n) for n in self.leaders],
            'suppliers': [asdict(n) for n in self.suppliers],
            'equipment': [asdict(n) for n in self.equipment],
            'materials': [asdict(n) for n in self.materials],
            'beneficiaries': [asdict(n) for n in self.beneficiaries],
            'infrastructure': [asdict(n) for n in self.infrastructure],
            'theme_strength': self.theme_strength,
            'opportunity_score': self.opportunity_score,
            'laggard_count': self.laggard_count,
            'patent_validation': self.patent_validation,
            'contract_validation': self.contract_validation,
            'insider_validation': self.insider_validation,
            'lifecycle_stage': self.lifecycle_stage,
            'estimated_runway': self.estimated_runway,
            'timestamp': self.timestamp,
        }


class ThemeDiscoveryEngine:
    """
    Discovers emerging themes by analyzing supply chains of high story-score stocks.

    The key insight: When a theme is hot, the leaders move first.
    The supply chain (suppliers, equipment makers, materials) follows later.

    By mapping supply chains from story score leaders, we can find
    opportunities BEFORE they become obvious.
    """

    # Known supply chain relationships for common themes
    SUPPLY_CHAIN_MAP = {
        'ai_infrastructure': {
            'leaders': ['NVDA', 'AMD', 'MSFT', 'GOOGL', 'META'],
            'suppliers': ['ASML', 'LRCX', 'AMAT', 'KLAC'],  # Chip equipment
            'equipment': ['DELL', 'HPE', 'SMCI'],  # Servers
            'materials': ['ENTG', 'MKSI', 'CRUS'],  # Materials
            'beneficiaries': ['PLTR', 'SNOW', 'MDB', 'DDOG'],  # Software
            'infrastructure': ['EQIX', 'DLR', 'AMT'],  # Data centers
        },
        'nuclear_energy': {
            'leaders': ['CEG', 'VST', 'NRG'],
            'suppliers': ['CCJ', 'UEC', 'DNN', 'UUUU'],  # Uranium
            'equipment': ['GEV', 'BWX', 'FLR'],  # Equipment/Construction
            'materials': ['NEM', 'FCX'],  # Mining
            'beneficiaries': ['ETN', 'EMR', 'ROK'],  # Grid/Electrical
            'infrastructure': ['NEE', 'DUK', 'SO'],  # Utilities
        },
        'defense_tech': {
            'leaders': ['LMT', 'RTX', 'NOC', 'GD'],
            'suppliers': ['HII', 'TXT', 'LHX'],  # Contractors
            'equipment': ['AXON', 'PLTR', 'LDOS'],  # Tech
            'materials': ['ATI', 'HWM', 'TDG'],  # Aerospace materials
            'beneficiaries': ['KTOS', 'RGR', 'SWBI'],  # Smaller defense
            'infrastructure': ['BAH', 'CACI', 'SAIC'],  # Services
        },
        'ev_battery': {
            'leaders': ['TSLA', 'RIVN', 'LCID'],
            'suppliers': ['PCRFY', 'ALB', 'SQM', 'LAC'],  # Lithium
            'equipment': ['PLUG', 'BLNK', 'CHPT'],  # Charging
            'materials': ['MP', 'LTHM'],  # Rare earth
            'beneficiaries': ['F', 'GM', 'STLA'],  # Legacy auto
            'infrastructure': ['EOSE', 'STEM', 'NOVA'],  # Energy storage
        },
        'biotech_glp1': {
            'leaders': ['LLY', 'NVO'],
            'suppliers': ['TMO', 'DHR', 'A'],  # Lab equipment
            'equipment': ['ISRG', 'BSX', 'MDT'],  # Medical devices
            'materials': ['CTLT', 'WST'],  # Drug delivery
            'beneficiaries': ['HUM', 'CI', 'UNH'],  # Insurance
            'infrastructure': ['CVS', 'WBA', 'ABC'],  # Distribution
        },
        'cybersecurity': {
            'leaders': ['CRWD', 'PANW', 'ZS'],
            'suppliers': ['FTNT', 'S', 'TENB'],  # Security vendors
            'equipment': ['CSCO', 'JNPR', 'ANET'],  # Network
            'materials': ['QLYS', 'VRNS', 'RPD'],  # Tools
            'beneficiaries': ['OKTA', 'NET', 'DDOG'],  # Cloud security
            'infrastructure': ['ACN', 'IBM', 'LDOS'],  # Services
        },
    }

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_times: Dict[str, datetime] = {}
        self._cache_ttl = 3600  # 1 hour
        self._lock = threading.Lock()

        logger.info("ThemeDiscoveryEngine initialized")

    def _call_ai(self, prompt: str, task_type: str = "theme", max_tokens: int = 3000) -> Optional[str]:
        """Call AI service for analysis."""
        try:
            from src.services.ai_service import get_ai_service
            service = get_ai_service()
            return service.call(prompt, max_tokens=max_tokens, task_type=task_type)
        except Exception as e:
            logger.error(f"AI call failed: {e}")
            return None

    def _gather_realtime_data(self, tickers: List[str] = None) -> Dict[str, Any]:
        """
        Gather real-time market data for AI analysis.

        Collects:
        - Recent news and sentiment
        - Price movements and volume
        - Social buzz signals
        - SEC filings
        - Sector performance
        """
        data = {
            'timestamp': datetime.now().isoformat(),
            'news': [],
            'movers': [],
            'social_buzz': [],
            'filings': [],
            'sector_performance': {},
            'high_story_scores': []
        }

        try:
            # Get high story score stocks
            story_scores = self._get_story_scores()
            if story_scores:
                top_scorers = sorted(story_scores.items(), key=lambda x: x[1], reverse=True)[:20]
                data['high_story_scores'] = [
                    {'ticker': t, 'story_score': float(s)} for t, s in top_scorers if s >= 50
                ]

            # Get recent news
            try:
                from src.sentiment.news_aggregator import get_latest_news
                news = get_latest_news(limit=30)
                if news:
                    data['news'] = [
                        {
                            'headline': n.get('title', ''),
                            'source': n.get('source', ''),
                            'tickers': n.get('tickers', []),
                            'sentiment': n.get('sentiment', 'neutral')
                        }
                        for n in news[:20]
                    ]
            except Exception as e:
                logger.debug(f"News fetch failed: {e}")

            # Get top movers (limited to reduce API calls)
            try:
                import yfinance as yf
                check_tickers = tickers or [t for t, s in (story_scores.items() if story_scores else [])][:10]

                if check_tickers:
                    for ticker in check_tickers[:5]:  # Reduced from 15 to avoid timeout
                        try:
                            stock = yf.Ticker(ticker)
                            hist = stock.history(period='5d')
                            if len(hist) >= 2:
                                change = float((hist['Close'].iloc[-1] / hist['Close'].iloc[-2]) - 1) * 100
                                vol_ratio = float(hist['Volume'].iloc[-1] / hist['Volume'].iloc[:-1].mean()) if hist['Volume'].iloc[:-1].mean() > 0 else 1.0

                                if abs(change) > 2 or vol_ratio > 2:
                                    data['movers'].append({
                                        'ticker': ticker,
                                        'change_pct': round(change, 2),
                                        'volume_ratio': round(vol_ratio, 2),
                                        'story_score': float(story_scores.get(ticker, 0))
                                    })
                        except:
                            pass
            except Exception as e:
                logger.debug(f"Movers fetch failed: {e}")

            # Get social buzz from StockTwits (limited to reduce API calls)
            try:
                from story_scorer import fetch_stocktwits_sentiment
                for ticker in (tickers or list(story_scores.keys()))[:3]:  # Reduced from 10
                    try:
                        buzz = fetch_stocktwits_sentiment(ticker)
                        if buzz and buzz.get('message_count', 0) > 5:
                            data['social_buzz'].append({
                                'ticker': ticker,
                                'messages': int(buzz.get('message_count', 0)),
                                'bullish_pct': float(buzz.get('bullish_percent', 50)),
                                'trending': bool(buzz.get('trending', False))
                            })
                    except:
                        pass
            except Exception as e:
                logger.debug(f"Social buzz fetch failed: {e}")

            # Get recent SEC filings (limited to reduce API calls)
            try:
                from src.data.sec_edgar import SECEdgarClient
                client = SECEdgarClient()

                for ticker in (tickers or list(story_scores.keys()))[:3]:  # Reduced from 10
                    try:
                        filings = client.get_recent_filings(ticker, days_back=7)
                        if filings:
                            for f in filings[:2]:
                                data['filings'].append({
                                    'ticker': ticker,
                                    'form': f.get('form', ''),
                                    'description': f.get('description', ''),
                                    'date': f.get('filing_date', '')
                                })
                    except:
                        pass
            except Exception as e:
                logger.debug(f"SEC filings fetch failed: {e}")

            # Get sector performance (limited to key sectors to reduce API calls)
            try:
                sector_etfs = {
                    'Technology': 'XLK',
                    'Healthcare': 'XLV',
                    'Energy': 'XLE',
                    'Industrials': 'XLI'
                }  # Reduced from 11 sectors

                import yfinance as yf
                for sector, etf in sector_etfs.items():
                    try:
                        hist = yf.Ticker(etf).history(period='5d')
                        if len(hist) >= 2:
                            change = float((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
                            data['sector_performance'][sector] = round(change, 2)
                    except:
                        pass
            except Exception as e:
                logger.debug(f"Sector performance fetch failed: {e}")

        except Exception as e:
            logger.error(f"Real-time data gathering failed: {e}")

        return data

    def analyze_with_ai(self, context: str = "general") -> Dict[str, Any]:
        """
        Use AI to analyze real-time market data and discover opportunities.

        Returns AI-reasoned insights about:
        - Emerging themes
        - Supply chain opportunities
        - Lagging plays
        """
        # Gather real-time data
        realtime_data = self._gather_realtime_data()

        # Build context for AI
        prompt = f"""Analyze this real-time market data and identify emerging investment themes and supply chain opportunities.

REAL-TIME MARKET DATA:
=====================

HIGH STORY SCORE STOCKS (algorithmic momentum + catalyst detection):
{json.dumps(realtime_data.get('high_story_scores', []), indent=2)}

RECENT NEWS HEADLINES:
{json.dumps(realtime_data.get('news', []), indent=2)}

TODAY'S MOVERS (significant price/volume):
{json.dumps(realtime_data.get('movers', []), indent=2)}

SOCIAL BUZZ (StockTwits sentiment):
{json.dumps(realtime_data.get('social_buzz', []), indent=2)}

RECENT SEC FILINGS:
{json.dumps(realtime_data.get('filings', []), indent=2)}

SECTOR PERFORMANCE (5-day):
{json.dumps(realtime_data.get('sector_performance', {}), indent=2)}

KNOWN THEME SUPPLY CHAINS (for reference):
{json.dumps(list(self.SUPPLY_CHAIN_MAP.keys()), indent=2)}

YOUR TASK:
==========
1. IDENTIFY EMERGING THEMES: What investment themes are heating up based on this data?
   - Look for clusters of related stocks moving together
   - News patterns pointing to sector shifts
   - Social buzz concentrations

2. SUPPLY CHAIN ANALYSIS: For each theme, identify:
   - LEADERS: The obvious plays already moving
   - LAGGARDS: Supply chain stocks that HAVEN'T moved yet but should benefit
   - Why they're connected (supplier, customer, infrastructure, materials, etc.)

3. OPPORTUNITY RANKING: Rank lagging plays by:
   - Connection strength to the theme
   - How much they've missed the move
   - Catalyst potential

Return a JSON object with this structure:
{{
    "analysis_summary": "2-3 sentence market overview",
    "emerging_themes": [
        {{
            "theme_name": "Theme Name",
            "theme_id": "theme_id_snake_case",
            "confidence": 0-100,
            "reasoning": "Why this theme is emerging based on the data",
            "leaders": ["TICKER1", "TICKER2"],
            "lagging_opportunities": [
                {{
                    "ticker": "TICKER",
                    "role": "supplier/equipment/materials/beneficiary/infrastructure",
                    "connection": "How it connects to the theme",
                    "why_lagging": "Why it hasn't moved yet",
                    "catalyst": "What could trigger the move",
                    "opportunity_score": 0-100
                }}
            ]
        }}
    ],
    "top_actionable_ideas": [
        {{
            "ticker": "TICKER",
            "theme": "Theme it belongs to",
            "thesis": "1-2 sentence investment thesis",
            "risk": "Key risk to watch"
        }}
    ]
}}

Focus on QUALITY over quantity. Only include high-conviction ideas with clear reasoning."""

        response = self._call_ai(prompt, task_type="heavy", max_tokens=4000)

        if not response:
            return {'error': 'AI analysis failed', 'raw_data': realtime_data}

        try:
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                result['raw_data'] = realtime_data
                result['timestamp'] = datetime.now().isoformat()
                return result
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")

        return {
            'error': 'Failed to parse AI response',
            'raw_response': response[:500],
            'raw_data': realtime_data
        }

    def discover_realtime_opportunities(self) -> List[Dict]:
        """
        Main entry point for AI-driven opportunity discovery.

        Combines real-time data analysis with supply chain mapping
        to find the best lagging plays.
        """
        # Get AI analysis with exception handling
        try:
            ai_analysis = self.analyze_with_ai()
        except Exception as e:
            import traceback
            logger.error(f"AI analysis exception: {e}\n{traceback.format_exc()}")
            return self._fallback_static_analysis()

        if 'error' in ai_analysis:
            logger.warning(f"AI analysis had error: {ai_analysis.get('error')}")
            # Fall back to static analysis
            return self._fallback_static_analysis()

        opportunities = []

        # Extract opportunities from AI analysis
        for theme in ai_analysis.get('emerging_themes', []):
            for opp in theme.get('lagging_opportunities', []):
                opportunities.append({
                    'ticker': opp.get('ticker'),
                    'theme': theme.get('theme_name'),
                    'theme_id': theme.get('theme_id'),
                    'role': opp.get('role'),
                    'connection': opp.get('connection'),
                    'opportunity_score': opp.get('opportunity_score', 50),
                    'catalyst': opp.get('catalyst'),
                    'confidence': theme.get('confidence', 50),
                    'reasoning': theme.get('reasoning'),
                    'source': 'ai_realtime'
                })

        # Add top actionable ideas
        for idea in ai_analysis.get('top_actionable_ideas', []):
            # Check if already in opportunities
            if not any(o['ticker'] == idea.get('ticker') for o in opportunities):
                opportunities.append({
                    'ticker': idea.get('ticker'),
                    'theme': idea.get('theme'),
                    'thesis': idea.get('thesis'),
                    'risk': idea.get('risk'),
                    'opportunity_score': 75,  # Top ideas get high score
                    'source': 'ai_top_pick'
                })

        # Sort by opportunity score
        opportunities.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)

        return opportunities

    def _fallback_static_analysis(self) -> List[Dict]:
        """Fallback to static supply chain analysis if AI fails."""
        opportunities = []

        story_scores = self._get_story_scores()

        # Check each known theme
        for theme_id, chain in self.SUPPLY_CHAIN_MAP.items():
            leaders = chain.get('leaders', [])
            leader_scores = [story_scores.get(t, 0) for t in leaders]

            # If leaders have high scores, find laggards
            if any(s >= 60 for s in leader_scores):
                for role in ['suppliers', 'equipment', 'materials', 'beneficiaries', 'infrastructure']:
                    for ticker in chain.get(role, []):
                        perf = self._get_price_performance(ticker, 30)
                        if perf < 15:  # Hasn't moved much
                            opportunities.append({
                                'ticker': ticker,
                                'theme': theme_id.replace('_', ' ').title(),
                                'theme_id': theme_id,
                                'role': role,
                                'price_perf_30d': perf,
                                'opportunity_score': max(0, 70 - perf),
                                'source': 'static_fallback'
                            })

        opportunities.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)
        return opportunities[:20]

    def _get_story_scores(self) -> Dict[str, float]:
        """Get current story scores from scan data."""
        try:
            # Try to read from latest scan file
            scan_files = list(Path('.').glob('scan_*.csv'))
            if scan_files:
                import pandas as pd
                latest_scan = max(scan_files, key=lambda x: x.stat().st_mtime)
                df = pd.read_csv(latest_scan)
                if 'ticker' in df.columns and 'story_score' in df.columns:
                    # Convert to Python floats to avoid numpy serialization issues
                    return {
                        str(t).upper(): float(s)
                        for t, s in zip(df['ticker'], df['story_score'].fillna(0))
                    }
        except Exception as e:
            logger.debug(f"Could not load story scores: {e}")
        return {}

    def _get_price_performance(self, ticker: str, days: int = 30) -> float:
        """Get price performance for a ticker."""
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            hist = stock.history(period=f'{days}d')
            if len(hist) >= 2:
                return float((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
        except:
            pass
        return 0.0

    def _validate_with_patents(self, tickers: List[str], theme_keywords: List[str]) -> float:
        """Validate theme with patent data."""
        try:
            from src.data.patents import get_patent_intelligence
            intel = get_patent_intelligence()

            total_score = 0
            checked = 0

            for ticker in tickers[:5]:  # Check top 5
                activity = intel.get_company_patents(ticker)
                if activity and activity.patent_count > 0:
                    # Check if patents relate to theme keywords
                    patent_text = ' '.join(activity.top_keywords).lower()
                    matches = sum(1 for kw in theme_keywords if kw.lower() in patent_text)
                    total_score += min(100, matches * 25 + activity.yoy_change)
                    checked += 1

            return total_score / max(1, checked)
        except:
            return 0

    def _validate_with_contracts(self, tickers: List[str]) -> float:
        """Validate theme with government contract data."""
        try:
            from src.data.gov_contracts import get_contract_intelligence
            intel = get_contract_intelligence()

            total_value = 0
            for ticker in tickers[:5]:
                activity = intel.get_company_contracts(ticker)
                if activity:
                    total_value += activity.total_value

            # Score based on total contract value
            return min(100, total_value / 1e9 * 20)  # $5B = 100
        except:
            return 0

    def _validate_with_insider(self, tickers: List[str]) -> float:
        """Validate theme with insider activity."""
        try:
            from src.data.sec_edgar import SECEdgarClient
            client = SECEdgarClient()

            total_activity = 0
            for ticker in tickers[:5]:
                transactions = client.get_insider_transactions(ticker, days_back=60)
                if transactions:
                    total_activity += len(transactions)

            return min(100, total_activity * 10)
        except:
            return 0

    def analyze_supply_chain(self, theme_id: str) -> Optional[EmergingTheme]:
        """
        Analyze supply chain for a known theme.

        Returns EmergingTheme with all supply chain members scored.
        """
        if theme_id not in self.SUPPLY_CHAIN_MAP:
            # Try to discover supply chain using AI
            return self._discover_supply_chain_ai(theme_id)

        chain = self.SUPPLY_CHAIN_MAP[theme_id]
        story_scores = self._get_story_scores()

        theme = EmergingTheme(
            theme_id=theme_id,
            theme_name=theme_id.replace('_', ' ').title(),
            description=f"Supply chain analysis for {theme_id}",
            discovered_from=chain.get('leaders', []),
            discovery_method='supply_chain_map',
            timestamp=datetime.now().isoformat()
        )

        # Analyze each role
        for role in ['leaders', 'suppliers', 'equipment', 'materials', 'beneficiaries', 'infrastructure']:
            tickers = chain.get(role, [])
            nodes = []

            for ticker in tickers:
                perf = self._get_price_performance(ticker)
                score = story_scores.get(ticker, 50)
                has_moved = perf > 20  # Consider "moved" if up 20%+

                # Opportunity score: high story score + hasn't moved yet = opportunity
                opportunity = score * (1 - min(1, perf / 50)) if not has_moved else score * 0.3

                node = SupplyChainNode(
                    ticker=ticker,
                    company_name=ticker,  # Would need API to get full name
                    role=role.rstrip('s'),  # Remove plural
                    relationship=f"{role.rstrip('s')} in {theme_id}",
                    story_score=score,
                    price_performance_30d=perf,
                    has_moved=has_moved,
                    opportunity_score=opportunity
                )
                nodes.append(node)

                if not has_moved:
                    theme.laggard_count += 1

            # Sort by opportunity score
            nodes.sort(key=lambda x: x.opportunity_score, reverse=True)
            setattr(theme, role, nodes)

        # Calculate overall scores
        all_nodes = theme.leaders + theme.suppliers + theme.equipment + theme.materials + theme.beneficiaries + theme.infrastructure

        if all_nodes:
            theme.theme_strength = sum(n.story_score for n in all_nodes) / len(all_nodes)
            theme.opportunity_score = sum(n.opportunity_score for n in all_nodes if not n.has_moved) / max(1, theme.laggard_count)

        # Validate with hard data
        all_tickers = [n.ticker for n in all_nodes]
        theme.patent_validation = self._validate_with_patents(all_tickers, [theme_id])
        theme.contract_validation = self._validate_with_contracts(all_tickers)
        theme.insider_validation = self._validate_with_insider(all_tickers)

        # Determine lifecycle stage
        moved_pct = 1 - (theme.laggard_count / max(1, len(all_nodes)))
        if moved_pct < 0.3:
            theme.lifecycle_stage = 'emerging'
            theme.estimated_runway = 'High - Early stage, most plays haven\'t moved'
        elif moved_pct < 0.6:
            theme.lifecycle_stage = 'accelerating'
            theme.estimated_runway = 'Medium - Mid-cycle, suppliers/materials opportunity'
        elif moved_pct < 0.8:
            theme.lifecycle_stage = 'mainstream'
            theme.estimated_runway = 'Low - Late cycle, only laggards left'
        else:
            theme.lifecycle_stage = 'late'
            theme.estimated_runway = 'Minimal - Theme is mature'

        return theme

    def _discover_supply_chain_ai(self, theme_or_ticker: str) -> Optional[EmergingTheme]:
        """Use AI to discover supply chain for unknown theme/ticker."""
        prompt = f"""Analyze the supply chain for: {theme_or_ticker}

Return a JSON object with this structure:
{{
    "theme_name": "Human readable theme name",
    "description": "Brief description of the theme/industry",
    "supply_chain": {{
        "leaders": ["TICKER1", "TICKER2"],
        "suppliers": ["TICKER1", "TICKER2"],
        "equipment": ["TICKER1", "TICKER2"],
        "materials": ["TICKER1", "TICKER2"],
        "beneficiaries": ["TICKER1", "TICKER2"],
        "infrastructure": ["TICKER1", "TICKER2"]
    }},
    "keywords": ["keyword1", "keyword2"]
}}

Focus on:
- Leaders: Main companies driving the theme
- Suppliers: Who supplies components/services to leaders
- Equipment: Who makes the equipment/tools used
- Materials: Raw materials, chemicals, inputs
- Beneficiaries: Who benefits from theme success
- Infrastructure: Supporting services, logistics, facilities

Only include real US stock tickers. Be specific and accurate."""

        response = self._call_ai(prompt, task_type="theme")

        if not response:
            return None

        try:
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())

                # Build theme from AI response
                theme = EmergingTheme(
                    theme_id=theme_or_ticker.lower().replace(' ', '_'),
                    theme_name=data.get('theme_name', theme_or_ticker),
                    description=data.get('description', ''),
                    discovered_from=[theme_or_ticker],
                    discovery_method='ai_analysis',
                    timestamp=datetime.now().isoformat()
                )

                # Populate supply chain
                chain = data.get('supply_chain', {})
                story_scores = self._get_story_scores()

                for role in ['leaders', 'suppliers', 'equipment', 'materials', 'beneficiaries', 'infrastructure']:
                    tickers = chain.get(role, [])
                    nodes = []

                    for ticker in tickers:
                        if not ticker or len(ticker) > 5:
                            continue

                        perf = self._get_price_performance(ticker)
                        score = story_scores.get(ticker.upper(), 50)
                        has_moved = perf > 20
                        opportunity = score * (1 - min(1, perf / 50)) if not has_moved else score * 0.3

                        node = SupplyChainNode(
                            ticker=ticker.upper(),
                            company_name=ticker.upper(),
                            role=role.rstrip('s'),
                            relationship=f"AI-identified {role.rstrip('s')}",
                            story_score=score,
                            price_performance_30d=perf,
                            has_moved=has_moved,
                            opportunity_score=opportunity
                        )
                        nodes.append(node)

                        if not has_moved:
                            theme.laggard_count += 1

                    setattr(theme, role, nodes)

                return theme

        except Exception as e:
            logger.error(f"Failed to parse AI supply chain response: {e}")

        return None

    def discover_emerging_themes(self, min_story_score: float = 60) -> List[EmergingTheme]:
        """
        Discover emerging themes from high story-score stocks.

        1. Get stocks with high story scores
        2. Cluster by sector/theme
        3. Analyze supply chains
        4. Find lagging opportunities
        """
        discoveries = []

        # Get story scores
        story_scores = self._get_story_scores()

        if not story_scores:
            logger.warning("No story scores available")
            # Fall back to analyzing known themes
            for theme_id in list(self.SUPPLY_CHAIN_MAP.keys())[:3]:
                theme = self.analyze_supply_chain(theme_id)
                if theme and theme.laggard_count > 0:
                    discoveries.append(theme)
            return discoveries

        # Find high-scoring stocks
        high_scorers = [(t, s) for t, s in story_scores.items() if s >= min_story_score]
        high_scorers.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Found {len(high_scorers)} stocks with story score >= {min_story_score}")

        # Check which known themes have high-scoring leaders
        for theme_id, chain in self.SUPPLY_CHAIN_MAP.items():
            leaders = chain.get('leaders', [])
            leader_scores = [story_scores.get(t, 0) for t in leaders]

            if any(s >= min_story_score for s in leader_scores):
                theme = self.analyze_supply_chain(theme_id)
                if theme and theme.laggard_count > 0:
                    discoveries.append(theme)

        # Sort by opportunity score
        discoveries.sort(key=lambda x: x.opportunity_score, reverse=True)

        return discoveries

    def find_lagging_plays(self, theme_id: str) -> List[SupplyChainNode]:
        """
        Find stocks in a theme that haven't moved yet.

        These are the best opportunities - connected to hot theme
        but haven't been discovered by the market yet.
        """
        theme = self.analyze_supply_chain(theme_id)

        if not theme:
            return []

        # Collect all nodes that haven't moved
        laggards = []

        for role in ['suppliers', 'equipment', 'materials', 'beneficiaries', 'infrastructure']:
            nodes = getattr(theme, role, [])
            for node in nodes:
                if not node.has_moved and node.opportunity_score > 30:
                    laggards.append(node)

        # Sort by opportunity score
        laggards.sort(key=lambda x: x.opportunity_score, reverse=True)

        return laggards

    def get_discovery_summary(self, use_ai: bool = False) -> Dict:
        """Get summary of all discovered themes and opportunities."""

        # Try AI-driven analysis first if requested
        if use_ai:
            try:
                ai_analysis = self.analyze_with_ai()
                if 'error' not in ai_analysis:
                    return {
                        'timestamp': datetime.now().isoformat(),
                        'source': 'ai_realtime',
                        'analysis_summary': ai_analysis.get('analysis_summary', ''),
                        'themes_analyzed': len(ai_analysis.get('emerging_themes', [])),
                        'total_opportunities': sum(
                            len(t.get('lagging_opportunities', []))
                            for t in ai_analysis.get('emerging_themes', [])
                        ),
                        'themes': [
                            {
                                'theme_id': t.get('theme_id'),
                                'theme_name': t.get('theme_name'),
                                'confidence': t.get('confidence', 50),
                                'reasoning': t.get('reasoning'),
                                'lifecycle_stage': 'emerging' if t.get('confidence', 50) > 70 else 'developing',
                                'opportunity_score': t.get('confidence', 50),
                                'laggard_count': len(t.get('lagging_opportunities', [])),
                                'top_laggards': [
                                    {
                                        'ticker': l.get('ticker'),
                                        'role': l.get('role'),
                                        'connection': l.get('connection'),
                                        'catalyst': l.get('catalyst'),
                                        'opportunity_score': l.get('opportunity_score', 50)
                                    }
                                    for l in t.get('lagging_opportunities', [])[:5]
                                ],
                                'leaders': t.get('leaders', [])
                            }
                            for t in ai_analysis.get('emerging_themes', [])
                        ],
                        'top_ideas': ai_analysis.get('top_actionable_ideas', [])
                    }
            except Exception as e:
                logger.warning(f"AI analysis failed, falling back to static: {e}")

        # Fallback to static analysis
        discoveries = self.discover_emerging_themes()

        summary = {
            'timestamp': datetime.now().isoformat(),
            'source': 'static_mapping',
            'themes_analyzed': len(discoveries),
            'total_opportunities': sum(d.laggard_count for d in discoveries),
            'themes': []
        }

        for theme in discoveries[:5]:
            # Get top laggards
            laggards = self.find_lagging_plays(theme.theme_id)[:3]

            summary['themes'].append({
                'theme_id': theme.theme_id,
                'theme_name': theme.theme_name,
                'lifecycle_stage': theme.lifecycle_stage,
                'opportunity_score': theme.opportunity_score,
                'laggard_count': theme.laggard_count,
                'top_laggards': [
                    {
                        'ticker': l.ticker,
                        'role': l.role,
                        'story_score': l.story_score,
                        'price_perf_30d': l.price_performance_30d,
                        'opportunity_score': l.opportunity_score
                    }
                    for l in laggards
                ],
                'validation': {
                    'patents': theme.patent_validation,
                    'contracts': theme.contract_validation,
                    'insider': theme.insider_validation
                }
            })

        return summary

    def get_ai_opportunities(self) -> Dict:
        """
        Get AI-analyzed real-time opportunities.

        This is the main method for getting AI-driven supply chain opportunities.
        """
        try:
            opportunities = self.discover_realtime_opportunities()

            return {
                'timestamp': datetime.now().isoformat(),
                'source': 'ai_realtime',
                'total_opportunities': len(opportunities),
                'opportunities': opportunities[:15],
                'themes_detected': list(set(o.get('theme') for o in opportunities if o.get('theme')))
            }
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"get_ai_opportunities error: {e}\n{tb}")
            return {
                'timestamp': datetime.now().isoformat(),
                'source': 'error_fallback',
                'error': str(e),
                'traceback': tb[:500],
                'total_opportunities': 0,
                'opportunities': [],
                'themes_detected': []
            }


# Singleton instance
_engine: Optional[ThemeDiscoveryEngine] = None
_engine_lock = threading.Lock()


def get_theme_discovery_engine() -> ThemeDiscoveryEngine:
    """Get or create the singleton engine instance."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = ThemeDiscoveryEngine()
    return _engine
