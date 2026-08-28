import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiFehler } from "../api";
import type { Dienstleister, Kontakt, Objekt } from "../types";
import Stammdaten from "./Stammdaten";

// Regression für den gemeldeten Bug "Stammdatenliste ist nicht editierbar"
// — bislang gab es in Stammdaten.tsx für Objekte/Kontakte/Dienstleister nur
// Anlegen und Löschen, obwohl das Backend (PUT /objekte/{id} etc.) volle
// Bearbeitung längst unterstützt hat.

const { getMock, postMock, putMock, delMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  putMock: vi.fn(),
  delMock: vi.fn(),
}));
vi.mock("../api", async () => {
  const echtesModul = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...echtesModul,
    api: { ...echtesModul.api, get: getMock, post: postMock, put: putMock, del: delMock },
  };
});

const OBJEKT: Objekt = {
  id: 1,
  bezeichnung: "Liegenschaft Musterstraße 5",
  adresse: "Musterstraße 5, 1010 Wien",
  einheit: "Top 3",
  notizen: null,
};

const KONTAKT: Kontakt = {
  id: 1,
  name: "Erika Musterfrau",
  rolle: "mieter",
  email: "erika@example.test",
  telefon: null,
  objekt_id: null,
};

const DIENSTLEISTER: Dienstleister = {
  id: 1,
  name: "Schlosserei Sicherheit GmbH",
  gewerk: "schlosser",
  email: "auftraege@schlosserei-sicherheit.example.test",
  telefon: null,
  konditionen: null,
  aktiv: true,
};

describe("Stammdaten", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    putMock.mockReset();
    delMock.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("Objekt: bearbeiten zeigt Eingabefelder, speichern ruft PUT auf und lädt neu", async () => {
    getMock.mockResolvedValue([OBJEKT]);
    putMock.mockResolvedValue(undefined);
    render(<Stammdaten />);

    await screen.findByText("Liegenschaft Musterstraße 5");
    fireEvent.click(screen.getByRole("button", { name: /bearbeiten/ }));

    const zeile = screen.getByDisplayValue("Liegenschaft Musterstraße 5").closest("tr")!;
    fireEvent.change(within(zeile).getByDisplayValue("Liegenschaft Musterstraße 5"), {
      target: { value: "Liegenschaft Musterstraße 5 (neu)" },
    });
    fireEvent.click(within(zeile).getByRole("button", { name: /speichern/ }));

    await waitFor(() =>
      expect(putMock).toHaveBeenCalledWith(
        "/objekte/1",
        expect.objectContaining({ bezeichnung: "Liegenschaft Musterstraße 5 (neu)" }),
      ),
    );
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(2));
  });

  it("Objekt: abbrechen verwirft Änderungen ohne PUT-Aufruf", async () => {
    getMock.mockResolvedValue([OBJEKT]);
    render(<Stammdaten />);

    await screen.findByText("Liegenschaft Musterstraße 5");
    fireEvent.click(screen.getByRole("button", { name: /bearbeiten/ }));
    fireEvent.click(screen.getByRole("button", { name: /abbrechen/ }));

    expect(await screen.findByText("Liegenschaft Musterstraße 5")).toBeInTheDocument();
    expect(putMock).not.toHaveBeenCalled();
  });

  it("Objekt: zeigt eine Fehlermeldung, wenn das Speichern fehlschlägt", async () => {
    getMock.mockResolvedValue([OBJEKT]);
    putMock.mockRejectedValue(new ApiFehler("Speichern fehlgeschlagen.", 500));
    render(<Stammdaten />);

    await screen.findByText("Liegenschaft Musterstraße 5");
    fireEvent.click(screen.getByRole("button", { name: /bearbeiten/ }));
    fireEvent.click(screen.getByRole("button", { name: /speichern/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Speichern fehlgeschlagen.");
  });

  it("Kontakt: Bearbeitung erlaubt die Zuordnung eines Objekts", async () => {
    getMock.mockImplementation((pfad: string) =>
      Promise.resolve(pfad === "/kontakte" ? [KONTAKT] : [OBJEKT]),
    );
    putMock.mockResolvedValue(undefined);
    render(<Stammdaten />);

    fireEvent.click(screen.getByRole("button", { name: /Kontakte/ }));
    await screen.findByText("Erika Musterfrau");
    fireEvent.click(screen.getByRole("button", { name: /bearbeiten/ }));

    const zeile = screen.getByDisplayValue("Erika Musterfrau").closest("tr")!;
    const objektSelect = within(zeile).getAllByRole("combobox")[1]!;
    fireEvent.change(objektSelect, { target: { value: "1" } });
    fireEvent.click(within(zeile).getByRole("button", { name: /speichern/ }));

    await waitFor(() =>
      expect(putMock).toHaveBeenCalledWith("/kontakte/1", expect.objectContaining({ objekt_id: 1 })),
    );
  });

  it("Dienstleister: Bearbeitung erlaubt das Umschalten von aktiv/inaktiv", async () => {
    getMock.mockResolvedValue([DIENSTLEISTER]);
    putMock.mockResolvedValue(undefined);
    render(<Stammdaten />);

    fireEvent.click(screen.getByRole("button", { name: /Dienstleister/ }));
    await screen.findByText("Schlosserei Sicherheit GmbH");
    fireEvent.click(screen.getByRole("button", { name: /bearbeiten/ }));

    const zeile = screen.getByDisplayValue("Schlosserei Sicherheit GmbH").closest("tr")!;
    fireEvent.click(within(zeile).getByRole("checkbox"));
    fireEvent.click(within(zeile).getByRole("button", { name: /speichern/ }));

    await waitFor(() =>
      expect(putMock).toHaveBeenCalledWith("/dienstleister/1", expect.objectContaining({ aktiv: false })),
    );
  });
});
