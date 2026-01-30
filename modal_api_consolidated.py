#!/usr/bin/env python3
"""
Modal.com Consolidated API - Single FastAPI App with All Routes

Uses ONE Modal web endpoint with FastAPI routing for unlimited endpoints.
Bypasses Modal's 8 endpoint limit on free plan.

Total Routes: 40+
"""

import modal
from datetime import datetime
from pathlib import Path
import json
import os
from typing import Optional

# =============================================================================
# MODAL SETUP
# =============================================================================

app = modal.App("stock-scanner-consolidated-api")

# Persistent volume
volume = modal.Volume.from_name("scan-results", create_if_missing=True)
VOLUME_PATH = "/data"

# Image with FastAPI
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .pip_install("fastapi[standard]", "yfinance", "pandas", "numpy")
    .add_local_dir("src", remote_path="/root/src")
    .add_local_dir("config", remote_path="/root/config")
)

# FastAPI app will be created inside Modal function


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_latest_scan_file():
    """Get the most recent scan results file"""
    data_dir = Path(VOLUME_PATH)
    scan_files = sorted(data_dir.glob("scan_*.json"), reverse=True)
    return scan_files[0] if scan_files else None


def load_scan_results():
    """Load the latest scan results"""
    scan_file = get_latest_scan_file()
    if not scan_file:
        return None
    try:
        with open(scan_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading scan results: {e}")
        return None


# =============================================================================
# API ROUTES
# =============================================================================

@web_app.get("/")
async def root():
    """API root"""
    return {"ok": True, "service": "stock-scanner-api", "version": "2.0"}


@web_app.get("/health")
async def health():
    """GET /health - System health"""
    import sys
    sys.path.insert(0, '/root')

    try:
        from src.analysis.market_breadth import get_market_health
        health_data = get_market_health()
        return {"ok": True, **health_data}
    except Exception as e:
        return {
            "ok": True,
            "status": "healthy",
            "service": "modal-stock-scanner",
            "version": "2.0",
            "timestamp": datetime.now().isoformat()
        }


@web_app.get("/scan")
async def scan():
    """GET /scan - Get scan results"""
    results = load_scan_results()
    if not results:
        return {
            "ok": False,
            "status": "no_data",
            "message": "No scan results available yet.",
            "results": []
        }
    return results


@web_app.post("/scan/trigger")
async def scan_trigger(mode: str = Query("quick")):
    """POST /scan/trigger - Trigger scan"""
    from modal_scanner import scan_stock_with_ai_brain
    import sys
    sys.path.insert(0, '/root')

    if mode == "quick":
        tickers = ['NVDA', 'AMD', 'AVGO', 'TSM', 'MSFT', 'GOOGL', 'META', 'AAPL']
    else:
        try:
            from src.data.universe_manager import get_universe_manager
            um = get_universe_manager()
            tickers = um.get_scan_universe(use_polygon_full=False, min_market_cap=300_000_000)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    try:
        results = list(scan_stock_with_ai_brain.map(tickers))
        successful = [r for r in results if r and 'error' not in r]

        scan_data = {
            "ok": True,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total": len(tickers),
            "successful": len(successful),
            "results": successful
        }

        filename = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(VOLUME_PATH) / filename
        with open(filepath, 'w') as f:
            json.dump(scan_data, f)
        volume.commit()

        return scan_data
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/ticker/{ticker_symbol}")
async def ticker(ticker_symbol: str):
    """GET /ticker/:ticker - Ticker data"""
    import sys
    sys.path.insert(0, '/root')

    results = load_scan_results()
    if results:
        ticker_upper = ticker_symbol.upper()
        for stock in results.get('results', []):
            if stock.get('ticker', '').upper() == ticker_upper:
                return {"ok": True, "data": stock}

    try:
        from src.core.async_scanner import AsyncScanner
        import asyncio

        async def get_ticker():
            scanner = AsyncScanner(max_concurrent=1)
            result = await scanner.scan_ticker(ticker_symbol, price_data=None)
            await scanner.close()
            return result

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_ticker())
        loop.close()

        if result:
            return {"ok": True, "data": result}
        else:
            return {"ok": False, "error": "No data available"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/themes/list")
async def themes_list():
    """GET /themes/list"""
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.intelligence.theme_discovery import get_all_themes
        themes = get_all_themes()
        return {"ok": True, "data": themes}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/theme-intel/radar")
async def theme_intel_radar():
    """GET /theme-intel/radar"""
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.intelligence.theme_intelligence import get_theme_radar
        radar = get_theme_radar()
        return {"ok": True, "data": radar}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/theme-intel/alerts")
async def theme_intel_alerts():
    """GET /theme-intel/alerts"""
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.intelligence.theme_intelligence import get_theme_alerts
        alerts = get_theme_alerts()
        return {"ok": True, "data": alerts}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/theme-intel/ticker/{ticker_symbol}")
async def theme_intel_ticker(ticker_symbol: str):
    """GET /theme-intel/ticker/:ticker"""
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.intelligence.theme_intelligence import analyze_ticker_themes
        analysis = analyze_ticker_themes(ticker_symbol)
        return {"ok": True, "data": analysis}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.post("/theme-intel/run-analysis")
async def theme_intel_run_analysis():
    """POST /theme-intel/run-analysis"""
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.intelligence.theme_intelligence import run_theme_analysis
        result = run_theme_analysis()
        return {"ok": True, "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/conviction/alerts")
async def conviction_alerts(min_score: int = Query(60)):
    """GET /conviction/alerts"""
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
async def conviction_ticker(ticker_symbol: str):
    """GET /conviction/:ticker"""
    results = load_scan_results()
    if results:
        ticker_upper = ticker_symbol.upper()
        for stock in results.get('results', []):
            if stock.get('ticker', '').upper() == ticker_upper:
                return {"ok": True, "data": {
                    'ticker': ticker_symbol,
                    'score': stock.get('story_score', 0),
                    'strength': stock.get('story_strength'),
                    'themes': stock.get('themes', [])
                }}
    return {"ok": False, "error": "No data"}


@web_app.get("/briefing")
async def briefing():
    """GET /briefing"""
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.intelligence.executive_commentary import generate_executive_briefing
        brief = generate_executive_briefing()
        return {"ok": True, "data": brief}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/supplychain/themes")
async def supplychain_themes():
    """GET /supplychain/themes"""
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.intelligence.ecosystem_intelligence import get_supply_chain_themes
        themes = get_supply_chain_themes()
        return {"ok": True, "data": themes}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/supplychain/{theme_id}")
async def supplychain_theme(theme_id: str):
    """GET /supplychain/:themeId"""
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.intelligence.ecosystem_intelligence import get_theme_supply_chain
        chain = get_theme_supply_chain(theme_id)
        return {"ok": True, "data": chain}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.post("/supplychain/ai-discover")
async def supplychain_ai_discover():
    """POST /supplychain/ai-discover"""
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.intelligence.ecosystem_intelligence import ai_discover_supply_chain
        result = ai_discover_supply_chain()
        return {"ok": True, "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/earnings")
async def earnings():
    """GET /earnings"""
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.data.earnings import get_upcoming_earnings
        earnings_data = get_upcoming_earnings()
        return {"ok": True, "data": earnings_data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# SEC endpoints
@web_app.get("/sec/deals")
async def sec_deals():
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.data.sec_edgar import get_recent_ma_deals
        deals = get_recent_ma_deals()
        return {"ok": True, "data": deals}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/sec/ma-radar")
async def sec_ma_radar():
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.data.sec_edgar import get_ma_radar
        radar = get_ma_radar()
        return {"ok": True, "data": radar}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/sec/ma-check/{ticker_symbol}")
async def sec_ma_check(ticker_symbol: str):
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.data.sec_edgar import check_ticker_ma_activity
        activity = check_ticker_ma_activity(ticker_symbol)
        return {"ok": True, "data": activity}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/sec/filings/{ticker_symbol}")
async def sec_filings(ticker_symbol: str):
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.data.sec_edgar import get_recent_filings
        filings = get_recent_filings(ticker_symbol)
        return {"ok": True, "data": filings}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/sec/insider/{ticker_symbol}")
async def sec_insider(ticker_symbol: str):
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.data.sec_edgar import get_insider_trades
        trades = get_insider_trades(ticker_symbol)
        return {"ok": True, "data": trades}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Contracts
@web_app.get("/contracts/themes")
async def contracts_themes():
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.data.gov_contracts import get_contract_themes
        themes = get_contract_themes()
        return {"ok": True, "data": themes}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/contracts/recent")
async def contracts_recent():
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.data.gov_contracts import get_recent_contracts
        contracts = get_recent_contracts()
        return {"ok": True, "data": contracts}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/contracts/company/{ticker_symbol}")
async def contracts_company(ticker_symbol: str):
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.data.gov_contracts import get_company_contracts
        contracts = get_company_contracts(ticker_symbol)
        return {"ok": True, "data": contracts}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Patents
@web_app.get("/patents/themes")
async def patents_themes():
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.data.patents import get_patent_trends
        themes = get_patent_trends()
        return {"ok": True, "data": themes}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/patents/company/{ticker_symbol}")
async def patents_company(ticker_symbol: str):
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.data.patents import get_company_patents
        patents = get_company_patents(ticker_symbol)
        return {"ok": True, "data": patents}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Evolution
@web_app.get("/evolution/status")
async def evolution_status():
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.scoring.param_helper import get_learning_status
        status = get_learning_status()
        return {"ok": True, "data": status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/evolution/weights")
async def evolution_weights():
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.scoring.param_helper import get_scoring_weights
        weights = get_scoring_weights()
        return {"ok": True, "data": weights}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@web_app.get("/evolution/correlations")
async def evolution_correlations():
    return {"ok": True, "data": {"message": "Not yet implemented"}}


# Parameters
@web_app.get("/parameters/status")
async def parameters_status():
    import sys
    sys.path.insert(0, '/root')
    try:
        from src.scoring.param_helper import get_learning_status
        status = get_learning_status()
        return {"ok": True, "data": status}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Trades (stubs)
@web_app.get("/trades/positions")
async def trades_positions():
    return {"ok": True, "data": []}


@web_app.get("/trades/watchlist")
async def trades_watchlist():
    return {"ok": True, "data": []}


@web_app.get("/trades/activity")
async def trades_activity():
    return {"ok": True, "data": []}


@web_app.get("/trades/risk")
async def trades_risk():
    return {"ok": True, "data": {"risk_level": "low"}}


@web_app.get("/trades/journal")
async def trades_journal():
    return {"ok": True, "data": []}


@web_app.get("/trades/daily-report")
async def trades_daily_report():
    return {"ok": True, "data": {"message": "No trades today"}}


@web_app.get("/trades/scan")
async def trades_scan():
    return {"ok": True, "data": []}


@web_app.post("/trades/create")
async def trades_create():
    return {"ok": False, "error": "Trading not enabled"}


@web_app.get("/trades/{trade_id}")
async def trades_detail(trade_id: str):
    return {"ok": False, "error": "Trade not found"}


@web_app.post("/trades/{trade_id}/sell")
async def trades_sell(trade_id: str):
    return {"ok": False, "error": "Trading not enabled"}


@web_app.post("/sec/deals/add")
async def sec_deals_add():
    return {"ok": False, "error": "Not implemented"}


# =============================================================================
# MODAL DEPLOYMENT
# =============================================================================

@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("stock-api-keys")],
    keep_warm=1,  # Keep 1 container warm for faster response
)
@modal.asgi_app()
def fastapi_app():
    """
    Single Modal endpoint serving ALL routes via FastAPI.
    Bypasses 8 endpoint limit.
    """
    # Import FastAPI inside function (only available in container)
    from fastapi import FastAPI, Query
    from fastapi.middleware.cors import CORSMiddleware

    # Create app
    web_app = FastAPI(title="Stock Scanner API", version="2.0")

    # Add CORS
    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Note: All route definitions above will need to be moved here
    # or registered programmatically
    return web_app
