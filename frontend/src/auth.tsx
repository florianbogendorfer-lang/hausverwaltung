import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";
import type { Benutzer } from "./types";

interface AuthContextWert {
  benutzer: Benutzer | null;
  ladend: boolean;
  anmelden: (email: string, passwort: string) => Promise<void>;
  abmelden: () => Promise<void>;
}

const AuthContext = createContext<AuthContextWert | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [benutzer, setBenutzer] = useState<Benutzer | null>(null);
  const [ladend, setLadend] = useState(true);

  useEffect(() => {
    api
      .get<Benutzer>("/auth/me")
      .then(setBenutzer)
      .catch(() => setBenutzer(null))
      .finally(() => setLadend(false));
  }, []);

  useEffect(() => {
    // Siehe api.ts: bei jeder 401-Antwort (Session abgelaufen/ungültig)
    // Nutzer zurücksetzen — App.tsx leitet dann automatisch zu /login um.
    const zuruecksetzen = () => setBenutzer(null);
    window.addEventListener("hv:unauthorized", zuruecksetzen);
    return () => window.removeEventListener("hv:unauthorized", zuruecksetzen);
  }, []);

  async function anmelden(email: string, passwort: string) {
    const eingeloggt = await api.post<Benutzer>("/auth/login", { email, passwort });
    setBenutzer(eingeloggt);
  }

  async function abmelden() {
    await api.post("/auth/logout");
    setBenutzer(null);
  }

  return (
    <AuthContext.Provider value={{ benutzer, ladend, anmelden, abmelden }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextWert {
  const wert = useContext(AuthContext);
  if (!wert) throw new Error("useAuth muss innerhalb von <AuthProvider> verwendet werden.");
  return wert;
}
