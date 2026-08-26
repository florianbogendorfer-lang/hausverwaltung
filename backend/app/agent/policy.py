"""Zentrale Freigabe-Policy (FR-HITL-2).

Legt fest, welche Tools freigabepflichtig sind — bewusst als eigene,
durchsuchbare Konfiguration und NICHT im Modell-Prompt hartkodiert, damit
sie unabhängig vom LLM geprüft/geändert werden kann.
"""

# Name des Tools (siehe app.agent.tools) → freigabepflichtig?
TOOL_FREIGABE_POLICY: dict[str, bool] = {
    # irreversibel / Geldbezug → Pre-Action-Freigabe Pflicht
    "nachricht_senden": True,
    "dienstleister_beauftragen": True,
    "rechnung_erfassen": True,
    # reversibel/folgenlos → auto (nur protokolliert)
    "fall_einordnen": False,
    "objekt_suchen": False,
    "kontakt_suchen": False,
    "dienstleister_suchen": False,
    "dokumente_durchsuchen": False,
    "fall_anlegen": False,
    "fall_aktualisieren": False,
    "notiz_hinzufuegen": False,
    "nachricht_entwerfen": False,
    "fall_eskalieren": False,
}


def ist_freigabepflichtig(tool_name: str) -> bool:
    return TOOL_FREIGABE_POLICY.get(tool_name, True)  # unbekannt → sicherer Default: Freigabe nötig
