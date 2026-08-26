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

async function anfrage<T>(pfad: string, optionen?: RequestInit): Promise<T> {
  const antwort = await fetch(`${API_BASE}${pfad}`, {
    headers: { "Content-Type": "application/json" },
    ...optionen,
  });
  if (!antwort.ok) {
    let detail = antwort.statusText;
    try {
      const body = await antwort.json();
      detail = body.detail ?? detail;
    } catch {
      // kein JSON-Body — Statustext genügt
    }
    throw new ApiFehler(detail, antwort.status);
  }
  if (antwort.status === 204) return undefined as T;
  return antwort.json() as Promise<T>;
}

export const api = {
  get: <T>(pfad: string) => anfrage<T>(pfad),
  post: <T>(pfad: string, body?: unknown) =>
    anfrage<T>(pfad, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(pfad: string, body: unknown) =>
    anfrage<T>(pfad, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(pfad: string, body: unknown) =>
    anfrage<T>(pfad, { method: "PATCH", body: JSON.stringify(body) }),
  del: (pfad: string) => anfrage<void>(pfad, { method: "DELETE" }),
};
