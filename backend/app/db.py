from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# Kleiner, expliziter Pool statt SQLAlchemys Default (5 + 10 Overflow =
# bis zu 15 Verbindungen PRO laufendem Container): Clever-Cloud-Deploys
# laufen blue/green (der alte Container bleibt aktiv, während der neue
# gebaut wird) — mit dem Default hat allein der alte Container schon das
# knappe Verbindungslimit eines kleinen Postgres-Plans (z. B. DEV)
# ausgeschöpft, sodass die Migration des neuen Deploys keine Verbindung
# mehr bekommt. pool_pre_ping fängt vom DB-Server gekappte Verbindungen ab.
_ist_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if _ist_sqlite else {}
pool_kwargs = {} if _ist_sqlite else {"pool_size": 2, "max_overflow": 2, "pool_pre_ping": True}
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
