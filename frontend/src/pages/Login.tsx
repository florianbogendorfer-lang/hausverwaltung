import { Building2, LogIn } from "lucide-react";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ApiFehler } from "../api";

export default function Login() {
  const { benutzer, ladend, anmelden } = useAuth();
  const [email, setEmail] = useState("");
  const [passwort, setPasswort] = useState("");
  const [fehler, setFehler] = useState<string | null>(null);
  const [wirdGesendet, setWirdGesendet] = useState(false);

  async function absenden(e: React.FormEvent) {
    e.preventDefault();
    setFehler(null);
    setWirdGesendet(true);
    try {
      await anmelden(email, passwort);
    } catch (err) {
      setFehler(err instanceof ApiFehler ? err.message : "Anmeldung fehlgeschlagen.");
    } finally {
      setWirdGesendet(false);
    }
  }

  // Bewusst immer zu "/" statt zur zuvor versuchten Seite: nach einem
  // Logout+Neu-Login als anderer Nutzer (z. B. andere Rolle) würde die
  // alte Zielseite sonst 403/404 zeigen statt des Boards.
  if (!ladend && benutzer) return <Navigate to="/" replace />;

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white">
            <Building2 size={20} />
          </div>
          <p className="text-lg font-semibold tracking-tight text-slate-900">Hausverwaltung</p>
          <p className="text-xs font-medium uppercase tracking-wider text-indigo-600">Agent</p>
        </div>

        <form onSubmit={absenden} className="flex flex-col gap-4">
          <label className="text-sm">
            <span className="mb-1 block font-medium text-slate-700">E-Mail</span>
            <input
              type="email"
              name="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
              autoFocus
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium text-slate-700">Passwort</span>
            <input
              type="password"
              name="current-password"
              autoComplete="current-password"
              required
              maxLength={72}
              value={passwort}
              onChange={(e) => setPasswort(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
          </label>

          {fehler && (
            <p role="alert" className="text-sm text-rose-600">
              {fehler}
            </p>
          )}

          <button
            type="submit"
            disabled={wirdGesendet}
            className="mt-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            <LogIn size={15} /> Anmelden
          </button>
        </form>
      </div>
    </div>
  );
}
