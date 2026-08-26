"""Regelbasierter Demo-Client (kein LLM-Aufruf, kein Netzwerk).

Ist kein `ANTHROPIC_API_KEY` konfiguriert, verwendet der `ModelRouter`
diesen Client, damit der Prototyp auch ohne Zugangsdaten end-to-end
vorführbar bleibt (§0: Ziel ist der sichtbare End-to-End-Fluss). Für echte
Modellantworten genügt es, `HV_ANTHROPIC_API_KEY` zu setzen — der Wechsel
ist rein konfigurativ (NFR-5), kein Code-Umbau.
"""

import json
import re
import time

from app.agent.model_router import LLMAntwort

_GEWERK_STICHWORTE: dict[str, list[str]] = {
    "schlosser": ["schloss", "türe", "tür ", "versperren", "schlüssel"],
    "installateur": ["wasser", "rohr", "leitung", "tropft", "abfluss", "heizung"],
    "elektriker": ["strom", "elektr", "steckdose", "sicherung", "licht"],
    "maurer": ["riss", "mauer", "putz", "wand"],
}


class DemoLLMClient:
    def complete(self, modell: str, system: str, prompt: str, temperature: float) -> LLMAntwort:
        start = time.monotonic()
        if "JSON-Objekt" in system:
            text = self._einordnen(prompt)
        else:
            text = self._entwerfen(prompt)
        dauer_ms = int((time.monotonic() - start) * 1000)
        return LLMAntwort(text=text, modell=f"{modell} (demo, kein API-Key konfiguriert)", dauer_ms=dauer_ms)

    def _einordnen(self, prompt: str) -> str:
        inhalt = prompt.lower()
        gewerk = None
        for kandidat, stichworte in _GEWERK_STICHWORTE.items():
            if any(s in inhalt for s in stichworte):
                gewerk = kandidat
                break

        von_treffer = re.search(r"Von:\s*(.+)", prompt)
        objekt_treffer = re.search(
            r"(musterstra(?:ss|ß)e\s*\d+|beispielgasse\s*\d+)", prompt, re.IGNORECASE
        )

        konfidenz = 0.85 if gewerk else 0.2
        daten = {
            "typ": "reparaturmeldung",
            "gewerk": gewerk,
            "objekt_suchbegriff": objekt_treffer.group(0) if objekt_treffer else None,
            "melder_suchbegriff": von_treffer.group(1).strip() if von_treffer else None,
            "konfidenz": konfidenz,
            "begruendung": (
                f"Demo-Client: Stichwortsuche ergab Gewerk={gewerk}."
                if gewerk
                else "Demo-Client: kein bekanntes Gewerk-Stichwort im Text gefunden."
            ),
        }
        return json.dumps(daten)

    def _entwerfen(self, prompt: str) -> str:
        kontext = prompt.split("Kontext:", 1)[-1].strip()[:400]
        return (
            "Sehr geehrte Damen und Herren,\n\n"
            "im Auftrag unserer Hausverwaltung bitten wir Sie, für das unten beschriebene "
            "Anliegen zeitnah einen Termin zu vereinbaren.\n\n"
            f"{kontext}\n\n"
            "Bitte stimmen Sie den Termin direkt mit dem Mieter bzw. der Mieterin ab.\n\n"
            "Freundliche Grüße\nIhre Hausverwaltung\n\n"
            "(Hinweis: Dieser Text stammt vom regelbasierten Demo-Client, nicht von einem LLM.)"
        )
