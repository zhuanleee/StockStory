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

app = modal.App("stockstory-api")

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
    .add_local_dir("data", remote_path="/root/data")
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
    # Helper to reload volume - creates fresh reference each time to avoid scoping issues
    def reload_volume():
        modal.Volume.from_name("scan-results").reload()

    # Imports only available in container
    from fastapi import FastAPI, Query, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
    import sys
    sys.path.insert(0, '/root')

    # Create FastAPI app with comprehensive documentation
    web_app = FastAPI(
        title="StockStory API",
        version="2.0.0",
        description="""
# StockStory API

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

* **Documentation:** https://github.com/zhuanleee/StockStory
* **Issues:** https://github.com/zhuanleee/StockStory/issues
        """,
        contact={
            "name": "StockStory Support",
            "email": "support@stockstory.app",
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
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.socket.io; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://zhuanleee--stockstory-api-create-fastapi-app.modal.run wss://zhuanleee--stockstory-api-create-fastapi-app.modal.run"
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
            "service": "stockstory-api",
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

            # Add raw_data for dashboard market pulse
            raw_data = {}
            try:
                import yfinance as yf
                # Get SPY price and daily change
                spy = yf.Ticker("SPY")
                spy_hist = spy.history(period="1mo")
                if len(spy_hist) >= 2:
                    spy_price = spy_hist['Close'].iloc[-1]
                    spy_prev = spy_hist['Close'].iloc[-2]
                    spy_change = ((spy_price / spy_prev) - 1) * 100
                    raw_data['spy_price'] = round(spy_price, 2)
                    raw_data['spy_change'] = round(spy_change, 2)
                    if len(spy_hist) >= 20:
                        spy_20d_return = ((spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[-20]) - 1) * 100
                        raw_data['spy_20d_return'] = round(spy_20d_return, 2)
                    else:
                        raw_data['spy_20d_return'] = 0
                else:
                    raw_data['spy_price'] = 0
                    raw_data['spy_change'] = 0
                    raw_data['spy_20d_return'] = 0

                # Get QQQ price and daily change
                qqq = yf.Ticker("QQQ")
                qqq_hist = qqq.history(period="5d")
                if len(qqq_hist) >= 2:
                    qqq_price = qqq_hist['Close'].iloc[-1]
                    qqq_prev = qqq_hist['Close'].iloc[-2]
                    qqq_change = ((qqq_price / qqq_prev) - 1) * 100
                    raw_data['qqq_price'] = round(qqq_price, 2)
                    raw_data['qqq_change'] = round(qqq_change, 2)
                else:
                    raw_data['qqq_price'] = 0
                    raw_data['qqq_change'] = 0

                # Get VIX
                vix = yf.Ticker("^VIX")
                vix_hist = vix.history(period="5d")
                if len(vix_hist) > 0:
                    raw_data['vix'] = round(vix_hist['Close'].iloc[-1], 1)
                else:
                    raw_data['vix'] = 16.0

                # Get VIX term structure ratio (VIX/VIX3M as proxy)
                raw_data['vix_term_ratio'] = 0.95  # Default neutral

            except Exception as e:
                raw_data = {'spy_price': 0, 'spy_change': 0, 'spy_20d_return': 0, 'qqq_price': 0, 'qqq_change': 0, 'vix': 16.0, 'vix_term_ratio': 0.95}

            return {"ok": True, **health_data, "raw_data": raw_data}
        except Exception as e:
            return {"ok": True, "status": "healthy", "service": "modal", "timestamp": datetime.now().isoformat()}

    @web_app.get("/debug/volume", tags=["Admin"])
    def debug_volume():
        """Debug endpoint to check volume contents."""
        import os
        reload_volume()  # Try to sync volume
        volume_path = VOLUME_PATH
        files = []
        if os.path.exists(volume_path):
            for f in os.listdir(volume_path):
                fpath = os.path.join(volume_path, f)
                size = os.path.getsize(fpath) if os.path.isfile(fpath) else 0
                files.append({"name": f, "size": size})
        return {
            "ok": True,
            "volume_path": volume_path,
            "files": files,
            "csv_exists": os.path.exists(os.path.join(volume_path, "scan_results_latest.csv"))
        }

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
                    <h1>📊 StockStory API Dashboard</h1>
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
                return {"ok": True, "themes": []}

            # Group stocks by theme
            theme_data = {}
            for stock in results['results']:
                theme = stock.get('hottest_theme', 'No Theme')
                if theme and theme != 'No Theme':
                    if theme not in theme_data:
                        theme_data[theme] = []
                    theme_data[theme].append(stock.get('ticker', ''))

            # Format as list with tickers
            themes = [
                {
                    "name": theme,
                    "count": len(tickers),
                    "tickers": tickers,
                    "active": True
                }
                for theme, tickers in sorted(theme_data.items(), key=lambda x: -len(x[1]))
            ]

            return {"ok": True, "themes": themes}
        except Exception as e:
            return {"ok": True, "themes": []}

    # =========================================================================
    # THEME MANAGEMENT API (for dashboard)
    # =========================================================================

    @web_app.get("/themes/config", tags=["Themes"])
    def get_themes_config():
        """Get all themes from ThemeManager."""
        try:
            from src.themes.theme_manager import get_theme_manager
            manager = get_theme_manager()
            themes = manager.get_all_themes(include_archived=True)
            stats = manager.get_stats()
            return {
                "ok": True,
                "themes": themes,
                "stats": stats
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.post("/themes/add", tags=["Themes"])
    def add_theme(request: dict):
        """Add a new theme."""
        try:
            from src.themes.theme_manager import get_theme_manager
            manager = get_theme_manager()

            theme_id = request.get("theme_id", "").upper().replace(" ", "_")
            name = request.get("name", theme_id.replace("_", " ").title())
            keywords = request.get("keywords", [])
            tickers = request.get("tickers", [])

            if not theme_id:
                return {"ok": False, "error": "theme_id is required"}
            if not keywords:
                return {"ok": False, "error": "keywords list is required"}

            success = manager.add_theme(theme_id, name, keywords, tickers)
            if success:
                return {"ok": True, "message": f"Added theme: {theme_id}"}
            else:
                return {"ok": False, "error": f"Theme {theme_id} already exists"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.post("/themes/update", tags=["Themes"])
    def update_theme(request: dict):
        """Update an existing theme."""
        try:
            from src.themes.theme_manager import get_theme_manager
            manager = get_theme_manager()

            theme_id = request.get("theme_id", "").upper()
            updates = {}
            if "name" in request:
                updates["name"] = request["name"]
            if "keywords" in request:
                updates["keywords"] = request["keywords"]
            if "tickers" in request:
                updates["tickers"] = request["tickers"]
            if "status" in request:
                updates["status"] = request["status"]

            if not theme_id:
                return {"ok": False, "error": "theme_id is required"}

            success = manager.update_theme(theme_id, **updates)
            if success:
                return {"ok": True, "message": f"Updated theme: {theme_id}"}
            else:
                return {"ok": False, "error": f"Theme {theme_id} not found"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.post("/themes/remove", tags=["Themes"])
    def remove_theme(request: dict):
        """Archive a theme (soft delete)."""
        try:
            from src.themes.theme_manager import get_theme_manager
            manager = get_theme_manager()

            theme_id = request.get("theme_id", "").upper()
            if not theme_id:
                return {"ok": False, "error": "theme_id is required"}

            success = manager.remove_theme(theme_id, archive=True)
            if success:
                return {"ok": True, "message": f"Archived theme: {theme_id}"}
            else:
                return {"ok": False, "error": f"Theme {theme_id} not found"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.post("/themes/restore", tags=["Themes"])
    def restore_theme(request: dict):
        """Restore an archived theme."""
        try:
            from src.themes.theme_manager import get_theme_manager
            manager = get_theme_manager()

            theme_id = request.get("theme_id", "").upper()
            if not theme_id:
                return {"ok": False, "error": "theme_id is required"}

            success = manager.restore_theme(theme_id)
            if success:
                return {"ok": True, "message": f"Restored theme: {theme_id}"}
            else:
                return {"ok": False, "error": f"Theme {theme_id} not found or not archived"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/themes/stats", tags=["Themes"])
    def get_theme_stats():
        """Get theme statistics."""
        try:
            from src.themes.theme_manager import get_theme_manager
            manager = get_theme_manager()
            stats = manager.get_stats()
            return {"ok": True, "stats": stats}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.post("/themes/discover", tags=["Themes"])
    def discover_themes():
        """Run AI theme discovery."""
        try:
            from src.themes.theme_manager import get_theme_manager
            from src.themes.fast_stories import fetch_all_sources_parallel
            manager = get_theme_manager()

            # Fetch recent headlines
            tickers = ['NVDA', 'AAPL', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META', 'AMD', 'AVGO']
            headlines = fetch_all_sources_parallel(tickers, max_workers=5)

            if not headlines:
                return {"ok": False, "error": "No headlines to analyze"}

            # Run AI discovery
            discovered = manager.discover_themes_with_ai(headlines)
            return {
                "ok": True,
                "discovered": discovered,
                "headline_count": len(headlines)
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/theme-intel/radar")
    def theme_radar():
        try:
            # Extract theme radar from scan results
            results = load_scan_results()
            if not results or not results.get('results'):
                return {"ok": True, "radar": []}

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
                count = data["count"]
                avg_score = round(data["total_score"] / count, 1) if count > 0 else 0

                # Determine lifecycle based on count and score
                if count >= 15 and avg_score >= 60:
                    lifecycle = "peak"
                elif count >= 10:
                    lifecycle = "accelerating"
                elif count >= 5:
                    lifecycle = "emerging"
                elif count >= 2:
                    lifecycle = "declining"
                else:
                    lifecycle = "dead"

                radar.append({
                    "theme_name": theme,
                    "theme": theme,
                    "stock_count": count,
                    "score": avg_score,
                    "avg_score": avg_score,
                    "tickers": data["stocks"][:5],
                    "top_stocks": data["stocks"][:5],
                    "lifecycle": lifecycle,
                    "trend": 0,  # No historical data for trend
                    "heat": "hot" if count >= 10 else "developing"
                })

            # Sort by stock count
            radar.sort(key=lambda x: -x["stock_count"])

            return {"ok": True, "radar": radar[:20]}  # Top 20 themes
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
            # JS expects data.briefing as a string
            if isinstance(brief, dict):
                # Format dict as readable briefing text
                summary = brief.get('summary', brief.get('market_state', 'No briefing available'))
                message = brief.get('message', '')
                briefing_text = f"{summary}\n\n{message}" if message else summary
                return {"ok": True, "briefing": briefing_text}
            return {"ok": True, "briefing": str(brief) if brief else "No briefing available"}
        except Exception as e:
            return {"ok": True, "briefing": "Briefing unavailable. Run a scan to populate data."}

    # =============================================================================
    # ROUTES - ECONOMIC DASHBOARD (FRED)
    # =============================================================================

    @web_app.get("/economic/dashboard")
    def economic_dashboard():
        """
        Get comprehensive economic indicators from FRED.
        Includes yield curve, employment, inflation, and credit data.
        """
        try:
            from utils.data_providers import FREDProvider

            if not FREDProvider.is_configured():
                return {
                    "ok": False,
                    "error": "FRED API key not configured",
                    "message": "Add FRED_API_KEY to environment variables"
                }

            dashboard = FREDProvider.get_economic_dashboard()
            return {"ok": True, **dashboard}
        except Exception as e:
            import traceback
            return {"ok": False, "error": str(e), "traceback": traceback.format_exc()[:500]}

    @web_app.get("/economic/series/{series_name}")
    def economic_series(series_name: str):
        """Get historical data for a specific economic series."""
        try:
            from utils.data_providers import FREDProvider

            if not FREDProvider.is_configured():
                return {"ok": False, "error": "FRED API key not configured"}

            series_id = FREDProvider.SERIES.get(series_name)
            if not series_id:
                return {"ok": False, "error": f"Unknown series: {series_name}"}

            data = FREDProvider.get_series(series_id, limit=30)
            meta = FREDProvider.SERIES_META.get(series_name, {})

            return {
                "ok": True,
                "series": series_name,
                "name": meta.get('name', series_name),
                "tooltip": meta.get('tooltip', ''),
                "data": data
            }
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
            from src.data.sec_edgar import get_pending_mergers_from_sec
            deals = get_pending_mergers_from_sec()
            return {"ok": True, "deals": deals or []}
        except Exception as e:
            return {"ok": False, "error": str(e), "deals": []}

    @web_app.get("/sec/ma-radar")
    def sec_ma_radar():
        try:
            from src.data.sec_edgar import get_pending_mergers_from_sec
            radar = get_pending_mergers_from_sec()
            return {"ok": True, "radar": radar[:20] if radar else []}  # Top 20
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/sec/ma-check/{ticker_symbol}")
    def sec_ma_check(ticker_symbol: str):
        try:
            from src.data.sec_edgar import detect_ma_activity
            activity = detect_ma_activity(ticker_symbol.upper())
            # Extract ma_score and signals from activity dict
            if isinstance(activity, dict):
                return {
                    "ok": True,
                    "ma_score": activity.get("ma_score", activity.get("score", 0)),
                    "signals": activity.get("signals", [])
                }
            return {"ok": True, "ma_score": 0, "signals": []}
        except Exception as e:
            return {"ok": False, "error": str(e), "ma_score": 0, "signals": []}

    @web_app.get("/sec/filings/{ticker_symbol}")
    def sec_filings(ticker_symbol: str):
        try:
            from src.data.sec_edgar import SECEdgarClient
            client = SECEdgarClient()
            filings = client.get_company_filings(ticker_symbol.upper(), days_back=90)
            filings_list = [f.to_dict() for f in filings] if filings else []
            return {"ok": True, "filings": filings_list, "count": len(filings_list)}
        except Exception as e:
            return {"ok": False, "error": str(e), "filings": [], "count": 0}

    @web_app.get("/sec/insider/{ticker_symbol}")
    def sec_insider(ticker_symbol: str):
        try:
            from src.data.sec_edgar import get_insider_transactions_sync
            trades = get_insider_transactions_sync(ticker_symbol.upper())
            trades_list = trades if trades else []
            return {"ok": True, "transactions": trades_list, "count": len(trades_list)}
        except Exception as e:
            return {"ok": False, "error": str(e), "transactions": [], "count": 0}

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
    # ROUTES - ENHANCED OPTIONS FLOW
    # =============================================================================

    @web_app.get("/options/feed", tags=["Options"])
    def options_unusual_feed(
        limit: int = Query(50),
        min_premium: float = Query(0),
        tickers: str = Query(None),
        sentiment: str = Query(None)
    ):
        """
        Get real-time unusual options activity feed.

        Args:
            limit: Max entries (default 50)
            min_premium: Minimum premium filter
            tickers: Comma-separated tickers to scan (default: top 10)
            sentiment: Filter by sentiment (bullish/bearish)
        """
        try:
            from src.analysis.options_flow import SmartMoneyTracker
            from src.data.polygon_provider import get_unusual_options_sync

            # Parse tickers
            if tickers:
                ticker_list = [t.strip().upper() for t in tickers.split(',')]
            else:
                ticker_list = ['SPY', 'QQQ', 'NVDA', 'AAPL', 'TSLA', 'META', 'AMZN', 'GOOGL', 'MSFT', 'AMD']

            all_unusual = []
            for ticker in ticker_list[:15]:  # Max 15 tickers
                try:
                    result = get_unusual_options_sync(ticker, volume_threshold=2.0)
                    if result and result.get('unusual_contracts'):
                        for contract in result['unusual_contracts']:
                            contract['ticker'] = ticker
                            if min_premium <= 0 or contract.get('premium', 0) >= min_premium:
                                all_unusual.append(contract)
                except Exception:
                    continue

            # Sort by vol/oi ratio descending
            all_unusual.sort(key=lambda x: x.get('vol_oi_ratio', 0), reverse=True)
            return {"ok": True, "feed": all_unusual[:limit], "count": len(all_unusual)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.post("/options/feed/scan", tags=["Options"])
    def options_scan_feed(min_premium: float = Query(50000)):
        """
        Scan all tracked stocks and update unusual activity feed.

        Args:
            min_premium: Minimum premium to track (default $50K)
        """
        try:
            from src.analysis.options_flow import scan_unusual_activity
            results = load_scan_results()
            if not results or not results.get('results'):
                return {"ok": False, "error": "No scan data available"}

            # Get top 50 stocks by score for scanning
            tickers = [s['ticker'] for s in results['results'][:50]]
            activities = scan_unusual_activity(tickers, min_premium)
            return {
                "ok": True,
                "scanned": len(tickers),
                "unusual_found": len(activities),
                "activities": activities[:20]
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/options/whales", tags=["Options"])
    def options_whale_trades(min_premium: float = Query(500000)):
        """Get whale trades (large premium options activity)."""
        try:
            from src.analysis.options_flow import SmartMoneyTracker

            # Scan top tickers for whale trades
            top_tickers = ['SPY', 'QQQ', 'NVDA', 'AAPL', 'TSLA', 'META', 'AMZN', 'GOOGL', 'MSFT', 'AMD']
            tracker = SmartMoneyTracker()
            all_whales = []

            for ticker in top_tickers:
                try:
                    flow = tracker.analyze_flow(ticker)
                    if flow and flow.get('notable_trades'):
                        for trade in flow['notable_trades']:
                            if trade.get('premium', 0) >= min_premium:
                                trade['ticker'] = ticker
                                trade['side'] = 'BUY'  # Assume buy for unusual activity
                                all_whales.append(trade)
                except Exception:
                    continue

            # Sort by premium descending
            all_whales.sort(key=lambda x: x.get('premium', 0), reverse=True)
            return {"ok": True, "whales": all_whales[:20], "count": len(all_whales)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/options/smart-money/{ticker_symbol}", tags=["Options"])
    def options_smart_money(ticker_symbol: str):
        """
        Get smart money flow analysis for a ticker.

        Returns institutional flow signals, sweep/block counts, sentiment.
        """
        try:
            from src.analysis.options_flow import get_smart_money_flow
            flow = get_smart_money_flow(ticker_symbol.upper())
            return {"ok": True, "data": flow}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/options/sentiment/{ticker_symbol}", tags=["Options"])
    def options_sentiment_dashboard(ticker_symbol: str):
        """
        Get comprehensive options sentiment dashboard.

        Returns P/C ratio, IV rank, GEX, max pain, skew analysis.
        """
        try:
            from src.analysis.options_flow import get_options_sentiment
            sentiment = get_options_sentiment(ticker_symbol.upper())
            return {"ok": True, "data": sentiment}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/options/screener", tags=["Options"])
    def options_screener(
        min_iv_rank: float = Query(None),
        max_iv_rank: float = Query(None),
        min_premium: float = Query(None),
        min_volume: int = Query(None),
        min_vol_oi_ratio: float = Query(None),
        sentiment: str = Query(None),
        limit: int = Query(30)
    ):
        """
        Screen options across universe based on criteria.

        Args:
            min_iv_rank: Minimum IV Rank (0-100)
            max_iv_rank: Maximum IV Rank (0-100)
            min_premium: Minimum unusual premium
            min_volume: Minimum total options volume
            min_vol_oi_ratio: Minimum volume/OI ratio
            sentiment: bullish or bearish
            limit: Max results (default 30)
        """
        try:
            from src.analysis.options_flow import screen_options
            results = load_scan_results()
            if not results or not results.get('results'):
                return {"ok": False, "error": "No scan data available"}

            # Get tickers from scan
            tickers = [s['ticker'] for s in results['results'][:100]]

            screened = screen_options(
                tickers,
                min_iv_rank=min_iv_rank,
                max_iv_rank=max_iv_rank,
                min_premium=min_premium,
                min_volume=min_volume,
                min_vol_oi_ratio=min_vol_oi_ratio,
                sentiment=sentiment,
                limit=limit
            )
            return {"ok": True, "results": screened, "count": len(screened)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/options/market-sentiment", tags=["Options"])
    def options_market_sentiment():
        """
        Get overall market options sentiment (SPY, QQQ, VIX options).
        """
        try:
            from src.analysis.options_flow import get_options_sentiment
            market_tickers = ['SPY', 'QQQ', 'IWM']
            sentiment_data = {}

            for ticker in market_tickers:
                try:
                    sentiment_data[ticker] = get_options_sentiment(ticker)
                except:
                    continue

            # Calculate aggregate sentiment
            scores = [s.get('sentiment_score', 50) for s in sentiment_data.values()]
            avg_score = sum(scores) / len(scores) if scores else 50

            pc_ratios = [s.get('put_call_ratio', 1.0) for s in sentiment_data.values()]
            avg_pc = sum(pc_ratios) / len(pc_ratios) if pc_ratios else 1.0

            # Get VIX data
            try:
                import yfinance as yf
                vix = yf.Ticker('^VIX')
                vix_price = vix.info.get('regularMarketPrice', 20)
            except:
                vix_price = 20

            # Get 0DTE volume (SPY options expiring today)
            zero_dte_volume = 0
            try:
                from src.data.polygon_provider import get_options_chain_sync
                from datetime import datetime
                today = datetime.now().strftime('%Y-%m-%d')
                spy_0dte = get_options_chain_sync('SPY', expiration_date=today)
                if spy_0dte:
                    calls = spy_0dte.get('calls', [])
                    puts = spy_0dte.get('puts', [])
                    zero_dte_volume = sum(c.get('volume', 0) for c in calls + puts)
            except Exception as e:
                log(f"Error fetching 0DTE volume: {e}")

            return {
                "ok": True,
                "data": {
                    "spy_put_call_ratio": sentiment_data.get('SPY', {}).get('put_call_ratio', {}).get('volume', 1.0) if isinstance(sentiment_data.get('SPY', {}).get('put_call_ratio'), dict) else sentiment_data.get('SPY', {}).get('put_call_ratio', 1.0),
                    "put_call_ratio": round(avg_pc, 2),
                    "total_gex": sum(s.get('gex', 0) if isinstance(s.get('gex'), (int, float)) else s.get('gex', {}).get('total', 0) for s in sentiment_data.values()),
                    "vix": vix_price,
                    "zero_dte_volume": zero_dte_volume,
                    "market_sentiment_score": round(avg_score, 1),
                    "market_label": "Bullish" if avg_score >= 60 else ("Bearish" if avg_score <= 40 else "Neutral"),
                    "tickers": sentiment_data
                }
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # ROUTES - CONTRACTS
    # =============================================================================

    @web_app.get("/contracts/themes")
    def contracts_themes():
        try:
            from src.data.gov_contracts import get_contract_trends
            result = get_contract_trends()
            # Handle if result is already a full response object
            if isinstance(result, dict) and 'themes' in result:
                return {"ok": True, "themes": result.get('themes', {})}
            return {"ok": True, "themes": result or {}}
        except Exception as e:
            return {"ok": False, "error": str(e), "themes": {}}

    @web_app.get("/contracts/recent")
    def contracts_recent():
        try:
            from src.data.gov_contracts import get_recent_contracts
            contracts = get_recent_contracts()
            return {"ok": True, "contracts": contracts or []}
        except Exception as e:
            return {"ok": False, "error": str(e), "contracts": []}

    @web_app.get("/contracts/company/{ticker_symbol}")
    def contracts_company(ticker_symbol: str):
        try:
            from src.data.gov_contracts import get_company_contracts
            result = get_company_contracts(ticker_symbol)
            # Handle both dict (activity) and list formats
            if isinstance(result, dict):
                return {"ok": True, "activity": result}
            elif isinstance(result, list):
                # Convert list to activity summary
                total_value = sum(c.get('amount', 0) for c in result) if result else 0
                agencies = list(set(c.get('agency', 'Unknown') for c in result if c.get('agency')))
                return {
                    "ok": True,
                    "activity": {
                        "contract_count": len(result),
                        "total_value": total_value,
                        "signal_strength": min(len(result) / 100, 1.0),
                        "top_agencies": agencies[:5]
                    }
                }
            return {"ok": True, "activity": None}
        except Exception as e:
            return {"ok": False, "error": str(e), "activity": None}

    # =============================================================================
    # ROUTES - PATENTS
    # =============================================================================

    @web_app.get("/patents/themes")
    def patents_themes():
        try:
            from src.data.patents import get_patent_trends
            result = get_patent_trends()
            # Handle if result is already a full response object
            if isinstance(result, dict) and 'themes' in result:
                return {"ok": True, "themes": result.get('themes', {})}
            return {"ok": True, "themes": result or {}}
        except Exception as e:
            return {"ok": False, "error": str(e), "themes": {}}

    @web_app.get("/patents/company/{ticker_symbol}")
    def patents_company(ticker_symbol: str):
        try:
            from src.data.patents import get_company_patents
            result = get_company_patents(ticker_symbol)
            # Handle both dict (activity) and list formats
            if isinstance(result, dict):
                return {"ok": True, "activity": result}
            elif isinstance(result, list):
                # Convert list to activity summary
                keywords = []
                for p in result[:50]:
                    if p.get('title'):
                        words = p['title'].lower().split()
                        keywords.extend([w for w in words if len(w) > 4])
                # Get top keywords by frequency
                from collections import Counter
                top_kw = [w for w, _ in Counter(keywords).most_common(10)]
                return {
                    "ok": True,
                    "activity": {
                        "patent_count": len(result),
                        "trend": "neutral",
                        "yoy_change": 0,
                        "top_keywords": top_kw
                    }
                }
            return {"ok": True, "activity": None}
        except Exception as e:
            return {"ok": False, "error": str(e), "activity": None}

    # =============================================================================
    # ROUTES - EVOLUTION & PARAMETERS
    # =============================================================================

    @web_app.get("/evolution/status")
    def evolution_status():
        try:
            from src.scoring.param_helper import get_learning_status
            status = get_learning_status()
            # Return status fields at top level for JS compatibility
            if isinstance(status, dict) and 'error' not in status:
                return {
                    "ok": True,
                    "learning_cycles": status.get("learning_cycles", 0),
                    "overall_accuracy": status.get("overall_accuracy", 0),
                    "calibration_score": status.get("calibration_score", 0),
                    "last_evolution": status.get("last_evolution", "Never")
                }
            return {"ok": True, "learning_cycles": 0, "overall_accuracy": 0, "calibration_score": 0, "last_evolution": "Never"}
        except Exception as e:
            return {"ok": True, "learning_cycles": 0, "overall_accuracy": 0, "calibration_score": 0, "last_evolution": "Never"}

    @web_app.get("/evolution/weights")
    def evolution_weights():
        try:
            from src.scoring.param_helper import get_scoring_weights
            weights = get_scoring_weights()
            return {"ok": True, "weights": weights}
        except Exception as e:
            # Return default weights on error
            return {"ok": True, "weights": {
                "theme_heat": 0.18,
                "catalyst": 0.18,
                "social_buzz": 0.12,
                "news_momentum": 0.10,
                "sentiment": 0.07,
                "ecosystem": 0.10,
                "technical": 0.25
            }}

    @web_app.get("/evolution/correlations")
    def evolution_correlations():
        """
        Get theme and sector correlation analysis.
        Returns top correlation pairs for dashboard display.
        """
        try:
            correlation_file = Path(VOLUME_PATH) / 'correlation_analysis_latest.json'

            if correlation_file.exists():
                with open(correlation_file) as f:
                    correlation_data = json.load(f)

                # Extract correlation_matrix
                matrix = correlation_data.get('correlation_matrix', {})

                # Convert matrix to flat list of unique pairs with correlation values
                pairs = []
                seen = set()
                for theme1, correlations in matrix.items():
                    if theme1 == 'null':
                        continue
                    for theme2, value in correlations.items():
                        if theme2 == 'null' or theme1 == theme2:
                            continue
                        # Create sorted pair key to avoid duplicates
                        pair_key = tuple(sorted([theme1, theme2]))
                        if pair_key not in seen:
                            seen.add(pair_key)
                            pairs.append({
                                'pair': f"{theme1} ↔ {theme2}",
                                'value': value
                            })

                # Sort by correlation value (highest first) and take top pairs
                pairs.sort(key=lambda x: abs(x['value']), reverse=True)

                # Return as flat dict for JS compatibility: {"pair_name": value}
                flat_correlations = {p['pair']: p['value'] for p in pairs[:8]}

                return {
                    "ok": True,
                    "correlations": flat_correlations
                }
            else:
                return {
                    "ok": True,
                    "correlations": {},
                    "message": "No correlation analysis available yet"
                }
        except Exception as e:
            return {"ok": True, "correlations": {}}

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

    @web_app.get("/debug/polygon", tags=["Debug"])
    def debug_polygon():
        """Check Polygon.io API configuration and test connection."""
        import os
        result = {
            "ok": True,
            "polygon_configured": False,
            "api_key_set": False,
            "api_key_preview": None,
            "test_result": None
        }

        api_key = os.environ.get('POLYGON_API_KEY', '')
        if api_key:
            result["api_key_set"] = True
            result["api_key_preview"] = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
            result["polygon_configured"] = True

            # Test API call
            try:
                from src.data.polygon_provider import get_options_flow_sync
                test_data = get_options_flow_sync('SPY')
                if test_data and not test_data.get('error'):
                    result["test_result"] = {
                        "status": "success",
                        "put_call_ratio": test_data.get('put_call_ratio'),
                        "sentiment": test_data.get('sentiment'),
                        "total_call_volume": test_data.get('total_call_volume'),
                        "total_put_volume": test_data.get('total_put_volume'),
                    }
                else:
                    result["test_result"] = {
                        "status": "error",
                        "error": test_data.get('error') if test_data else "No data returned"
                    }
            except Exception as e:
                import traceback
                result["test_result"] = {"status": "exception", "error": str(e), "trace": traceback.format_exc()[:500]}
        else:
            result["test_result"] = {"status": "not_configured", "error": "POLYGON_API_KEY not set"}

        return result

    @web_app.get("/debug/providers", tags=["Debug"])
    def debug_providers():
        """Check all data provider configurations and test connections."""
        import os
        from utils.data_providers import (
            FinnhubProvider, TiingoProvider, AlphaVantageProvider, FREDProvider
        )

        providers = {}

        # Check Polygon
        polygon_key = os.environ.get('POLYGON_API_KEY', '')
        providers['polygon'] = {
            'configured': bool(polygon_key),
            'key_preview': f"{polygon_key[:4]}...{polygon_key[-4:]}" if len(polygon_key) > 8 else None
        }

        # Check Finnhub
        finnhub_key = os.environ.get('FINNHUB_API_KEY', '')
        providers['finnhub'] = {
            'configured': FinnhubProvider.is_configured(),
            'key_preview': f"{finnhub_key[:4]}...{finnhub_key[-4:]}" if len(finnhub_key) > 8 else None
        }

        # Check Tiingo
        tiingo_key = os.environ.get('TIINGO_API_KEY', '')
        providers['tiingo'] = {
            'configured': TiingoProvider.is_configured(),
            'key_preview': f"{tiingo_key[:4]}...{tiingo_key[-4:]}" if len(tiingo_key) > 8 else None
        }

        # Check Alpha Vantage
        av_key = os.environ.get('ALPHA_VANTAGE_API_KEY', '')
        providers['alpha_vantage'] = {
            'configured': AlphaVantageProvider.is_configured(),
            'key_preview': f"{av_key[:4]}...{av_key[-4:]}" if len(av_key) > 8 else None
        }

        # Check FRED
        fred_key = os.environ.get('FRED_API_KEY', '')
        providers['fred'] = {
            'configured': FREDProvider.is_configured(),
            'key_preview': f"{fred_key[:4]}...{fred_key[-4:]}" if len(fred_key) > 8 else None
        }

        # Check DeepSeek
        deepseek_key = os.environ.get('DEEPSEEK_API_KEY', '')
        providers['deepseek'] = {
            'configured': bool(deepseek_key),
            'key_preview': f"{deepseek_key[:4]}...{deepseek_key[-4:]}" if len(deepseek_key) > 8 else None
        }

        # Check xAI
        xai_key = os.environ.get('XAI_API_KEY', '')
        providers['xai'] = {
            'configured': bool(xai_key),
            'key_preview': f"{xai_key[:4]}...{xai_key[-4:]}" if len(xai_key) > 8 else None
        }

        # Check Telegram
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        telegram_chat = os.environ.get('TELEGRAM_CHAT_ID', '')
        providers['telegram'] = {
            'configured': bool(telegram_token and telegram_chat),
            'bot_token_set': bool(telegram_token),
            'chat_id_set': bool(telegram_chat)
        }

        # Count configured
        configured_count = sum(1 for p in providers.values() if p.get('configured'))

        return {
            "ok": True,
            "providers": providers,
            "summary": {
                "total": len(providers),
                "configured": configured_count,
                "status": "healthy" if configured_count >= 5 else "partial" if configured_count >= 3 else "minimal"
            }
        }

    @web_app.get("/parameters/status")
    def parameters_status():
        try:
            from src.scoring.param_helper import get_learning_status
            status = get_learning_status()
            # Extract parameters dict for JS compatibility
            if isinstance(status, dict) and 'parameters' in status:
                return {"ok": True, "parameters": status['parameters']}
            # Return default parameters
            return {"ok": True, "parameters": {
                "total": 80,
                "learned": 0,
                "learning_progress": 0,
                "avg_confidence": 0
            }}
        except Exception as e:
            return {"ok": True, "parameters": {
                "total": 80,
                "learned": 0,
                "learning_progress": 0,
                "avg_confidence": 0
            }}

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

    @web_app.get("/watchlist", tags=["Watchlist"])
    def get_watchlist():
        """Get watchlist with performance data"""
        try:
            from src.data.watchlist_manager import get_watchlist_manager
            wm = get_watchlist_manager(VOLUME_PATH)
            watchlist = wm.get_watchlist_with_performance()
            return {
                "ok": True,
                "watchlist": watchlist,
                "count": len(watchlist)
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.post("/watchlist/add", tags=["Watchlist"])
    def add_to_watchlist(ticker: str, notes: str = ""):
        """Add a stock to watchlist"""
        try:
            from src.data.watchlist_manager import get_watchlist_manager
            wm = get_watchlist_manager(VOLUME_PATH)
            item = wm.add_to_watchlist(ticker.upper(), notes=notes)
            volume.commit()  # Persist to Modal volume
            return {"ok": True, "item": item.to_dict()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.delete("/watchlist/{ticker}", tags=["Watchlist"])
    def remove_from_watchlist(ticker: str):
        """Remove a stock from watchlist"""
        try:
            from src.data.watchlist_manager import get_watchlist_manager
            wm = get_watchlist_manager(VOLUME_PATH)
            success = wm.remove_from_watchlist(ticker.upper())
            volume.commit()  # Persist to Modal volume
            return {"ok": success}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/scans", tags=["Scans"])
    def get_scans(starred_only: bool = False, archived: bool = False, limit: int = 20):
        """Get scan history"""
        try:
            from src.data.watchlist_manager import get_watchlist_manager
            wm = get_watchlist_manager(VOLUME_PATH)

            if starred_only:
                scans = wm.get_starred_scans()
            elif archived:
                scans = wm.get_archived_scans()
            else:
                scans = wm.get_recent_scans(limit)

            return {
                "ok": True,
                "scans": [s.to_dict() for s in scans],
                "count": len(scans)
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/scans/{scan_id}", tags=["Scans"])
    def get_scan_detail(scan_id: int):
        """Get full scan data"""
        try:
            from src.data.watchlist_manager import get_watchlist_manager
            wm = get_watchlist_manager(VOLUME_PATH)
            record = wm.get_scan(scan_id)
            if not record:
                return {"ok": False, "error": "Scan not found"}
            data = wm.get_scan_data(scan_id)
            return {
                "ok": True,
                "scan": record.to_dict(),
                "data": data
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.post("/scans/{scan_id}/star", tags=["Scans"])
    def star_scan(scan_id: int, add_to_watchlist: bool = False):
        """Star a scan to preserve it"""
        try:
            from src.data.watchlist_manager import get_watchlist_manager
            wm = get_watchlist_manager(VOLUME_PATH)
            record = wm.star_scan(scan_id, add_to_watchlist=add_to_watchlist)
            if not record:
                return {"ok": False, "error": "Scan not found"}
            volume.commit()  # Persist to Modal volume
            return {"ok": True, "scan": record.to_dict()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.post("/scans/{scan_id}/unstar", tags=["Scans"])
    def unstar_scan(scan_id: int):
        """Remove star from a scan"""
        try:
            from src.data.watchlist_manager import get_watchlist_manager
            wm = get_watchlist_manager(VOLUME_PATH)
            record = wm.unstar_scan(scan_id)
            if not record:
                return {"ok": False, "error": "Scan not found"}
            volume.commit()  # Persist to Modal volume
            return {"ok": True, "scan": record.to_dict()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/history/{ticker}", tags=["Watchlist"])
    def get_stock_history(ticker: str):
        """Get scan history for a specific stock"""
        try:
            from src.data.watchlist_manager import get_watchlist_manager
            wm = get_watchlist_manager(VOLUME_PATH)
            history = wm.get_stock_history(ticker.upper())
            return {
                "ok": True,
                "ticker": ticker.upper(),
                "history": history,
                "count": len(history)
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/trades/watchlist", tags=["Deprecated"])
    def trades_watchlist_deprecated():
        """Deprecated - use /watchlist instead"""
        return {
            "ok": False,
            "error": "Endpoint deprecated",
            "message": "Use /watchlist endpoint instead"
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
    # AI INTELLIGENCE HUB - Unified Analysis
    # =============================================================================

    @web_app.get("/ai/intelligence", tags=["AI Intelligence"])
    def ai_intelligence():
        """
        Unified AI Intelligence Hub - Synthesizes ALL data sources into actionable insights.

        Aggregates:
        - Market health (Fear/Greed, Breadth, VIX)
        - Economic indicators (FRED)
        - Stock scanner results
        - Theme analysis
        - SEC intelligence
        - Options flow

        Returns AI-synthesized market narrative with:
        - Market regime assessment
        - Top themes with macro support
        - Conviction picks with reasoning
        - Risk alerts
        - Trade ideas
        """
        try:
            from src.services.ai_service import get_ai_service

            # Gather all data sources
            data_sources = {}

            # 1. Market Health
            try:
                from src.analysis.market_health import get_market_health
                health = get_market_health()
                data_sources['market_health'] = {
                    'fear_greed': health.get('fear_greed', {}),
                    'breadth': health.get('breadth', {}),
                    'vix': health.get('raw_data', {}).get('vix'),
                    'spy_change': health.get('raw_data', {}).get('spy_change')
                }
            except Exception as e:
                data_sources['market_health'] = {'error': str(e)}

            # 2. Economic Data (FRED)
            try:
                from utils.data_providers import FREDProvider
                if FREDProvider.is_configured():
                    econ = FREDProvider.get_economic_dashboard()
                    data_sources['economic'] = {
                        'overall_label': econ.get('overall_label'),
                        'yield_curve': econ.get('yield_curve', {}).get('display'),
                        'inverted': econ.get('yield_curve', {}).get('inverted'),
                        'cpi': econ.get('indicators', {}).get('cpi_yoy', {}).get('display'),
                        'unemployment': econ.get('indicators', {}).get('unemployment', {}).get('display'),
                        'fed_funds': econ.get('indicators', {}).get('fed_funds_rate', {}).get('display'),
                        'alerts': econ.get('alerts', [])
                    }
            except Exception as e:
                data_sources['economic'] = {'error': str(e)}

            # 3. Scanner Results Summary
            try:
                results = load_scan_results()
                if results and results.get('results'):
                    all_results = list(results['results'])  # Ensure it's a list
                    stocks = all_results[:20]  # Top 20
                    themes_summary = {}
                    for s in stocks:
                        if not isinstance(s, dict):
                            continue
                        theme = s.get('hottest_theme', 'Unknown') or 'Unknown'
                        if theme not in themes_summary:
                            themes_summary[theme] = []
                        catalyst = str(s.get('catalyst') or '')
                        themes_summary[theme].append({
                            'ticker': s.get('ticker'),
                            'score': s.get('final_score'),
                            'catalyst': catalyst[:100] if len(catalyst) > 100 else catalyst
                        })
                    data_sources['scanner'] = {
                        'total_stocks': len(all_results),
                        'top_themes': themes_summary,
                        'top_5': [{'ticker': s.get('ticker'), 'score': s.get('final_score'),
                                   'theme': s.get('hottest_theme')} for s in stocks[:5] if isinstance(s, dict)]
                    }
            except Exception as e:
                import traceback
                data_sources['scanner'] = {'error': str(e), 'trace': traceback.format_exc()[:200]}

            # 4. SEC Deals
            try:
                from src.data.sec_edgar import get_pending_mergers_from_sec
                deals = get_pending_mergers_from_sec()
                data_sources['sec_deals'] = {'count': len(deals) if deals else 0, 'recent': (deals[:3] if deals else [])}
            except Exception as e:
                data_sources['sec_deals'] = {'error': str(e)}

            # Build AI prompt - simplified for reliability
            ai_service = get_ai_service()

            # Simplify data for AI consumption
            health = data_sources.get('market_health', {})
            econ = data_sources.get('economic', {})
            scanner = data_sources.get('scanner', {})

            # Extract key metrics
            fear_greed = health.get('fear_greed', {}).get('score', 50)
            breadth = health.get('breadth', {}).get('advance_decline_ratio', 1.0)
            top_themes = list(scanner.get('top_themes', {}).keys())[:5]
            top_5 = scanner.get('top_5', [])

            system_prompt = "You are a senior market strategist. Respond ONLY with valid JSON."

            user_prompt = f"""Analyze this market data:

Fear/Greed: {fear_greed}/100
Breadth (A/D): {breadth}
Economy: {econ.get('overall_label', 'N/A')}
Yield Curve: {econ.get('yield_curve', 'N/A')} (Inverted: {econ.get('inverted', False)})
CPI: {econ.get('cpi', 'N/A')}, Unemployment: {econ.get('unemployment', 'N/A')}
Alerts: {[a.get('indicator') for a in econ.get('alerts', [])]}
Top Themes: {top_themes}
Top Stocks: {[s.get('ticker') for s in top_5]}

Return this JSON (no other text):
{{"regime":{{"label":"RISK-ON or RISK-OFF or ROTATION or CONSOLIDATION","confidence":70,"reasoning":"one sentence"}},"macro_theme_connection":{{"supporting_themes":["theme1"],"reasoning":"brief"}},"top_conviction_picks":[{{"ticker":"XXX","reasoning":"brief","risk":"brief"}}],"key_risks":["risk1"],"trade_ideas":[{{"idea":"trade","rationale":"why","invalidation":"exit"}}],"summary":"2 sentences"}}"""

            try:
                response = ai_service.call(user_prompt, system_prompt, max_tokens=2500,
                                           temperature=0.4, task_type="analysis")
            except Exception as ai_error:
                response = None
                data_sources['ai_error'] = str(ai_error)

            # Parse AI response
            ai_analysis = {}
            if response:
                try:
                    # Extract JSON from response
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', response)
                    if json_match:
                        ai_analysis = json.loads(json_match.group())
                    else:
                        ai_analysis = {"raw_response": response}
                except Exception as parse_error:
                    ai_analysis = {"raw_response": response, "parse_error": str(parse_error)}
            else:
                ai_analysis = {"error": "AI service returned no response", "ai_error": data_sources.get('ai_error')}

            return {
                "ok": True,
                "timestamp": datetime.now().isoformat(),
                "data_sources": list(data_sources.keys()),
                "analysis": ai_analysis,
                "raw_data": data_sources
            }

        except Exception as e:
            import traceback
            return {"ok": False, "error": str(e), "trace": traceback.format_exc()[:500]}

    @web_app.get("/ai/regime", tags=["AI Intelligence"])
    def ai_regime():
        """
        Quick market regime assessment.
        Returns: RISK-ON, RISK-OFF, ROTATION, or CONSOLIDATION with confidence.
        """
        try:
            from src.services.ai_service import get_ai_service
            from src.analysis.market_health import get_market_health

            health = get_market_health()

            # Quick data summary
            vix = health.get('raw_data', {}).get('vix', 20)
            fear_greed = health.get('fear_greed', {}).get('score', 50)
            breadth = health.get('breadth', {}).get('advance_decline_ratio', 1.0)
            spy_change = health.get('raw_data', {}).get('spy_change', 0)

            ai_service = get_ai_service()

            prompt = f"""Based on these market indicators, classify the current regime:

VIX: {vix}
Fear/Greed Score: {fear_greed}/100
Advance/Decline Ratio: {breadth}
SPY Daily Change: {spy_change}%

Respond with ONLY a JSON object:
{{"regime": "RISK-ON|RISK-OFF|ROTATION|CONSOLIDATION", "confidence": 0-100, "reasoning": "one sentence"}}"""

            response = ai_service.call(prompt, max_tokens=200, temperature=0.2, task_type="quick")

            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    result = json.loads(json_match.group())
                    return {"ok": True, **result}
            except:
                pass

            return {"ok": True, "regime": "UNKNOWN", "raw": response}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/ai/reasoning/{ticker}", tags=["AI Intelligence"])
    def ai_reasoning(ticker: str):
        """
        Get AI reasoning for why a specific stock is interesting.
        Combines technical, fundamental, and thematic analysis.
        """
        try:
            from src.services.ai_service import get_ai_service

            ticker = ticker.upper()
            stock_data = {}

            # Get stock from scanner results
            results = load_scan_results()
            if results and results.get('results'):
                for s in results['results']:
                    if s.get('ticker', '').upper() == ticker:
                        stock_data = s
                        break

            if not stock_data:
                return {"ok": False, "error": f"Ticker {ticker} not found in recent scan"}

            ai_service = get_ai_service()

            prompt = f"""Analyze why {ticker} is showing up as a top pick:

Stock Data:
- Final Score: {stock_data.get('final_score')}
- Theme: {stock_data.get('hottest_theme')}
- Catalyst: {stock_data.get('catalyst', 'N/A')}
- Story: {stock_data.get('story', 'N/A')[:500]}
- Technical Score: {stock_data.get('technical_score', 'N/A')}
- News Score: {stock_data.get('news_score', 'N/A')}

Provide analysis as JSON:
{{
    "thesis": "2-3 sentence investment thesis",
    "bull_case": ["point1", "point2"],
    "bear_case": ["risk1", "risk2"],
    "catalyst_timeline": "near-term/medium-term/long-term",
    "conviction_level": "HIGH/MEDIUM/LOW",
    "suggested_action": "specific actionable suggestion"
}}"""

            response = ai_service.call(prompt, max_tokens=800, temperature=0.3, task_type="analysis")

            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    analysis = json.loads(json_match.group())
                    return {"ok": True, "ticker": ticker, "analysis": analysis, "stock_data": stock_data}
            except:
                pass

            return {"ok": True, "ticker": ticker, "raw_analysis": response, "stock_data": stock_data}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/ai/digest", tags=["AI Intelligence"])
    def ai_digest():
        """
        Generate AI-powered daily market digest.
        Comprehensive morning briefing combining all data sources.
        """
        try:
            from src.services.ai_service import get_ai_service

            # Gather comprehensive data
            digest_data = {}

            # Market health
            try:
                from src.analysis.market_health import get_market_health
                digest_data['health'] = get_market_health()
            except:
                digest_data['health'] = {}

            # Economic
            try:
                from utils.data_providers import FREDProvider
                if FREDProvider.is_configured():
                    digest_data['economic'] = FREDProvider.get_economic_dashboard()
            except:
                digest_data['economic'] = {}

            # Top stocks
            try:
                results = load_scan_results()
                if results:
                    digest_data['top_stocks'] = results.get('results', [])[:10]
            except:
                digest_data['top_stocks'] = []

            ai_service = get_ai_service()

            system_prompt = """You are a senior market analyst preparing the morning briefing for a trading desk.
Be concise, actionable, and data-driven. Focus on what matters TODAY."""

            prompt = f"""Generate a morning market digest based on this data:

MARKET HEALTH:
- Fear/Greed: {digest_data.get('health', {}).get('fear_greed', {}).get('score', 'N/A')}
- VIX: {digest_data.get('health', {}).get('raw_data', {}).get('vix', 'N/A')}
- Breadth: {digest_data.get('health', {}).get('breadth', {}).get('breadth_score', 'N/A')}

ECONOMIC:
- Overall: {digest_data.get('economic', {}).get('overall_label', 'N/A')}
- Yield Curve: {digest_data.get('economic', {}).get('yield_curve', {}).get('display', 'N/A')}
- Alerts: {digest_data.get('economic', {}).get('alerts', [])}

TOP SCANNER PICKS:
{json.dumps([{{'ticker': s.get('ticker'), 'score': s.get('final_score'), 'theme': s.get('hottest_theme')}} for s in digest_data.get('top_stocks', [])[:5]], indent=2)}

Format your response as JSON:
{{
    "headline": "One compelling headline for today",
    "market_stance": "BULLISH/BEARISH/NEUTRAL with brief reason",
    "key_levels": {{"SPY": "support/resistance levels", "QQQ": "..."}},
    "sector_rotation": "Which sectors to favor/avoid today",
    "top_3_ideas": [
        {{"ticker": "XXX", "action": "BUY/WATCH/AVOID", "reason": "brief"}}
    ],
    "risks_today": ["risk1", "risk2"],
    "events_to_watch": ["event1", "event2"],
    "one_liner": "The single most important thing to know today"
}}"""

            response = ai_service.call(prompt, system_prompt, max_tokens=1500,
                                       temperature=0.4, task_type="analysis")

            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    digest = json.loads(json_match.group())
                    return {
                        "ok": True,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "generated_at": datetime.now().isoformat(),
                        "digest": digest
                    }
            except:
                pass

            return {"ok": True, "raw_digest": response}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/ai/matrix", tags=["AI Intelligence"])
    def ai_signal_matrix():
        """
        Smart Signal Matrix - Correlation between all data sources.
        Shows confirmations and conflicts across signals.
        """
        try:
            from src.services.ai_service import get_ai_service

            # Gather signals
            signals = {}

            # Market signals
            try:
                from src.analysis.market_health import get_market_health
                health = get_market_health()
                fg = health.get('fear_greed', {}).get('score', 50)
                signals['fear_greed'] = {
                    'value': fg,
                    'signal': 'BULLISH' if fg > 60 else 'BEARISH' if fg < 40 else 'NEUTRAL'
                }
                vix = health.get('raw_data', {}).get('vix', 20)
                signals['vix'] = {
                    'value': vix,
                    'signal': 'BULLISH' if vix < 15 else 'BEARISH' if vix > 25 else 'NEUTRAL'
                }
                breadth = health.get('breadth', {}).get('advance_decline_ratio', 1.0)
                signals['breadth'] = {
                    'value': breadth,
                    'signal': 'BULLISH' if breadth > 1.5 else 'BEARISH' if breadth < 0.7 else 'NEUTRAL'
                }
            except:
                pass

            # Economic signals
            try:
                from utils.data_providers import FREDProvider
                if FREDProvider.is_configured():
                    econ = FREDProvider.get_economic_dashboard()
                    yc = econ.get('yield_curve', {})
                    signals['yield_curve'] = {
                        'value': yc.get('spread'),
                        'signal': 'BEARISH' if yc.get('inverted') else 'BULLISH' if yc.get('spread', 0) > 0.5 else 'NEUTRAL'
                    }
                    cpi = econ.get('indicators', {}).get('cpi_yoy', {}).get('value', 2)
                    signals['inflation'] = {
                        'value': cpi,
                        'signal': 'BEARISH' if cpi > 4 else 'BULLISH' if cpi < 2.5 else 'NEUTRAL'
                    }
            except:
                pass

            # Theme momentum
            try:
                results = load_scan_results()
                if results and results.get('results'):
                    themes = {}
                    for s in results['results'][:50]:
                        theme = s.get('hottest_theme', 'Unknown')
                        if theme not in themes:
                            themes[theme] = 0
                        themes[theme] += 1
                    top_theme = max(themes, key=themes.get) if themes else 'N/A'
                    signals['theme_momentum'] = {
                        'value': top_theme,
                        'signal': 'ACTIVE' if themes.get(top_theme, 0) > 5 else 'WEAK'
                    }
            except:
                pass

            # Build correlation matrix
            signal_list = list(signals.keys())
            matrix = {}
            confirmations = []
            conflicts = []

            # Only directional signals can confirm or conflict
            directional_signals = {'BULLISH', 'BEARISH'}

            for i, s1 in enumerate(signal_list):
                for s2 in signal_list[i+1:]:
                    sig1 = signals[s1].get('signal', 'NEUTRAL')
                    sig2 = signals[s2].get('signal', 'NEUTRAL')

                    # Only compare directional signals
                    sig1_directional = sig1 in directional_signals
                    sig2_directional = sig2 in directional_signals

                    if sig1_directional and sig2_directional:
                        if sig1 == sig2:
                            confirmations.append({
                                'signals': [s1, s2],
                                'direction': sig1,
                                'strength': 'STRONG'
                            })
                        else:
                            # True conflict: BULLISH vs BEARISH
                            conflicts.append({
                                'signals': [s1, s2],
                                'directions': [sig1, sig2],
                                'note': f'{s1} is {sig1} but {s2} is {sig2} - conflicting signals'
                            })

            # AI interpretation
            ai_service = get_ai_service()

            prompt = f"""Interpret this signal matrix:

SIGNALS:
{json.dumps(signals, indent=2)}

CONFIRMATIONS: {json.dumps(confirmations)}
CONFLICTS: {json.dumps(conflicts)}

Provide brief JSON interpretation:
{{"overall_signal": "BULLISH/BEARISH/MIXED", "confidence": 0-100, "key_insight": "one sentence", "action": "what to do"}}"""

            response = ai_service.call(prompt, max_tokens=300, temperature=0.2, task_type="quick")

            interpretation = {}
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    interpretation = json.loads(json_match.group())
            except:
                interpretation = {"raw": response}

            return {
                "ok": True,
                "signals": signals,
                "confirmations": confirmations,
                "conflicts": conflicts,
                "interpretation": interpretation,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # TELEGRAM WEBHOOK - Full-Featured Bot
    # =============================================================================

    # Import WatchlistManager for persistent watchlist and scan management
    from src.data.watchlist_manager import get_watchlist_manager

    @web_app.post("/telegram/webhook")
    async def telegram_webhook(request: Request):
        """
        Full-featured Telegram bot webhook with rich analysis, charts, and more.
        """
        import os
        import requests as http_requests
        import io
        import sys

        import logging
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        tg_logger = logging.getLogger("telegram_webhook")

        def log(msg):
            """Log to both print and logging for Modal."""
            tg_logger.info(f"[TG] {msg}")
            print(f"[TG] {msg}", file=sys.stderr, flush=True)

        try:
            update = await request.json()
            bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')

            # Log incoming update
            log(f"📨 UPDATE RECEIVED: {json.dumps(update, default=str)[:500]}")

            if not bot_token:
                log("❌ Bot token not configured")
                return {"ok": False, "error": "Bot token not configured"}

            # Handle callback queries (button clicks)
            callback_query = update.get('callback_query')
            msg_thread_id = None  # Initialize thread ID

            if callback_query:
                callback_id = callback_query.get('id')
                callback_data = callback_query.get('data', '')
                cb_message = callback_query.get('message', {})
                cb_chat_id = cb_message.get('chat', {}).get('id')
                cb_user = callback_query.get('from', {}).get('username', 'unknown')
                msg_thread_id = cb_message.get('message_thread_id')  # Get topic ID from callback message

                log(f"🔘 BUTTON CLICK from @{cb_user}: {callback_data}")

                # Answer the callback to remove loading state
                http_requests.post(
                    f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                    json={"callback_query_id": callback_id},
                    timeout=5
                )

                # Map callback to command
                if callback_data.startswith('cmd_'):
                    cmd_text = '/' + callback_data[4:]  # cmd_top -> /top
                elif callback_data.startswith('chart_'):
                    ticker = callback_data[6:]  # chart_NVDA -> NVDA
                    cmd_text = f'/chart {ticker}'
                else:
                    cmd_text = callback_data

                # Redirect to message handler by setting text
                text = cmd_text
                msg_chat_id = cb_chat_id
                user_id = str(callback_query.get('from', {}).get('id', cb_chat_id))
                username = cb_user
                log(f"🔄 Redirecting to command: {text}")
            else:
                message = update.get('message', {})
                text = message.get('text', '').strip()
                msg_chat_id = message.get('chat', {}).get('id')
                msg_thread_id = message.get('message_thread_id')  # Topic ID if in a topic
                user_id = str(message.get('from', {}).get('id', msg_chat_id))
                username = message.get('from', {}).get('username', 'unknown')

                # Filter: Only respond to messages in Bot Alerts topic when in group
                group_chat_id = os.environ.get('TELEGRAM_GROUP_CHAT_ID', '-1003774843100')
                group_topic_id = int(os.environ.get('TELEGRAM_GROUP_TOPIC_ID', '46'))

                # Check if message is from the group
                if str(msg_chat_id) == group_chat_id:
                    # Only process if it's in the Bot Alerts topic
                    if msg_thread_id != group_topic_id:
                        log(f"⏭️ Ignoring group message outside Bot Alerts topic (thread_id: {msg_thread_id})")
                        return {"ok": True}
                    log(f"✅ Processing message from Bot Alerts topic")

            if not text or not msg_chat_id:
                log("⏭️ Skipping non-text update")
                return {"ok": True}

            # Use topic thread ID for replies (set earlier in message/callback processing)
            reply_thread_id = msg_thread_id

            def send_reply(reply_text: str):
                log(f"📤 SENDING REPLY ({len(reply_text)} chars): {reply_text[:100]}...")
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                try:
                    # Build payload
                    payload = {
                        'chat_id': msg_chat_id,
                        'text': reply_text,
                        'parse_mode': 'Markdown',
                        'disable_web_page_preview': True
                    }
                    # Add thread_id if replying to a topic
                    if reply_thread_id:
                        payload['message_thread_id'] = reply_thread_id

                    resp = http_requests.post(url, json=payload, timeout=15)
                    if resp.status_code == 200:
                        log("✅ Reply sent successfully")
                    elif resp.status_code == 400 and 'parse entities' in resp.text:
                        # Markdown parsing failed - retry without formatting
                        log("⚠️ Markdown parse failed, retrying without formatting...")
                        plain_text = reply_text.replace('*', '').replace('_', '').replace('`', '')
                        payload2 = {
                            'chat_id': msg_chat_id,
                            'text': plain_text,
                            'disable_web_page_preview': True
                        }
                        if reply_thread_id:
                            payload2['message_thread_id'] = reply_thread_id
                        resp2 = http_requests.post(url, json=payload2, timeout=15)
                        if resp2.status_code == 200:
                            log("✅ Reply sent (plain text)")
                        else:
                            log(f"❌ Plain reply also failed: {resp2.status_code}")
                    else:
                        log(f"❌ Reply failed: {resp.status_code} - {resp.text[:200]}")
                except Exception as e:
                    log(f"❌ Reply exception: {e}")

            def send_photo(photo_bytes: bytes, caption: str = ""):
                log(f"📤 SENDING PHOTO ({len(photo_bytes)} bytes)")
                url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
                files = {'photo': ('chart.png', photo_bytes, 'image/png')}
                data = {'chat_id': msg_chat_id, 'caption': caption, 'parse_mode': 'Markdown'}
                # Add thread_id if replying to a topic
                if reply_thread_id:
                    data['message_thread_id'] = reply_thread_id
                try:
                    resp = http_requests.post(url, files=files, data=data, timeout=30)
                    if resp.status_code == 200:
                        log("✅ Photo sent successfully")
                    else:
                        log(f"❌ Photo failed: {resp.status_code} - {resp.text[:200]}")
                except Exception as e:
                    log(f"❌ Photo exception: {e}")

            def send_with_buttons(reply_text: str, buttons: list):
                """Send message with inline keyboard buttons."""
                log(f"📤 SENDING WITH BUTTONS: {reply_text[:50]}...")
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                try:
                    payload = {
                        'chat_id': msg_chat_id,
                        'text': reply_text,
                        'parse_mode': 'Markdown',
                        'disable_web_page_preview': True,
                        'reply_markup': {
                            'inline_keyboard': buttons
                        }
                    }
                    if reply_thread_id:
                        payload['message_thread_id'] = reply_thread_id

                    resp = http_requests.post(url, json=payload, timeout=15)
                    if resp.status_code == 200:
                        log("✅ Message with buttons sent")
                    elif resp.status_code == 400 and 'parse entities' in resp.text:
                        # Retry without markdown
                        plain_text = reply_text.replace('*', '').replace('_', '').replace('`', '')
                        payload2 = {
                            'chat_id': msg_chat_id,
                            'text': plain_text,
                            'reply_markup': {'inline_keyboard': buttons}
                        }
                        if reply_thread_id:
                            payload2['message_thread_id'] = reply_thread_id
                        http_requests.post(url, json=payload2, timeout=15)
                    else:
                        log(f"❌ Buttons failed: {resp.status_code}")
                except Exception as e:
                    log(f"❌ Buttons exception: {e}")

            # Parse command and args
            parts = text.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1].strip().upper() if len(parts) > 1 else ""

            # ============ HELP / START ============
            if cmd == '/help' or cmd == '/start':
                welcome_text = (
                    "📈 *STOCKSTORY*\n\n"
                    "AI-powered stock analysis with story-first scoring.\n\n"
                    "*Quick Start:*\n"
                    "Just send any ticker: `NVDA`, `AAPL`, `TSLA`\n\n"
                    "Use the buttons below or tap *Menu* for all commands."
                )
                # Inline keyboard buttons
                buttons = [
                    [
                        {"text": "🏆 Top 10", "callback_data": "cmd_top"},
                        {"text": "📊 Movers", "callback_data": "cmd_movers"},
                        {"text": "🔥 Themes", "callback_data": "cmd_themes"}
                    ],
                    [
                        {"text": "📅 Earnings", "callback_data": "cmd_earnings"},
                        {"text": "👁 Watchlist", "callback_data": "cmd_watchlist"},
                        {"text": "🟢 Status", "callback_data": "cmd_status"}
                    ],
                    [
                        {"text": "📈 Chart NVDA", "callback_data": "chart_NVDA"},
                        {"text": "📈 Chart AAPL", "callback_data": "chart_AAPL"},
                        {"text": "📈 Chart TSLA", "callback_data": "chart_TSLA"}
                    ]
                ]
                send_with_buttons(welcome_text, buttons)
                return {"ok": True}

            # ============ CHAT ID ============
            elif cmd == '/chatid':
                # Return the chat ID - useful for getting group chat IDs
                chat_type = message.get('chat', {}).get('type', 'private')
                chat_title = message.get('chat', {}).get('title', 'Private Chat')
                msg = f"💬 *Chat Information*\n\n"
                msg += f"*Chat ID:* `{msg_chat_id}`\n"
                msg += f"*Type:* {chat_type}\n"
                if chat_type != 'private':
                    msg += f"*Title:* {chat_title}\n"
                msg += f"\n_Use this ID to configure group alerts._"
                send_reply(msg)
                return {"ok": True}

            # ============ STATUS ============
            elif cmd == '/status':
                import pandas as pd
                import os as os_mod
                # Check volume mount - don't call reload, just check what's there
                latest_path = Path(VOLUME_PATH) / 'scan_results_latest.csv'
                # Debug: list files in volume
                volume_exists = os_mod.path.exists(VOLUME_PATH)
                volume_files = os_mod.listdir(VOLUME_PATH) if volume_exists else []
                csv_exists = latest_path.exists()
                logger.info(f"[TG] Volume exists: {volume_exists}, files: {volume_files}, csv_exists: {csv_exists}")
                scan_count = 0
                scan_time = "Unknown"
                if latest_path.exists():
                    df = pd.read_csv(latest_path)
                    scan_count = len(df)
                    mtime = os_mod.path.getmtime(latest_path)
                    from datetime import datetime
                    scan_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')

                send_reply(
                    "🟢 *System Status*\n\n"
                    f"API: Operational\n"
                    f"Stocks in DB: {scan_count}\n"
                    f"Last Scan: {scan_time}\n"
                    f"Mode: Modal Serverless\n"
                    f"Path: {VOLUME_PATH}\n"
                    f"Exists: {volume_exists}\n"
                    f"CSV: {csv_exists}\n"
                    f"Files: {volume_files}"
                )
                return {"ok": True}

            # ============ TOP 10 ============
            elif cmd == '/top':
                try:
                    import pandas as pd
                    import os as os_mod
                    latest_path = Path(VOLUME_PATH) / 'scan_results_latest.csv'
                    logger.info(f"[TG] /top checking: path={latest_path}, exists={latest_path.exists()}, volume_files={os_mod.listdir(VOLUME_PATH) if os_mod.path.exists(VOLUME_PATH) else []}")
                    if latest_path.exists():
                        df = pd.read_csv(latest_path)
                        score_col = 'composite_score' if 'composite_score' in df.columns else 'story_score'
                        msg = "🏆 *TOP 10 STOCKS*\n\n"
                        for i, row in df.head(10).iterrows():
                            ticker = row.get('ticker', 'N/A')
                            score = row.get(score_col, 0)
                            price = row.get('price', 0)
                            rs = row.get('rs_composite', 0)
                            strength = "🔥" if score >= 80 else "📈" if score >= 60 else "📊"
                            msg += f"{strength} `{ticker:5}` Score: *{score:.0f}*"
                            if price:
                                msg += f" | ${price:.2f}"
                            if rs:
                                msg += f" | RS: {rs:+.1f}%"
                            msg += "\n"
                        send_reply(msg)
                    else:
                        send_reply("❌ No scan results. Run a scan first.")
                except Exception as e:
                    send_reply(f"Error: {str(e)[:100]}")
                return {"ok": True}

            # ============ MOVERS ============
            elif cmd == '/movers':
                try:
                    import pandas as pd
                    import os as os_mod
                    latest_path = Path(VOLUME_PATH) / 'scan_results_latest.csv'
                    logger.info(f"[TG] /movers checking: path={latest_path}, exists={latest_path.exists()}")
                    if latest_path.exists():
                        df = pd.read_csv(latest_path)
                        if 'change_pct' in df.columns:
                            df_sorted = df.sort_values('change_pct', ascending=False)
                            gainers = df_sorted.head(5)
                            losers = df_sorted.tail(5).iloc[::-1]

                            msg = "📊 *TODAY'S MOVERS*\n\n"
                            msg += "*Top Gainers:*\n"
                            for _, row in gainers.iterrows():
                                msg += f"🟢 `{row['ticker']:5}` +{row['change_pct']:.1f}%\n"
                            msg += "\n*Top Losers:*\n"
                            for _, row in losers.iterrows():
                                msg += f"🔴 `{row['ticker']:5}` {row['change_pct']:.1f}%\n"
                            send_reply(msg)
                        else:
                            send_reply("Change data not available in latest scan.")
                    else:
                        send_reply("❌ No scan results available.")
                except Exception as e:
                    send_reply(f"Error: {str(e)[:100]}")
                return {"ok": True}

            # ============ THEMES ============
            elif cmd == '/themes':
                try:
                    from src.themes.fast_stories import run_fast_story_detection
                    result = run_fast_story_detection(use_cache=True)
                    themes = result.get('themes', []) if result else []
                    if themes:
                        msg = "🔥 *HOT THEMES*\n\n"
                        for i, t in enumerate(themes[:8], 1):
                            name = t.get('name', t.get('theme', 'Unknown'))
                            # Check all possible field names for mention count
                            count = t.get('mention_count', t.get('count', t.get('mentions', 0)))
                            heat = t.get('heat', 'WARM')
                            momentum = t.get('momentum', 'STABLE')
                            # Heat-based emoji
                            emoji = "🔥" if heat == 'HOT' else "📈" if heat == 'WARM' else "🌱" if heat == 'EMERGING' else "📊"
                            msg += f"{emoji} *{name}*: {count} mentions"
                            if momentum == 'HEATING_UP':
                                msg += " ⬆️"
                            elif momentum == 'COOLING_DOWN':
                                msg += " ⬇️"
                            msg += "\n"
                            # Show top stocks for this theme
                            plays = t.get('primary_plays', [])
                            if plays:
                                msg += f"   `{'` `'.join(plays[:3])}`\n"
                        send_reply(msg)
                    else:
                        send_reply("No theme data available. Try again later.")
                except Exception as e:
                    send_reply(f"Theme error: {str(e)[:100]}")
                return {"ok": True}

            # ============ THEME MANAGEMENT ============
            elif cmd == '/addtheme':
                # /addtheme THEME_NAME keyword1,keyword2 TICK1,TICK2
                if not args:
                    send_reply("Usage: `/addtheme THEME_NAME keywords tickers`\n\n"
                               "Example:\n`/addtheme AI_AGENTS ai agent,autonomous,agentic AGNT,PLTR`")
                    return {"ok": True}
                try:
                    from src.themes.theme_manager import get_theme_manager
                    parts = args.split()
                    if len(parts) < 3:
                        send_reply("Need: THEME_NAME keywords tickers\n"
                                   "Example: `/addtheme AI_AGENTS ai,agent,autonomous AGNT,PLTR`")
                        return {"ok": True}
                    theme_id = parts[0].upper()
                    keywords = [k.strip().lower() for k in parts[1].split(',')]
                    tickers = [t.strip().upper() for t in parts[2].split(',')]
                    manager = get_theme_manager()
                    if manager.add_theme(theme_id, theme_id.replace('_', ' ').title(), keywords, tickers):
                        send_reply(f"✅ Added theme: *{theme_id}*\n"
                                   f"Keywords: {', '.join(keywords)}\n"
                                   f"Tickers: {', '.join(tickers)}")
                    else:
                        send_reply(f"Theme *{theme_id}* already exists. Use `/removetheme` first.")
                except Exception as e:
                    send_reply(f"Error: {str(e)[:100]}")
                return {"ok": True}

            elif cmd == '/removetheme':
                if not args:
                    send_reply("Usage: `/removetheme THEME_NAME`\nThis archives the theme (can be restored).")
                    return {"ok": True}
                try:
                    from src.themes.theme_manager import get_theme_manager
                    theme_id = args.strip().upper().replace(' ', '_')
                    manager = get_theme_manager()
                    if manager.remove_theme(theme_id, archive=True):
                        send_reply(f"🗑️ Archived theme: *{theme_id}*\nUse `/restoretheme {theme_id}` to restore.")
                    else:
                        send_reply(f"Theme *{theme_id}* not found.")
                except Exception as e:
                    send_reply(f"Error: {str(e)[:100]}")
                return {"ok": True}

            elif cmd == '/restoretheme':
                if not args:
                    send_reply("Usage: `/restoretheme THEME_NAME`")
                    return {"ok": True}
                try:
                    from src.themes.theme_manager import get_theme_manager
                    theme_id = args.strip().upper().replace(' ', '_')
                    manager = get_theme_manager()
                    if manager.restore_theme(theme_id):
                        send_reply(f"✅ Restored theme: *{theme_id}*")
                    else:
                        send_reply(f"Theme *{theme_id}* not found or not archived.")
                except Exception as e:
                    send_reply(f"Error: {str(e)[:100]}")
                return {"ok": True}

            elif cmd == '/themestats':
                try:
                    from src.themes.theme_manager import get_theme_manager
                    manager = get_theme_manager()
                    stats = manager.get_stats()
                    msg = "📊 *THEME STATISTICS*\n\n"
                    msg += f"Total themes: *{stats['total_themes']}*\n"
                    msg += f"  🟢 Known: {stats['known']}\n"
                    msg += f"  🌱 Emerging: {stats['emerging']}\n"
                    msg += f"  🗄️ Archived: {stats['archived']}\n\n"
                    msg += f"Last updated: {stats['last_updated'][:16] if stats['last_updated'] else 'Never'}\n"
                    if stats['ai_discovery_enabled']:
                        msg += f"AI Discovery: ✅ Enabled\n"
                        if stats['last_ai_run']:
                            msg += f"Last AI scan: {stats['last_ai_run'][:16]}\n"
                    else:
                        msg += f"AI Discovery: ❌ Disabled\n"
                    send_reply(msg)
                except Exception as e:
                    send_reply(f"Error: {str(e)[:100]}")
                return {"ok": True}

            elif cmd == '/discoverthemes':
                send_reply("🔍 Running AI theme discovery... (this may take 30s)")
                try:
                    from src.themes.theme_manager import get_theme_manager
                    from src.themes.fast_stories import fetch_all_sources_parallel
                    manager = get_theme_manager()
                    # Fetch recent headlines
                    tickers = ['NVDA', 'AAPL', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META']
                    headlines = fetch_all_sources_parallel(tickers)
                    if not headlines:
                        send_reply("No headlines to analyze.")
                        return {"ok": True}
                    # Run AI discovery
                    discovered = manager.discover_themes_with_ai(headlines)
                    if discovered:
                        msg = "🌱 *AI DISCOVERED THEMES*\n\n"
                        for t in discovered[:5]:
                            msg += f"*{t.get('name', 'Unknown')}*\n"
                            msg += f"  Keywords: {', '.join(t.get('keywords', [])[:3])}\n"
                            msg += f"  Tickers: {', '.join(t.get('suggested_tickers', [])[:3])}\n"
                            msg += f"  Catalyst: {t.get('catalyst', 'N/A')[:60]}\n\n"
                        msg += "_Use `/addtheme` to add any of these._"
                        send_reply(msg)
                    else:
                        send_reply("No new themes discovered. Current themes cover the news well!")
                except Exception as e:
                    send_reply(f"Discovery error: {str(e)[:100]}")
                return {"ok": True}

            # ============ EARNINGS ============
            elif cmd == '/earnings':
                try:
                    from src.analysis.earnings import get_upcoming_earnings
                    earnings = get_upcoming_earnings(days_ahead=7)
                    if earnings:
                        msg = "📅 *UPCOMING EARNINGS (7 days)*\n\n"
                        for e in earnings[:10]:
                            ticker = e.get('ticker', 'N/A')
                            date = e.get('date', 'TBD')
                            time = e.get('time', '')
                            emoji = "🌅" if time == 'bmo' else "🌙" if time == 'amc' else "📅"
                            msg += f"{emoji} `{ticker:5}` - {date}\n"
                        if len(earnings) > 10:
                            msg += f"\n_...and {len(earnings)-10} more_"
                        send_reply(msg)
                    else:
                        send_reply("No upcoming earnings in the next 7 days.")
                except Exception as e:
                    send_reply(f"Earnings error: {str(e)[:100]}")
                return {"ok": True}

            # ============ NEWS ============
            elif cmd == '/news':
                if not args:
                    send_reply("Usage: `/news TICKER`\nExample: `/news NVDA`")
                    return {"ok": True}
                ticker = args.split()[0].upper()
                try:
                    from src.analysis.news_analyzer import fetch_finnhub_news
                    news = fetch_finnhub_news(ticker)
                    if news and len(news) > 0:
                        msg = f"📰 *{ticker} NEWS*\n\n"
                        for n in news[:5]:
                            title = n.get('headline', n.get('title', 'No title'))[:60]
                            source = n.get('source', 'Unknown')
                            msg += f"• {title}...\n  _via {source}_\n\n"
                        send_reply(msg)
                    else:
                        send_reply(f"No recent news for `{ticker}`")
                except Exception as e:
                    send_reply(f"News error: {str(e)[:100]}")
                return {"ok": True}

            # ============ INSIDER ============
            elif cmd == '/insider':
                if not args:
                    send_reply("Usage: `/insider TICKER`\nExample: `/insider AAPL`")
                    return {"ok": True}
                ticker = args.split()[0]
                try:
                    from src.data.sec_edgar import get_insider_transactions_sync
                    trades = get_insider_transactions_sync(ticker, days_back=30)
                    if trades:
                        msg = f"👔 *{ticker} INSIDER TRADES (30d)*\n\n"
                        for t in trades[:5]:
                            name = t.get('name', 'Unknown')[:20]
                            txn_type = t.get('transaction_type', 'Unknown')
                            shares = t.get('shares', 0)
                            date = t.get('date', 'N/A')
                            emoji = "🟢" if 'buy' in txn_type.lower() or 'purchase' in txn_type.lower() else "🔴"
                            msg += f"{emoji} *{name}*\n   {txn_type}: {shares:,} shares ({date})\n\n"
                        send_reply(msg)
                    else:
                        send_reply(f"No insider trades for `{ticker}` in last 30 days")
                except Exception as e:
                    send_reply(f"Insider error: {str(e)[:100]}")
                return {"ok": True}

            # ============ SEC FILINGS ============
            elif cmd == '/sec':
                if not args:
                    send_reply("Usage: `/sec TICKER`\nExample: `/sec MSFT`")
                    return {"ok": True}
                ticker = args.split()[0]
                try:
                    from src.data.sec_edgar import SECEdgarClient
                    client = SECEdgarClient()
                    filings = client.get_company_filings(ticker, days_back=60)
                    if filings:
                        msg = f"📋 *{ticker} SEC FILINGS (60d)*\n\n"
                        for f in filings[:5]:
                            form = f.form_type if hasattr(f, 'form_type') else f.get('form_type', 'Unknown')
                            date = f.filed_date if hasattr(f, 'filed_date') else f.get('filed_date', 'N/A')
                            desc = f.description if hasattr(f, 'description') else f.get('description', '')
                            desc = desc[:40] if desc else form
                            emoji = "📄" if '10-' in form else "📊" if '8-K' in form else "📁"
                            msg += f"{emoji} *{form}* - {date}\n   {desc}\n\n"
                        send_reply(msg)
                    else:
                        send_reply(f"No SEC filings for `{ticker}` in last 60 days")
                except Exception as e:
                    send_reply(f"SEC error: {str(e)[:100]}")
                return {"ok": True}

            # ============ CHART ============
            elif cmd == '/chart':
                if not args:
                    send_reply("Usage: `/chart TICKER`\nExample: `/chart AAPL`")
                    return {"ok": True}
                ticker = args.split()[0]
                try:
                    import yfinance as yf
                    import matplotlib
                    matplotlib.use('Agg')
                    import matplotlib.pyplot as plt
                    import matplotlib.dates as mdates
                    from matplotlib.patches import Rectangle
                    import numpy as np

                    # Fetch data - get 1 year to fully calculate 200 SMA, display last 6 months
                    stock = yf.Ticker(ticker)
                    hist_full = stock.history(period='1y')

                    if hist_full.empty:
                        send_reply(f"No data available for `{ticker}`")
                        return {"ok": True}

                    # Calculate all SMAs on full data
                    hist_full['SMA10'] = hist_full['Close'].rolling(10).mean()
                    hist_full['SMA20'] = hist_full['Close'].rolling(20).mean()
                    hist_full['SMA50'] = hist_full['Close'].rolling(50).mean()
                    hist_full['SMA200'] = hist_full['Close'].rolling(200).mean()

                    # Get last 6 months for display (approx 126 trading days)
                    hist = hist_full.tail(126)

                    # Create chart
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), height_ratios=[3, 1],
                                                   gridspec_kw={'hspace': 0.05})
                    fig.patch.set_facecolor('#1a1a2e')

                    # Candlestick chart
                    ax1.set_facecolor('#1a1a2e')

                    # Calculate candle width (0.6 of average spacing)
                    width = 0.6
                    width2 = 0.1  # Wick width

                    # Colors
                    up_color = '#00d4ff'    # Cyan for up
                    down_color = '#ff6b6b'  # Red for down

                    # Draw candlesticks
                    for i in range(len(hist)):
                        date_num = mdates.date2num(hist.index[i])
                        open_price = hist['Open'].iloc[i]
                        close_price = hist['Close'].iloc[i]
                        high_price = hist['High'].iloc[i]
                        low_price = hist['Low'].iloc[i]

                        if close_price >= open_price:
                            color = up_color
                            body_bottom = open_price
                            body_height = close_price - open_price
                        else:
                            color = down_color
                            body_bottom = close_price
                            body_height = open_price - close_price

                        # Draw wick (high-low line)
                        ax1.plot([date_num, date_num], [low_price, high_price],
                                color=color, linewidth=1)

                        # Draw body (rectangle)
                        if body_height == 0:
                            body_height = 0.01  # Minimum height for doji
                        rect = Rectangle((date_num - width/2, body_bottom), width, body_height,
                                         facecolor=color, edgecolor=color, linewidth=0.5)
                        ax1.add_patch(rect)

                    # Add SMAs (pre-calculated on full data for accuracy)
                    dates_num = [mdates.date2num(d) for d in hist.index]

                    # SMA10 - Yellow
                    if hist['SMA10'].notna().any():
                        ax1.plot(dates_num, hist['SMA10'], color='#f1c40f', linewidth=1.2, alpha=0.9, label='SMA10')

                    # SMA20 - Orange
                    if hist['SMA20'].notna().any():
                        ax1.plot(dates_num, hist['SMA20'], color='#e67e22', linewidth=1.2, alpha=0.9, label='SMA20')

                    # SMA50 - Purple
                    if hist['SMA50'].notna().any():
                        ax1.plot(dates_num, hist['SMA50'], color='#9b59b6', linewidth=1.5, alpha=0.9, label='SMA50')

                    # SMA200 - White
                    if hist['SMA200'].notna().any():
                        ax1.plot(dates_num, hist['SMA200'], color='#ecf0f1', linewidth=2, alpha=0.9, label='SMA200')

                    ax1.set_ylabel('Price ($)', color='white', fontsize=10)
                    ax1.tick_params(colors='white')
                    ax1.spines['bottom'].set_color('#333')
                    ax1.spines['left'].set_color('#333')
                    ax1.spines['top'].set_visible(False)
                    ax1.spines['right'].set_visible(False)
                    ax1.legend(loc='upper left', facecolor='#1a1a2e', edgecolor='none',
                              labelcolor='white', fontsize=9)
                    ax1.set_xticklabels([])
                    ax1.grid(True, alpha=0.2, color='#444')
                    ax1.set_xlim(dates_num[0] - 1, dates_num[-1] + 1)

                    current_price = hist['Close'].iloc[-1]
                    change = ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
                    change_color = up_color if change >= 0 else down_color
                    ax1.set_title(f'{ticker}  ${current_price:.2f}  ({change:+.1f}%)',
                                 color='white', fontsize=14, fontweight='bold', pad=10)

                    # Volume chart
                    ax2.set_facecolor('#1a1a2e')
                    colors = [up_color if hist['Close'].iloc[i] >= hist['Open'].iloc[i] else down_color
                              for i in range(len(hist))]
                    ax2.bar(dates_num, hist['Volume'], color=colors, alpha=0.7, width=width)
                    ax2.set_ylabel('Vol', color='white', fontsize=9)
                    ax2.tick_params(colors='white', labelsize=8)
                    ax2.spines['bottom'].set_color('#333')
                    ax2.spines['left'].set_color('#333')
                    ax2.spines['top'].set_visible(False)
                    ax2.spines['right'].set_visible(False)
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
                    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
                    ax2.grid(True, alpha=0.2, color='#444')
                    ax2.set_xlim(dates_num[0] - 1, dates_num[-1] + 1)
                    plt.xticks(rotation=45, ha='right')

                    # Format volume axis
                    ax2.yaxis.set_major_formatter(
                        plt.FuncFormatter(lambda x, p: f'{x/1e6:.0f}M' if x >= 1e6 else f'{x/1e3:.0f}K')
                    )

                    plt.tight_layout()

                    # Save to bytes
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png', dpi=120, facecolor='#1a1a2e', edgecolor='none',
                               bbox_inches='tight', pad_inches=0.1)
                    buf.seek(0)
                    plt.close()

                    # Send chart
                    send_photo(buf.read(), f"📊 *{ticker}* - 6 Month Candlestick")

                except Exception as e:
                    log(f"Chart error for {ticker}: {e}")
                    send_reply(f"Chart error: {str(e)[:100]}")
                return {"ok": True}

            # ============ WATCHLIST ============
            elif cmd == '/watchlist':
                wm = get_watchlist_manager(VOLUME_PATH)
                watchlist = wm.get_watchlist_with_performance()
                if watchlist:
                    msg = "👁 *YOUR WATCHLIST*\n\n"
                    # Update prices first
                    try:
                        import yfinance as yf
                        tickers = [item['ticker'] for item in watchlist]
                        prices = {}
                        for t in tickers[:20]:
                            try:
                                stock = yf.Ticker(t)
                                prices[t] = stock.info.get('regularMarketPrice', 0)
                            except:
                                pass
                        wm.update_watchlist_prices(prices)
                        watchlist = wm.get_watchlist_with_performance()
                    except:
                        pass

                    for item in watchlist:
                        ticker = item['ticker']
                        change_pct = item.get('change_pct')
                        entry = item.get('entry_price')
                        current = item.get('current_price')
                        source = item.get('source_scan', {})

                        if change_pct is not None:
                            emoji = "🟢" if change_pct >= 0 else "🔴"
                            msg += f"`{ticker:5}` {emoji} {change_pct:+.1f}%"
                        else:
                            msg += f"`{ticker:5}`"

                        if current:
                            msg += f" | ${current:,.2f}"
                        if source.get('id'):
                            msg += f" (Scan #{source['id']})"
                        msg += "\n"

                    msg += f"\n_Total: {len(watchlist)} stocks_"
                    send_reply(msg)
                else:
                    send_reply("Your watchlist is empty.\nUse `/watch TICKER` to add stocks.")
                return {"ok": True}

            elif cmd == '/watch':
                if not args:
                    send_reply("Usage: `/watch TICKER [notes]`\nExample: `/watch NVDA Strong AI play`")
                    return {"ok": True}
                parts = args.split(maxsplit=1)
                ticker = parts[0].upper()
                notes = parts[1] if len(parts) > 1 else ""

                wm = get_watchlist_manager(VOLUME_PATH)

                # Get current price
                entry_price = None
                try:
                    import yfinance as yf
                    stock = yf.Ticker(ticker)
                    entry_price = stock.info.get('regularMarketPrice', 0)
                except:
                    pass

                item = wm.add_to_watchlist(ticker, entry_price=entry_price, notes=notes)
                msg = f"✅ Added `{ticker}` to watchlist"
                if entry_price:
                    msg += f" @ ${entry_price:,.2f}"
                if notes:
                    msg += f"\n📝 {notes}"
                send_reply(msg)
                return {"ok": True}

            elif cmd == '/unwatch':
                if not args:
                    send_reply("Usage: `/unwatch TICKER`\nExample: `/unwatch NVDA`")
                    return {"ok": True}
                ticker = args.split()[0].upper()
                wm = get_watchlist_manager(VOLUME_PATH)
                if wm.remove_from_watchlist(ticker):
                    send_reply(f"✅ Removed `{ticker}` from watchlist")
                else:
                    send_reply(f"`{ticker}` is not in your watchlist.")
                return {"ok": True}

            # ============ SCAN MANAGEMENT ============
            elif cmd == '/scans':
                wm = get_watchlist_manager(VOLUME_PATH)
                recent = wm.get_recent_scans(10)
                if recent:
                    msg = "📊 *RECENT SCANS*\n\n"
                    for scan in recent:
                        star = "⭐" if scan.starred else "  "
                        date = scan.date[:10] if scan.date else "Unknown"
                        picks = ", ".join(scan.top_picks[:3]) if scan.top_picks else "No picks"
                        msg += f"{star} `#{scan.scan_id:3}` {date}\n"
                        msg += f"    Top: {picks}\n"
                    msg += "\n_Use `/star ID` to keep a scan_"
                    send_reply(msg)
                else:
                    send_reply("No scans found.")
                return {"ok": True}

            elif cmd == '/star':
                wm = get_watchlist_manager(VOLUME_PATH)
                if not args:
                    # Star latest scan
                    latest = wm.get_latest_scan()
                    if latest:
                        scan_id = latest.scan_id
                    else:
                        send_reply("No scans available to star.")
                        return {"ok": True}
                else:
                    try:
                        scan_id = int(args.split()[0].replace('#', ''))
                    except ValueError:
                        send_reply("Usage: `/star [ID]`\nExample: `/star 12` or `/star` for latest")
                        return {"ok": True}

                # Check if user wants to add to watchlist
                add_to_wl = 'watch' in args.lower() or 'add' in args.lower()
                record = wm.star_scan(scan_id, add_to_watchlist=add_to_wl)

                if record:
                    msg = f"⭐ *Starred Scan #{scan_id}*\n\n"
                    msg += f"Date: {record.date[:10]}\n"
                    msg += f"Top Picks: {', '.join(record.top_picks[:5])}\n"
                    if add_to_wl:
                        msg += f"\n✅ Added top 5 picks to watchlist"
                    msg += "\n\n_This scan won't be auto-deleted_"
                    send_reply(msg)
                else:
                    send_reply(f"Scan #{scan_id} not found.")
                return {"ok": True}

            elif cmd == '/unstar':
                if not args:
                    send_reply("Usage: `/unstar ID`\nExample: `/unstar 12`")
                    return {"ok": True}
                try:
                    scan_id = int(args.split()[0].replace('#', ''))
                except ValueError:
                    send_reply("Invalid scan ID. Use `/unstar 12`")
                    return {"ok": True}

                wm = get_watchlist_manager(VOLUME_PATH)
                record = wm.unstar_scan(scan_id)
                if record:
                    send_reply(f"Removed star from Scan #{scan_id}")
                else:
                    send_reply(f"Scan #{scan_id} not found.")
                return {"ok": True}

            elif cmd == '/starred':
                wm = get_watchlist_manager(VOLUME_PATH)
                starred = wm.get_starred_scans()
                if starred:
                    msg = "⭐ *STARRED SCANS*\n\n"
                    for scan in sorted(starred, key=lambda x: x.date, reverse=True):
                        date = scan.date[:10] if scan.date else "Unknown"
                        picks = ", ".join(scan.top_picks[:3]) if scan.top_picks else "No picks"
                        msg += f"⭐ `#{scan.scan_id:3}` {date}\n"
                        msg += f"    {picks}\n"
                    msg += f"\n_Total: {len(starred)} starred scans_"
                    send_reply(msg)
                else:
                    send_reply("No starred scans.\nUse `/star` to star the latest scan.")
                return {"ok": True}

            elif cmd == '/archive':
                wm = get_watchlist_manager(VOLUME_PATH)
                if args:
                    # Archive specific scan
                    try:
                        scan_id = int(args.split()[0].replace('#', ''))
                        record = wm.archive_scan(scan_id)
                        if record:
                            send_reply(f"📁 Archived Scan #{scan_id}")
                        else:
                            send_reply(f"Scan #{scan_id} not found.")
                    except ValueError:
                        send_reply("Usage: `/archive [ID]` or `/archive` to view")
                else:
                    # List archived scans
                    archived = wm.get_archived_scans()
                    if archived:
                        msg = "📁 *ARCHIVED SCANS*\n\n"
                        for scan in sorted(archived, key=lambda x: x.date, reverse=True)[:15]:
                            date = scan.date[:10] if scan.date else "Unknown"
                            picks = ", ".join(scan.top_picks[:2]) if scan.top_picks else ""
                            msg += f"`#{scan.scan_id:3}` {date} - {picks}\n"
                        msg += f"\n_Total: {len(archived)} archived_"
                        send_reply(msg)
                    else:
                        send_reply("No archived scans.")
                return {"ok": True}

            elif cmd == '/history':
                if not args:
                    send_reply("Usage: `/history TICKER`\nExample: `/history NVDA`")
                    return {"ok": True}
                ticker = args.split()[0].upper()
                wm = get_watchlist_manager(VOLUME_PATH)
                history = wm.get_stock_history(ticker)

                if history:
                    msg = f"📜 *{ticker} SCAN HISTORY*\n\n"
                    for entry in history[:10]:
                        star = "⭐" if entry['starred'] else "  "
                        date = entry['date'][:10] if entry['date'] else "Unknown"
                        msg += f"{star} `#{entry['scan_id']:3}` {date}\n"

                        if entry.get('stock_data'):
                            sd = entry['stock_data']
                            score = sd.get('story_score', sd.get('composite_score', 0))
                            price = sd.get('price', 0)
                            if score:
                                msg += f"      Score: {score:.0f}"
                            if price:
                                msg += f" | ${price:,.2f}"
                            msg += "\n"

                    msg += f"\n_Found in {len(history)} scans_"
                    send_reply(msg)
                else:
                    send_reply(f"`{ticker}` not found in any scans.")
                return {"ok": True}

            elif cmd == '/cleanup':
                wm = get_watchlist_manager(VOLUME_PATH)
                days = 7
                if args:
                    try:
                        days = int(args.split()[0])
                    except:
                        pass
                archived = wm.cleanup_old_scans(days)
                send_reply(f"🧹 Cleaned up {archived} scans older than {days} days\n\n_Starred scans are preserved_")

            # ============ TICKER ANALYSIS (rich version) ============
            elif len(text) <= 5 and text.isalpha():
                ticker = text.upper()
                log(f"🔍 ANALYZING TICKER: {ticker}")
                try:
                    # Get comprehensive analysis
                    log(f"📊 Importing calculate_story_score...")
                    from src.scoring.story_scorer import calculate_story_score
                    log(f"📊 Calling calculate_story_score({ticker})...")
                    result = calculate_story_score(ticker)
                    log(f"📊 Got result: score={result.get('story_score', 'N/A')}, strength={result.get('story_strength', 'N/A')}")

                    if result:
                        score = result.get('story_score', 0)
                        strength = result.get('story_strength', 'unknown')

                        # Determine emoji
                        if score >= 80:
                            score_emoji = "🔥"
                        elif score >= 60:
                            score_emoji = "📈"
                        elif score >= 40:
                            score_emoji = "📊"
                        else:
                            score_emoji = "📉"

                        msg = f"{score_emoji} *{ticker} ANALYSIS*\n\n"
                        msg += f"*Score:* {score:.0f}/100 ({strength})\n"

                        # Price info
                        try:
                            import yfinance as yf
                            stock = yf.Ticker(ticker)
                            info = stock.info
                            price = info.get('regularMarketPrice', info.get('currentPrice', 0))
                            change = info.get('regularMarketChangePercent', 0)
                            volume = info.get('regularMarketVolume', 0)
                            avg_vol = info.get('averageVolume', 1)

                            if price:
                                change_emoji = "🟢" if change >= 0 else "🔴"
                                msg += f"\n*Price:* ${price:.2f} {change_emoji} {change:+.2f}%\n"
                            if volume and avg_vol:
                                vol_ratio = volume / avg_vol
                                vol_emoji = "🔊" if vol_ratio > 1.5 else "🔈"
                                msg += f"*Volume:* {vol_emoji} {vol_ratio:.1f}x avg\n"
                        except:
                            pass

                        # Theme
                        if result.get('hottest_theme'):
                            msg += f"\n*Theme:* 🎯 {result['hottest_theme']}\n"

                        # Technical
                        tech = result.get('technical', {})
                        if tech:
                            msg += "\n*Technical:*\n"
                            if tech.get('above_20'):
                                msg += "  ✅ Above 20 SMA\n"
                            if tech.get('above_50'):
                                msg += "  ✅ Above 50 SMA\n"
                            if tech.get('in_squeeze'):
                                msg += "  ⚡ IN SQUEEZE\n"
                            if tech.get('breakout_up'):
                                msg += "  🚀 BREAKOUT\n"

                        # Catalysts from catalyst component
                        catalyst_data = result.get('catalyst', {})
                        catalysts = catalyst_data.get('catalysts', [])
                        if catalysts:
                            msg += "\n*Catalysts:*\n"
                            for c in catalysts[:3]:
                                if isinstance(c, dict):
                                    c_type = c.get('type', 'event')
                                    c_date = c.get('date', '')
                                    c_emoji = "📅" if c_type == 'earnings' else "💰" if c_type == 'dividend' else "📊"
                                    msg += f"  {c_emoji} {c_type.title()}: {c_date}\n"
                                else:
                                    msg += f"  • {c}\n"

                        # Sentiment (0-100 scale, 50 = neutral)
                        sentiment = result.get('sentiment', {})
                        if sentiment:
                            sent_score = sentiment.get('score', 50)
                            sent_label = sentiment.get('sentiment', 'neutral')
                            sent_emoji = "🟢" if sent_score >= 60 else "🔴" if sent_score <= 40 else "⚪"
                            msg += f"\n*Sentiment:* {sent_emoji} {sent_label.title()} ({sent_score:.0f})\n"

                        # Social buzz
                        if result.get('is_trending'):
                            msg += "🔥 *TRENDING on social media*\n"

                        log(f"✅ Analysis complete for {ticker}, sending reply...")
                        send_reply(msg)
                    else:
                        log(f"⚠️ No data found for {ticker}")
                        send_reply(f"No data found for `{ticker}`")
                except Exception as e:
                    import traceback
                    error_tb = traceback.format_exc()
                    log(f"❌ ERROR analyzing {ticker}: {e}")
                    log(f"TRACEBACK:\n{error_tb}")
                    send_reply(f"Error analyzing {ticker}: {str(e)[:100]}")
                return {"ok": True}

            # ============ OPTIONS FLOW ============
            elif cmd == '/options':
                if not args:
                    send_reply("Usage: `/options TICKER`\nExample: `/options NVDA`")
                    return {"ok": True}
                ticker = args.split()[0].upper()
                try:
                    from src.analysis.options_flow import get_options_sentiment
                    sentiment = get_options_sentiment(ticker)
                    if sentiment:
                        msg = f"📊 *{ticker} OPTIONS SENTIMENT*\n\n"

                        # Put/Call ratio
                        pcr = sentiment.get('put_call_ratio', {})
                        if pcr:
                            vol_pcr = pcr.get('volume', 0)
                            oi_pcr = pcr.get('open_interest', 0)
                            pcr_emoji = "🐻" if vol_pcr > 1.0 else "🐂" if vol_pcr < 0.7 else "⚖️"
                            msg += f"*Put/Call Ratio:* {pcr_emoji}\n"
                            msg += f"  Volume: {vol_pcr:.2f}\n"
                            msg += f"  Open Interest: {oi_pcr:.2f}\n\n"

                        # IV Rank
                        iv = sentiment.get('iv_rank', {})
                        if iv:
                            rank = iv.get('rank', 0)
                            percentile = iv.get('percentile', 0)
                            iv_emoji = "🔥" if rank > 70 else "❄️" if rank < 30 else "📊"
                            msg += f"*IV Rank:* {iv_emoji} {rank:.0f}%\n"
                            msg += f"*IV Percentile:* {percentile:.0f}%\n\n"

                        # Max Pain
                        if sentiment.get('max_pain'):
                            msg += f"*Max Pain:* ${sentiment['max_pain']:.2f}\n\n"

                        # GEX
                        gex = sentiment.get('gex', {})
                        if gex:
                            total_gex = gex.get('total', 0)
                            gex_emoji = "📈" if total_gex > 0 else "📉"
                            msg += f"*GEX:* {gex_emoji} ${total_gex/1e6:.1f}M\n"
                            if gex.get('flip_price'):
                                msg += f"*GEX Flip:* ${gex['flip_price']:.2f}\n"

                        # Overall sentiment
                        overall = sentiment.get('overall_sentiment', 'neutral')
                        sent_emoji = "🟢" if overall == 'bullish' else "🔴" if overall == 'bearish' else "⚪"
                        msg += f"\n*Overall:* {sent_emoji} {overall.upper()}"

                        send_reply(msg)
                    else:
                        send_reply(f"No options data for `{ticker}`")
                except Exception as e:
                    send_reply(f"Options error: {str(e)[:100]}")
                return {"ok": True}

            elif cmd == '/whales':
                try:
                    from src.analysis.options_flow import get_whale_trades
                    min_premium = 500000  # $500K minimum
                    if args:
                        try:
                            min_premium = int(args.split()[0]) * 1000  # Accept as thousands
                        except:
                            pass

                    whales = get_whale_trades(min_premium=min_premium)
                    if whales:
                        msg = f"🐋 *WHALE OPTIONS TRADES (>${min_premium/1000:.0f}K)*\n\n"
                        for trade in whales[:8]:
                            ticker = trade.get('ticker', 'N/A')
                            premium = trade.get('premium', 0)
                            side = trade.get('side', 'unknown')
                            strike = trade.get('strike', 0)
                            expiry = trade.get('expiry', 'N/A')
                            opt_type = trade.get('type', 'C')

                            side_emoji = "🟢" if side.lower() in ['buy', 'call'] else "🔴"
                            type_emoji = "📈" if opt_type == 'C' else "📉"

                            msg += f"{side_emoji} *{ticker}* {type_emoji} ${strike:.0f} {expiry}\n"
                            msg += f"   ${premium/1000:.0f}K premium | {side.upper()}\n\n"

                        if len(whales) > 8:
                            msg += f"_...and {len(whales) - 8} more whale trades_"
                        send_reply(msg)
                    else:
                        send_reply(f"No whale trades found above ${min_premium/1000:.0f}K")
                except Exception as e:
                    send_reply(f"Whales error: {str(e)[:100]}")
                return {"ok": True}

            elif cmd == '/flow':
                if not args:
                    send_reply("Usage: `/flow TICKER`\nExample: `/flow AAPL`")
                    return {"ok": True}
                ticker = args.split()[0].upper()
                try:
                    from src.analysis.options_flow import get_smart_money_flow
                    flow = get_smart_money_flow(ticker)
                    if flow:
                        msg = f"💰 *{ticker} SMART MONEY FLOW*\n\n"

                        # Net flow
                        net = flow.get('net_flow', 0)
                        flow_emoji = "🟢" if net > 0 else "🔴" if net < 0 else "⚪"
                        msg += f"*Net Flow:* {flow_emoji} ${abs(net)/1e6:.2f}M "
                        msg += "INFLOW\n" if net > 0 else "OUTFLOW\n" if net < 0 else "NEUTRAL\n"

                        # Breakdown
                        call_flow = flow.get('call_flow', 0)
                        put_flow = flow.get('put_flow', 0)
                        msg += f"\n*Call Flow:* ${call_flow/1e6:.2f}M\n"
                        msg += f"*Put Flow:* ${put_flow/1e6:.2f}M\n"

                        # Notable trades
                        notable = flow.get('notable_trades', [])
                        if notable:
                            msg += "\n*Notable Trades:*\n"
                            for trade in notable[:5]:
                                t_type = trade.get('signal', 'trade')
                                premium = trade.get('premium', 0)
                                strike = trade.get('strike', 0)
                                t_emoji = "🔹" if 'sweep' in t_type.lower() else "🔶" if 'block' in t_type.lower() else "•"
                                msg += f"  {t_emoji} ${strike:.0f} | ${premium/1000:.0f}K ({t_type})\n"

                        # Institutional ratio
                        inst_ratio = flow.get('institutional_ratio', 0)
                        if inst_ratio:
                            msg += f"\n*Institutional:* {inst_ratio:.0%} of flow"

                        send_reply(msg)
                    else:
                        send_reply(f"No flow data for `{ticker}`")
                except Exception as e:
                    send_reply(f"Flow error: {str(e)[:100]}")
                return {"ok": True}

            elif cmd == '/unusual':
                try:
                    from src.analysis.options_flow import scan_unusual_activity
                    # Get tickers from args or use defaults
                    if args:
                        tickers = [t.strip().upper() for t in args.split(',')]
                    else:
                        # Default to top tech + recent movers
                        tickers = ['NVDA', 'AAPL', 'TSLA', 'META', 'AMZN', 'GOOGL', 'MSFT', 'AMD', 'SPY', 'QQQ']

                    unusual = scan_unusual_activity(tickers, min_premium=25000)
                    if unusual:
                        msg = "⚡ *UNUSUAL OPTIONS ACTIVITY*\n\n"
                        for item in unusual[:10]:
                            ticker = item.get('ticker', 'N/A')
                            premium = item.get('premium', 0)
                            vol_oi = item.get('volume_oi_ratio', 0)
                            opt_type = item.get('type', 'C')
                            strike = item.get('strike', 0)

                            type_emoji = "📈" if opt_type == 'C' else "📉"
                            msg += f"{type_emoji} *{ticker}* ${strike:.0f}\n"
                            msg += f"   ${premium/1000:.0f}K | Vol/OI: {vol_oi:.1f}x\n\n"

                        if len(unusual) > 10:
                            msg += f"_...and {len(unusual) - 10} more unusual trades_"
                        send_reply(msg)
                    else:
                        send_reply("No unusual options activity detected")
                except Exception as e:
                    send_reply(f"Unusual activity error: {str(e)[:100]}")
                return {"ok": True}

            elif cmd == '/hedge':
                try:
                    from src.analysis.options_flow import get_crisis_market_sentiment, get_put_protection_recommendations, get_options_sentiment

                    # Parse optional portfolio value
                    portfolio_value = 100000  # Default $100K
                    severity = 7  # Default elevated
                    if args:
                        parts = args.split()
                        for part in parts:
                            try:
                                val = int(part.replace('k', '000').replace('K', '000'))
                                portfolio_value = val
                            except:
                                pass

                    # Get market sentiment
                    sentiment = get_crisis_market_sentiment()

                    # Get SPY options data (GEX, Max Pain) from Polygon
                    spy_options = get_options_sentiment('SPY')
                    qqq_options = get_options_sentiment('QQQ')

                    # Get put recommendations
                    recs = get_put_protection_recommendations(crisis_severity=severity, portfolio_value=portfolio_value)

                    msg = "🛡️ *PUT PROTECTION RECOMMENDATIONS*\n\n"

                    # Market Sentiment Section
                    msg += "*📊 Live Market Sentiment*\n"
                    vix = sentiment.get('vix')
                    if vix:
                        vix_change = sentiment.get('vix_change', 0)
                        vix_emoji = "🔴" if vix >= 25 else "🟡" if vix >= 20 else "🟢"
                        msg += f"{vix_emoji} VIX: {vix:.1f} ({'+' if vix_change >= 0 else ''}{vix_change:.1f}%)\n"

                    spy_price = sentiment.get('spy_price')
                    if spy_price:
                        spy_change = sentiment.get('spy_change', 0)
                        msg += f"SPY: ${spy_price:,.2f} ({'+' if spy_change >= 0 else ''}{spy_change:.2f}%)\n"

                    qqq_price = sentiment.get('qqq_price')
                    if qqq_price:
                        qqq_change = sentiment.get('qqq_change', 0)
                        msg += f"QQQ: ${qqq_price:,.2f} ({'+' if qqq_change >= 0 else ''}{qqq_change:.2f}%)\n"

                    msg += f"Fear Level: {sentiment.get('market_fear_level', 'unknown')}\n\n"

                    # Options Flow Data (GEX, Max Pain, P/C Ratio)
                    msg += "*📈 Options Flow (Polygon)*\n"

                    # SPY Options Data
                    if spy_options:
                        spy_gex = spy_options.get('gex', {})
                        spy_gex_val = spy_gex.get('total', 0) if isinstance(spy_gex, dict) else spy_gex
                        spy_max_pain = spy_options.get('max_pain', 0)
                        spy_pc = spy_options.get('put_call_ratio', 0)
                        spy_iv_rank = spy_options.get('iv_rank', 0)

                        # Format GEX
                        if abs(spy_gex_val) >= 1e9:
                            gex_str = f"${spy_gex_val/1e9:.2f}B"
                        else:
                            gex_str = f"${spy_gex_val/1e6:.0f}M"

                        gex_emoji = "🟢" if spy_gex_val > 0 else "🔴"
                        msg += f"*SPY:* {gex_emoji} GEX {gex_str} | Max Pain ${spy_max_pain:,.0f}\n"
                        msg += f"      P/C {spy_pc:.2f} | IV Rank {spy_iv_rank:.0f}%\n"

                    # QQQ Options Data
                    if qqq_options:
                        qqq_gex = qqq_options.get('gex', {})
                        qqq_gex_val = qqq_gex.get('total', 0) if isinstance(qqq_gex, dict) else qqq_gex
                        qqq_max_pain = qqq_options.get('max_pain', 0)
                        qqq_pc = qqq_options.get('put_call_ratio', 0)
                        qqq_iv_rank = qqq_options.get('iv_rank', 0)

                        if abs(qqq_gex_val) >= 1e9:
                            gex_str = f"${qqq_gex_val/1e9:.2f}B"
                        else:
                            gex_str = f"${qqq_gex_val/1e6:.0f}M"

                        gex_emoji = "🟢" if qqq_gex_val > 0 else "🔴"
                        msg += f"*QQQ:* {gex_emoji} GEX {gex_str} | Max Pain ${qqq_max_pain:,.0f}\n"
                        msg += f"      P/C {qqq_pc:.2f} | IV Rank {qqq_iv_rank:.0f}%\n"

                    msg += "\n"

                    # AI Recommendations
                    msg += f"*🤖 Grok AI Analysis*\n"
                    msg += f"Portfolio: ${portfolio_value:,}\n"
                    msg += f"Protection Level: {recs.get('protection_level', 'standard').upper()}\n\n"

                    ai_analysis = recs.get('ai_analysis', '')
                    if ai_analysis:
                        msg += f"{ai_analysis}\n\n"

                    # Unusual puts (smart money)
                    unusual_puts = sentiment.get('unusual_put_activity', [])
                    if unusual_puts:
                        msg += "*🐋 Smart Money Put Activity*\n"
                        for put in unusual_puts[:3]:
                            ticker = put.get('ticker', '--')
                            strike = put.get('strike', 0)
                            premium = put.get('premium', 0) / 1000
                            msg += f"  {ticker} ${strike:.0f}P - ${premium:.0f}K\n"

                    msg += f"\n_Usage: /hedge [portfolio_value]_\n"
                    msg += f"_Example: /hedge 250000_"

                    send_reply(msg)
                except Exception as e:
                    send_reply(f"Hedge error: {str(e)[:100]}")
                return {"ok": True}

            # ============ COMMANDS LIST ============
            elif cmd == '/commands':
                msg = "📋 *ALL COMMANDS*\n\n"
                msg += "*Market Overview:*\n"
                msg += "  `/top` - Top 10 stocks by Story Score\n"
                msg += "  `/movers` - Market movers (gainers/losers)\n"
                msg += "  `/status` - System status\n\n"
                msg += "*Themes:*\n"
                msg += "  `/themes` - Hot market themes\n"
                msg += "  `/themestats` - Theme statistics\n"
                msg += "  `/addtheme` - Add a new theme\n"
                msg += "  `/removetheme` - Archive a theme\n"
                msg += "  `/restoretheme` - Restore archived theme\n"
                msg += "  `/discoverthemes` - AI discover new themes\n\n"
                msg += "*Stock Analysis (send ticker):*\n"
                msg += "  `NVDA` - Full stock analysis\n"
                msg += "  `/chart NVDA` - Price chart\n"
                msg += "  `/news NVDA` - Recent news\n"
                msg += "  `/insider NVDA` - Insider trades\n"
                msg += "  `/sec NVDA` - SEC filings\n\n"
                msg += "*Options Flow:*\n"
                msg += "  `/options NVDA` - Options sentiment\n"
                msg += "  `/flow NVDA` - Smart money flow\n"
                msg += "  `/whales` - Large options trades\n"
                msg += "  `/unusual` - Unusual activity scan\n"
                msg += "  `/hedge [amount]` - Put protection recs\n\n"
                msg += "*Watchlist & Scans:*\n"
                msg += "  `/watchlist` - Your watchlist with P&L\n"
                msg += "  `/watch NVDA` - Add to watchlist\n"
                msg += "  `/unwatch NVDA` - Remove from watchlist\n"
                msg += "  `/scans` - Recent scans\n"
                msg += "  `/star [ID]` - Star a scan (keep forever)\n"
                msg += "  `/starred` - View starred scans\n"
                msg += "  `/history NVDA` - Scan history for stock\n"
                msg += "  `/archive [ID]` - View/archive scans\n"
                msg += "  `/cleanup` - Archive old scans\n\n"
                msg += "*Other:*\n"
                msg += "  `/earnings` - Upcoming earnings\n"
                msg += "  `/chatid` - Get chat ID for group alerts\n"
                msg += "  `/help` - Quick start guide"
                send_reply(msg)
                return {"ok": True}

            # ============ UNKNOWN ============
            else:
                log(f"❓ Unknown command/text: {text}")
                if text.startswith('/'):
                    send_reply(f"Unknown command: `{cmd}`\nSend `/commands` for all commands.")
                else:
                    send_reply("Send a ticker symbol (e.g., `NVDA`) or `/commands` for help.")
                return {"ok": True}

        except Exception as e:
            import traceback
            error_tb = traceback.format_exc()
            log(f"❌ WEBHOOK ERROR: {e}")
            log(f"TRACEBACK:\n{error_tb}")
            return {"ok": False, "error": str(e)}

    @web_app.get("/telegram/setup")
    def telegram_setup():
        """Instructions for setting up Telegram webhook."""
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
            },
            "available_commands": [
                "/help", "/top", "/movers", "/themes", "/earnings",
                "/news TICKER", "/insider TICKER", "/sec TICKER", "/chart TICKER",
                "/options TICKER", "/flow TICKER", "/whales", "/unusual",
                "/watchlist", "/watch TICKER", "/unwatch TICKER", "/status"
            ]
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
