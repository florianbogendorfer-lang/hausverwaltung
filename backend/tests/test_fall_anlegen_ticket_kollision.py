"""app.agent.tools.fall_anlegen — Retry bei ticket_nummer-Kollision.

ticket_nummer hat bewusst nur 32 Bit Entropie (kurz, für Menschen
aussprech-/nennbar, siehe app.models.fall._ticket_nummer_erzeugen) — eine
zufällige Kollision ist bei wachsendem Datenbestand nicht mehr
vernachlässigbar (Geburtstagsparadoxon). Dieser Test erzwingt eine
Kollision deterministisch (secrets.token_hex gemockt) und prüft, dass
fall_anlegen automatisch mit einem neuen Zufallswert erneut versucht,
statt den UNIQUE-Constraint-Verstoß als 500er durchschlagen zu lassen."""

import secrets as echtes_secrets_modul
from unittest.mock import patch

from sqlmodel import Session

from app.agent import tools
from app.models import FallTyp
from tests.conftest import engine


def test_fall_anlegen_erzeugt_bei_ticket_nummer_kollision_automatisch_neuen_versuch():
    aufrufe = {"n": 0}
    echter_token_hex = echtes_secrets_modul.token_hex

    def fake_token_hex(n: int) -> str:
        aufrufe["n"] += 1
        # Die ersten beiden Aufrufe liefern denselben Wert (erzwingt eine
        # Kollision beim zweiten fall_anlegen-Aufruf), danach echter Zufall.
        if aufrufe["n"] <= 2:
            return "00" * n
        return echter_token_hex(n)

    with Session(engine) as session, patch(
        "app.models.fall.secrets.token_hex", side_effect=fake_token_hex
    ):
        erster = tools.fall_anlegen(session, FallTyp.reparaturmeldung, "Fall eins")
        zweiter = tools.fall_anlegen(session, FallTyp.reparaturmeldung, "Fall zwei")
        assert erster.ticket_nummer != zweiter.ticket_nummer

    # Kollision + Retry bedeutet mindestens drei token_hex-Aufrufe
    # (1 für erster, 2 kollidierender + 1 erfolgreicher für zweiter).
    assert aufrufe["n"] >= 3
