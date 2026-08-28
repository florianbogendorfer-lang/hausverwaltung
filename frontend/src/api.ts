// Produktion: Frontend + Backend laufen im selben Docker-Container hinter
// demselben Origin, API-Routen liegen unter /api (siehe backend/app/main.py).
// Lokaler Dev-Modus überschreibt das via frontend/.env.development.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiFehler extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

// FastAPI liefert bei Validierungsfehlern (422) `detail` NICHT als
// String, sondern als Liste strukturierter Fehlerobjekte
// ({loc, msg, type, ...}) — ohne diese Umwandlung würde ApiFehler.message
// (ein Array) beim Rendern zu unbrauchbarem Text wie
// "[object Object],[object Object]" statt einer lesbaren Meldung.
function _detailAlsText(detail: unknown): string | undefined {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const nachrichten = detail
      .map((eintrag) =>
        eintrag && typeof eintrag === "object" && "msg" in eintrag
          ? String((eintrag as { msg: unknown }).msg)
          : null,
      )
      .filter((m): m is string => m !== null);
    if (nachrichten.length > 0) return nachrichten.join("; ");
  }
  return undefined;
}

async function anfrage<T>(pfad: string, optionen?: RequestInit): Promise<T> {
  const antwort = await fetch(`${API_BASE}${pfad}`, {
    headers: { "Content-Type": "application/json" },
    // Session-Cookie (§0-Login) muss auch im lokalen Dev-Modus mitgeschickt
    // werden, wo Vite-Dev-Server und Backend auf unterschiedlichen Origins
    // laufen — in Produktion (gleicher Origin) ist das ein No-op.
    credentials: "include",
    ...optionen,
  });
  if (!antwort.ok) {
    let detail = antwort.statusText;
    try {
      const body = await antwort.json();
      detail = _detailAlsText(body.detail) ?? detail;
    } catch {
      // kein JSON-Body — Statustext genügt
    }
    if (antwort.status === 401) {
      // Session serverseitig abgelaufen/ungültig geworden (z. B. nach
      // Cookie-Ablauf oder einem Logout in einem anderen Tab), während der
      // Bearbeiter noch auf einer geschützten Seite war — ohne dieses
      // Event bliebe die Seite in einem inkonsistenten Zustand (verstreute
      // "Fehler beim Laden"-Meldungen statt eines klaren Zurück-zum-Login).
      // auth.tsx hört darauf und setzt den Nutzer zurück, App.tsx leitet
      // dann über die bestehende !benutzer-Weiche automatisch um.
      window.dispatchEvent(new Event("hv:unauthorized"));
    }
    throw new ApiFehler(detail, antwort.status);
  }
  if (antwort.status === 204) return undefined as T;
  return antwort.json() as Promise<T>;
}

export const api = {
  get: <T>(pfad: string) => anfrage<T>(pfad),
  // `optionen` erlaubt u. a. { signal } — für Anfragen, die lange laufen
  // können (z. B. der Agent-Loop beim Mail-Einspielen) und daher manuell
  // abbrechbar/mit eigenem Timeout ausgestattet werden sollen.
  post: <T>(pfad: string, body?: unknown, optionen?: RequestInit) =>
    anfrage<T>(pfad, { method: "POST", body: body ? JSON.stringify(body) : undefined, ...optionen }),
  put: <T>(pfad: string, body: unknown) =>
    anfrage<T>(pfad, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(pfad: string, body: unknown) =>
    anfrage<T>(pfad, { method: "PATCH", body: JSON.stringify(body) }),
  del: (pfad: string) => anfrage<void>(pfad, { method: "DELETE" }),
};
