# CLAUDE.md — benchmark-notify-api

## Project Overview

A notification REST API built with FastAPI and SQLAlchemy. This is an Overwatch inner benchmark — agents implement code to make pre-seeded failing tests pass.

## Tech Stack

- **Python 3.11+**
- **FastAPI** — REST API framework
- **SQLAlchemy 2.0** — ORM with declarative models
- **Pydantic v2** — Request/response schemas
- **SQLite** — Database (in-memory for tests)
- **pytest + httpx** — Testing

## Architecture

```
models.py       → SQLAlchemy declarative models (Notification table)
database.py     → Engine, SessionLocal, Base, get_db dependency
repository.py   → Data access layer (CRUD operations on Notification)
service.py      → Business logic layer (calls repository)
schemas.py      → Pydantic request/response models
routes.py       → FastAPI router with REST endpoints
main.py         → FastAPI app, includes router
```

## Layer Dependencies

```
routes → schemas + service
service → repository + models
repository → models + database
models → database (Base)
```

## Commands

```bash
poetry install              # Install dependencies
poetry run pytest           # Run all tests
poetry run pytest tests/test_models.py -v   # Run specific test file
poetry run uvicorn notify_api.main:app --reload  # Dev server
```

## Conventions

- All models use SQLAlchemy 2.0 declarative style with `DeclarativeBase`
- Repository functions take a `Session` parameter (dependency injection)
- Service functions take a `Session` parameter
- Routes use FastAPI's `Depends(get_db)` for session management
- Pydantic schemas use `model_config = ConfigDict(from_attributes=True)`
- Use `datetime.utcnow` for timestamps
- Notification priorities: "low", "normal", "high", "critical"
- Notification table name: "notifications"

## Data Model

The `Notification` model has these fields:
- `id`: Integer, primary key, auto-increment
- `title`: String(255), not nullable
- `message`: Text, not nullable
- `priority`: String(20), default "normal"
- `role`: String(100), not nullable (which agent role this is for)
- `is_read`: Boolean, default False
- `created_at`: DateTime, defaults to utcnow
