import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiFehler } from "../api";
import { PasswortAendernDialog } from "./PasswortAendernDialog";

// Erster Komponententest im Projekt (bisher nur api.ts pur getestet) —
// die Passwortänderung ist sicherheitsrelevant (siehe
// app/routers/auth.py::passwort_aendern) und verdient mehr Absicherung
// als ein manueller Klick im Browser.

const { postMock } = vi.hoisted(() => ({ postMock: vi.fn() }));
vi.mock("../api", async () => {
  const echtesModul = await vi.importActual<typeof import("../api")>("../api");
  return { ...echtesModul, api: { ...echtesModul.api, post: postMock } };
});

describe("PasswortAendernDialog", () => {
  beforeEach(() => {
    postMock.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("zeigt eine Fehlermeldung, wenn das aktuelle Passwort falsch ist", async () => {
    postMock.mockRejectedValue(new ApiFehler("Aktuelles Passwort falsch", 401));
    const onGeschlossen = vi.fn();
    render(<PasswortAendernDialog onGeschlossen={onGeschlossen} />);

    fireEvent.change(screen.getByLabelText("Aktuelles Passwort"), {
      target: { value: "falsches-passwort" },
    });
    fireEvent.change(screen.getByLabelText(/^Neues Passwort/), {
      target: { value: "ein-neues-langes-passwort" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Ändern/ }));

    expect(await screen.findByText("Aktuelles Passwort falsch")).toBeInTheDocument();
    expect(onGeschlossen).not.toHaveBeenCalled();
  });

  it("zeigt eine Erfolgsmeldung nach erfolgreicher Änderung", async () => {
    postMock.mockResolvedValue(undefined);
    render(<PasswortAendernDialog onGeschlossen={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Aktuelles Passwort"), {
      target: { value: "altes-passwort-123" },
    });
    fireEvent.change(screen.getByLabelText(/^Neues Passwort/), {
      target: { value: "ein-neues-langes-passwort" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Ändern/ }));

    await waitFor(() =>
      expect(postMock).toHaveBeenCalledWith("/auth/passwort", {
        aktuelles_passwort: "altes-passwort-123",
        neues_passwort: "ein-neues-langes-passwort",
      }),
    );
    expect(await screen.findByText(/Passwort geändert/)).toBeInTheDocument();
  });

  it("ruft onGeschlossen auf, wenn der Schließen-Button geklickt wird", () => {
    const onGeschlossen = vi.fn();
    render(<PasswortAendernDialog onGeschlossen={onGeschlossen} />);
    fireEvent.click(screen.getByRole("button", { name: "Schließen" }));
    expect(onGeschlossen).toHaveBeenCalledTimes(1);
  });
});
