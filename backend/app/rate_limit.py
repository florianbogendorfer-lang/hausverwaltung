"""Einfacher In-Memory-Rate-Limiter pro Client-IP.

Ergänzt den bereits vorhandenen Konto-basierten Login-Lockout
(`app.auth._fehlversuch_vermerken`) um eine IP-basierte Bremse: ohne sie
könnte ein Angreifer gezielt viele fremde Konten durch wiederholte
Fehlversuche in die (temporäre) Sperre nach OWASP Authentication Cheat
Sheet treiben — Account-Lockout selbst wird so zum Denial-of-Service-
Vektor gegen legitime Nutzer. Eine IP-Bremse schränkt das ein, ohne
selbst zur permanenten Sperre zu werden.

Bewusst In-Memory (kein Redis o. Ä.) — der Prototyp läuft als einzelner
Container (siehe NullPool-Entscheidung in app/db.py für denselben
Deployment-Kontext), ein Prozess-lokaler Zustand reicht daher aus.
"""

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request

_LOCK = threading.Lock()
_VERSUCHE: dict[str, list[float]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unbekannt"


def ip_rate_limit(max_versuche: int, fenster_sekunden: float):
    """Dependency-Factory: max. `max_versuche` Aufrufe pro IP innerhalb
    von `fenster_sekunden` (gleitendes Fenster), sonst 429."""

    def _pruefen(request: Request) -> None:
        ip = _client_ip(request)
        jetzt = time.monotonic()
        with _LOCK:
            versuche = _VERSUCHE[ip]
            versuche[:] = [t for t in versuche if jetzt - t < fenster_sekunden]
            if len(versuche) >= max_versuche:
                raise HTTPException(
                    status_code=429,
                    detail="Zu viele Versuche — bitte kurz warten.",
                    headers={"Retry-After": str(int(fenster_sekunden))},
                )
            versuche.append(jetzt)

    return _pruefen
