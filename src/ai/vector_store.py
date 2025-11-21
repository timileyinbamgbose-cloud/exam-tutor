"""
Vector Store Service using FAISS
Manages document embeddings and similarity search
"""
from typing import List, Dict, Any, Optional, Tuple
import os
import json
import pickle
from pathlib import Path
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("⚠️  FAISS not available - vector search disabled")


class VectorStore:
    """
    FAISS-based vector store for semantic search
    """

    def __init__(
        self,
        dimension: int = 1536,
        index_type: str = "flat",
        storage_path: str = "data/vector_store"
    ):
        """
        Initialize vector store

        Args:
            dimension: Embedding dimension
            index_type: FAISS index type ('flat', 'ivf', 'hnsw')
            storage_path: Path to store index and metadata
        """
        self.dimension = dimension
        self.index_type = index_type
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # FAISS index
        self.index = None
        self.metadata = []  # Store document metadata
        self.document_count = 0

        if not FAISS_AVAILABLE:
            print("⚠️  FAISS not installed - vector store disabled")
            return

        # Create or load index
        self._initialize_index()

    def _initialize_index(self):
        """Initialize or load FAISS index"""
        index_path = self.storage_path / "faiss.index"
        metadata_path = self.storage_path / "metadata.pkl"

        # Try to load existing index
        if index_path.exists() and metadata_path.exists():
            try:
                self.index = faiss.read_index(str(index_path))
                with open(metadata_path, "rb") as f:
                    self.metadata = pickle.load(f)
                self.document_count = len(self.metadata)
                print(f"✅ Loaded vector store with {self.document_count} documents")
                return
            except Exception as e:
                print(f"⚠️  Failed to load index: {e}, creating new one")

        # Create new index
        if self.index_type == "flat":
            # Simple flat index (exact search)
            self.index = faiss.IndexFlatL2(self.dimension)
        elif self.index_type == "ivf":
            # IVF index (faster but approximate)
            quantizer = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
        elif self.index_type == "hnsw":
            # HNSW index (fast and accurate)
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)
        else:
            # Default to flat
            self.index = faiss.IndexFlatL2(self.dimension)

        print(f"✅ Created new {self.index_type} vector store")

    def add_documents(
        self,
        embeddings: List[List[float]],
        documents: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Add documents to vector store

        Args:
            embeddings: List of embedding vectors
            documents: List of document metadata dicts

        Returns:
            List of document IDs
        """
        if not FAISS_AVAILABLE or self.index is None:
            return []

        if len(embeddings) != len(documents):
            raise ValueError("Number of embeddings must match number of documents")

        # Convert to numpy array
        embeddings_np = np.array(embeddings, dtype=np.float32)

        # Normalize for cosine similarity (optional)
        faiss.normalize_L2(embeddings_np)

        # Add to index
        start_id = self.document_count
        self.index.add(embeddings_np)

        # Store metadata with IDs
        document_ids = []
        for i, doc in enumerate(documents):
            doc_id = start_id + i
            doc["id"] = doc_id
            self.metadata.append(doc)
            document_ids.append(doc_id)

        self.document_count += len(documents)

        print(f"✅ Added {len(documents)} documents (total: {self.document_count})")

        # Auto-save
        self.save()

        return document_ids

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_fn: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter_fn: Optional function to filter results

        Returns:
            List of documents with similarity scores
        """
        if not FAISS_AVAILABLE or self.index is None:
            return []

        if self.document_count == 0:
            return []

        # Convert to numpy array
        query_np = np.array([query_embedding], dtype=np.float32)

        # Normalize for cosine similarity
        faiss.normalize_L2(query_np)

        # Search
        distances, indices = self.index.search(query_np, min(top_k * 2, self.document_count))

        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue

            if idx >= len(self.metadata):
                continue

            doc = self.metadata[idx].copy()

            # Convert L2 distance to similarity score (0-1)
            # For normalized vectors: similarity = 1 - (distance^2 / 4)
            similarity = 1 - (dist / 4)
            similarity = max(0, min(1, similarity))  # Clamp to [0, 1]

            doc["similarity_score"] = float(similarity)
            doc["distance"] = float(dist)

            # Apply filter
            if filter_fn is None or filter_fn(doc):
                results.append(doc)

            if len(results) >= top_k:
                break

        return results

    def search_by_metadata(
        self,
        metadata_filter: Dict[str, Any],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search documents by metadata fields (exact match)

        Args:
            metadata_filter: Dict of field->value to match
            limit: Maximum results

        Returns:
            List of matching documents
        """
        results = []

        for doc in self.metadata:
            match = all(doc.get(key) == value for key, value in metadata_filter.items())
            if match:
                results.append(doc.copy())
                if len(results) >= limit:
                    break

        return results

    def delete_documents(self, document_ids: List[int]) -> int:
        """
        Delete documents by ID

        Note: FAISS doesn't support deletion, so we mark as deleted in metadata.
        For true deletion, need to rebuild index.

        Args:
            document_ids: List of document IDs to delete

        Returns:
            Number of documents deleted
        """
        deleted_count = 0

        for doc_id in document_ids:
            if doc_id < len(self.metadata):
                self.metadata[doc_id]["deleted"] = True
                deleted_count += 1

        if deleted_count > 0:
            self.save()

        return deleted_count

    def rebuild_index(self):
        """
        Rebuild index excluding deleted documents
        """
        if not FAISS_AVAILABLE:
            return

        # Get non-deleted documents
        active_docs = [(i, doc) for i, doc in enumerate(self.metadata) if not doc.get("deleted", False)]

        if not active_docs:
            self._initialize_index()
            self.metadata = []
            self.document_count = 0
            return

        # Extract embeddings (must be stored in metadata)
        embeddings = []
        new_metadata = []

        for _, doc in active_docs:
            if "embedding" in doc:
                embeddings.append(doc["embedding"])
                new_doc = doc.copy()
                del new_doc["embedding"]  # Don't duplicate storage
                new_metadata.append(new_doc)

        if not embeddings:
            print("⚠️  No embeddings found in metadata, cannot rebuild")
            return

        # Create new index
        self._initialize_index()
        self.metadata = []
        self.document_count = 0

        # Re-add documents
        self.add_documents(embeddings, new_metadata)

        print(f"✅ Rebuilt index with {len(new_metadata)} documents")

    def save(self):
        """Save index and metadata to disk"""
        if not FAISS_AVAILABLE or self.index is None:
            return

        try:
            index_path = self.storage_path / "faiss.index"
            metadata_path = self.storage_path / "metadata.pkl"

            faiss.write_index(self.index, str(index_path))

            with open(metadata_path, "wb") as f:
                pickle.dump(self.metadata, f)

        except Exception as e:
            print(f"❌ Failed to save vector store: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics

        Returns:
            Dict with stats
        """
        active_count = sum(1 for doc in self.metadata if not doc.get("deleted", False))

        return {
            "total_documents": self.document_count,
            "active_documents": active_count,
            "deleted_documents": self.document_count - active_count,
            "dimension": self.dimension,
            "index_type": self.index_type,
            "storage_path": str(self.storage_path),
            "faiss_available": FAISS_AVAILABLE
        }

    def clear(self):
        """Clear all documents and reset index"""
        self._initialize_index()
        self.metadata = []
        self.document_count = 0
        self.save()
        print("✅ Vector store cleared")


# Global instance (will be initialized by RAG service)
vector_store: Optional[VectorStore] = None


def get_vector_store(dimension: int = 1536, index_type: str = "flat") -> VectorStore:
    """
    Get or create global vector store instance

    Args:
        dimension: Embedding dimension
        index_type: FAISS index type

    Returns:
        VectorStore instance
    """
    global vector_store

    if vector_store is None:
        vector_store = VectorStore(dimension=dimension, index_type=index_type)

    return vector_store
