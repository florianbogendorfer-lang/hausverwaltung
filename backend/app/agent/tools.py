"""Tool-Katalog (§9).

FR-AGENT-4: Der Agent handelt ausschließlich über diese Funktionen — keine
freien Seiteneffekte. FR-HITL-1: Die drei freigabepflichtigen Tools
(`nachricht_senden`, `dienstleister_beauftragen`, `rechnung_erfassen`)
führen NICHTS direkt aus — sie legen nur einen `freigaben`-Eintrag
(propose) an und parken den Fall. Die eigentliche Ausführung (commit)
passiert erst in `app.agent.freigabe_service`, wenn der Operator freigibt.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.agent.model_router import ModellStufe, ModelRouter
from app.agent.schemas import EingehendeMail, Einordnung
from app.agent.vector_store import DokumentenIndex
from app.models import (
    Aktion,
    Akteur,
    Aktionstyp,
    Dienstleister,
    Dokument,
    Fall,
    FallStatus,
    FallTyp,
    Freigabe,
    Gewerk,
    Kontakt,
    Nachricht,
    NachrichtRichtung,
    NachrichtStatus,
)

EINORDNUNG_SYSTEM_PROMPT = """\
Du bist der Klassifikations-Baustein eines Hausverwaltungs-Agenten. Du \
ordnest eingehende Mieter-Mails ein. Antworte AUSSCHLIESSLICH mit einem \
JSON-Objekt (keine Erklärung, kein Markdown) mit exakt diesen Feldern:

{
  "typ": "reparaturmeldung",
  "gewerk": "schlosser" | "maurer" | "installateur" | "elektriker" | "sonstiges" | null,
  "objekt_suchbegriff": string | null,   // Adress-/Objekthinweis aus der Mail
  "melder_suchbegriff": string | null,   // Name oder E-Mail des Melders
  "konfidenz": number zwischen 0.0 und 1.0,
  "begruendung": string  // kurze Begründung, welche Hinweise zur Einordnung führten
}

