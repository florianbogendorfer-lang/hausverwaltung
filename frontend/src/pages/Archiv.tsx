import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { FallListe } from "./Board";
import type { Fall, Objekt } from "../types";

// Gegenstück zu Board.tsx: dort werden ABGESCHLOSSEN/ABGEBROCHEN-Fälle
// bewusst herausgefiltert (siehe ARCHIVIERT_STATUS dort), damit sie das
// Board nicht mit erledigten Vorgängen zumüllen — hier bleiben sie
// weiterhin einsehbar, nur getrennt von den aktiven Fällen. Sortiert
// chronologisch absteigend (zuletzt abgeschlossen zuerst) statt nach
// Dringlichkeit — für archivierte Fälle gibt es keine mehr.
export default function Archiv() {
  const navigate = useNavigate();
  const [faelle, setFaelle] = useState<Fall[]>([]);
  const [objekte, setObjekte] = useState<Objekt[]>([]);
  const [suche, setSuche] = useState("");
  const [ladeFehler, setLadeFehler] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.get<Fall[]>("/faelle"), api.get<Objekt[]>("/objekte")])
      .then(([f, o]) => {
        setFaelle(f);
        setObjekte(o);
        setLadeFehler(null);
      })
      .catch((e) => setLadeFehler(e instanceof Error ? e.message : "Unbekannter Fehler"));
  }, []);

  const objektNachId = useMemo(() => new Map(objekte.map((o) => [o.id, o])), [objekte]);

  const archivierte = useMemo(() => {
    const suchbegriff = suche.trim().toLowerCase();
    return faelle.filter((f) => {
      if (f.status !== "ABGESCHLOSSEN" && f.status !== "ABGEBROCHEN") return false;
      if (!suchbegriff) return true;
      const objekt = f.objekt_id ? objektNachId.get(f.objekt_id) : undefined;
      return (
        f.betreff.toLowerCase().includes(suchbegriff) ||
        objekt?.bezeichnung.toLowerCase().includes(suchbegriff)
      );
    });
  }, [faelle, suche, objektNachId]);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Archiv</h2>
          <p className="mt-1 text-sm text-slate-500">
            Abgeschlossene und abgebrochene Fälle — aus dem Board ausgeblendet, hier weiterhin
            einsehbar.
          </p>
        </div>
        <input
          value={suche}
          onChange={(e) => setSuche(e.target.value)}
          placeholder="Suchen nach Betreff oder Objekt…"
          className="w-64 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
        />
      </div>

      {ladeFehler && (
        <p className="mb-4 rounded-lg bg-rose-50 px-4 py-2.5 text-sm text-rose-700">
          Archiv konnte nicht geladen werden: {ladeFehler}
        </p>
      )}

      <FallListe
        faelle={archivierte}
        objektNachId={objektNachId}
        offeneFreigabenProFall={new Map()}
        onOeffnen={(id) => navigate(`/faelle/${id}`)}
        geoeffneterFallId={null}
        sortierung="aktualisiert_absteigend"
      />
    </div>
  );
}
