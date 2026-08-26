"""Gemeinsame Test-Infrastruktur: eine In-Memory-SQLite-Engine für die
gesamte Testsuite, damit alle Testdateien dieselbe `get_session`-Overrides
auf dem einen FastAPI-`app`-Singleton teilen (sonst gewinnt beim Import
zufällig die zuletzt importierte Datei — mit potenziell nicht
initialisierten Tabellen)."""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.db import get_session
from app.main import app
from app.models import Dokument
from app.routers.postfach import get_dokumenten_index
from app.seed import seed
from tests.fakes import fake_dokumenten_index

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def _get_session_override():
    with Session(engine, expire_on_commit=False) as session:
        yield session


app.dependency_overrides[get_session] = _get_session_override

# §16 Phase 5 / §0: In-Memory-Index + Fake-Embedding statt des echten
# Chroma-Modells — hält die Testsuite netzwerkfrei.
_test_index = fake_dokumenten_index()
app.dependency_overrides[get_dokumenten_index] = lambda: _test_index


@pytest.fixture(scope="session", autouse=True)
def _datenbank_aufsetzen():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)
        _test_index.indizieren(list(session.exec(select(Dokument)).all()))
    yield
