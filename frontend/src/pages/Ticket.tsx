import { AlertCircle, Building2, Mail, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import type { TicketAnsicht } from "../types";
import { alsUtcDatum } from "../zeit";

// Öffentliche Kundenansicht — bewusst ohne die interne Navigation
// (Board/Postfach/Stammdaten): Kunden erreichen diese Seite über den Link
// in ihrer E-Mail, nicht über die Operator-Oberfläche.
//
// Automatisches Neuladen im Hintergrund (alle 30s) + manueller
// Aktualisieren-Button: Statusänderungen (z. B. "Termin bestätigt",
// "Arbeiten wurden durchgeführt") passieren im Hintergrund durch den
// Agenten bzw. den Dienstleister — ohne aktives Neuladen bekam der Kunde
// davon nichts mit, obwohl der Status im Backend längst aktuell war.
export default function Ticket() {
  const { zugriffstoken } = useParams();
  const [ticket, setTicket] = useState<TicketAnsicht | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);
  const [wirdAktualisiert, setWirdAktualisiert] = useState(false);

  const laden = useCallback(
    (imHintergrund = false) => {
      if (!zugriffstoken) return;
      if (imHintergrund) setWirdAktualisiert(true);
      api
        .get<TicketAnsicht>(`/ticket/${zugriffstoken}`)
        .then((daten) => {
          setTicket(daten);
          setFehler(null);
        })
        .catch(() => {
          if (!imHintergrund) {
            setFehler("Dieses Ticket wurde nicht gefunden. Bitte prüfen Sie den Link aus Ihrer E-Mail.");
          }
        })
        .finally(() => setWirdAktualisiert(false));
    },
    [zugriffstoken],
  );

  useEffect(() => {
    laden();
    const intervall = setInterval(() => laden(true), 30_000);
    return () => clearInterval(intervall);
  }, [laden]);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-2xl items-center gap-2.5 px-6 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
            <Building2 size={16} />
          </div>
          <p className="text-[15px] font-semibold tracking-tight text-slate-900">Hausverwaltung</p>
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

        {!fehler && !ticket && <p className="text-sm text-slate-400">Lädt…</p>}

        {ticket && (
          <div>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                  Ticket {ticket.ticket_nummer}
                </p>
                <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
                  {ticket.betreff}
                </h1>
              </div>
              <button
                onClick={() => laden(true)}
                disabled={wirdAktualisiert}
                title="Status jetzt aktualisieren"
                aria-label="Status jetzt aktualisieren"
                className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-indigo-600 disabled:opacity-50"
              >
                <RefreshCw size={15} className={wirdAktualisiert ? "animate-spin" : ""} />
              </button>
            </div>

            <div className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-sm font-medium text-indigo-800">
              {ticket.status_text}
            </div>

            <p className="mt-4 text-xs text-slate-400">
              Eingegangen am {alsUtcDatum(ticket.erstellt_am).toLocaleString("de-AT")} · zuletzt
              aktualisiert am {alsUtcDatum(ticket.geaendert_am).toLocaleString("de-AT")}
            </p>

            <h2 className="mt-8 mb-3 flex items-center gap-1.5 text-sm font-semibold uppercase tracking-wide text-slate-400">
              <Mail size={14} /> Ihre Korrespondenz
            </h2>
            <div className="flex flex-col gap-3">
              {ticket.nachrichten.map((n, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-slate-200 bg-white p-3.5 text-sm shadow-sm"
                >
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-medium text-slate-500">
                      {n.richtung === "eingehend" ? "Von Ihnen" : "Von der Hausverwaltung"}
                    </span>
                    <span>{alsUtcDatum(n.erstellt_am).toLocaleString("de-AT")}</span>
                  </div>
                  <p className="mt-1 font-medium text-slate-800">{n.betreff}</p>
                  <p className="mt-1 whitespace-pre-wrap text-slate-600">{n.inhalt}</p>
                </div>
              ))}
              {ticket.nachrichten.length === 0 && (
                <p className="text-sm text-slate-400">Noch keine Korrespondenz vorhanden.</p>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
