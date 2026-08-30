import {
  AlertTriangle,
  Building2,
  Clock,
  LayoutGrid,
  List as ListIcon,
  Mail,
  ShieldAlert,
  Wrench,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, Outlet, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { FallStatusBadge } from "../components/StatusBadge";
import type { Fall, FallStatus, Freigabe, Objekt } from "../types";
import { alsUtcDatum } from "../zeit";

// Fall-Board (UI-1, überarbeitet): bildet den Verarbeitungsfluss (§4.1) als
// Kanban-Board ab — Spalten = grobe Pipeline-Phasen, Karten = Fälle. Kein
// Drag & Drop: Statuswechsel laufen über die Agent-/Freigabe-Logik (HITL),
// nicht über freies Verschieben — das Board ist eine Sicht, keine
// Bedienoberfläche für den Zustand selbst. Eskalierte Fälle stehen als
// eigene Zeile oben, weil Eskalation „jederzeit" auftreten kann (§4.1) und
// kein regulärer Pipeline-Schritt ist.
//
// Fall-Detail öffnet als Vollbild-Popup statt als eigene Seite: Board ist
// die Layout-Route für „faelle/:fallId" (siehe main.tsx), FallDetail
// rendert über <Outlet/> in einem Overlay über dem Board, mit
// Schließen-Button (X). Das gilt einheitlich auf allen Bildschirmgrößen
// (kein Split-Pane mehr — der halbierte Bildschirm hat sich in der
// Praxis als unübersichtlich erwiesen).
//
// Abgeschlossene/abgebrochene Fälle bleiben NICHT im Board liegen — sie
// werden komplett herausgefiltert (siehe ARCHIVIERT_STATUS) und sind nur
// noch über die eigene Archiv-Seite (pages/Archiv.tsx) einsehbar. Sonst
// häufen sich hier über die Zeit beliebig viele erledigte Fälle an und
// verdecken, was tatsächlich noch Aufmerksamkeit braucht — genau das
// Gegenteil vom Zweck dieser Seite. Innerhalb des Boards ist zusätzlich
// alles nach Dringlichkeit sortiert (FALL_PRIORITAET): zuerst was aktiv
// eine Entscheidung braucht (Eskaliert, Freigabe, Rechnungsprüfung), dann
// der Rest — je länger ein Fall in seinem aktuellen Status unverändert
// liegt (geaendert_am), desto weiter oben, damit hängengebliebene Fälle
// nicht in der Masse untergehen.

type Spaltenfarbe = "slate" | "sky" | "amber" | "violet" | "emerald";

interface Spalte {
  titel: string;
  beschreibung: string;
  status: FallStatus[];
  farbe: Spaltenfarbe;
  aktion?: boolean;
}

// Jede Spalte bekommt eine eigene Farbe statt nur "Aktion nötig" (Amber)
// vs. neutral (Weiß) — macht die fünf Pipeline-Phasen auf einen Blick
// unterscheidbar, nicht erst über den Spaltentitel.
const SPALTEN: Spalte[] = [
  { titel: "Neu", beschreibung: "Mail eingegangen", status: ["NEU"], farbe: "slate" },
  {
    titel: "Eingeordnet",
    beschreibung: "Agent reichert an",
    status: ["EINGEORDNET"],
    farbe: "sky",
  },
  {
    titel: "Wartet auf Freigabe",
    beschreibung: "Deine Entscheidung nötig",
    status: ["WARTET_AUF_FREIGABE"],
    farbe: "amber",
    aktion: true,
  },
  {
    titel: "In Bearbeitung",
    beschreibung: "Dienstleister/Termin/Rechnung",
    status: ["DIENSTLEISTER_BEAUFTRAGT", "TERMIN_BESTAETIGT", "ARBEIT_ERLEDIGT", "RECHNUNG_ERFASST"],
    farbe: "violet",
  },
  // Kein "Abgeschlossen"-Spalte mehr — erledigte/abgebrochene Fälle werden
  // archiviert statt im Board zu bleiben, siehe ARCHIVIERT_STATUS unten.
];

// Fälle in diesen Status verschwinden komplett aus dem Board (Kanban wie
// Liste) und sind nur noch über die Archiv-Seite einsehbar.
const ARCHIVIERT_STATUS: readonly FallStatus[] = ["ABGESCHLOSSEN", "ABGEBROCHEN"];

// Dringlichkeits-Reihenfolge für die Listenansicht (und die Sortierung
// innerhalb einer Kanban-Spalte): zuerst alles, was eine aktive
// Entscheidung braucht (Eskalation > offene Freigabe > Rechnung prüfen),
// dann der Rest in der Reihenfolge des normalen Bearbeitungsflusses.
// ABGESCHLOSSEN/ABGEBROCHEN tauchen wegen ARCHIVIERT_STATUS in der Praxis
// hier nie auf, bekommen aber trotzdem einen (niedrigsten) Wert, damit
// FALL_PRIORITAET für jeden FallStatus vollständig bleibt.
const FALL_PRIORITAET: Record<FallStatus, number> = {
  ESKALIERT: 0,
  WARTET_AUF_FREIGABE: 1,
  RECHNUNG_ERFASST: 2,
  ARBEIT_ERLEDIGT: 3,
  TERMIN_BESTAETIGT: 4,
  DIENSTLEISTER_BEAUFTRAGT: 5,
  EINGEORDNET: 6,
  NEU: 7,
  ABGESCHLOSSEN: 8,
  ABGEBROCHEN: 8,
};

const SPALTEN_STYLE: Record<
  Spaltenfarbe,
  { rahmen: string; hintergrund: string; titel: string; badge: string; beschreibung: string }
> = {
  slate: {
    rahmen: "border-slate-200",
    hintergrund: "bg-white",
    titel: "text-slate-700",
    badge: "bg-slate-200 text-slate-600",
    beschreibung: "text-slate-400",
  },
  sky: {
    rahmen: "border-sky-200",
    hintergrund: "bg-sky-50",
    titel: "text-sky-800",
    badge: "bg-sky-500 text-white",
    beschreibung: "text-sky-600",
  },
  amber: {
    rahmen: "border-amber-300",
    hintergrund: "bg-amber-50",
    titel: "text-amber-800",
    badge: "bg-amber-500 text-white",
    beschreibung: "text-amber-700",
  },
  violet: {
    rahmen: "border-violet-200",
    hintergrund: "bg-violet-50",
    titel: "text-violet-800",
    badge: "bg-violet-500 text-white",
    beschreibung: "text-violet-600",
  },
  emerald: {
    rahmen: "border-emerald-200",
    hintergrund: "bg-emerald-50",
    titel: "text-emerald-800",
    badge: "bg-emerald-500 text-white",
    beschreibung: "text-emerald-600",
  },
};

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

const ANSICHT_SPEICHER_KEY = "hv-board-ansicht";

function gespeicherteAnsicht(): "kanban" | "liste" {
  try {
    const wert = localStorage.getItem(ANSICHT_SPEICHER_KEY);
    return wert === "liste" ? "liste" : "kanban";
  } catch {
    return "kanban";
  }
}

function zeitVor(iso: string): string {
  const diffMs = Date.now() - alsUtcDatum(iso).getTime();
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
  const { fallId } = useParams();
  const geoeffneterFallId = fallId ? Number(fallId) : null;
  const [faelle, setFaelle] = useState<Fall[]>([]);
  const [objekte, setObjekte] = useState<Objekt[]>([]);
  const [offeneFreigaben, setOffeneFreigaben] = useState<Freigabe[]>([]);
  const [suche, setSuche] = useState("");
  const [statusFilter, setStatusFilter] = useState<"alle" | FallStatus>("alle");
  const [ansicht, setAnsicht] = useState<"kanban" | "liste">(gespeicherteAnsicht);
  const [ladeFehler, setLadeFehler] = useState<string | null>(null);

  function ansichtWaehlen(neu: "kanban" | "liste") {
    setAnsicht(neu);
    try {
      localStorage.setItem(ANSICHT_SPEICHER_KEY, neu);
    } catch {
      // Speicher nicht verfügbar (z. B. privater Modus) — Ansicht bleibt
      // für diese Sitzung trotzdem gewechselt, nur ohne Persistenz.
    }
  }

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
    return faelle.filter((f) => {
      if (ARCHIVIERT_STATUS.includes(f.status)) return false;
      if (statusFilter !== "alle" && f.status !== statusFilter) return false;
      if (!suchbegriff) return true;
      const objekt = f.objekt_id ? objektNachId.get(f.objekt_id) : undefined;
      return (
        f.betreff.toLowerCase().includes(suchbegriff) ||
        objekt?.bezeichnung.toLowerCase().includes(suchbegriff)
      );
    });
  }, [faelle, suche, statusFilter, objektNachId]);

  // Innerhalb desselben Status: je länger unverändert (geaendert_am),
  // desto weiter oben — surfacet Fälle, die seit einer Weile in ihrem
  // aktuellen Schritt hängen, statt dass sie zwischen frisch
  // hereingekommenen untergehen.
  const nachAlter = (a: Fall, b: Fall) =>
    alsUtcDatum(a.geaendert_am).getTime() - alsUtcDatum(b.geaendert_am).getTime();

  const eskaliert = gefiltert.filter((f) => f.status === "ESKALIERT").sort(nachAlter);
  const panelOffen = geoeffneterFallId != null;

  function schliessen() {
    navigate("/");
  }

  return (
    <div className="flex items-start gap-6">
      {/* Board wird vom Vollbild-Popup verdeckt (siehe Panel unten) — hier
          ausgeblendet statt nur dahinterliegend, damit es nicht
          versehentlich bedienbar bleibt, während das Panel offen ist. */}
      <div className={`min-w-0 flex-1 ${panelOffen ? "hidden" : ""}`}>
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Fall-Board</h2>
            <p className="mt-1 text-sm text-slate-500">
              Ein Fall, ein Weg — von der eingehenden Mail bis zum Abschluss.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={suche}
              onChange={(e) => setSuche(e.target.value)}
              placeholder="Suchen nach Betreff oder Objekt…"
              className="w-64 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as "alle" | FallStatus)}
              aria-label="Nach Status filtern"
              className="rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            >
              <option value="alle">Alle Status</option>
              {(Object.keys(STATUS_LABEL) as FallStatus[])
                .filter((status) => !ARCHIVIERT_STATUS.includes(status))
                .map((status) => (
                  <option key={status} value={status}>
                    {STATUS_LABEL[status]}
                  </option>
                ))}
            </select>
            <div className="flex items-center gap-0.5 rounded-lg border border-slate-300 bg-white p-0.5 shadow-sm">
              <button
                onClick={() => ansichtWaehlen("kanban")}
                aria-pressed={ansicht === "kanban"}
                title="Kanban-Ansicht"
                className={`flex h-8 w-8 items-center justify-center rounded-md transition-colors ${
                  ansicht === "kanban" ? "bg-indigo-600 text-white" : "text-slate-400 hover:bg-slate-100"
                }`}
              >
                <LayoutGrid size={15} />
              </button>
              <button
                onClick={() => ansichtWaehlen("liste")}
                aria-pressed={ansicht === "liste"}
                title="Listen-Ansicht"
                className={`flex h-8 w-8 items-center justify-center rounded-md transition-colors ${
                  ansicht === "liste" ? "bg-indigo-600 text-white" : "text-slate-400 hover:bg-slate-100"
                }`}
              >
                <ListIcon size={15} />
              </button>
            </div>
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

        {ansicht === "kanban" ? (
          <>
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
                      ausgewaehlt={fall.id === geoeffneterFallId}
                      variante="eskaliert"
                    />
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {SPALTEN.map((spalte) => {
                const karten = gefiltert.filter((f) => spalte.status.includes(f.status)).sort(nachAlter);
                const stil = SPALTEN_STYLE[spalte.farbe];
                return (
                  <div key={spalte.titel} className="flex min-w-0 flex-col">
                    <div className={`mb-3 rounded-lg border px-3 py-2.5 ${stil.rahmen} ${stil.hintergrund}`}>
                      <div className="flex items-center justify-between">
                        <span className={`text-sm font-semibold ${stil.titel}`}>{spalte.titel}</span>
                        <span
                          className={`inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-xs font-semibold ${stil.badge}`}
                        >
                          {karten.length}
                        </span>
                      </div>
                      <p className={`mt-0.5 text-xs ${stil.beschreibung}`}>{spalte.beschreibung}</p>
                    </div>

                    <div className="flex flex-col gap-3">
                      {karten.map((fall) => (
                        <FallKarte
                          key={fall.id}
                          fall={fall}
                          objekt={fall.objekt_id ? objektNachId.get(fall.objekt_id) : undefined}
                          offeneFreigaben={offeneFreigabenProFall.get(fall.id) ?? 0}
                          onClick={() => navigate(`/faelle/${fall.id}`)}
                          ausgewaehlt={fall.id === geoeffneterFallId}
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
          </>
        ) : (
          <FallListe
            faelle={gefiltert}
            objektNachId={objektNachId}
            offeneFreigabenProFall={offeneFreigabenProFall}
            onOeffnen={(id) => navigate(`/faelle/${id}`)}
            geoeffneterFallId={geoeffneterFallId}
          />
        )}
      </div>

      {panelOffen && (
        <div className="fixed inset-0 z-30 overflow-y-auto bg-white">
          <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Falldetails
            </span>
            <button
              onClick={schliessen}
              aria-label="Falldetails schließen"
              title="Schließen"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
            >
              <X size={18} />
            </button>
          </div>
          <div className="mx-auto max-w-3xl p-5">
            <Outlet context={{ aufFallGeaendert: laden }} />
          </div>
        </div>
      )}
    </div>
  );
}

function FallKarte({
  fall,
  objekt,
  offeneFreigaben,
  onClick,
  ausgewaehlt,
  variante,
}: {
  fall: Fall;
  objekt?: Objekt;
  offeneFreigaben: number;
  onClick: () => void;
  ausgewaehlt: boolean;
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
      aria-current={ausgewaehlt ? "true" : undefined}
      className={`w-full rounded-xl border bg-white p-3.5 text-left shadow-sm transition-colors ${
        ausgewaehlt ? "border-indigo-400 ring-2 ring-indigo-100" : rahmen
      } ${variante === "eskaliert" ? "sm:w-64" : ""}`}
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

// Listenansicht — Alternative zum Kanban-Board, angelehnt an eine
// Pipeline-Tabelle (z. B. Google Sheets): ein Fall = eine Zeile, statt in
// Spalten gruppiert. Standardmäßig nach Dringlichkeit sortiert
// (FALL_PRIORITAET, dann je länger unverändert desto weiter oben) —
// alternativ chronologisch absteigend fürs Archiv (pages/Archiv.tsx), wo
// "dringend" keine Bedeutung mehr hat und stattdessen die zuletzt
// abgeschlossenen Fälle oben stehen sollen. Nutzt dasselbe Farbsystem wie
// überall sonst in der App (FallStatusBadge, siehe
// components/StatusBadge.tsx) statt einer eigenen Farbzuordnung.
export function FallListe({
  faelle,
  objektNachId,
  offeneFreigabenProFall,
  onOeffnen,
  geoeffneterFallId,
  sortierung = "prioritaet",
}: {
  faelle: Fall[];
  objektNachId: Map<number, Objekt>;
  offeneFreigabenProFall: Map<number, number>;
  onOeffnen: (fallId: number) => void;
  geoeffneterFallId: number | null;
  sortierung?: "prioritaet" | "aktualisiert_absteigend";
}) {
  const sortiert = useMemo(() => {
    if (sortierung === "aktualisiert_absteigend") {
      return [...faelle].sort(
        (a, b) => alsUtcDatum(b.geaendert_am).getTime() - alsUtcDatum(a.geaendert_am).getTime(),
      );
    }
    return [...faelle].sort((a, b) => {
      const prioritaetsdiff = FALL_PRIORITAET[a.status] - FALL_PRIORITAET[b.status];
      if (prioritaetsdiff !== 0) return prioritaetsdiff;
      return alsUtcDatum(a.geaendert_am).getTime() - alsUtcDatum(b.geaendert_am).getTime();
    });
  }, [faelle, sortierung]);

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="hidden grid-cols-[9rem_1fr_8rem_7rem_5rem] items-center gap-4 border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-400 sm:grid">
        <span>Status</span>
        <span>Fall</span>
        <span>Gewerk</span>
        <span>Zuletzt geändert</span>
        <span className="text-right">Freigabe</span>
      </div>
      <div className="divide-y divide-slate-100">
        {sortiert.map((fall) => {
          const objekt = fall.objekt_id ? objektNachId.get(fall.objekt_id) : undefined;
          const offen = offeneFreigabenProFall.get(fall.id) ?? 0;
          const ausgewaehlt = fall.id === geoeffneterFallId;
          return (
            <button
              key={fall.id}
              onClick={() => onOeffnen(fall.id)}
              aria-current={ausgewaehlt ? "true" : undefined}
              className={`grid w-full grid-cols-1 items-start gap-1.5 px-4 py-3 text-left text-sm transition-colors hover:bg-slate-50 sm:grid-cols-[9rem_1fr_8rem_7rem_5rem] sm:items-center sm:gap-4 sm:py-2.5 ${
                ausgewaehlt ? "bg-indigo-50" : ""
              }`}
            >
              <span>
                <FallStatusBadge status={fall.status} />
              </span>
              <span className="min-w-0">
                <span className="block truncate font-medium text-slate-900">{fall.betreff}</span>
                {objekt && (
                  <span className="flex items-center gap-1 truncate text-xs text-slate-400">
                    <Building2 size={11} className="shrink-0" /> {objekt.bezeichnung}
                  </span>
                )}
              </span>
              <span className="flex items-center gap-1 text-xs text-slate-500 sm:text-sm">
                {fall.gewerk && <Wrench size={11} className="shrink-0 text-slate-400" />}
                {fall.gewerk ?? "—"}
              </span>
              <span className="flex items-center gap-1 text-xs text-slate-400">
                <Clock size={11} className="shrink-0" /> {zeitVor(fall.geaendert_am)}
              </span>
              <span className="flex sm:justify-end">
                {offen > 0 && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-500 px-2 py-0.5 text-xs font-semibold text-white">
                    <ShieldAlert size={11} /> Prüfen
                  </span>
                )}
              </span>
            </button>
          );
        })}
        {sortiert.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-slate-300">Keine Fälle gefunden.</p>
        )}
      </div>
    </div>
  );
}
