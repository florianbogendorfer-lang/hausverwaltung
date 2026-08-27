"""Agent-Kern: ReAct-Loop für den Referenzfall „Reparaturmeldung" (§8, §4.2).

FR-AGENT-1: pro Fall wahrnehmen → planen → Tool wählen → beobachten →
wiederholen, bis Ziel erreicht oder Freigabe/Eskalation nötig. Jeder
Schritt schreibt einen `traces`-Eintrag.

Der Loop läuft bis zum ersten freigabepflichtigen Schritt (§4.2 Schritt 4:
Beauftragungsmail entwerfen und zur Freigabe vorlegen) und pausiert dann
(FR-HITL-3) — das Committen/Ablehnen der Freigabe passiert außerhalb des
Loops in `app.agent.freigabe_service`, ausgelöst durch den Operator.
"""

from app.agent import tools
from app.agent.model_router import ModelRouter, SchemaValidierungFehlgeschlagen
from app.agent.schemas import EingehendeMail
from app.agent.trace_logger import TraceLogger
from app.agent.vector_store import DokumentenIndex
from app.config import settings
from app.models import (
    Fall,
    FallStatus,
    Nachricht,
    NachrichtRichtung,
    NachrichtStatus,
    TracePhase,
)
from sqlmodel import Session

HAUSVERWALTUNG_ABSENDER = "hausverwaltung@example.test"


