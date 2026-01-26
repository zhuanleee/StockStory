"""
DeepSeek Intelligence Layer - AI-Enhanced Analysis

Provides AI capabilities for:
1. Theme naming and thesis generation
2. Role classification with business reasoning
3. Stage detection from narrative analysis
4. Supply chain discovery from filings
5. Emerging theme detection
6. Membership validation

Uses DeepSeek API for cost-effective AI analysis.
Includes caching, batching, and budget management.

Author: Stock Scanner Bot
Version: 1.0
"""

import json
import os
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on environment variables

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger('deepseek_intelligence')

# Data directory
DATA_DIR = Path(__file__).parent / 'ai_data'
DATA_DIR.mkdir(exist_ok=True)

CACHE_FILE = DATA_DIR / 'ai_cache.json'
USAGE_FILE = DATA_DIR / 'ai_usage.json'
HEALTH_FILE = DATA_DIR / 'ai_health.json'


@dataclass
class AIHealthStatus:
    """Health status of AI system"""
    status: str
    api_available: bool
    cache_size: int
    daily_calls: int
    daily_budget: int
    budget_remaining: int
    avg_latency_ms: float
    last_error: Optional[str]
    last_check: str
    # Additional fields for API compatibility
    model: str = "deepseek-chat"
    calls_last_24h: int = 0
    health_score: float = 100.0


class DeepSeekIntelligence:
    """
    AI Intelligence layer using DeepSeek for enhanced analysis.
    """

    DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

    # Cost management
    DAILY_BUDGET = 500  # Max API calls per day
    CACHE_TTL_HOURS = 24  # Cache AI responses for 24h

    def __init__(self):
        self.api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        self.cache: Dict[str, Dict] = {}
        self.usage: Dict[str, int] = defaultdict(int)
        self.latencies: List[float] = []
        self.last_error: Optional[str] = None
        self._load_cache()
        self._load_usage()

    def _load_cache(self):
        """Load AI response cache"""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r') as f:
                    data = json.load(f)
                self.cache = data.get('cache', {})

                # Prune expired entries
                now = datetime.now()
                expired = []
                for key, entry in self.cache.items():
                    if 'timestamp' in entry:
                        age = now - datetime.fromisoformat(entry['timestamp'])
                        if age.total_seconds() > self.CACHE_TTL_HOURS * 3600:
                            expired.append(key)

                for key in expired:
                    del self.cache[key]

                logger.info(f"Loaded AI cache: {len(self.cache)} entries")
            except Exception as e:
                logger.error(f"Failed to load AI cache: {e}")

    def _save_cache(self):
        """Save AI response cache"""
        # Keep only recent entries (max 1000)
        if len(self.cache) > 1000:
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: x[1].get('timestamp', ''),
                reverse=True
            )
            self.cache = dict(sorted_entries[:1000])

        data = {
            'version': '1.0',
            'last_updated': datetime.now().isoformat(),
            'cache': self.cache
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)

    def _load_usage(self):
        """Load API usage stats"""
        if USAGE_FILE.exists():
            try:
                with open(USAGE_FILE, 'r') as f:
                    data = json.load(f)

                # Reset if new day
                last_date = data.get('date', '')
                today = datetime.now().strftime('%Y-%m-%d')

                if last_date != today:
                    self.usage = defaultdict(int)
                else:
                    self.usage = defaultdict(int, data.get('usage', {}))
            except:
                self.usage = defaultdict(int)

    def _save_usage(self):
        """Save API usage stats"""
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'usage': dict(self.usage),
            'total_today': sum(self.usage.values()),
        }
        with open(USAGE_FILE, 'w') as f:
            json.dump(data, f)

    def _get_cache_key(self, task: str, data: Any) -> str:
        """Generate cache key for request"""
        content = json.dumps({'task': task, 'data': data}, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def _check_budget(self) -> bool:
        """Check if within daily budget"""
        total_today = sum(self.usage.values())
        return total_today < self.DAILY_BUDGET

    def _call_deepseek(self, prompt: str, system_prompt: str = None,
                       temperature: float = 0.3) -> Optional[str]:
        """Make API call to DeepSeek"""
        if not self.api_key:
            logger.warning("DeepSeek API key not configured")
            return None

        if not self._check_budget():
            logger.warning("Daily AI budget exhausted")
            return None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            start_time = datetime.now()

            response = requests.post(
                self.DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 2000,
                },
                timeout=60
            )

            latency = (datetime.now() - start_time).total_seconds() * 1000
            self.latencies.append(latency)
            self.latencies = self.latencies[-100:]  # Keep last 100

            response.raise_for_status()
            result = response.json()

            # Track usage
            self.usage['api_calls'] += 1
            self._save_usage()

            return result['choices'][0]['message']['content']

        except Exception as e:
            self.last_error = str(e)
            logger.error(f"DeepSeek API error: {e}")
            return None

    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from AI response"""
        if not response:
            return None

        try:
            # Try direct JSON parse
            return json.loads(response)
        except:
            pass

        # Try to extract JSON from markdown code block
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass

        # Try to find JSON object
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass

        return None

    # =========================================================================
    # THEME NAMING & THESIS
    # =========================================================================

    def generate_theme_info(self, correlated_stocks: List[str],
                            news_headlines: List[str] = None) -> Dict:
        """
        Generate theme name and thesis from correlated stocks.

        Returns:
        {
            'name': 'AI Power Infrastructure',
            'thesis': 'Data centers driving unprecedented power demand...',
            'keywords': ['data center', 'power', 'AI'],
            'stage': 'early',
            'confidence': 0.85
        }
        """
        cache_key = self._get_cache_key('theme_info', {
            'stocks': sorted(correlated_stocks),
            'headlines': news_headlines[:10] if news_headlines else []
        })

        # Check cache
        if cache_key in self.cache:
            return self.cache[cache_key]['response']

        # Build prompt
        headlines_text = ""
        if news_headlines:
            headlines_text = "\n".join([f"- {h}" for h in news_headlines[:15]])

        prompt = f"""Analyze this cluster of correlated stocks and identify the investment theme.

