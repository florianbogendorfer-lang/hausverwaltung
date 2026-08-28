import { AlertCircle, Inbox, KeyRound, Send, Wrench, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiFehler } from "../api";
import { NachrichtStatusBadge } from "../components/StatusBadge";
import type { Fall, Nachricht, PostfachAbrufErgebnis } from "../types";

// Sicherheitsnetz für den Agent-Loop (läuft synchron in dieser Request):
// das Backend hat inzwischen ein eigenes, kürzeres Timeout für den
// LLM-Aufruf, aber falls die Anfrage aus anderem Grund hängt (Netzwerk,
// überlasteter Container, DB), soll der Bearbeiter nicht endlos vor einem
// drehenden Button sitzen — automatischer Abbruch nach 40s, plus ein
// Button, um jederzeit selbst abzubrechen.
const EINSPIELEN_TIMEOUT_MS = 40_000;

// UI-5 — Simuliertes Postfach + Outbox (§10): vorformulierte Test-Mails
// einspielen oder eigene tippen (löst die Fallbearbeitung aus), sowie die
// Outbox als Nachweis, dass nichts real rausging.

interface TestMail {
  label: string;
  icon: typeof KeyRound;
  von: string;
  betreff: string;
  inhalt: string;
}

const TEST_MAILS: TestMail[] = [
  {
    label: "Türschloss defekt (Referenzfall)",
    icon: KeyRound,
    von: "erika.musterfrau@example.test",
    betreff: "Türschloss defekt",
    inhalt:
      "Guten Tag,\n\ndas Türschloss meiner Wohnung in der Musterstraße 5 ist seit heute " +
      "Morgen defekt und lässt sich nicht mehr versperren. Bitte um rasche Hilfe.\n\n" +
      "Freundliche Grüße\nErika Musterfrau",
  },
  {
    label: "Wasserhahn tropft",
    icon: Wrench,
    von: "hans.beispiel@example.test",
    betreff: "Wasserhahn in der Küche tropft",
    inhalt:
      "Hallo,\n\nseit ein paar Tagen tropft der Wasserhahn in der Küche meiner Wohnung " +
      "in der Beispielgasse 12 ununterbrochen. Könnte das jemand reparieren?\n\nDanke, Hans Beispiel",
  },
  {
    label: "Unklares Anliegen (soll eskalieren)",
    icon: AlertCircle,
    von: "unbekannt@example.test",
    betreff: "Frage",
    inhalt: "Ich hätte da eine allgemeine Frage zu meinem Mietvertrag, können Sie mich anrufen?",
  },
];

// TEST_MAILS ist ein Literal mit fest bekannten Einträgen — der erste
// existiert garantiert, `noUncheckedIndexedAccess` kann das bei einem
// Index-Zugriff aber nicht wissen (siehe tsconfig.app.json).
const [ERSTE_TEST_MAIL] = TEST_MAILS as [TestMail, ...TestMail[]];