def bearbeite_eingehende_mail(
    session: Session, router: ModelRouter, index: DokumentenIndex, mail: EingehendeMail
) -> Fall:
    # Im MVP ist „reparaturmeldung" der einzige unterstützte Falltyp (§1),
    # daher kann der Fall sofort angelegt werden — Trace-Einträge (DM-8)
    # benötigen von Anfang an eine gültige fall_id.
    from app.models import FallTyp

    fall = tools.fall_anlegen(session, FallTyp.reparaturmeldung, mail.betreff)
    trace = TraceLogger(session, fall.id)

    trace.log(TracePhase.wahrnehmung, f"Eingehende Mail von {mail.von}: „{mail.betreff}“")

    eingehende_nachricht = Nachricht(
        fall_id=fall.id,
        richtung=NachrichtRichtung.eingehend,
        von=mail.von,
        an=HAUSVERWALTUNG_ABSENDER,
        betreff=mail.betreff,
        inhalt=mail.inhalt,
        status=NachrichtStatus.empfangen,
    )
    session.add(eingehende_nachricht)
    session.commit()

    # --- Schritt: Einordnung (FR-AGENT-1, FR-AGENT-3) ---
    trace.log(TracePhase.plan, "Nächster Schritt: Fall einordnen (Tool fall_einordnen).")
    trace.log(TracePhase.tool_call, "fall_einordnen(mailinhalt=...)")
    try:
        einordnung, modell = tools.fall_einordnen(router, mail)
    except SchemaValidierungFehlgeschlagen as exc:
        trace.log(
            TracePhase.tool_result,
            f"fall_einordnen fehlgeschlagen: strukturierte Ausgabe ungültig ({exc}).",
        )
        return tools.fall_eskalieren(
            session, fall, "Einordnung lieferte keine gültige, schema-konforme Antwort."
        )

    trace.log(
        TracePhase.tool_result,
        f"Einordnung: typ={einordnung.typ.value}, gewerk={einordnung.gewerk}, "
        f"konfidenz={einordnung.konfidenz:.2f}. Begründung: {einordnung.begruendung}",
        modell=modell,
    )

    fall = tools.fall_aktualisieren(
        session,
        fall,
        gewerk=einordnung.gewerk,
        konfidenz=einordnung.konfidenz,
        zusammenfassung=einordnung.begruendung,
        status=FallStatus.eingeordnet,
    )
    trace.log(TracePhase.entscheidung, f"Status → {FallStatus.eingeordnet.value}")

    if einordnung.konfidenz < settings.konfidenz_schwelle:
        trace.log(
            TracePhase.reasoning,
            f"Konfidenz {einordnung.konfidenz:.2f} unter Schwelle "
            f"{settings.konfidenz_schwelle} → Eskalation statt Raten (FR-HITL-6).",
        )
        return tools.fall_eskalieren(session, fall, "Konfidenz unter Schwelle.")

    if einordnung.gewerk is None:
        trace.log(TracePhase.reasoning, "Kein Gewerk erkennbar → Eskalation.")
        return tools.fall_eskalieren(session, fall, "Kein Gewerk erkennbar.")

    # --- Schritt: Anreicherung — Objekt ---
    trace.log(TracePhase.plan, "Nächster Schritt: Objekt ermitteln (Tool objekt_suchen).")
    objekt_suchbegriff = einordnung.objekt_suchbegriff or mail.von
    trace.log(TracePhase.tool_call, f"objekt_suchen(suchbegriff={objekt_suchbegriff!r})")
    objekte = tools.objekt_suchen(session, objekt_suchbegriff)
    trace.log(TracePhase.tool_result, f"{len(objekte)} Objekt(e) gefunden.")

    if not objekte:
        trace.log(TracePhase.reasoning, "Kein passendes Objekt gefunden → Eskalation (FR-HITL-6).")
        return tools.fall_eskalieren(session, fall, "Kein passendes Objekt gefunden.")

    objekt = objekte[0]
    fall = tools.fall_aktualisieren(session, fall, objekt_id=objekt.id)

    # --- Schritt: Anreicherung — Melder ---
    trace.log(TracePhase.plan, "Nächster Schritt: Melder identifizieren (Tool kontakt_suchen).")
    melder_suchbegriff = einordnung.melder_suchbegriff or mail.von
    trace.log(TracePhase.tool_call, f"kontakt_suchen(suchbegriff={melder_suchbegriff!r})")
    kontakt = tools.kontakt_suchen(session, melder_suchbegriff)
    if kontakt is None:
        trace.log(TracePhase.tool_result, "Kein Kontakt gefunden.")
        tools.notiz_hinzufuegen(
            session, fall.id, "Melder konnte nicht eindeutig identifiziert werden."
        )
    else:
        trace.log(TracePhase.tool_result, f"Kontakt gefunden: {kontakt.name} ({kontakt.email}).")
        fall = tools.fall_aktualisieren(session, fall, melder_kontakt_id=kontakt.id)

    # --- Schritt: Anreicherung — Dienstleister ---
    trace.log(
        TracePhase.plan, "Nächster Schritt: Dienstleister ermitteln (Tool dienstleister_suchen)."
    )
    trace.log(TracePhase.tool_call, f"dienstleister_suchen(gewerk={einordnung.gewerk.value})")
    kandidaten = tools.dienstleister_suchen(session, einordnung.gewerk)
    trace.log(TracePhase.tool_result, f"{len(kandidaten)} aktive(r) Dienstleister gefunden.")

    if not kandidaten:
        trace.log(
            TracePhase.reasoning, "Kein passender aktiver Dienstleister → Eskalation (FR-HITL-6)."
        )
        return tools.fall_eskalieren(session, fall, "Kein passender Dienstleister gefunden.")

    dienstleister = kandidaten[0]
    fall = tools.fall_aktualisieren(session, fall, dienstleister_id=dienstleister.id)

    # --- Schritt: Anreicherung — Dokumente (Zuständigkeit/Kostenregelung) ---
    trace.log(
        TracePhase.plan,
        "Nächster Schritt: Dokumente auf Zuständigkeit/Kostenregelung prüfen "
        "(Tool dokumente_durchsuchen).",
    )
    frage = f"Zuständigkeit Kostenregelung {einordnung.gewerk.value} Reparatur"
    trace.log(TracePhase.tool_call, f"dokumente_durchsuchen(frage={frage!r})")
    treffer = tools.dokumente_durchsuchen(session, index, frage)
    quellen = ", ".join(d.titel for d in treffer) or "keine passende Passage gefunden"
    trace.log(TracePhase.tool_result, f"Herangezogene Dokumente: {quellen}")

    # --- Schritt: Vorschlag 1 — Beauftragungsmail entwerfen (§4.2 Schritt 4) ---
    trace.log(
        TracePhase.plan,
        "Nächster Schritt: Beauftragungsmail entwerfen (Tool nachricht_entwerfen). "
        "Versand ist freigabepflichtig und erfordert danach eine Freigabe (§5).",
    )
    kontext = (
        f"Objekt: {objekt.bezeichnung}, {objekt.adresse}\n"
        f"Anliegen: {einordnung.begruendung}\n"
        f"Auszug aus Originalmail: {mail.inhalt}\n"
        f"Herangezogene Dokumente: {quellen}"
    )
    trace.log(TracePhase.tool_call, "nachricht_entwerfen(zweck='Dienstleister beauftragen', ...)")
    entwurf = tools.nachricht_entwerfen(
        router,
        session,
        fall.id,
        von=HAUSVERWALTUNG_ABSENDER,
        an=dienstleister.email,
        betreff=f"[{fall.ticket_nummer}] Beauftragung: {mail.betreff}",
        zweck=f"{dienstleister.name} ({einordnung.gewerk.value}) mit der Behebung beauftragen",
        kontext=kontext,
    )
    trace.log(
        TracePhase.tool_result,
        f"Entwurf erstellt (Nachricht #{entwurf.id}, Status={entwurf.status.value}).",
        modell=settings.modell_stark,
    )

    # --- Schritt: Freigabe anfordern (FR-HITL-1, FR-HITL-2) ---
    trace.log(
        TracePhase.plan,
        "Nächster Schritt: Versand freigabepflichtig → Tool nachricht_senden "
        "legt nur eine Freigabe an (propose), führt nichts aus.",
    )
    begruendung = (
        f"{dienstleister.name} ist ein aktiver Dienstleister für Gewerk "
        f"'{einordnung.gewerk.value}'. Objekt: {objekt.bezeichnung}. "
        f"Einordnung: {einordnung.begruendung} Herangezogene Dokumente: {quellen}."
    )
    trace.log(TracePhase.tool_call, "nachricht_senden(nachricht_id=..., begruendung=...)")
    freigabe = tools.nachricht_senden(
        session,
        fall,
        entwurf,
        begruendung=begruendung,
        kontext_referenzen={
            "objekt_id": objekt.id,
            "dienstleister_id": dienstleister.id,
            "dokument_ids": [d.id for d in treffer],
            "original_mail": mail.inhalt,
        },
    )
    trace.log(
        TracePhase.tool_result,
        f"Freigabe #{freigabe.id} angelegt (Status={freigabe.status.value}) → Freigabe-Queue.",
    )
    trace.log(
        TracePhase.entscheidung,
        f"Status → {FallStatus.wartet_auf_freigabe.value}. Agent pausiert diesen Fall "
        "und arbeitet an anderen Fällen weiter (FR-HITL-3), bis der Operator entscheidet.",
    )

    return fall
