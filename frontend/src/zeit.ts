// Das Backend serialisiert Zeitstempel als naives UTC (kein "Z"/Offset im
// ISO-String, z. B. "2026-08-27T21:12:00.727371") — `new Date(...)` würde
// das sonst als lokale Zeit interpretieren und damit um den UTC-Offset
// des Browsers verschoben anzeigen. Immer diese Funktion statt `new
// Date(iso)` verwenden, wenn ein Zeitstempel vom Backend geparst wird.
export function alsUtcDatum(iso: string): Date {
  const hatZeitzone = /[Zz]|[+-]\d{2}:\d{2}$/.test(iso);
  return new Date(hatZeitzone ? iso : `${iso}Z`);
}