export default function Postfach() {
  const navigate = useNavigate();
  const [von, setVon] = useState(ERSTE_TEST_MAIL.von);
  const [betreff, setBetreff] = useState(ERSTE_TEST_MAIL.betreff);
  const [inhalt, setInhalt] = useState(ERSTE_TEST_MAIL.inhalt);
  const [ausgewaehlt, setAusgewaehlt] = useState(ERSTE_TEST_MAIL.label);
  const [sendetGerade, setSendetGerade] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);
  const abbruchRef = useRef<AbortController | null>(null);

  const [outbox, setOutbox] = useState<Nachricht[]>([]);
  const [faelle, setFaelle] = useState<Map<number, Fall>>(new Map());

  async function outboxLaden() {
    const [n, f] = await Promise.all([api.get<Nachricht[]>("/outbox"), api.get<Fall[]>("/faelle")]);
    setOutbox(n);
    setFaelle(new Map(f.map((fall) => [fall.id, fall])));
  }

  useEffect(() => {
    outboxLaden();
  }, []);

  function testMailUebernehmen(mail: TestMail) {
    setVon(mail.von);
    setBetreff(mail.betreff);
    setInhalt(mail.inhalt);
    setAusgewaehlt(mail.label);
  }

  async function einspielen() {
    setSendetGerade(true);
    setFehler(null);
    const controller = new AbortController();
    abbruchRef.current = controller;
    const zeitlimit = setTimeout(() => controller.abort(), EINSPIELEN_TIMEOUT_MS);
    try {
      const fall = await api.post<Fall>(
        "/postfach/eingang",
        { von, betreff, inhalt },
        { signal: controller.signal },
      );
      navigate(`/faelle/${fall.id}`);
    } catch (e) {
      if (controller.signal.aborted) {
        setFehler(
          "Abgebrochen. Die Bearbeitung läuft im Hintergrund evtl. trotzdem weiter — bitte in " +
            "ein paar Sekunden im Board nachsehen, ob der Fall doch erschienen ist.",
        );
      } else {
        setFehler(e instanceof ApiFehler ? e.message : "Mail konnte nicht eingespielt werden.");
      }
    } finally {
      clearTimeout(zeitlimit);
      abbruchRef.current = null;
      setSendetGerade(false);
    }
  }

  function abbrechen() {
    abbruchRef.current?.abort();
  }

  const [ruftAb, setRuftAb] = useState(false);
  const [abrufErgebnis, setAbrufErgebnis] = useState<PostfachAbrufErgebnis | null>(null);
  const [abrufFehler, setAbrufFehler] = useState<string | null>(null);
  const [imapNichtKonfiguriert, setImapNichtKonfiguriert] = useState(false);

  async function echtesPostfachAbrufen() {
    setRuftAb(true);
    setAbrufFehler(null);
    setAbrufErgebnis(null);
    try {
      const ergebnis = await api.post<PostfachAbrufErgebnis>("/postfach/abrufen");
      setAbrufErgebnis(ergebnis);
      if (ergebnis.neue_faelle > 0 || ergebnis.zugeordnete_antworten > 0) {
        await outboxLaden();
      }
    } catch (e) {
      if (e instanceof ApiFehler && e.status === 404) {
        setImapNichtKonfiguriert(true);
      } else {
        setAbrufFehler(e instanceof ApiFehler ? e.message : "Postfach-Abruf fehlgeschlagen.");
      }
    } finally {
      setRuftAb(false);
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
          Postfach &amp; Outbox
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Simulierter Mail-Eingang — kein echter Versand, nichts verlässt das System ungesehen.
        </p>
      </div>

      <div className="mb-8 flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-700">
              <Inbox size={15} /> Echtes Postfach
            </h3>
            <p className="mt-0.5 text-sm text-slate-500">
              Ruft ein per HV_IMAP_* konfiguriertes Postfach ab — neue Mails legen einen Fall an,
              Antworten mit bekannter Ticketnummer im Betreff landen im jeweiligen Fall.
            </p>
          </div>
          <button
            onClick={echtesPostfachAbrufen}
            disabled={ruftAb}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-300 px-3.5 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50"
          >
            <Inbox size={15} /> {ruftAb ? "Ruft ab…" : "Postfach abrufen"}
          </button>
        </div>
        {imapNichtKonfiguriert && (
          <p className="text-sm text-slate-400">
            Kein echtes Postfach konfiguriert — HV_IMAP_HOST (und HV_IMAP_BENUTZER/
            HV_IMAP_PASSWORT) sind nicht gesetzt.
          </p>
        )}
        {abrufFehler && (
          <p role="alert" className="text-sm text-rose-600">
            {abrufFehler}
          </p>
        )}
        {abrufErgebnis && (
          <p className="text-sm text-emerald-700">
            {abrufErgebnis.neue_faelle} neue{abrufErgebnis.neue_faelle === 1 ? "r" : ""} Fall
            {abrufErgebnis.neue_faelle === 1 ? "" : "e"}, {abrufErgebnis.zugeordnete_antworten}{" "}
            Antwort{abrufErgebnis.zugeordnete_antworten === 1 ? "" : "en"} zugeordnet
            {abrufErgebnis.uebersprungene_mails > 0 &&
              `, ${abrufErgebnis.uebersprungene_mails} übersprungen (ungültiger Absender)`}
            .
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Mail einspielen
          </h3>

          <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
            {TEST_MAILS.map((mail) => (
              <button
                key={mail.label}
                onClick={() => testMailUebernehmen(mail)}
                className={`flex flex-col items-start gap-2 rounded-xl border p-3 text-left text-xs font-medium shadow-sm transition-colors ${
                  ausgewaehlt === mail.label
                    ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                    : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <mail.icon size={16} />
                {mail.label}
              </button>
            ))}
          </div>

          <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <label className="text-sm">
              <span className="mb-1 block font-medium text-slate-600">Von</span>
              <input
                value={von}
                onChange={(e) => setVon(e.target.value)}
                maxLength={320}
                className="w-full rounded-lg border border-slate-300 px-3 py-1.5 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium text-slate-600">Betreff</span>
              <input
                value={betreff}
                onChange={(e) => setBetreff(e.target.value)}
                maxLength={500}
                className="w-full rounded-lg border border-slate-300 px-3 py-1.5 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium text-slate-600">Inhalt</span>
              <textarea
                value={inhalt}
                onChange={(e) => setInhalt(e.target.value)}
                rows={8}
                maxLength={20_000}
                className="w-full rounded-lg border border-slate-300 px-3 py-1.5 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
              />
            </label>
            {fehler && (
              <p role="alert" className="text-sm text-rose-600">
                {fehler}
              </p>
            )}
            <div className="flex items-center gap-2">
              <button
                onClick={einspielen}
                disabled={sendetGerade || !von || !betreff || !inhalt}
                className="inline-flex items-center gap-1.5 self-start rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
              >
                <Send size={15} /> {sendetGerade ? "Wird verarbeitet…" : "Mail einspielen"}
              </button>
              {sendetGerade && (
                <button
                  onClick={abbrechen}
                  className="inline-flex items-center gap-1.5 self-start rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50"
                >
                  <X size={15} /> Abbrechen
                </button>
              )}
            </div>
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Outbox
          </h3>
          <p className="mb-3 -mt-1 text-sm text-slate-500">
            Alle „gesendeten" Nachrichten — Nachweis, dass nichts real rausgeht (§2/§13).
          </p>
          <div className="flex flex-col gap-3">
            {outbox.map((n) => (
              <div key={n.id} className="rounded-xl border border-slate-200 bg-white p-3.5 text-sm shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-800">{n.betreff}</span>
                  <NachrichtStatusBadge status={n.status} />
                </div>
                <p className="mt-1 text-slate-500">
                  An: {n.an} · Fall: {faelle.get(n.fall_id)?.betreff ?? `#${n.fall_id}`}
                </p>
                <p className="mt-1 whitespace-pre-wrap text-slate-600">{n.inhalt}</p>
              </div>
            ))}
            {outbox.length === 0 && (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-14 text-center">
                <Send className="mx-auto mb-2 text-slate-300" size={26} />
                <p className="text-slate-400">Outbox ist leer.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
