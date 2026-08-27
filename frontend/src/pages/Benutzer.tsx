import { Trash2, UserPlus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, ApiFehler } from "../api";
import { useAuth } from "../auth";
import type { Benutzer, BenutzerRolle } from "../types";

export default function BenutzerVerwaltung() {
  const { benutzer: aktiverBenutzer } = useAuth();
  const [liste, setListe] = useState<Benutzer[]>([]);
  const [fehler, setFehler] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [passwort, setPasswort] = useState("");
  const [rolle, setRolle] = useState<BenutzerRolle>("user");
  const [wirdAngelegt, setWirdAngelegt] = useState(false);

  const laden = useCallback(async () => {
    try {
      setListe(await api.get<Benutzer[]>("/benutzer"));
      setFehler(null);
    } catch (e) {
      setFehler(e instanceof ApiFehler ? e.message : "Benutzer konnten nicht geladen werden.");
    }
  }, []);

  useEffect(() => {
    laden();
  }, [laden]);

  async function anlegen(e: React.FormEvent) {
    e.preventDefault();
    setWirdAngelegt(true);
    setFehler(null);
    try {
      await api.post("/benutzer", { name, email, passwort, rolle });
      setName("");
      setEmail("");
      setPasswort("");
      setRolle("user");
      await laden();
    } catch (e) {
      setFehler(e instanceof ApiFehler ? e.message : "Benutzer konnte nicht angelegt werden.");
    } finally {
      setWirdAngelegt(false);
    }
  }

  async function loeschen(id: number) {
    try {
      await api.del(`/benutzer/${id}`);
      await laden();
    } catch (e) {
      setFehler(e instanceof ApiFehler ? e.message : "Benutzer konnte nicht gelöscht werden.");
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Benutzer</h2>
      <p className="mt-1 text-sm text-slate-500">
        Admins können Fälle löschen, normale Nutzer bearbeiten nur.
      </p>

      {fehler && (
        <p className="mt-4 rounded-lg bg-rose-50 px-4 py-2.5 text-sm text-rose-700">{fehler}</p>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-4 py-2.5">Name</th>
                <th className="px-4 py-2.5">E-Mail</th>
                <th className="px-4 py-2.5">Rolle</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {liste.map((b) => (
                <tr key={b.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2.5 font-medium text-slate-800">{b.name}</td>
                  <td className="px-4 py-2.5 text-slate-500">{b.email}</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                        b.rolle === "admin" ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {b.rolle === "admin" ? "Admin" : "User"}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {b.id !== aktiverBenutzer?.id && (
                      <button
                        onClick={() => loeschen(b.id)}
                        title="Benutzer löschen"
                        className="text-slate-400 transition-colors hover:text-rose-600"
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {liste.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-400">
                    Keine Benutzer.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <form
          onSubmit={anlegen}
          className="flex h-fit flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
        >
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-700">
            <UserPlus size={15} /> Neuer Benutzer
          </h3>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Name
            </span>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
              E-Mail
            </span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Passwort
            </span>
            <input
              type="password"
              required
              minLength={15}
              value={passwort}
              onChange={(e) => setPasswort(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
            />
            <span className="mt-1 block text-xs text-slate-400">
              Mindestens 15 Zeichen (OWASP-Empfehlung ohne Zwei-Faktor-Login) — lange
              Passphrase statt Komplexitätsregeln.
            </span>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
              Rolle
            </span>
            <select
              value={rolle}
              onChange={(e) => setRolle(e.target.value as BenutzerRolle)}
              className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </label>
          <button
            type="submit"
            disabled={wirdAngelegt}
            className="mt-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            <UserPlus size={15} /> Anlegen
          </button>
        </form>
      </div>
    </div>
  );
}
