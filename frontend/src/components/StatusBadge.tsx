import type { FallStatus, FreigabeStatus, NachrichtStatus } from "../types";

// Einheitliches Dot+Label-Muster über alle Status-Typen, eingedampft auf
// vier Semantik-Farben: Slate (neutral) · Amber (wartend/offen) ·
// Indigo (in Bearbeitung) · Emerald (erledigt/freigegeben) · Rose
// (eskaliert/abgelehnt).

type Ton = "slate" | "amber" | "indigo" | "emerald" | "rose";

const TON_STYLES: Record<Ton, { dot: string; text: string; bg: string }> = {
  slate: { dot: "bg-slate-400", text: "text-slate-700", bg: "bg-slate-100" },
  amber: { dot: "bg-amber-500", text: "text-amber-800", bg: "bg-amber-50" },
  indigo: { dot: "bg-indigo-500", text: "text-indigo-700", bg: "bg-indigo-50" },
  emerald: { dot: "bg-emerald-500", text: "text-emerald-700", bg: "bg-emerald-50" },
  rose: { dot: "bg-rose-500", text: "text-rose-700", bg: "bg-rose-50" },
};

function Dot({ ton, label }: { ton: Ton; label: string }) {
  const s = TON_STYLES[ton];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full ${s.bg} px-2.5 py-1 text-xs font-medium ${s.text}`}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${s.dot}`} />
      {label}
    </span>
  );
}

const FALL_STATUS: Record<FallStatus, { ton: Ton; label: string }> = {
  NEU: { ton: "slate", label: "Neu" },
  EINGEORDNET: { ton: "indigo", label: "Eingeordnet" },
  WARTET_AUF_FREIGABE: { ton: "amber", label: "Wartet auf Freigabe" },
  DIENSTLEISTER_BEAUFTRAGT: { ton: "indigo", label: "Dienstleister beauftragt" },
  TERMIN_BESTAETIGT: { ton: "indigo", label: "Termin bestätigt" },
  ARBEIT_ERLEDIGT: { ton: "emerald", label: "Arbeit erledigt" },
  RECHNUNG_ERFASST: { ton: "emerald", label: "Rechnung erfasst" },
  ABGESCHLOSSEN: { ton: "emerald", label: "Abgeschlossen" },
  ESKALIERT: { ton: "rose", label: "Eskaliert" },
  ABGEBROCHEN: { ton: "slate", label: "Abgebrochen" },
};

export function FallStatusBadge({ status }: { status: FallStatus }) {
  const s = FALL_STATUS[status];
  return <Dot ton={s.ton} label={s.label} />;
}

const FREIGABE_STATUS: Record<FreigabeStatus, { ton: Ton; label: string }> = {
  offen: { ton: "amber", label: "Offen" },
  freigegeben: { ton: "emerald", label: "Freigegeben" },
  bearbeitet_freigegeben: { ton: "emerald", label: "Bearbeitet freigegeben" },
  abgelehnt: { ton: "rose", label: "Abgelehnt" },
};

export function FreigabeStatusBadge({ status }: { status: FreigabeStatus }) {
  const s = FREIGABE_STATUS[status];
  return <Dot ton={s.ton} label={s.label} />;
}

const NACHRICHT_STATUS: Record<NachrichtStatus, { ton: Ton; label: string }> = {
  empfangen: { ton: "slate", label: "empfangen" },
  entwurf: { ton: "amber", label: "entwurf" },
  freigegeben: { ton: "emerald", label: "freigegeben" },
  gesendet_simuliert: { ton: "emerald", label: "gesendet (simuliert)" },
  gesendet: { ton: "emerald", label: "gesendet" },
  abgelehnt: { ton: "rose", label: "abgelehnt" },
  versand_fehlgeschlagen: { ton: "rose", label: "Versand fehlgeschlagen" },
};

export function NachrichtStatusBadge({ status }: { status: NachrichtStatus }) {
  const s = NACHRICHT_STATUS[status];
  return <Dot ton={s.ton} label={s.label} />;
}
