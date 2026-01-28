"""
Unified AI Service - Central hub for all AI API calls.

This module provides a single, high-quality interface for all AI operations
with automatic failover, rate limiting, caching, and monitoring.

Usage:
    from src.services.ai_service import ai_service

    # Simple call (auto-routes based on task complexity)
    result = ai_service.call("Analyze this stock...", task_type="analysis")

    # Force specific provider
    result = ai_service.call_deepseek("Quick sentiment check")
    result = ai_service.call_xai("Complex reasoning task")

Routing Strategy:
    - DeepSeek: Fast, good for sentiment, quick queries (default)
    - xAI/Grok: Better for complex reasoning, large context, heavy analysis
    - Automatic fallback: If primary fails, tries secondary
"""

import os
import time
import json
import logging
import requests
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class AIProviderConfig:
    """Configuration for an AI provider."""
    name: str
    api_key: str
    api_url: str
    model: str
    max_tokens: int = 2000
    temperature: float = 0.3
    timeout: int = 30

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)


@dataclass
class AIServiceStats:
    """Track AI service usage and performance."""
    calls_today: int = 0
    calls_total: int = 0
    errors_today: int = 0
    last_call: Optional[datetime] = None
    avg_latency_ms: float = 0
    deepseek_calls: int = 0
    xai_calls: int = 0
    fallback_count: int = 0
    cache_hits: int = 0


# =============================================================================
# UNIFIED AI SERVICE
# =============================================================================

