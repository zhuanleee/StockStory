#!/usr/bin/env python3
"""
AI Stress Test & A/B Comparison: xAI vs DeepSeek
================================================

Tests:
1. Response Time (latency)
2. Rate Limiting Behavior
3. Concurrent Request Handling
4. Error Recovery
5. Response Quality
6. Token Efficiency
7. Cost Analysis

Usage:
    python tests/ai_stress_test.py
"""

import os
import sys
import time
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# API Configuration
XAI_API_KEY = os.environ.get('XAI_API_KEY', '')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

XAI_BASE = "https://api.x.ai/v1"
DEEPSEEK_BASE = "https://api.deepseek.com/v1"


@dataclass
class TestResult:
    """Single test result."""
    provider: str
    test_name: str
    success: bool
    response_time: float  # seconds
    tokens_used: Optional[int]
    error: Optional[str]
    response_quality: Optional[int]  # 0-100
    timestamp: str


@dataclass
class StressTestSummary:
    """Aggregate test summary."""
    provider: str
    total_tests: int
    successful: int
    failed: int
    success_rate: float
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    total_tokens: int
    avg_tokens_per_request: float
    total_cost: float
    errors: Dict[str, int]


class AIStressTester:
    """Stress test and A/B comparison for AI providers."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.xai_available = bool(XAI_API_KEY)
        self.deepseek_available = bool(DEEPSEEK_API_KEY)

        # Cost per 1M tokens (approximate)
        self.costs = {
            'xai': {
                'input': 5.0,   # $5 per 1M input tokens
                'output': 15.0  # $15 per 1M output tokens
            },
            'deepseek': {
                'input': 0.14,   # $0.14 per 1M input tokens
                'output': 0.28   # $0.28 per 1M output tokens
            }
        }

        print(f"xAI API Key: {'✓ Available' if self.xai_available else '✗ Missing'}")
        print(f"DeepSeek API Key: {'✓ Available' if self.deepseek_available else '✗ Missing'}")
        print()

    def _make_request(
        self,
        provider: str,
        prompt: str,
        system: str = "You are a helpful assistant.",
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Tuple[bool, Optional[str], Optional[Dict], Optional[str], float]:
        """
        Make API request to provider.

        Returns:
            (success, response_text, usage_dict, error, response_time)
        """
        start_time = time.time()

        if provider == 'xai':
            if not self.xai_available:
                return False, None, None, "API key not configured", 0.0

            url = f"{XAI_BASE}/chat/completions"
            headers = {
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "grok-beta",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }

        elif provider == 'deepseek':
            if not self.deepseek_available:
                return False, None, None, "API key not configured", 0.0

            url = f"{DEEPSEEK_BASE}/chat/completions"
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        else:
            return False, None, None, f"Unknown provider: {provider}", 0.0

        try:
            import requests
            response = requests.post(url, json=data, headers=headers, timeout=30)
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

    def test_latency(self, provider: str, iterations: int = 10) -> List[TestResult]:
        """Test average response time."""
        print(f"\n{'='*60}")
        print(f"LATENCY TEST: {provider.upper()} ({iterations} requests)")
        print(f"{'='*60}")

        prompt = "What is the capital of France? Answer in one sentence."
        results = []

        for i in range(iterations):
            success, response, usage, error, resp_time = self._make_request(
                provider, prompt, max_tokens=50
            )

            tokens = usage.get('total_tokens', 0) if usage else 0

            result = TestResult(
                provider=provider,
                test_name="latency",
                success=success,
                response_time=resp_time,
                tokens_used=tokens,
                error=error,
                response_quality=100 if success else 0,
                timestamp=datetime.now().isoformat()
            )
            results.append(result)
            self.results.append(result)

            status = "✓" if success else "✗"
            print(f"  [{i+1}/{iterations}] {status} {resp_time:.2f}s | {tokens} tokens | {error or 'OK'}")

            # Small delay to avoid rate limits
            time.sleep(0.5)

        return results

    def test_rate_limiting(self, provider: str, requests_per_second: int = 5) -> List[TestResult]:
        """Test rate limiting behavior."""
        print(f"\n{'='*60}")
        print(f"RATE LIMIT TEST: {provider.upper()} ({requests_per_second} req/s)")
        print(f"{'='*60}")

        prompt = "Count to 5."
        results = []

        # Send burst of requests
        for i in range(requests_per_second):
            success, response, usage, error, resp_time = self._make_request(
                provider, prompt, max_tokens=50
            )

            tokens = usage.get('total_tokens', 0) if usage else 0

            result = TestResult(
                provider=provider,
                test_name="rate_limit",
                success=success,
                response_time=resp_time,
                tokens_used=tokens,
                error=error,
                response_quality=100 if success else 0,
                timestamp=datetime.now().isoformat()
            )
            results.append(result)
            self.results.append(result)

            status = "✓" if success else "✗"
            print(f"  [{i+1}/{requests_per_second}] {status} {resp_time:.2f}s | {error or 'OK'}")

            # No delay - testing burst capacity

        return results

    def test_concurrent_requests(self, provider: str, concurrent: int = 5) -> List[TestResult]:
        """Test concurrent request handling."""
        print(f"\n{'='*60}")
        print(f"CONCURRENT TEST: {provider.upper()} ({concurrent} parallel)")
        print(f"{'='*60}")

        prompts = [
            "What is AI?",
            "Explain machine learning.",
            "What is a neural network?",
            "Define deep learning.",
            "What is natural language processing?"
        ][:concurrent]

        results = []

        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = {
                executor.submit(self._make_request, provider, prompt, max_tokens=100): i
                for i, prompt in enumerate(prompts)
            }

            for future in as_completed(futures):
                i = futures[future]
                success, response, usage, error, resp_time = future.result()

                tokens = usage.get('total_tokens', 0) if usage else 0

                result = TestResult(
                    provider=provider,
                    test_name="concurrent",
                    success=success,
                    response_time=resp_time,
                    tokens_used=tokens,
                    error=error,
                    response_quality=100 if success else 0,
                    timestamp=datetime.now().isoformat()
                )
                results.append(result)
                self.results.append(result)

                status = "✓" if success else "✗"
                print(f"  [{i+1}/{concurrent}] {status} {resp_time:.2f}s | {tokens} tokens")

        return results

    def test_complex_task(self, provider: str, task: str = "market_analysis") -> TestResult:
        """Test complex task quality."""
        print(f"\n{'='*60}")
        print(f"COMPLEX TASK TEST: {provider.upper()} - {task}")
        print(f"{'='*60}")

        prompts = {
            "market_analysis": """Analyze the current AI chip market. Include:
