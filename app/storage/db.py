import os
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

def _normalize_pg_url(url: str) -> str:
    # Force SQLAlchemy to use Psycopg 3 driver
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url  # already has a driver or is something else

def _build_sync_url() -> str:
    load_dotenv(find_dotenv(), override=False)
    url = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL_SYNC (or DATABASE_URL) is not set")
    return _normalize_pg_url(url)

SYNC_URL = _build_sync_url()

engine = create_engine(SYNC_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

class Base(DeclarativeBase):
    pass
