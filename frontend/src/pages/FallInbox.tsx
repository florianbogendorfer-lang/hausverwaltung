import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { FallStatusBadge } from "../components/StatusBadge";
import type { Fall, FallStatus, Freigabe, Objekt } from "../types";

// UI-1 — Fall-Inbox (§10): Fälle mit offener Freigabe und eskalierte Fälle
// werden hervorgehoben, damit der Operator sofort sieht, wo er ran muss.

const ALLE = "ALLE" as const;

export default function FallInbox() {
  const [faelle, setFaelle] = useState<Fall[]>([]);
  const [objekte, setObjekte] = useState<Objekt[]>([]);
  const [offeneFreigaben, setOffeneFreigaben] = useState<Freigabe[]>([]);
  const [statusFilter, setStatusFilter] = useState<FallStatus | typeof ALLE>(ALLE);
  const [ladeFehler, setLadeFehler] = useState<string | null>(null);

  async function laden() {
    try {
      const [f, o, fr] = await Promise.all([
        api.get<Fall[]>("/faelle"),
        api.get<Objekt[]>("/objekte"),
        api.get<Freigabe[]>("/freigaben?nur_offene=true"),
      ]);
      setFaelle(f);
      setObjekte(o);
      setOffeneFreigaben(fr);
      setLadeFehler(null);
    } catch (e) {
      setLadeFehler(e instanceof Error ? e.message : "Unbekannter Fehler");
    }
  }

  useEffect(() => {
    laden();
  }, []);

  const objektNachId = useMemo(() => new Map(objekte.map((o) => [o.id, o])), [objekte]);
  const offeneFreigabenProFall = useMemo(() => {
    const map = new Map<number, number>();
    for (const f of offeneFreigaben) map.set(f.fall_id, (map.get(f.fall_id) ?? 0) + 1);
    return map;
  }, [offeneFreigaben]);

  const sichtbareFaelle = useMemo(() => {
    const gefiltert = statusFilter === ALLE ? faelle : faelle.filter((f) => f.status === statusFilter);
    return [...gefiltert].sort((a, b) => {
      const prio = (f: Fall) => (f.status === "ESKALIERT" ? 0 : f.status === "WARTET_AUF_FREIGABE" ? 1 : 2);
      const prioDiff = prio(a) - prio(b);
      if (prioDiff !== 0) return prioDiff;
      return new Date(b.geaendert_am).getTime() - new Date(a.geaendert_am).getTime();
    });
  }, [faelle, statusFilter]);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold">Fall-Inbox</h2>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as FallStatus | typeof ALLE)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        >
          <option value={ALLE}>Alle Status</option>
          {STATUS_OPTIONEN.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {ladeFehler && (
        <p className="mb-4 rounded-md bg-rose-50 px-4 py-2 text-sm text-rose-700">
          Fälle konnten nicht geladen werden: {ladeFehler}
        </p>
      )}

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Betreff</th>
              <th className="px-4 py-2 font-medium">Objekt</th>
              <th className="px-4 py-2 font-medium">Typ</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Letzte Aktivität</th>
              <th className="px-4 py-2 font-medium">Freigaben</th>
            </tr>
          </thead>
          <tbody>
            {sichtbareFaelle.map((fall) => {
              const offen = offeneFreigabenProFall.get(fall.id) ?? 0;
              return (
                <tr
                  key={fall.id}
                  className={`border-b border-slate-100 last:border-0 hover:bg-slate-50 ${
                    fall.status === "ESKALIERT" ? "bg-rose-50/60" : ""
                  }`}
                >
                  <td className="px-4 py-3">
                    <Link to={`/faelle/${fall.id}`} className="font-medium text-slate-900 hover:underline">
                      {fall.betreff}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {fall.objekt_id ? (objektNachId.get(fall.objekt_id)?.bezeichnung ?? "—") : "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{fall.typ}</td>
                  <td className="px-4 py-3">
                    <FallStatusBadge status={fall.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {new Date(fall.geaendert_am).toLocaleString("de-AT")}
                  </td>
                  <td className="px-4 py-3">
                    {offen > 0 && (
                      <span className="inline-flex items-center rounded-full bg-amber-500 px-2 py-0.5 text-xs font-semibold text-white">
                        {offen} offen
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
            {sichtbareFaelle.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  Keine Fälle vorhanden. Über „Postfach & Outbox" eine Mail einspielen.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const STATUS_OPTIONEN: FallStatus[] = [
  "NEU",
  "EINGEORDNET",
  "WARTET_AUF_FREIGABE",
  "DIENSTLEISTER_BEAUFTRAGT",
  "TERMIN_BESTAETIGT",
  "ARBEIT_ERLEDIGT",
  "RECHNUNG_ERFASST",
  "ABGESCHLOSSEN",
  "ESKALIERT",
  "ABGEBROCHEN",
];
