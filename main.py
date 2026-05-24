"""Fly.io entrypoint: same idea as run_local.py but exposes ``app`` at
module level so a generic uvicorn ``main:app`` command can pick it up.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
WEB = ROOT / "web"

sys.path.insert(0, str(BACKEND))

os.environ.setdefault(
    "DATABASE_URL", f"sqlite+aiosqlite:///{ROOT / 'app.db'}"
)
# Default to same-origin only. To host the frontend on a separate
# domain, set ALLOWED_ORIGINS (comma-separated) in the environment
# explicitly — never default to "*", which would let any site call the
# API and read survey/payment payloads.
os.environ.setdefault("ALLOWED_ORIGINS", "")

from fastapi.staticfiles import StaticFiles  # noqa: E402

from api.main import app  # noqa: E402

app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")
