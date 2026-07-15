# Installation Guide

## Prerequisites

- Windows 10/11 (this project was built and tested there) or Linux
- Python 3.10 (the project's `.venv` was built against 3.10.11 — other 3.10.x
  should work; not tested on 3.11+)
- ~3 GB disk for the venv + PyTorch

## Local installation (no Docker)

```powershell
cd smartgrid_simulation
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

Copy the environment template and edit as needed:

```powershell
copy ..\.env.example .env
```

At minimum for local development, the defaults in `.env.example` work
unmodified — only change `SGRID_JWT_SECRET_KEY` before anything beyond
`localhost`.

## Verify the installation

```powershell
.\.venv\Scripts\python.exe -m pytest production\tests\ -q
```

Expect `46 passed`. If any test fails, check `production/config/settings.py`
loaded correctly (`.\.venv\Scripts\python.exe -c "from production.config.settings import get_settings; print(get_settings())"`).

## Run the server

```powershell
.\.venv\Scripts\python.exe api_server.py
```

Then open:
- Dashboard: http://127.0.0.1:8000/dashboard
- API docs (OpenAPI): http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## Default accounts (development only — see `operator_manual.md` to change them)

| Username | Password | Role |
|---|---|---|
| admin | `ChangeMe-Admin-2026!` | administrator |
| operator | `ChangeMe-Operator-2026!` | grid_operator |
| analyst | `ChangeMe-Analyst-2026!` | analyst |
| viewer | `ChangeMe-Viewer-2026!` | viewer |

## Docker installation

See `deployment_guide.md` — requires Docker Desktop (Windows) or Docker
Engine + Compose plugin (Linux). **Not verified in this environment** (Docker
was not installed on the development machine); Dockerfiles/compose were
validated by static review, path-existence checks, and YAML linting only.
Run the smoke test in `deployment_guide.md` on a Docker-enabled machine
before relying on it.
