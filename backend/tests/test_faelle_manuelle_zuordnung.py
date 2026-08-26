from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models import Fall, FallStatus, FallTyp
from tests.conftest import engine

client = TestClient(app)


def _erzeuge_fall(status: FallStatus = FallStatus.neu) -> int:
    with Session(engine) as session:
        fall = Fall(typ=FallTyp.reparaturmeldung, betreff="Testfall für manuelle Zuordnung", status=status)
        session.add(fall)
        session.commit()
        session.refresh(fall)
        return fall.id


def test_manuelle_zuordnung_setzt_objekt_melder_dienstleister():
    fall_id = _erzeuge_fall()

    response = client.patch(
        f"/api/faelle/{fall_id}",
        json={"objekt_id": 1, "melder_kontakt_id": 1, "dienstleister_id": 1, "gewerk": "schlosser"},
    )
    assert response.status_code == 200
    daten = response.json()
    assert daten["objekt_id"] == 1
    assert daten["melder_kontakt_id"] == 1
    assert daten["dienstleister_id"] == 1
    assert daten["gewerk"] == "schlosser"

    aktionen = client.get(f"/api/faelle/{fall_id}/aktionen").json()
    assert any(a["aktionsart"] == "fall:manuell_aktualisiert" for a in aktionen)
    letzte = [a for a in aktionen if a["aktionsart"] == "fall:manuell_aktualisiert"][-1]
    assert letzte["akteur"] == "operator"


def test_manuelle_zuordnung_unbekanntes_objekt_gibt_404():
    fall_id = _erzeuge_fall()
    response = client.patch(f"/api/faelle/{fall_id}", json={"objekt_id": 99999})
    assert response.status_code == 404


def test_status_uebergang_von_eskaliert_zu_eingeordnet_erlaubt():
    fall_id = _erzeuge_fall(status=FallStatus.eskaliert)
    response = client.patch(f"/api/faelle/{fall_id}", json={"status": "EINGEORDNET"})
    assert response.status_code == 200
    assert response.json()["status"] == FallStatus.eingeordnet.value


def test_status_uebergang_ausserhalb_eskaliert_wird_abgelehnt():
    fall_id = _erzeuge_fall(status=FallStatus.neu)
    response = client.patch(f"/api/faelle/{fall_id}", json={"status": "EINGEORDNET"})
    assert response.status_code == 400


def test_manuelle_zuordnung_unbekannter_fall_gibt_404():
    response = client.patch("/api/faelle/99999", json={"objekt_id": 1})
    assert response.status_code == 404
