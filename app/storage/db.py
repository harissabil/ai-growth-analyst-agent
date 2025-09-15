import os

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _build_sync_url() -> str:
    """
    Use Render's sync DSN from env and normalize the driver.
    Prefer DATABASE_URL_SYNC; fallback to DATABASE_URL.
    """
    load_dotenv(find_dotenv(), override=False)
    url = os.getenv("DATABASE_URL_SYNC")

    return url


SYNC_URL = _build_sync_url()

# Pure sync engine + session
engine = create_engine(SYNC_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


class Base(DeclarativeBase):
    pass
