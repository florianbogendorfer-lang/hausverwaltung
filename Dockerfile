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

COPY --from=frontend-build /app/frontend/dist ./static

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

ENTRYPOINT ["/app/docker-entrypoint.sh"]
