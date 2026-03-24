"""One-command launcher for API server and dashboard."""
from __future__ import annotations

import os
import webbrowser

import uvicorn


def main() -> None:
    dashboard_url = "http://127.0.0.1:8000/dashboard"
    print("=" * 60)
    print("SMART GRID LIVE DEMO")
    print("=" * 60)
    print("1) Generate data first if needed: python run_simulation_fast.py")
    print("2) API docs: http://127.0.0.1:8000/docs")
    print("3) Dashboard: http://127.0.0.1:8000/dashboard")
    print("=" * 60)

    if os.environ.get("NO_BROWSER", "0") != "1":
        webbrowser.open(dashboard_url)

    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
