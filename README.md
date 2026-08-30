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

Probeweise steht zusätzlich NVIDIA NIM (Nemotron, OpenAI-kompatible API)
als Alternative zu Mistral bereit (`NvidiaLLMClient`) — **aber bewusst
nicht per Konfiguration wählbar.** Der Umschalter dazu ist die
Code-Konstante `NVIDIA_STATT_MISTRAL` in `backend/app/config.py`
(aktuell `True`): solange sie auf `True` steht, läuft
`HV_LLM_PROVIDER=mistral` tatsächlich über NVIDIA statt Mistral — auf
`False` zurücksetzen, um wieder auf Mistral umzuschalten. Grund für den
Code- statt Env-Umschalter: es gibt (Stand jetzt) kein zugesagtes NVIDIA-
Produktionskontingent, nur einen persönlichen Zugang — ein Versehen in
der Deploy-Konfiguration soll den Provider daher nicht unbemerkt
umschalten können. Key über `HV_NVIDIA_API_KEY`, die bestehende
Mistral-Anbindung bleibt dabei vollständig erhalten.

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

**Bekannte CVEs, betreffen dieses Deployment nicht:** `pip-audit` meldet
für chromadb 1.5.9 (installiert, zum Zeitpunkt dieser Notiz noch ohne
offiziellen Patch) vier offene CVEs — u. a. CVE-2026-45829 (CVSS 10.0,
Pre-Auth-RCE) und CVE-2026-45833 (Code-Injection) im eigenständigen,
netzwerkexponierten Chroma-FastAPI-Server (`chroma run`), sowie
CVE-2026-45830/-45831 in Chromas optionalem RBAC-Autorisierungs-
Provider für Multi-Tenant-Server-Deployments. Diese App startet nie
einen solchen Server und konfiguriert keinen Autorisierungs-Provider;
`chromadb.PersistentClient` läuft rein lokal/eingebettet ohne eigenen
Netzwerk-Listener (siehe Sicherheitshinweis in `vector_store.py`).
Trotzdem im Auge behalten und aktualisieren, sobald Patches erscheinen
— und diesen eingebetteten Modus nicht durch einen `chroma run`-Server
oder eine RBAC-Konfiguration ersetzen, solange die Lücken offen sind.

**Phase 6 — Mail-Adapter-Architektur:**
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
erkennen lässt, ob wirklich etwas rausging.

