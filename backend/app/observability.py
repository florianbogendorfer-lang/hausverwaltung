"""Beobachtbarkeit für den Produktivbetrieb: Fehler-Tracking (Sentry,
optional) + Request-IDs zur Korrelation von Log-Zeilen über einen
einzelnen Request hinweg (OWASP Logging Cheat Sheet — ohne Korrelations-ID
sind gleichzeitige Requests im Log kaum auseinanderzuhalten). Beides ist
bewusst per Default inaktiv/neutral, damit lokale Entwicklung und die
bestehende Testsuite unverändert funktionieren."""

import logging
import uuid
from contextvars import ContextVar

from app.config import settings

_logger = logging.getLogger("hv.app")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s APP %(message)s"))
    _logger.addHandler(_handler)
    # Wie app/audit_log.py: nicht an den Root-Logger weiterreichen, sonst
    # doppelte Ausgabe, falls uvicorn selbst einen Stream-Handler setzt.
    _logger.propagate = False

# Default "-" statt None: Code außerhalb eines Requests (z. B. app/seed.py
# beim Container-Start) soll request_id() ohne Sonderfall aufrufen können.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def request_id() -> str:
    """Die Request-ID des aktuell laufenden Requests, "-" außerhalb eines
    Requests (z. B. Start-Skripte, Hintergrund-Code)."""
    return request_id_var.get()


def neue_request_id(vorgeschlagen: str | None) -> str:
    """Übernimmt eine vom Client mitgeschickte X-Request-Id (z. B. von einem
    vorgelagerten Load Balancer/Proxy) oder erzeugt eine neue — ein Request
    ohne ID zu lassen würde die Korrelation genau für die Fehlerfälle
    verlieren, die man beobachten will."""
    return vorgeschlagen or str(uuid.uuid4())


def log_unbehandelte_ausnahme(exc: BaseException) -> None:
    """Eine bis zur Middleware durchgereichte, unbehandelte Ausnahme mit der
    aktuellen Request-ID protokollieren, bevor sie an Starlettes eigene
    Fehlerbehandlung (500-Response) weitergereicht wird — ohne das landet
    die Ursache nur in der generischen 500-Antwort, nicht im Log."""
    _logger.error("Unbehandelte Ausnahme request_id=%s", request_id(), exc_info=exc)


def init_sentry() -> None:
    """Fehler-Tracking nur aktiv, wenn HV_SENTRY_DSN gesetzt ist — ohne DSN
    bleibt sentry_sdk vollständig inaktiv (No-Op), es ändert sich nichts am
    Verhalten. Muss vor der FastAPI-App-Erzeugung aufgerufen werden, damit
    die automatische Starlette/FastAPI-Instrumentierung von sentry-sdk
    (seit Version 2.x) noch greift."""
    if not settings.sentry_dsn:
        return

    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment
        or ("produktion" if settings.cookie_secure else "entwicklung"),
        # Reines Error-Tracking genügt für diesen Anwendungsfall — kein
        # Performance-/Trace-Sampling, das zusätzliches Sentry-Kontingent
        # ohne hier bekannten Bedarf kosten würde.
        traces_sample_rate=0.0,
        # Keine automatische PII-Übermittlung (z. B. Request-Bodies mit
        # Kontaktdaten/E-Mail-Inhalten) an Sentry — OWASP-Grundsatz "keine
        # sensiblen Daten in externe Logging-/Monitoring-Dienste", gleiche
        # Haltung wie app/audit_log.py (nie Passwörter/Token loggen).
        send_default_pii=False,
    )
