import { Archive, KeyRound, LayoutGrid, LogOut, Mail, Settings2, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "./api";
import { useAuth } from "./auth";
import { PasswortAendernDialog } from "./components/PasswortAendernDialog";
import type { Freigabe } from "./types";

const NAV_ITEMS = [
  { to: "/", label: "Board", ende: true, icon: LayoutGrid },
  { to: "/postfach", label: "Postfach & Outbox", icon: Mail },
  { to: "/archiv", label: "Archiv", icon: Archive },
  { to: "/stammdaten", label: "Stammdaten", icon: Settings2 },
];

function Logo() {
  return (
    <svg width="30" height="30" viewBox="0 0 32 32" fill="none" className="shrink-0">
      <rect width="32" height="32" rx="8" fill="#4338CA" />
      <path d="M16 6.5 6 14v11.5h6.5V19h7v6.5H26V14L16 6.5Z" fill="white" />
      <path
        d="M13.5 21.8 15.4 23.7 19 19.2"
        stroke="#4338CA"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function App() {
  const location = useLocation();
  const { benutzer, ladend, abmelden } = useAuth();
  const [offeneFreigaben, setOffeneFreigaben] = useState(0);
  const [passwortDialogOffen, setPasswortDialogOffen] = useState(false);

  useEffect(() => {
    if (!benutzer) return;
    api
      .get<Freigabe[]>("/freigaben?nur_offene=true")
      .then((liste) => setOffeneFreigaben(liste.length))
      .catch(() => undefined);
  }, [location.pathname, benutzer]);

  if (ladend) return <p className="p-8 text-sm text-slate-400">Lädt…</p>;
  if (!benutzer) return <Navigate to="/login" replace />;

  const navItems = [
    ...NAV_ITEMS,
    ...(benutzer.rolle === "admin"
      ? [{ to: "/benutzer", label: "Benutzer", ende: true, icon: Users }]
      : []),
  ];

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur supports-backdrop-blur:bg-white/70">
        <div className="mx-auto flex max-w-[1400px] items-center gap-8 px-6 py-3.5">
          <div className="flex items-center gap-2.5">
            <Logo />
            <div className="leading-tight">
              <p className="text-[15px] font-semibold tracking-tight text-slate-900">
                Hausverwaltung
              </p>
              <p className="text-[11px] font-medium uppercase tracking-wider text-indigo-600">
                Agent
              </p>
            </div>
          </div>
          <nav className="flex flex-1 gap-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.ende}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-indigo-300 ${
                    isActive
                      ? "bg-indigo-600 text-white shadow-sm shadow-indigo-200"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`
                }
              >
                <item.icon size={16} strokeWidth={2.25} />
                {item.label}
                {item.to === "/" && offeneFreigaben > 0 && (
                  <span className="ml-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-500 px-1 text-xs font-semibold text-white">
                    {offeneFreigaben}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <div className="text-right leading-tight">
              <p className="font-medium text-slate-700">{benutzer.name}</p>
              <p className="text-xs text-slate-400">{benutzer.rolle === "admin" ? "Admin" : "User"}</p>
            </div>
            <button
              onClick={() => setPasswortDialogOffen(true)}
              title="Passwort ändern"
              aria-label="Passwort ändern"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
            >
              <KeyRound size={16} />
            </button>
            <button
              onClick={() => abmelden()}
              title="Abmelden"
              aria-label="Abmelden"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1400px] px-6 py-8">
        <Outlet />
      </main>
      {passwortDialogOffen && (
        <PasswortAendernDialog onGeschlossen={() => setPasswortDialogOffen(false)} />
      )}
    </div>
  );
}
