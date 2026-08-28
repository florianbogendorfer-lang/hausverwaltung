import { KeyRound, X } from "lucide-react";
import { useState } from "react";
import { api, ApiFehler } from "../api";

// Self-Service-Passwortänderung für jeden eingeloggten Benutzer (Admin wie
// User) — vorher gab es dafür keinerlei UI, obwohl der Backend-Endpunkt
// (app/routers/auth.py::passwort_aendern) das eigene Passwort per aktuellem
// Passwort verifiziert und bei Erfolg alle anderen Sessions des Kontos
// beendet. Bewusst im Header statt auf der (admin-only) Benutzer-Seite, da
// jeder Benutzer sein eigenes Passwort ändern können muss.

export function PasswortAendernDialog({ onGeschlossen }: { onGeschlossen: () => void }) {
  const [aktuellesPasswort, setAktuellesPasswort] = useState("");
  const [neuesPasswort, setNeuesPasswort] = useState("");
  const [wirdGeaendert, setWirdGeaendert] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);
  const [erfolg, setErfolg] = useState(false);

  async function absenden(e: React.FormEvent) {
    e.preventDefault();
    setWirdGeaendert(true);
    setFehler(null);
    try {
      await api.post("/auth/passwort", {
        aktuelles_passwort: aktuellesPasswort,
        neues_passwort: neuesPasswort,
      });
      setErfolg(true);
      setAktuellesPasswort("");
      setNeuesPasswort("");
    } catch (e) {
      setFehler(e instanceof ApiFehler ? e.message : "Passwort konnte nicht geändert werden.");
    } finally {
      setWirdGeaendert(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-20 flex items-start justify-center bg-slate-900/30 pt-24"
      onClick={onGeschlossen}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-5 shadow-lg"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-700">
            <KeyRound size={15} /> Passwort ändern
          </h3>
          <button
            onClick={onGeschlossen}
            aria-label="Schließen"
            className="text-slate-400 hover:text-slate-700"
          >
            <X size={16} />
          </button>
        </div>

        {erfolg ? (
          <div>
            <p className="rounded-lg bg-emerald-50 px-3 py-2.5 text-sm text-emerald-700">
              Passwort geändert. Andere angemeldete Geräte/Tabs wurden abgemeldet.
            </p>
            <button
              onClick={onGeschlossen}
              className="mt-4 w-full rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
            >
              Schließen
            </button>
          </div>
        ) : (
          <form onSubmit={absenden} className="flex flex-col gap-3">
            <label className="text-sm">
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
                Aktuelles Passwort
              </span>
              <input
                type="password"
                required
                maxLength={72}
                autoComplete="current-password"
                value={aktuellesPasswort}
                onChange={(e) => setAktuellesPasswort(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
                Neues Passwort
              </span>
              <input
                type="password"
                required
                minLength={15}
                maxLength={72}
                autoComplete="new-password"
                value={neuesPasswort}
                onChange={(e) => setNeuesPasswort(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
              />
              <span className="mt-1 block text-xs text-slate-400">
                15–72 Zeichen (OWASP-Empfehlung ohne Zwei-Faktor-Login).
              </span>
            </label>

            {fehler && (
              <p role="alert" className="text-sm text-rose-600">
                {fehler}
              </p>
            )}

            <button
              type="submit"
              disabled={wirdGeaendert}
              className="mt-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
            >
              <KeyRound size={15} /> Ändern
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