Der eingehende Kanal war seit Phase 2 nur simuliert (`POST
/api/postfach/eingang`) — Sorge dabei: Kommunikation, die außerhalb dieser
manuellen Einspielung passiert (z. B. eine Antwort direkt im echten
Postfach des Bearbeiters), taucht im System nie auf und "verschwindet"
faktisch. `app/agent/imap_adapter.py` + `POST /api/postfach/abrufen`
schließen diese Lücke mit einem echten, per `HV_IMAP_HOST` (+
`HV_IMAP_PORT`/`HV_IMAP_BENUTZER`/`HV_IMAP_PASSWORT`/`HV_IMAP_ORDNER`,
gleiches Muster wie SMTP) konfigurierbaren IMAP-Abruf: jede ungelesene
Mail landet entweder — falls der Betreff eine bekannte Ticketnummer
enthält (z. B. eine Dienstleister-Antwort) — als neue Nachricht am
bestehenden Fall, oder wird (wie bislang die simulierte Einspielung) über
den vollen Agent-Loop zu einem neuen Fall. Bewusst manuell auslösbar
(Button "Postfach abrufen" auf der Postfach-Seite) statt über einen
Hintergrund-Scheduler — kein zusätzlicher Infrastruktur-Prozess nötig, ein
Klick reicht für einen ersten Testlauf. Ohne `HV_IMAP_HOST` bleibt der
Endpunkt schlicht nicht verfügbar (404), am bisherigen Verhalten ändert
sich nichts. HTML-Mails/Anhänge werden (noch) nicht ausgewertet.

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
siehe [Deployment](#deployment-clever-cloud) für den Hintergrund. Bis auf
Login/Logout und die öffentliche Kundenansicht (`/api/ticket/{token}`)
verlangen alle Routen eine gültige Session (siehe
[Nutzer/Login](#nutzer-und-login) unten) — die Beispiele hier loggen sich
daher zuerst per Cookie-Jar ein.

```bash
curl http://localhost:8000/health

# Einloggen (Demo-Zugangsdaten, siehe unten) — Cookie-Jar für die Folgeaufrufe
curl -c /tmp/hv-cookies.txt -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" -d '{"email":"admin@example.test","passwort":"admin123"}'

curl -b /tmp/hv-cookies.txt http://localhost:8000/api/objekte
curl -b /tmp/hv-cookies.txt "http://localhost:8000/api/dienstleister?gewerk=schlosser"

# Referenzfall „Türschloss defekt" einspielen
curl -b /tmp/hv-cookies.txt -X POST http://localhost:8000/api/postfach/eingang \
  -H "Content-Type: application/json" \
  -d '{"von":"erika.musterfrau@example.test","betreff":"Türschloss defekt","inhalt":"Das Türschloss meiner Wohnung in der Musterstraße 5 ist kaputt. Erika Musterfrau"}'

# Trace des erzeugten Falls ansehen (Fall-Id aus der Antwort oben)
curl -b /tmp/hv-cookies.txt http://localhost:8000/api/faelle/1/trace

# Offene Freigabe-Queue ansehen und entscheiden (Freigabe-Id aus der Liste) —
# "entscheider" kommt aus der Session, nicht aus dem Request-Body (siehe unten)
curl -b /tmp/hv-cookies.txt http://localhost:8000/api/freigaben
curl -b /tmp/hv-cookies.txt -X POST http://localhost:8000/api/freigaben/1/freigeben \
  -H "Content-Type: application/json" -d '{}'
curl -b /tmp/hv-cookies.txt -X POST http://localhost:8000/api/freigaben/1/ablehnen \
  -H "Content-Type: application/json" -d '{"grund":"..."}'
```

### Nutzer und Login

Rollen-Login statt offenem Zugriff (`backend/app/auth.py`,
`backend/app/routers/auth.py`): Session-Cookie (HttpOnly, SameSite=Lax,
im Deploy zusätzlich Secure — siehe unten), bcrypt-Passwort-Hashing,
zwei Rollen (`admin` darf Fälle löschen und Benutzer verwalten, `user`
darf alles andere). Härtung nach OWASP Authentication Cheat Sheet:
zeitkonstanter Login-Vergleich gegen User-Enumeration, Konto-Lockout mit
exponentiell wachsender Sperrdauer nach 5 Fehlversuchen, zusätzliche
IP-Rate-Bremse gegen "Lockout als DoS" (`app/rate_limit.py`), 15-Zeichen-
Mindestlänge statt Komplexitätsregeln.

`python -m app.seed` legt zwei Demo-Konten an:
`admin@example.test` / `admin123` (Admin) und `user@example.test` /
`user1234` (User). Die Passwörter kommen aus `HV_SEED_ADMIN_PASSWORT`/
`HV_SEED_USER_PASSWORT` — **auf einem öffentlich erreichbaren Deployment
unbedingt auf starke, zufällige Werte setzen**, sonst trägt der
Admin-Login ein aus diesem Repo bekanntes, triviales Passwort.

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

### Linting

```bash
cd backend && ruff check .          # Pyflakes + Pycodestyle-Kernregeln
cd frontend && npx oxlint           # React-/TS-Lint
cd frontend && npx tsc -b --noEmit  # TypeScript strict mode
cd frontend && npm test             # Vitest — reine Logik (z. B. api.ts-Fehlerbehandlung)

# CVE-Scan gegen die tatsächlich installierten Versionen (nicht nur
# gegen die Versionsbereiche in pyproject.toml/package-lock.json) —
# unregelmäßig laufen lassen, deckt z. B. die dokumentierte
# chromadb-Lücke oben auf.
cd backend && pip install pip-audit && python -m pip_audit
cd frontend && npm audit
```

`.github/workflows/ci.yml` führt Tests, Linter und den Produktions-Build
bei jedem Push/PR automatisch aus (Backend-, Frontend- und Migrations-Job
parallel). Backend/Frontend-Jobs sind netzwerkfrei und brauchen keine
Secrets; der Migrations-Job spielt die komplette Alembic-Kette (`alembic
upgrade head`, dann `python -m app.seed`) gegen einen echten
Postgres-Service-Container — die Tests selbst laufen gegen SQLite
(`SQLModel.create_all`, kein Alembic), ohne diesen Job wäre ein
Postgres-inkompatibles Migrations-Statement erst beim echten
Clever-Cloud-Deploy aufgefallen. `.github/dependabot.yml` öffnet
wöchentlich Update-PRs für pip/npm/Docker/GitHub-Actions-Abhängigkeiten
innerhalb der in `backend/pyproject.toml` gesetzten Versions-Obergrenzen
— jeder davon läuft automatisch durch dieselbe CI.

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

### Dienstleister-Terminportal

Statt den vom Dienstleister vorgeschlagenen Termin aus einer Freitext-
Mail-Antwort herausparsen zu müssen (fehleranfällig, nicht zuverlässig
strukturiert), enthält die Beauftragungsmail einen Link zu einem eigenen,
login-freien Portal (`/dienstleister-portal/{token}`,
`backend/app/routers/dienstleister_portal.py`
+ `frontend/src/pages/DienstleisterPortal.tsx`). Dort bestätigt der
Dienstleister den Termin über ein Formular (Fall wechselt
`DIENSTLEISTER_BEAUFTRAGT` → `TERMIN_BESTAETIGT`) und meldet später die
Erledigung (`TERMIN_BESTAETIGT` → `ARBEIT_ERLEDIGT`). Eigenes
Zugriffs-Token (`Fall.dienstleister_zugriffstoken`, 192 Bit Entropie),
getrennt vom Kunden-`zugriffstoken` — beide Parteien sehen unterschiedliche
Ausschnitte desselben Falls und dürfen unterschiedliche Aktionen auslösen.

Die öffentliche Basis-URL für diesen Link braucht keine manuelle
Konfiguration: `POST /api/postfach/eingang` (`backend/app/routers/postfach.py`)
leitet sie aus dem eingehenden Request ab (`request.base_url`) — der
Endpunkt wird immer vom eigenen Frontend auf genau der Domain aufgerufen,
unter der die App gerade läuft, das funktioniert also lokal wie im Deploy
gleichermaßen ohne Setup. `HV_OEFFENTLICHE_BASIS_URL` bleibt als expliziter
Override nutzbar, falls die abgeleitete URL nicht passt (z. B. eine eigene
Domain statt der Clever-Cloud-Vorschau-URL).

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
   siehe oben — ist `HV_LLM_PROVIDER` gesetzt, aber der zugehörige Key
   fehlt, scheitert der Start bewusst sofort mit einer klaren Meldung
   statt später kryptisch beim ersten Mail-Eingang). Ebenfalls optional:
   `HV_SMTP_HOST`/`HV_SMTP_PORT`/`HV_SMTP_BENUTZER`/`HV_SMTP_PASSWORT`/
   `HV_SMTP_ABSENDER` für echten Mailversand (§16 Phase 6) — ohne diese
   Variablen bleibt der Versand vollständig simuliert. Ebenso optional:
   `HV_IMAP_HOST`/`HV_IMAP_PORT`/`HV_IMAP_BENUTZER`/`HV_IMAP_PASSWORT`/
   `HV_IMAP_ORDNER` für den echten Postfach-Abruf (Button „Postfach
   abrufen" auf der Postfach-Seite, siehe oben) — ohne `HV_IMAP_HOST`
   bleibt nur die simulierte Einspielung verfügbar. **Dringend
   empfohlen, sobald `HV_COOKIE_SECURE` aktiv ist** (siehe unten):
   `HV_SEED_ADMIN_PASSWORT`/`HV_SEED_USER_PASSWORT` auf starke, zufällige
   Werte setzen (siehe [Nutzer/Login](#nutzer-und-login)) — fehlen sie,
   erzeugt der Start automatisch ein zufälliges Passwort und schreibt es
   einmalig klar ins Deploy-Log (`app/config.py`), damit der öffentlich
   erreichbare Admin-Login nicht unbemerkt das im Repo sichtbare
   Demo-Passwort trägt UND der Deploy trotzdem nicht blockiert. Das
   Zufallspasswort aus dem allerersten erfolgreichen Deploy-Log notieren
   (spätere Neustarts erzeugen neue, ungenutzte Werte, da der Seed-Lauf
   idempotent ist) oder gleich eigene Werte setzen.
   `HV_COOKIE_SECURE` setzt `docker-entrypoint.sh` im Deploy-Pfad bereits
   automatisch auf `true` (TLS-Terminierung durch Clever Cloud), das muss
   normalerweise nicht manuell gesetzt werden. Der Link zum Dienstleister-
   Terminportal (`/dienstleister-portal/{token}`, login-frei) in der
   Beauftragungsmail braucht ebenfalls keine manuelle Konfiguration — die
   Basis-URL wird automatisch aus dem eingehenden Request abgeleitet (siehe
   [Dienstleister-Terminportal](#dienstleister-terminportal)). Nur falls
   die abgeleitete URL nicht passen sollte (z. B. eine eigene Domain statt
   der Clever-Cloud-Vorschau-URL), optional `HV_OEFFENTLICHE_BASIS_URL`
   (z. B. `https://hv.example.com`, ohne abschließenden Slash) als
   Override setzen.
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

- Weitere Anliegen-Typen über „Reparaturmeldung" hinaus
- Siehe [Production-Readiness](#production-readiness) für den aktuellen
  Stand Richtung echten Produktivbetrieb (Monitoring, Backups,
  horizontale Skalierung).

## Production-Readiness

Der aktuelle Stand ist für Einzel-Container-Betrieb mit überschaubarem
Traffic ausgelegt (siehe z. B. `NullPool` in `backend/app/db.py`,
In-Memory-Rate-Limiting in `backend/app/rate_limit.py`). Für echten
Produktivbetrieb zu beachten:

- **Stille Fake-Fallbacks**: Ohne `HV_ANTHROPIC_API_KEY`/`HV_LLM_PROVIDER`
  läuft der Agent mit `DemoLLMClient` (regelbasierte Stichwortsuche statt
  echtem LLM); ohne `HV_SMTP_HOST` wird Mailversand nur simuliert. Ist
  `HV_COOKIE_SECURE` aktiv (Produktions-Indikator, siehe unten) und einer
  dieser Fälle liegt vor, schreibt `backend/app/config.py` beim Start eine
  unübersehbare `WARNUNG:`-Zeile ins Log — Deploy-Logs nach dem ersten
  Start darauf prüfen.
- **`/health`** prüft inzwischen auch die DB-Erreichbarkeit (nicht nur
  „Prozess läuft") und liefert `503`, falls die Datenbank nicht erreichbar
  ist — der Docker-`HEALTHCHECK` wertet das korrekt als unhealthy.
- **Backups**: Kein automatisiertes Backup-Konzept im Repo. Bei Clever
  Cloud Postgres das Backup-Feature des Add-ons aktivieren/prüfen und
  einmal einen Restore testen, bevor echte Daten anfallen — ohne das ist
  ein Datenverlust nicht wiederherstellbar.
- **Migrationen**: `alembic upgrade head` läuft automatisch bei jedem
  Containerstart (`docker-entrypoint.sh`). Bei mehreren parallelen
  Instanzen ist das eine potenzielle Race Condition; bei einer
  fehlschlagenden Migration gibt es aktuell kein dokumentiertes
  Rollback-Vorgehen außer manuell `alembic downgrade` gegen die
  Produktions-DB auszuführen (vorher Backup ziehen, siehe oben).
- **Monitoring**: Optionales Sentry-Error-Tracking über `HV_SENTRY_DSN`
  (+ optional `HV_SENTRY_ENVIRONMENT`, sonst automatisch `produktion`/
  `entwicklung` je nach `HV_COOKIE_SECURE`) — ohne DSN bleibt Sentry
  inaktiv und es erscheint eine `WARNUNG:`-Zeile im Produktions-Log (siehe
  oben). Jeder Request bekommt zusätzlich eine Request-ID
  (`app/observability.py`, Header `X-Request-Id`, auch im Security-
  Audit-Log verknüpft) zur Korrelation gleichzeitiger Requests im Log.
  Das Frontend hat ein analoges, ebenfalls optionales Sentry-Tracking
  (`frontend/src/sentry.ts`, fängt u. a. Rendering-Fehler in der
  `ErrorBoundary`) — hier aber über `VITE_SENTRY_DSN`/
  `VITE_SENTRY_ENVIRONMENT` als **Docker-Build-ARG** (`docker build
  --build-arg VITE_SENTRY_DSN=...`, siehe `Dockerfile`), nicht als
  normale Laufzeit-Umgebungsvariable — Vite ersetzt `import.meta.env.*`
  bereits beim Build statisch, eine erst zur Laufzeit gesetzte Variable
  käme zu spät. Falls die verwendete Deployment-Pipeline (z. B. Clever
  Cloud) keine eigenen Build-ARGs erlaubt, bleibt das Frontend-Tracking
  inaktiv — das Backend-Tracking über `HV_SENTRY_DSN` ist davon unberührt
  und deckt bereits alle serverseitigen Fehler ab.
- **Rate-Limiting**: In-Memory, bewusst für Single-Container gebaut — bei
  horizontaler Skalierung (mehrere Instanzen) wird das Limit effektiv mit
  der Instanzzahl multipliziert. Vor einer Skalierung auf Redis-basiertes
  Rate-Limiting umstellen.
- **Tests**: Backend-Testabdeckung ist umfangreich (~160 Tests), Frontend
  deutlich dünner (4 Testdateien) und ohne E2E-Tests — beim Ausbau
  priorisieren.
