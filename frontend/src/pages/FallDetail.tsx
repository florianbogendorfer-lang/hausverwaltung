import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  CheckCircle2,
  ChevronDown,
  Clock,
  Compass,
  Eye,
  FileSearch,
  Gauge,
  Info,
  Pencil,
  PlayCircle,
  Sparkles,
  Trash2,
  UserRound,
  Wrench,
  X,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { FreigabeKarte } from "../components/FreigabeKarte";
import { FallStatusBadge, NachrichtStatusBadge } from "../components/StatusBadge";
import { alsUtcDatum } from "../zeit";
import type {
  Aktion,
  Dienstleister,
  Fall,
  FallStatus,
  Freigabe,
  Gewerk,
  Kontakt,
  Nachricht,
  Objekt,
  Trace,
} from "../types";

const GEWERK_OPTIONEN: Gewerk[] = ["schlosser", "maurer", "installateur", "elektriker", "sonstiges"];

// UI-3 — Fall-Detail (§10): „Was ist Sache, was muss ich tun". Reihenfolge
// folgt bewusst progressive disclosure — zuerst die Handlungsanweisung in
// Klartext, dann eine offene Freigabe (falls vorhanden — die eigentliche
// Handlungsoberfläche), dann alle bisher ermittelten Fakten, dann der
// Nachrichtenverlauf. Die rohe Schritt-für-Schritt-Timeline ist Beleg-/
// Debugging-Detail und steht deshalb zugeklappt ganz am Ende.

type TimelineEintrag =
  | { art: "trace"; zeitstempel: string; daten: Trace }
  | { art: "aktion"; zeitstempel: string; daten: Aktion };

