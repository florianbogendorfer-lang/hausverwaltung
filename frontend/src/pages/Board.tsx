import {
  AlertTriangle,
  Building2,
  Clock,
  Mail,
  ShieldAlert,
  Wrench,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import type { Fall, FallStatus, Freigabe, Objekt } from "../types";

// Fall-Board (UI-1, überarbeitet): bildet den Verarbeitungsfluss (§4.1) als
// Kanban-Board ab — Spalten = grobe Pipeline-Phasen, Karten = Fälle. Kein
// Drag & Drop: Statuswechsel laufen über die Agent-/Freigabe-Logik (HITL),
// nicht über freies Verschieben — das Board ist eine Sicht, keine
// Bedienoberfläche für den Zustand selbst. Eskalierte Fälle stehen als
// eigene Zeile oben, weil Eskalation „jederzeit" auftreten kann (§4.1) und
// kein regulärer Pipeline-Schritt ist.

interface Spalte {
  titel: string;
  beschreibung: string;
  status: FallStatus[];
  aktion?: boolean;
}

const SPALTEN: Spalte[] = [
  { titel: "Neu", beschreibung: "Mail eingegangen", status: ["NEU"] },
  { titel: "Eingeordnet", beschreibung: "Agent reichert an", status: ["EINGEORDNET"] },
  {
    titel: "Wartet auf Freigabe",
    beschreibung: "Deine Entscheidung nötig",
    status: ["WARTET_AUF_FREIGABE"],
    aktion: true,
  },
  {
    titel: "In Bearbeitung",
    beschreibung: "Dienstleister/Termin/Rechnung",
    status: ["DIENSTLEISTER_BEAUFTRAGT", "TERMIN_BESTAETIGT", "ARBEIT_ERLEDIGT", "RECHNUNG_ERFASST"],
  },
  {
    titel: "Abgeschlossen",
    beschreibung: "Erledigt oder abgebrochen",
    status: ["ABGESCHLOSSEN", "ABGEBROCHEN"],
  },
];

const STATUS_LABEL: Record<FallStatus, string> = {
  NEU: "Neu",
  EINGEORDNET: "Eingeordnet",
  WARTET_AUF_FREIGABE: "Wartet auf Freigabe",
  DIENSTLEISTER_BEAUFTRAGT: "Dienstleister beauftragt",
  TERMIN_BESTAETIGT: "Termin bestätigt",
  ARBEIT_ERLEDIGT: "Arbeit erledigt",
  RECHNUNG_ERFASST: "Rechnung erfasst",
  ABGESCHLOSSEN: "Abgeschlossen",
  ESKALIERT: "Eskaliert",
  ABGEBROCHEN: "Abgebrochen",
};

function zeitVor(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return "gerade eben";
  if (min < 60) return `vor ${min} Min.`;
  const std = Math.floor(min / 60);
  if (std < 24) return `vor ${std} Std.`;
  const tage = Math.floor(std / 24);
  return `vor ${tage} Tag${tage === 1 ? "" : "en"}`;
}

export default function Board() {
  const navigate = useNavigate();
  const [faelle, setFaelle] = useState<Fall[]>([]);
  const [objekte, setObjekte] = useState<Objekt[]>([]);
  const [offeneFreigaben, setOffeneFreigaben] = useState<Freigabe[]>([]);
  const [suche, setSuche] = useState("");
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

  const gefiltert = useMemo(() => {
    const suchbegriff = suche.trim().toLowerCase();
    if (!suchbegriff) return faelle;
    return faelle.filter((f) => {
      const objekt = f.objekt_id ? objektNachId.get(f.objekt_id) : undefined;
      return (
        f.betreff.toLowerCase().includes(suchbegriff) ||
        objekt?.bezeichnung.toLowerCase().includes(suchbegriff)
      );
    });
  }, [faelle, suche, objektNachId]);

  const eskaliert = gefiltert.filter((f) => f.status === "ESKALIERT");

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Fall-Board</h2>
          <p className="mt-1 text-sm text-slate-500">
            Ein Fall, ein Weg — von der eingehenden Mail bis zum Abschluss.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={suche}
            onChange={(e) => setSuche(e.target.value)}
            placeholder="Suchen nach Betreff oder Objekt…"
            className="w-64 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          />
          <Link
            to="/postfach"
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700"
          >
            <Mail size={15} /> Mail einspielen
          </Link>
        </div>
      </div>

      {ladeFehler && (
        <p className="mb-4 rounded-lg bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
          Board konnte nicht geladen werden: {ladeFehler}
        </p>
      )}

      {eskaliert.length > 0 && (
        <div className="mb-6 rounded-xl border border-rose-300 bg-rose-50 p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-rose-700">
            <AlertTriangle size={16} />
            Eskaliert — benötigt manuelle Bearbeitung ({eskaliert.length})
          </div>
          <div className="flex flex-wrap gap-3">
            {eskaliert.map((fall) => (
              <FallKarte
                key={fall.id}
                fall={fall}
                objekt={fall.objekt_id ? objektNachId.get(fall.objekt_id) : undefined}
                offeneFreigaben={offeneFreigabenProFall.get(fall.id) ?? 0}
                onClick={() => navigate(`/faelle/${fall.id}`)}
                variante="eskaliert"
              />
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {SPALTEN.map((spalte) => {
          const karten = gefiltert.filter((f) => spalte.status.includes(f.status));
          return (
            <div key={spalte.titel} className="flex min-w-0 flex-col">
              <div
                className={`mb-3 rounded-lg border px-3 py-2.5 ${
                  spalte.aktion
                    ? "border-amber-300 bg-amber-50"
                    : "border-slate-200 bg-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`text-sm font-semibold ${spalte.aktion ? "text-amber-800" : "text-slate-700"}`}
                  >
                    {spalte.titel}
                  </span>
                  <span
                    className={`inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-xs font-semibold ${
                      spalte.aktion ? "bg-amber-500 text-white" : "bg-slate-200 text-slate-600"
                    }`}
                  >
                    {karten.length}
                  </span>
                </div>
                <p className={`mt-0.5 text-xs ${spalte.aktion ? "text-amber-700" : "text-slate-400"}`}>
                  {spalte.beschreibung}
                </p>
              </div>

              <div className="flex flex-col gap-3">
                {karten.map((fall) => (
                  <FallKarte
                    key={fall.id}
                    fall={fall}
                    objekt={fall.objekt_id ? objektNachId.get(fall.objekt_id) : undefined}
                    offeneFreigaben={offeneFreigabenProFall.get(fall.id) ?? 0}
                    onClick={() => navigate(`/faelle/${fall.id}`)}
                    variante={spalte.aktion ? "aktion" : "normal"}
                  />
                ))}
                {karten.length === 0 && (
                  <div className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-xs text-slate-300">
                    leer
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FallKarte({
  fall,
  objekt,
  offeneFreigaben,
  onClick,
  variante,
}: {
  fall: Fall;
  objekt?: Objekt;
  offeneFreigaben: number;
  onClick: () => void;
  variante: "normal" | "aktion" | "eskaliert";
}) {
  const rahmen =
    variante === "eskaliert"
      ? "border-rose-200 hover:border-rose-300"
      : variante === "aktion"
        ? "border-amber-200 hover:border-amber-300"
        : "border-slate-200 hover:border-slate-300";

  return (
    <button
      onClick={onClick}
      className={`w-full rounded-xl border bg-white p-3.5 text-left shadow-sm transition-colors ${rahmen} ${
        variante === "eskaliert" ? "sm:w-64" : ""
      }`}
    >
      <p className="text-sm font-medium text-slate-900">{fall.betreff}</p>
      {objekt && (
        <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
          <Building2 size={12} /> {objekt.bezeichnung}
        </p>
      )}
      {fall.gewerk && (
        <p className="mt-0.5 flex items-center gap-1 text-xs text-slate-400">
          <Wrench size={12} /> {fall.gewerk}
        </p>
      )}
      <div className="mt-2.5 flex items-center justify-between">
        <span className="flex items-center gap-1 text-xs text-slate-400">
          <Clock size={11} /> {zeitVor(fall.geaendert_am)}
        </span>
        {offeneFreigaben > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500 px-2 py-0.5 text-xs font-semibold text-white">
            <ShieldAlert size={11} /> Prüfen
          </span>
        )}
      </div>
      <p className="sr-only">{STATUS_LABEL[fall.status]}</p>
    </button>
  );
}
