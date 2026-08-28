"""app.agent.schemas.EingehendeMail.von — Formatprüfung (siehe
app.validators.email_gueltig_pruefen). Ein syntaktisch ungültiger Absender
würde sonst unverändert als Nachricht.von gespeichert und potenziell
später als SMTP-Empfänger einer Antwort verwendet (app.agent.mail_adapter).
Die Validierung greift vor jedem Modellaufruf — kein Override von
get_model_router nötig."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_postfach_eingang_lehnt_ungueltigen_absender_ab():
    response = client.post(
        "/api/postfach/eingang",
        json={"von": "nicht-valide", "betreff": "Test", "inhalt": "Test"},
    )
    assert response.status_code == 422
