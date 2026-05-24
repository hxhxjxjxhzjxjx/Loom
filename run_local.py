"""Local launcher for Lira: serves the FastAPI app + prebuilt web bundle
on a single port so the whole product is reachable at http://127.0.0.1:8000

Equivalent to what nginx does in production (install.sh), minus rate
limiting and security headers.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
WEB = ROOT / "web"

# Make `import bot.*` / `import api.*` work.
sys.path.insert(0, str(BACKEND))

# Default to a local writable SQLite path so we don't need /var/lib/lira.
os.environ.setdefault(
    "DATABASE_URL", f"sqlite+aiosqlite:///{ROOT / 'app.db'}"
)
os.environ.setdefault("API_HOST", "127.0.0.1")
os.environ.setdefault("API_PORT", "8000")
os.environ.setdefault("ALLOWED_ORIGINS", "")

from fastapi.staticfiles import StaticFiles  # noqa: E402

from api.main import app  # noqa: E402

# Routes registered with @app.get/post above run first; this mount is a
# catch-all for the SPA shell + Expo bundle.
app.mount("/", StaticFiles(directory=str(WEB), html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ["API_HOST"],
        port=int(os.environ["API_PORT"]),
        log_level="info",
    )