1. Top 3 companies by market share
2. Key trends driving growth
3. Major risks to watch
Keep it under 200 words.""",

            "sentiment": """Analyze sentiment of this text:
'NVDA crushes earnings, guides up 25% next quarter. Supply still tight, demand accelerating.'
Respond with: BULLISH, BEARISH, or NEUTRAL and 1-sentence reasoning.""",

            "pattern": """Identify the trading pattern:
Day 1: +5%, high volume
Day 2: +3%, high volume
Day 3: +1%, declining volume
Day 4: -2%, low volume
Day 5: -1%, low volume

Pattern name and implication in 2 sentences.""",

            "ecosystem": """What companies are in NVIDIA's supply chain ecosystem?
List 5 key suppliers and their role in one sentence each."""
        }

        prompt = prompts.get(task, prompts["market_analysis"])

        success, response, usage, error, resp_time = self._make_request(
            provider, prompt, max_tokens=500
        )

        tokens = usage.get('total_tokens', 0) if usage else 0

        # Quality scoring (basic heuristic)
        quality = 0
        if success and response:
            # Check response length
            if len(response) > 50:
                quality += 30
            # Check if structured
            if any(c in response for c in ['1.', '2.', '-', '•']):
                quality += 20
            # Check if specific companies mentioned
            if any(name in response.upper() for name in ['NVDA', 'NVIDIA', 'AMD', 'INTEL', 'TSMC']):
                quality += 25
            # Check if reasoning provided
            if len(response.split('.')) >= 3:
                quality += 25

        result = TestResult(
            provider=provider,
            test_name=f"complex_{task}",
            success=success,
            response_time=resp_time,
            tokens_used=tokens,
            error=error,
            response_quality=quality,
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)

        status = "✓" if success else "✗"
        print(f"  {status} {resp_time:.2f}s | {tokens} tokens | Quality: {quality}/100")
        if success and response:
            print(f"\n  Response Preview:")
            print(f"  {response[:300]}...")

        return result

    def test_error_recovery(self, provider: str) -> List[TestResult]:
        """Test error handling with invalid inputs."""
        print(f"\n{'='*60}")
        print(f"ERROR RECOVERY TEST: {provider.upper()}")
        print(f"{'='*60}")

        test_cases = [
            ("Empty prompt", ""),
            ("Very long prompt", "AI " * 5000),  # ~10K tokens
            ("Special characters", "!@#$%^&*()_+ {} [] | \\ / ? < >"),
        ]

        results = []

        for name, prompt in test_cases:
            success, response, usage, error, resp_time = self._make_request(
                provider, prompt, max_tokens=50
            )

            tokens = usage.get('total_tokens', 0) if usage else 0

            result = TestResult(
                provider=provider,
                test_name=f"error_{name.lower().replace(' ', '_')}",
                success=success,
                response_time=resp_time,
                tokens_used=tokens,
                error=error,
                response_quality=0,  # Error tests don't measure quality
                timestamp=datetime.now().isoformat()
            )
            results.append(result)
            self.results.append(result)

            status = "✓" if success else "✗"
            print(f"  {name}: {status} {resp_time:.2f}s | {error or 'Handled gracefully'}")

            time.sleep(0.5)

        return results

    def calculate_summary(self, provider: str) -> StressTestSummary:
        """Calculate aggregate statistics for a provider."""
        provider_results = [r for r in self.results if r.provider == provider]

        if not provider_results:
            return StressTestSummary(
                provider=provider,
                total_tests=0,
                successful=0,
                failed=0,
                success_rate=0.0,
                avg_response_time=0.0,
                median_response_time=0.0,
                p95_response_time=0.0,
                total_tokens=0,
                avg_tokens_per_request=0.0,
                total_cost=0.0,
                errors={}
            )

        successful = [r for r in provider_results if r.success]
        failed = [r for r in provider_results if not r.success]

        response_times = [r.response_time for r in provider_results]
        tokens = [r.tokens_used for r in provider_results if r.tokens_used]

        # Calculate costs (rough estimate)
        total_tokens = sum(tokens)
        # Assume 50/50 split input/output for simplicity
        input_tokens = total_tokens * 0.5
        output_tokens = total_tokens * 0.5
        total_cost = (
            (input_tokens / 1_000_000 * self.costs[provider]['input']) +
            (output_tokens / 1_000_000 * self.costs[provider]['output'])
        )

        # Error breakdown
        errors = {}
        for r in failed:
            error_type = r.error.split(':')[0] if r.error else 'Unknown'
            errors[error_type] = errors.get(error_type, 0) + 1

        return StressTestSummary(
            provider=provider,
            total_tests=len(provider_results),
            successful=len(successful),
            failed=len(failed),
            success_rate=len(successful) / len(provider_results) * 100,
            avg_response_time=statistics.mean(response_times),
            median_response_time=statistics.median(response_times),
            p95_response_time=statistics.quantiles(response_times, n=20)[18] if len(response_times) > 10 else max(response_times),
            total_tokens=total_tokens,
            avg_tokens_per_request=statistics.mean(tokens) if tokens else 0,
            total_cost=total_cost,
            errors=errors
        )

    def print_comparison(self):
        """Print side-by-side comparison."""
        print(f"\n{'='*80}")
        print(f"{'A/B COMPARISON SUMMARY':^80}")
        print(f"{'='*80}\n")

        xai_summary = self.calculate_summary('xai')
        deepseek_summary = self.calculate_summary('deepseek')

        # Comparison table
        print(f"{'Metric':<30} {'xAI':>20} {'DeepSeek':>20}")
        print(f"{'-'*30} {'-'*20} {'-'*20}")

        print(f"{'Total Tests':<30} {xai_summary.total_tests:>20} {deepseek_summary.total_tests:>20}")
        print(f"{'Successful':<30} {xai_summary.successful:>20} {deepseek_summary.successful:>20}")
        print(f"{'Failed':<30} {xai_summary.failed:>20} {deepseek_summary.failed:>20}")
        print(f"{'Success Rate':<30} {xai_summary.success_rate:>19.1f}% {deepseek_summary.success_rate:>19.1f}%")
        print()

        print(f"{'Avg Response Time':<30} {xai_summary.avg_response_time:>18.2f}s {deepseek_summary.avg_response_time:>18.2f}s")
        print(f"{'Median Response Time':<30} {xai_summary.median_response_time:>18.2f}s {deepseek_summary.median_response_time:>18.2f}s")
        print(f"{'P95 Response Time':<30} {xai_summary.p95_response_time:>18.2f}s {deepseek_summary.p95_response_time:>18.2f}s")
        print()

        print(f"{'Total Tokens Used':<30} {xai_summary.total_tokens:>20,} {deepseek_summary.total_tokens:>20,}")
        print(f"{'Avg Tokens/Request':<30} {xai_summary.avg_tokens_per_request:>19.1f} {deepseek_summary.avg_tokens_per_request:>19.1f}")
        print()

        print(f"{'Estimated Cost':<30} ${xai_summary.total_cost:>18.4f} ${deepseek_summary.total_cost:>18.4f}")
        xai_avg_cost = (self.costs['xai']['input'] + self.costs['xai']['output']) / 2
        deepseek_avg_cost = (self.costs['deepseek']['input'] + self.costs['deepseek']['output']) / 2
        print(f"{'Cost per 1M tokens (avg)':<30} ${xai_avg_cost:>18.2f} ${deepseek_avg_cost:>18.2f}")
        print()

        # Winner determination
        print(f"\n{'WINNER ANALYSIS':^80}")
        print(f"{'='*80}\n")

        # Speed
        if xai_summary.avg_response_time < deepseek_summary.avg_response_time:
            speed_winner = "xAI"
            speed_diff = ((deepseek_summary.avg_response_time / xai_summary.avg_response_time) - 1) * 100
        else:
            speed_winner = "DeepSeek"
            speed_diff = ((xai_summary.avg_response_time / deepseek_summary.avg_response_time) - 1) * 100

        print(f"⚡ SPEED: {speed_winner} is {speed_diff:.1f}% faster")

        # Reliability
        if xai_summary.success_rate > deepseek_summary.success_rate:
            reliability_winner = "xAI"
            reliability_diff = xai_summary.success_rate - deepseek_summary.success_rate
        else:
            reliability_winner = "DeepSeek"
            reliability_diff = deepseek_summary.success_rate - xai_summary.success_rate

        print(f"✓ RELIABILITY: {reliability_winner} is {reliability_diff:.1f}% more reliable")

        # Cost
        if xai_summary.total_cost < deepseek_summary.total_cost:
            cost_winner = "xAI"
            cost_diff = ((deepseek_summary.total_cost / xai_summary.total_cost) - 1) * 100 if xai_summary.total_cost > 0 else 0
        else:
            cost_winner = "DeepSeek"
            cost_diff = ((xai_summary.total_cost / deepseek_summary.total_cost) - 1) * 100 if deepseek_summary.total_cost > 0 else 0

        print(f"💰 COST: {cost_winner} is {cost_diff:.1f}% cheaper")

        # Overall recommendation
        print(f"\n{'RECOMMENDATION':^80}")
        print(f"{'='*80}\n")

        # Calculate weighted score (reliability 40%, speed 30%, cost 30%)
        xai_score = (
            xai_summary.success_rate * 0.4 +
            (100 - (xai_summary.avg_response_time / max(xai_summary.avg_response_time, deepseek_summary.avg_response_time) * 100)) * 0.3 +
            (100 - (xai_summary.total_cost / max(xai_summary.total_cost, deepseek_summary.total_cost) * 100)) * 0.3 if xai_summary.total_cost > 0 else 0
        )

        deepseek_score = (
            deepseek_summary.success_rate * 0.4 +
            (100 - (deepseek_summary.avg_response_time / max(xai_summary.avg_response_time, deepseek_summary.avg_response_time) * 100)) * 0.3 +
            (100 - (deepseek_summary.total_cost / max(xai_summary.total_cost, deepseek_summary.total_cost) * 100)) * 0.3 if deepseek_summary.total_cost > 0 else 0
        )

        if xai_score > deepseek_score:
            print(f"🏆 OVERALL WINNER: xAI (Score: {xai_score:.1f}/100)")
            print(f"\nUse xAI when: You need fastest response times and reliability")
            print(f"Use DeepSeek when: Cost optimization is priority")
        else:
            print(f"🏆 OVERALL WINNER: DeepSeek (Score: {deepseek_score:.1f}/100)")
            print(f"\nUse DeepSeek when: Cost optimization is priority and speed is acceptable")
            print(f"Use xAI when: You need fastest response times")

    def save_results(self, filename: str = "ai_stress_test_results.json"):
        """Save detailed results to JSON."""
        output = {
            "test_date": datetime.now().isoformat(),
            "xai_summary": asdict(self.calculate_summary('xai')),
            "deepseek_summary": asdict(self.calculate_summary('deepseek')),
            "detailed_results": [asdict(r) for r in self.results]
        }

        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n📊 Detailed results saved to: {filename}")

    def run_full_suite(self):
        """Run complete test suite for both providers."""
        print(f"\n{'#'*80}")
        print(f"{'AI STRESS TEST & A/B COMPARISON':^80}")
        print(f"{'xAI vs DeepSeek':^80}")
        print(f"{'#'*80}\n")

        providers = []
        if self.xai_available:
            providers.append('xai')
        if self.deepseek_available:
            providers.append('deepseek')

        if not providers:
            print("❌ No API keys configured. Set XAI_API_KEY and/or DEEPSEEK_API_KEY")
            return

        for provider in providers:
            print(f"\n\n{'█'*80}")
            print(f"{'TESTING: ' + provider.upper():^80}")
            print(f"{'█'*80}")

            # Run test suite
            self.test_latency(provider, iterations=10)
            time.sleep(2)

            self.test_rate_limiting(provider, requests_per_second=5)
            time.sleep(2)

            self.test_concurrent_requests(provider, concurrent=3)
            time.sleep(2)

            # Complex tasks
            for task in ["market_analysis", "sentiment", "pattern", "ecosystem"]:
                self.test_complex_task(provider, task)
                time.sleep(1)

            self.test_error_recovery(provider)
            time.sleep(2)

        # Print comparison
        if len(providers) == 2:
            self.print_comparison()
        else:
            # Single provider summary
            summary = self.calculate_summary(providers[0])
            print(f"\n{'='*80}")
            print(f"SUMMARY: {providers[0].upper()}")
            print(f"{'='*80}\n")
            print(f"Total Tests: {summary.total_tests}")
            print(f"Success Rate: {summary.success_rate:.1f}%")
            print(f"Avg Response Time: {summary.avg_response_time:.2f}s")
            print(f"Total Tokens: {summary.total_tokens:,}")
            print(f"Estimated Cost: ${summary.total_cost:.4f}")

        # Save results
        self.save_results()


def main():
    """Main entry point."""
    tester = AIStressTester()
    tester.run_full_suite()


if __name__ == "__main__":
    main()
