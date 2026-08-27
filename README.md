# Hausverwaltungsagent (Prototyp)

Umsetzung des Lastenhefts „HITL-Agent für Hausverwaltung" — siehe dort für
den vollständigen Anforderungskatalog. Dieses Repository baut die Phasen aus
§16 nacheinander auf.

## Aktueller Stand: Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 5 + Phase 6 (Adapter-Architektur)

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
(`frontend/`) gemäß §12/UI-1 bis UI-5. Statt vier lose verbundener Seiten
ist das UI seit einem UX-Überarbeitungsdurchgang um den tatsächlichen
Verarbeitungsfluss (§4.1) herum aufgebaut — siehe
[„Web-GUI"](#web-gui-kanban-board-statt-getrennter-listen) unten für den
Aufbau. Läuft **ohne** konfigurierten API-Key bereits vollständig
vorführbar: ein regelbasierter `DemoLLMClient`
(`backend/app/agent/demo_llm_client.py`) übernimmt dann Einordnung und
Mailentwurf, damit der komplette Referenzfall auch ohne Zugangsdaten
durchspielbar ist. Der LLM-Anbieter ist austauschbar (`LLMClient`-
Protokoll, `backend/app/agent/model_router.py`) — Anthropic und Mistral
AI (günstiger, EU-gehostet) stehen beide bereit, gewählt wird rein per
Konfiguration (NFR-5) über `HV_LLM_PROVIDER=anthropic|mistral|demo` plus
dem passenden `HV_ANTHROPIC_API_KEY`/`HV_MISTRAL_API_KEY`. Ohne
`HV_LLM_PROVIDER` gilt zur Abwärtskompatibilität: Anthropic-Key gesetzt
→ Anthropic, sonst Demo.

**Phase 5 — RAG-Vektorsuche:** `dokumente_durchsuchen` nutzt jetzt einen
echten, von der DB getrennten Vektorspeicher (§6/§12) statt der früheren
Stichwortzählung: [Chroma](https://www.trychroma.com/) mit eingebauter
ONNX-Embedding-Funktion (kein API-Key nötig), gekapselt in
`backend/app/agent/vector_store.py::DokumentenIndex`. Der Index wird bei
jedem App-Start aus der Tabelle `dokumente` neu aufgebaut — abgeleitete
Daten, die DB bleibt das System of Record (kein persistentes Docker-Volume
für `chroma_data/` nötig). Damit findet der Agent auch bei umformulierten
Anfragen die passende Dokumentpassage (z. B. „Wer bezahlt, wenn das
Türschloss kaputt geht?" → Hausordnung/Mustermietvertrag, ganz ohne
wörtliche Übereinstimmung). Wie beim `ModelRouter` ist die Embedding-
Funktion injizierbar: Tests laufen mit einem In-Memory-Index und einem
deterministischen Hash-Embedding (`tests/fakes.py::FakeEmbeddingFunction`)
weiterhin komplett netzwerkfrei (§0).

**Phase 6 — Mail-Adapter-Architektur (bewusst weiter simuliert):**
`app/agent/mail_adapter.py` formalisiert den ausgehenden Kanal als
austauschbare `MailAdapter`-Schnittstelle — dieselbe Dependency-Injection
wie bei `ModelRouter`/`DokumentenIndex`. `freigabe_service.freigeben` kennt
nur das Protokoll, nicht die konkrete Implementierung. Default bleibt
`SimulierterMailAdapter` (§0/§2.2: kein echter Mailversand im Prototyp).
Es gibt zusätzlich einen echten, funktionierenden `SmtpMailAdapter`
(STARTTLS über `smtplib`) — der wird aber **nur aktiv**, wenn `HV_SMTP_HOST`
explizit gesetzt wird (`get_mail_adapter()` wählt danach, analog zum
`HV_ANTHROPIC_API_KEY`-Umschalter). Ohne SMTP-Konfiguration ändert sich am
Verhalten nichts. Ein `NachrichtStatus.gesendet` (echt) ergänzt das
bisherige `gesendet_simuliert`, damit das Audit-Log (§11) im Zweifel
erkennen lässt, ob wirklich etwas rausging. Der eingehende Kanal
(simuliertes Postfach, `POST /api/postfach/eingang`) hatte seine
Austauschstelle bereits seit Phase 2 — echter IMAP-Eingang und weitere
Anliegen-Typen bleiben offen für einen späteren Durchgang.

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

# Optional: LLM-Anbieter wählen (§12) — ohne Konfiguration läuft
# automatisch der regelbasierte Demo-Client (siehe oben)
export HV_LLM_PROVIDER=anthropic   # oder: mistral
export HV_ANTHROPIC_API_KEY=sk-...
# export HV_MISTRAL_API_KEY=...    # falls HV_LLM_PROVIDER=mistral

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

Die Tests laufen ohne Netzwerkzugriff/API-Key — ein `FakeLLMClient` und
eine `FakeEmbeddingFunction` (`backend/tests/fakes.py`) simulieren
Modellantworten bzw. Dokumenten-Embeddings deterministisch, passend zum
Grundsatz „externe Welt wird simuliert" (§0). Der erste Lauf, der den
*echten* Chroma-Index nutzt (z. B. beim manuellen Server-Start), lädt
einmalig das ~80-MB-ONNX-Embedding-Modell nach — im Docker-Image ist das
bereits vorab gebacken (siehe `Dockerfile`).

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
- `vector_store.py` — Chroma-Vektorindex für `dokumente_durchsuchen` (§16
  Phase 5)
- `mail_adapter.py` — austauschbarer Versandkanal (§16 Phase 6), Default
  simuliert

## Web-GUI — Kanban-Board statt getrennter Listen

Die ursprüngliche UI (Phase 4) hatte vier lose verbundene Seiten
(Fall-Inbox-Tabelle, separate Freigabe-Queue-Liste, Postfach, Stammdaten)
— fachlich korrekt, aber die Freigabe-Entscheidung war vom Fallkontext
getrennt, und nichts zeigte den Verarbeitungsfluss (§4.1) auf einen Blick.
Ein UX-Überarbeitungsdurchgang hat das Board um den Fluss selbst
aufgebaut, angelehnt an Kanban-Boards (Linear/Trello) und die Board-Sicht
von Support-/Wartungs-Ticketsystemen (Zendesk, AppFolio/Buildium
Maintenance-Boards — Spalte = Status, Karte = Vorgang, Priorität als
eigene Zeile statt eigener Spalte):

- **`pages/Board.tsx`** (UI-1, Startseite) — Kanban-Board, Spalten =
  gruppierte Pipeline-Phasen (`Neu` · `Eingeordnet` · `Wartet auf
  Freigabe` — hervorgehoben, das ist die Aktions-Spalte — · `In
  Bearbeitung` · `Abgeschlossen`), eskalierte Fälle als eigene rote Zeile
  oberhalb der Spalten (Eskalation ist „jederzeit" möglich, §4.1, kein
  regulärer Pipeline-Schritt). **Bewusst kein Drag & Drop:** Statuswechsel
  laufen über die Agent-/Freigabe-Logik (HITL), nicht über freies
  Verschieben — das Board ist eine Sicht auf den Zustand, keine
  Bedienoberfläche dafür (das hätte eine falsche Erwartung geweckt).
- **`components/FreigabeKarte.tsx`** (vormals eigene UI-2-Seite) — die
  Freigabe-Karte (Auslöser, Entwurf, Begründung, Fakten — FR-HITL-4;
  Freigeben/Bearbeiten/Ablehnen — FR-HITL-5) erscheint jetzt direkt oben
  in `FallDetail`, wenn eine offene Freigabe vorliegt — Entscheidungen
  fallen im vollen Fallkontext, nicht aus einer entkoppelten globalen
  Liste heraus (Best Practice aus Human-in-the-Loop-Approval-UX: Kontext
  neben der Entscheidung vermeidet „Rubber-Stamping").
- **`pages/FallDetail.tsx`** (UI-3) — Freigabe-Karte (falls offen) +
  Trace-Timeline inkl. Modell pro Schritt + Nachrichtenverlauf.
- **`pages/Stammdaten.tsx`** (UI-4), **`pages/Postfach.tsx`** (UI-5,
  Postfach + Outbox) — unverändert.
- Nav-Badge auf „Board" zeigt die Anzahl offener Freigaben (Inbox-
  Badge-Muster, wie bei Mail-/Chat-Apps) — sichtbar von jeder Seite aus.
- `api.ts` / `types.ts` — schlanker API-Client + Typen, gespiegelt aus den
  Backend-Modellen.

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
3. Optional als Umgebungsvariablen setzen: `HV_LLM_PROVIDER` (`anthropic`
   oder `mistral`) plus `HV_ANTHROPIC_API_KEY`/`HV_MISTRAL_API_KEY` (ohne
   Konfiguration läuft automatisch der regelbasierte `DemoLLMClient`,
   siehe oben). Ebenfalls optional: `HV_SMTP_HOST`/`HV_SMTP_PORT`/`HV_SMTP_BENUTZER`/
   `HV_SMTP_PASSWORT`/`HV_SMTP_ABSENDER` für echten Mailversand (§16
   Phase 6) — ohne diese Variablen bleibt der Versand vollständig
   simuliert.
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

## Offen

- Echter IMAP-Eingang (der ausgehende Kanal ist als Adapter vorbereitet,
  siehe Phase 6 oben — der eingehende noch nicht)
- Weitere Anliegen-Typen über „Reparaturmeldung" hinaus
