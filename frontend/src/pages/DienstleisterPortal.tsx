import { AlertCircle, Building2, Calendar, CheckCircle2, User, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiFehler } from "../api";
import type { DienstleisterPortalAnsicht } from "../types";
import { alsUtcDatum } from "../zeit";

// Öffentliches, login-freies Terminportal für Dienstleister — analog zu
// Ticket.tsx (Kundenansicht), aber mit Schreibzugriff: der Dienstleister
// bestätigt hier strukturiert einen Termin und meldet die Erledigung,
// statt dass der Agent das aus einer Freitext-Mail-Antwort herauslesen
// müsste. Erreichbar über den Link in der Beauftragungsmail
// (dienstleister_zugriffstoken, siehe app/routers/dienstleister_portal.py).
export default function DienstleisterPortal() {
  const { zugriffstoken } = useParams();
  const [ansicht, setAnsicht] = useState<DienstleisterPortalAnsicht | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);
  const [terminEingabe, setTerminEingabe] = useState("");
  const [aktionFehler, setAktionFehler] = useState<string | null>(null);
  const [wirdGesendet, setWirdGesendet] = useState(false);

  const laden = () => {
    if (!zugriffstoken) return;
    api
      .get<DienstleisterPortalAnsicht>(`/dienstleister-portal/${zugriffstoken}`)
      .then((daten) => {
        setAnsicht(daten);
        setFehler(null);
      })
      .catch(() =>
        setFehler("Dieser Link wurde nicht gefunden. Bitte prüfen Sie den Link aus Ihrer E-Mail."),
      );
  };

  useEffect(laden, [zugriffstoken]);

  async function terminBestaetigen(e: React.FormEvent) {
    e.preventDefault();
    if (!zugriffstoken || !terminEingabe) return;
    setWirdGesendet(true);
    setAktionFehler(null);
    try {
      await api.post(`/dienstleister-portal/${zugriffstoken}/termin`, {
        termin_am: new Date(terminEingabe).toISOString(),
      });
      laden();
    } catch (e) {
      setAktionFehler(e instanceof ApiFehler ? e.message : "Termin konnte nicht bestätigt werden.");
    } finally {
      setWirdGesendet(false);
    }
  }

  async function alsErledigtMelden() {
    if (!zugriffstoken) return;
    setWirdGesendet(true);
    setAktionFehler(null);
    try {
      await api.post(`/dienstleister-portal/${zugriffstoken}/erledigt`);
      laden();
    } catch (e) {
      setAktionFehler(e instanceof ApiFehler ? e.message : "Konnte nicht als erledigt gemeldet werden.");
    } finally {
      setWirdGesendet(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-2xl items-center gap-2.5 px-6 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
            <Building2 size={16} />
          </div>
          <p className="text-[15px] font-semibold tracking-tight text-slate-900">
            Hausverwaltung — Terminportal
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-10">
        {fehler && (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          >
            <AlertCircle size={18} className="mt-0.5 shrink-0" />
            <p>{fehler}</p>
          </div>
        )}

        {!fehler && !ansicht && <p className="text-sm text-slate-400">Lädt…</p>}

        {ansicht && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
              Auftrag {ansicht.ticket_nummer}
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
              {ansicht.betreff}
            </h1>

            <div className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-sm font-medium text-indigo-800">
              {ansicht.status_text}
            </div>

            <div className="mt-4 flex flex-col gap-2 text-sm text-slate-600">
              {ansicht.objekt_adresse && (
                <p className="flex items-center gap-2">
                  <Building2 size={14} className="shrink-0 text-slate-400" /> {ansicht.objekt_adresse}
                </p>
              )}
              {ansicht.melder_name && (
                <p className="flex items-center gap-2">
                  <User size={14} className="shrink-0 text-slate-400" /> Ansprechperson vor Ort:{" "}
                  {ansicht.melder_name}
                  {ansicht.melder_telefon && <> · {ansicht.melder_telefon}</>}
                </p>
              )}
              {ansicht.termin_am && (
                <p className="flex items-center gap-2">
                  <Calendar size={14} className="shrink-0 text-slate-400" /> Termin:{" "}
                  {alsUtcDatum(ansicht.termin_am).toLocaleString("de-AT")}
                </p>
              )}
            </div>

            {aktionFehler && (
              <p role="alert" className="mt-4 text-sm text-rose-600">
                {aktionFehler}
              </p>
            )}

            {ansicht.status === "DIENSTLEISTER_BEAUFTRAGT" && (
              <form
                onSubmit={terminBestaetigen}
                className="mt-6 flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
              >
                <label className="text-sm">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Termin für den Vor-Ort-Besuch
                  </span>
                  <input
                    type="datetime-local"
                    required
                    value={terminEingabe}
                    onChange={(e) => setTerminEingabe(e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
                  />
                </label>
                <button
                  type="submit"
                  disabled={wirdGesendet}
                  className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
                >
                  <Calendar size={15} /> Termin bestätigen
                </button>
              </form>
            )}

            {ansicht.status === "TERMIN_BESTAETIGT" && (
              <button
                onClick={alsErledigtMelden}
                disabled={wirdGesendet}
                className="mt-6 inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:opacity-50"
              >
                <Wrench size={15} /> Arbeit als erledigt melden
              </button>
            )}

            {ansicht.status === "ARBEIT_ERLEDIGT" && (
              <p className="mt-6 flex items-center gap-1.5 text-sm font-medium text-emerald-700">
                <CheckCircle2 size={16} /> Vielen Dank — die Hausverwaltung wurde informiert.
              </p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
