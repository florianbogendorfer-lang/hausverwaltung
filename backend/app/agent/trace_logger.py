"""Schreibt den Denk-/Schritt-Verlauf eines Loop-Durchlaufs (DM-8, §11)."""

from sqlmodel import Session, select

from app.models import Trace, TracePhase


class TraceLogger:
    def __init__(self, session: Session, fall_id: int) -> None:
        self.session = session
        self.fall_id = fall_id
        self._naechster_schritt = self._ermittle_naechsten_schritt()

    def _ermittle_naechsten_schritt(self) -> int:
        letzter = self.session.exec(
            select(Trace.schritt_nr)
            .where(Trace.fall_id == self.fall_id)
            .order_by(Trace.schritt_nr.desc())
        ).first()
        return (letzter or 0) + 1

    def log(
        self,
        phase: TracePhase,
        inhalt: str,
        modell: str | None = None,
        token_kosten: int | None = None,
        dauer_ms: int | None = None,
    ) -> Trace:
        trace = Trace(
            fall_id=self.fall_id,
            schritt_nr=self._naechster_schritt,
            phase=phase,
            modell=modell,
            inhalt=inhalt,
            token_kosten=token_kosten,
            dauer_ms=dauer_ms,
        )
        self.session.add(trace)
        self.session.commit()
        self.session.refresh(trace)
        self._naechster_schritt += 1
        return trace
