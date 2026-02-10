# benchmark-notify-api

Inner benchmark for [Overwatch](https://github.com/TobiahRex/overwatch) multi-agent orchestration.

## What This Tests

Can the Overwatch agent team collectively ship a working notification API through a real git workflow (branches, PRs, CI, merges)?

## Benchmark

- **20 pre-seeded failing tests** define the contract
- Agents implement code to make them pass
- **Score** = passing tests / 20 on `main` after all PRs merge

## Architecture

```
FastAPI REST API
├── models.py       → SQLAlchemy Notification model
├── database.py     → Engine + session management
├── repository.py   → CRUD data access
├── service.py      → Business logic
├── schemas.py      → Pydantic request/response
├── routes.py       → REST endpoints
└── main.py         → App entrypoint
```

## Running Tests

```bash
poetry install
poetry run pytest tests/ -v
```
