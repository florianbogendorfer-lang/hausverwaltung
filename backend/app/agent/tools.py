"""Tool-Katalog (§9).

FR-AGENT-4: Der Agent handelt ausschließlich über diese Funktionen — keine
freien Seiteneffekte. Freigabepflichtige Tools (`nachricht_senden`,
`dienstleister_beauftragen`, `rechnung_erfassen`) sind in dieser Phase
bewusst noch nicht funktionsfähig: die propose/commit-Trennung (FR-HITL-1)
und die Freigabe-Queue kommen erst in Phase 3. Bis dahin lösen sie einen
klaren Fehler statt eines stillen No-Ops aus — sicherer als so zu tun, als
hätten sie gewirkt (§0: bei Unklarheit die sichere Variante wählen).
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.agent.model_router import ModellStufe, ModelRouter
from app.agent.schemas import EingehendeMail, Einordnung
from app.models import (
    Aktion,
    Akteur,
    Dienstleister,
    Dokument,
    Fall,
    FallStatus,
    FallTyp,
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


def dokumente_durchsuchen(session: Session, frage: str, top_k: int = 2) -> list[Dokument]:
    """RAG über Hausordnung/Verträge.

    Platzhalter für Phase 1: einfache Stichwortsuche über den Volltext.
    Echte Vektorsuche folgt in Phase 5 (§16).
    """
    begriffe = [b.lower() for b in frage.split() if len(b) > 3]
    dokumente = list(session.exec(select(Dokument)).all())

    def score(dok: Dokument) -> int:
        text = dok.inhalt.lower()
        return sum(text.count(b) for b in begriffe)

    treffer = sorted((d for d in dokumente if score(d) > 0), key=score, reverse=True)
    return treffer[:top_k]


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


def nachricht_senden(session: Session, nachricht_id: int) -> None:
    """Entwurf versenden — freigabepflichtig (§5). Erst ab Phase 3
    (Freigabe-Queue) verfügbar."""
    raise NotImplementedError(
        "nachricht_senden ist freigabepflichtig und erst ab Phase 3 (HITL "
        "propose/commit, Freigabe-Queue) implementiert."
    )


def dienstleister_beauftragen(session: Session, dienstleister_id: int, fall_id: int, auftragstext: str) -> None:
    """Beauftragung auslösen — freigabepflichtig (§5). Erst ab Phase 3
    verfügbar."""
    raise NotImplementedError(
        "dienstleister_beauftragen ist freigabepflichtig und erst ab Phase 3 "
        "(HITL propose/commit, Freigabe-Queue) implementiert."
    )


def rechnung_erfassen(session: Session, fall_id: int, betrag: float, positionen: list[str]) -> None:
    """(Simulierte) Rechnung buchen — freigabepflichtig (§5). Erst ab
    Phase 3 verfügbar."""
    raise NotImplementedError(
        "rechnung_erfassen ist freigabepflichtig und erst ab Phase 3 (HITL "
        "propose/commit, Freigabe-Queue) implementiert."
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
