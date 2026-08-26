import type { FallStatus, FreigabeStatus, NachrichtStatus } from "../types";

const FALL_STATUS_FARBEN: Record<FallStatus, string> = {
  NEU: "bg-slate-100 text-slate-700",
  EINGEORDNET: "bg-sky-100 text-sky-700",
  WARTET_AUF_FREIGABE: "bg-amber-100 text-amber-800",
  DIENSTLEISTER_BEAUFTRAGT: "bg-indigo-100 text-indigo-700",
  TERMIN_BESTAETIGT: "bg-indigo-100 text-indigo-700",
  ARBEIT_ERLEDIGT: "bg-teal-100 text-teal-700",
  RECHNUNG_ERFASST: "bg-teal-100 text-teal-700",
  ABGESCHLOSSEN: "bg-emerald-100 text-emerald-700",
  ESKALIERT: "bg-rose-100 text-rose-700",
  ABGEBROCHEN: "bg-slate-200 text-slate-600",
};

const FALL_STATUS_LABEL: Record<FallStatus, string> = {
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

export function FallStatusBadge({ status }: { status: FallStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${FALL_STATUS_FARBEN[status]}`}>
      {FALL_STATUS_LABEL[status]}
    </span>
  );
}

const FREIGABE_STATUS_FARBEN: Record<FreigabeStatus, string> = {
  offen: "bg-amber-100 text-amber-800",
  freigegeben: "bg-emerald-100 text-emerald-700",
  bearbeitet_freigegeben: "bg-emerald-100 text-emerald-700",
  abgelehnt: "bg-rose-100 text-rose-700",
};

const FREIGABE_STATUS_LABEL: Record<FreigabeStatus, string> = {
  offen: "Offen",
  freigegeben: "Freigegeben",
  bearbeitet_freigegeben: "Bearbeitet freigegeben",
  abgelehnt: "Abgelehnt",
};

export function FreigabeStatusBadge({ status }: { status: FreigabeStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${FREIGABE_STATUS_FARBEN[status]}`}>
      {FREIGABE_STATUS_LABEL[status]}
    </span>
  );
}

const NACHRICHT_STATUS_FARBEN: Record<NachrichtStatus, string> = {
  empfangen: "bg-slate-100 text-slate-700",
  entwurf: "bg-amber-100 text-amber-800",
  freigegeben: "bg-emerald-100 text-emerald-700",
  gesendet_simuliert: "bg-emerald-100 text-emerald-700",
  abgelehnt: "bg-rose-100 text-rose-700",
};

export function NachrichtStatusBadge({ status }: { status: NachrichtStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${NACHRICHT_STATUS_FARBEN[status]}`}>
      {status.replace("_", " ")}
    </span>
  );
}
