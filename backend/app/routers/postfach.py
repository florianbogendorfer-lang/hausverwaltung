"""Simulierter Postfach-Eingang (§6, §10 UI-5).

Eine eingespielte Mail löst den Agent-Loop aus (kein echter IMAP-Betrieb,
§2.2 Out of Scope). Die Schnittstelle ist so geschnitten, dass sie später
durch einen echten Mail-Adapter ersetzt werden kann, ohne den Agent-Kern
anzufassen.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.agent.loop import bearbeite_eingehende_mail
from app.agent.model_router import ModelRouter
from app.agent.schemas import EingehendeMail
from app.db import get_session
from app.models import Fall

router = APIRouter(prefix="/postfach", tags=["postfach"])


def get_model_router() -> ModelRouter:
    return ModelRouter()


@router.post("/eingang", response_model=Fall)
def mail_einspielen(
    mail: EingehendeMail,
    session: Session = Depends(get_session),
    router: ModelRouter = Depends(get_model_router),
) -> Fall:
    """Simuliert den Eingang einer Mieter-Mail und stößt die Fallbearbeitung an."""
    return bearbeite_eingehende_mail(session, router, mail)
