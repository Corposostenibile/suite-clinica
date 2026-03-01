"""
Qdrant vector database wrapper for SOP document embeddings.
"""
import os
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "sop_documents")
VECTOR_SIZE = 384  # BAAI/bge-small-en-v1.5


class QdrantService:
    _client = None

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            url = os.getenv("QDRANT_URL", "http://localhost:6333")
            cls._client = QdrantClient(url=url)
            logger.info("Qdrant client connected to %s", url)
        return cls._client

    @classmethod
    def init_collection(cls):
        """Create the SOP collection if it doesn't exist."""
        client = cls._get_client()
        collections = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME not in collections:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection '%s'", COLLECTION_NAME)
        else:
            logger.info("Qdrant collection '%s' already exists", COLLECTION_NAME)

    @classmethod
    def upsert_chunks(cls, doc_id, chunks, embeddings, filename):
        """Insert document chunks with their embeddings into Qdrant."""
        client = cls._get_client()
        points = [
            PointStruct(
                id=doc_id * 100_000 + i,
                vector=embedding,
                payload={
                    "doc_id": doc_id,
                    "text": chunk,
                    "chunk_index": i,
                    "filename": filename,
                },
            )
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]
        # Batch upsert in groups of 100
        batch_size = 100
        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            client.upsert(collection_name=COLLECTION_NAME, points=batch)
        logger.info("Upserted %d chunks for doc_id=%d", len(points), doc_id)

    @classmethod
    def search(cls, query_embedding, top_k=5):
        """Search for similar chunks. Returns list of dicts with text, filename, score."""
        client = cls._get_client()
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=top_k,
        )
        return [
            {
                "text": point.payload["text"],
                "filename": point.payload["filename"],
                "doc_id": point.payload["doc_id"],
                "chunk_index": point.payload["chunk_index"],
                "score": point.score,
            }
            for point in results.points
        ]

    @classmethod
    def delete_by_doc_id(cls, doc_id):
        """Remove all vectors belonging to a document."""
        client = cls._get_client()
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id),
                    )
                ]
            ),
        )
        logger.info("Deleted vectors for doc_id=%d", doc_id)

    @classmethod
    def get_total_chunks(cls):
        """Return total number of vectors in the collection."""
        try:
            client = cls._get_client()
            info = client.get_collection(COLLECTION_NAME)
            return info.points_count
        except Exception:
            return 0
