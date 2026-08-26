"""Fake-LLM-Client für Tests — kein Netzwerkzugriff nötig (§0: externe Welt
wird simuliert). Liefert deterministische, szenario-gesteuerte Antworten."""

import json

from app.agent.model_router import LLMAntwort


class FakeLLMClient:
    """Antwortet anhand von Stichworten im Prompt — reicht, um die im Test
    verwendeten Szenarien (Türschloss defekt, unklares Anliegen) sauber
    auseinanderzuhalten, ohne einen echten Modellaufruf zu benötigen."""

    def __init__(self) -> None:
        self.aufrufe: list[dict] = []

    def complete(self, modell: str, system: str, prompt: str, temperature: float) -> LLMAntwort:
        self.aufrufe.append(
            {"modell": modell, "system": system, "prompt": prompt, "temperature": temperature}
        )

        if "Zweck der Mail" in prompt:
            text = (
                "Sehr geehrte Damen und Herren,\n\n"
                "wir bitten Sie, bei der oben genannten Liegenschaft einen Termin zur "
                "Behebung des defekten Türschlosses zu vereinbaren.\n\n"
                "Freundliche Grüße\nIhre Hausverwaltung"
            )
            return LLMAntwort(text=text, modell=modell, dauer_ms=5)

        if "Türschloss" in prompt or "schloss" in prompt.lower():
            daten = {
                "typ": "reparaturmeldung",
                "gewerk": "schlosser",
                "objekt_suchbegriff": "Musterstraße 5",
                "melder_suchbegriff": "Erika Musterfrau",
                "konfidenz": 0.92,
                "begruendung": "Mail beschreibt eindeutig ein defektes Türschloss.",
            }
        else:
            daten = {
                "typ": "reparaturmeldung",
                "gewerk": None,
                "objekt_suchbegriff": None,
                "melder_suchbegriff": None,
                "konfidenz": 0.2,
                "begruendung": "Anliegen ist unklar, kein Gewerk erkennbar.",
            }

        return LLMAntwort(text=json.dumps(daten), modell=modell, dauer_ms=5)
