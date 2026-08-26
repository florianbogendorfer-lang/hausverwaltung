import {
  ArrowLeft,
  Building2,
  Compass,
  Eye,
  Gauge,
  Sparkles,
  UserRound,
  Wrench,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { FreigabeKarte } from "../components/FreigabeKarte";
import { FallStatusBadge, NachrichtStatusBadge } from "../components/StatusBadge";
import type { Aktion, Dienstleister, Fall, Freigabe, Kontakt, Nachricht, Objekt, Trace } from "../types";

// UI-3 — Fall-Detail mit Trace (§10): die „Denk-Sicht". Zeigt Fall-Stammdaten,
// beteiligte Objekte/Kontakte/Dienstleister, die chronologische Timeline aus
// traces + aktionen (inkl. verwendetem Modell je Schritt) sowie den
// Nachrichtenverlauf. Liegt eine offene Freigabe für den Fall vor, erscheint
// sie direkt hier oben — die Entscheidung fällt im vollen Kontext des
// Falls, nicht aus einer entkoppelten globalen Liste heraus.

type TimelineEintrag =
  | { art: "trace"; zeitstempel: string; daten: Trace }
  | { art: "aktion"; zeitstempel: string; daten: Aktion };

export default function FallDetail() {
  const { fallId } = useParams();
  const [fall, setFall] = useState<Fall | null>(null);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [aktionen, setAktionen] = useState<Aktion[]>([]);
  const [nachrichten, setNachrichten] = useState<Nachricht[]>([]);
  const [offeneFreigabe, setOffeneFreigabe] = useState<Freigabe | null>(null);
  const [objekt, setObjekt] = useState<Objekt | null>(null);
  const [kontakt, setKontakt] = useState<Kontakt | null>(null);
  const [dienstleister, setDienstleister] = useState<Dienstleister | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  const laden = useCallback(async () => {
    if (!fallId) return;
    try {
      const f = await api.get<Fall>(`/faelle/${fallId}`);
      setFall(f);
      const [t, a, n, fr] = await Promise.all([
        api.get<Trace[]>(`/faelle/${fallId}/trace`),
        api.get<Aktion[]>(`/faelle/${fallId}/aktionen`),
        api.get<Nachricht[]>(`/faelle/${fallId}/nachrichten`),
        api.get<Freigabe[]>(`/freigaben?nur_offene=true&fall_id=${fallId}`),
      ]);
      setTraces(t);
      setAktionen(a);
      setNachrichten(n);
      setOffeneFreigabe(fr[0] ?? null);
      if (f.objekt_id) api.get<Objekt>(`/objekte/${f.objekt_id}`).then(setObjekt).catch(() => undefined);
      if (f.melder_kontakt_id)
        api.get<Kontakt>(`/kontakte/${f.melder_kontakt_id}`).then(setKontakt).catch(() => undefined);
      if (f.dienstleister_id)
        api
          .get<Dienstleister>(`/dienstleister/${f.dienstleister_id}`)
          .then(setDienstleister)
          .catch(() => undefined);
      setFehler(null);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Fall konnte nicht geladen werden.");
    }
  }, [fallId]);

  useEffect(() => {
    laden();
  }, [laden]);

  const timeline = useMemo<TimelineEintrag[]>(() => {
    const eintraege: TimelineEintrag[] = [
      ...traces.map((t): TimelineEintrag => ({ art: "trace", zeitstempel: t.zeitstempel, daten: t })),
      ...aktionen.map((a): TimelineEintrag => ({ art: "aktion", zeitstempel: a.zeitstempel, daten: a })),
    ];
    return eintraege.sort((x, y) => new Date(x.zeitstempel).getTime() - new Date(y.zeitstempel).getTime());
  }, [traces, aktionen]);

  if (fehler) return <p className="text-rose-600">{fehler}</p>;
  if (!fall) return <p className="text-slate-400">Lädt…</p>;

  return (
    <div>
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-indigo-600"
      >
        <ArrowLeft size={15} /> zurück zum Board
      </Link>

      <div className="mt-3 mb-6 flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">{fall.betreff}</h2>
          <p className="mt-1 text-sm text-slate-500">
            Fall #{fall.id} · {fall.typ}
            {fall.gewerk && <> · {fall.gewerk}</>}
            {fall.konfidenz != null && <> · Konfidenz {(fall.konfidenz * 100).toFixed(0)}%</>}
          </p>
        </div>
        <FallStatusBadge status={fall.status} />
      </div>

      {offeneFreigabe && (
        <div className="mb-6">
          <FreigabeKarte
            freigabe={offeneFreigabe}
            fall={fall}
            objekt={objekt ?? undefined}
            dienstleister={dienstleister ?? undefined}
            onEntschieden={laden}
          />
        </div>
      )}

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <InfoKarte
          icon={Building2}
          titel="Objekt"
          wert={objekt ? `${objekt.bezeichnung} — ${objekt.adresse}` : "—"}
        />
        <InfoKarte
          icon={UserRound}
          titel="Melder"
          wert={kontakt ? `${kontakt.name} (${kontakt.email})` : "—"}
        />
        <InfoKarte
          icon={Wrench}
          titel="Dienstleister"
          wert={dienstleister ? `${dienstleister.name} (${dienstleister.gewerk})` : "—"}
        />
      </div>

      {fall.zusammenfassung && (
        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Zusammenfassung (Agent)
          </h3>
          <p className="text-sm text-slate-700">{fall.zusammenfassung}</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Timeline
          </h3>
          <ol className="flex flex-col gap-3">
            {timeline.map((eintrag) => (
              <TimelineZeile key={`${eintrag.art}-${eintrag.daten.id}`} eintrag={eintrag} />
            ))}
            {timeline.length === 0 && <p className="text-sm text-slate-400">Keine Einträge.</p>}
          </ol>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Nachrichtenverlauf
          </h3>
          <div className="flex flex-col gap-3">
            {nachrichten.map((n) => (
              <div key={n.id} className="rounded-xl border border-slate-200 bg-white p-3.5 text-sm shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-700">
                    {n.richtung === "eingehend" ? "↓ eingehend" : "↑ ausgehend"}
                  </span>
                  <NachrichtStatusBadge status={n.status} />
                </div>
                <p className="mt-1 text-slate-500">
                  {n.von} → {n.an}
                </p>
                <p className="mt-1 font-medium text-slate-800">{n.betreff}</p>
                <p className="mt-1 whitespace-pre-wrap text-slate-600">{n.inhalt}</p>
              </div>
            ))}
            {nachrichten.length === 0 && <p className="text-sm text-slate-400">Keine Nachrichten.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoKarte({
  icon: Icon,
  titel,
  wert,
}: {
  icon: typeof Building2;
  titel: string;
  wert: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
        <Icon size={15} />
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{titel}</p>
        <p className="mt-0.5 text-sm text-slate-800">{wert}</p>
      </div>
    </div>
  );
}

const PHASE_LABEL: Record<Trace["phase"], string> = {
  wahrnehmung: "Wahrnehmung",
  plan: "Plan",
  tool_call: "Tool-Aufruf",
  tool_result: "Tool-Ergebnis",
  entscheidung: "Entscheidung",
  reasoning: "Reasoning",
};

const PHASE_ICON: Record<Trace["phase"], typeof Eye> = {
  wahrnehmung: Eye,
  plan: Compass,
  tool_call: Wrench,
  tool_result: Wrench,
  entscheidung: Zap,
  reasoning: Gauge,
};

const PHASE_STYLE: Record<Trace["phase"], string> = {
  wahrnehmung: "bg-slate-100 text-slate-600",
  plan: "bg-sky-100 text-sky-700",
  tool_call: "bg-violet-100 text-violet-700",
  tool_result: "bg-violet-100 text-violet-700",
  entscheidung: "bg-amber-100 text-amber-700",
  reasoning: "bg-slate-100 text-slate-600",
};

function TimelineZeile({ eintrag }: { eintrag: TimelineEintrag }) {
  const zeit = new Date(eintrag.zeitstempel).toLocaleTimeString("de-AT");

  if (eintrag.art === "trace") {
    const t = eintrag.daten;
    const Icon = PHASE_ICON[t.phase];
    return (
      <li className="flex gap-3 rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm">
        <div
          className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${PHASE_STYLE[t.phase]}`}
        >
          <Icon size={14} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
            <span className="font-medium text-slate-500">
              Schritt {t.schritt_nr} · {PHASE_LABEL[t.phase]}
            </span>
            <span className="flex items-center gap-2">
              {t.modell && (
                <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600">
                  {t.modell}
                </span>
              )}
              {t.dauer_ms != null && <span>{t.dauer_ms} ms</span>}
              <span>{zeit}</span>
            </span>
          </div>
          <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">{t.inhalt}</p>
        </div>
      </li>
    );
  }

  const a = eintrag.daten;
  return (
    <li className="flex gap-3 rounded-xl border border-emerald-200 bg-emerald-50/40 p-3.5">
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
        <Sparkles size={14} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span className="font-medium text-slate-500">
            Aktion · {a.akteur} · {a.aktionsart}
          </span>
          <span>{zeit}</span>
        </div>
        {Object.keys(a.details).length > 0 && (
          <pre className="mt-1 overflow-x-auto text-xs text-slate-600">
            {JSON.stringify(a.details, null, 2)}
          </pre>
        )}
      </div>
    </li>
  );
}
