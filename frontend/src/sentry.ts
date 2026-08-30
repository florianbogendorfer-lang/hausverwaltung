import * as Sentry from "@sentry/react";

// Fehler-Tracking bleibt komplett inaktiv, solange VITE_SENTRY_DSN nicht
// gesetzt ist (Vite-Build-Zeit-Variable, siehe README) — kein
// Verhaltensunterschied für lokale Entwicklung oder ein Deployment ohne
// DSN. Gegenstück zu app/observability.py::init_sentry() im Backend.
const dsn = import.meta.env.VITE_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT ?? (import.meta.env.PROD ? "produktion" : "entwicklung"),
    // Reines Error-Tracking, kein Performance-/Session-Replay-Sampling —
    // gleiche Haltung wie im Backend (kein zusätzliches Sentry-Kontingent
    // ohne hier bekannten Bedarf).
    tracesSampleRate: 0,
    sendDefaultPii: false,
  });
}

export function fehlerMelden(fehler: unknown, extra?: Record<string, unknown>): void {
  if (!dsn) return;
  Sentry.captureException(fehler, extra ? { extra } : undefined);
}
