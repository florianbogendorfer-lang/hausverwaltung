from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.models import Gewerk

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_meldet_503_wenn_datenbank_nicht_erreichbar():
    # /health prüft bewusst auch die DB-Erreichbarkeit (nicht nur "Prozess
    # läuft") — ein hängender Postgres soll den Docker-HEALTHCHECK als
    # unhealthy erkennen lassen, siehe app/main.py::health. Simuliert das
    # über eine Fake-Session statt eine echte DB abzuklemmen.
    class KaputteSession:
        def exec(self, *args, **kwargs):
            raise RuntimeError("DB nicht erreichbar")

    def kaputte_session():
        yield KaputteSession()

    # tests/conftest.py setzt app.dependency_overrides[get_session] global
    # für die gesamte Suite (eine gemeinsame In-Memory-DB) — ein simples
    # `del` würde dieses Override komplett entfernen statt es wieder-
    # herzustellen und damit alle nachfolgenden Tests gegen eine andere
    # (leere) Datenbank laufen lassen. Daher den ursprünglichen Override
    # merken und danach zurücksetzen statt zu löschen.
    urspruengliche_override = app.dependency_overrides[get_session]
    app.dependency_overrides[get_session] = kaputte_session
    try:
        response = client.get("/health")
        assert response.status_code == 503
    finally:
        app.dependency_overrides[get_session] = urspruengliche_override


def test_objekte_liste():
    response = client.get("/api/objekte")
    assert response.status_code == 200
    daten = response.json()
    assert len(daten) == 4
    assert {o["bezeichnung"] for o in daten} == {
        "Liegenschaft Musterstraße 5",
        "Liegenschaft Beispielgasse 12",
        "Liegenschaft Am Kanal 8",
        "Liegenschaft Ringstraße 21",
    }


def test_objekt_details_404():
    response = client.get("/api/objekte/9999")
    assert response.status_code == 404


def test_kontakte_liste():
    response = client.get("/api/kontakte")
    assert response.status_code == 200
    assert len(response.json()) == 9


def test_dienstleister_liste():
    response = client.get("/api/dienstleister")
    assert response.status_code == 200
    assert len(response.json()) == 9


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
