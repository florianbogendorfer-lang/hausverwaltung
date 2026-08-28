"""Simulierter Postfach-Eingang (§6, §10 UI-5).

Eine eingespielte Mail löst den Agent-Loop aus (kein echter IMAP-Betrieb,
§2.2 Out of Scope). Die Schnittstelle ist so geschnitten, dass sie später
durch einen echten Mail-Adapter ersetzt werden kann, ohne den Agent-Kern
anzufassen.
"""

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.agent.loop import bearbeite_eingehende_mail
from app.agent.model_router import ModelRouter
from app.agent.schemas import EingehendeMail
from app.agent.vector_store import DokumentenIndex
from app.db import get_session
from app.models import Fall
from app.rate_limit import ip_rate_limit

router = APIRouter(prefix="/postfach", tags=["postfach"])

# Jeder Aufruf löst einen echten LLM-API-Aufruf aus (Kosten!) — ohne Bremse
# könnte ein Frontend-Bug (Retry-Schleife) oder eine kompromittierte Session
# unbemerkt hohe Kosten verursachen. 30 Versuche/5 Minuten ist großzügig
# genug für normale Bedienung (auch mehrere Test-Mails hintereinander),
# bremst aber eine Endlosschleife spürbar. Analog zur Login-Bremse in
# app/routers/auth.py.
postfach_rate_limiter = ip_rate_limit(max_versuche=30, fenster_sekunden=300)


def get_model_router() -> ModelRouter:
    return ModelRouter()


_dokumenten_index: DokumentenIndex | None = None


def get_dokumenten_index() -> DokumentenIndex:
    """Modulweite Default-Instanz (lazy) — der Chroma-Client/das Embedding-
    Modell sollen nicht pro Request neu aufgebaut werden. Tests überschreiben
    diese Dependency mit einem In-Memory-Index + Fake-Embedding (§0)."""
    global _dokumenten_index
    if _dokumenten_index is None:
        _dokumenten_index = DokumentenIndex()
    return _dokumenten_index


@router.post("/eingang", response_model=Fall, dependencies=[Depends(postfach_rate_limiter)])
def mail_einspielen(
    mail: EingehendeMail,
    request: Request,
    session: Session = Depends(get_session),
    router: ModelRouter = Depends(get_model_router),
    index: DokumentenIndex = Depends(get_dokumenten_index),
) -> Fall:
    """Simuliert den Eingang einer Mieter-Mail und stößt die Fallbearbeitung an.

    Die Basis-URL für den Dienstleister-Terminportal-Link (siehe
    app/agent/loop.py) wird aus `request.base_url` abgeleitet — dieser
    Endpunkt wird ausschließlich vom eigenen Frontend auf genau der Domain
    aufgerufen, unter der die App gerade läuft (kein echter IMAP-Betrieb),
    daher lässt sich die öffentliche Basis-URL ohne manuelle Konfiguration
    zuverlässig bestimmen (docker-entrypoint.sh startet uvicorn mit
    --proxy-headers, Clever Cloud liefert den echten Host/das echte Schema
    dadurch korrekt durch, auch hinter dessen TLS-Terminierung)."""
    basis_url = str(request.base_url).rstrip("/")
    return bearbeite_eingehende_mail(session, router, index, mail, basis_url=basis_url)