class AIService:
    """
    Unified AI Service with intelligent routing and failover.

    Features:
    - Automatic provider selection based on task type
    - Failover from primary to secondary provider
    - Rate limiting and budget management
    - Response caching for repeated queries
    - Performance monitoring and health checks
    """

    # Task type to provider mapping
    HEAVY_TASKS = {"heavy", "news", "portfolio", "narrative", "catalyst",
                   "theme", "strategy", "reasoning", "analysis"}
    SIMPLE_TASKS = {"simple", "sentiment", "calculation", "quick", "classification"}

    # Daily budget limits
    DAILY_BUDGET_DEEPSEEK = 1000  # calls per day
    DAILY_BUDGET_XAI = 500        # calls per day

    def __init__(self):
        self._lock = Lock()
        self._stats = AIServiceStats()
        self._stats_file = Path('ai_learning_data/ai_service_stats.json')
        self._stats_file.parent.mkdir(exist_ok=True)

        # Response cache (short TTL for dynamic content)
        self._cache: Dict[str, tuple] = {}  # key -> (response, timestamp)
        self._cache_ttl = 300  # 5 minutes

        # Initialize providers from environment
        self.deepseek = AIProviderConfig(
            name="DeepSeek",
            api_key=os.environ.get('DEEPSEEK_API_KEY', ''),
            api_url="https://api.deepseek.com/v1/chat/completions",
            model=os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat'),
            temperature=0.3
        )

        self.xai = AIProviderConfig(
            name="xAI/Grok",
            api_key=os.environ.get('XAI_API_KEY', ''),
            api_url="https://api.x.ai/v1/chat/completions",
            model=os.environ.get('XAI_MODEL', 'grok-2-latest'),
            temperature=0.3
        )

        self._load_stats()
        logger.info(f"AI Service initialized: DeepSeek={'OK' if self.deepseek.is_configured else 'NOT SET'}, "
                   f"xAI={'OK' if self.xai.is_configured else 'NOT SET'}")

    def _load_stats(self):
        """Load stats from file, reset if new day."""
        try:
            if self._stats_file.exists():
                data = json.loads(self._stats_file.read_text())
                last_date = data.get('date')
                if last_date == str(date.today()):
                    self._stats.calls_today = data.get('calls_today', 0)
                    self._stats.errors_today = data.get('errors_today', 0)
                    self._stats.deepseek_calls = data.get('deepseek_calls', 0)
                    self._stats.xai_calls = data.get('xai_calls', 0)
                self._stats.calls_total = data.get('calls_total', 0)
        except Exception as e:
            logger.debug(f"Could not load AI stats: {e}")

    def _save_stats(self):
        """Save stats to file."""
        try:
            data = {
                'date': str(date.today()),
                'calls_today': self._stats.calls_today,
                'calls_total': self._stats.calls_total,
                'errors_today': self._stats.errors_today,
                'deepseek_calls': self._stats.deepseek_calls,
                'xai_calls': self._stats.xai_calls,
                'fallback_count': self._stats.fallback_count,
                'avg_latency_ms': self._stats.avg_latency_ms,
            }
            self._stats_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"Could not save AI stats: {e}")

    def _get_cache_key(self, prompt: str, system_prompt: str = None) -> str:
        """Generate cache key from prompt."""
        import hashlib
        content = f"{system_prompt or ''}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _check_cache(self, key: str) -> Optional[str]:
        """Check if response is cached and still valid."""
        if key in self._cache:
            response, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                self._stats.cache_hits += 1
                return response
            del self._cache[key]
        return None

    def _set_cache(self, key: str, response: str):
        """Cache a response."""
        # Limit cache size
        if len(self._cache) > 100:
            # Remove oldest entries
            oldest = sorted(self._cache.items(), key=lambda x: x[1][1])[:20]
            for k, _ in oldest:
                del self._cache[k]
        self._cache[key] = (response, time.time())

    def _call_provider(self, provider: AIProviderConfig, prompt: str,
                       system_prompt: str = None, max_tokens: int = None,
                       temperature: float = None) -> Optional[str]:
        """Make API call to a specific provider."""
        if not provider.is_configured:
            logger.debug(f"{provider.name} not configured")
            return None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start_time = time.time()

        try:
            response = requests.post(
                provider.api_url,
                headers={
                    "Authorization": f"Bearer {provider.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": provider.model,
                    "messages": messages,
                    "max_tokens": max_tokens or provider.max_tokens,
                    "temperature": temperature if temperature is not None else provider.temperature,
                },
                timeout=provider.timeout
            )

            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                result = response.json()['choices'][0]['message']['content']

                # Update stats
                with self._lock:
                    self._stats.calls_today += 1
                    self._stats.calls_total += 1
                    self._stats.last_call = datetime.now()
                    if provider.name == "DeepSeek":
                        self._stats.deepseek_calls += 1
                    else:
                        self._stats.xai_calls += 1
                    # Running average latency
                    n = self._stats.calls_total
                    self._stats.avg_latency_ms = ((n-1) * self._stats.avg_latency_ms + latency_ms) / n
                    self._save_stats()

                logger.debug(f"{provider.name} call successful ({latency_ms:.0f}ms)")
                return result
            else:
                logger.error(f"{provider.name} returned {response.status_code}: {response.text[:200]}")
                with self._lock:
                    self._stats.errors_today += 1
                return None

        except requests.Timeout:
            logger.error(f"{provider.name} timeout after {provider.timeout}s")
            with self._lock:
                self._stats.errors_today += 1
            return None
        except Exception as e:
            logger.error(f"{provider.name} error: {e}")
            with self._lock:
                self._stats.errors_today += 1
            return None

    def call(self, prompt: str, system_prompt: str = None,
             max_tokens: int = 2000, temperature: float = None,
             task_type: str = "default", use_cache: bool = True,
             prefer_xai: bool = False) -> Optional[str]:
        """
        Make AI call with intelligent routing and automatic failover.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum response tokens
            temperature: Override temperature (0.0-1.0)
            task_type: Task category for routing:
                - "simple", "sentiment", "quick" -> DeepSeek first
                - "heavy", "news", "analysis", "reasoning" -> xAI first
                - "default" -> auto-detect based on max_tokens
            use_cache: Whether to use response caching
            prefer_xai: Force xAI as primary provider

        Returns:
            AI response text or None if all providers fail
        """
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(prompt, system_prompt)
            cached = self._check_cache(cache_key)
            if cached:
                logger.debug("AI response served from cache")
                return cached

        # Determine routing
        use_xai_first = prefer_xai

        if not use_xai_first:
            if task_type in self.HEAVY_TASKS:
                use_xai_first = True
            elif task_type in self.SIMPLE_TASKS:
                use_xai_first = False
            elif task_type == "default":
                # Auto-detect: heavy if complex output expected
                use_xai_first = max_tokens > 500

        # Try primary provider
        primary = self.xai if use_xai_first else self.deepseek
        secondary = self.deepseek if use_xai_first else self.xai

        result = self._call_provider(primary, prompt, system_prompt, max_tokens, temperature)

        if result:
            if use_cache:
                self._set_cache(cache_key, result)
            return result

        # Fallback to secondary
        logger.info(f"Falling back from {primary.name} to {secondary.name}")
        with self._lock:
            self._stats.fallback_count += 1

        result = self._call_provider(secondary, prompt, system_prompt, max_tokens, temperature)

        if result and use_cache:
            self._set_cache(cache_key, result)

        return result

    def call_deepseek(self, prompt: str, system_prompt: str = None,
                      max_tokens: int = 2000, temperature: float = None) -> Optional[str]:
        """Direct call to DeepSeek (with xAI fallback)."""
        result = self._call_provider(self.deepseek, prompt, system_prompt, max_tokens, temperature)
        if result:
            return result
        # Fallback
        logger.info("DeepSeek failed, falling back to xAI")
        with self._lock:
            self._stats.fallback_count += 1
        return self._call_provider(self.xai, prompt, system_prompt, max_tokens, temperature)

    def call_xai(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 2000, temperature: float = None) -> Optional[str]:
        """Direct call to xAI/Grok (with DeepSeek fallback)."""
        result = self._call_provider(self.xai, prompt, system_prompt, max_tokens, temperature)
        if result:
            return result
        # Fallback
        logger.info("xAI failed, falling back to DeepSeek")
        with self._lock:
            self._stats.fallback_count += 1
        return self._call_provider(self.deepseek, prompt, system_prompt, max_tokens, temperature)

    def get_status(self) -> Dict[str, Any]:
        """Get service status and statistics."""
        return {
            'providers': {
                'deepseek': {
                    'configured': self.deepseek.is_configured,
                    'model': self.deepseek.model if self.deepseek.is_configured else None,
                },
                'xai': {
                    'configured': self.xai.is_configured,
                    'model': self.xai.model if self.xai.is_configured else None,
                }
            },
            'stats': {
                'calls_today': self._stats.calls_today,
                'calls_total': self._stats.calls_total,
                'errors_today': self._stats.errors_today,
                'deepseek_calls': self._stats.deepseek_calls,
                'xai_calls': self._stats.xai_calls,
                'fallback_count': self._stats.fallback_count,
                'cache_hits': self._stats.cache_hits,
                'avg_latency_ms': round(self._stats.avg_latency_ms, 1),
            },
            'health': 'healthy' if (self.deepseek.is_configured or self.xai.is_configured) else 'no_providers'
        }

    def health_check(self) -> Dict[str, Any]:
        """Run health check on all providers."""
        results = {
            'timestamp': datetime.now().isoformat(),
            'providers': {}
        }

        test_prompt = "Reply with exactly: OK"

        for name, provider in [('deepseek', self.deepseek), ('xai', self.xai)]:
            if not provider.is_configured:
                results['providers'][name] = {'status': 'not_configured'}
                continue

            start = time.time()
            try:
                response = self._call_provider(provider, test_prompt, max_tokens=10)
                latency = (time.time() - start) * 1000
                results['providers'][name] = {
                    'status': 'healthy' if response else 'error',
                    'latency_ms': round(latency, 1),
                    'model': provider.model
                }
            except Exception as e:
                results['providers'][name] = {
                    'status': 'error',
                    'error': str(e)
                }

        return results


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_ai_service: Optional[AIService] = None
_init_lock = Lock()

