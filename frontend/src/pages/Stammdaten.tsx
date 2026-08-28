import { Building2, Plus, Trash2, UserRound, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiFehler } from "../api";
import type { Dienstleister, Gewerk, Kontakt, KontaktRolle, Objekt } from "../types";

// UI-4 — Stammdatenpflege (§10): einfache CRUD-Formulare + Listen für
// Objekte, Kontakte, Dienstleister.

type Tab = "objekte" | "kontakte" | "dienstleister";

const TABS: { key: Tab; label: string; icon: typeof Building2 }[] = [
  { key: "objekte", label: "Objekte", icon: Building2 },
  { key: "kontakte", label: "Kontakte", icon: UserRound },
  { key: "dienstleister", label: "Dienstleister", icon: Wrench },
];

export default function Stammdaten() {
  const [tab, setTab] = useState<Tab>("objekte");

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Stammdatenpflege</h2>
        <p className="mt-1 text-sm text-slate-500">
          Objekte, Kontakte und Dienstleister, auf die sich der Agent bei der Fallbearbeitung stützt.
        </p>
      </div>
      <div className="mb-6 flex gap-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-indigo-600 text-white shadow-sm shadow-indigo-200"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <t.icon size={15} />
            {t.label}
          </button>
        ))}
      </div>
      {tab === "objekte" && <ObjektePflege />}
      {tab === "kontakte" && <KontaktePflege />}
      {tab === "dienstleister" && <DienstleisterPflege />}
    </div>
  );
}

const LEERES_OBJEKT = { bezeichnung: "", adresse: "", einheit: "", notizen: "" };

