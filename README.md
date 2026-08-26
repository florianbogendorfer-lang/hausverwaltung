# Hausverwaltungsagent (Prototyp)

Umsetzung des Lastenhefts „HITL-Agent für Hausverwaltung" — siehe dort für
den vollständigen Anforderungskatalog. Dieses Repository baut die Phasen aus
§16 nacheinander auf.

## Aktueller Stand: Phase 1 + Phase 2 + Phase 3 + Phase 4

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

**Phase 4 — Web-GUI:** React + Vite + Tailwind-Operator-Oberfläche
(`frontend/`) gemäß §12/UI-1 bis UI-5: Fall-Inbox mit Statusfiltern und
Hervorhebung eskalierter/wartender Fälle (UI-1), Freigabe-Queue mit
aufklappbaren Karten (Auslöser, Entwurf, Begründung, Fakten — FR-HITL-4)
und Freigeben/Bearbeiten/Ablehnen (UI-2), Fall-Detail mit vollständiger
Trace-Timeline inkl. Modell pro Schritt (UI-3), Stammdatenpflege für
Objekte/Kontakte/Dienstleister (UI-4) sowie simuliertes Postfach mit
vorformulierten Test-Mails und Outbox (UI-5). Läuft **ohne** konfigurierten
`HV_ANTHROPIC_API_KEY` bereits vollständig vorführbar: ein regelbasierter
`DemoLLMClient` (`backend/app/agent/demo_llm_client.py`) übernimmt dann
Einordnung und Mailentwurf, damit der komplette Referenzfall auch ohne
Zugangsdaten durchspielbar ist — mit echtem Key wird automatisch die
Anthropic-API verwendet (reiner Konfigurationswechsel, NFR-5).

**Noch nicht enthalten** (spätere Phasen laut §16): echte RAG-Vektorsuche
(nutzt bisher eine einfache Stichwortsuche als Platzhalter), echter
Mail-Adapter, weitere Anliegen-Typen.

### Setup — Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Migrationen anwenden
alembic upgrade head

# Seed-Daten laden (idempotent)
python -m app.seed

# Optional: Anthropic-API-Key setzen (§12) — ohne Key läuft automatisch
# der regelbasierte Demo-Client (siehe oben)
export HV_ANTHROPIC_API_KEY=sk-...

# Server starten
uvicorn app.main:app --reload
```

### Setup — Frontend

```bash
cd frontend
npm install
npm run dev
```

Die GUI läuft auf `http://localhost:5173` und erwartet das Backend auf
`http://localhost:8000/api` (Default aus `frontend/.env.development`, CORS
ist dafür in `app/main.py` freigeschaltet). Ein anderer Backend-Host lässt
sich per `VITE_API_BASE_URL` überschreiben.

### Prüfen

Alle API-Routen liegen unter `/api` (nur `/health` liegt auf Root-Ebene) —
siehe [Deployment](#deployment-clever-cloud) für den Hintergrund.

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/objekte
curl http://localhost:8000/api/dienstleister?gewerk=schlosser

# Referenzfall „Türschloss defekt" einspielen
curl -X POST http://localhost:8000/api/postfach/eingang \
  -H "Content-Type: application/json" \
  -d '{"von":"erika.musterfrau@example.test","betreff":"Türschloss defekt","inhalt":"Das Türschloss meiner Wohnung in der Musterstraße 5 ist kaputt. Erika Musterfrau"}'

# Trace des erzeugten Falls ansehen (Fall-Id aus der Antwort oben)
curl http://localhost:8000/api/faelle/1/trace

# Offene Freigabe-Queue ansehen und entscheiden (Freigabe-Id aus der Liste)
curl http://localhost:8000/api/freigaben
curl -X POST http://localhost:8000/api/freigaben/1/freigeben \
  -H "Content-Type: application/json" -d '{"entscheider":"operator@example.test"}'
curl -X POST http://localhost:8000/api/freigaben/1/ablehnen \
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

## Web-GUI

Siehe `frontend/src/`:
- `pages/FallInbox.tsx` — UI-1
- `pages/FreigabeQueue.tsx` — UI-2
- `pages/FallDetail.tsx` — UI-3 (Trace-Timeline)
- `pages/Stammdaten.tsx` — UI-4
- `pages/Postfach.tsx` — UI-5 (Postfach + Outbox)
- `api.ts` / `types.ts` — schlanker API-Client + Typen, gespiegelt aus den
  Backend-Modellen

## Deployment (Clever Cloud)

Das Repo enthält ein Root-`Dockerfile` (Multi-Stage: baut `frontend/` und
liefert es über FastAPI aus demselben Container aus, siehe
`backend/app/main.py`/`FRONTEND_DIST`) sowie `docker-entrypoint.sh`
(Migrationen + Server-Start). Alle API-Routen liegen unter `/api`, damit
sie nicht mit den React-Router-Pfaden (`/faelle`, `/freigaben`, …)
kollidieren, wenn beides aus demselben Origin kommt.

**Vorgehen in der Clever-Cloud-Konsole:**

1. Neue App anlegen, Typ **„Docker"** wählen, das GitHub-Repo
   `florianbogendorfer-lang/hausverwaltung` (Branch der Wahl) verbinden.
2. Ein **PostgreSQL-Add-on** erstellen und mit der App verlinken — Clever
   Cloud injiziert dadurch automatisch `POSTGRESQL_ADDON_URI`, die der
   `docker-entrypoint.sh` beim Start in `HV_DATABASE_URL`
   (Schema `postgresql+psycopg://`) übersetzt. Kein manuelles Kopieren
   nötig.
3. Optional als Umgebungsvariable setzen: `HV_ANTHROPIC_API_KEY` (ohne
   Key läuft automatisch der regelbasierte `DemoLLMClient`, siehe oben).
4. `PORT` wird von Clever Cloud automatisch injiziert, der Container
   bindet daran (`docker-entrypoint.sh`, Fallback `8080` für lokale Tests).
5. Deploy auslösen — beim Containerstart laufen die Alembic-Migrationen
   automatisch (`alembic upgrade head`), danach startet Uvicorn.

**Lokal testen** (baut denselben Container, den Clever Cloud baut):

```bash
docker build -t hv-agent .
docker run -p 8080:8080 -e HV_DATABASE_URL=sqlite:///./test.db hv-agent
# Browser: http://localhost:8080  ·  curl http://localhost:8080/health
```

Falls das **Anlegen** der App in Clever Cloud weiterhin blockiert (nicht
nur der Build/Deploy fehlschlägt), liegt das erfahrungsgemäß an der
GitHub-App-Repo-Freigabe auf Clever-Cloud-Seite (Organisation/Repo nicht
für die Clever-Cloud-GitHub-Integration freigegeben) — das ist außerhalb
dieses Repos zu prüfen, nicht code-seitig lösbar.

## Nächste Phasen

- Phase 5: echte RAG-Vektorsuche über die Dokumentensammlung
- Phase 6: echter IMAP/SMTP-Adapter, weitere Anliegen-Typen
