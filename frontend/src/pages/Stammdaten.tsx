import { useEffect, useState } from "react";
import { api, ApiFehler } from "../api";
import type { Dienstleister, Gewerk, Kontakt, KontaktRolle, Objekt } from "../types";

// UI-4 — Stammdatenpflege (§10): einfache CRUD-Formulare + Listen für
// Objekte, Kontakte, Dienstleister.

type Tab = "objekte" | "kontakte" | "dienstleister";

export default function Stammdaten() {
  const [tab, setTab] = useState<Tab>("objekte");

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold">Stammdatenpflege</h2>
      <div className="mb-6 flex gap-1">
        {(["objekte", "kontakte", "dienstleister"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium capitalize ${
              tab === t ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {t}
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
      <div className="lg:col-span-2 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Bezeichnung</th>
              <th className="px-4 py-2 font-medium">Adresse</th>
              <th className="px-4 py-2 font-medium">Einheit</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {liste.map((o) => (
              <tr key={o.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-2">{o.bezeichnung}</td>
                <td className="px-4 py-2 text-slate-600">{o.adresse}</td>
                <td className="px-4 py-2 text-slate-600">{o.einheit ?? "—"}</td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => loeschen(o.id)} className="text-xs text-rose-600 hover:underline">
                    löschen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-700">Neues Objekt</h3>
        <Feld label="Bezeichnung" value={formular.bezeichnung} onChange={(v) => setFormular({ ...formular, bezeichnung: v })} />
        <Feld label="Adresse" value={formular.adresse} onChange={(v) => setFormular({ ...formular, adresse: v })} />
        <Feld label="Einheit" value={formular.einheit} onChange={(v) => setFormular({ ...formular, einheit: v })} />
        {fehler && <p className="text-sm text-rose-600">{fehler}</p>}
        <button
          onClick={anlegen}
          disabled={!formular.bezeichnung || !formular.adresse}
          className="self-start rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Anlegen
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
      <div className="lg:col-span-2 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
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
              <tr key={k.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-2">{k.name}</td>
                <td className="px-4 py-2 text-slate-600">{k.rolle}</td>
                <td className="px-4 py-2 text-slate-600">{k.email}</td>
                <td className="px-4 py-2 text-slate-600">
                  {objekte.find((o) => o.id === k.objekt_id)?.bezeichnung ?? "—"}
                </td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => loeschen(k.id)} className="text-xs text-rose-600 hover:underline">
                    löschen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-700">Neuer Kontakt</h3>
        <Feld label="Name" value={formular.name} onChange={(v) => setFormular({ ...formular, name: v })} />
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-600">Rolle</span>
          <select
            value={formular.rolle}
            onChange={(e) => setFormular({ ...formular, rolle: e.target.value as KontaktRolle })}
            className="w-full rounded-md border border-slate-300 px-3 py-1.5"
          >
            <option value="mieter">Mieter</option>
            <option value="eigentümer">Eigentümer</option>
          </select>
        </label>
        <Feld label="E-Mail" value={formular.email} onChange={(v) => setFormular({ ...formular, email: v })} />
        {fehler && <p className="text-sm text-rose-600">{fehler}</p>}
        <button
          onClick={anlegen}
          disabled={!formular.name || !formular.email}
          className="self-start rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Anlegen
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
      <div className="lg:col-span-2 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-500">
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
              <tr key={d.id} className="border-b border-slate-100 last:border-0">
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
                  <button onClick={() => loeschen(d.id)} className="text-xs text-rose-600 hover:underline">
                    löschen
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-700">Neuer Dienstleister</h3>
        <Feld label="Name" value={formular.name} onChange={(v) => setFormular({ ...formular, name: v })} />
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-600">Gewerk</span>
          <select
            value={formular.gewerk}
            onChange={(e) => setFormular({ ...formular, gewerk: e.target.value as Gewerk })}
            className="w-full rounded-md border border-slate-300 px-3 py-1.5"
          >
            <option value="schlosser">Schlosser</option>
            <option value="maurer">Maurer</option>
            <option value="installateur">Installateur</option>
            <option value="elektriker">Elektriker</option>
            <option value="sonstiges">Sonstiges</option>
          </select>
        </label>
        <Feld label="E-Mail" value={formular.email} onChange={(v) => setFormular({ ...formular, email: v })} />
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
          className="self-start rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Anlegen
        </button>
      </div>
    </div>
  );
}

function Feld({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="text-sm">
      <span className="mb-1 block font-medium text-slate-600">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-slate-300 px-3 py-1.5"
      />
    </label>
  );
}