STOCKS MOVING TOGETHER: {', '.join(correlated_stocks)}

{f'RECENT HEADLINES:{chr(10)}{headlines_text}' if headlines_text else ''}

Provide analysis as JSON:
{{
    "name": "Theme name (2-4 words, e.g., 'AI Power Infrastructure')",
    "thesis": "Investment thesis explaining WHY these stocks are correlated (1-2 sentences)",
    "keywords": ["list", "of", "5-8", "keywords", "for", "detection"],
    "stage": "early|middle|peak|fading",
    "catalyst": "What's driving this theme now",
    "suggested_additions": ["tickers", "that", "should", "be", "included"],
    "suggested_removals": ["tickers", "that", "don't", "belong"],
    "confidence": 0.0-1.0
}}"""

        system_prompt = """You are a senior equity analyst specializing in thematic investing.
Identify investment themes from stock correlations and news patterns.
Be specific and actionable. Return valid JSON only."""

        response = self._call_deepseek(prompt, system_prompt)
        result = self._parse_json_response(response)

        if result:
            self.cache[cache_key] = {
                'response': result,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache()
            return result

        # Fallback
        return {
            'name': f"Cluster_{hashlib.md5(''.join(correlated_stocks).encode()).hexdigest()[:6]}",
            'thesis': 'Auto-discovered correlation cluster',
            'keywords': [],
            'stage': 'unknown',
            'confidence': 0.5
        }

    # =========================================================================
    # ROLE CLASSIFICATION
    # =========================================================================

    def classify_role(self, ticker: str, theme_name: str,
                      company_description: str,
                      lead_lag_days: float = 0,
                      correlation: float = 0) -> Dict:
        """
        Classify stock's role in a theme using AI + quantitative data.

        Returns:
        {
            'role': 'driver|beneficiary|picks_shovels|peripheral',
            'confidence': 0.85,
            'reasoning': 'NVDA makes the GPUs that power AI...'
        }
        """
        cache_key = self._get_cache_key('role', {
            'ticker': ticker,
            'theme': theme_name,
            'lead_lag': round(lead_lag_days, 1)
        })

        if cache_key in self.cache:
            return self.cache[cache_key]['response']

        prompt = f"""Classify {ticker}'s role in the "{theme_name}" investment theme.

