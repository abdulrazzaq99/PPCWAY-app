"""Mint the permission PPCWay uses to ask Keyword Planner, once.

The free audit's money line needs a Google Ads account to ask from, and the
stranger running that audit has not given us one. So PPCWay holds a permission
to its own account, and only for this: asking what a trade is worth in a town.
No merchant's account is read with it and nothing is spent through it.

Run once, from a machine with a browser:

    GOOGLE_OAUTH_CLIENT_ID=... GOOGLE_OAUTH_CLIENT_SECRET=... \
        .venv/bin/python scripts/house_permission.py

It prints a refresh token. Put it straight into Secret Manager, clear the
terminal, and never commit it.
"""

from __future__ import annotations

import http.server
import os
import secrets
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ppcway.ads.oauth import consent_url, exchange_code

PORT = 8787
REDIRECT = f"http://localhost:{PORT}/oauth"
came_back: dict[str, str] = {}


class Doorbell(http.server.BaseHTTPRequestHandler):
    """Catches the one redirect Google sends back, and nothing else."""

    def do_GET(self) -> None:
        query = urllib.parse.urlparse(self.path).query
        code = urllib.parse.parse_qs(query).get("code", [""])[0]
        if code:
            came_back["code"] = code
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<h2>Done. Close this tab and look at the terminal.</h2>"
            if code
            else b"<h2>No code came back. Try again.</h2>"
        )

    def log_message(self, *args: object) -> None:
        return


def main() -> int:
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    if not (client_id and client_secret):
        print("Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in the environment.")
        return 1

    print(f"\n  Register {REDIRECT} as an authorised redirect URI first.")
    print("  Then sign in as the Google account that owns PPCWay's Google Ads account.\n")

    url = consent_url(client_id=client_id, redirect_uri=REDIRECT, state=secrets.token_urlsafe(16))
    with socketserver.TCPServer(("127.0.0.1", PORT), Doorbell) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        webbrowser.open(url)
        print(f"If no browser opened, visit:\n\n{url}\n")
        while "code" not in came_back:
            server.handle_request()
        server.shutdown()

    grant = exchange_code(
        came_back["code"],
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=REDIRECT,
    )
    print("\nRefresh token follows. Store it, then clear this terminal.\n")
    print(grant.refresh_token)
    print(
        "\n  printf %s '<token>' | gcloud secrets create ppcway-ads-house-token"
        " --data-file=- --project=ppcway-509313\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
