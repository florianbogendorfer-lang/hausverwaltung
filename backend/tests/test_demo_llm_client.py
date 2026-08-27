"""Der regelbasierte Demo-Client (kein API-Key konfiguriert) muss Objekte
anhand einer generischen Adress-Erkennung finden können — nicht nur die
zwei ursprünglich einprogrammierten Straßennamen (Musterstraße/
Beispielgasse). Sonst bleiben neu angelegte Stammdaten-Objekte für die
automatische Einordnung unsichtbar."""

import json

from app.agent.demo_llm_client import DemoLLMClient

client = DemoLLMClient()


def _objekt_suchbegriff(inhalt: str) -> str | None:
    prompt = f"Von: mieter@example.test\nBetreff: Anliegen\n\nInhalt:\n{inhalt}"
    antwort = client.complete("m", "JSON-Objekt", prompt, 0.0)
    return json.loads(antwort.text)["objekt_suchbegriff"]


def test_erkennt_strasse_mit_ss_schreibweise():
    assert _objekt_suchbegriff("Das Schloss in der Musterstrasse 5 ist defekt.") == "Musterstrasse 5"


def test_erkennt_strasse_mit_eszett_schreibweise():
    assert _objekt_suchbegriff("Das Schloss in der Musterstraße 5 ist defekt.") == "Musterstraße 5"


def test_erkennt_gasse():
    assert _objekt_suchbegriff("Die Heizung in der Beispielgasse 12 tropft.") == "Beispielgasse 12"


def test_erkennt_am_praefix_adresse():
    assert _objekt_suchbegriff("Wasserschaden Am Kanal 8, bitte um Hilfe.") == "Am Kanal 8"


def test_erkennt_neu_angelegte_stammdaten_strasse():
    assert _objekt_suchbegriff("Steckdose in der Ringstraße 21 kaputt.") == "Ringstraße 21"


def test_kein_treffer_ohne_adresshinweis():
    assert _objekt_suchbegriff("Ich habe eine allgemeine Frage zu meinem Vertrag.") is None
