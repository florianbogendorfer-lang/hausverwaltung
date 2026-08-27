"""Soft-Delete für Fälle: verschwindet aus Board/Kundenansicht, der
Audit-Trail (Aktionen) bleibt aber vollständig erhalten."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models import Fall, FallStatus, FallTyp
from tests.conftest import engine

client = TestClient(app)


def _erzeuge_fall() -> dict:
    with Session(engine) as session:
        fall = Fall(typ=FallTyp.reparaturmeldung, betreff="Zu löschender Testfall", status=FallStatus.neu)
        session.add(fall)
        session.commit()
        session.refresh(fall)
        return {"id": fall.id, "ticket_nummer": fall.ticket_nummer}


def test_geloeschter_fall_verschwindet_aus_liste_und_details():
    fall = _erzeuge_fall()

    response = client.delete(f"/api/faelle/{fall['id']}")
    assert response.status_code == 204

    liste = client.get("/api/faelle").json()
    assert fall["id"] not in [f["id"] for f in liste]

    details = client.get(f"/api/faelle/{fall['id']}")
    assert details.status_code == 404


def test_geloeschter_fall_hinterlaesst_audit_log_eintrag():
    fall = _erzeuge_fall()
    client.delete(f"/api/faelle/{fall['id']}")

    aktionen_response = client.get(f"/api/faelle/{fall['id']}/aktionen")
    # Der Sub-Endpunkt bleibt bewusst über deleted Fälle hinweg abrufbar
    # (Audit-Trail ist append-only und soll nicht mit verschwinden).
    assert aktionen_response.status_code == 200
    aktionsarten = {a["aktionsart"] for a in aktionen_response.json()}
    assert "fall:geloescht" in aktionsarten


def test_geloeschtes_ticket_gibt_404():
    fall = _erzeuge_fall()
    client.delete(f"/api/faelle/{fall['id']}")

    response = client.get(f"/api/ticket/{fall['ticket_nummer']}")
    assert response.status_code == 404


def test_nicht_existierenden_fall_loeschen_gibt_404():
    response = client.delete("/api/faelle/999999")
    assert response.status_code == 404
