#!/usr/bin/env python3
"""
Modal API v2 - Single ASGI endpoint with FastAPI routing

Solves:
- Modal free plan 8 endpoint limit
- FastAPI import issues during deployment

All 40+ routes served via ONE Modal endpoint.
"""

import modal
from datetime import datetime
from pathlib import Path
import json

# =============================================================================
# MODAL SETUP
# =============================================================================

app = modal.App("stock-scanner-api-v2")

volume = modal.Volume.from_name("scan-results", create_if_missing=True)
VOLUME_PATH = "/data"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .pip_install("fastapi[standard]")
    .add_local_dir("src", remote_path="/root/src")
    .add_local_dir("config", remote_path="/root/config")
    .add_local_dir("utils", remote_path="/root/utils")
    .add_local_dir("static", remote_path="/root/static")
)


# =============================================================================
# MODAL ASGI APP
# =============================================================================

@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("Stock_Story")],
    min_containers=1,
    timeout=600
)
@modal.asgi_app()
def create_fastapi_app():
    """
    Create FastAPI app inside Modal function.
    All imports happen here (in container where packages are available).
    """
    # Imports only available in container
    from fastapi import FastAPI, Query, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
    import sys
    sys.path.insert(0, '/root')

    # Create FastAPI app with comprehensive documentation
    web_app = FastAPI(
        title="Stock Scanner API",
        version="2.0.0",
        description="""
# Stock Scanner API

A comprehensive stock analysis API featuring story-first scoring, theme intelligence,
and institutional-grade data sources.

## Features

* **Story-First Scoring** - Find stocks with compelling narratives before the crowd
* **Theme Intelligence** - Track emerging themes and sector momentum
* **Multi-Source Data** - Polygon, DeepSeek, StockTwits, Reddit, SEC Edgar
* **Self-Learning System** - 124 parameters that evolve based on outcomes
* **Real-Time Monitoring** - Social sentiment, news momentum, unusual activity
* **API Authentication** - Secure access with rate limiting
* **Performance Optimized** - Response compression, cache preloading, parallel fetching

## Authentication

Most endpoints require an API key. Include in requests as:

```
Authorization: Bearer <your-api-key>
```

Get an API key at `/api-keys/request`

## Rate Limits

* **Free tier:** 1,000 requests/day
* **Pro tier:** 10,000 requests/day
* **Enterprise tier:** 100,000 requests/day

## Support

* **Documentation:** https://github.com/yourusername/stock_scanner_bot
* **Issues:** https://github.com/yourusername/stock_scanner_bot/issues
        """,
        contact={
            "name": "Stock Scanner API Support",
            "email": "support@example.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        openapi_tags=[
            {
                "name": "Core",
                "description": "Core API endpoints for health checks and scan results"
            },
            {
                "name": "Admin",
                "description": "Administrative endpoints for monitoring and metrics"
            },
            {
                "name": "API Keys",
                "description": "API key management and usage tracking"
            },
            {
                "name": "Scanning",
                "description": "Stock scanning and analysis endpoints"
            },
            {
                "name": "Conviction",
                "description": "High-conviction trade setups and alerts"
            },
            {
                "name": "Intelligence",
                "description": "Theme intelligence and market insights"
            },
            {
                "name": "Learning",
                "description": "Self-learning system parameters and evolution"
            },
        ]
    )

    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger("api")

    # Add CORS (restricted to known origins)
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://zhuanleee.github.io",
            "http://localhost:5000",
            "http://127.0.0.1:5000"
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"]
    )

    # Add GZip compression for responses
    from fastapi.middleware.gzip import GZipMiddleware
    web_app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Add security headers middleware
    @web_app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.socket.io; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://zhuanleee--stock-scanner-api-v2-create-fastapi-app.modal.run wss://zhuanleee--stock-scanner-api-v2-create-fastapi-app.modal.run"
        return response

    # Global metrics for monitoring
    from collections import defaultdict
    import time as time_module

    class APIMetrics:
        def __init__(self):
            self.total_requests = 0
            self.total_errors = 0
            self.status_codes = defaultdict(int)
            self.endpoint_calls = defaultdict(int)
            self.endpoint_errors = defaultdict(int)
            self.latencies = []
            self.error_log = []  # Store recent errors
            self.start_time = time_module.time()

        def record_request(self, path: str, status_code: int, duration: float):
            self.total_requests += 1
            self.status_codes[status_code] += 1
            self.endpoint_calls[path] += 1
            self.latencies.append(duration)

            # Keep only last 1000 latencies
            if len(self.latencies) > 1000:
                self.latencies = self.latencies[-1000:]

            # Track errors (4xx and 5xx)
            if status_code >= 400:
                self.total_errors += 1
                self.endpoint_errors[path] += 1

        def record_error(self, path: str, error: str):
            self.error_log.append({
                'path': path,
                'error': error,
                'timestamp': datetime.now().isoformat()
            })
            # Keep only last 100 errors
            if len(self.error_log) > 100:
                self.error_log = self.error_log[-100:]

        def get_stats(self):
            uptime = time_module.time() - self.start_time
            latencies = sorted(self.latencies) if self.latencies else [0]

            return {
                'uptime_seconds': round(uptime, 2),
                'total_requests': self.total_requests,
                'total_errors': self.total_errors,
                'error_rate': round(self.total_errors / max(self.total_requests, 1) * 100, 2),
                'status_codes': dict(self.status_codes),
                'top_endpoints': dict(sorted(self.endpoint_calls.items(), key=lambda x: x[1], reverse=True)[:10]),
                'error_endpoints': dict(sorted(self.endpoint_errors.items(), key=lambda x: x[1], reverse=True)[:10]),
                'latency_p50': round(latencies[len(latencies) // 2] * 1000, 2),
                'latency_p95': round(latencies[int(len(latencies) * 0.95)] * 1000, 2),
                'latency_p99': round(latencies[int(len(latencies) * 0.99)] * 1000, 2),
                'recent_errors': self.error_log[-10:]  # Last 10 errors
            }

    api_metrics = APIMetrics()

    # Add request logging and metrics middleware
    @web_app.middleware("http")
    async def log_requests(request, call_next):
        import time
        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Record metrics
            api_metrics.record_request(request.url.path, response.status_code, process_time)

            # Log request details
            import logging
            logger = logging.getLogger("api")

            # Log level based on status code
            if response.status_code >= 500:
                logger.error(
                    f"{request.method} {request.url.path} "
                    f"status={response.status_code} "
                    f"duration={process_time:.3f}s "
                    f"client={request.client.host if request.client else 'unknown'}"
                )
            elif response.status_code >= 400:
                logger.warning(
                    f"{request.method} {request.url.path} "
                    f"status={response.status_code} "
                    f"duration={process_time:.3f}s "
                    f"client={request.client.host if request.client else 'unknown'}"
                )
            else:
                logger.info(
                    f"{request.method} {request.url.path} "
                    f"status={response.status_code} "
                    f"duration={process_time:.3f}s "
                    f"client={request.client.host if request.client else 'unknown'}"
                )

            return response

        except Exception as e:
            process_time = time.time() - start_time

            # Record error metrics
            api_metrics.record_request(request.url.path, 500, process_time)
            api_metrics.record_error(request.url.path, str(e))

            # Log error
            import logging
            logger = logging.getLogger("api")
            logger.exception(
                f"Unhandled exception in {request.method} {request.url.path}: {e}"
            )

            # Re-raise to let FastAPI handle it
            raise

    # Startup optimization: preload hot data into cache
    @web_app.on_event("startup")
    async def startup():
        """Preload frequently accessed data on container startup"""
        try:
            from src.core.performance import optimize_startup
            await optimize_startup()
        except Exception as e:
            import logging
            logger = logging.getLogger("api")
            logger.warning(f"Startup optimization failed: {e}")

    # =============================================================================
    # AUTHENTICATION SETUP
    # =============================================================================

    # Initialize auth components
    from src.core.auth import APIKeyManager, RateLimiter, extract_api_key, validate_request
    import os

    api_key_manager = APIKeyManager(keys_file=f"{VOLUME_PATH}/api_keys.json")
    rate_limiter = RateLimiter(requests_per_second=10.0)

    # Grace period: Allow requests without API keys until this date
    # Set REQUIRE_API_KEYS=true environment variable to enforce authentication
    REQUIRE_API_KEYS = os.environ.get('REQUIRE_API_KEYS', 'false').lower() == 'true'
    GRACE_PERIOD_DAYS = 7  # Days from first deployment

    # Public endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {
        '/',
        '/health',
        '/docs',
        '/openapi.json',
        '/redoc',
        '/api-keys/request',  # Allow users to request API keys
        '/api-keys/generate',  # Allow key generation during grace period
        '/admin/dashboard',  # Admin dashboard (consider adding auth later)
        '/admin/metrics',  # Metrics endpoint
        '/admin/performance',  # Performance endpoint
    }

    # Add authentication middleware
    @web_app.middleware("http")
    async def auth_middleware(request, call_next):
        """Authenticate requests using API keys"""
        # Skip auth for public endpoints
        if request.url.path in PUBLIC_ENDPOINTS:
            return await call_next(request)

        # Extract API key from header
        auth_header = request.headers.get('Authorization', '')
        api_key = extract_api_key(auth_header)

        if not api_key:
            # Grace period: Allow requests without API keys (with warning)
            if not REQUIRE_API_KEYS:
                logger.warning(
                    f"Request without API key from {request.client.host if request.client else 'unknown'} "
                    f"to {request.url.path} (grace period active)"
                )
                response = await call_next(request)
                response.headers['X-API-Warning'] = 'API keys will be required soon. Get yours at /api-keys/request'
                return response

            return JSONResponse(
                status_code=401,
                content={
                    "ok": False,
                    "error": "Missing API key",
                    "message": "Include 'Authorization: Bearer <your-api-key>' header",
                    "get_key": "/api-keys/request"
                }
            )

        # Validate request
        is_valid, error_msg, rate_info = validate_request(api_key, api_key_manager, rate_limiter)

        if not is_valid:
            status_code = 429 if "rate limit" in error_msg.lower() else 401
            content = {
                "ok": False,
                "error": "Authentication failed",
                "message": error_msg
            }
            if rate_info:
                content["rate_limit"] = rate_info

            return JSONResponse(status_code=status_code, content=content)

        # Add rate limit info to request state
        request.state.api_key = api_key
        request.state.rate_limit = rate_info

        # Continue with request
        response = await call_next(request)

        # Add rate limit headers
        if rate_info:
            response.headers['X-RateLimit-Remaining'] = str(rate_info['requests_remaining'])
            response.headers['X-RateLimit-Reset'] = rate_info['reset_at'].isoformat()

        return response

    # Helper to load scan results
    def load_scan_results():
        data_dir = Path(VOLUME_PATH)
        scan_files = sorted(data_dir.glob("scan_*.json"), reverse=True)
        if scan_files:
            try:
                with open(scan_files[0]) as f:
                    return json.load(f)
            except:
                pass
        return None

    # =============================================================================
    # ROUTES - CORE
    # =============================================================================

    @web_app.get("/", tags=["Core"])
    def root():
        """
        API Root

        Returns basic API information and version.
        """
        return {
            "ok": True,
            "service": "stock-scanner-api-v2",
            "version": "2.0.0",
            "documentation": "/docs",
            "dashboard": "/admin/dashboard"
        }

    @web_app.get("/health", tags=["Core"])
    def health():
        """
        Health Check

        Returns API health status and market health metrics.

        Returns:
        - status: System status (healthy/degraded)
        - market_health: Overall market health metrics
        - timestamp: Current server time
        """
        try:
            from src.analysis.market_health import get_market_health
            health_data = get_market_health()
            return {"ok": True, **health_data}
        except Exception as e:
            return {"ok": True, "status": "healthy", "service": "modal", "timestamp": datetime.now().isoformat()}

    @web_app.get("/admin/metrics", tags=["Admin"])
    def get_metrics():
        """
        View API metrics and performance statistics.

        Tracks:
        - Request counts and error rates
        - Latency percentiles (p50, p95, p99)
        - Top endpoints by traffic
        - Recent errors
        - Uptime

        Example: GET /admin/metrics
        """
        stats = api_metrics.get_stats()
        return {
            "ok": True,
            "timestamp": datetime.now().isoformat(),
            "metrics": stats
        }

    @web_app.get("/admin/performance", tags=["Admin"])
    def get_performance():
        """
        View performance monitor statistics from scoring functions.

        Shows detailed timing stats for all monitored operations.

        Example: GET /admin/performance
        """
        try:
            from src.core.performance import perf_monitor
            stats = perf_monitor.get_all_stats()
            return {
                "ok": True,
                "timestamp": datetime.now().isoformat(),
                "performance": stats
            }
        except ImportError:
            return {"ok": False, "error": "Performance monitoring not available"}

    @web_app.get("/admin/dashboard", response_class=HTMLResponse, tags=["Admin"])
    def admin_dashboard():
        """
        Admin dashboard with real-time metrics visualization.

        Shows:
        - System status and uptime
        - Request/error statistics
        - Latency percentiles
        - Status code distribution
        - Top endpoints by traffic
        - Recent errors
        - Function performance stats

        Example: GET /admin/dashboard
        """
        try:
            # Read dashboard HTML from static directory
            dashboard_path = Path(__file__).parent / "static" / "admin_dashboard.html"
            if dashboard_path.exists():
                with open(dashboard_path, 'r') as f:
                    return f.read()
            else:
                # Fallback: simple dashboard
                return """
                <html>
                <head><title>Admin Dashboard</title></head>
                <body style="font-family: sans-serif; padding: 40px; background: #0f172a; color: #e2e8f0;">
                    <h1>📊 Stock Scanner API Dashboard</h1>
                    <p>Dashboard HTML not found. View metrics at:</p>
                    <ul>
                        <li><a href="/admin/metrics" style="color: #6366f1;">API Metrics</a></li>
                        <li><a href="/admin/performance" style="color: #6366f1;">Performance Stats</a></li>
                    </ul>
                </body>
                </html>
                """
        except Exception as e:
            return f"<html><body><h1>Error loading dashboard</h1><p>{str(e)}</p></body></html>"

    # =============================================================================
    # ROUTES - API KEY MANAGEMENT
    # =============================================================================

    @web_app.post("/api-keys/generate", tags=["API Keys"])
    def generate_api_key(
        user_id: str = Query(..., description="Unique user identifier"),
        tier: str = Query("free", description="API tier: free, pro, enterprise"),
        email: str = Query(None, description="Contact email (optional)")
    ):
        """
        Generate a new API key.

        Tiers:
        - free: 1,000 requests/day
        - pro: 10,000 requests/day
        - enterprise: 100,000 requests/day

        Example: POST /api-keys/generate?user_id=user123&tier=free
        """
        # Determine rate limits based on tier
        rate_limits = {
            'free': 1000,
            'pro': 10000,
            'enterprise': 100000
        }

        requests_per_day = rate_limits.get(tier, 1000)

        try:
            api_key = api_key_manager.generate_key(
                user_id=user_id,
                tier=tier,
                requests_per_day=requests_per_day
            )

            return {
                "ok": True,
                "api_key": api_key,
                "tier": tier,
                "requests_per_day": requests_per_day,
                "created_at": datetime.now().isoformat(),
                "usage": "Include in request headers as: Authorization: Bearer <api_key>"
            }
        except Exception as e:
            return {"ok": False, "error": f"Failed to generate API key: {str(e)}"}

    @web_app.get("/api-keys/usage", tags=["API Keys"])
    def get_api_key_usage(request: Request):
        """
        Get usage statistics for the authenticated API key.

        Requires: Authorization header with API key

        Example: GET /api-keys/usage
        """
        api_key = getattr(request.state, 'api_key', None)
        if not api_key:
            return {"ok": False, "error": "No API key in request"}

        usage_stats = api_key_manager.get_usage_stats(api_key)
        if not usage_stats:
            return {"ok": False, "error": "API key not found"}

        return {
            "ok": True,
            "usage": usage_stats,
            "timestamp": datetime.now().isoformat()
        }

    @web_app.post("/api-keys/revoke", tags=["API Keys"])
    def revoke_api_key(api_key: str = Query(..., description="API key to revoke")):
        """
        Revoke an API key.

        Example: POST /api-keys/revoke?api_key=ssk_live_...
        """
        success = api_key_manager.revoke_key(api_key)

        if success:
            return {
                "ok": True,
                "message": "API key revoked successfully",
                "api_key": api_key[:15] + "..."  # Show only prefix
            }
        else:
            return {"ok": False, "error": "API key not found"}

    @web_app.get("/api-keys/request", tags=["API Keys"])
    def request_api_key():
        """
        Public endpoint: Instructions for requesting an API key.

        Example: GET /api-keys/request
        """
        return {
            "ok": True,
            "message": "API Key Request Instructions",
            "instructions": [
                "1. Email your request to: support@stockscanner.example.com",
                "2. Include: your name, email, intended use case",
                "3. You'll receive an API key within 24 hours",
                "4. Free tier: 1,000 requests/day",
                "5. Pro tier: 10,000 requests/day (contact for pricing)"
            ],
            "tiers": {
                "free": {"requests_per_day": 1000, "price": "$0"},
                "pro": {"requests_per_day": 10000, "price": "$49/month"},
                "enterprise": {"requests_per_day": 100000, "price": "Contact us"}
            },
            "usage": "Authorization: Bearer <your-api-key>"
        }

    @web_app.get("/scan", tags=["Scanning"])
    def scan():
        results = load_scan_results()
        if not results:
            return {"ok": False, "status": "no_data", "message": "No scan results available", "results": []}
        return results

    @web_app.post("/scan/trigger")
    def scan_trigger(mode: str = Query("quick")):
        """
        Trigger a manual scan.

        NOTE: Modal SDK doesn't allow calling functions across apps from within a function.
        This is a limitation of Modal's security model - functions can't spawn other app's functions.

        Manual trigger disabled. Use: modal run modal_scanner.py --daily
        Or wait for automatic cron schedule (daily at 6 AM PST).
        """
        return {
            "ok": False,
            "error": "Modal security restriction",
            "message": "Manual scan trigger not available from API due to Modal SDK limitations.",
            "workaround": "Scanner runs automatically daily at 6 AM PST, or use: modal run modal_scanner.py --daily",
            "info": "Modal doesn't allow cross-app function calls from within functions for security reasons."
        }

    @web_app.get("/ticker/{ticker_symbol}")
    def ticker(ticker_symbol: str):
        results = load_scan_results()
        if results:
            ticker_upper = ticker_symbol.upper()
            for stock in results.get('results', []):
                if stock.get('ticker', '').upper() == ticker_upper:
                    return {"ok": True, "data": stock}
        return {"ok": False, "error": "Ticker not found"}

    # =============================================================================
    # ROUTES - THEMES & INTELLIGENCE
    # =============================================================================

    @web_app.get("/themes/list")
    def themes_list():
        try:
            # Extract themes from scan results
            results = load_scan_results()
            if not results or not results.get('results'):
                return {"ok": False, "data": []}

            # Count stocks per theme
            theme_counts = {}
            for stock in results['results']:
                theme = stock.get('hottest_theme', 'No Theme')
                if theme and theme != 'No Theme':
                    theme_counts[theme] = theme_counts.get(theme, 0) + 1

            # Format as list
            themes = [
                {"name": theme, "count": count, "active": True}
                for theme, count in sorted(theme_counts.items(), key=lambda x: -x[1])
            ]

            return {"ok": True, "data": themes}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/theme-intel/radar")
    def theme_radar():
        try:
            # Extract theme radar from scan results
            results = load_scan_results()
            if not results or not results.get('results'):
                return {"ok": True, "data": []}

            # Aggregate theme data
            theme_data = {}
            for stock in results['results']:
                theme = stock.get('hottest_theme', 'No Theme')
                if theme and theme != 'No Theme':
                    if theme not in theme_data:
                        theme_data[theme] = {
                            "theme": theme,
                            "stocks": [],
                            "avg_score": 0,
                            "total_score": 0,
                            "count": 0
                        }
                    theme_data[theme]["stocks"].append(stock.get('ticker'))
                    theme_data[theme]["total_score"] += stock.get('story_score', 0)
                    theme_data[theme]["count"] += 1

            # Calculate averages and format
            radar = []
            for theme, data in theme_data.items():
                radar.append({
                    "theme": theme,
                    "stock_count": data["count"],
                    "avg_score": round(data["total_score"] / data["count"], 1) if data["count"] > 0 else 0,
                    "top_stocks": data["stocks"][:5],  # Top 5
                    "heat": "hot" if data["count"] >= 10 else "developing"
                })

            # Sort by stock count
            radar.sort(key=lambda x: -x["stock_count"])

            return {"ok": True, "data": radar[:20]}  # Top 20 themes
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/theme-intel/alerts")
    def theme_alerts():
        """
        Get automated theme discovery alerts.
        Returns latest theme discovery results from automated analysis.
        """
        try:
            # Load latest automated theme discovery results from volume
            latest_path = Path(VOLUME_PATH) / 'theme_discovery_latest.json'

            if latest_path.exists():
                with open(latest_path) as f:
                    discovery_data = json.load(f)

                # Extract themes for alerts format
                themes = discovery_data.get('themes', [])

                # Sort by confidence score
                sorted_themes = sorted(
                    themes,
                    key=lambda x: x.get('confidence_score', 0),
                    reverse=True
                )

                # Format as alerts
                alerts = []
                for theme in sorted_themes[:20]:  # Top 20 themes
                    alert = {
                        'name': theme.get('name', 'Unknown'),
                        'confidence': theme.get('confidence_score', 0),
                        'laggards': theme.get('laggard_count', 0),
                        'method': theme.get('discovery_method', 'unknown'),
                        'patent_validated': theme.get('patent_validation', 0) > 30,
                        'contract_validated': theme.get('contract_validation', 0) > 20,
                        'leaders': theme.get('leaders', []),
                        'laggards_list': theme.get('laggards', [])[:5],  # Top 5 laggards
                        'timestamp': theme.get('timestamp', discovery_data.get('timestamp'))
                    }
                    alerts.append(alert)

                return {
                    "ok": True,
                    "data": alerts,
                    "metadata": {
                        "timestamp": discovery_data.get('timestamp'),
                        "total_themes": discovery_data.get('total_themes', 0),
                        "discovery_methods": discovery_data.get('discovery_methods', {})
                    }
                }
            else:
                # No automated results yet - return empty
                return {
                    "ok": True,
                    "data": [],
                    "message": "No theme discovery results available yet. Runs automatically Mon-Fri at 6:30 AM PST"
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/theme-intel/ticker/{ticker_symbol}")
    def theme_ticker(ticker_symbol: str):
        try:
            from src.intelligence.theme_intelligence import analyze_ticker_themes
            analysis = analyze_ticker_themes(ticker_symbol)
            return {"ok": True, "data": analysis}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/theme-intel/discovery")
    def theme_discovery_results():
        """
        Get full automated theme discovery results.
        Returns complete analysis from all 4 discovery methods:
        - Supply Chain Analysis
        - Patent Clustering
        - Contract Analysis
        - News Co-occurrence
        """
        try:
            latest_path = Path(VOLUME_PATH) / 'theme_discovery_latest.json'

            if latest_path.exists():
                with open(latest_path) as f:
                    discovery_data = json.load(f)

                return {
                    "ok": True,
                    "data": discovery_data
                }
            else:
                return {
                    "ok": False,
                    "error": "No theme discovery results available yet",
                    "message": "Theme discovery runs automatically Mon-Fri at 6:30 AM PST"
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # ROUTES - CONVICTION
    # =============================================================================

    @web_app.get("/conviction/alerts")
    def conviction_alerts(min_score: int = Query(60)):
        results = load_scan_results()
        if not results:
            return {"ok": True, "data": []}

        alerts = []
        for stock in results.get('results', []):
            score = stock.get('story_score', 0)
            if score >= min_score:
                alerts.append({
                    'ticker': stock.get('ticker'),
                    'score': score,
                    'strength': stock.get('story_strength'),
                    'theme': stock.get('hottest_theme')
                })

        alerts.sort(key=lambda x: x['score'], reverse=True)
        return {"ok": True, "data": alerts}

    @web_app.get("/conviction/{ticker_symbol}")
    def conviction_ticker(ticker_symbol: str):
        results = load_scan_results()
        if results:
            ticker_upper = ticker_symbol.upper()
            for stock in results.get('results', []):
                if stock.get('ticker', '').upper() == ticker_upper:
                    conviction_data = {
                        'ticker': ticker_symbol,
                        'score': stock.get('story_score', 0),
                        'strength': stock.get('story_strength'),
                        'themes': stock.get('themes', [])
                    }
                    return {"ok": True, "data": conviction_data}
        return {"ok": False, "error": "No data"}

    # =============================================================================
    # ROUTES - BRIEFING
    # =============================================================================

    @web_app.get("/briefing")
    def briefing():
        try:
            from src.intelligence.executive_commentary import generate_executive_briefing
            brief = generate_executive_briefing()
            return {"ok": True, "data": brief}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # ROUTES - SUPPLY CHAIN
    # =============================================================================

    @web_app.get("/supplychain/themes")
    def supplychain_themes():
        try:
            from src.intelligence.ecosystem_intelligence import get_supply_chain_themes
            themes = get_supply_chain_themes()
            return {"ok": True, "data": themes}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/supplychain/{theme_id}")
    def supplychain_theme(theme_id: str):
        try:
            from src.intelligence.ecosystem_intelligence import get_theme_supply_chain
            chain = get_theme_supply_chain(theme_id)
            return {"ok": True, "data": chain}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # ROUTES - EARNINGS
    # =============================================================================

    @web_app.get("/earnings")
    def earnings():
        try:
            from src.analysis.earnings import get_upcoming_earnings
            earnings_data = get_upcoming_earnings()
            return {"ok": True, "data": earnings_data}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # ROUTES - SEC & DEALS
    # =============================================================================

    @web_app.get("/sec/deals")
    def sec_deals():
        try:
            from src.data.sec_edgar import get_recent_ma_deals
            deals = get_recent_ma_deals()
            return {"ok": True, "data": deals}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/sec/ma-radar")
    def sec_ma_radar():
        try:
            from src.data.sec_edgar import get_pending_mergers_from_sec
            radar = get_pending_mergers_from_sec()
            return {"ok": True, "data": radar[:20] if radar else []}  # Top 20
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/sec/ma-check/{ticker_symbol}")
    def sec_ma_check(ticker_symbol: str):
        try:
            from src.data.sec_edgar import check_ticker_ma_activity
            activity = check_ticker_ma_activity(ticker_symbol)
            return {"ok": True, "data": activity}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/sec/filings/{ticker_symbol}")
    def sec_filings(ticker_symbol: str):
        try:
            from src.data.sec_edgar import SECEdgarClient
            client = SECEdgarClient()
            filings = client.get_company_filings(ticker_symbol.upper(), days_back=90)
            return {"ok": True, "data": [f.to_dict() for f in filings]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/sec/insider/{ticker_symbol}")
    def sec_insider(ticker_symbol: str):
        try:
            from src.data.sec_edgar import get_insider_transactions_sync
            trades = get_insider_transactions_sync(ticker_symbol.upper())
            return {"ok": True, "data": trades}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # ROUTES - OPTIONS (POLYGON)
    # =============================================================================

    @web_app.get("/options/flow/{ticker_symbol}")
    def options_flow(ticker_symbol: str):
        """Get options flow sentiment for a ticker"""
        try:
            from src.data.options import get_options_flow
            flow = get_options_flow(ticker_symbol.upper())
            return {"ok": True, "data": flow}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/options/unusual/{ticker_symbol}")
    def options_unusual(ticker_symbol: str, threshold: float = Query(2.0)):
        """Detect unusual options activity for a ticker"""
        try:
            from src.data.options import get_unusual_activity
            unusual = get_unusual_activity(ticker_symbol.upper(), threshold)
            return {"ok": True, "data": unusual}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/options/chain/{ticker_symbol}")
    def options_chain(ticker_symbol: str, expiration: str = Query(None)):
        """Get options chain with Greeks for a ticker"""
        try:
            from src.data.options import get_options_chain
            chain = get_options_chain(ticker_symbol.upper(), expiration)
            return {"ok": True, "data": chain}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/options/technical/{ticker_symbol}")
    def options_technical(ticker_symbol: str):
        """Get technical indicators (SMA, RSI, MACD) for a ticker"""
        try:
            from src.data.options import get_technical_indicators
            technical = get_technical_indicators(ticker_symbol.upper())
            return {"ok": True, "data": technical}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/options/overview/{ticker_symbol}")
    def options_overview(ticker_symbol: str):
        """Get comprehensive options overview combining flow, unusual activity, and technicals"""
        try:
            from src.data.options import get_options_overview
            overview = get_options_overview(ticker_symbol.upper())
            return {"ok": True, "data": overview}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/options/scan/unusual")
    def options_scan_unusual(limit: int = Query(20)):
        """Scan all tracked stocks for unusual options activity"""
        try:
            from src.data.options import scan_unusual_options_universe
            results = load_scan_results()
            if not results or not results.get('results'):
                return {"ok": False, "error": "No scan data available"}

            # Get top 100 stocks from scan results
            tickers = [s['ticker'] for s in results['results'][:100]]
            unusual = scan_unusual_options_universe(tickers, limit=limit)
            return {"ok": True, "data": unusual}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # ROUTES - CONTRACTS
    # =============================================================================

    @web_app.get("/contracts/themes")
    def contracts_themes():
        try:
            from src.data.gov_contracts import get_contract_trends
            themes = get_contract_trends()
            return {"ok": True, "data": themes}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/contracts/recent")
    def contracts_recent():
        try:
            from src.data.gov_contracts import get_recent_contracts
            contracts = get_recent_contracts()
            return {"ok": True, "data": contracts}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/contracts/company/{ticker_symbol}")
    def contracts_company(ticker_symbol: str):
        try:
            from src.data.gov_contracts import get_company_contracts
            contracts = get_company_contracts(ticker_symbol)
            return {"ok": True, "data": contracts}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # ROUTES - PATENTS
    # =============================================================================

    @web_app.get("/patents/themes")
    def patents_themes():
        try:
            from src.data.patents import get_patent_trends
            themes = get_patent_trends()
            return {"ok": True, "data": themes}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/patents/company/{ticker_symbol}")
    def patents_company(ticker_symbol: str):
        try:
            from src.data.patents import get_company_patents
            patents = get_company_patents(ticker_symbol)
            return {"ok": True, "data": patents}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # ROUTES - EVOLUTION & PARAMETERS
    # =============================================================================

    @web_app.get("/evolution/status")
    def evolution_status():
        try:
            from src.scoring.param_helper import get_learning_status
            status = get_learning_status()
            return {"ok": True, "data": status}
        except Exception as e:
            import traceback
            return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}

    @web_app.get("/evolution/weights")
    def evolution_weights():
        try:
            from src.scoring.param_helper import get_scoring_weights
            weights = get_scoring_weights()
            return {"ok": True, "data": weights}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/evolution/correlations")
    def evolution_correlations():
        """
        Get theme and sector correlation analysis.
        Returns daily correlation matrix and theme statistics.
        """
        try:
            correlation_file = Path(VOLUME_PATH) / 'correlation_analysis_latest.json'

            if correlation_file.exists():
                with open(correlation_file) as f:
                    correlation_data = json.load(f)

                return {
                    "ok": True,
                    "data": correlation_data
                }
            else:
                return {
                    "ok": False,
                    "error": "No correlation analysis available yet",
                    "message": "Correlation analysis runs daily at 1:00 PM PST"
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/debug/health", status_code=200)
    def debug_health():
        """System health check endpoint (production-safe)"""
        import sys
        try:
            from src.learning.parameter_learning import get_learning_status
            learning_status = get_learning_status()
            learning_ok = "error" not in learning_status
        except Exception as e:
            learning_status = {"error": str(e)}
            learning_ok = False

        return {
            "ok": True,
            "timestamp": datetime.now().isoformat(),
            "system": {
                "python_version": sys.version.split()[0],
                "platform": sys.platform
            },
            "services": {
                "api": "operational",
                "learning_system": "operational" if learning_ok else "degraded",
                "volume_mount": "operational" if Path(VOLUME_PATH).exists() else "unavailable"
            },
            "parameters": {
                "total": learning_status.get("parameters", {}).get("total", 0) if learning_ok else 0,
                "status": "healthy" if learning_ok else "degraded"
            }
        }

    @web_app.get("/parameters/status")
    def parameters_status():
        try:
            from src.scoring.param_helper import get_learning_status
            status = get_learning_status()
            return {"ok": True, "data": status}
        except Exception as e:
            import traceback
            return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}

    # =============================================================================
    # ROUTES - TRADES (STUBS)
    # =============================================================================

    # =============================================================================
    # TRADING ENDPOINTS (NOT IMPLEMENTED - Analysis-only mode)
    # =============================================================================
    # Returns HTTP 501 Not Implemented with roadmap information

    @web_app.get("/trades/positions", status_code=501)
    def trades_positions():
        return {
            "ok": False,
            "error": "Trading execution not implemented",
            "message": "This endpoint is planned for future release. Currently in read-only analysis mode.",
            "roadmap": ["Paper trading", "Alpaca integration", "Risk management"],
            "alternatives": ["Use /scan for analysis", "Use /conviction/alerts for setups"]
        }

    @web_app.get("/trades/watchlist", status_code=501)
    def trades_watchlist():
        return {
            "ok": False,
            "error": "Watchlist feature not implemented",
            "message": "Use browser localStorage or external tools for watchlists."
        }

    @web_app.get("/trades/activity", status_code=501)
    def trades_activity():
        return {
            "ok": False,
            "error": "Trade activity tracking not implemented"
        }

    @web_app.get("/trades/risk", status_code=501)
    def trades_risk():
        return {
            "ok": False,
            "error": "Risk analysis not implemented",
            "planned_metrics": ["Beta", "VaR", "Sharpe ratio", "Max drawdown"]
        }

    @web_app.get("/trades/journal", status_code=501)
    def trades_journal():
        return {
            "ok": False,
            "error": "Trade journal not implemented"
        }

    @web_app.get("/trades/daily-report", status_code=501)
    def trades_daily_report():
        return {
            "ok": False,
            "error": "Daily report not implemented"
        }

    @web_app.get("/trades/scan", status_code=501)
    def trades_scan():
        return {
            "ok": False,
            "error": "Trade scanning not implemented",
            "alternative": "Use /scan endpoint instead"
        }

    @web_app.post("/trades/create", status_code=501)
    def trades_create():
        return {
            "ok": False,
            "error": "Trade execution not implemented",
            "message": "Live trading disabled. Analysis-only system.",
            "reason": "No broker integration. Paper trading planned for Q2 2026."
        }

    @web_app.get("/trades/{trade_id}", status_code=501)
    def trades_detail(trade_id: str):
        return {
            "ok": False,
            "error": "Trade lookup not implemented"
        }

    @web_app.post("/trades/{trade_id}/sell", status_code=501)
    def trades_sell(trade_id: str):
        return {
            "ok": False,
            "error": "Trade execution not implemented"
        }

    @web_app.post("/sec/deals/add", status_code=501)
    def sec_deals_add():
        return {
            "ok": False,
            "error": "Manual deal entry not implemented",
            "message": "M&A deals are auto-discovered from SEC filings.",
            "alternative": "Deals are automatically tracked. Check /sec/deals for discovered M&A activity."
        }

    @web_app.post("/supplychain/ai-discover")
    def supplychain_ai_discover(ticker: str = None, theme: str = None):
        """
        AI-powered supply chain discovery using xAI/DeepSeek.

        Provide either ticker or theme parameter:
        - ticker: Discover supply chain for specific company
        - theme: Discover ecosystem for theme/sector

        Returns discovered relationships with confidence scores.
        """
        try:
            from src.intelligence.ecosystem_intelligence import ai_discover_supply_chain
            result = ai_discover_supply_chain(ticker=ticker, theme=theme)
            return {"ok": True, "data": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.post("/theme-intel/run-analysis")
    def theme_intel_run_analysis():
        """
        Manually trigger automated theme discovery.
        Runs all 4 discovery methods:
        - Supply Chain Analysis
        - Patent Clustering
        - Contract Analysis
        - News Co-occurrence

        Returns latest results immediately if discovery ran within last hour,
        otherwise returns status indicating scheduled run time.
        """
        try:
            # Check if we have recent results (within last hour)
            latest_path = Path(VOLUME_PATH) / 'theme_discovery_latest.json'

            if latest_path.exists():
                with open(latest_path) as f:
                    discovery_data = json.load(f)

                timestamp_str = discovery_data.get('timestamp', '')
                if timestamp_str:
                    from datetime import datetime, timedelta
                    result_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    age = datetime.now().astimezone() - result_time

                    if age < timedelta(hours=1):
                        # Recent results available
                        return {
                            "ok": True,
                            "data": discovery_data,
                            "message": f"Recent discovery results (age: {int(age.total_seconds()/60)} minutes)",
                            "age_minutes": int(age.total_seconds() / 60)
                        }

            # No recent results - return scheduled run info
            return {
                "ok": True,
                "message": "Theme discovery runs automatically Mon-Fri at 6:30 AM PST",
                "next_run": "See scheduled runs: modal app list",
                "note": "Results will be available via GET /theme-intel/alerts after next scheduled run"
            }

        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # TELEGRAM WEBHOOK
    # =============================================================================

    @web_app.post("/telegram/webhook")
    async def telegram_webhook(request: Request):
        """
        Telegram bot webhook endpoint for instant message handling.
        Set webhook: https://api.telegram.org/bot<TOKEN>/setWebhook?url=<MODAL_URL>/telegram/webhook
        """
        import os
        import requests as http_requests

        try:
            update = await request.json()
            bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
            chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')

            if not bot_token:
                return {"ok": False, "error": "Bot token not configured"}

            message = update.get('message', {})
            text = message.get('text', '').strip()
            msg_chat_id = message.get('chat', {}).get('id')

            if not text or not msg_chat_id:
                return {"ok": True}  # Ignore non-text updates

            def send_reply(reply_text: str):
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                http_requests.post(url, json={
                    'chat_id': msg_chat_id,
                    'text': reply_text,
                    'parse_mode': 'Markdown'
                }, timeout=10)

            # Handle commands
            if text.lower() == '/help':
                send_reply(
                    "*BOT COMMANDS*\n\n"
                    "Send any ticker (e.g., `NVDA`) for analysis\n\n"
                    "*Scan Commands:*\n"
                    "`/top` - Show top 10 stocks\n"
                    "`/status` - Check system status\n"
                    "`/themes` - Show hot themes\n\n"
                    "*Info:*\n"
                    "`/help` - Show this help"
                )
                return {"ok": True}

            elif text.lower() == '/status':
                send_reply(
                    "*System Status*\n\n"
                    "API: Operational\n"
                    f"Mode: Modal Serverless\n"
                    f"Webhook: Active"
                )
                return {"ok": True}

            elif text.lower() == '/top':
                try:
                    # Try to get latest scan results
                    latest_path = Path(VOLUME_PATH) / 'scan_results_latest.csv'
                    if latest_path.exists():
                        import pandas as pd
                        df = pd.read_csv(latest_path)
                        msg = "*TOP 10 STOCKS*\n\n"
                        score_col = 'composite_score' if 'composite_score' in df.columns else 'story_score'
                        for i, row in df.head(10).iterrows():
                            ticker = row.get('ticker', 'N/A')
                            score = row.get(score_col, 0)
                            msg += f"`{ticker:5}` | Score: {score:.0f}\n"
                        send_reply(msg)
                    else:
                        send_reply("No scan results available. Run a scan first.")
                except Exception as e:
                    send_reply(f"Error loading results: {str(e)[:100]}")
                return {"ok": True}

            elif text.lower() == '/themes':
                try:
                    from src.themes.fast_stories import get_hottest_themes_fast
                    themes = get_hottest_themes_fast(limit=5)
                    if themes:
                        msg = "*HOT THEMES*\n\n"
                        for t in themes[:5]:
                            name = t.get('theme', t.get('name', 'Unknown'))
                            heat = t.get('heat_score', t.get('score', 0))
                            msg += f"🔥 *{name}*: {heat:.0f}\n"
                        send_reply(msg)
                    else:
                        send_reply("No theme data available.")
                except Exception as e:
                    send_reply(f"Theme error: {str(e)[:100]}")
                return {"ok": True}

            # Ticker query (1-5 uppercase letters)
            elif len(text) <= 5 and text.isalpha():
                ticker = text.upper()
                try:
                    from src.scoring.story_scorer import score_stock_story
                    result = score_stock_story(ticker)
                    if result:
                        msg = f"*{ticker} ANALYSIS*\n\n"
                        msg += f"*Score:* {result.get('story_score', 0):.0f}/100\n"
                        msg += f"*Strength:* {result.get('story_strength', 'unknown')}\n"
                        if result.get('hottest_theme'):
                            msg += f"*Theme:* {result['hottest_theme']}\n"
                        if result.get('catalysts'):
                            msg += f"\n*Catalysts:*\n"
                            for c in result['catalysts'][:3]:
                                msg += f"• {c}\n"
                        send_reply(msg)
                    else:
                        send_reply(f"No data found for `{ticker}`")
                except Exception as e:
                    send_reply(f"Error analyzing {ticker}: {str(e)[:100]}")
                return {"ok": True}

            # Unknown command
            else:
                send_reply("Unknown command. Send /help for available commands.")
                return {"ok": True}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/telegram/setup")
    def telegram_setup():
        """
        Instructions for setting up Telegram webhook.
        """
        import os
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')

        return {
            "ok": True,
            "instructions": [
                "1. Get your Modal API URL from the deployment",
                "2. Set webhook using Telegram API:",
                f"   curl 'https://api.telegram.org/bot{bot_token[:10]}...{bot_token[-5:]}/setWebhook?url=YOUR_MODAL_URL/telegram/webhook'",
                "3. Test by sending /help to @Stocks_Story_Bot"
            ],
            "current_config": {
                "bot_token_set": bool(bot_token),
                "webhook_endpoint": "/telegram/webhook"
            }
        }

    # =============================================================================
    # CATCH-ALL FOR UNIMPLEMENTED ROUTES
    # =============================================================================

    @web_app.get("/{full_path:path}")
    def catch_all(full_path: str):
        return {
            "ok": False,
            "error": "Not implemented",
            "path": full_path,
            "message": "This endpoint hasn't been implemented yet"
        }

    return web_app
