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
import json
import os
import secrets
import shutil
import socketserver
import subprocess
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ppcway.ads.oauth import consent_url, exchange_code

#: The deployment is the source of truth for which OAuth client we are. A local
#: .env can hold a stale one from an older project, and asking Google with the
#: wrong client produces a redirect mismatch that looks exactly like an
#: unregistered URI. That cost an afternoon, so the deployment is asked first.
PROJECT = "ppcway-509313"
REGION = "northamerica-northeast2"
SERVICE = "ppcway-api"
SECRET = "ppcway-oauth-client-secret"

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


def gcloud_path() -> str:
    """Where gcloud is, including the install the shell does not know about."""
    found = shutil.which("gcloud")
    if found:
        return found
    bundled = Path.home() / "google-cloud-sdk" / "bin" / "gcloud"
    return str(bundled) if bundled.exists() else ""


def gcloud(*args: str) -> str:
    """One value out of gcloud, with the caller's own credentials."""
    binary = gcloud_path()
    if not binary:
        return ""
    try:
        done = subprocess.run(
            [binary, *args], capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def deployed_client_id() -> str:
    """Which OAuth client the running service is, in its own words."""
    out = gcloud(
        "run",
        "services",
        "describe",
        SERVICE,
        f"--project={PROJECT}",
        f"--region={REGION}",
        "--format=json",
    )
    if not out:
        return ""
    container = json.loads(out)["spec"]["template"]["spec"]["containers"][0]
    for entry in container.get("env", []):
        if entry.get("name") == "GOOGLE_OAUTH_CLIENT_ID":
            return str(entry.get("value", ""))
    return ""


def main() -> int:
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip() or deployed_client_id()
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip() or gcloud(
        "secrets", "versions", "access", "latest", f"--secret={SECRET}", f"--project={PROJECT}"
    )
    if not (client_id and client_secret):
        print("Could not read the OAuth client from the deployment. Is gcloud signed in?")
        return 1
    print(f"\n  Asking as {client_id}")

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
    # Never printed. A terminal is shared with more things than its owner
    # expects, and a refresh token read once is a refresh token to be replaced.
    out = Path.home() / ".ppcway-house-token"
    out.touch(mode=0o600, exist_ok=True)
    out.chmod(0o600)
    out.write_text(grant.refresh_token)
    print(f"\nWritten to {out} (readable only by you). Store it, then delete it:\n")
    print(
        f"  gcloud secrets create ppcway-ads-house-token --data-file={out}"
        f" --project={PROJECT} && rm -P {out}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
