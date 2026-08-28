"""Postfach-Eingang (§6, §10 UI-5): simulierte Einspielung (POST
/postfach/eingang, seit jeher) und — sofern HV_IMAP_HOST konfiguriert ist
— echter Abruf eines IMAP-Postfachs (POST /postfach/abrufen). Beide
Wege münden im selben Agent-Kern (`bearbeite_eingehende_mail`); die
Schnittstelle war von Anfang an so geschnitten, dass sie durch einen
echten Mail-Adapter ergänzt werden kann, ohne den Agent-Kern anzufassen.
"""

import imaplib

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ValidationError
from sqlmodel import Session, select

from app.agent.imap_adapter import unbearbeitete_mails_abrufen
from app.agent.loop import HAUSVERWALTUNG_ABSENDER, bearbeite_eingehende_mail
from app.agent.model_router import ModelRouter
from app.agent.schemas import EingehendeMail
from app.agent.tools import log_aktion
from app.agent.vector_store import DokumentenIndex
from app.config import settings
from app.db import get_session
from app.models import Akteur, Fall, Nachricht, NachrichtRichtung, NachrichtStatus
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


class PostfachAbrufErgebnis(BaseModel):
    neue_faelle: int
    zugeordnete_antworten: int
    uebersprungene_mails: int


@router.post(
    "/abrufen",
    response_model=PostfachAbrufErgebnis,
    dependencies=[Depends(postfach_rate_limiter)],
)
def postfach_abrufen(
    request: Request,
    session: Session = Depends(get_session),
    router: ModelRouter = Depends(get_model_router),
    index: DokumentenIndex = Depends(get_dokumenten_index),
) -> PostfachAbrufErgebnis:
    """Ruft ein echtes, per HV_IMAP_* konfiguriertes Postfach ab und
    verarbeitet jede ungelesene Mail:

    - Enthält der Betreff eine bekannte Ticketnummer (z. B. eine Antwort
      des Dienstleisters), wird die Mail dem bestehenden Fall als
      eingehende Nachricht angehängt (kein erneuter Agent-Loop-Durchlauf
      — der Bearbeiter sieht die Antwort im Nachrichtenverlauf des Falls
      und entscheidet selbst über das weitere Vorgehen, FR-HITL-3).
    - Sonst läuft die Mail genau wie eine simulierte Einspielung über
      /postfach/eingang durch den vollen Agent-Loop und legt einen neuen
      Fall an.

    So geht keine Mail unbemerkt "verloren" — jede landet entweder an
    einem bestehenden Fall oder wird selbst zu einem neuen. Ohne
    HV_IMAP_HOST nicht verfügbar (404)."""
    if not settings.imap_host:
        raise HTTPException(
            status_code=404, detail="Kein echtes Postfach konfiguriert (HV_IMAP_HOST fehlt)."
        )

    try:
        abgerufene_mails = unbearbeitete_mails_abrufen()
    except (imaplib.IMAP4.error, OSError) as exc:
        raise HTTPException(
            status_code=502, detail=f"Postfach-Abruf fehlgeschlagen: {exc}"
        ) from exc

    basis_url = str(request.base_url).rstrip("/")
    neue_faelle = 0
    zugeordnete_antworten = 0
    uebersprungene_mails = 0

    for mail in abgerufene_mails:
        fall = None
        if mail.ticket_nummer:
            fall = session.exec(
                select(Fall).where(
                    Fall.ticket_nummer == mail.ticket_nummer, Fall.geloescht.is_(False)
                )
            ).first()

        if fall is not None:
            nachricht = Nachricht(
                fall_id=fall.id,
                richtung=NachrichtRichtung.eingehend,
                von=mail.von,
                an=HAUSVERWALTUNG_ABSENDER,
                betreff=mail.betreff,
                inhalt=mail.inhalt,
                status=NachrichtStatus.empfangen,
            )
            session.add(nachricht)
            session.commit()
            session.refresh(nachricht)
            log_aktion(
                session,
                fall.id,
                Akteur.system,
                "postfach:antwort_empfangen",
                {"nachricht_id": nachricht.id, "von": mail.von},
            )
            zugeordnete_antworten += 1
            continue

        try:
            eingehende_mail = EingehendeMail(von=mail.von, betreff=mail.betreff, inhalt=mail.inhalt)
        except ValidationError:
            # Absenderadresse ließ sich nicht sauber extrahieren/validieren
            # (z. B. eine Systemmail mit ungewöhnlichem From-Header) — eine
            # einzelne kaputte Mail soll nicht den ganzen Abruf abbrechen.
            uebersprungene_mails += 1
            continue

        bearbeite_eingehende_mail(session, router, index, eingehende_mail, basis_url=basis_url)
        neue_faelle += 1

    return PostfachAbrufErgebnis(
        neue_faelle=neue_faelle,
        zugeordnete_antworten=zugeordnete_antworten,
        uebersprungene_mails=uebersprungene_mails,
    )
