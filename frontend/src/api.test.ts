import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiFehler } from "./api";

// Bisher gab es keinerlei Frontend-Tests — die Fehlerbehandlung in
// api.ts (insb. `_detailAlsText`, indirekt über die öffentliche `api.*`-
// Fassade getestet) wurde bislang nur manuell im Browser verifiziert.
// Gerade die FastAPI-422-Umwandlung ist nicht offensichtlich (ein Array
// von {msg,...}-Objekten statt eines Strings) und leicht durch einen
// Refactor kaputtzumachen, ohne dass es auffällt.

function fetchResponse(status: number, body?: unknown, ok = status >= 200 && status < 300) {
  return {
    ok,
    status,
    statusText: "Fehler",
    json: async () => body,
  } as Response;
}

describe("api", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("gibt bei Erfolg den geparsten JSON-Body zurück", async () => {
    vi.mocked(fetch).mockResolvedValue(fetchResponse(200, { id: 1, name: "Test" }));
    const ergebnis = await api.get<{ id: number; name: string }>("/objekte/1");
    expect(ergebnis).toEqual({ id: 1, name: "Test" });
  });

  it("gibt bei 204 No Content undefined zurück statt JSON zu parsen", async () => {
    vi.mocked(fetch).mockResolvedValue(fetchResponse(204, undefined));
    const ergebnis = await api.del("/faelle/1");
    expect(ergebnis).toBeUndefined();
  });

  it("wandelt einen FastAPI-422-detail-Array in eine lesbare Meldung um", async () => {
    vi.mocked(fetch).mockResolvedValue(
      fetchResponse(422, {
        detail: [
          { loc: ["body", "passwort"], msg: "String should have at least 15 characters", type: "too_short" },
        ],
      }),
    );
    await expect(api.post("/benutzer", {})).rejects.toMatchObject({
      message: "String should have at least 15 characters",
      status: 422,
    });
  });

  it("verbindet mehrere Validierungsfehler mit Semikolon", async () => {
    vi.mocked(fetch).mockResolvedValue(
      fetchResponse(422, {
        detail: [{ msg: "Fehler A" }, { msg: "Fehler B" }],
      }),
    );
    await expect(api.post("/benutzer", {})).rejects.toMatchObject({
      message: "Fehler A; Fehler B",
    });
  });

  it("fällt auf den HTTP-Statustext zurück, wenn detail ein String ist", async () => {
    vi.mocked(fetch).mockResolvedValue(fetchResponse(404, { detail: "Ticket nicht gefunden" }));
    await expect(api.get("/ticket/x")).rejects.toMatchObject({
      message: "Ticket nicht gefunden",
      status: 404,
    });
  });

  it("fällt auf statusText zurück, wenn der Body kein gültiges JSON ist", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => {
        throw new SyntaxError("kein JSON");
      },
    } as unknown as Response);
    await expect(api.get("/faelle")).rejects.toMatchObject({
      message: "Internal Server Error",
      status: 500,
    });
  });

  it("wirft eine ApiFehler-Instanz, keinen generischen Error", async () => {
    vi.mocked(fetch).mockResolvedValue(fetchResponse(401, { detail: "Nicht angemeldet" }));
    await expect(api.get("/faelle")).rejects.toBeInstanceOf(ApiFehler);
  });

  it("löst bei 401 das hv:unauthorized-Event aus", async () => {
    vi.mocked(fetch).mockResolvedValue(fetchResponse(401, { detail: "Nicht angemeldet" }));
    const listener = vi.fn();
    window.addEventListener("hv:unauthorized", listener);
    try {
      await api.get("/faelle").catch(() => undefined);
      expect(listener).toHaveBeenCalledTimes(1);
    } finally {
      window.removeEventListener("hv:unauthorized", listener);
    }
  });

  it("löst bei anderen Fehlerstatus KEIN hv:unauthorized-Event aus", async () => {
    vi.mocked(fetch).mockResolvedValue(fetchResponse(404, { detail: "Nicht gefunden" }));
    const listener = vi.fn();
    window.addEventListener("hv:unauthorized", listener);
    try {
      await api.get("/faelle").catch(() => undefined);
      expect(listener).not.toHaveBeenCalled();
    } finally {
      window.removeEventListener("hv:unauthorized", listener);
    }
  });
});
