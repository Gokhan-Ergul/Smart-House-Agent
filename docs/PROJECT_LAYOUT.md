# Project layout (what each part is for)

This repo root is organized so the **active code** lives in `src/`, **tests** in `tests/`, the **local device API mock** in `app/`, and **documentation** in `docs/`.

## Active paths (use these)

| Path | Purpose |
|------|---------|
| **`src/smart_house_agent/`** | Main Python package: config, LangGraph graphs, agents, tools, persistence, CLI (`python -m smart_house_agent.main`). |
| **`tests/`** | `pytest` suite; mocks for HTTP and filesystem where relevant. |
| **`app/main.py`** | FastAPI server that simulates device state (`/status`, `/update_device`) and reads/writes `home_status.json` using the same paths as `config.py`. |
| **`pyproject.toml`** | Package metadata, editable install, pytest `pythonpath` for `src/`. |
| **`requirements.txt`** | Canonical pinned dependencies for the project (install into a venv). |
| **`.env.example`** | Template for environment variables (`GOOGLE_API_KEY`, `SMART_HOUSE_API_URL`, optional paths). Copy to `.env` locally (never commit `.env`). |
| **`README.md`** | Project overview and usage. |

## Runtime / local data (at repo root by default)

These files are **created or updated** while the app runs. Paths can be overridden via env (see `.env.example`).

| File | Purpose |
|------|---------|
| **`home_status.json`** | Current simulated device states (shared with `app/main.py` and the agent). |
| **`user_memory.txt`** | Long-term user memory text from the user-memory agent. |
| **`rules_operations.json`** | Automation rules and named operations for the rule-keeper agent. |

You may add these to `.gitignore` if you do not want local state in Git.

## Documentation

| Path | Purpose |
|------|---------|
| **`docs/`** | Extra documentation (this layout guide and any future guides). |

## Quick mental model

```text
┌─────────────────────────────────────────────────────────────┐
│  CLI / library:  src/smart_house_agent  →  Gemini + graphs  │
│                         │                                    │
│                         ▼                                    │
│              HTTP (optional)  →  app/main.py (FastAPI mock)   │
│                         │                                    │
│                         ▼                                    │
│              JSON files at repo root (device state, rules)   │
└─────────────────────────────────────────────────────────────┘
```
