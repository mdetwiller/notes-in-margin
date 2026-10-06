from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import get_config

config = get_config()

# Read-only connection to the Cortico snapshot. Opened with mode=ro&immutable=1 so the
# OS/SQLite layer itself refuses writes — this is not just a convention, there is no write
# path through this engine at all. See docs/prototype-log.md.
cortico_engine = create_engine(
    f"sqlite:///file:{config.cortico_db_abspath}?mode=ro&immutable=1&uri=true",
    connect_args={"check_same_thread": False},
)


@event.listens_for(cortico_engine, "connect")
def _enforce_query_only(dbapi_connection, _record):
    dbapi_connection.execute("PRAGMA query_only = ON;")


CorticoSession = sessionmaker(bind=cortico_engine, autoflush=False, autocommit=False)
CorticoBase = declarative_base()

# Separate, read-write database for everything this prototype owns.
prototype_engine = create_engine(
    f"sqlite:///{config.prototype_db_abspath}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(prototype_engine, "connect")
def _enable_foreign_keys(dbapi_connection, _record):
    dbapi_connection.execute("PRAGMA foreign_keys = ON;")


PrototypeSession = sessionmaker(bind=prototype_engine, autoflush=False, autocommit=False)
PrototypeBase = declarative_base()


def get_cortico_db():
    db: Session = CorticoSession()
    try:
        yield db
    finally:
        db.close()


def get_prototype_db():
    db: Session = PrototypeSession()
    try:
        yield db
    finally:
        db.close()
