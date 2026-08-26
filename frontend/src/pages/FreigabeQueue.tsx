import {
  AlertTriangle,
  Check,
  ChevronDown,
  FileText,
  Mail,
  Pencil,
  ShieldCheck,
  Wrench,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiFehler } from "../api";
import { FreigabeStatusBadge } from "../components/StatusBadge";
import type { Dienstleister, Fall, Freigabe, Nachricht, Objekt } from "../types";

// UI-2 — Freigabe-Queue (§10): das HITL-Kernstück. Jede Karte zeigt
// Auslöser, Entwurf/Payload, Begründung und herangezogene Fakten
// (FR-HITL-4) und bietet die drei Entscheidungen aus FR-HITL-5.

const OPERATOR_KEY = "hv_entscheider";

export default function FreigabeQueue() {
  const [freigaben, setFreigaben] = useState<Freigabe[]>([]);
  const [nurOffene, setNurOffene] = useState(true);
  const [faelle, setFaelle] = useState<Map<number, Fall>>(new Map());
  const [objekte, setObjekte] = useState<Map<number, Objekt>>(new Map());
  const [dienstleister, setDienstleister] = useState<Map<number, Dienstleister>>(new Map());
  const [fehler, setFehler] = useState<string | null>(null);
  const [entscheider, setEntscheider] = useState(
    () => localStorage.getItem(OPERATOR_KEY) ?? "operator@example.test",
  );

  async function laden() {
    try {
      const fr = await api.get<Freigabe[]>(`/freigaben?nur_offene=${nurOffene}`);
      setFreigaben(fr);
      const [alleFaelle, alleObjekte, alleDienstleister] = await Promise.all([
        api.get<Fall[]>("/faelle"),
        api.get<Objekt[]>("/objekte"),
        api.get<Dienstleister[]>("/dienstleister"),
      ]);
      setFaelle(new Map(alleFaelle.map((f) => [f.id, f])));
      setObjekte(new Map(alleObjekte.map((o) => [o.id, o])));
      setDienstleister(new Map(alleDienstleister.map((d) => [d.id, d])));
      setFehler(null);
    } catch (e) {
      setFehler(e instanceof Error ? e.message : "Unbekannter Fehler");
    }
  }

  useEffect(() => {
    laden();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nurOffene]);

  function entscheiderAendern(wert: string) {
    setEntscheider(wert);
    localStorage.setItem(OPERATOR_KEY, wert);
  }

  return (
    <div>
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Freigabe-Queue</h2>
          <p className="mt-1 text-sm text-slate-500">
            Jede Aktion mit Außenwirkung wartet hier auf deine Entscheidung.
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <label className="flex items-center gap-2 text-slate-600">
            Operator
            <input
              value={entscheider}
              onChange={(e) => entscheiderAendern(e.target.value)}
              className="rounded-lg border border-slate-300 px-2.5 py-1.5 shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
            />
          </label>
          <label className="flex items-center gap-2 text-slate-600">
            <input
              type="checkbox"
              checked={nurOffene}
              onChange={(e) => setNurOffene(e.target.checked)}
              className="accent-indigo-600"
            />
            nur offene
          </label>
        </div>
      </div>

      {fehler && (
        <p className="mb-4 rounded-lg bg-rose-50 px-4 py-2.5 text-sm text-rose-700">{fehler}</p>
      )}

      <div className="flex flex-col gap-4">
        {freigaben.map((f) => (
          <FreigabeKarte
            key={f.id}
            freigabe={f}
            fall={faelle.get(f.fall_id)}
            objekt={
              typeof f.kontext_referenzen.objekt_id === "number"
                ? objekte.get(f.kontext_referenzen.objekt_id)
                : undefined
            }
            dienstleister={
              typeof f.kontext_referenzen.dienstleister_id === "number"
                ? dienstleister.get(f.kontext_referenzen.dienstleister_id)
                : undefined
            }
            entscheider={entscheider}
            onEntschieden={laden}
          />
        ))}
        {freigaben.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-14 text-center">
            <ShieldCheck className="mx-auto mb-2 text-slate-300" size={28} />
            <p className="text-slate-400">Keine {nurOffene ? "offenen " : ""}Freigaben.</p>
          </div>
        )}
      </div>
    </div>
  );
}

const AKTIONSTYP_ICON: Record<Freigabe["aktionstyp"], typeof Mail> = {
  nachricht_senden: Mail,
  dienstleister_beauftragen: Wrench,
  rechnung_erfassen: FileText,
};

function FreigabeKarte({
  freigabe,
  fall,
  objekt,
  dienstleister,
  entscheider,
  onEntschieden,
}: {
  freigabe: Freigabe;
  fall?: Fall;
  objekt?: Objekt;
  dienstleister?: Dienstleister;
  entscheider: string;
  onEntschieden: () => void;
}) {
  const [aufgeklappt, setAufgeklappt] = useState(freigabe.status === "offen");
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
        entscheider,
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
      await api.post(`/freigaben/${freigabe.id}/ablehnen`, { entscheider, grund: ablehnGrund });
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
      className={`rounded-xl border bg-white shadow-sm ${freigabe.ueberfaellig ? "border-rose-300" : "border-slate-200"}`}
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
              <span className="font-medium text-slate-900">
                {AKTIONSTYP_LABEL[freigabe.aktionstyp]}
              </span>
              <FreigabeStatusBadge status={freigabe.status} />
              {freigabe.ueberfaellig && (
                <span className="inline-flex items-center gap-1 rounded-full bg-rose-500 px-2 py-0.5 text-xs font-semibold text-white">
                  <AlertTriangle size={11} /> überfällig
                </span>
              )}
            </div>
            <p className="mt-0.5 text-sm text-slate-500">
              Fall: {fall?.betreff ?? `#${freigabe.fall_id}`} · angelegt{" "}
              {new Date(freigabe.erstellt_am).toLocaleString("de-AT")}
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
              {freigabe.entscheidung_am && new Date(freigabe.entscheidung_am).toLocaleString("de-AT")}
              {freigabe.ablehnungsgrund && <> — Grund: {freigabe.ablehnungsgrund}</>}
            </p>
          )}

          {aktionsFehler && <p className="mb-3 text-sm text-rose-600">{aktionsFehler}</p>}

          {freigabe.status === "offen" && (
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
          )}
        </div>
      )}
    </div>
  );
}

const AKTIONSTYP_LABEL: Record<Freigabe["aktionstyp"], string> = {
  nachricht_senden: "Nachricht senden",
  dienstleister_beauftragen: "Dienstleister beauftragen",
  rechnung_erfassen: "Rechnung erfassen",
};
