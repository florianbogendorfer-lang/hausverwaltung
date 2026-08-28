"""Löschen von Objekt/Kontakt/Dienstleister muss abgelehnt werden, solange
ein Fall darauf verweist — sonst würde SQLite (Dev/Tests) den Verweis
klaglos verwaisen lassen und Postgres (Prod) mit einem harten
IntegrityError/500 statt einer verständlichen Fehlermeldung abbrechen.

Aufräumen ist hier bewusst explizit (nicht nur "möglichst"): andere Tests
(tests/test_stammdaten_api.py) zählen exakt die Anzahl der Seed-Objekte/
-Kontakte/-Dienstleister auf der gemeinsamen, sessionweiten Test-DB (siehe
conftest.py) — ohne Aufräumen wären diese Zählungen nur durch die
zufällige alphabetische Dateireihenfolge korrekt, nicht durch echte
Testisolation."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models import Dienstleister, Fall, FallStatus, FallTyp, Gewerk, Kontakt, KontaktRolle, Objekt
from tests.conftest import engine

client = TestClient(app)


def _aufraeumen(modell, id_: int | None) -> None:
    if id_ is None:
        return
    with Session(engine) as session:
        instanz = session.get(modell, id_)
        if instanz is not None:
            session.delete(instanz)
            session.commit()


def _objekt() -> int:
    with Session(engine) as session:
        objekt = Objekt(bezeichnung="Referenztest-Objekt", adresse="Teststraße 1")
        session.add(objekt)
        session.commit()
        session.refresh(objekt)
        return objekt.id


def _kontakt(objekt_id: int | None = None) -> int:
    with Session(engine) as session:
        kontakt = Kontakt(
            name="Referenztest-Kontakt",
            rolle=KontaktRolle.mieter,
            email="referenztest@example.test",
            objekt_id=objekt_id,
        )
        session.add(kontakt)
        session.commit()
        session.refresh(kontakt)
        return kontakt.id


def _dienstleister() -> int:
    with Session(engine) as session:
        dienstleister = Dienstleister(
            name="Referenztest-Dienstleister", gewerk=Gewerk.schlosser, email="dl@example.test"
        )
        session.add(dienstleister)
        session.commit()
        session.refresh(dienstleister)
        return dienstleister.id


def _fall(**kwargs) -> int:
    with Session(engine) as session:
        fall = Fall(
            typ=FallTyp.reparaturmeldung, betreff="Referenztest-Fall", status=FallStatus.neu, **kwargs
        )
        session.add(fall)
        session.commit()
        session.refresh(fall)
        return fall.id


def test_objekt_mit_fall_kann_nicht_geloescht_werden():
    objekt_id = _objekt()
    fall_id = _fall(objekt_id=objekt_id)
    try:
        response = client.delete(f"/api/objekte/{objekt_id}")
        assert response.status_code == 409
    finally:
        _aufraeumen(Fall, fall_id)
        _aufraeumen(Objekt, objekt_id)


def test_objekt_mit_kontakt_kann_nicht_geloescht_werden():
    objekt_id = _objekt()
    kontakt_id = _kontakt(objekt_id=objekt_id)
    try:
        response = client.delete(f"/api/objekte/{objekt_id}")
        assert response.status_code == 409
    finally:
        _aufraeumen(Kontakt, kontakt_id)
        _aufraeumen(Objekt, objekt_id)


def test_unreferenziertes_objekt_kann_geloescht_werden():
    objekt_id = _objekt()
    try:
        response = client.delete(f"/api/objekte/{objekt_id}")
        assert response.status_code == 204
    finally:
        _aufraeumen(Objekt, objekt_id)  # No-op, falls die Löschung oben erfolgreich war.


def test_kontakt_mit_fall_kann_nicht_geloescht_werden():
    kontakt_id = _kontakt()
    fall_id = _fall(melder_kontakt_id=kontakt_id)
    try:
        response = client.delete(f"/api/kontakte/{kontakt_id}")
        assert response.status_code == 409
    finally:
        _aufraeumen(Fall, fall_id)
        _aufraeumen(Kontakt, kontakt_id)


def test_dienstleister_mit_fall_kann_nicht_geloescht_werden():
    dienstleister_id = _dienstleister()
    fall_id = _fall(dienstleister_id=dienstleister_id)
    try:
        response = client.delete(f"/api/dienstleister/{dienstleister_id}")
        assert response.status_code == 409
    finally:
        _aufraeumen(Fall, fall_id)
        _aufraeumen(Dienstleister, dienstleister_id)


def test_kontakt_anlegen_mit_unbekanntem_objekt_gibt_404():
    response = client.post(
        "/api/kontakte",
        json={
            "name": "Referenztest-Kontakt-2",
            "rolle": "mieter",
            "email": "referenztest2@example.test",
            "objekt_id": 999999,
        },
    )
    assert response.status_code == 404


def test_kontakt_aktualisieren_mit_unbekanntem_objekt_gibt_404():
    kontakt_id = _kontakt()
    try:
        response = client.put(
            f"/api/kontakte/{kontakt_id}",
            json={
                "name": "Referenztest-Kontakt",
                "rolle": "mieter",
                "email": "referenztest@example.test",
                "objekt_id": 999999,
            },
        )
        assert response.status_code == 404
    finally:
        _aufraeumen(Kontakt, kontakt_id)
