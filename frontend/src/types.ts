// Spiegelt die Backend-Modelle aus backend/app/models/ (§7 DM-1..DM-9).

export type Gewerk = "schlosser" | "maurer" | "installateur" | "elektriker" | "sonstiges";
export type KontaktRolle = "mieter" | "eigentümer";
export type FallTyp = "reparaturmeldung";

export type FallStatus =
  | "NEU"
  | "EINGEORDNET"
  | "WARTET_AUF_FREIGABE"
  | "DIENSTLEISTER_BEAUFTRAGT"
  | "TERMIN_BESTAETIGT"
  | "ARBEIT_ERLEDIGT"
  | "RECHNUNG_ERFASST"
  | "ABGESCHLOSSEN"
  | "ESKALIERT"
  | "ABGEBROCHEN";

export type NachrichtRichtung = "eingehend" | "ausgehend";
export type NachrichtStatus =
  | "empfangen"
  | "entwurf"
  | "freigegeben"
  | "gesendet_simuliert"
  | "gesendet"
  | "abgelehnt";
export type TracePhase = "wahrnehmung" | "plan" | "tool_call" | "tool_result" | "entscheidung" | "reasoning";
export type Aktionstyp = "nachricht_senden" | "dienstleister_beauftragen" | "rechnung_erfassen";
export type FreigabeStatus = "offen" | "freigegeben" | "bearbeitet_freigegeben" | "abgelehnt";
export type Akteur = "agent" | "operator" | "system";

export interface Objekt {
  id: number;
  bezeichnung: string;
  adresse: string;
  einheit?: string | null;
  notizen?: string | null;
}

export interface Kontakt {
  id: number;
  name: string;
  rolle: KontaktRolle;
  email: string;
  telefon?: string | null;
  objekt_id?: number | null;
}

export interface Dienstleister {
  id: number;
  name: string;
  gewerk: Gewerk;
  email: string;
  telefon?: string | null;
  konditionen?: string | null;
  aktiv: boolean;
}

export interface Dokument {
  id: number;
  titel: string;
  quelle: string;
  inhalt: string;
  metadaten: Record<string, unknown>;
}

export interface Fall {
  id: number;
  typ: FallTyp;
  gewerk?: Gewerk | null;
  objekt_id?: number | null;
  melder_kontakt_id?: number | null;
  dienstleister_id?: number | null;
  status: FallStatus;
  betreff: string;
  zusammenfassung?: string | null;
  konfidenz?: number | null;
  erstellt_am: string;
  geaendert_am: string;
}

export interface Nachricht {
  id: number;
  fall_id: number;
  richtung: NachrichtRichtung;
  kanal: "email";
  von: string;
  an: string;
  betreff: string;
  inhalt: string;
  status: NachrichtStatus;
  erstellt_am: string;
}

export interface Trace {
  id: number;
  fall_id: number;
  schritt_nr: number;
  phase: TracePhase;
  modell?: string | null;
  inhalt: string;
  token_kosten?: number | null;
  dauer_ms?: number | null;
  zeitstempel: string;
}

export interface Aktion {
  id: number;
  fall_id: number;
  zeitstempel: string;
  akteur: Akteur;
  aktionsart: string;
  details: Record<string, unknown>;
  freigabe_id?: number | null;
}

export interface Freigabe {
  id: number;
  fall_id: number;
  aktionstyp: Aktionstyp;
  payload: Record<string, unknown>;
  begruendung: string;
  kontext_referenzen: Record<string, unknown>;
  status: FreigabeStatus;
  idempotency_key: string;
  entscheider?: string | null;
  entscheidung_am?: string | null;
  ablehnungsgrund?: string | null;
  erstellt_am: string;
  ueberfaellig: boolean;
}
