import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DienstleisterPortalAnsicht } from "../types";
import DienstleisterPortal from "./DienstleisterPortal";

const { getMock, postMock, postFormMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  postFormMock: vi.fn(),
}));
vi.mock("../api", async () => {
  const echtesModul = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...echtesModul,
    api: { ...echtesModul.api, get: getMock, post: postMock, postForm: postFormMock },
  };
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
  rechnung_betrag: null,
  rechnung_nummer: null,
  rechnungsbeleg_vorhanden: false,
};

describe("DienstleisterPortal", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    postFormMock.mockReset();
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

  it("meldet die Arbeit als erledigt und zeigt danach das Rechnungsformular", async () => {
    getMock.mockResolvedValueOnce({
      ...BASIS_ANSICHT,
      status: "TERMIN_BESTAETIGT",
      termin_am: "2026-09-05T10:30:00",
    });
    postMock.mockResolvedValue(undefined);
    getMock.mockResolvedValueOnce({
      ...BASIS_ANSICHT,
      status: "ARBEIT_ERLEDIGT",
      status_text: "Als erledigt gemeldet — bitte reichen Sie noch die Rechnung ein.",
      termin_am: "2026-09-05T10:30:00",
    });
    rendern("mein-token");

    const button = await screen.findByRole("button", { name: /erledigt melden/ });
    fireEvent.click(button);

    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith("/dienstleister-portal/mein-token/erledigt"),
    );
    expect(await screen.findByRole("button", { name: /Rechnung einreichen/ })).toBeInTheDocument();
  });

  it("sendet die eingegebene Rechnung bei ARBEIT_ERLEDIGT", async () => {
    getMock.mockResolvedValueOnce({ ...BASIS_ANSICHT, status: "ARBEIT_ERLEDIGT" }).mockResolvedValueOnce({
      ...BASIS_ANSICHT,
      status: "RECHNUNG_ERFASST",
      status_text: "Rechnung eingereicht — vielen Dank.",
      rechnung_betrag: 249.5,
      rechnung_nummer: "RE-2026-042",
    });
    postFormMock.mockResolvedValue(undefined);
    rendern("mein-token");

    await screen.findByRole("button", { name: /Rechnung einreichen/ });
    fireEvent.change(screen.getByLabelText(/Rechnungsbetrag/), { target: { value: "249.50" } });
    fireEvent.change(screen.getByLabelText(/Rechnungsnummer/), { target: { value: "RE-2026-042" } });
    fireEvent.click(screen.getByRole("button", { name: /Rechnung einreichen/ }));

    await waitFor(() => expect(postFormMock).toHaveBeenCalledTimes(1));
    const aufruf = postFormMock.mock.calls[0]!;
    const [pfad, formular] = aufruf;
    expect(pfad).toBe("/dienstleister-portal/mein-token/rechnung");
    expect(formular).toBeInstanceOf(FormData);
    expect((formular as FormData).get("betrag")).toBe("249.50");
    expect((formular as FormData).get("rechnungsnummer")).toBe("RE-2026-042");
    expect(await screen.findByText(/Hausverwaltung wurde informiert/)).toBeInTheDocument();
  });

  it("hängt die ausgewählte Beleg-Datei an das Formular an", async () => {
    getMock.mockResolvedValueOnce({ ...BASIS_ANSICHT, status: "ARBEIT_ERLEDIGT" }).mockResolvedValueOnce({
      ...BASIS_ANSICHT,
      status: "RECHNUNG_ERFASST",
      rechnungsbeleg_vorhanden: true,
    });
    postFormMock.mockResolvedValue(undefined);
    rendern("mein-token");

    await screen.findByRole("button", { name: /Rechnung einreichen/ });
    fireEvent.change(screen.getByLabelText(/Rechnungsbetrag/), { target: { value: "50" } });
    const datei = new File(["%PDF-1.4"], "rechnung.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText(/Rechnungsbeleg/), { target: { files: [datei] } });
    fireEvent.click(screen.getByRole("button", { name: /Rechnung einreichen/ }));

    await waitFor(() => expect(postFormMock).toHaveBeenCalledTimes(1));
    const formular = postFormMock.mock.calls[0]![1] as FormData;
    expect((formular.get("beleg") as File).name).toBe("rechnung.pdf");
  });

  it("zeigt keine Formulare mehr, wenn die Rechnung bereits erfasst ist", async () => {
    getMock.mockResolvedValue({ ...BASIS_ANSICHT, status: "RECHNUNG_ERFASST", rechnung_betrag: 100 });
    rendern();

    await screen.findByText("Türschloss defekt");
    expect(screen.queryByRole("button", { name: /Termin bestätigen/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /erledigt melden/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Rechnung einreichen/ })).not.toBeInTheDocument();
  });
});
