"""
Offline Vector Store for RAG (Retrieval-Augmented Generation)
Epic 3.1: Enable curriculum-grounded answers in offline mode

Supports:
- Qdrant (recommended): Fast, persistent, production-ready
- ChromaDB: Simple, embedded, good for development
- FAISS: Ultra-fast, in-memory, best for CPU inference

Target: <500ms semantic search on embedded curriculum
"""
from typing import List, Dict, Any, Optional, Literal
from pathlib import Path
from abc import ABC, abstractmethod
import json
from sentence_transformers import SentenceTransformer
from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)

VectorStoreType = Literal["qdrant", "chromadb", "faiss"]


class BaseVectorStore(ABC):
    """Abstract base class for vector stores"""

    def __init__(
        self,
        collection_name: str,
        embedding_model: str,
        persist_directory: str,
    ):
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Load embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        logger.info(f"✓ Embedding model loaded ({self.embedding_model.get_sentence_embedding_dimension()}D)")

    @abstractmethod
    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> None:
        """Add documents to vector store"""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        pass

    @abstractmethod
    def delete_collection(self) -> None:
        """Delete the collection"""
        pass

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        return self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
        ).tolist()


class QdrantVectorStore(BaseVectorStore):
    """Qdrant-based vector store for offline RAG"""

    def __init__(
        self,
        collection_name: str = "examstutor_curriculum",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        persist_directory: str = "./data/vector_db/qdrant/",
    ):
        super().__init__(collection_name, embedding_model, persist_directory)

        # Import Qdrant
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        # Initialize Qdrant client (local/embedded mode for offline)
        logger.info(f"Initializing Qdrant client at {persist_directory}")
        self.client = QdrantClient(path=str(self.persist_directory))

        # Create collection if it doesn't exist
        try:
            self.client.get_collection(collection_name)
            logger.info(f"✓ Collection '{collection_name}' already exists")
        except:
            logger.info(f"Creating collection '{collection_name}'")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_model.get_sentence_embedding_dimension(),
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"✓ Collection '{collection_name}' created")

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> None:
        """
        Add documents to Qdrant

        Documents format:
        [
            {
                "text": "content text",
                "metadata": {"subject": "Mathematics", "topic": "Algebra", ...}
            },
            ...
        ]
        """
        from qdrant_client.models import PointStruct
        import uuid

        logger.info(f"Adding {len(documents)} documents to Qdrant")

        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            # Extract texts and metadata
            texts = [doc["text"] for doc in batch]
            metadatas = [doc.get("metadata", {}) for doc in batch]

            # Generate embeddings
            embeddings = self.embed_texts(texts)

            # Create points
            points = []
            for j, (text, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas)):
                point = PointStruct(
                    id=str(uuid.uuid4()),  # Generate unique ID
                    vector=embedding,
                    payload={
                        "text": text,
                        **metadata,  # Include all metadata fields
                    },
                )
                points.append(point)

            # Upload to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            logger.info(f"✓ Batch {i//batch_size + 1} uploaded ({len(points)} documents)")

        logger.info(f"✓ All {len(documents)} documents added to Qdrant")

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Metadata filters (e.g., {"subject": "Mathematics"})

        Returns:
            List of matching documents with scores
        """
        import time
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        start_time = time.time()

        # Embed query
        query_embedding = self.embed_texts([query])[0]

        # Build filter if provided
        search_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )
            search_filter = Filter(must=conditions)

        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=top_k,
        )

        search_time = time.time() - start_time

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "text": result.payload["text"],
                "score": result.score,
                "metadata": {
                    k: v for k, v in result.payload.items() if k != "text"
                },
            })

        logger.info(
            f"✓ Search completed in {search_time*1000:.2f}ms "
            f"(target: <500ms), found {len(formatted_results)} results"
        )

        return formatted_results

    def delete_collection(self) -> None:
        """Delete the collection"""
        self.client.delete_collection(collection_name=self.collection_name)
        logger.info(f"✓ Collection '{self.collection_name}' deleted")


class FAISSVectorStore(BaseVectorStore):
    """FAISS-based vector store for ultra-fast CPU inference"""

    def __init__(
        self,
        collection_name: str = "examstutor_curriculum",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        persist_directory: str = "./data/vector_db/faiss/",
    ):
        super().__init__(collection_name, embedding_model, persist_directory)

        import faiss
        import numpy as np

        self.dimension = self.embedding_model.get_sentence_embedding_dimension()

        # Initialize FAISS index (using Inner Product for cosine similarity)
        logger.info(f"Initializing FAISS index (dimension: {self.dimension})")
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine sim

        # Storage for documents and metadata
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []

        # Load existing index if available
        index_path = self.persist_directory / f"{collection_name}.index"
        metadata_path = self.persist_directory / f"{collection_name}_metadata.json"

        if index_path.exists():
            logger.info(f"Loading existing FAISS index from {index_path}")
            self.index = faiss.read_index(str(index_path))

            with open(metadata_path, 'r') as f:
                data = json.load(f)
                self.documents = data["documents"]
                self.metadatas = data["metadatas"]

            logger.info(f"✓ Loaded {len(self.documents)} documents from existing index")

    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> None:
        """Add documents to FAISS index"""
        import numpy as np

        logger.info(f"Adding {len(documents)} documents to FAISS")

        # Extract texts and metadata
        texts = [doc["text"] for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]

        # Generate embeddings
        embeddings = np.array(self.embed_texts(texts), dtype=np.float32)

        # Normalize for cosine similarity (required for Inner Product)
        faiss.normalize_L2(embeddings)

        # Add to index
        self.index.add(embeddings)

        # Store documents and metadata
        self.documents.extend(texts)
        self.metadatas.extend(metadatas)

        logger.info(f"✓ Added {len(documents)} documents to FAISS index")

        # Persist
        self._persist()

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search FAISS index"""
        import time
        import numpy as np
        import faiss

        start_time = time.time()

        # Embed query
        query_embedding = np.array([self.embed_texts([query])[0]], dtype=np.float32)
        faiss.normalize_L2(query_embedding)

        # Search
        scores, indices = self.index.search(query_embedding, top_k)

        search_time = time.time() - start_time

        # Format results
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx == -1:  # No more results
                break

            # Apply filters if provided
            if filters:
                metadata = self.metadatas[idx]
                if not all(metadata.get(k) == v for k, v in filters.items()):
                    continue

            results.append({
                "text": self.documents[idx],
                "score": float(score),
                "metadata": self.metadatas[idx],
            })

        logger.info(
            f"✓ FAISS search completed in {search_time*1000:.2f}ms "
            f"(target: <500ms), found {len(results)} results"
        )

        return results

    def _persist(self) -> None:
        """Persist index and metadata to disk"""
        import faiss

        index_path = self.persist_directory / f"{self.collection_name}.index"
        metadata_path = self.persist_directory / f"{self.collection_name}_metadata.json"

        # Save index
        faiss.write_index(self.index, str(index_path))

        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump({
                "documents": self.documents,
                "metadatas": self.metadatas,
            }, f)

        logger.info(f"✓ FAISS index persisted to {index_path}")

    def delete_collection(self) -> None:
        """Delete FAISS index and metadata"""
        index_path = self.persist_directory / f"{self.collection_name}.index"
        metadata_path = self.persist_directory / f"{self.collection_name}_metadata.json"

        if index_path.exists():
            index_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()

        logger.info(f"✓ Collection '{self.collection_name}' deleted")


