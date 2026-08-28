"""Sicherheits-Audit-Log (OWASP Logging Cheat Sheet): sicherheitsrelevante
Ereignisse (Login-Erfolg/-Fehlschlag, Konto-Sperre, Passwort-Änderung,
Benutzerverwaltung) strukturiert protokollieren — unabhängig von der
Anwendungs-DB, damit sich sicherheitsrelevante Vorgänge auch nachvollziehen
lassen, wenn die DB selbst kompromittiert oder ihr Audit-Trail manipuliert
wurde. Läuft auf stdout (wie die übrigen print()-Meldungen in diesem
Prototyp, siehe app/config.py) — Clever Cloud sammelt Container-stdout
automatisch als Log-Stream, ein externer Log-Aggregator ist außerhalb des
Prototyp-Scopes (§2.2)."""

import logging

_logger = logging.getLogger("hv.audit")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s AUDIT %(message)s"))
    _logger.addHandler(_handler)
    # Nicht an den Root-Logger weiterreichen — sonst doppelte Ausgabe, falls
    # der Root-Logger (z. B. durch uvicorn) ebenfalls einen Stream-Handler
    # konfiguriert.
    _logger.propagate = False


def audit(ereignis: str, **felder: object) -> None:
    """Ein sicherheitsrelevantes Ereignis protokollieren, z. B.
    `audit("login_fehlgeschlagen", email=email)`. Nie Passwörter oder
    Session-Token als Feld übergeben — nur Identifikatoren (E-Mail, Rolle,
    Fall-ID etc.)."""
    detail = " ".join(f"{schluessel}={wert!r}" for schluessel, wert in felder.items())
    _logger.info("%s %s", ereignis, detail)
