import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FallListe } from "./Board";
import type { Fall } from "../types";

// Regression-Schutz für die Dringlichkeits-Sortierung (FALL_PRIORITAET,
// siehe Board.tsx): Fälle, die eine aktive Entscheidung brauchen
// (Eskaliert > Freigabe > Rechnung prüfen), müssen immer vor Fällen
// stehen, die der Agent/Dienstleister automatisch weiterbearbeitet —
// sonst geht genau das unter, was der Bearbeiter zuerst sehen soll.
function fall(überschreibungen: Partial<Fall>): Fall {
  return {
    id: 1,
    ticket_nummer: "HV-TEST",
    zugriffstoken: "t",
    dienstleister_zugriffstoken: "d",
    typ: "reparaturmeldung",
    status: "NEU",
    betreff: "Test",
    erstellt_am: "2026-01-01T00:00:00",
    geaendert_am: "2026-01-01T00:00:00",
    geloescht: false,
    ...überschreibungen,
  };
}

describe("FallListe – Sortierung", () => {
  it("zeigt Eskaliert vor Wartet-auf-Freigabe vor unauffälligen Status", () => {
    const faelle: Fall[] = [
      fall({ id: 1, betreff: "Neu-Fall", status: "NEU", geaendert_am: "2026-01-05T00:00:00" }),
      fall({
        id: 2,
        betreff: "Freigabe-Fall",
        status: "WARTET_AUF_FREIGABE",
        geaendert_am: "2026-01-03T00:00:00",
      }),
      fall({ id: 3, betreff: "Eskaliert-Fall", status: "ESKALIERT", geaendert_am: "2026-01-04T00:00:00" }),
    ];

    render(
      <FallListe
        faelle={faelle}
        objektNachId={new Map()}
        offeneFreigabenProFall={new Map()}
        onOeffnen={() => {}}
        geoeffneterFallId={null}
      />,
    );

    const namen = screen.getAllByText(/-Fall$/).map((el) => el.textContent);
    expect(namen).toEqual(["Eskaliert-Fall", "Freigabe-Fall", "Neu-Fall"]);
  });

  it("sortiert innerhalb desselben Status nach längster Unveränderheit zuerst", () => {
    const faelle: Fall[] = [
      fall({ id: 1, betreff: "Kuerzlich-Fall", status: "NEU", geaendert_am: "2026-01-05T00:00:00" }),
      fall({ id: 2, betreff: "Laenger-Fall", status: "NEU", geaendert_am: "2026-01-01T00:00:00" }),
    ];

    render(
      <FallListe
        faelle={faelle}
        objektNachId={new Map()}
        offeneFreigabenProFall={new Map()}
        onOeffnen={() => {}}
        geoeffneterFallId={null}
      />,
    );

    const namen = screen.getAllByText(/-Fall$/).map((el) => el.textContent);
    expect(namen).toEqual(["Laenger-Fall", "Kuerzlich-Fall"]);
  });

  it("sortierung=aktualisiert_absteigend zeigt zuletzt geänderte zuerst (Archiv)", () => {
    const faelle: Fall[] = [
      fall({ id: 1, betreff: "Aelter-Fall", status: "ABGESCHLOSSEN", geaendert_am: "2026-01-01T00:00:00" }),
      fall({ id: 2, betreff: "Neuer-Fall", status: "ABGESCHLOSSEN", geaendert_am: "2026-01-10T00:00:00" }),
    ];

    render(
      <FallListe
        faelle={faelle}
        objektNachId={new Map()}
        offeneFreigabenProFall={new Map()}
        onOeffnen={() => {}}
        geoeffneterFallId={null}
        sortierung="aktualisiert_absteigend"
      />,
    );

    const namen = screen.getAllByText(/-Fall$/).map((el) => el.textContent);
    expect(namen).toEqual(["Neuer-Fall", "Aelter-Fall"]);
  });
});
