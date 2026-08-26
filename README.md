# Hausverwaltungsagent (Prototyp)

Umsetzung des Lastenhefts „HITL-Agent für Hausverwaltung" — siehe dort für
den vollständigen Anforderungskatalog. Dieses Repository baut die Phasen aus
§16 nacheinander auf.

## Aktueller Stand: Phase 1 + Phase 2 + Phase 3

**Phase 1 — Fundament:** Projektgerüst, Datenmodell (§7, DM-1 bis DM-9),
Alembic-Migrationen, synthetische Seed-Daten (Objekte, Kontakte,
Dienstleister, Dokumente) und lesende REST-Endpunkte für die Stammdaten.

**Phase 2 — Agent-Kern + Tools:** ReAct-Loop (§8) für den Referenzfall
„Reparaturmeldung", Tool-Katalog (§9, `backend/app/agent/tools.py`),
Modell-Routing (FR-AGENT-2: günstiges Modell für die Einordnung, starkes
Modell für den Mailentwurf) und vollständiges Trace-Logging (DM-8). Ein
simulierter Postfach-Eingang (`POST /postfach/eingang`) stößt den Loop an:
Mail → Einordnung → Objekt/Kontakt/Dienstleister ermitteln →
Beauftragungsmail-Entwurf. Bei Unsicherheit (niedrige Konfidenz, kein
passendes Objekt/Dienstleister) eskaliert der Fall statt zu raten
(FR-HITL-6).

**Phase 3 — HITL propose/commit:** Die drei freigabepflichtigen Tools
(`nachricht_senden`, `dienstleister_beauftragen`, `rechnung_erfassen`)
führen nichts mehr direkt aus, sondern legen nur einen `freigaben`-Eintrag
an (propose, FR-HITL-1) und parken den Fall in `WARTET_AUF_FREIGABE`
(FR-HITL-3). Der Operator entscheidet über die Freigabe-Queue-API
(`GET/POST /freigaben/...`): **freigeben**, **bearbeiten** (Text ändern und
freigeben) oder **ablehnen** — der Ablehnungsgrund fließt als Notiz in den
Fall zurück (FR-HITL-5). Erst beim Commit wird die Aktion ausgeführt
(z. B. Mail in die simulierte Outbox, Status → `DIENSTLEISTER_BEAUFTRAGT`).
Eine bereits entschiedene Freigabe kann nicht erneut committet werden
(FR-HITL-8, Idempotenz) — der zweite Versuch liefert HTTP 409. Offene
Freigaben werden nach einer konfigurierbaren Frist als überfällig markiert,
aber nicht automatisch ausgeführt (FR-HITL-7). Die Policy, welche Tools
freigabepflichtig sind, steht zentral in `app/agent/policy.py` (FR-HITL-2)
— nicht im Modell-Prompt.

**Noch nicht enthalten** (spätere Phasen laut §16): Web-GUI, echte
RAG-Vektorsuche (Phase 2/3 nutzen eine einfache Stichwortsuche als
Platzhalter), echter Mail-Adapter.

### Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Migrationen anwenden
alembic upgrade head

# Seed-Daten laden (idempotent)
python -m app.seed

# Anthropic-API-Key setzen (für den Agent-Loop, §12)
export HV_ANTHROPIC_API_KEY=sk-...

# Server starten
uvicorn app.main:app --reload
```

### Prüfen

```bash
curl http://localhost:8000/health
curl http://localhost:8000/objekte
curl http://localhost:8000/dienstleister?gewerk=schlosser

# Referenzfall „Türschloss defekt" einspielen
curl -X POST http://localhost:8000/postfach/eingang \
  -H "Content-Type: application/json" \
  -d '{"von":"erika.musterfrau@example.test","betreff":"Türschloss defekt","inhalt":"Das Türschloss meiner Wohnung in der Musterstraße 5 ist kaputt. Erika Musterfrau"}'

# Trace des erzeugten Falls ansehen (Fall-Id aus der Antwort oben)
curl http://localhost:8000/faelle/1/trace

# Offene Freigabe-Queue ansehen und entscheiden (Freigabe-Id aus der Liste)
curl http://localhost:8000/freigaben
curl -X POST http://localhost:8000/freigaben/1/freigeben \
  -H "Content-Type: application/json" -d '{"entscheider":"operator@example.test"}'
curl -X POST http://localhost:8000/freigaben/1/ablehnen \
  -H "Content-Type: application/json" -d '{"entscheider":"operator@example.test","grund":"..."}'
```

### Tests

```bash
cd backend
pytest
```

Die Tests laufen ohne Netzwerkzugriff/API-Key — ein `FakeLLMClient`
(`backend/tests/fakes.py`) simuliert die Modellantworten deterministisch,
passend zum Grundsatz „externe Welt wird simuliert" (§0).

## Datenmodell

Siehe `backend/app/models/` — jede Datei entspricht einer Tabelle aus §7 des
Lastenhefts (Docstring verweist auf die jeweilige DM-ID).

## Agent-Kern

Siehe `backend/app/agent/`:
- `model_router.py` — Modell-Routing-Abstraktion (FR-AGENT-2), Provider
  austauschbar (NFR-5)
- `tools.py` — Tool-Katalog (§9)
- `loop.py` — ReAct-Loop für den Referenzfall (§4.2, FR-AGENT-1)
- `trace_logger.py` — Denk-/Schritt-Protokoll (DM-8)
- `policy.py` — zentrale Freigabe-Policy (FR-HITL-2)
- `freigabe_service.py` — Freigabe-Commit/-Ablehnung (FR-HITL-1/5/8)

## Nächste Phasen

- Phase 4: Web-GUI (Fall-Inbox, Freigabe-Queue, Fall-Detail mit Trace,
  Stammdatenpflege, simuliertes Postfach)
- Phase 5: echte RAG-Vektorsuche über die Dokumentensammlung
- Phase 6: echter IMAP/SMTP-Adapter, weitere Anliegen-Typen
