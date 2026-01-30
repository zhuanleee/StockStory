#!/usr/bin/env python3
"""
Modal.com API Server - Web Endpoints for Dashboard

Provides REST API endpoints for the dashboard to access scan results.
Replaces Digital Ocean API server.
"""

import modal
from datetime import datetime
from pathlib import Path
import json
from typing import Optional

# Create Modal app
app = modal.App("stock-scanner-api")

# Create persistent volume for storing scan results
volume = modal.Volume.from_name("scan-results", create_if_missing=True)

# Mount path for volume
VOLUME_PATH = "/data"

# Same image as scanner + FastAPI for web endpoints
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .pip_install("fastapi[standard]")  # Required for web endpoints
    .add_local_dir("src", remote_path="/root/src")
    .add_local_dir("config", remote_path="/root/config")
)


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
# API ENDPOINTS
# =============================================================================

@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("stock-api-keys")],
)
@modal.fastapi_endpoint(method="GET")
def health():
    """
    Health check endpoint
    GET /health
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "modal-stock-scanner",
        "version": "2.0"
    }


@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("stock-api-keys")],
)
@modal.fastapi_endpoint(method="GET")
def scan():
    """
    Get latest scan results
    GET /scan

    Returns:
        {
            "status": "success",
            "timestamp": "2024-01-30T14:00:00",
            "total": 500,
            "results": [...]
        }
    """
    results = load_scan_results()

    if not results:
        return {
            "status": "no_data",
            "message": "No scan results available yet. Run a scan first.",
            "results": []
        }

    return results


@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("stock-api-keys")],
)
@modal.fastapi_endpoint(method="GET")
def ticker(ticker_symbol: str):
    """
    Get specific ticker data
    GET /ticker/:ticker

    Args:
        ticker_symbol: Stock ticker (e.g., NVDA)

    Returns:
        Ticker details from latest scan
    """
    results = load_scan_results()

    if not results:
        return {
            "error": "No scan data available",
            "ticker": ticker_symbol
        }

    # Find ticker in results
    ticker_upper = ticker_symbol.upper()
    for stock in results.get('results', []):
        if stock.get('ticker', '').upper() == ticker_upper:
            return {
                "status": "success",
                "ticker": ticker_symbol,
                "data": stock
            }

    return {
        "error": "Ticker not found in scan results",
        "ticker": ticker_symbol
    }


@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("stock-api-keys")],
    timeout=600,  # 10 minutes for manual scans
)
@modal.fastapi_endpoint(method="POST")
def scan_trigger(mode: str = "quick"):
    """
    Trigger a new scan
    POST /scan/trigger?mode=quick

    Args:
        mode: 'quick' (20 stocks) or 'full' (500 stocks)

    Returns:
        {
            "status": "started",
            "mode": "quick",
            "estimated_time": 120
        }
    """
    from modal_scanner import daily_scan, scan_stock_with_ai_brain

    if mode == "quick":
        # Quick scan: 20 stocks
        tickers = [
            'NVDA', 'AMD', 'AVGO', 'TSM', 'MSFT',
            'GOOGL', 'META', 'AAPL', 'TSLA', 'PLTR',
            'CRWD', 'NET', 'SNOW', 'DDOG', 'S',
            'VST', 'CEG', 'LLY', 'NVO', 'LMT'
        ]
        estimated_time = 12  # 2 batches × 6 seconds
    else:
        # Full scan: Get universe
        try:
            import sys
            sys.path.insert(0, '/root')
            from src.data.universe_manager import get_universe_manager
            um = get_universe_manager()
            tickers = um.get_scan_universe(use_polygon_full=False, min_market_cap=300_000_000)
            estimated_time = int(len(tickers) / 10 * 6)  # batches × 6 seconds
        except Exception as e:
            return {
                "error": f"Failed to get universe: {e}",
                "status": "error"
            }

    # Trigger scan asynchronously
    print(f"Starting {mode} scan of {len(tickers)} stocks...")

    try:
        # Run scan in background
        results = list(scan_stock_with_ai_brain.map(tickers))

        # Save results
        successful = [r for r in results if r and 'error' not in r]

        scan_data = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "total": len(tickers),
            "successful": len(successful),
            "failed": len(tickers) - len(successful),
            "results": successful
        }

        # Save to volume
        filename = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(VOLUME_PATH) / filename

        with open(filepath, 'w') as f:
            json.dump(scan_data, f, indent=2)

        volume.commit()  # Persist to volume

        print(f"✅ Scan complete: {len(successful)}/{len(tickers)} successful")

        return {
            "status": "completed",
            "mode": mode,
            "total": len(tickers),
            "successful": len(successful),
            "failed": len(tickers) - len(successful),
            "duration": estimated_time,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"❌ Scan failed: {e}")
        import traceback
        traceback.print_exc()

        return {
            "status": "error",
            "error": str(e),
            "mode": mode
        }


# =============================================================================
# WEBHOOK FOR TELEGRAM NOTIFICATIONS
# =============================================================================

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("stock-api-keys")],
)
def send_telegram_notification(message: str):
    """
    Send notification to Telegram

    Called after daily scans complete
    """
    import os
    import requests

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("⚠️  Telegram not configured")
        return False

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            print(f"✅ Telegram notification sent")
            return True
        else:
            print(f"❌ Telegram failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False


# =============================================================================
# MAIN ENTRYPOINT
# =============================================================================

@app.local_entrypoint()
def main():
    """
    Deploy API endpoints

    Usage:
        modal deploy modal_api.py
    """
    print("🚀 Deploying Modal API endpoints...")
    print("")
    print("Available endpoints:")
    print("  GET  /health")
    print("  GET  /scan")
    print("  GET  /ticker/:ticker")
    print("  POST /scan/trigger?mode=quick")
    print("")
    print("✅ Deploy complete!")
