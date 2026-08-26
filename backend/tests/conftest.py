"""Gemeinsame Test-Infrastruktur: eine In-Memory-SQLite-Engine für die
gesamte Testsuite, damit alle Testdateien dieselbe `get_session`-Overrides
auf dem einen FastAPI-`app`-Singleton teilen (sonst gewinnt beim Import
zufällig die zuletzt importierte Datei — mit potenziell nicht
initialisierten Tabellen)."""

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import get_session
from app.main import app
from app.seed import seed

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def _get_session_override():
    with Session(engine, expire_on_commit=False) as session:
        yield session


app.dependency_overrides[get_session] = _get_session_override


@pytest.fixture(scope="session", autouse=True)
def _datenbank_aufsetzen():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
    yield