COMPANY DESCRIPTION:
{company_description[:500]}

QUANTITATIVE SIGNALS:
- Lead/lag vs theme average: {lead_lag_days:+.1f} days (negative = leads, positive = lags)
- Correlation with theme: {correlation:.2f}

ROLE DEFINITIONS:
- DRIVER: Sets the narrative, moves first, core to the theme's success
- BENEFICIARY: Benefits from theme success, moves after drivers
- PICKS_SHOVELS: Sells to theme players (suppliers, enablers), steady but less volatile
- PERIPHERAL: Loosely connected, not core to theme

Return JSON:
{{
    "role": "driver|beneficiary|picks_shovels|peripheral",
    "confidence": 0.0-1.0,
    "reasoning": "Explanation based on business model AND quantitative signals"
}}"""

        system_prompt = """You are a portfolio manager analyzing stock roles within investment themes.
Consider both the company's business model and quantitative signals.
A stock that leads price-wise AND has a core business connection is likely a driver.
Return valid JSON only."""

        response = self._call_deepseek(prompt, system_prompt)
        result = self._parse_json_response(response)

        if result:
            self.cache[cache_key] = {
                'response': result,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache()
            return result

        # Fallback based on lead-lag
        if lead_lag_days < -1:
            role = 'driver'
        elif lead_lag_days > 1:
            role = 'beneficiary'
        else:
            role = 'beneficiary'

        return {'role': role, 'confidence': 0.5, 'reasoning': 'Based on lead-lag analysis'}

    # =========================================================================
    # STAGE DETECTION
    # =========================================================================

    def detect_theme_stage(self, theme_name: str,
                           recent_headlines: List[str],
                           quant_signals: Dict) -> Dict:
        """
        Detect theme lifecycle stage from narrative + quantitative signals.

        Returns:
        {
            'stage': 'early|middle|peak|fading',
            'confidence': 0.8,
            'evidence': ['Key evidence points'],
            'days_to_next_stage': 30
        }
        """
        cache_key = self._get_cache_key('stage', {
            'theme': theme_name,
            'headlines_hash': hashlib.md5(''.join(recent_headlines[:5]).encode()).hexdigest()[:8]
        })

        if cache_key in self.cache:
            cached = self.cache[cache_key]
            # Stages can change quickly, shorter cache
            age = datetime.now() - datetime.fromisoformat(cached['timestamp'])
            if age.total_seconds() < 6 * 3600:  # 6 hour cache
                return cached['response']

        headlines_text = "\n".join([f"- {h}" for h in recent_headlines[:20]])

        prompt = f"""Analyze the lifecycle stage of the "{theme_name}" investment theme.

RECENT HEADLINES (newest first):
{headlines_text}

QUANTITATIVE SIGNALS:
- News volume trend: {quant_signals.get('news_trend', 'unknown')}
- 30-day price momentum: {quant_signals.get('momentum_30d', 'unknown')}
- Retail interest (social): {quant_signals.get('retail_buzz', 'unknown')}
- Institutional activity: {quant_signals.get('institutional', 'unknown')}

STAGE DEFINITIONS:
- EARLY: Theme emerging, few talking about it, discovery language, "under the radar"
- MIDDLE: Theme recognized, institutions building, upgrades, momentum growing
- PEAK: Maximum hype, retail FOMO, superlatives, "everyone knows", bubble warnings
- FADING: Narrative exhausted, profit-taking, rotation talk, disappointment

Look for language patterns:
- Early: "new opportunity", "emerging", "under-appreciated"
- Middle: "continues to", "analysts upgrade", "fund flows"
- Peak: "explosive", "can't miss", "everyone's talking about"
- Fading: "disappointing", "concerns mount", "rotating out"

Return JSON:
{{
    "stage": "early|middle|peak|fading",
    "confidence": 0.0-1.0,
    "evidence": ["3-5 key evidence points from headlines"],
    "days_to_next_stage": estimated_days_or_null,
    "warning_signs": ["any concerning patterns"]
}}"""

        system_prompt = """You are a market strategist analyzing investment theme lifecycles.
