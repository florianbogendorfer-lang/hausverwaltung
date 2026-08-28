"""Wiederverwendbare Pydantic-Feld-Validatoren (OWASP Input Validation
Cheat Sheet: Eingabeformat prüfen, nicht nur Länge)."""

from email_validator import EmailNotValidError, validate_email


def email_gueltig_pruefen(klartext: str) -> str:
    """Prüft nur das Format (Syntax) — keine DNS-Abfrage
    (`check_deliverability=False`), sonst wäre jeder Kontakt-/Dienstleister-
    Anlage von einer Netzwerkanfrage abhängig (§0: netzwerkfreie Tests) und
    ein Betreiber könnte durch einen kurzzeitigen DNS-Ausfall an der
    eigentlichen Aufgabe gehindert werden.

    `test_environment=True`, weil diese App selbst Demo-/Seed-Konten unter
    der RFC-2606-reservierten `.test`-Domain anlegt (admin@example.test,
    siehe app/seed.py) — ohne dieses Flag würde email_validator genau diese
    Adressen als "reserved/special-use domain" ablehnen, obwohl sie exakt
    dem von dieser App selbst verwendeten Demo-Muster entsprechen."""
    try:
        ergebnis = validate_email(klartext, check_deliverability=False, test_environment=True)
    except EmailNotValidError as exc:
        raise ValueError(f"Ungültige E-Mail-Adresse: {exc}") from exc
    return ergebnis.normalized
