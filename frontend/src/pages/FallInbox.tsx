import { AlertTriangle, FolderKanban, Inbox, ShieldAlert } from "lucide-react";
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

  const eskalierteAnzahl = useMemo(
    () => faelle.filter((f) => f.status === "ESKALIERT").length,
    [faelle],
  );

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
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Fall-Inbox</h2>
          <p className="mt-1 text-sm text-slate-500">
            Überblick über alle laufenden Reparaturmeldungen des Agenten.
          </p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as FallStatus | typeof ALLE)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
        >
          <option value={ALLE}>Alle Status</option>
          {STATUS_OPTIONEN.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatKarte
          icon={FolderKanban}
          label="Fälle gesamt"
          wert={faelle.length}
          ton="slate"
        />
        <StatKarte
          icon={ShieldAlert}
          label="Offene Freigaben"
          wert={offeneFreigaben.length}
          ton="amber"
        />
        <StatKarte
          icon={AlertTriangle}
          label="Eskaliert"
          wert={eskalierteAnzahl}
          ton="rose"
        />
      </div>

      {ladeFehler && (
        <p className="mb-4 rounded-lg bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
          Fälle konnten nicht geladen werden: {ladeFehler}
        </p>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50/70 text-slate-500">
            <tr>
              <th className="px-5 py-3 font-medium">Betreff</th>
              <th className="px-5 py-3 font-medium">Objekt</th>
              <th className="px-5 py-3 font-medium">Typ</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium">Letzte Aktivität</th>
              <th className="px-5 py-3 font-medium">Freigaben</th>
            </tr>
          </thead>
          <tbody>
            {sichtbareFaelle.map((fall) => {
              const offen = offeneFreigabenProFall.get(fall.id) ?? 0;
              return (
                <tr
                  key={fall.id}
                  className={`border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50 ${
                    fall.status === "ESKALIERT" ? "bg-rose-50/50" : ""
                  }`}
                >
                  <td className="px-5 py-3.5">
                    <Link
                      to={`/faelle/${fall.id}`}
                      className="font-medium text-slate-900 hover:text-indigo-600"
                    >
                      {fall.betreff}
                    </Link>
                  </td>
                  <td className="px-5 py-3.5 text-slate-600">
                    {fall.objekt_id ? (objektNachId.get(fall.objekt_id)?.bezeichnung ?? "—") : "—"}
                  </td>
                  <td className="px-5 py-3.5 text-slate-600">{fall.typ}</td>
                  <td className="px-5 py-3.5">
                    <FallStatusBadge status={fall.status} />
                  </td>
                  <td className="px-5 py-3.5 text-slate-500">
                    {new Date(fall.geaendert_am).toLocaleString("de-AT")}
                  </td>
                  <td className="px-5 py-3.5">
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
                <td colSpan={6} className="px-5 py-16 text-center">
                  <Inbox className="mx-auto mb-2 text-slate-300" size={28} />
                  <p className="text-slate-400">
                    Keine Fälle vorhanden. Über „Postfach & Outbox" eine Mail einspielen.
                  </p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatKarte({
  icon: Icon,
  label,
  wert,
  ton,
}: {
  icon: typeof FolderKanban;
  label: string;
  wert: number;
  ton: "slate" | "amber" | "rose";
}) {
  const iconStyles = {
    slate: "bg-slate-100 text-slate-600",
    amber: "bg-amber-100 text-amber-700",
    rose: "bg-rose-100 text-rose-700",
  }[ton];

  return (
    <div className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ${iconStyles}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-semibold leading-none tracking-tight text-slate-900">{wert}</p>
        <p className="mt-1 text-xs font-medium text-slate-500">{label}</p>
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
