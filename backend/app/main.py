"""FastAPI-Einstiegspunkt.

Phase 1 (§16, Fundament): lesende Stammdaten-Endpunkte.
Phase 2 (§16, Agent-Kern + Tools): simulierter Postfach-Eingang stößt den
Agent-Loop an; Fall-/Trace-Endpunkte machen den Lauf nachvollziehbar.
Phase 3 (§16, HITL propose/commit): Freigabe-Queue-Endpunkte für
Freigeben/Bearbeiten/Ablehnen.
Phase 4 (§16, GUI): CRUD-Endpunkte für Stammdaten + Outbox-Endpunkt und
CORS für die React-Operator-Oberfläche (`frontend/`).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import create_db_and_tables
from app.routers import (
    dienstleister,
    dokumente,
    faelle,
    freigaben,
    kontakte,
    objekte,
    outbox,
    postfach,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Hausverwaltungsagent (Prototyp)",
    description="Backend für den HITL-Agenten",
    version="0.4.0",
    lifespan=lifespan,
)

# Prototyp mit einem lokalen Operator (§3) — permissive CORS für die lokal
# laufende Vite-Dev-GUI genügt, kein produktiver Härtungsanspruch.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(objekte.router)
app.include_router(kontakte.router)
app.include_router(dienstleister.router)
app.include_router(dokumente.router)
app.include_router(faelle.router)
app.include_router(postfach.router)
app.include_router(freigaben.router)
app.include_router(outbox.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
