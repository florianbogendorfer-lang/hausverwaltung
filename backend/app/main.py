"""FastAPI-Einstiegspunkt.

Phase 1 (Fundament, §16): stellt nur lesende Stammdaten-Endpunkte bereit.
Agent-Loop, HITL-Freigabemechanismus und GUI folgen in späteren Phasen.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import create_db_and_tables
from app.routers import dienstleister, dokumente, kontakte, objekte


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Hausverwaltungsagent (Prototyp)",
    description="Backend für den HITL-Agenten — Phase 1: Fundament",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(objekte.router)
app.include_router(kontakte.router)
app.include_router(dienstleister.router)
app.include_router(dokumente.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
