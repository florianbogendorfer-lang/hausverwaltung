"""Modell-Routing-Abstraktion (FR-AGENT-2, NFR-5).

Wählt je nach Aufgabenklasse ein "günstiges" oder "starkes" Modell und
protokolliert, welches Modell tatsächlich verwendet wurde (§11). Der
LLM-Aufruf selbst läuft hinter dem `LLMClient`-Protokoll — Produktivcode
nutzt die Anthropic API direkt (§12), Tests injizieren einen Fake-Client,
damit sie ohne Netzwerkzugriff laufen.

FR-AGENT-3: strukturierte Schritte laufen mit temperature=0 und werden
gegen ein Pydantic-Schema validiert; bei Verletzung wird erneut versucht,
danach eskaliert der Aufrufer (siehe `SchemaValidierungFehlgeschlagen`).
"""

import enum
import json
import time
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import settings

T = TypeVar("T", bound=BaseModel)


class ModellStufe(str, enum.Enum):
    guenstig = "guenstig"
    stark = "stark"


class LLMAntwort(BaseModel):
    text: str
    modell: str
    dauer_ms: int


class LLMClient(Protocol):
    def complete(
        self, modell: str, system: str, prompt: str, temperature: float
    ) -> LLMAntwort: ...


class AnthropicLLMClient:
    """Ruft die Anthropic Messages API auf (direkte API, §12 — für den
    Prototyp mit synthetischen Daten zulässig; für echte Mieterdaten ist
    laut §12/§13 auf AWS Bedrock eu-central-1 umzustellen)."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def complete(
        self, modell: str, system: str, prompt: str, temperature: float = 0.0
    ) -> LLMAntwort:
        client = self._get_client()
        start = time.monotonic()
        response = client.messages.create(
            model=modell,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            # `temperature` ist im aktuell installierten SDK-Stub nicht
            # typisiert, wird von der Messages-API aber weiterhin
            # akzeptiert — daher über extra_body statt Kwarg (FR-AGENT-3).
            extra_body={"temperature": temperature},
        )
        dauer_ms = int((time.monotonic() - start) * 1000)
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        return LLMAntwort(text=text, modell=modell, dauer_ms=dauer_ms)


class SchemaValidierungFehlgeschlagen(Exception):
    """Strukturierte Ausgabe hat auch nach erneutem Versuch das Schema
    verletzt (FR-AGENT-3) — der Aufrufer soll daraufhin eskalieren."""

    def __init__(self, grund: str, letzte_antwort: LLMAntwort | None):
        super().__init__(grund)
        self.letzte_antwort = letzte_antwort


def _extrahiere_json(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    ende = text.rfind("}")
    if start == -1 or ende == -1:
        return text
    return text[start : ende + 1]


def _default_client() -> LLMClient:
    if settings.anthropic_api_key:
        return AnthropicLLMClient()
    # Kein API-Key konfiguriert: Demo-Client statt Absturz, damit der
    # Prototyp auch ohne Zugangsdaten vorführbar ist (§0).
    from app.agent.demo_llm_client import DemoLLMClient

    return DemoLLMClient()


class ModelRouter:
    def __init__(self, client: LLMClient | None = None) -> None:
        self._client = client or _default_client()

    def modell_fuer(self, stufe: ModellStufe) -> str:
        if stufe == ModellStufe.guenstig:
            return settings.modell_guenstig
        return settings.modell_stark

    def complete_text(
        self, stufe: ModellStufe, system: str, prompt: str, temperature: float = 0.3
    ) -> LLMAntwort:
        modell = self.modell_fuer(stufe)
        return self._client.complete(modell, system, prompt, temperature)

    def complete_structured(
        self,
        stufe: ModellStufe,
        system: str,
        prompt: str,
        schema: type[T],
        max_versuche: int = 2,
    ) -> tuple[T, LLMAntwort]:
        letzter_fehler: Exception | None = None
        antwort: LLMAntwort | None = None
        for _ in range(max_versuche):
            antwort = self.complete_text(stufe, system, prompt, temperature=0.0)
            try:
                daten = json.loads(_extrahiere_json(antwort.text))
                return schema.model_validate(daten), antwort
            except (json.JSONDecodeError, ValidationError) as exc:
                letzter_fehler = exc
                continue
        raise SchemaValidierungFehlgeschlagen(str(letzter_fehler), antwort)
