import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import Optional
from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    def __init__(self):
        self._client: Optional[chromadb.Client] = None
        self._collection = None

    def _get_client(self) -> chromadb.Client:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    def _get_collection(self, collection_name: Optional[str] = None):
        name = collection_name or settings.chroma_collection_name
        if self._collection is None or self._collection.name != name:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection
    def upsert_document(self, doc_id: str, text: str, metadata: Optional[dict] = None, collection_name: Optional[str] = None) -> None:
        collection = self._get_collection(collection_name)
        collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
        )
        logger.debug(f"Upserted document id={doc_id}")

    def query_similar(self, query_text: str, n_results: int = 10, collection_name: Optional[str] = None) -> list[dict]:
        collection = self._get_collection(collection_name)
        count = collection.count()
        if count == 0:
            return []
        n_results = min(n_results, count)
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for i, doc_id in enumerate(results["ids"][0]):
            output.append({
                "id": doc_id,
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
                "similarity": 1.0 - results["distances"][0][i],
            })
        return output

    def compute_similarity(self, text1: str, text2: str) -> float:
        try:
            temp_name = f"temp_sim_{abs(hash(text1[:50] + text2[:50])) % 1000000}"
            collection = self._get_client().get_or_create_collection(
                name=temp_name,
                metadata={"hnsw:space": "cosine"},
            )
            collection.upsert(ids=["doc1"], documents=[text1])
            results = collection.query(query_texts=[text2], n_results=1, include=["distances"])
            distance = results["distances"][0][0]
            self._get_client().delete_collection(temp_name)
            return float(1.0 - distance)
        except Exception as e:
            logger.warning(f"Similarity computation failed: {e}")
            return 0.0

    def delete_collection(self, collection_name: str) -> None:
        try:
            self._get_client().delete_collection(collection_name)
        except Exception as e:
            logger.warning(f"Could not delete collection {collection_name}: {e}")

    def is_available(self) -> bool:
        try:
            self._get_client().heartbeat()
            return True
        except Exception:
            return False


embedding_service = EmbeddingService()
