# syntax=docker/dockerfile:1

# ---- Frontend bauen ----
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Backend + ausgeliefertes Frontend ----
FROM python:3.12-slim AS backend

WORKDIR /app

COPY backend/ ./
RUN pip install --no-cache-dir .

# §16 Phase 5: Chromas Default-Embedding-Modell (ONNX MiniLM, ~80 MB) hier
# einmal auslösen, damit es im Image gebacken ist — der Container braucht
# beim Start dann kein Netzwerk mehr dafür (nur einmalig beim Build).
RUN python -c "\
import chromadb; \
c = chromadb.Client(); \
col = c.get_or_create_collection('warmup'); \
col.upsert(ids=['1'], documents=['warmup'])"

COPY --from=frontend-build /app/frontend/dist ./static

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Docker-/OWASP-Best-Practice: nicht als root laufen (CIS Docker Benchmark,
# OWASP Docker Security Cheat Sheet) — ohne expliziten USER liefe der
# Prozess sonst mit vollen Root-Rechten im Container, unnötig bei einem
# Prozess, der nur auf Port 8080 (>1024, kein Root nötig) lauscht und
# innerhalb von /app schreibt (SQLite-Datei bei lokalen Tests, Chromas
# Laufzeitverzeichnis). chown VOR dem USER-Wechsel, damit appuser dort
# schreiben kann.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Docker-/OWASP-Best-Practice: dem Orchestrator (Clever Cloud, aber auch
# `docker run`/-compose lokal) erlauben zu erkennen, ob der Prozess läuft
# UND tatsächlich Requests beantwortet (nicht nur, dass der Container
# existiert) — ohne HEALTHCHECK bliebe ein hängender/deadlocked Uvicorn-
# Prozess unbemerkt "healthy". Nutzt Python statt curl/wget, um keine
# zusätzlichen Pakete ins schlanke Image zu ziehen.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8080') + '/health', timeout=2)" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