export default function FallDetail() {
  const { fallId } = useParams();
  const navigate = useNavigate();
  const { benutzer } = useAuth();
  const [fall, setFall] = useState<Fall | null>(null);
  const [traces, setTraces] = useState<Trace[]>([]);
  const [aktionen, setAktionen] = useState<Aktion[]>([]);
  const [nachrichten, setNachrichten] = useState<Nachricht[]>([]);
  const [offeneFreigabe, setOffeneFreigabe] = useState<Freigabe | null>(null);
  const [objekt, setObjekt] = useState<Objekt | null>(null);
  const [kontakt, setKontakt] = useState<Kontakt | null>(null);
  const [dienstleister, setDienstleister] = useState<Dienstleister | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  const [alleObjekte, setAlleObjekte] = useState<Objekt[]>([]);
  const [alleKontakte, setAlleKontakte] = useState<Kontakt[]>([]);
  const [alleDienstleister, setAlleDienstleister] = useState<Dienstleister[]>([]);

  useEffect(() => {
    api.get<Objekt[]>("/objekte").then(setAlleObjekte).catch(() => undefined);
    api.get<Kontakt[]>("/kontakte").then(setAlleKontakte).catch(() => undefined);
    api.get<Dienstleister[]>("/dienstleister").then(setAlleDienstleister).catch(() => undefined);
  }, []);

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
    return eintraege.sort(
      (x, y) => alsUtcDatum(x.zeitstempel).getTime() - alsUtcDatum(y.zeitstempel).getTime(),
    );
  }, [traces, aktionen]);

  const eskalationsgrund = useMemo(() => {
    const eintrag = aktionen.find((a) => a.aktionsart === "fall:eskaliert");
    const grund = eintrag?.details?.grund;
    return typeof grund === "string" ? grund : null;
  }, [aktionen]);

  if (fehler)
    return (
      <p role="alert" className="text-rose-600">
        {fehler}
      </p>
    );
  if (!fall) return <p className="text-slate-400">Lädt…</p>;

  return (
    <div>
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-indigo-600"
      >
        <ArrowLeft size={15} /> zurück zum Board
      </Link>

      <div className="mt-3 mb-4 flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">{fall.betreff}</h2>
          <p className="mt-1 text-sm text-slate-500">
            Fall #{fall.id} · {fall.typ}
            {fall.gewerk && <> · {fall.gewerk}</>}
            {fall.konfidenz != null && <> · Konfidenz {(fall.konfidenz * 100).toFixed(0)}%</>}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Ticket{" "}
            <a
              href={`/ticket/${fall.zugriffstoken}`}
              target="_blank"
              rel="noreferrer"
              className="font-medium text-indigo-600 hover:underline"
              title="Kundenansicht in neuem Tab öffnen"
            >
              {fall.ticket_nummer}
            </a>
            {fall.dienstleister_id && (
              <>
                {" · "}
                <a
                  href={`/dienstleister-portal/${fall.dienstleister_zugriffstoken}`}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-indigo-600 hover:underline"
                  title="Dienstleister-Terminportal in neuem Tab öffnen"
                >
                  Terminportal
                </a>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <FallStatusBadge status={fall.status} />
          {benutzer?.rolle === "admin" && (
            <button
              onClick={async () => {
                if (!fallId) return;
                if (!confirm(`Fall #${fall.id} „${fall.betreff}“ wirklich löschen?`)) return;
                await api.del(`/faelle/${fallId}`);
                navigate("/");
              }}
              title="Fall löschen (nur Admin)"
              aria-label="Fall löschen"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600"
            >
              <Trash2 size={16} />
            </button>
          )}
        </div>
      </div>

      <HandlungsanweisungBanner
        status={fall.status}
        eskalationsgrund={eskalationsgrund}
        terminAm={fall.termin_am}
        fallId={fall.id}
        onEskaliert={laden}
      />

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

      <section className="mb-6">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide text-slate-400">
            <FileSearch size={14} /> Ermittelte Informationen
          </h3>
        </div>
        <ManuelleZuordnung
          fall={fall}
          objekt={objekt}
          kontakt={kontakt}
          dienstleister={dienstleister}
          alleObjekte={alleObjekte}
          alleKontakte={alleKontakte}
          alleDienstleister={alleDienstleister}
          onGespeichert={laden}
        />
        {fall.zusammenfassung && (
          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Zusammenfassung (Agent)
            </h4>
            <p className="text-sm text-slate-700">{fall.zusammenfassung}</p>
          </div>
        )}
      </section>

      <section className="mb-6">
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
      </section>

      <VerlaufDisclosure timeline={timeline} />
    </div>
  );
}

const HANDLUNGSANWEISUNG: Record<
  FallStatus,
  { text: string; ton: "rose" | "amber" | "indigo" | "slate" | "emerald"; icon: typeof Info }
> = {
  NEU: { text: "Agent bearbeitet diesen Fall automatisch — keine Aktion nötig.", ton: "slate", icon: Info },
  EINGEORDNET: {
    text: "Agent reichert diesen Fall automatisch an — keine Aktion nötig.",
    ton: "indigo",
    icon: Info,
  },
  WARTET_AUF_FREIGABE: {
    text: "Aktion nötig — prüfe die Freigabe unten und entscheide.",
    ton: "amber",
    icon: AlertTriangle,
  },
  DIENSTLEISTER_BEAUFTRAGT: {
    text: "Dienstleister wurde beauftragt — wartet auf Terminrückmeldung. Keine Aktion nötig.",
    ton: "indigo",
    icon: Clock,
  },
  TERMIN_BESTAETIGT: {
    text: "Termin ist bestätigt — wartet auf Erledigung vor Ort. Keine Aktion nötig.",
    ton: "indigo",
    icon: Clock,
  },
  ARBEIT_ERLEDIGT: {
    text: "Arbeit ist erledigt — wartet auf die Rechnung. Keine Aktion nötig.",
    ton: "indigo",
    icon: Clock,
  },
  RECHNUNG_ERFASST: {
    text: "Rechnung ist erfasst — Fall wird abgeschlossen. Keine Aktion nötig.",
    ton: "indigo",
    icon: Clock,
  },
  ABGESCHLOSSEN: { text: "Fall ist abgeschlossen.", ton: "emerald", icon: CheckCircle2 },
  ESKALIERT: { text: "Eskaliert — bitte manuell übernehmen.", ton: "rose", icon: AlertTriangle },
  ABGEBROCHEN: { text: "Fall wurde abgebrochen.", ton: "slate", icon: Info },
};

const BANNER_STYLE: Record<string, string> = {
  rose: "border-rose-300 bg-rose-50 text-rose-800",
  amber: "border-amber-300 bg-amber-50 text-amber-800",
  indigo: "border-indigo-200 bg-indigo-50 text-indigo-800",
  slate: "border-slate-200 bg-slate-100 text-slate-700",
  emerald: "border-emerald-300 bg-emerald-50 text-emerald-800",
};

function HandlungsanweisungBanner({
  status,
  eskalationsgrund,
  terminAm,
  fallId,
  onEskaliert,
}: {
  status: FallStatus;
  eskalationsgrund: string | null;
  terminAm?: string | null;
  fallId: number;
  onEskaliert: () => void | Promise<void>;
}) {
  const [wirdEskaliert, setWirdEskaliert] = useState(false);
  const { text, ton, icon: Icon } = HANDLUNGSANWEISUNG[status];
  const grundOhneEndpunkt = eskalationsgrund?.replace(/\.+$/, "");
  const anzeigeText =
    status === "ESKALIERT" && grundOhneEndpunkt
      ? `Eskaliert — ${grundOhneEndpunkt}. Bitte manuell übernehmen.`
      : status === "TERMIN_BESTAETIGT" && terminAm
        ? `${text} Termin: ${alsUtcDatum(terminAm).toLocaleString("de-AT")}.`
        : text;

  // Notausstieg für Fälle, die scheinbar "hängen" — der Agent-Loop läuft
  // synchron in der Request, die den Fall angelegt hat, und wird bei
  // einem Fehler nicht automatisch erneut angestoßen. Sichtbar für alle
  // Nicht-Endzustände, damit ein Bearbeiter einen verdächtig lange
  // stillstehenden Fall jederzeit selbst zur manuellen Bearbeitung holen
  // kann, statt auf ein automatisches Weiterlaufen zu warten, das nicht
  // kommt.
  const kannManuellEskalierenLassen = !["ESKALIERT", "ABGESCHLOSSEN", "ABGEBROCHEN"].includes(
    status,
  );

  async function eskalieren() {
    setWirdEskaliert(true);
    try {
      await api.patch(`/faelle/${fallId}`, { status: "ESKALIERT" });
      await onEskaliert();
    } finally {
      setWirdEskaliert(false);
    }
  }

  return (
    <div className={`mb-6 flex items-start gap-3 rounded-xl border p-4 ${BANNER_STYLE[ton]}`}>
      <Icon size={18} className="mt-0.5 shrink-0" />
      <p className="flex-1 text-sm font-medium">{anzeigeText}</p>
      {kannManuellEskalierenLassen && (
        <button
          onClick={eskalieren}
          disabled={wirdEskaliert}
          className="shrink-0 rounded-lg border border-current/20 px-2.5 py-1 text-xs font-medium underline decoration-dotted underline-offset-2 hover:bg-black/5 disabled:opacity-50"
          title="Falls dieser Fall verdächtig lange in diesem Status steht: manuell zur Bearbeitung eskalieren"
        >
          Wirkt hängengeblieben? Manuell eskalieren
        </button>
      )}
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

function ManuelleZuordnung({
  fall,
  objekt,
  kontakt,
  dienstleister,
  alleObjekte,
  alleKontakte,
  alleDienstleister,
  onGespeichert,
}: {
  fall: Fall;
  objekt: Objekt | null;
  kontakt: Kontakt | null;
  dienstleister: Dienstleister | null;
  alleObjekte: Objekt[];
  alleKontakte: Kontakt[];
  alleDienstleister: Dienstleister[];
  onGespeichert: () => void | Promise<void>;
}) {
  const [bearbeiten, setBearbeiten] = useState(false);
  const [objektId, setObjektId] = useState("");
  const [kontaktId, setKontaktId] = useState("");
  const [dienstleisterId, setDienstleisterId] = useState("");
  const [gewerk, setGewerk] = useState("");
  const [wirdGespeichert, setWirdGespeichert] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);

  const bearbeitungStarten = () => {
    setObjektId(fall.objekt_id != null ? String(fall.objekt_id) : "");
    setKontaktId(fall.melder_kontakt_id != null ? String(fall.melder_kontakt_id) : "");
    setDienstleisterId(fall.dienstleister_id != null ? String(fall.dienstleister_id) : "");
    setGewerk(fall.gewerk ?? "");
    setFehler(null);
    setBearbeiten(true);
  };

  const speichern = async () => {
    setWirdGespeichert(true);
    setFehler(null);
    try {
      await api.patch(`/faelle/${fall.id}`, {
        objekt_id: objektId ? Number(objektId) : null,
        melder_kontakt_id: kontaktId ? Number(kontaktId) : null,
        dienstleister_id: dienstleisterId ? Number(dienstleisterId) : null,
        gewerk: gewerk || null,
      });
      setBearbeiten(false);
      await onGespeichert();
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Speichern fehlgeschlagen.");
    } finally {
      setWirdGespeichert(false);
    }
  };

  const wiederAufnehmen = async () => {
    setWirdGespeichert(true);
    setFehler(null);
    try {
      await api.patch(`/faelle/${fall.id}`, { status: "EINGEORDNET" });
      await onGespeichert();
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Fall konnte nicht wieder aufgenommen werden.");
    } finally {
      setWirdGespeichert(false);
    }
  };

  if (!bearbeiten) {
    return (
      <div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <InfoKarte
            icon={Building2}
            titel="Objekt"
            wert={objekt ? `${objekt.bezeichnung} — ${objekt.adresse}` : "noch nicht ermittelt"}
          />
          <InfoKarte
            icon={UserRound}
            titel="Melder"
            wert={kontakt ? `${kontakt.name} (${kontakt.email})` : "noch nicht ermittelt"}
          />
          <InfoKarte
            icon={Wrench}
            titel="Dienstleister"
            wert={dienstleister ? `${dienstleister.name} (${dienstleister.gewerk})` : "noch nicht ermittelt"}
          />
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            onClick={bearbeitungStarten}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-800"
          >
            <Pencil size={14} /> Manuell zuordnen
          </button>
          {fall.status === "ESKALIERT" && (
            <button
              onClick={wiederAufnehmen}
              disabled={wirdGespeichert}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
            >
              <PlayCircle size={15} /> Fall wieder aufnehmen
            </button>
          )}
        </div>
        {fehler && (
          <p role="alert" className="mt-2 text-sm text-rose-600">
            {fehler}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-4 shadow-sm">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-sm">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Objekt
          </span>
          <select
            value={objektId}
            onChange={(e) => setObjektId(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
          >
            <option value="">— nicht zugeordnet —</option>
            {alleObjekte.map((o) => (
              <option key={o.id} value={o.id}>
                {o.bezeichnung} — {o.adresse}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Melder
          </span>
          <select
            value={kontaktId}
            onChange={(e) => setKontaktId(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
          >
            <option value="">— nicht zugeordnet —</option>
            {alleKontakte.map((k) => (
              <option key={k.id} value={k.id}>
                {k.name} ({k.email})
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Dienstleister
          </span>
          <select
            value={dienstleisterId}
            onChange={(e) => setDienstleisterId(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
          >
            <option value="">— nicht zugeordnet —</option>
            {alleDienstleister.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.gewerk}
                {d.aktiv ? "" : ", inaktiv"})
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Gewerk
          </span>
          <select
            value={gewerk}
            onChange={(e) => setGewerk(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm"
          >
            <option value="">— nicht zugeordnet —</option>
            {GEWERK_OPTIONEN.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="mt-4 flex items-center gap-2">
        <button
          onClick={speichern}
          disabled={wirdGespeichert}
          className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          Speichern
        </button>
        <button
          onClick={() => setBearbeiten(false)}
          disabled={wirdGespeichert}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          <X size={14} /> Abbrechen
        </button>
      </div>
      {fehler && (
          <p role="alert" className="mt-2 text-sm text-rose-600">
            {fehler}
          </p>
        )}
    </div>
  );
}

function VerlaufDisclosure({ timeline }: { timeline: TimelineEintrag[] }) {
  const [aufgeklappt, setAufgeklappt] = useState(false);

  return (
    <section>
      <button
        onClick={() => setAufgeklappt((v) => !v)}
        className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 text-left shadow-sm transition-colors hover:bg-slate-50"
      >
        <span className="text-sm font-semibold text-slate-700">
          Verlauf anzeigen ({timeline.length} Schritt{timeline.length === 1 ? "" : "e"})
        </span>
        <ChevronDown
          size={18}
          className={`shrink-0 text-slate-400 transition-transform ${aufgeklappt ? "rotate-180" : ""}`}
        />
      </button>

      {aufgeklappt && (
        <ol className="mt-3 flex flex-col gap-3">
          {timeline.map((eintrag) => (
            <TimelineZeile key={`${eintrag.art}-${eintrag.daten.id}`} eintrag={eintrag} />
          ))}
          {timeline.length === 0 && <p className="text-sm text-slate-400">Keine Einträge.</p>}
        </ol>
      )}
    </section>
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
  const zeit = alsUtcDatum(eintrag.zeitstempel).toLocaleTimeString("de-AT");

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
