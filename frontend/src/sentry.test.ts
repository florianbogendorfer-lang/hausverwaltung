import { describe, expect, it } from "vitest";
import { fehlerMelden } from "./sentry";

// Ohne VITE_SENTRY_DSN (Standard in der Testumgebung) bleibt Sentry
// komplett inaktiv — fehlerMelden darf dann nie werfen, unabhängig vom
// übergebenen Fehler.
describe("sentry", () => {
  it("fehlerMelden wirft nicht, wenn kein DSN konfiguriert ist", () => {
    expect(() => fehlerMelden(new Error("Test-Fehler"))).not.toThrow();
    expect(() => fehlerMelden(new Error("Test-Fehler"), { info: "extra" })).not.toThrow();
  });
});