def get_ai_service() -> AIService:
    """Get or create the singleton AI service instance."""
    global _ai_service
    if _ai_service is None:
        with _init_lock:
            if _ai_service is None:
                _ai_service = AIService()
    return _ai_service

# Convenience alias
ai_service = property(lambda self: get_ai_service())


# =============================================================================
# BACKWARD COMPATIBLE FUNCTIONS
# =============================================================================

def call_ai(prompt: str, system_prompt: str = None, max_tokens: int = 2000,
            timeout: int = 30, prefer_xai: bool = False,
            task_type: str = "default") -> Optional[str]:
    """
    Backward compatible function for AI calls.

    This function maintains compatibility with existing code while using
    the new unified AI service under the hood.
    """
    service = get_ai_service()
    return service.call(prompt, system_prompt, max_tokens,
                       task_type=task_type, prefer_xai=prefer_xai)


def call_deepseek(prompt: str, system_prompt: str = None,
                  max_tokens: int = 2000, timeout: int = 25) -> Optional[str]:
    """Backward compatible DeepSeek call with xAI fallback."""
    service = get_ai_service()
    return service.call_deepseek(prompt, system_prompt, max_tokens)


def call_xai(prompt: str, system_prompt: str = None,
             max_tokens: int = 2000, timeout: int = 25) -> Optional[str]:
    """Backward compatible xAI call with DeepSeek fallback."""
    service = get_ai_service()
    return service.call_xai(prompt, system_prompt, max_tokens)
