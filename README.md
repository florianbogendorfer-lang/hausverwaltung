# Hausverwaltungsagent (Prototyp)

Umsetzung des Lastenhefts „HITL-Agent für Hausverwaltung" — siehe dort für
den vollständigen Anforderungskatalog. Dieses Repository baut die Phasen aus
§16 nacheinander auf.

## Phase 1 — Fundament (aktueller Stand)

Enthalten: Projektgerüst, Datenmodell (§7, DM-1 bis DM-9), Alembic-Migrationen,
synthetische Seed-Daten (Objekte, Kontakte, Dienstleister, Dokumente) und
lesende REST-Endpunkte für die Stammdaten.

**Noch nicht enthalten** (spätere Phasen laut §16): Agent-Loop, HITL-
Freigabemechanismus, Web-GUI, RAG-Vektorsuche, echter Mail-Adapter.

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

# Server starten
uvicorn app.main:app --reload
```

### Prüfen

```bash
curl http://localhost:8000/health
curl http://localhost:8000/objekte
curl http://localhost:8000/dienstleister?gewerk=schlosser
```

### Tests

```bash
cd backend
pytest
```

## Datenmodell

Siehe `backend/app/models/` — jede Datei entspricht einer Tabelle aus §7 des
Lastenhefts (Docstring verweist auf die jeweilige DM-ID).

## Nächste Phasen

- Phase 2: Agent-Kern + Tools (extern gemockt), Trace-Logging, Modell-Routing
- Phase 3: HITL propose/commit, Freigabe-Queue, Eskalation, Audit-Log
- Phase 4: Web-GUI
- Phase 5: RAG über die Dokumentensammlung
- Phase 6: echter IMAP/SMTP-Adapter, weitere Anliegen-Typen