# Factory function
def create_vector_store(
    store_type: VectorStoreType = "qdrant",
    collection_name: str = "examstutor_curriculum",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    persist_directory: Optional[str] = None,
) -> BaseVectorStore:
    """
    Factory function to create vector store

    Args:
        store_type: Type of vector store ("qdrant", "chromadb", "faiss")
        collection_name: Name of the collection
        embedding_model: Sentence transformer model name
        persist_directory: Directory to persist data

    Returns:
        Vector store instance
    """
    if persist_directory is None:
        persist_directory = f"./data/vector_db/{store_type}/"

    stores = {
        "qdrant": QdrantVectorStore,
        "faiss": FAISSVectorStore,
        # "chromadb": ChromaDBVectorStore,  # TODO: Implement if needed
    }

    if store_type not in stores:
        raise ValueError(f"Unsupported store type: {store_type}")

    logger.info(f"Creating {store_type} vector store")

    return stores[store_type](
        collection_name=collection_name,
        embedding_model=embedding_model,
        persist_directory=persist_directory,
    )


# Example usage
if __name__ == "__main__":
    # Create vector store
    vector_store = create_vector_store(store_type="faiss")

    # Add sample curriculum documents
    sample_documents = [
        {
            "text": "Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce glucose and oxygen.",
            "metadata": {
                "subject": "Biology",
                "topic": "Plant Physiology",
                "subtopic": "Photosynthesis",
                "class": "SS2",
            }
        },
        {
            "text": "Newton's first law states that an object at rest stays at rest and an object in motion stays in motion unless acted upon by an external force.",
            "metadata": {
                "subject": "Physics",
                "topic": "Mechanics",
                "subtopic": "Newton's Laws",
                "class": "SS2",
            }
        },
        {
            "text": "A quadratic equation is an equation of the form ax² + bx + c = 0, where a ≠ 0.",
            "metadata": {
                "subject": "Mathematics",
                "topic": "Algebra",
                "subtopic": "Quadratic Equations",
                "class": "SS2",
            }
        },
    ]

    vector_store.add_documents(sample_documents)

    # Search
    results = vector_store.search(
        query="How do plants make food?",
        top_k=2,
        filters={"subject": "Biology"},
    )

    print(f"\nSearch results:")
    for i, result in enumerate(results):
        print(f"\n{i+1}. Score: {result['score']:.3f}")
        print(f"   Text: {result['text']}")
        print(f"   Metadata: {result['metadata']}")
