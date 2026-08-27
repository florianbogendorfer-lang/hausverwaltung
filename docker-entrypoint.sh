#!/bin/sh
set -e

# Clever Cloud injiziert bei einem verlinkten Postgres-Add-on
# POSTGRESQL_ADDON_URI im Format postgres://user:pass@host:port/db.
# SQLAlchemy braucht für den psycopg3-Treiber das Schema
# "postgresql+psycopg://" — falls HV_DATABASE_URL nicht explizit gesetzt
# ist, hier automatisch ummappen (NFR-5: reine Konfiguration, kein Umbau).
if [ -z "$HV_DATABASE_URL" ] && [ -n "$POSTGRESQL_ADDON_URI" ]; then
  export HV_DATABASE_URL=$(echo "$POSTGRESQL_ADDON_URI" | sed -E 's#^postgres(ql)?://#postgresql+psycopg://#')
fi

# Der Docker-Deploy-Pfad läuft immer hinter Clever Clouds TLS-Terminierung
# (nie direkt über http://) — Session-Cookie also standardmäßig mit
# Secure-Flag versenden, ohne dass das manuell konfiguriert werden muss.
# Ein expliziter Wert in der Umgebung (z. B. für einen Spezialfall) hat
# weiterhin Vorrang.
export HV_COOKIE_SECURE=${HV_COOKIE_SECURE:-true}

alembic upgrade head

# Idempotent (überspringt sich selbst, falls bereits Daten vorhanden) —
# ohne diesen Schritt bleibt die DB nach reinen Migrationen leer und die
# Erstklassifikation findet nie ein Objekt/Kontakt/Dienstleister (§0:
# Prototyp mit synthetischen Testdaten für den sichtbaren End-to-End-Fluss).
python -m app.seed

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
