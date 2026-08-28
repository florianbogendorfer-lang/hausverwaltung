"""Vektorspeicher für die Dokumentensuche (§16 Phase 5, §12).

Bewusst als eigener Speicher getrennt von der relationalen DB (§6: „RAG/
Vektorspeicher: nur für semantische Dokumentensuche — getrennt von der
DB"). Chroma statt sqlite-vec, weil die App sowohl mit SQLite (lokal) als
auch Postgres (Clever-Cloud-Deploy) läuft — ein DB-gebundener Vektorindex
würde das an eine der beiden Engines fesseln.

Der Index ist abgeleitet: er wird bei jedem App-Start aus der Tabelle
`dokumente` neu aufgebaut (siehe app/main.py), die DB bleibt alleiniges
System of Record. Embedding-Funktion ist injizierbar (wie `ModelRouter`),
damit Tests ohne Modell-Download/Netzwerk laufen (§0).

SICHERHEITSHINWEIS (`pip-audit` findet für chromadb 1.5.9 vier offene
CVEs, alle noch ungepatcht): CVE-2026-45829 (CVSS 10.0, Pre-Auth-RCE)
und CVE-2026-45833 (Code-Injection) betreffen den *Python-basierten
Chroma-FastAPI-Server* (gestartet über `chroma run`, exponiert u. a.
`/api/v2/tenants/{tenant}/databases/{db}/collections` mit angreifbarem
`trust_remote_code`). CVE-2026-45830/-45831 betreffen ausschließlich
Chromas optionalen `SimpleRBACAuthorizationProvider` (Multi-Tenant-
Autorisierung für Server-Deployments). Betrifft NICHT diesen Code:
`chromadb.PersistentClient` (siehe `_default_client` unten) ist ein rein
lokaler, eingebetteter Client ohne eigenen Netzwerk-Listener und ohne
Auth-/RBAC-Provider — hier wird nirgends ein Chroma-Server gestartet,
keine Chroma-eigene HTTP-API exponiert und kein Autorisierungs-Provider
konfiguriert; der einzige nach außen erreichbare Server ist unsere
eigene FastAPI-App. **Diesen eingebetteten Modus nicht durch einen
netzwerkexponierten Chroma-Server (`chroma run` / `chromadb.HttpClient`)
oder eine RBAC-Konfiguration ersetzen, solange diese CVEs offen sind**
— sonst greifen die Lücken.
"""

import chromadb
from chromadb.api.types import EmbeddingFunction

from app.config import settings
from app.models import Dokument

COLLECTION_NAME = "dokumente"


def _default_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


class DokumentenIndex:
    def __init__(
        self,
        client: chromadb.ClientAPI | None = None,
        embedding_function: EmbeddingFunction | None = None,
    ) -> None:
        self._client = client or _default_client()
        kwargs = {"embedding_function": embedding_function} if embedding_function else {}
        self._collection = self._client.get_or_create_collection(COLLECTION_NAME, **kwargs)

    def indizieren(self, dokumente: list[Dokument]) -> None:
        """Upsert aller Dokument-Zeilen — idempotent, sicher bei jedem
        App-Start erneut aufrufbar."""
        if not dokumente:
            return
        self._collection.upsert(
            ids=[str(d.id) for d in dokumente],
            documents=[d.inhalt for d in dokumente],
            metadatas=[{"titel": d.titel, "quelle": d.quelle} for d in dokumente],
        )

    def suchen(self, frage: str, top_k: int = 2) -> list[int]:
        """Semantische Suche — liefert Dokument-IDs nach Relevanz sortiert."""
        if self._collection.count() == 0:
            return []
        ergebnis = self._collection.query(
            query_texts=[frage], n_results=min(top_k, self._collection.count())
        )
        treffer_ids = ergebnis["ids"][0] if ergebnis["ids"] else []
        return [int(i) for i in treffer_ids]
