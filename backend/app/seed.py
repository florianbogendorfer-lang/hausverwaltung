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
    objekt_kanal = Objekt(
        bezeichnung="Liegenschaft Am Kanal 8",
        adresse="Am Kanal 8, 1030 Wien",
        einheit="Top 7",
        notizen="Sanierter Altbau, 9 Wohneinheiten",
    )
    objekt_ringstrasse = Objekt(
        bezeichnung="Liegenschaft Ringstraße 21",
        adresse="Ringstraße 21, 4020 Linz",
        einheit="Top 1",
        notizen="Neubau, 4 Wohneinheiten, Erdgeschoß-Lokal",
    )
    for objekt in (objekt_musterstrasse, objekt_beispielgasse, objekt_kanal, objekt_ringstrasse):
        session.add(objekt)
    session.commit()
    for objekt in (objekt_musterstrasse, objekt_beispielgasse, objekt_kanal, objekt_ringstrasse):
        session.refresh(objekt)

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
        Kontakt(
            name="Tobias Kanaleck",
            rolle=KontaktRolle.mieter,
            email="tobias.kanaleck@example.test",
            telefon="+43 660 3334445",
            objekt_id=objekt_kanal.id,
        ),
        Kontakt(
            name="Julia Wassergasse",
            rolle=KontaktRolle.mieter,
            email="julia.wassergasse@example.test",
            telefon="+43 660 4445556",
            objekt_id=objekt_kanal.id,
        ),
        Kontakt(
            name="Markus Ringstraßer",
            rolle=KontaktRolle.eigentuemer,
            email="markus.ringstrasser@example.test",
            telefon="+43 664 7778889",
            objekt_id=objekt_ringstrasse.id,
        ),
        Kontakt(
            name="Nina Lokalbesitzerin",
            rolle=KontaktRolle.mieter,
            email="nina.lokalbesitzerin@example.test",
            telefon="+43 660 8889990",
            objekt_id=objekt_ringstrasse.id,
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
            name="Rohrfrei Notdienst",
            gewerk=Gewerk.installateur,
            email="notdienst@rohrfrei.example.test",
            telefon="+43 1 4447779",
            konditionen="24h-Notdienst, Anfahrtspauschale EUR 60",
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
            name="Elektrotechnik Ohm & Watt",
            gewerk=Gewerk.elektriker,
            email="office@ohm-watt.example.test",
            telefon="+43 1 5559991",
            konditionen=None,
            aktiv=False,
        ),
        Dienstleister(
            name="Maurermeister Fest & Stein",
            gewerk=Gewerk.maurer,
            email="info@fest-stein.example.test",
            telefon="+43 1 6667778",
            konditionen=None,
            aktiv=True,
        ),
        Dienstleister(
            name="Bau & Putz Linz GmbH",
            gewerk=Gewerk.maurer,
            email="anfragen@bauputz-linz.example.test",
            telefon="+43 732 1112223",
            konditionen=None,
            aktiv=True,
        ),
        Dienstleister(
            name="Facility Allround Service",
            gewerk=Gewerk.sonstiges,
            email="service@facility-allround.example.test",
            telefon="+43 1 7778889",
            konditionen="Für Anliegen ohne klares Gewerk, z. B. Schädlingsbekämpfung",
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
