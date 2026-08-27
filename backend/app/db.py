from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# Kein Connection-Pool für Postgres: selbst ein knapp bemessener Pool
# (zuvor pool_size=2/max_overflow=2, max. 4 Verbindungen) hat das
# Verbindungslimit eines kleinen Postgres-Plans (z. B. Clever-Cloud-DEV)
# schon unter gewöhnlicher Last (ein paar parallele GETs eines einzigen
# Browser-Tabs) ausgeschöpft — "too many connections for role". Mit
# NullPool wird pro Request eine frische Verbindung geöffnet und beim
# Schließen der Session sofort wieder freigegeben (keine Verbindung wird
# im Leerlauf gehalten): der DB-seitige Fußabdruck entspricht damit immer
# genau der Zahl der gerade tatsächlich laufenden Requests, nie einer
# stehenden Reserve. Etwas mehr Verbindungs-Overhead pro Request, für
# diesen Traffic (wenige Bearbeiter) unerheblich.
_ist_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if _ist_sqlite else {}
pool_kwargs = {} if _ist_sqlite else {"poolclass": NullPool}
engine = create_engine(settings.database_url, connect_args=connect_args, **pool_kwargs)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    # expire_on_commit=False: der Agent-Loop führt pro Request mehrere
    # Commits aus (Fall, Aktionen, Traces, Nachrichten). Mit dem Default
    # würde jedes weitere Commit bereits zurückgegebene Objekte (z. B. den
    # Fall) für die Response-Serialisierung entwerten.
    with Session(engine, expire_on_commit=False) as session:
        yield session
