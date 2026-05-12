"""Create a fresh preview invite for local development.

Each run wipes prior PREVIEW invites (and all their decisions/events/answers via
ON DELETE CASCADE) and inserts a new one. Prints the candidate URL; optional
flags copy it to the clipboard or open it directly in Chrome incognito.

Usage:
    cd backend && .venv/bin/python preview.py
    cd backend && .venv/bin/python preview.py --copy
    cd backend && .venv/bin/python preview.py --open
    cd backend && .venv/bin/python preview.py --base https://your-deploy.up.railway.app
"""
from __future__ import annotations

import argparse
import secrets
import subprocess
import sys

from supabase_client import get_supabase


PREVIEW_LABEL = "__PREVIEW__"
DEFAULT_BASE = "http://localhost:5173"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE,
                        help="Base URL of the frontend (default: http://localhost:5173)")
    parser.add_argument("--copy", action="store_true", help="Copy URL to macOS clipboard")
    parser.add_argument("--open", action="store_true", help="Open URL in Chrome incognito")
    args = parser.parse_args()

    sb = get_supabase()

    # Wipe prior preview invites + cascade (decisions, events, quiz answers).
    sb.table("candidates").delete().eq("invited_label", PREVIEW_LABEL).execute()

    token = secrets.token_urlsafe(24)
    sb.table("candidates").insert({
        "invite_token": token,
        "invited_label": PREVIEW_LABEL,
        "invited_label_email": "preview@local.test",
    }).execute()

    url = f"{args.base.rstrip('/')}/test/{token}"
    print(url)

    if args.copy:
        try:
            subprocess.run("pbcopy", input=url.encode(), check=False)
            print("(copied to clipboard)", file=sys.stderr)
        except Exception as e:
            print(f"(pbcopy failed: {e})", file=sys.stderr)

    if args.open:
        try:
            subprocess.run([
                "open", "-na", "Google Chrome", "--args",
                "--incognito", url,
            ], check=False)
        except Exception as e:
            print(f"(open failed: {e})", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
