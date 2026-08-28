import { AlertTriangle, Check, ChevronDown, FileText, Mail, Pencil, Wrench, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiFehler } from "../api";
import { FreigabeStatusBadge } from "./StatusBadge";
import type { Dienstleister, Fall, Freigabe, Nachricht, Objekt } from "../types";
import { alsUtcDatum } from "../zeit";

// HITL-Kernstück (§5): zeigt Auslöser, Entwurf/Payload, Begründung und
// herangezogene Fakten (FR-HITL-4) und bietet die drei Entscheidungen aus
// FR-HITL-5. Wird im Fall-Detail direkt im Kontext des Falls angezeigt
// (nicht mehr als separate, entkoppelte Liste) — Reviewer sollen im
// vollen Kontext entscheiden, nicht aus einer anonymen Queue heraus.
//
// Wer entscheidet, ergibt sich aus der eingeloggten Session (Backend liest
// das aus dem Auth-Cookie, siehe app/routers/freigaben.py) — kein
// Freitextfeld mehr, das ein Nutzer beliebig auf einen anderen Namen
// setzen könnte (Audit-Trail-Integrität).

const AKTIONSTYP_ICON: Record<Freigabe["aktionstyp"], typeof Mail> = {
  nachricht_senden: Mail,
  dienstleister_beauftragen: Wrench,
  rechnung_erfassen: FileText,
};

const AKTIONSTYP_LABEL: Record<Freigabe["aktionstyp"], string> = {
  nachricht_senden: "Nachricht senden",
  dienstleister_beauftragen: "Dienstleister beauftragen",
  rechnung_erfassen: "Rechnung erfassen",
};

