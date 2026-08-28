"""`kontakt_suchen` muss LIKE-Sonderzeichen (% und _) im Suchbegriff als
Literalzeichen behandeln — sonst würde z. B. ein Name/eine Mailadresse mit
einem zufälligen '%' oder '_' die Suchsemantik verfälschen (Platzhalter
statt Literal), obwohl der Suchbegriff selbst aus der LLM-Extraktion einer
externen Mail stammt und nicht kontrolliert werden kann."""

from contextlib import contextmanager

from sqlmodel import Session

from app.agent import tools
from app.models import Kontakt, KontaktRolle
from tests.conftest import engine


@contextmanager
def _temporaerer_kontakt(name: str, email: str):
    """Andere Tests (z. B. test_stammdaten_api.py) zählen exakt die Anzahl
    der Seed-Kontakte — Testdaten hier müssen daher wieder entfernt werden,
    nicht in der gemeinsamen, sessionweiten DB (siehe conftest.py) hängen
    bleiben."""
    with Session(engine) as session:
        kontakt = Kontakt(name=name, rolle=KontaktRolle.mieter, email=email)
        session.add(kontakt)
        session.commit()
        session.refresh(kontakt)
        try:
            yield session
        finally:
            frisch = session.get(Kontakt, kontakt.id)
            if frisch is not None:
                session.delete(frisch)
                session.commit()


def test_prozentzeichen_im_suchbegriff_matcht_nicht_beliebige_zeichenfolge():
    # Bewusst KEIN exakter Treffer in den Testdaten: ohne Escaping würde
    # "%" als Beliebige-Zeichenfolge-Platzhalter fälschlich auf
    # "50XYZ Rabatt GmbH" matchen — mit Escaping (Fix) darf hier gar kein
    # Treffer entstehen.
    with _temporaerer_kontakt("50XYZ Rabatt GmbH", "x@example.test") as session:
        treffer = tools.kontakt_suchen(session, "50% Rabatt")
        assert treffer is None


def test_findet_kontakt_mit_prozentzeichen_im_namen_bei_exaktem_treffer():
    with _temporaerer_kontakt("50% Rabatt GmbH", "fifty@example.test") as session:
        treffer = tools.kontakt_suchen(session, "50% Rabatt")
        assert treffer is not None
        assert treffer.name == "50% Rabatt GmbH"


def test_unterstrich_im_suchbegriff_matcht_nicht_beliebiges_zeichen():
    # Bewusst KEIN exakter Treffer in den Testdaten: ohne Escaping würde
    # "_" als Einzelzeichen-Platzhalter fälschlich auf "MaxXMustermann"
    # matchen — mit Escaping (Fix) darf hier gar kein Treffer entstehen.
    with _temporaerer_kontakt("MaxXMustermann", "maxx@example.test") as session:
        treffer = tools.kontakt_suchen(session, "Max_Mustermann")
        assert treffer is None


def test_findet_kontakt_unabhaengig_von_gross_kleinschreibung():
    # .ilike() statt .like() — SQLite ist bei LIKE ohnehin schon
    # case-insensitiv (dieser Test würde also auch ohne den Fix grün
    # sein), Postgres (Prod) dagegen nicht: der Fix garantiert dasselbe
    # Verhalten dialektübergreifend, siehe Kommentar in tools.py.
    with _temporaerer_kontakt("Erika Musterfrau", "ERIKA.MUSTERFRAU@EXAMPLE.TEST") as session:
        treffer = tools.kontakt_suchen(session, "erika.musterfrau@example.test")
        assert treffer is not None
        assert treffer.name == "Erika Musterfrau"
