"""
memory/chroma_store.py
───────────────────────
ChromaDB vector store for agent long-term memory.

Interview explanation:
  "ChromaDB stores embeddings of past agent runs and conversations.
   When Jarvis gets a command, it first searches memory for similar
   past interactions — this gives context like 'last time you asked
   about costs, we found 4 idle instances'. It makes Jarvis smarter
   over time without retraining."
"""

import structlog
from config.settings import get_settings

logger = structlog.get_logger(__name__)


class ChromaStore:

    def __init__(self):
        self.settings  = get_settings()
        self._client   = None
        self._collection = None

    def _get_client(self):
        if not self._client:
            import chromadb
            self._client = chromadb.HttpClient(
                host=self.settings.chroma_host,
                port=self.settings.chroma_port,
            )
        return self._client

    def _get_collection(self):
        if not self._collection:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name="jarvis_memory",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def store_interaction(
        self,
        interaction_id: str,
        text: str,
        metadata: dict | None = None,
    ) -> None:
        """Store a voice interaction in vector memory."""
        try:
            collection = self._get_collection()
            collection.upsert(
                ids=[interaction_id],
                documents=[text],
                metadatas=[metadata or {}],
            )
            logger.info("chroma.stored", id=interaction_id)
        except Exception as e:
            logger.warning("chroma.store_failed", error=str(e))

    async def search_similar(
        self,
        query: str,
        n_results: int = 3,
    ) -> list:
        """Search for similar past interactions."""
        try:
            collection = self._get_collection()
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
            )
            docs = results.get("documents", [[]])[0]
            logger.info("chroma.searched", query=query[:50], results=len(docs))
            return docs
        except Exception as e:
            logger.warning("chroma.search_failed", error=str(e))
            return []

    async def get_agent_memory(self, agent_id: str) -> list:
        """Get all stored memories for a specific agent."""
        try:
            collection = self._get_collection()
            results = collection.get(
                where={"agent_id": agent_id},
            )
            return results.get("documents", [])
        except Exception as e:
            logger.warning("chroma.get_failed", error=str(e))
            return []
