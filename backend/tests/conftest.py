"""Gemeinsame Test-Infrastruktur: eine In-Memory-SQLite-Engine für die
gesamte Testsuite, damit alle Testdateien dieselbe `get_session`-Overrides
auf dem einen FastAPI-`app`-Singleton teilen (sonst gewinnt beim Import
zufällig die zuletzt importierte Datei — mit potenziell nicht
initialisierten Tabellen)."""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.auth import aktueller_benutzer
from app.db import get_session
from app.main import app
from app.models import Benutzer, BenutzerRolle, Dokument
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

# Login/Session ist eigenes Test-Thema (tests/test_auth.py, mit echten
# Requests gegen /api/auth/*) — alle anderen Tests wollen unbehelligt von
# der Rollen-Prüfung die eigentliche Fachlogik testen, daher hier pauschal
# als eingeloggter Admin überschrieben (Admin, nicht User, damit auch die
# admin_erforderlich-Endpunkte wie das Fall-Löschen ohne Extra-Setup
# funktionieren).
_TEST_BENUTZER = Benutzer(
    id=0, name="Test-Admin", email="test-admin@example.test", passwort_hash="", rolle=BenutzerRolle.admin
)
app.dependency_overrides[aktueller_benutzer] = lambda: _TEST_BENUTZER

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
