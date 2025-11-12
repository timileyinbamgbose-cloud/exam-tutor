"""
Unit tests for Offline RAG modules
Epic 3.2: Testing & Quality Assurance
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.offline.rag.vector_store import (
    BaseVectorStore,
    FAISSVectorStore,
    QdrantVectorStore,
    create_vector_store,
)
from src.offline.rag.rag_pipeline import OfflineRAGPipeline


@pytest.mark.unit
class TestVectorStoreFactory:
    """Test vector store factory"""

    def test_create_faiss_store(self, temp_dir):
        """Test FAISS vector store creation"""
        store = create_vector_store(
            store_type="faiss",
            collection_name="test_collection",
            persist_directory=str(temp_dir)
        )

        assert isinstance(store, FAISSVectorStore)
        assert store.collection_name == "test_collection"

    def test_create_qdrant_store(self, temp_dir):
        """Test Qdrant vector store creation"""
        store = create_vector_store(
            store_type="qdrant",
            collection_name="test_collection",
            persist_directory=str(temp_dir)
        )

        assert isinstance(store, QdrantVectorStore)

    def test_unsupported_store_type_raises_error(self):
        """Test unsupported store type raises error"""
        with pytest.raises(ValueError, match="Unsupported store type"):
            create_vector_store(store_type="unsupported")


@pytest.mark.unit
class TestFAISSVectorStore:
    """Test FAISS vector store"""

    def test_initialization(self, temp_dir):
        """Test FAISS initialization"""
        store = FAISSVectorStore(
            collection_name="test",
            persist_directory=str(temp_dir)
        )

        assert store.collection_name == "test"
        assert store.dimension > 0
        assert len(store.documents) == 0
        assert len(store.metadatas) == 0

    def test_add_documents(self, temp_dir, sample_curriculum_documents):
        """Test adding documents to FAISS"""
        store = FAISSVectorStore(persist_directory=str(temp_dir))

        store.add_documents(sample_curriculum_documents)

        assert len(store.documents) == len(sample_curriculum_documents)
        assert len(store.metadatas) == len(sample_curriculum_documents)

    def test_search_returns_results(self, test_vector_store):
        """Test search returns relevant results"""
        results = test_vector_store.search(
            query="How do plants make food?",
            top_k=2
        )

        assert len(results) > 0
        assert len(results) <= 2
        assert all("text" in r for r in results)
        assert all("score" in r for r in results)
        assert all("metadata" in r for r in results)

    def test_search_with_filters(self, test_vector_store):
        """Test search with metadata filters"""
        results = test_vector_store.search(
            query="physics",
            top_k=5,
            filters={"subject": "Physics"}
        )

        # Should only return Physics documents
        for result in results:
            assert result["metadata"]["subject"] == "Physics"

    @pytest.mark.performance
    def test_search_performance(self, test_vector_store, performance_timer):
        """Test search meets performance target (<500ms)"""
        performance_timer.start()

        test_vector_store.search(query="What is the quadratic formula?", top_k=5)

        performance_timer.stop()

        # Should be < 500ms (target from Epic 3.1)
        assert performance_timer.elapsed_ms < 500, \
            f"Search took {performance_timer.elapsed_ms}ms, target is <500ms"

    def test_persistence(self, temp_dir, sample_curriculum_documents):
        """Test vector store persistence"""
        # Create and populate store
        store1 = FAISSVectorStore(
            collection_name="persist_test",
            persist_directory=str(temp_dir)
        )
        store1.add_documents(sample_curriculum_documents)

        # Load new instance from same directory
        store2 = FAISSVectorStore(
            collection_name="persist_test",
            persist_directory=str(temp_dir)
        )

        # Should have loaded existing data
        assert len(store2.documents) == len(sample_curriculum_documents)


@pytest.mark.unit
class TestOfflineRAGPipeline:
    """Test Offline RAG Pipeline"""

    def test_initialization(self):
        """Test RAG pipeline initialization"""
        rag = OfflineRAGPipeline(
            vector_store_type="faiss",
            top_k=3
        )

        assert rag.vector_store_type == "faiss"
        assert rag.top_k == 3
        assert rag.vector_store is not None

    def test_retrieve_context(self, test_vector_store):
        """Test context retrieval"""
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.vector_store = test_vector_store

        results = rag.retrieve(
            query="What is photosynthesis?",
            top_k=2
        )

        assert len(results) > 0
        assert len(results) <= 2

    def test_build_prompt(self):
        """Test prompt building with context"""
        rag = OfflineRAGPipeline(vector_store_type="faiss")

        context_docs = [
            {
                "text": "Photosynthesis is a process...",
                "metadata": {"subject": "Biology", "topic": "Plant Physiology"}
            }
        ]

        prompt = rag.build_prompt(
            question="What is photosynthesis?",
            context_docs=context_docs,
            subject="Biology"
        )

        assert "photosynthesis" in prompt.lower()
        assert "Biology" in prompt
        assert "Context 1" in prompt
        assert "Answer:" in prompt

    def test_answer_question_without_model(self, test_vector_store):
        """Test question answering without model (retrieval only)"""
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.vector_store = test_vector_store

        result = rag.answer_question(
            question="What is Newton's first law?",
            subject="Physics",
            top_k=2
        )

        assert "question" in result
        assert "context_documents" in result
        assert "num_sources" in result
        assert "retrieval_time_ms" in result
        assert result["num_sources"] > 0
        assert result["retrieval_time_ms"] < 500  # Performance target

    def test_add_curriculum_content(self, temp_dir, sample_curriculum_documents):
        """Test adding curriculum content"""
        rag = OfflineRAGPipeline(
            vector_store_type="faiss",
            collection_name="curriculum_test"
        )

        # Should not raise exception
        rag.add_curriculum_content(sample_curriculum_documents)

    def test_subject_filtering(self, test_vector_store):
        """Test subject-specific filtering"""
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.vector_store = test_vector_store

        # Search with subject filter
        result = rag.answer_question(
            question="mathematical concepts",
            subject="Mathematics",
            top_k=5
        )

        # All returned documents should be Mathematics
        for doc in result["context_documents"]:
            assert doc["metadata"]["subject"] == "Mathematics"


@pytest.mark.unit
class TestRAGPerformance:
    """Performance tests for RAG pipeline"""

    @pytest.mark.performance
    def test_retrieval_latency(self, test_vector_store, performance_timer):
        """Test retrieval latency meets target"""
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.vector_store = test_vector_store

        latencies = []

        # Test multiple queries
        queries = [
            "What is photosynthesis?",
            "Explain Newton's law",
            "How to solve quadratic equations?",
        ]

        for query in queries:
            performance_timer.start()
            rag.retrieve(query, top_k=5)
            performance_timer.stop()

            latencies.append(performance_timer.elapsed_ms)

        avg_latency = sum(latencies) / len(latencies)

        assert avg_latency < 500, \
            f"Average retrieval latency {avg_latency}ms exceeds 500ms target"

    @pytest.mark.performance
    def test_batch_document_addition(self, temp_dir, performance_timer):
        """Test batch document addition performance"""
        store = FAISSVectorStore(persist_directory=str(temp_dir))

        # Generate large batch of documents
        documents = [
            {
                "text": f"Test document number {i} with some content",
                "metadata": {"id": i}
            }
            for i in range(100)
        ]

        performance_timer.start()
        store.add_documents(documents, batch_size=50)
        performance_timer.stop()

        # Should complete reasonably quickly
        assert performance_timer.elapsed_ms < 10000  # 10 seconds for 100 docs


@pytest.mark.unit
def test_embedding_model_loaded():
    """Test embedding model is properly loaded"""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    # Should have correct dimension
    assert model.get_sentence_embedding_dimension() == 384

    # Should be able to encode
    embeddings = model.encode(["test sentence"])
    assert len(embeddings[0]) == 384
