# Database engine, session, Base — to be implemented by data-layer-engineer
#
# Minimal stubs so tests can import and fail on assertions (not import errors).
# The data-layer-engineer should replace this entire file with a real implementation.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency that yields a database session. Stub — replace with real implementation."""
    raise NotImplementedError("get_db not implemented")
