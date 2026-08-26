from fastapi.testclient import TestClient

from app.main import app
from app.models import Gewerk

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_objekte_liste():
    response = client.get("/api/objekte")
    assert response.status_code == 200
    daten = response.json()
    assert len(daten) == 2
    assert {o["bezeichnung"] for o in daten} == {
        "Liegenschaft Musterstraße 5",
        "Liegenschaft Beispielgasse 12",
    }


def test_objekt_details_404():
    response = client.get("/api/objekte/9999")
    assert response.status_code == 404


def test_kontakte_liste():
    response = client.get("/api/kontakte")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_dienstleister_liste():
    response = client.get("/api/dienstleister")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_dienstleister_filter_nach_gewerk():
    response = client.get("/api/dienstleister", params={"gewerk": Gewerk.schlosser.value})
    assert response.status_code == 200
    daten = response.json()
    assert len(daten) == 2
    assert all(d["gewerk"] == Gewerk.schlosser.value for d in daten)
    aktive_schlosser = [d for d in daten if d["aktiv"]]
    assert len(aktive_schlosser) == 1
    assert aktive_schlosser[0]["name"] == "Schlosserei Sicherheit GmbH"


def test_dokumente_liste():
    response = client.get("/api/dokumente")
    assert response.status_code == 200
    daten = response.json()
    assert len(daten) == 3
    quellen = {d["quelle"] for d in daten}
    assert "hausordnung_auszug.txt" in quellen
