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
)


# =============================================================================
# MODAL ASGI APP
# =============================================================================

@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("stock-api-keys")],
    keep_warm=1,
    timeout=600
)
@modal.asgi_app()
def create_fastapi_app():
    """
    Create FastAPI app inside Modal function.
    All imports happen here (in container where packages are available).
    """
    # Imports only available in container
    from fastapi import FastAPI, Query
    from fastapi.middleware.cors import CORSMiddleware
    import sys
    sys.path.insert(0, '/root')

    # Create FastAPI app
    web_app = FastAPI(title="Stock Scanner API v2", version="2.0")

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

    # Add request logging middleware
    @web_app.middleware("http")
    async def log_requests(request, call_next):
        import time
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log request details
        import logging
        logger = logging.getLogger("api")
        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"duration={process_time:.3f}s "
            f"client={request.client.host if request.client else 'unknown'}"
        )
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

    @web_app.get("/")
    def root():
        return {"ok": True, "service": "stock-scanner-api-v2", "version": "2.0"}

    @web_app.get("/health")
    def health():
        try:
            from src.analysis.market_health import get_market_health
            health_data = get_market_health()
            return {"ok": True, **health_data}
        except Exception as e:
            return {"ok": True, "status": "healthy", "service": "modal", "timestamp": datetime.now().isoformat()}

    @web_app.get("/scan")
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
        try:
            from src.intelligence.theme_intelligence import get_theme_alerts
            alerts = get_theme_alerts()
            return {"ok": True, "data": alerts}
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
            from src.data.earnings import get_upcoming_earnings
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
            from src.data.sec_edgar import get_recent_filings
            filings = get_recent_filings(ticker_symbol)
            return {"ok": True, "data": filings}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.get("/sec/insider/{ticker_symbol}")
    def sec_insider(ticker_symbol: str):
        try:
            from src.data.sec_edgar import get_insider_trades
            trades = get_insider_trades(ticker_symbol)
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
            from src.data.gov_contracts import get_contract_themes
            themes = get_contract_themes()
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

    @web_app.get("/evolution/correlations", status_code=501)
    def evolution_correlations():
        return {
            "ok": False,
            "error": "Signal correlation analysis not implemented",
            "message": "Correlation matrix planned for future release.",
            "planned_features": [
                "Signal-to-signal correlations",
                "Theme-to-performance correlations",
                "Lag analysis between signals",
                "Conditional correlation matrices"
            ],
            "estimated_release": "Q2 2026"
        }

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
    def supplychain_ai_discover():
        try:
            from src.intelligence.ecosystem_intelligence import ai_discover_supply_chain
            result = ai_discover_supply_chain()
            return {"ok": True, "data": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @web_app.post("/theme-intel/run-analysis")
    def theme_intel_run_analysis():
        try:
            from src.intelligence.theme_intelligence import run_theme_analysis
            result = run_theme_analysis()
            return {"ok": True, "data": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

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
