#!/usr/bin/env python3
"""
Tastytrade OAuth Token Helper

Run this script to get your refresh_token for the Tastytrade API.
It will open your browser, you'll log in, and it will display the token.

Usage:
    python scripts/get_tastytrade_token.py
"""

import http.server
import socketserver
import urllib.parse
import webbrowser
import requests
import sys

# Your OAuth credentials
CLIENT_ID = "e4ab4c6f-e702-4dcb-81e9-c986294d15ed"
CLIENT_SECRET = "445095f0aef5354c42cad0476a281baf126a0f45"

# OAuth endpoints
AUTH_URL = "https://api.tastytrade.com/oauth/authorize"
TOKEN_URL = "https://api.tastytrade.com/oauth/token"
REDIRECT_URI = "http://localhost:8000/callback"
SCOPES = "openid profile offline_access read trade account market_data"

# Store the authorization code
auth_code = None

class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global auth_code

        # Parse the callback URL
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/callback":
            # Extract the authorization code
            params = urllib.parse.parse_qs(parsed.query)

            if "code" in params:
                auth_code = params["code"][0]

                # Send success response
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                <html>
                <head><title>Success!</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: green;">Authorization Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
                """)
            else:
                error = params.get("error", ["Unknown error"])[0]
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"""
                <html>
                <head><title>Error</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: red;">Authorization Failed</h1>
                    <p>Error: {error}</p>
                </body>
                </html>
                """.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logging


def get_refresh_token():
    global auth_code

    print("\n" + "="*60)
    print("  TASTYTRADE OAUTH TOKEN HELPER")
    print("="*60)
    print(f"\nClient ID: {CLIENT_ID[:20]}...")
    print(f"Redirect URI: {REDIRECT_URI}")

    # Build authorization URL
    auth_params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    print("\n" + "-"*60)
    print("STEP 1: Opening browser for Tastytrade login...")
    print("-"*60)
    print(f"\nIf browser doesn't open, go to:\n{auth_url}\n")

    # Start local server to catch callback
    with socketserver.TCPServer(("", 8000), OAuthHandler) as httpd:
        print("Waiting for authorization (local server on port 8000)...")

        # Open browser
        webbrowser.open(auth_url)

        # Wait for callback
        while auth_code is None:
            httpd.handle_request()

    if not auth_code:
        print("\nERROR: No authorization code received")
        sys.exit(1)

    print("\n" + "-"*60)
    print("STEP 2: Exchanging code for tokens...")
    print("-"*60)

    # Exchange authorization code for tokens
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    try:
        response = requests.post(TOKEN_URL, data=token_data)
        response.raise_for_status()
        tokens = response.json()

        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")

        if refresh_token:
            print("\n" + "="*60)
            print("  SUCCESS! Here's your refresh token:")
            print("="*60)
            print(f"\nREFRESH_TOKEN:\n{refresh_token}\n")
            print("-"*60)
            print("\nAdd this to your Modal secrets (Stock_Story):")
            print("-"*60)
            print(f"""
TASTYTRADE_CLIENT_ID={CLIENT_ID}
TASTYTRADE_CLIENT_SECRET={CLIENT_SECRET}
TASTYTRADE_REFRESH_TOKEN={refresh_token}
""")
            print("-"*60)
            print("\nTo add secrets in Modal:")
            print("1. Go to: https://modal.com/secrets")
            print("2. Edit 'Stock_Story' secret")
            print("3. Add the three TASTYTRADE_* variables above")
            print("4. Redeploy: modal deploy modal_api_v2.py")
            print("-"*60)

            # Also save to a file for convenience
            with open("tastytrade_credentials.txt", "w") as f:
                f.write(f"TASTYTRADE_CLIENT_ID={CLIENT_ID}\n")
                f.write(f"TASTYTRADE_CLIENT_SECRET={CLIENT_SECRET}\n")
                f.write(f"TASTYTRADE_REFRESH_TOKEN={refresh_token}\n")
            print("\nCredentials also saved to: tastytrade_credentials.txt")
            print("(Delete this file after adding to Modal secrets!)")

        else:
            print("\nERROR: No refresh token in response")
            print(f"Response: {tokens}")

    except requests.exceptions.RequestException as e:
        print(f"\nERROR: Failed to exchange code for tokens")
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    get_refresh_token()
