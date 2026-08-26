import { AlertCircle, KeyRound, Send, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiFehler } from "../api";
import { NachrichtStatusBadge } from "../components/StatusBadge";
import type { Fall, Nachricht } from "../types";

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

export default function Postfach() {
  const navigate = useNavigate();
  const [von, setVon] = useState(TEST_MAILS[0].von);
  const [betreff, setBetreff] = useState(TEST_MAILS[0].betreff);
  const [inhalt, setInhalt] = useState(TEST_MAILS[0].inhalt);
  const [ausgewaehlt, setAusgewaehlt] = useState(TEST_MAILS[0].label);
  const [sendetGerade, setSendetGerade] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);

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
    try {
      const fall = await api.post<Fall>("/postfach/eingang", { von, betreff, inhalt });
      navigate(`/faelle/${fall.id}`);
    } catch (e) {
      setFehler(e instanceof ApiFehler ? e.message : "Mail konnte nicht eingespielt werden.");
    } finally {
      setSendetGerade(false);
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
                className="w-full rounded-lg border border-slate-300 px-3 py-1.5 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium text-slate-600">Betreff</span>
              <input
                value={betreff}
                onChange={(e) => setBetreff(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-1.5 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium text-slate-600">Inhalt</span>
              <textarea
                value={inhalt}
                onChange={(e) => setInhalt(e.target.value)}
                rows={8}
                className="w-full rounded-lg border border-slate-300 px-3 py-1.5 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
              />
            </label>
            {fehler && <p className="text-sm text-rose-600">{fehler}</p>}
            <button
              onClick={einspielen}
              disabled={sendetGerade || !von || !betreff || !inhalt}
              className="inline-flex items-center gap-1.5 self-start rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
            >
              <Send size={15} /> {sendetGerade ? "Wird verarbeitet…" : "Mail einspielen"}
            </button>
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