Read the narrative arc in headlines to determine where we are in the cycle.
Early detection of stage changes is valuable alpha.
Return valid JSON only."""

        response = self._call_deepseek(prompt, system_prompt)
        result = self._parse_json_response(response)

        if result:
            self.cache[cache_key] = {
                'response': result,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache()
            return result

        return {
            'stage': 'unknown',
            'confidence': 0.3,
            'evidence': ['Insufficient data for AI analysis'],
        }

    # =========================================================================
    # SUPPLY CHAIN DISCOVERY
    # =========================================================================

    def discover_supply_chain(self, ticker: str,
                              company_info: Dict,
                              recent_news: List[str] = None) -> Dict:
        """
        Discover supply chain relationships from company info and news.

        Returns:
        {
            'suppliers': [{'ticker': 'TSM', 'relationship': 'chip fabrication', 'strength': 9}],
            'customers': [...],
            'competitors': [...],
            'ecosystem': [...]
        }
        """
        cache_key = self._get_cache_key('supply_chain', {'ticker': ticker})

        if cache_key in self.cache:
            cached = self.cache[cache_key]
            # Supply chains change slowly
            age = datetime.now() - datetime.fromisoformat(cached['timestamp'])
            if age.total_seconds() < 7 * 24 * 3600:  # 7 day cache
                return cached['response']

        news_text = ""
        if recent_news:
            news_text = "\n".join([f"- {n}" for n in recent_news[:10]])

        prompt = f"""Analyze {ticker}'s business relationships and supply chain.

COMPANY INFO:
Name: {company_info.get('name', ticker)}
Sector: {company_info.get('sector', 'Unknown')}
Industry: {company_info.get('industry', 'Unknown')}
Description: {company_info.get('description', '')[:600]}

{f'RECENT NEWS:{chr(10)}{news_text}' if news_text else ''}

Identify key relationships:

Return JSON:
{{
    "suppliers": [
        {{"ticker": "XXX", "name": "Company Name", "relationship": "what they provide", "strength": 1-10}}
    ],
    "customers": [
        {{"ticker": "XXX", "name": "Company Name", "relationship": "what they buy", "strength": 1-10}}
    ],
    "competitors": [
        {{"ticker": "XXX", "name": "Company Name", "competitive_overlap": "description", "strength": 1-10}}
    ],
    "ecosystem_partners": [
        {{"ticker": "XXX", "name": "Company Name", "relationship": "how they benefit together", "strength": 1-10}}
    ]
}}

Only include publicly traded US stocks. Use standard ticker symbols.
Focus on material relationships (strength >= 6)."""

        system_prompt = """You are a supply chain analyst identifying business relationships.
Only include relationships you're confident about from public information.
Use standard US ticker symbols. Return valid JSON only."""

        response = self._call_deepseek(prompt, system_prompt)
        result = self._parse_json_response(response)

        if result:
            self.cache[cache_key] = {
                'response': result,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache()
            return result

        return {
            'suppliers': [],
            'customers': [],
            'competitors': [],
            'ecosystem_partners': []
        }

    # =========================================================================
    # EMERGING THEME DETECTION
    # =========================================================================

    def detect_emerging_themes(self, news_feed: List[Dict]) -> List[Dict]:
        """
        Detect emerging themes from news before they show in correlations.

        Returns list of emerging themes:
        [{
            'name': 'Theme Name',
            'description': '...',
            'tickers': ['XXX', 'YYY'],
            'catalyst': 'What\'s driving emergence',
            'confidence': 0.7,
            'days_to_mainstream': 14
        }]
        """
        if len(news_feed) < 10:
            return []

        # Format headlines
        headlines = []
        for item in news_feed[:50]:
            title = item.get('title', '')
            ticker = item.get('ticker', '')
            if title:
                headlines.append(f"[{ticker}] {title}" if ticker else title)

        headlines_text = "\n".join([f"- {h}" for h in headlines])

        prompt = f"""Analyze these market news headlines for EMERGING investment themes.

RECENT HEADLINES (last 48 hours):
{headlines_text}

