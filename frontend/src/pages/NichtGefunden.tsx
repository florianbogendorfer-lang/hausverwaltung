import { Link } from "react-router-dom";

export default function NichtGefunden() {
  return (
    <div className="flex flex-col items-center gap-3 py-16 text-center">
      <p className="text-2xl font-semibold tracking-tight text-slate-900">Seite nicht gefunden</p>
      <p className="text-sm text-slate-500">Diese Adresse gibt es hier nicht.</p>
      <Link
        to="/"
        className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
      >
        Zurück zum Board
      </Link>
    </div>
  );
}
