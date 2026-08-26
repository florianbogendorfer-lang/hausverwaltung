import { Inbox, Mail, Settings2, ShieldCheck } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Fälle", ende: true, icon: Inbox },
  { to: "/freigaben", label: "Freigabe-Queue", icon: ShieldCheck },
  { to: "/postfach", label: "Postfach & Outbox", icon: Mail },
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
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur supports-backdrop-blur:bg-white/70">
        <div className="mx-auto flex max-w-6xl items-center gap-8 px-6 py-3.5">
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
          <nav className="flex gap-1">
            {NAV_ITEMS.map((item) => (
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
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
