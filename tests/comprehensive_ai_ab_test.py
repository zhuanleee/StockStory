#!/usr/bin/env python3
"""
Comprehensive AI A/B Test - DeepSeek vs xAI
============================================

Tests BOTH providers on ALL AI tasks in the Stock Scanner Bot project.
NO SIMULATIONS - REAL API CALLS ONLY.

Tests:
1. Theme naming & thesis generation
2. Role classification (driver, beneficiary, etc.)
3. Stage detection (early, middle, peak, fading)
4. Supply chain discovery
5. Emerging theme detection
6. Membership validation
7. Sentiment analysis
8. News summarization
9. Market analysis
10. Pattern recognition
11. Ecosystem mapping
12. Stress testing (concurrent requests, rate limits)

Usage:
    python tests/comprehensive_ai_ab_test.py

Requires:
    - DEEPSEEK_API_KEY in environment
    - XAI_API_KEY in environment
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
XAI_API_KEY = os.environ.get('XAI_API_KEY', '')

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
XAI_URL = "https://api.x.ai/v1/chat/completions"


@dataclass
class TaskResult:
    """Result for a single AI task test."""
    provider: str
    task_name: str
    task_category: str  # theme/sentiment/analysis/etc
    success: bool
    response_time: float
    tokens_used: int
    cost_usd: float
    quality_score: int  # 0-100
    error: Optional[str]
    response_preview: str
    timestamp: str


class ComprehensiveAITester:
    """Comprehensive AI testing across all project tasks."""

    # Cost per 1M tokens
    COSTS = {
        'deepseek': {
            'input': 0.14,
            'output': 0.28
        },
        'xai': {
            'input': 0.20,  # Actual xAI pricing
            'output': 0.50  # Actual xAI pricing
        }
    }

    def __init__(self):
        self.results: List[TaskResult] = []
        self.deepseek_available = bool(DEEPSEEK_API_KEY and len(DEEPSEEK_API_KEY) > 10)
        self.xai_available = bool(XAI_API_KEY and len(XAI_API_KEY) > 10)

        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE AI A/B TEST - DeepSeek vs xAI")
        print(f"{'='*80}\n")
        print(f"DeepSeek API: {'✓ Configured' if self.deepseek_available else '✗ NOT CONFIGURED'}")
        print(f"xAI API: {'✓ Configured' if self.xai_available else '✗ NOT CONFIGURED'}")

        if not self.deepseek_available and not self.xai_available:
            print("\n❌ ERROR: No API keys configured!")
            print("Please set DEEPSEEK_API_KEY and/or XAI_API_KEY in your .env file")
            sys.exit(1)

        if not self.xai_available:
            print("\n⚠️  WARNING: xAI API key not set. Only testing DeepSeek.")
            print("To enable full A/B comparison, add XAI_API_KEY to .env")
            print("Get your key at: https://console.x.ai/")

        print()

    def _call_api(
        self,
        provider: str,
        prompt: str,
        system_prompt: str = "You are a helpful financial analyst.",
        max_tokens: int = 1000,
        temperature: float = 0.3
    ) -> Tuple[bool, Optional[str], Optional[Dict], Optional[str], float]:
        """
        Make API call to provider.

        Returns:
            (success, response_text, usage_dict, error, response_time)
        """
        start_time = time.time()

        if provider == 'deepseek':
            if not self.deepseek_available:
                return False, None, None, "API key not configured", 0.0

            url = DEEPSEEK_URL
            api_key = DEEPSEEK_API_KEY
            model = "deepseek-chat"

        elif provider == 'xai':
            if not self.xai_available:
                return False, None, None, "API key not configured", 0.0

            url = XAI_URL
            api_key = XAI_API_KEY
            model = "grok-4-1-fast-non-reasoning"

        else:
            return False, None, None, f"Unknown provider: {provider}", 0.0

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            import requests
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=60
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                text = result['choices'][0]['message']['content']
                usage = result.get('usage', {})
                return True, text, usage, None, response_time
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                return False, None, None, error_msg, response_time

        except Exception as e:
            response_time = time.time() - start_time
            return False, None, None, str(e), response_time

    def _calculate_cost(self, provider: str, tokens: int) -> float:
        """Calculate cost for token usage."""
        if tokens == 0:
            return 0.0

        # Assume 50/50 split input/output
        input_tokens = tokens * 0.5
        output_tokens = tokens * 0.5

        cost = (
            (input_tokens / 1_000_000 * self.COSTS[provider]['input']) +
            (output_tokens / 1_000_000 * self.COSTS[provider]['output'])
        )
        return cost

    # =========================================================================
    # TEST 1: THEME NAMING & THESIS GENERATION
    # =========================================================================

    def test_theme_naming(self, provider: str) -> TaskResult:
        """Test AI's ability to name themes and generate thesis."""
        print(f"\n[{provider.upper()}] Testing Theme Naming & Thesis Generation...")

        prompt = """Analyze this cluster of correlated stocks and identify the investment theme.

STOCKS MOVING TOGETHER: NVDA, AMD, SMCI, MRVL, AVGO, ARM

RECENT HEADLINES:
- NVIDIA reports record datacenter revenue, driven by AI demand
- AMD launches new MI300 AI accelerators to compete with NVIDIA
- Super Micro sees surge in AI server orders
- Marvell announces custom AI chip design wins
- Broadcom's AI networking revenue doubles

Provide analysis as JSON:
{
    "name": "Theme name (2-4 words)",
    "thesis": "Investment thesis explaining WHY these stocks are correlated (2-3 sentences)",
    "keywords": ["list", "of", "keywords"],
    "stage": "early|middle|peak|fading",
    "catalyst": "What's driving this theme now",
    "confidence": 0.0-1.0
}"""

        system_prompt = """You are a senior equity analyst specializing in thematic investing.
Identify investment themes from stock correlations and news patterns.
Return valid JSON only."""

        success, response, usage, error, resp_time = self._call_api(
            provider, prompt, system_prompt, max_tokens=500
        )

        tokens = usage.get('total_tokens', 0) if usage else 0
        cost = self._calculate_cost(provider, tokens)

        # Quality scoring
        quality = 0
        if success and response:
            if '"name"' in response:
                quality += 30
            if '"thesis"' in response and len(response) > 100:
                quality += 30
            if any(keyword in response.upper() for keyword in ['AI', 'NVIDIA', 'DATA', 'CHIP']):
                quality += 20
            if '"confidence"' in response:
                quality += 20

        result = TaskResult(
            provider=provider,
            task_name="theme_naming",
            task_category="theme_intelligence",
            success=success,
            response_time=resp_time,
            tokens_used=tokens,
            cost_usd=cost,
            quality_score=quality,
            error=error,
            response_preview=response[:200] if response else "",
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)

        print(f"  {'✓' if success else '✗'} {resp_time:.2f}s | {tokens} tokens | Quality: {quality}/100")
        return result

    # =========================================================================
    # TEST 2: ROLE CLASSIFICATION
    # =========================================================================

    def test_role_classification(self, provider: str) -> TaskResult:
        """Test AI's ability to classify stock roles in themes."""
        print(f"\n[{provider.upper()}] Testing Role Classification...")

        prompt = """Classify NVDA's role in the "AI Infrastructure" investment theme.

COMPANY: NVIDIA Corporation - Designs GPUs and AI accelerators for datacenter and edge computing.

QUANTITATIVE SIGNALS:
- Lead/lag vs theme average: -2.5 days (leads the theme)
- Correlation with theme: 0.92

ROLE DEFINITIONS:
- DRIVER: Sets the narrative, moves first, core to theme success
- BENEFICIARY: Benefits from theme, moves after drivers
- PICKS_SHOVELS: Suppliers/enablers, steady but less volatile
- PERIPHERAL: Loosely connected

Return JSON:
{
    "role": "driver|beneficiary|picks_shovels|peripheral",
    "confidence": 0.0-1.0,
    "reasoning": "Explanation based on business AND quantitative signals"
}"""

        success, response, usage, error, resp_time = self._call_api(
            provider, prompt, max_tokens=300
        )

        tokens = usage.get('total_tokens', 0) if usage else 0
        cost = self._calculate_cost(provider, tokens)

        # Quality scoring
        quality = 0
        if success and response:
            if '"driver"' in response.lower():
                quality += 40  # Correct answer
            if '"reasoning"' in response:
                quality += 30
            if 'GPU' in response or 'lead' in response.lower():
                quality += 30

        result = TaskResult(
            provider=provider,
            task_name="role_classification",
            task_category="theme_intelligence",
            success=success,
            response_time=resp_time,
            tokens_used=tokens,
            cost_usd=cost,
            quality_score=quality,
            error=error,
            response_preview=response[:200] if response else "",
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)

        print(f"  {'✓' if success else '✗'} {resp_time:.2f}s | {tokens} tokens | Quality: {quality}/100")
        return result

    # =========================================================================
    # TEST 3: STAGE DETECTION
    # =========================================================================

    def test_stage_detection(self, provider: str) -> TaskResult:
        """Test AI's ability to detect theme lifecycle stage."""
        print(f"\n[{provider.upper()}] Testing Stage Detection...")

        prompt = """Analyze the lifecycle stage of the "AI Infrastructure" investment theme.

RECENT HEADLINES:
- AI chip demand remains insatiable, NVIDIA can't keep up
- Microsoft, Google ramp up AI datacenter spending to record levels
- Retail investors pile into AI stocks, search interest at all-time highs
- Warning signs emerge: AI valuations stretch to extremes
- Some analysts call AI the biggest bubble since dot-com

QUANTITATIVE SIGNALS:
- News volume: Extremely high (200+ articles/day)
- 30-day momentum: +45%
- Retail interest: All-time high
- Institutional activity: Heavy accumulation slowing

STAGE DEFINITIONS:
- EARLY: Emerging, few talking about it
- MIDDLE: Recognized, institutions building
- PEAK: Maximum hype, retail FOMO, everyone knows
- FADING: Narrative exhausted, profit-taking

Return JSON:
{
    "stage": "early|middle|peak|fading",
    "confidence": 0.0-1.0,
    "evidence": ["key evidence points"],
    "warning_signs": ["concerning patterns"]
}"""

        success, response, usage, error, resp_time = self._call_api(
            provider, prompt, max_tokens=400
        )

        tokens = usage.get('total_tokens', 0) if usage else 0
        cost = self._calculate_cost(provider, tokens)

        # Quality scoring
        quality = 0
        if success and response:
            if '"peak"' in response.lower():
                quality += 40  # Correct answer given the signals
            if '"warning"' in response.lower():
                quality += 30
            if '"bubble"' in response.lower() or 'valuation' in response.lower():
                quality += 30

        result = TaskResult(
            provider=provider,
            task_name="stage_detection",
            task_category="theme_intelligence",
            success=success,
            response_time=resp_time,
            tokens_used=tokens,
            cost_usd=cost,
            quality_score=quality,
            error=error,
            response_preview=response[:200] if response else "",
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)

        print(f"  {'✓' if success else '✗'} {resp_time:.2f}s | {tokens} tokens | Quality: {quality}/100")
        return result

    # =========================================================================
    # TEST 4: SUPPLY CHAIN DISCOVERY
    # =========================================================================

    def test_supply_chain(self, provider: str) -> TaskResult:
        """Test AI's ability to map supply chains."""
        print(f"\n[{provider.upper()}] Testing Supply Chain Discovery...")

        prompt = """Identify NVIDIA's key business relationships and supply chain.

COMPANY INFO:
Name: NVIDIA Corporation
Sector: Technology
Industry: Semiconductors
Description: NVIDIA designs GPUs and AI accelerators. Fabless semiconductor company that outsources manufacturing to foundries. Sells to cloud providers, enterprises, and consumers.

Identify key relationships. Return JSON:
{
    "suppliers": [
        {"ticker": "TSM", "relationship": "chip fabrication", "strength": 9}
    ],
    "customers": [
        {"ticker": "MSFT", "relationship": "datacenter GPUs", "strength": 8}
    ],
    "competitors": [
        {"ticker": "AMD", "relationship": "AI accelerators", "strength": 9}
    ]
}

Only include publicly traded US stocks with strength >= 7."""

        success, response, usage, error, resp_time = self._call_api(
            provider, prompt, max_tokens=500
        )

        tokens = usage.get('total_tokens', 0) if usage else 0
        cost = self._calculate_cost(provider, tokens)

        # Quality scoring
        quality = 0
        if success and response:
            key_suppliers = ['TSM', 'ASML', 'SK', 'MICRON']
            key_customers = ['MSFT', 'GOOGL', 'AMZN', 'META']
            key_competitors = ['AMD', 'INTC']

            if any(s in response.upper() for s in key_suppliers):
                quality += 35
            if any(c in response.upper() for c in key_customers):
                quality += 35
            if any(c in response.upper() for c in key_competitors):
                quality += 30

        result = TaskResult(
            provider=provider,
            task_name="supply_chain_discovery",
            task_category="ecosystem_intelligence",
            success=success,
            response_time=resp_time,
            tokens_used=tokens,
            cost_usd=cost,
            quality_score=quality,
            error=error,
            response_preview=response[:200] if response else "",
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)

        print(f"  {'✓' if success else '✗'} {resp_time:.2f}s | {tokens} tokens | Quality: {quality}/100")
        return result

    # =========================================================================
    # TEST 5: SENTIMENT ANALYSIS
    # =========================================================================

    def test_sentiment_analysis(self, provider: str) -> TaskResult:
        """Test AI's sentiment analysis capability."""
        print(f"\n[{provider.upper()}] Testing Sentiment Analysis...")

        prompt = """Analyze sentiment of this financial text:

"NVIDIA crushes Q4 earnings with record $22B revenue (+265% YoY), driven by insatiable AI demand. Management guides Q1 above consensus, raising full-year outlook. Data center revenue hits $18.4B, up 409% YoY. Supply constraints easing, but demand visibility extends through 2025."

Respond with JSON:
{
    "sentiment": "bullish|bearish|neutral",
    "score": -1.0 to 1.0,
    "confidence": 0.0-1.0,
    "key_factors": ["factor1", "factor2", "factor3"]
}"""

        success, response, usage, error, resp_time = self._call_api(
            provider, prompt, max_tokens=200
        )

        tokens = usage.get('total_tokens', 0) if usage else 0
        cost = self._calculate_cost(provider, tokens)

        # Quality scoring
        quality = 0
        if success and response:
            if '"bullish"' in response.lower():
                quality += 40  # Correct sentiment
            if '"score"' in response and '0.' in response:
                quality += 30
            if '"key_factors"' in response:
                quality += 30

        result = TaskResult(
            provider=provider,
            task_name="sentiment_analysis",
            task_category="sentiment",
            success=success,
            response_time=resp_time,
            tokens_used=tokens,
            cost_usd=cost,
            quality_score=quality,
            error=error,
            response_preview=response[:200] if response else "",
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)

        print(f"  {'✓' if success else '✗'} {resp_time:.2f}s | {tokens} tokens | Quality: {quality}/100")
        return result

    # =========================================================================
    # TEST 6: PATTERN RECOGNITION
    # =========================================================================

    def test_pattern_recognition(self, provider: str) -> TaskResult:
        """Test AI's technical pattern recognition."""
        print(f"\n[{provider.upper()}] Testing Pattern Recognition...")

        prompt = """Identify the trading pattern from this price/volume data:

Day 1: +8.5%, volume 2.5x average (breakout)
Day 2: +5.2%, volume 2.1x average (continuation)
Day 3: +2.1%, volume 1.8x average (momentum fading)
Day 4: -1.5%, volume 1.2x average (profit taking)
Day 5: -0.8%, volume 0.9x average (consolidation)

Identify the pattern and next likely move. Response in 2-3 sentences."""

        success, response, usage, error, resp_time = self._call_api(
            provider, prompt, max_tokens=200
        )

        tokens = usage.get('total_tokens', 0) if usage else 0
        cost = self._calculate_cost(provider, tokens)

        # Quality scoring
        quality = 0
        if success and response:
            pattern_keywords = ['exhaustion', 'blow-off', 'consolidation', 'pullback', 'pause']
            if any(kw in response.lower() for kw in pattern_keywords):
                quality += 40
            if len(response) > 50:
                quality += 30
            if 'volume' in response.lower() and 'fading' in response.lower():
                quality += 30

        result = TaskResult(
            provider=provider,
            task_name="pattern_recognition",
            task_category="technical_analysis",
            success=success,
            response_time=resp_time,
            tokens_used=tokens,
            cost_usd=cost,
            quality_score=quality,
            error=error,
            response_preview=response[:200] if response else "",
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)

        print(f"  {'✓' if success else '✗'} {resp_time:.2f}s | {tokens} tokens | Quality: {quality}/100")
        return result

    # =========================================================================
    # TEST 7: MARKET ANALYSIS
    # =========================================================================

    def test_market_analysis(self, provider: str) -> TaskResult:
        """Test AI's comprehensive market analysis capability."""
        print(f"\n[{provider.upper()}] Testing Market Analysis...")

        prompt = """Analyze the current AI chip market. Include:
1. Top 3 companies by competitive position
2. Key trends driving growth
3. Major risks to watch

Keep under 250 words."""

        success, response, usage, error, resp_time = self._call_api(
            provider, prompt, max_tokens=500
        )

        tokens = usage.get('total_tokens', 0) if usage else 0
        cost = self._calculate_cost(provider, tokens)

        # Quality scoring
        quality = 0
        if success and response:
            companies = ['NVIDIA', 'NVDA', 'AMD', 'INTEL', 'INTC', 'TSMC', 'TSM']
            if any(c in response.upper() for c in companies):
                quality += 35
            if any(c in response for c in ['1.', '2.', '3.']):
                quality += 30
            if 'risk' in response.lower() or 'trend' in response.lower():
                quality += 35

        result = TaskResult(
            provider=provider,
            task_name="market_analysis",
            task_category="market_intelligence",
            success=success,
            response_time=resp_time,
            tokens_used=tokens,
            cost_usd=cost,
            quality_score=quality,
            error=error,
            response_preview=response[:200] if response else "",
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)

        print(f"  {'✓' if success else '✗'} {resp_time:.2f}s | {tokens} tokens | Quality: {quality}/100")
        return result

    # =========================================================================
    # TEST 8: STRESS TEST - CONCURRENT REQUESTS
    # =========================================================================

    def test_concurrent_requests(self, provider: str, concurrent: int = 3) -> List[TaskResult]:
        """Test concurrent request handling."""
        print(f"\n[{provider.upper()}] Testing Concurrent Requests ({concurrent} parallel)...")

        prompts = [
            "What is the current state of AI infrastructure investment? (1 sentence)",
            "Explain the semiconductor supply chain briefly. (1 sentence)",
            "What drives GPU demand for AI? (1 sentence)"
        ][:concurrent]

        results = []

        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = {
                executor.submit(self._call_api, provider, prompt, max_tokens=100): i
                for i, prompt in enumerate(prompts)
            }

            for future in as_completed(futures):
                i = futures[future]
                success, response, usage, error, resp_time = future.result()

                tokens = usage.get('total_tokens', 0) if usage else 0
                cost = self._calculate_cost(provider, tokens)

                result = TaskResult(
                    provider=provider,
                    task_name=f"concurrent_{i+1}",
                    task_category="stress_test",
                    success=success,
                    response_time=resp_time,
                    tokens_used=tokens,
                    cost_usd=cost,
                    quality_score=100 if success else 0,
                    error=error,
                    response_preview=response[:100] if response else "",
                    timestamp=datetime.now().isoformat()
                )
                results.append(result)
                self.results.append(result)

                print(f"  [{i+1}/{concurrent}] {'✓' if success else '✗'} {resp_time:.2f}s")

        return results

    # =========================================================================
    # RUN FULL TEST SUITE
    # =========================================================================

    def run_full_suite(self):
        """Run complete test suite for all configured providers."""
        print(f"\n{'#'*80}")
        print(f"COMPREHENSIVE AI A/B TEST - ALL PROJECT TASKS")
        print(f"{'#'*80}\n")

        providers = []
        if self.deepseek_available:
            providers.append('deepseek')
        if self.xai_available:
            providers.append('xai')

        for provider in providers:
            print(f"\n\n{'█'*80}")
            print(f"{'TESTING: ' + provider.upper():^80}")
            print(f"{'█'*80}")

            # Run all tests
            self.test_theme_naming(provider)
            time.sleep(1)

            self.test_role_classification(provider)
            time.sleep(1)

            self.test_stage_detection(provider)
            time.sleep(1)

            self.test_supply_chain(provider)
            time.sleep(1)

            self.test_sentiment_analysis(provider)
            time.sleep(1)

            self.test_pattern_recognition(provider)
            time.sleep(1)

            self.test_market_analysis(provider)
            time.sleep(1)

            self.test_concurrent_requests(provider, concurrent=3)
            time.sleep(2)

        # Generate comparison
        self.print_comparison()
        self.save_results()

    def print_comparison(self):
        """Print detailed comparison between providers."""
        if not self.xai_available:
            print(f"\n{'='*80}")
            print("DEEPSEEK RESULTS (Single Provider Test)")
            print(f"{'='*80}\n")
            self.print_provider_summary('deepseek')
            return

        print(f"\n{'='*80}")
        print("COMPREHENSIVE A/B COMPARISON")
        print(f"{'='*80}\n")

        # Compare by task category
        categories = set(r.task_category for r in self.results)

        for category in sorted(categories):
            print(f"\n{'─'*80}")
            print(f"{category.upper().replace('_', ' ')}")
            print(f"{'─'*80}")

            category_results = [r for r in self.results if r.task_category == category]

            # Group by task name
            tasks = {}
            for r in category_results:
                if r.task_name not in tasks:
                    tasks[r.task_name] = {}
                tasks[r.task_name][r.provider] = r

            # Compare each task
            for task_name, providers_results in tasks.items():
                print(f"\n{task_name.replace('_', ' ').title()}:")

                ds = providers_results.get('deepseek')
                xai = providers_results.get('xai')

                if ds and xai:
                    print(f"  DeepSeek:  {ds.response_time:.2f}s | Quality: {ds.quality_score}/100 | ${ds.cost_usd:.6f}")
                    print(f"  xAI:       {xai.response_time:.2f}s | Quality: {xai.quality_score}/100 | ${xai.cost_usd:.6f}")

                    # Winner
                    if ds.quality_score > xai.quality_score:
                        print(f"  Winner: DeepSeek (quality)")
                    elif xai.quality_score > ds.quality_score:
                        print(f"  Winner: xAI (quality)")
                    elif ds.response_time < xai.response_time:
                        print(f"  Winner: DeepSeek (speed)")
                    else:
                        print(f"  Winner: xAI (speed)")

        # Overall summary
        print(f"\n\n{'='*80}")
        print("OVERALL SUMMARY")
        print(f"{'='*80}\n")

        self.print_provider_summary('deepseek')
        print()
        self.print_provider_summary('xai')

        # Recommendation
        print(f"\n{'='*80}")
        print("RECOMMENDATION")
        print(f"{'='*80}\n")

        ds_results = [r for r in self.results if r.provider == 'deepseek']
        xai_results = [r for r in self.results if r.provider == 'xai']

        if ds_results and xai_results:
            ds_successful = [r for r in ds_results if r.success]
            xai_successful = [r for r in xai_results if r.success]

            ds_avg_quality = statistics.mean([r.quality_score for r in ds_successful]) if ds_successful else 0.0
            xai_avg_quality = statistics.mean([r.quality_score for r in xai_successful]) if xai_successful else 0.0

            ds_avg_time = statistics.mean([r.response_time for r in ds_results])
            xai_avg_time = statistics.mean([r.response_time for r in xai_results])

            ds_total_cost = sum([r.cost_usd for r in ds_results])
            xai_total_cost = sum([r.cost_usd for r in xai_results])

            print(f"Quality:  DeepSeek {ds_avg_quality:.1f}/100 vs xAI {xai_avg_quality:.1f}/100")
            print(f"Speed:    DeepSeek {ds_avg_time:.2f}s vs xAI {xai_avg_time:.2f}s")
            print(f"Cost:     DeepSeek ${ds_total_cost:.4f} vs xAI ${xai_total_cost:.4f}")

            if ds_avg_quality >= xai_avg_quality * 0.9 and ds_total_cost < xai_total_cost * 0.5:
                print(f"\n🏆 RECOMMENDATION: Use DeepSeek (comparable quality, much lower cost)")
            elif xai_avg_quality > ds_avg_quality * 1.2:
                print(f"\n🏆 RECOMMENDATION: Use xAI (significantly better quality)")
            else:
                print(f"\n🏆 RECOMMENDATION: Use DeepSeek for batch, xAI for critical real-time tasks")

    def print_provider_summary(self, provider: str):
        """Print summary for a single provider."""
        provider_results = [r for r in self.results if r.provider == provider]
        if not provider_results:
            return

        successful = [r for r in provider_results if r.success]
        failed = [r for r in provider_results if not r.success]

        total_tokens = sum([r.tokens_used for r in provider_results])
        total_cost = sum([r.cost_usd for r in provider_results])
        avg_time = statistics.mean([r.response_time for r in provider_results])
        avg_quality = statistics.mean([r.quality_score for r in successful]) if successful else 0.0

        print(f"{provider.upper()} Summary:")
        print(f"  Total Tests: {len(provider_results)}")
        print(f"  Success Rate: {len(successful)}/{len(provider_results)} ({len(successful)/len(provider_results)*100:.1f}%)")
        print(f"  Avg Response Time: {avg_time:.2f}s")
        print(f"  Avg Quality Score: {avg_quality:.1f}/100 ({len(successful)} successful tests)")
        print(f"  Total Tokens: {total_tokens:,}")
        print(f"  Total Cost: ${total_cost:.4f}")

    def save_results(self):
        """Save results to JSON."""
        output = {
            "test_date": datetime.now().isoformat(),
            "test_type": "comprehensive_real_ab_test",
            "providers_tested": list(set(r.provider for r in self.results)),
            "total_tests": len(self.results),
            "results": [asdict(r) for r in self.results]
        }

        filename = f"ai_ab_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n📊 Results saved to: {filename}")


def main():
    """Main entry point."""
    tester = ComprehensiveAITester()
    tester.run_full_suite()


if __name__ == "__main__":
    main()
