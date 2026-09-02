# syntax=docker/dockerfile:1

# ---- Frontend bauen ----
FROM node:26-slim AS frontend-build
WORKDIR /app/frontend
# Anders als die HV_*-Backend-Variablen (zur Laufzeit über docker-
# entrypoint.sh/Clever Cloud gesetzt) muss Vite VITE_*-Variablen schon beim
# Build kennen (src/sentry.ts liest import.meta.env.VITE_SENTRY_DSN, wird
# von Vite zur Build-Zeit statisch ersetzt) — daher hier als Build-ARG statt
# als normale Laufzeit-Umgebungsvariable. Ohne gesetzten ARG (Standardfall)
# bleiben beide leer und Sentry im Frontend inaktiv, siehe src/sentry.ts.
ARG VITE_SENTRY_DSN
ARG VITE_SENTRY_ENVIRONMENT
ENV VITE_SENTRY_DSN=${VITE_SENTRY_DSN}
ENV VITE_SENTRY_ENVIRONMENT=${VITE_SENTRY_ENVIRONMENT}
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
