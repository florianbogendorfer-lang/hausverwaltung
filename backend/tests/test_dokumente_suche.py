from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.agent.tools import dokumente_durchsuchen
from app.models import Dokument
from app.seed import seed
from tests.fakes import fake_dokumenten_index


def _aufsetzen():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    seed(session)
    index = fake_dokumenten_index()
    index.indizieren(list(session.exec(select(Dokument)).all()))
    return session, index


def test_suche_liefert_kostenregelung_bei_passender_anfrage():
    session, index = _aufsetzen()
    treffer = dokumente_durchsuchen(session, index, "Kostenregelung Reparaturen Schlosser", top_k=1)
    assert len(treffer) == 1
    assert "Kostenregelung" in treffer[0].titel


def test_suche_ist_nach_relevanz_sortiert_und_begrenzt():
    session, index = _aufsetzen()
    treffer = dokumente_durchsuchen(session, index, "Hausordnung Instandhaltung Meldungen", top_k=2)
    assert 1 <= len(treffer) <= 2
    titel = [d.titel for d in treffer]
    assert any("Hausordnung" in t for t in titel)


def test_index_ohne_dokumente_liefert_leere_liste():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    index = fake_dokumenten_index()
    assert dokumente_durchsuchen(session, index, "irgendeine Frage") == []