Look for:
1. NEW NARRATIVES: Topics getting attention for the first time
2. INFLECTION POINTS: Established themes accelerating or decelerating
3. CROSS-SECTOR CONNECTIONS: Themes affecting multiple sectors
4. POLICY CATALYSTS: Government actions creating investment opportunities
5. TECHNOLOGY SHIFTS: New technology enabling new investments

IMPORTANT: Focus on themes NOT YET widely recognized by mainstream investors.

Return JSON:
{{
    "emerging_themes": [
        {{
            "name": "Theme Name (2-4 words)",
            "description": "What is this theme about",
            "thesis": "Why this matters for investors",
            "tickers": ["relevant", "tickers"],
            "catalyst": "What's driving emergence now",
            "confidence": 0.0-1.0,
            "days_to_mainstream": estimated_days,
            "risk_factors": ["potential risks"]
        }}
    ]
}}

Only include themes with confidence >= 0.6"""

        system_prompt = """You are a thematic research analyst looking for emerging investment themes.
Your edge is identifying themes BEFORE they become consensus.
Focus on actionable themes with clear stock implications.
Return valid JSON only."""

        response = self._call_deepseek(prompt, system_prompt)
        result = self._parse_json_response(response)

        if result and 'emerging_themes' in result:
            return result['emerging_themes']

        return []

    # =========================================================================
    # MEMBERSHIP VALIDATION
    # =========================================================================

    def validate_theme_membership(self, ticker: str, theme_name: str,
                                   company_description: str,
                                   correlation: float) -> Dict:
        """
        Validate if a stock truly belongs to a theme (avoid spurious correlations).

        Returns:
        {
            'belongs': True/False,
            'confidence': 0.85,
            'reasoning': '...',
            'alternative_themes': ['other', 'themes', 'it', 'might', 'belong', 'to']
        }
        """
        cache_key = self._get_cache_key('membership', {
            'ticker': ticker,
            'theme': theme_name
        })

        if cache_key in self.cache:
            return self.cache[cache_key]['response']

        prompt = f"""Should {ticker} be included in the "{theme_name}" investment theme?

COMPANY:
{company_description[:400]}

CORRELATION WITH THEME: {correlation:.2f}

Questions to answer:
1. Does this company's business genuinely connect to the theme?
2. Is the correlation likely causal (real relationship) or spurious (coincidence)?
3. Would theme investors logically want to own this stock?
4. Are there better themes this stock belongs to?

Return JSON:
{{
    "belongs": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Explanation of decision",
    "connection_type": "direct|indirect|tangential|spurious",
    "alternative_themes": ["themes", "this", "stock", "better", "fits"]
}}"""

        system_prompt = """You are a portfolio manager validating thematic stock assignments.
High correlation doesn't mean the stock belongs - the connection must be logical.
Be skeptical of spurious correlations. Return valid JSON only."""

        response = self._call_deepseek(prompt, system_prompt)
        result = self._parse_json_response(response)

        if result:
            self.cache[cache_key] = {
                'response': result,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache()
            return result

        # Default: trust correlation if strong enough
        return {
            'belongs': correlation >= 0.6,
            'confidence': 0.5,
            'reasoning': 'Based on correlation strength only',
            'connection_type': 'unknown'
        }

    # =========================================================================
    # BATCH PROCESSING
    # =========================================================================

    def batch_classify_roles(self, theme_name: str,
                              stocks_data: List[Dict]) -> Dict[str, Dict]:
        """
        Classify multiple stocks' roles in a single API call.
        More efficient than individual calls.
        """
        if not stocks_data:
            return {}

        stocks_text = "\n".join([
            f"- {s['ticker']}: {s.get('description', 'N/A')[:100]}... (lead-lag: {s.get('lead_lag', 0):+.1f}d)"
            for s in stocks_data[:10]
        ])

        prompt = f"""Classify these stocks' roles in the "{theme_name}" theme.

STOCKS:
{stocks_text}

For each stock, determine:
- DRIVER: Core to theme, moves first
- BENEFICIARY: Benefits from theme, moves after
- PICKS_SHOVELS: Suppliers/enablers, steady
- PERIPHERAL: Loosely connected

