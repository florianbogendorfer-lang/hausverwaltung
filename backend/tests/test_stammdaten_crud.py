from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_objekt_anlegen_aktualisieren_loeschen():
    erstellt = client.post(
        "/api/objekte",
        json={"bezeichnung": "Testliegenschaft", "adresse": "Teststraße 1"},
    )
    assert erstellt.status_code == 201
    objekt_id = erstellt.json()["id"]

    aktualisiert = client.put(
        f"/api/objekte/{objekt_id}",
        json={"bezeichnung": "Testliegenschaft neu", "adresse": "Teststraße 1", "einheit": "Top 1"},
    )
    assert aktualisiert.status_code == 200
    assert aktualisiert.json()["bezeichnung"] == "Testliegenschaft neu"

    geloescht = client.delete(f"/api/objekte/{objekt_id}")
    assert geloescht.status_code == 204
    assert client.get(f"/api/objekte/{objekt_id}").status_code == 404


def test_dienstleister_anlegen_mit_ungueltigem_gewerk_schlaegt_fehl():
    response = client.post(
        "/api/dienstleister",
        json={"name": "X", "gewerk": "unbekannt", "email": "x@example.test"},
    )
    assert response.status_code == 422


def test_kontakt_anlegen_und_loeschen():
    erstellt = client.post(
        "/api/kontakte",
        json={"name": "Test Person", "rolle": "mieter", "email": "test@example.test"},
    )
    assert erstellt.status_code == 201
    kontakt_id = erstellt.json()["id"]
    assert client.delete(f"/api/kontakte/{kontakt_id}").status_code == 204
