"""Lädt synthetische Seed-Daten (Objekte, Kontakte, Dienstleister, Dokumente).

Idempotent: Wird die DB bereits befüllt vorgefunden, passiert nichts.
Ausführung: `python -m app.seed`
"""

from pathlib import Path

from sqlmodel import Session, select

from app.db import create_db_and_tables, engine
from app.models import Dienstleister, Dokument, Gewerk, Kontakt, KontaktRolle, Objekt

SEED_DATA_DIR = Path(__file__).resolve().parent.parent / "seed_data"


def _lade_dokument_text(dateiname: str) -> str:
    return (SEED_DATA_DIR / dateiname).read_text(encoding="utf-8")


def seed(session: Session) -> None:
    if session.exec(select(Objekt)).first() is not None:
        print("Seed-Daten bereits vorhanden — überspringe.")
        return

    objekt_musterstrasse = Objekt(
        bezeichnung="Liegenschaft Musterstraße 5",
        adresse="Musterstraße 5, 1010 Wien",
        einheit="Top 4",
        notizen="Altbau, 6 Wohneinheiten",
    )
    objekt_beispielgasse = Objekt(
        bezeichnung="Liegenschaft Beispielgasse 12",
        adresse="Beispielgasse 12, 1020 Wien",
        einheit="Top 2",
        notizen="Neubau, 12 Wohneinheiten",
    )
    session.add(objekt_musterstrasse)
    session.add(objekt_beispielgasse)
    session.commit()
    session.refresh(objekt_musterstrasse)
    session.refresh(objekt_beispielgasse)

    kontakte = [
        Kontakt(
            name="Erika Musterfrau",
            rolle=KontaktRolle.mieter,
            email="erika.musterfrau@example.test",
            telefon="+43 660 1234567",
            objekt_id=objekt_musterstrasse.id,
        ),
        Kontakt(
            name="Max Mustermann",
            rolle=KontaktRolle.mieter,
            email="max.mustermann@example.test",
            telefon="+43 660 7654321",
            objekt_id=objekt_musterstrasse.id,
        ),
        Kontakt(
            name="Petra Beispiel",
            rolle=KontaktRolle.eigentuemer,
            email="petra.beispiel@example.test",
            telefon="+43 664 1112223",
            objekt_id=objekt_musterstrasse.id,
        ),
        Kontakt(
            name="Hans Beispiel",
            rolle=KontaktRolle.mieter,
            email="hans.beispiel@example.test",
            telefon="+43 660 9998887",
            objekt_id=objekt_beispielgasse.id,
        ),
        Kontakt(
            name="Sabine Testperson",
            rolle=KontaktRolle.eigentuemer,
            email="sabine.testperson@example.test",
            telefon="+43 664 5556667",
            objekt_id=objekt_beispielgasse.id,
        ),
    ]
    for kontakt in kontakte:
        session.add(kontakt)

    dienstleister = [
        Dienstleister(
            name="Schlosserei Sicherheit GmbH",
            gewerk=Gewerk.schlosser,
            email="auftraege@schlosserei-sicherheit.example.test",
            telefon="+43 1 2223334",
            konditionen="Anfahrtspauschale EUR 40, Notdienst 24h",
            aktiv=True,
        ),
        Dienstleister(
            name="Schnell-Schlosser Wien",
            gewerk=Gewerk.schlosser,
            email="office@schnell-schlosser.example.test",
            telefon="+43 1 3334445",
            konditionen="Pauschale Türschloss-Tausch EUR 180",
            aktiv=False,
        ),
        Dienstleister(
            name="Installateur Wasserwerk KG",
            gewerk=Gewerk.installateur,
            email="service@wasserwerk-kg.example.test",
            telefon="+43 1 4445556",
            konditionen=None,
            aktiv=True,
        ),
        Dienstleister(
            name="Elektro Blitzschnell",
            gewerk=Gewerk.elektriker,
            email="kontakt@blitzschnell.example.test",
            telefon="+43 1 5556667",
            konditionen=None,
            aktiv=True,
        ),
        Dienstleister(
            name="Maurermeister Fest & Stein",
            gewerk=Gewerk.maurer,
            email="info@fest-stein.example.test",
            telefon="+43 1 6667778",
            konditionen=None,
            aktiv=True,
        ),
    ]
    for dl in dienstleister:
        session.add(dl)

    dokumente = [
        Dokument(
            titel="Hausordnung (Auszug) — § 4 Instandhaltung und Meldungen",
            quelle="hausordnung_auszug.txt",
            inhalt=_lade_dokument_text("hausordnung_auszug.txt"),
            metadaten={"typ": "hausordnung"},
        ),
        Dokument(
            titel="Mustermietvertrag (Auszug) — § 7 Instandhaltungspflichten",
            quelle="mustervertrag_auszug.txt",
            inhalt=_lade_dokument_text("mustervertrag_auszug.txt"),
            metadaten={"typ": "mustervertrag"},
        ),
        Dokument(
            titel="Interne Kostenregelung Reparaturen (Auszug)",
            quelle="kostenregelung_reparaturen.txt",
            inhalt=_lade_dokument_text("kostenregelung_reparaturen.txt"),
            metadaten={"typ": "kostenregelung"},
        ),
    ]
    for dok in dokumente:
        session.add(dok)

    session.commit()
    print("Seed-Daten erfolgreich geladen.")


def main() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        seed(session)


if __name__ == "__main__":
    main()
