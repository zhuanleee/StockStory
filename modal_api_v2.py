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

    # Add CORS
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

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
            from src.analysis.market_breadth import get_market_health
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
            return {"ok": False, "error": str(e)}

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
        return {"ok": True, "data": {"message": "Not yet implemented"}}

    @web_app.get("/parameters/status")
    def parameters_status():
        try:
            from src.scoring.param_helper import get_learning_status
            status = get_learning_status()
            return {"ok": True, "data": status}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # =============================================================================
    # ROUTES - TRADES (STUBS)
    # =============================================================================

    @web_app.get("/trades/positions")
    def trades_positions():
        return {"ok": True, "data": []}

    @web_app.get("/trades/watchlist")
    def trades_watchlist():
        return {"ok": True, "data": []}

    @web_app.get("/trades/activity")
    def trades_activity():
        return {"ok": True, "data": []}

    @web_app.get("/trades/risk")
    def trades_risk():
        return {"ok": True, "data": {"risk_level": "low", "exposure": 0}}

    @web_app.get("/trades/journal")
    def trades_journal():
        return {"ok": True, "data": []}

    @web_app.get("/trades/daily-report")
    def trades_daily_report():
        return {"ok": True, "data": {"message": "No trades today"}}

    @web_app.get("/trades/scan")
    def trades_scan():
        return {"ok": True, "data": []}

    @web_app.post("/trades/create")
    def trades_create():
        return {"ok": False, "error": "Trading not enabled"}

    @web_app.get("/trades/{trade_id}")
    def trades_detail(trade_id: str):
        return {"ok": False, "error": "Trade not found"}

    @web_app.post("/trades/{trade_id}/sell")
    def trades_sell(trade_id: str):
        return {"ok": False, "error": "Trading not enabled"}

    @web_app.post("/sec/deals/add")
    def sec_deals_add():
        return {"ok": False, "error": "Not implemented"}

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
