"""Fakes für Tests — kein Netzwerkzugriff nötig (§0: externe Welt wird
simuliert). Liefern deterministische, szenario-gesteuerte Antworten."""

import hashlib
import json

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.agent.model_router import LLMAntwort
from app.agent.vector_store import DokumentenIndex


class FakeLLMClient:
    """Antwortet anhand von Stichworten im Prompt — reicht, um die im Test
    verwendeten Szenarien (Türschloss defekt, unklares Anliegen) sauber
    auseinanderzuhalten, ohne einen echten Modellaufruf zu benötigen."""

    def __init__(self) -> None:
        self.aufrufe: list[dict] = []
        self.modell_guenstig = "fake-guenstig"
        self.modell_stark = "fake-stark"

    def complete(self, modell: str, system: str, prompt: str, temperature: float) -> LLMAntwort:
        self.aufrufe.append(
            {"modell": modell, "system": system, "prompt": prompt, "temperature": temperature}
        )

        if "Zweck der Mail" in prompt:
            text = (
                "Sehr geehrte Damen und Herren,\n\n"
                "wir bitten Sie, bei der oben genannten Liegenschaft einen Termin zur "
                "Behebung des defekten Türschlosses zu vereinbaren.\n\n"
                "Freundliche Grüße\nIhre Hausverwaltung"
            )
            return LLMAntwort(text=text, modell=modell, dauer_ms=5)

        if "Türschloss" in prompt or "schloss" in prompt.lower():
            daten = {
                "typ": "reparaturmeldung",
                "gewerk": "schlosser",
                "objekt_suchbegriff": "Musterstraße 5",
                "melder_suchbegriff": "Erika Musterfrau",
                "konfidenz": 0.92,
                "begruendung": "Mail beschreibt eindeutig ein defektes Türschloss.",
            }
        else:
            daten = {
                "typ": "reparaturmeldung",
                "gewerk": None,
                "objekt_suchbegriff": None,
                "melder_suchbegriff": None,
                "konfidenz": 0.2,
                "begruendung": "Anliegen ist unklar, kein Gewerk erkennbar.",
            }

        return LLMAntwort(text=json.dumps(daten), modell=modell, dauer_ms=5)


class FakeEmbeddingFunction(EmbeddingFunction[Documents]):
    """Deterministisches Bag-of-Words-Hashing statt eines echten
    Embedding-Modells — kein Modell-Download, keine Netzwerkabhängigkeit.
    Für die in den Tests verwendeten, thematisch klar unterscheidbaren
    Dokumente reicht reiner Wortüberlapp, um plausible Nächste-Nachbarn-
    Ergebnisse zu liefern. L2-normalisiert, damit Chromas (euklidische)
    Distanzberechnung nicht von der Dokumentlänge dominiert wird, sondern
    den thematischen Überlapp widerspiegelt."""

    DIM = 64

    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:
        vektoren = []
        for text in input:
            vektor = [0.0] * self.DIM
            for wort in text.lower().split():
                index = int(hashlib.sha1(wort.encode()).hexdigest(), 16) % self.DIM
                vektor[index] += 1.0
            norm = sum(v * v for v in vektor) ** 0.5
            if norm > 0:
                vektor = [v / norm for v in vektor]
            vektoren.append(vektor)
        return vektoren

    @staticmethod
    def name() -> str:
        return "fake-hash-embedding"

    def get_config(self) -> dict:
        return {}

    @staticmethod
    def build_from_config(config: dict) -> "FakeEmbeddingFunction":
        return FakeEmbeddingFunction()


def fake_dokumenten_index() -> DokumentenIndex:
    """In-Memory-Chroma-Client (keine Persistenz) + Fake-Embedding — für
    Tests, die den Agent-Loop komplett durchlaufen."""
    return DokumentenIndex(client=chromadb.Client(), embedding_function=FakeEmbeddingFunction())
