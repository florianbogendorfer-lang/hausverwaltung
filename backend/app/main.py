"""FastAPI-Einstiegspunkt.

Phase 1 (§16, Fundament): lesende Stammdaten-Endpunkte.
Phase 2 (§16, Agent-Kern + Tools): simulierter Postfach-Eingang stößt den
Agent-Loop an; Fall-/Trace-Endpunkte machen den Lauf nachvollziehbar.
HITL-Freigabemechanismus und GUI folgen in späteren Phasen.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import create_db_and_tables
from app.routers import dienstleister, dokumente, faelle, kontakte, objekte, postfach


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Hausverwaltungsagent (Prototyp)",
    description="Backend für den HITL-Agenten",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(objekte.router)
app.include_router(kontakte.router)
app.include_router(dienstleister.router)
app.include_router(dokumente.router)
app.include_router(faelle.router)
app.include_router(postfach.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
