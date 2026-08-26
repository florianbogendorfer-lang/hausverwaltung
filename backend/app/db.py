from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    # expire_on_commit=False: der Agent-Loop führt pro Request mehrere
    # Commits aus (Fall, Aktionen, Traces, Nachrichten). Mit dem Default
    # würde jedes weitere Commit bereits zurückgegebene Objekte (z. B. den
    # Fall) für die Response-Serialisierung entwerten.
    with Session(engine, expire_on_commit=False) as session:
        yield session
