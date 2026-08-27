"""`objekt_suchen` muss Schreibvarianten (ß vs. ss, Groß-/Kleinschreibung)
normalisiert vergleichen — sonst findet z. B. eine Mail mit 'Musterstrasse'
das in den Stammdaten mit 'Musterstraße' hinterlegte Objekt nicht."""

from sqlmodel import Session

from app.agent import tools
from tests.conftest import engine


def test_findet_objekt_trotz_ss_statt_eszett():
    with Session(engine) as session:
        treffer = tools.objekt_suchen(session, "Musterstrasse 5")
    assert len(treffer) == 1
    assert treffer[0].bezeichnung == "Liegenschaft Musterstraße 5"


def test_findet_objekt_trotz_eszett_statt_ss_in_suchbegriff():
    with Session(engine) as session:
        treffer = tools.objekt_suchen(session, "Ringstraße 21")
    assert len(treffer) == 1
    assert treffer[0].bezeichnung == "Liegenschaft Ringstraße 21"


def test_findet_objekt_case_insensitiv():
    with Session(engine) as session:
        treffer = tools.objekt_suchen(session, "AM KANAL 8")
    assert len(treffer) == 1
    assert treffer[0].bezeichnung == "Liegenschaft Am Kanal 8"


def test_kein_treffer_bei_unbekannter_adresse():
    with Session(engine) as session:
        treffer = tools.objekt_suchen(session, "Nirgendwo 99")
    assert treffer == []