function ObjektePflege() {
  const [liste, setListe] = useState<Objekt[]>([]);
  const [formular, setFormular] = useState(LEERES_OBJEKT);
  const [fehler, setFehler] = useState<string | null>(null);

  async function laden() {
    setListe(await api.get<Objekt[]>("/objekte"));
  }
  useEffect(() => {
    laden();
  }, []);

  async function anlegen() {
    setFehler(null);
    try {
      await api.post("/objekte", formular);
      setFormular(LEERES_OBJEKT);
      laden();
    } catch (e) {
      setFehler(e instanceof ApiFehler ? e.message : "Anlegen fehlgeschlagen.");
    }
  }

  async function loeschen(id: number) {
    await api.del(`/objekte/${id}`);
    laden();
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50/70 text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Bezeichnung</th>
              <th className="px-4 py-2 font-medium">Adresse</th>
              <th className="px-4 py-2 font-medium">Einheit</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {liste.map((o) => (
              <tr key={o.id} className="border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50">
                <td className="px-4 py-2">{o.bezeichnung}</td>
                <td className="px-4 py-2 text-slate-600">{o.adresse}</td>
                <td className="px-4 py-2 text-slate-600">{o.einheit ?? "—"}</td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => loeschen(o.id)} className="inline-flex items-center gap-1 text-xs font-medium text-rose-600 hover:text-rose-700">
                    <Trash2 size={12} /> löschen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700">Neues Objekt</h3>
        <Feld label="Bezeichnung" value={formular.bezeichnung} onChange={(v) => setFormular({ ...formular, bezeichnung: v })} maxLength={200} />
        <Feld label="Adresse" value={formular.adresse} onChange={(v) => setFormular({ ...formular, adresse: v })} maxLength={300} />
        <Feld label="Einheit" value={formular.einheit} onChange={(v) => setFormular({ ...formular, einheit: v })} maxLength={100} />
        {fehler && <p className="text-sm text-rose-600">{fehler}</p>}
        <button
          onClick={anlegen}
          disabled={!formular.bezeichnung || !formular.adresse}
          className="self-start inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
        >
          <Plus size={15} /> Anlegen
        </button>
      </div>
    </div>
  );
}

const LEERER_KONTAKT = { name: "", rolle: "mieter" as KontaktRolle, email: "", telefon: "" };

function KontaktePflege() {
  const [liste, setListe] = useState<Kontakt[]>([]);
  const [objekte, setObjekte] = useState<Objekt[]>([]);
  const [formular, setFormular] = useState(LEERER_KONTAKT);
  const [fehler, setFehler] = useState<string | null>(null);

  async function laden() {
    const [k, o] = await Promise.all([api.get<Kontakt[]>("/kontakte"), api.get<Objekt[]>("/objekte")]);
    setListe(k);
    setObjekte(o);
  }
  useEffect(() => {
    laden();
  }, []);

  async function anlegen() {
    setFehler(null);
    try {
      await api.post("/kontakte", formular);
      setFormular(LEERER_KONTAKT);
      laden();
    } catch (e) {
      setFehler(e instanceof ApiFehler ? e.message : "Anlegen fehlgeschlagen.");
    }
  }

  async function loeschen(id: number) {
    await api.del(`/kontakte/${id}`);
    laden();
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50/70 text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Rolle</th>
              <th className="px-4 py-2 font-medium">E-Mail</th>
              <th className="px-4 py-2 font-medium">Objekt</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {liste.map((k) => (
              <tr key={k.id} className="border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50">
                <td className="px-4 py-2">{k.name}</td>
                <td className="px-4 py-2 text-slate-600">{k.rolle}</td>
                <td className="px-4 py-2 text-slate-600">{k.email}</td>
                <td className="px-4 py-2 text-slate-600">
                  {objekte.find((o) => o.id === k.objekt_id)?.bezeichnung ?? "—"}
                </td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => loeschen(k.id)} className="inline-flex items-center gap-1 text-xs font-medium text-rose-600 hover:text-rose-700">
                    <Trash2 size={12} /> löschen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700">Neuer Kontakt</h3>
        <Feld label="Name" value={formular.name} onChange={(v) => setFormular({ ...formular, name: v })} maxLength={200} />
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-600">Rolle</span>
          <select
            value={formular.rolle}
            onChange={(e) => setFormular({ ...formular, rolle: e.target.value as KontaktRolle })}
            className="w-full rounded-lg border border-slate-300 px-3 py-1.5 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          >
            <option value="mieter">Mieter</option>
            <option value="eigentümer">Eigentümer</option>
          </select>
        </label>
        <Feld label="E-Mail" value={formular.email} onChange={(v) => setFormular({ ...formular, email: v })} maxLength={320} />
        {fehler && <p className="text-sm text-rose-600">{fehler}</p>}
        <button
          onClick={anlegen}
          disabled={!formular.name || !formular.email}
          className="self-start inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
        >
          <Plus size={15} /> Anlegen
        </button>
      </div>
    </div>
  );
}

const LEERER_DIENSTLEISTER = { name: "", gewerk: "schlosser" as Gewerk, email: "", telefon: "", konditionen: "", aktiv: true };

function DienstleisterPflege() {
  const [liste, setListe] = useState<Dienstleister[]>([]);
  const [formular, setFormular] = useState(LEERER_DIENSTLEISTER);
  const [fehler, setFehler] = useState<string | null>(null);

  async function laden() {
    setListe(await api.get<Dienstleister[]>("/dienstleister"));
  }
  useEffect(() => {
    laden();
  }, []);

  async function anlegen() {
    setFehler(null);
    try {
      await api.post("/dienstleister", formular);
      setFormular(LEERER_DIENSTLEISTER);
      laden();
    } catch (e) {
      setFehler(e instanceof ApiFehler ? e.message : "Anlegen fehlgeschlagen.");
    }
  }

  async function loeschen(id: number) {
    await api.del(`/dienstleister/${id}`);
    laden();
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50/70 text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Gewerk</th>
              <th className="px-4 py-2 font-medium">E-Mail</th>
              <th className="px-4 py-2 font-medium">Aktiv</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {liste.map((d) => (
              <tr key={d.id} className="border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50">
                <td className="px-4 py-2">{d.name}</td>
                <td className="px-4 py-2 text-slate-600">{d.gewerk}</td>
                <td className="px-4 py-2 text-slate-600">{d.email}</td>
                <td className="px-4 py-2">
                  {d.aktiv ? (
                    <span className="text-emerald-600">aktiv</span>
                  ) : (
                    <span className="text-slate-400">inaktiv</span>
                  )}
                </td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => loeschen(d.id)} className="inline-flex items-center gap-1 text-xs font-medium text-rose-600 hover:text-rose-700">
                    <Trash2 size={12} /> löschen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700">Neuer Dienstleister</h3>
        <Feld label="Name" value={formular.name} onChange={(v) => setFormular({ ...formular, name: v })} maxLength={200} />
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-600">Gewerk</span>
          <select
            value={formular.gewerk}
            onChange={(e) => setFormular({ ...formular, gewerk: e.target.value as Gewerk })}
            className="w-full rounded-lg border border-slate-300 px-3 py-1.5 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
          >
            <option value="schlosser">Schlosser</option>
            <option value="maurer">Maurer</option>
            <option value="installateur">Installateur</option>
            <option value="elektriker">Elektriker</option>
            <option value="sonstiges">Sonstiges</option>
          </select>
        </label>
        <Feld label="E-Mail" value={formular.email} onChange={(v) => setFormular({ ...formular, email: v })} maxLength={320} />
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={formular.aktiv}
            onChange={(e) => setFormular({ ...formular, aktiv: e.target.checked })}
          />
          aktiv
        </label>
        {fehler && <p className="text-sm text-rose-600">{fehler}</p>}
        <button
          onClick={anlegen}
          disabled={!formular.name || !formular.email}
          className="self-start inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:opacity-50"
        >
          <Plus size={15} /> Anlegen
        </button>
      </div>
    </div>
  );
}

function Feld({
  label,
  value,
  onChange,
  maxLength,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  // Spiegelt die Field(max_length=...)-Grenzen der Backend-Eingabemodelle
  // (OWASP Input Validation Cheat Sheet) — ohne das erfährt der Bearbeiter
  // erst nach dem Absenden per 422, dass der Wert zu lang ist.
  maxLength?: number;
}) {
  return (
    <label className="text-sm">
      <span className="mb-1 block font-medium text-slate-600">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={maxLength}
        className="w-full rounded-lg border border-slate-300 px-3 py-1.5 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
      />
    </label>
  );
}