Setze die Konfidenz NIEDRIG an, wenn das Anliegen unklar ist, kein Gewerk \
eindeutig erkennbar ist, oder es sich nicht um eine Reparaturmeldung \
handelt. Rate niemals — im Zweifel niedrige Konfidenz.\
"""


def fall_einordnen(router: ModelRouter, mail: EingehendeMail) -> tuple[Einordnung, str]:
    """Typ/Gewerk/Objekt/Melder bestimmen. Kein Freigabe nötig (nur Lesen/Denken)."""
    prompt = (
        f"Von: {mail.von}\nBetreff: {mail.betreff}\n\nInhalt:\n{mail.inhalt}"
    )
    einordnung, antwort = router.complete_structured(
        ModellStufe.guenstig, EINORDNUNG_SYSTEM_PROMPT, prompt, Einordnung
    )
    return einordnung, antwort.modell


def objekt_suchen(session: Session, suchbegriff: str):
    """Objekt zu Adresse/Melder finden."""
    from app.models import Objekt

    muster = f"%{suchbegriff}%"
    return list(
        session.exec(
            select(Objekt).where(
                (Objekt.adresse.like(muster)) | (Objekt.bezeichnung.like(muster))
            )
        ).all()
    )


def kontakt_suchen(session: Session, suchbegriff: str) -> Optional[Kontakt]:
    """Melder identifizieren (per Name oder E-Mail)."""
    muster = f"%{suchbegriff}%"
    return session.exec(
        select(Kontakt).where((Kontakt.name.like(muster)) | (Kontakt.email.like(muster)))
    ).first()


def dienstleister_suchen(session: Session, gewerk: Gewerk) -> list[Dienstleister]:
    """Passenden Dienstleister nach Gewerk finden (nur aktive)."""
    return list(
        session.exec(
            select(Dienstleister).where(
                Dienstleister.gewerk == gewerk, Dienstleister.aktiv.is_(True)
            )
        ).all()
    )


def dokumente_durchsuchen(
    session: Session, index: DokumentenIndex, frage: str, top_k: int = 2
) -> list[Dokument]:
    """RAG über Hausordnung/Verträge (§16 Phase 5) — echte Vektorsuche über
    einen von der DB getrennten Vektorspeicher (app.agent.vector_store)."""
    treffer_ids = index.suchen(frage, top_k=top_k)
    if not treffer_ids:
        return []
    dokumente = {d.id: d for d in session.exec(select(Dokument).where(Dokument.id.in_(treffer_ids))).all()}
    return [dokumente[i] for i in treffer_ids if i in dokumente]


def fall_anlegen(session: Session, typ: FallTyp, betreff: str) -> Fall:
    """Fall anlegen (reversibel, nur protokolliert — keine Freigabe nötig)."""
    fall = Fall(typ=typ, betreff=betreff, status=FallStatus.neu)
    session.add(fall)
    session.commit()
    session.refresh(fall)
    log_aktion(session, fall.id, Akteur.agent, "fall:angelegt", {"typ": typ.value})
    return fall


def fall_aktualisieren(session: Session, fall: Fall, **felder) -> Fall:
    """Fall-Felder + Status schreiben (reversibel, nur protokolliert)."""
    for feld, wert in felder.items():
        setattr(fall, feld, wert)
    fall.geaendert_am = datetime.utcnow()
    session.add(fall)
    session.commit()
    session.refresh(fall)
    details = {k: (v.value if hasattr(v, "value") else v) for k, v in felder.items()}
    log_aktion(session, fall.id, Akteur.agent, "fall:aktualisiert", details)
    return fall


def notiz_hinzufuegen(session: Session, fall_id: int, text: str) -> Aktion:
    """Interne Notiz an Fall (reversibel, nur protokolliert)."""
    return log_aktion(session, fall_id, Akteur.agent, "notiz", {"text": text})


NACHRICHT_ENTWERFEN_SYSTEM_PROMPT = """\
Du formulierst im Namen einer Hausverwaltung eine höfliche, knappe \
Geschäfts-E-Mail auf Deutsch. Gib AUSSCHLIESSLICH den E-Mail-Text aus \
(kein Betreff, keine Erklärung, keine Anführungszeichen).\
"""


def nachricht_entwerfen(
    router: ModelRouter,
    session: Session,
    fall_id: int,
    von: str,
    an: str,
    betreff: str,
    zweck: str,
    kontext: str,
) -> Nachricht:
    """Mailentwurf erzeugen (nur Entwurf, keine Freigabe nötig)."""
    prompt = f"Zweck der Mail: {zweck}\n\nKontext:\n{kontext}"
    antwort = router.complete_text(ModellStufe.stark, NACHRICHT_ENTWERFEN_SYSTEM_PROMPT, prompt)
    nachricht = Nachricht(
        fall_id=fall_id,
        richtung=NachrichtRichtung.ausgehend,
        von=von,
        an=an,
        betreff=betreff,
        inhalt=antwort.text.strip(),
        status=NachrichtStatus.entwurf,
    )
    session.add(nachricht)
    session.commit()
    session.refresh(nachricht)
    log_aktion(
        session,
        fall_id,
        Akteur.agent,
        "nachricht:entwurf_erstellt",
        {"nachricht_id": nachricht.id, "an": an, "modell": antwort.modell},
    )
    return nachricht


def _freigabe_anlegen_oder_vorhandene(
    session: Session,
    fall: Fall,
    aktionstyp: Aktionstyp,
    payload: dict,
    begruendung: str,
    kontext_referenzen: dict,
    idempotency_key: str,
) -> Freigabe:
    """FR-HITL-1 (propose) + FR-HITL-8 (Idempotenz): legt eine Freigabe an
    und parkt den Fall — oder gibt bei erneutem Aufruf mit demselben
    Idempotency-Key die bereits bestehende Freigabe zurück, statt sie
    doppelt anzulegen."""
    bestehende = session.exec(
        select(Freigabe).where(Freigabe.idempotency_key == idempotency_key)
    ).first()
    if bestehende is not None:
        return bestehende

    freigabe = Freigabe(
        fall_id=fall.id,
        aktionstyp=aktionstyp,
        payload=payload,
        begruendung=begruendung,
        kontext_referenzen=kontext_referenzen,
        idempotency_key=idempotency_key,
    )
    session.add(freigabe)
    fall.status = FallStatus.wartet_auf_freigabe
    fall.geaendert_am = datetime.utcnow()
    session.add(fall)
    session.commit()
    session.refresh(freigabe)

    log_aktion(
        session,
        fall.id,
        Akteur.agent,
        "freigabe:angefordert",
        {"freigabe_id": freigabe.id, "aktionstyp": aktionstyp.value},
        freigabe_id=freigabe.id,
    )
    return freigabe


def nachricht_senden(
    session: Session,
    fall: Fall,
    nachricht: Nachricht,
    begruendung: str,
    kontext_referenzen: Optional[dict] = None,
) -> Freigabe:
    """Entwurf versenden — freigabepflichtig (§5, FR-HITL-2). Legt nur die
    Freigabe an (propose); der tatsächliche Versand passiert erst beim
    Commit in `freigabe_service.freigeben`."""
    idempotency_key = f"nachricht_senden:{nachricht.id}"
    payload = {"nachricht_id": nachricht.id, "an": nachricht.an, "betreff": nachricht.betreff}
    return _freigabe_anlegen_oder_vorhandene(
        session,
        fall,
        Aktionstyp.nachricht_senden,
        payload,
        begruendung,
        kontext_referenzen or {},
        idempotency_key,
    )


def dienstleister_beauftragen(
    session: Session,
    fall: Fall,
    dienstleister_id: int,
    auftragstext: str,
    begruendung: str,
    kontext_referenzen: Optional[dict] = None,
) -> Freigabe:
    """Beauftragung auslösen — freigabepflichtig, Geldbezug (§5)."""
    idempotency_key = f"dienstleister_beauftragen:{fall.id}:{dienstleister_id}"
    payload = {"dienstleister_id": dienstleister_id, "auftragstext": auftragstext}
    return _freigabe_anlegen_oder_vorhandene(
        session,
        fall,
        Aktionstyp.dienstleister_beauftragen,
        payload,
        begruendung,
        kontext_referenzen or {},
        idempotency_key,
    )


def rechnung_erfassen(
    session: Session,
    fall: Fall,
    betrag: float,
    positionen: list[str],
    begruendung: str,
    kontext_referenzen: Optional[dict] = None,
) -> Freigabe:
    """(Simulierte) Rechnung buchen — freigabepflichtig, Geldbezug (§5)."""
    idempotency_key = f"rechnung_erfassen:{fall.id}:{betrag}:{'-'.join(positionen)}"
    payload = {"betrag": betrag, "positionen": positionen}
    return _freigabe_anlegen_oder_vorhandene(
        session,
        fall,
        Aktionstyp.rechnung_erfassen,
        payload,
        begruendung,
        kontext_referenzen or {},
        idempotency_key,
    )


def fall_eskalieren(session: Session, fall: Fall, grund: str) -> Fall:
    """An Operator übergeben, wenn der Agent unsicher ist (FR-HITL-6)."""
    fall.status = FallStatus.eskaliert
    fall.geaendert_am = datetime.utcnow()
    session.add(fall)
    session.commit()
    session.refresh(fall)
    log_aktion(session, fall.id, Akteur.agent, "fall:eskaliert", {"grund": grund})
    return fall


def log_aktion(
    session: Session,
    fall_id: int,
    akteur: Akteur,
    aktionsart: str,
    details: Optional[dict] = None,
    freigabe_id: Optional[int] = None,
) -> Aktion:
    """Schreibt einen Audit-Log-Eintrag (DM-7, append-only, §11)."""
    aktion = Aktion(
        fall_id=fall_id,
        akteur=akteur,
        aktionsart=aktionsart,
        details=details or {},
        freigabe_id=freigabe_id,
    )
    session.add(aktion)
    session.commit()
    session.refresh(aktion)
    return aktion