Return JSON:
{{
    "classifications": {{
        "TICKER1": {{"role": "driver", "confidence": 0.8, "reason": "..."}},
        "TICKER2": {{"role": "beneficiary", "confidence": 0.7, "reason": "..."}}
    }}
}}"""

        system_prompt = "Classify stock roles in investment themes. Return valid JSON only."

        response = self._call_deepseek(prompt, system_prompt)
        result = self._parse_json_response(response)

        if result and 'classifications' in result:
            return result['classifications']

        return {}

    # =========================================================================
    # HEALTH MONITORING
    # =========================================================================

    def run_health_check(self) -> AIHealthStatus:
        """Run health check on AI system"""
        daily_calls = sum(self.usage.values())
        budget_remaining = max(0, self.DAILY_BUDGET - daily_calls)

        # Calculate average latency
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0

        # Check API availability
        api_available = bool(self.api_key)

        # Determine status
        if not api_available:
            status = 'unavailable'
        elif budget_remaining == 0:
            status = 'exhausted'
        elif budget_remaining < self.DAILY_BUDGET * 0.1:
            status = 'low_budget'
        elif avg_latency > 5000:  # 5 seconds
            status = 'slow'
        else:
            status = 'healthy'

        # Calculate health score
        health_score = 100.0
        if not api_available:
            health_score = 0
        elif status == 'exhausted':
            health_score = 10
        elif status == 'low_budget':
            health_score = 50
        elif status == 'slow':
            health_score = 70

        health = AIHealthStatus(
            status=status,
            api_available=api_available,
            cache_size=len(self.cache),
            daily_calls=daily_calls,
            daily_budget=self.DAILY_BUDGET,
            budget_remaining=budget_remaining,
            avg_latency_ms=avg_latency,
            last_error=self.last_error,
            last_check=datetime.now().isoformat(),
            model="deepseek-chat",
            calls_last_24h=daily_calls,
            health_score=health_score,
        )

        # Save health
        with open(HEALTH_FILE, 'w') as f:
            json.dump(asdict(health), f, indent=2)

        return health

    def get_health_summary(self) -> Dict:
        """Get health summary"""
        return asdict(self.run_health_check())


# =============================================================================
# PUBLIC API
# =============================================================================

_intelligence: Optional[DeepSeekIntelligence] = None


def get_intelligence() -> DeepSeekIntelligence:
    """Get DeepSeek intelligence singleton"""
    global _intelligence
    if _intelligence is None:
        _intelligence = DeepSeekIntelligence()
    return _intelligence


# Alias for compatibility
get_deepseek_intelligence = get_intelligence


def generate_theme_info(stocks: List[str], headlines: List[str] = None) -> Dict:
    """Generate theme name and thesis"""
    return get_intelligence().generate_theme_info(stocks, headlines)


def classify_role(ticker: str, theme: str, description: str,
                  lead_lag: float = 0, correlation: float = 0) -> Dict:
    """Classify stock role in theme"""
    return get_intelligence().classify_role(ticker, theme, description, lead_lag, correlation)


def detect_stage(theme: str, headlines: List[str], signals: Dict) -> Dict:
    """Detect theme lifecycle stage"""
    return get_intelligence().detect_theme_stage(theme, headlines, signals)


def discover_supply_chain(ticker: str, company_info: Dict, news: List[str] = None) -> Dict:
    """Discover supply chain relationships"""
    return get_intelligence().discover_supply_chain(ticker, company_info, news)


def detect_emerging_themes(news_feed: List[Dict]) -> List[Dict]:
    """Detect emerging themes from news"""
    return get_intelligence().detect_emerging_themes(news_feed)


def validate_membership(ticker: str, theme: str, description: str, correlation: float) -> Dict:
    """Validate theme membership"""
    return get_intelligence().validate_theme_membership(ticker, theme, description, correlation)


def run_health_check() -> Dict:
    """Run AI health check"""
    return get_intelligence().get_health_summary()


if __name__ == '__main__':
    # Test
    health = run_health_check()
    print(f"AI Status: {health['status']}")
    print(f"API Available: {health['api_available']}")
    print(f"Budget Remaining: {health['budget_remaining']}/{health['daily_budget']}")