export function FreigabeKarte({
  freigabe,
  fall,
  objekt,
  dienstleister,
  standardAufgeklappt = true,
  onEntschieden,
}: {
  freigabe: Freigabe;
  fall?: Fall;
  objekt?: Objekt;
  dienstleister?: Dienstleister;
  standardAufgeklappt?: boolean;
  onEntschieden: () => void;
}) {
  const [aufgeklappt, setAufgeklappt] = useState(standardAufgeklappt);
  const [nachricht, setNachricht] = useState<Nachricht | null>(null);
  const [bearbeitenModus, setBearbeitenModus] = useState(false);
  const [entwurfText, setEntwurfText] = useState("");
  const [ablehnenModus, setAblehnenModus] = useState(false);
  const [ablehnGrund, setAblehnGrund] = useState("");
  const [läuft, setLäuft] = useState(false);
  const [aktionsFehler, setAktionsFehler] = useState<string | null>(null);

  const nachrichtId =
    freigabe.aktionstyp === "nachricht_senden" && typeof freigabe.payload.nachricht_id === "number"
      ? freigabe.payload.nachricht_id
      : null;

  useEffect(() => {
    if (aufgeklappt && nachrichtId && !nachricht) {
      api
        .get<Nachricht[]>(`/faelle/${freigabe.fall_id}/nachrichten`)
        .then((liste) => {
          const gefunden = liste.find((n) => n.id === nachrichtId) ?? null;
          setNachricht(gefunden);
          setEntwurfText(gefunden?.inhalt ?? "");
        })
        .catch(() => undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aufgeklappt, nachrichtId]);

  const originalMail =
    typeof freigabe.kontext_referenzen.original_mail === "string"
      ? freigabe.kontext_referenzen.original_mail
      : null;

  async function freigeben(bearbeiteterText?: string) {
    setLäuft(true);
    setAktionsFehler(null);
    try {
      await api.post(`/freigaben/${freigabe.id}/freigeben`, {
        bearbeiteter_text: bearbeiteterText,
      });
      onEntschieden();
    } catch (e) {
      setAktionsFehler(e instanceof ApiFehler ? e.message : "Freigabe fehlgeschlagen.");
    } finally {
      setLäuft(false);
    }
  }

  async function ablehnen() {
    if (!ablehnGrund.trim()) return;
    setLäuft(true);
    setAktionsFehler(null);
    try {
      await api.post(`/freigaben/${freigabe.id}/ablehnen`, { grund: ablehnGrund });
      onEntschieden();
    } catch (e) {
      setAktionsFehler(e instanceof ApiFehler ? e.message : "Ablehnung fehlgeschlagen.");
    } finally {
      setLäuft(false);
    }
  }

  const AktionsIcon = AKTIONSTYP_ICON[freigabe.aktionstyp];

  return (
    <div
      className={`rounded-xl border bg-white shadow-sm ${freigabe.ueberfaellig ? "border-rose-300" : "border-amber-200"}`}
    >
      <button
        onClick={() => setAufgeklappt((v) => !v)}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
            <AktionsIcon size={17} />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium text-slate-900">Freigabe nötig — {AKTIONSTYP_LABEL[freigabe.aktionstyp]}</span>
              <FreigabeStatusBadge status={freigabe.status} />
              {freigabe.ueberfaellig && (
                <span className="inline-flex items-center gap-1 rounded-full bg-rose-500 px-2 py-0.5 text-xs font-semibold text-white">
                  <AlertTriangle size={11} /> überfällig
                </span>
              )}
            </div>
            <p className="mt-0.5 text-sm text-slate-500">
              {fall ? `Fall: ${fall.betreff} · ` : ""}angelegt{" "}
              {alsUtcDatum(freigabe.erstellt_am).toLocaleString("de-AT")}
            </p>
          </div>
        </div>
        <ChevronDown
          size={18}
          className={`shrink-0 text-slate-400 transition-transform ${aufgeklappt ? "rotate-180" : ""}`}
        />
      </button>

      {aufgeklappt && (
        <div className="border-t border-slate-100 px-5 py-4">
          {originalMail && (
            <details className="mb-3 rounded-md bg-slate-50 p-3 text-sm">
              <summary className="cursor-pointer font-medium text-slate-700">
                Auslöser: Original-Mail
              </summary>
              <p className="mt-2 whitespace-pre-wrap text-slate-600">{originalMail}</p>
            </details>
          )}

          <div className="mb-3">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Vorgeschlagene Aktion
            </h4>
            {nachricht ? (
              <div className="mt-1 rounded-md border border-slate-200 p-3 text-sm">
                <p className="text-slate-500">
                  An: <span className="text-slate-800">{nachricht.an}</span> · Betreff:{" "}
                  <span className="text-slate-800">{nachricht.betreff}</span>
                </p>
                {bearbeitenModus ? (
                  <textarea
                    value={entwurfText}
                    onChange={(e) => setEntwurfText(e.target.value)}
                    rows={6}
                    className="mt-2 w-full rounded-md border border-slate-300 p-2 text-sm"
                  />
                ) : (
                  <p className="mt-2 whitespace-pre-wrap text-slate-800">{nachricht.inhalt}</p>
                )}
              </div>
            ) : (
              <pre className="mt-1 overflow-x-auto rounded-md bg-slate-50 p-3 text-xs text-slate-600">
                {JSON.stringify(freigabe.payload, null, 2)}
              </pre>
            )}
          </div>

          <div className="mb-3">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Begründung des Agenten
            </h4>
            <p className="mt-1 text-sm text-slate-700">{freigabe.begruendung}</p>
          </div>

          {(objekt || dienstleister) && (
            <div className="mb-4">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Herangezogene Fakten
              </h4>
              <ul className="mt-1 flex flex-wrap gap-2 text-sm">
                {objekt && (
                  <li className="rounded-md bg-slate-100 px-2 py-1 text-slate-700">
                    Objekt: {objekt.bezeichnung}
                  </li>
                )}
                {dienstleister && (
                  <li className="rounded-md bg-slate-100 px-2 py-1 text-slate-700">
                    Dienstleister: {dienstleister.name} ({dienstleister.gewerk})
                  </li>
                )}
              </ul>
            </div>
          )}

          {freigabe.status !== "offen" && (
            <p className="mb-3 text-sm text-slate-500">
              Entschieden von <strong>{freigabe.entscheider}</strong> am{" "}
              {freigabe.entscheidung_am && alsUtcDatum(freigabe.entscheidung_am).toLocaleString("de-AT")}
              {freigabe.ablehnungsgrund && <> — Grund: {freigabe.ablehnungsgrund}</>}
            </p>
          )}

          {aktionsFehler && (
            <p role="alert" className="mb-3 text-sm text-rose-600">
              {aktionsFehler}
            </p>
          )}

          {freigabe.status === "offen" && (
            <div className="flex flex-col gap-3 border-t border-slate-100 pt-3">
              <div className="flex flex-wrap items-center gap-2">
                {bearbeitenModus ? (
                  <>
                    <button
                      disabled={läuft}
                      onClick={() => freigeben(entwurfText)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
                    >
                      <Check size={15} /> Bearbeiteten Text freigeben
                    </button>
                    <button
                      onClick={() => setBearbeitenModus(false)}
                      className="rounded-lg px-3.5 py-2 text-sm text-slate-600 hover:bg-slate-100"
                    >
                      Abbrechen
                    </button>
                  </>
                ) : ablehnenModus ? (
                  <>
                    <input
                      value={ablehnGrund}
                      onChange={(e) => setAblehnGrund(e.target.value)}
                      placeholder="Ablehnungsgrund…"
                      className="min-w-64 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-100"
                    />
                    <button
                      disabled={läuft || !ablehnGrund.trim()}
                      onClick={ablehnen}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-rose-700 disabled:opacity-50"
                    >
                      <X size={15} /> Ablehnung bestätigen
                    </button>
                    <button
                      onClick={() => setAblehnenModus(false)}
                      className="rounded-lg px-3.5 py-2 text-sm text-slate-600 hover:bg-slate-100"
                    >
                      Abbrechen
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      disabled={läuft}
                      onClick={() => freigeben()}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:opacity-50"
                    >
                      <Check size={15} /> Freigeben
                    </button>
                    {nachricht && (
                      <button
                        onClick={() => setBearbeitenModus(true)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3.5 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                      >
                        <Pencil size={15} /> Bearbeiten
                      </button>
                    )}
                    <button
                      onClick={() => setAblehnenModus(true)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 px-3.5 py-2 text-sm font-medium text-rose-700 transition-colors hover:bg-rose-50"
                    >
                      <X size={15} /> Ablehnen
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
