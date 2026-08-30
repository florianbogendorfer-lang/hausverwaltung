"""FastAPI-Einstiegspunkt.

Phase 1 (§16, Fundament): lesende Stammdaten-Endpunkte.
Phase 2 (§16, Agent-Kern + Tools): simulierter Postfach-Eingang stößt den
Agent-Loop an; Fall-/Trace-Endpunkte machen den Lauf nachvollziehbar.
Phase 3 (§16, HITL propose/commit): Freigabe-Queue-Endpunkte für
Freigeben/Bearbeiten/Ablehnen.
Phase 4 (§16, GUI): CRUD-Endpunkte für Stammdaten + Outbox-Endpunkt und
CORS für die React-Operator-Oberfläche (`frontend/`).
Phase 5 (§16, RAG): der Vektorindex für `dokumente_durchsuchen` wird beim
Start aus der Tabelle `dokumente` neu aufgebaut (siehe `lifespan` unten).

Deployment: alle API-Routen liegen unter `/api`, damit sie nicht mit den
gleichnamigen React-Router-Pfaden (`/faelle`, `/freigaben`, …) kollidieren,
wenn das gebaute Frontend aus demselben Container ausgeliefert wird (siehe
Dockerfile + `FRONTEND_DIST`-Block unten).
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.auth import aktueller_benutzer
from app.config import settings
from app.db import create_db_and_tables, engine, get_session
from app.models import Dokument, MAX_BELEG_GROESSE_BYTES
from app.observability import init_sentry, log_unbehandelte_ausnahme, neue_request_id, request_id_var
from app.routers import (
    auth,
    benutzer,
    dienstleister,
    dienstleister_portal,
    dokumente,
    faelle,
    freigaben,
    kontakte,
    objekte,
    outbox,
    postfach,
    ticket,
)
from app.routers.postfach import get_dokumenten_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    # §16 Phase 5: der Chroma-Index ist abgeleitete Daten — bei jedem Start
    # aus der DB (System of Record) neu aufgebaut, robust auch ohne
    # persistentes Docker-Volume für chroma_data/.
    with Session(engine) as session:
        alle_dokumente = list(session.exec(select(Dokument)).all())
    get_dokumenten_index().indizieren(alle_dokumente)
    yield


# Muss vor der FastAPI-App-Erzeugung laufen (siehe Docstring in
# app/observability.py) — ohne HV_SENTRY_DSN ein reines No-Op.
init_sentry()

app = FastAPI(
    title="Hausverwaltungsagent (Prototyp)",
    description="Backend für den HITL-Agenten",
    version="0.5.0",
    lifespan=lifespan,
)

# Prototyp mit einem lokalen Operator (§3) — permissive CORS für die lokal
# laufende Vite-Dev-GUI genügt, kein produktiver Härtungsanspruch. Im
# Docker-Deploy läuft das Frontend ohnehin auf demselben Origin (kein CORS
# nötig), diese Regel betrifft nur den lokalen Dev-Workflow. allow_credentials
# ist nötig, damit das Session-Cookie (§0-Login) auch cross-origin (Vite-Dev-
# Server) mitgeschickt wird — deshalb explizite Origins statt Wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OWASP API Security Top 10 (API4:2023 — Unrestricted Resource Consumption):
# ohne Obergrenze für die Request-Body-Größe könnte ein einzelner Request
# beliebig viel Arbeitsspeicher/Bandbreite verbrauchen, bevor Pydantic die
# einzelnen Feld-Obergrenzen (max_length, siehe Router) überhaupt zu sehen
# bekommt — die greifen erst NACH dem vollständigen Einlesen/Parsen des
# Bodies. Auf MAX_BELEG_GROESSE_BYTES abgestimmt (größte erwartete
# Nutzlast: ein hochgeladener Rechnungsbeleg, siehe
# app/models/rechnungsbeleg.py) — für alle anderen Endpunkte (Mailtext
# max. 20.000 Zeichen, siehe app/agent/schemas.py) weiterhin großzügig.
_MAX_BODY_BYTES = MAX_BELEG_GROESSE_BYTES


class KoerpergroesseBegrenzenMiddleware:
    """Reine ASGI-Middleware statt `@app.middleware("http")`: eine reine
    Content-Length-Prüfung (frühere Version dieser Middleware) schützt
    NICHT gegen Transfer-Encoding: chunked — dabei fehlt der Content-Length-
    Header völlig, ein Angreifer könnte darüber einen beliebig großen Body
    einschleusen, ohne dass die Header-Prüfung je greift. Diese Middleware
    zählt stattdessen die tatsächlich am ASGI-`receive`-Kanal eintreffenden
    Bytes selbst — unabhängig von der Kodierung — und bricht ab, sobald das
    Limit überschritten wird, bevor FastAPI/Pydantic den Body vollständig in
    den Speicher liest."""

    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        gesehen = 0

        async def begrenztes_receive():
            nonlocal gesehen
            nachricht = await receive()
            if nachricht["type"] == "http.request":
                gesehen += len(nachricht.get("body", b""))
                if gesehen > self.max_bytes:
                    raise HTTPException(status_code=413, detail="Anfrage zu groß.")
            return nachricht

        await self.app(scope, begrenztes_receive, send)


app.add_middleware(KoerpergroesseBegrenzenMiddleware, max_bytes=_MAX_BODY_BYTES)


# OWASP Secure Headers Project: Basisschutz gegen MIME-Sniffing, Clickjacking
# und übermäßiges Referrer-Leaking — kostet nichts, hat aber ohne diese
# Middleware bisher komplett gefehlt. CSP erlaubt gezielt Google Fonts
# (index.html lädt sie fest ein — style-src für das <link rel="stylesheet">,
# font-src für die eigentlichen Font-Dateien von fonts.gstatic.com), sonst
# nur same-origin: kein weiteres externes CDN im Einsatz.
@app.middleware("http")
async def sicherheits_header_setzen(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "object-src 'none'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; base-uri 'self'"
    )
    # HSTS nur wenn wir wissen, dass wir hinter TLS laufen (cookie_secure
    # wird von docker-entrypoint.sh im Deploy-Pfad automatisch gesetzt) —
    # sonst würde ein lokaler http://-Dev-Server Browsern fälschlich
    # "immer HTTPS erzwingen" beibringen.
    if settings.cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# Request-ID zur Korrelation von Log-Zeilen über einen einzelnen Request
# hinweg (app/observability.py) — ohne das lassen sich gleichzeitige
# Requests im stdout-Log kaum auseinanderhalten. Übernimmt eine vom Client
# mitgeschickte X-Request-Id (z. B. von einem vorgelagerten Load Balancer),
# statt sie immer neu zu erzeugen, damit ein Request über mehrere Hops
# hinweg dieselbe ID behält.
@app.middleware("http")
async def request_id_setzen(request: Request, call_next):
    anfrage_id = neue_request_id(request.headers.get("X-Request-Id"))
    token = request_id_var.set(anfrage_id)
    try:
        response = await call_next(request)
    except Exception as exc:
        log_unbehandelte_ausnahme(exc)
        raise
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-Id"] = anfrage_id
    return response


# Login/Logout und die öffentliche Kundenansicht bleiben unauthentifiziert
# erreichbar — alle übrigen Routen verlangen eine gültige Session (§0-Wunsch:
# Nutzersystem mit Rollen statt offenem Zugriff).
app.include_router(auth.router, prefix="/api")
app.include_router(ticket.router, prefix="/api")
app.include_router(dienstleister_portal.router, prefix="/api")

_angemeldet = [Depends(aktueller_benutzer)]
app.include_router(objekte.router, prefix="/api", dependencies=_angemeldet)
app.include_router(kontakte.router, prefix="/api", dependencies=_angemeldet)
app.include_router(dienstleister.router, prefix="/api", dependencies=_angemeldet)
app.include_router(dokumente.router, prefix="/api", dependencies=_angemeldet)
app.include_router(faelle.router, prefix="/api", dependencies=_angemeldet)
app.include_router(postfach.router, prefix="/api", dependencies=_angemeldet)
app.include_router(freigaben.router, prefix="/api", dependencies=_angemeldet)
app.include_router(outbox.router, prefix="/api", dependencies=_angemeldet)
# benutzer.router ist bereits intern admin_erforderlich-gated (impliziert
# aktueller_benutzer), daher hier ohne zusätzliche Dependency.
app.include_router(benutzer.router, prefix="/api")


@app.get("/health", tags=["system"])
def health(session: Session = Depends(get_session)) -> dict[str, str]:
    # Prüft bewusst auch die DB-Erreichbarkeit statt nur "Prozess läuft" —
    # ein hängender/nicht erreichbarer Postgres würde sonst als "healthy"
    # gemeldet, obwohl praktisch jeder API-Endpunkt fehlschlägt. Das
    # Dockerfile-HEALTHCHECK wertet einen Nicht-2xx-Status als unhealthy.
    try:
        session.exec(select(1))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Datenbank nicht erreichbar") from exc
    return {"status": "ok"}


# Gebautes React-Frontend ausliefern (nur vorhanden, wenn per Dockerfile
# gebaut — lokales Backend-only-Dev bleibt ohne Frontend-Build unverändert
# funktionsfähig). Muss NACH allen /api-Routen und /health registriert
# werden: Starlette matched Routen in Registrierungsreihenfolge, der
# Catch-all würde sonst alles andere verdecken.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "static"
if FRONTEND_DIST.is_dir():

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str) -> FileResponse:
        kandidat = FRONTEND_DIST / full_path
        if full_path and kandidat.is_file():
            return FileResponse(kandidat)
        return FileResponse(FRONTEND_DIST / "index.html")
