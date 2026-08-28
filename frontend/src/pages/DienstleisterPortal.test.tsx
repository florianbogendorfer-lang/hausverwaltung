import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DienstleisterPortalAnsicht } from "../types";
import DienstleisterPortal from "./DienstleisterPortal";

const { getMock, postMock } = vi.hoisted(() => ({ getMock: vi.fn(), postMock: vi.fn() }));
vi.mock("../api", async () => {
  const echtesModul = await vi.importActual<typeof import("../api")>("../api");
  return { ...echtesModul, api: { ...echtesModul.api, get: getMock, post: postMock } };
});

function rendern(token = "test-token") {
  return render(
    <MemoryRouter initialEntries={[`/dienstleister-portal/${token}`]}>
      <Routes>
        <Route path="/dienstleister-portal/:zugriffstoken" element={<DienstleisterPortal />} />
      </Routes>
    </MemoryRouter>,
  );
}

const BASIS_ANSICHT: DienstleisterPortalAnsicht = {
  ticket_nummer: "HV-ABCD1234",
  betreff: "Türschloss defekt",
  status: "DIENSTLEISTER_BEAUFTRAGT",
  status_text: "Bitte bestätigen Sie einen Termin für den Vor-Ort-Besuch.",
  objekt_adresse: "Musterstraße 5, 1010 Wien",
  melder_name: "Erika Musterfrau",
  melder_telefon: "0664 1234567",
  termin_am: null,
};

describe("DienstleisterPortal", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("zeigt eine Fehlermeldung, wenn der Link nicht gefunden wird", async () => {
    getMock.mockRejectedValue(new Error("404"));
    rendern();
    expect(await screen.findByRole("alert")).toHaveTextContent(/nicht gefunden/);
  });

  it("zeigt die Falldaten und das Terminformular bei DIENSTLEISTER_BEAUFTRAGT", async () => {
    getMock.mockResolvedValue(BASIS_ANSICHT);
    rendern();

    expect(await screen.findByText("Türschloss defekt")).toBeInTheDocument();
    expect(screen.getByText(/Musterstraße 5/)).toBeInTheDocument();
    expect(screen.getByText(/Erika Musterfrau/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Termin bestätigen/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /erledigt melden/ })).not.toBeInTheDocument();
  });

  it("sendet den eingegebenen Termin und lädt danach neu", async () => {
    getMock.mockResolvedValueOnce(BASIS_ANSICHT).mockResolvedValueOnce({
      ...BASIS_ANSICHT,
      status: "TERMIN_BESTAETIGT",
      status_text: "Termin bestätigt.",
      termin_am: "2026-09-05T10:30:00",
    });
    postMock.mockResolvedValue(undefined);
    rendern("mein-token");

    await screen.findByText("Türschloss defekt");
    const eingabe = screen.getByLabelText(/Termin für den Vor-Ort-Besuch/);
    fireEvent.change(eingabe, { target: { value: "2026-09-05T10:30" } });
    fireEvent.click(screen.getByRole("button", { name: /Termin bestätigen/ }));

    await waitFor(() => expect(postMock).toHaveBeenCalledTimes(1));
    expect(postMock).toHaveBeenCalledWith(
      "/dienstleister-portal/mein-token/termin",
      expect.objectContaining({ termin_am: expect.stringContaining("2026-09-05") }),
    );
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole("button", { name: /erledigt melden/ })).toBeInTheDocument();
  });

  it("meldet die Arbeit als erledigt, wenn ein Termin bestätigt ist", async () => {
    getMock.mockResolvedValueOnce({
      ...BASIS_ANSICHT,
      status: "TERMIN_BESTAETIGT",
      termin_am: "2026-09-05T10:30:00",
    });
    postMock.mockResolvedValue(undefined);
    getMock.mockResolvedValueOnce({
      ...BASIS_ANSICHT,
      status: "ARBEIT_ERLEDIGT",
      status_text: "Als erledigt gemeldet — vielen Dank.",
      termin_am: "2026-09-05T10:30:00",
    });
    rendern("mein-token");

    const button = await screen.findByRole("button", { name: /erledigt melden/ });
    fireEvent.click(button);

    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith("/dienstleister-portal/mein-token/erledigt"),
    );
    expect(await screen.findByText(/vielen Dank/)).toBeInTheDocument();
  });

  it("zeigt keine Formulare mehr, wenn die Arbeit bereits erledigt ist", async () => {
    getMock.mockResolvedValue({ ...BASIS_ANSICHT, status: "ARBEIT_ERLEDIGT" });
    rendern();

    await screen.findByText("Türschloss defekt");
    expect(screen.queryByRole("button", { name: /Termin bestätigen/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /erledigt melden/ })).not.toBeInTheDocument();
  });
});
