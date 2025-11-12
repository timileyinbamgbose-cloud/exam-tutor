"""
Integration tests for complete ExamsTutor workflows
Epic 3.2: Testing & Quality Assurance
"""
import pytest
import asyncio
from pathlib import Path

from src.offline.rag.rag_pipeline import OfflineRAGPipeline
from src.offline.sync.sync_manager import OfflineSyncManager
from src.offline.detection.network_detector import OfflineCapabilityManager


@pytest.mark.integration
class TestStudentOfflineWorkflow:
    """Test complete student workflow in offline mode"""

    @pytest.mark.asyncio
    async def test_offline_study_session(self, temp_dir, sample_curriculum_documents):
        """Test complete offline study session workflow"""
        # 1. Initialize RAG for offline Q&A
        rag = OfflineRAGPipeline(
            vector_store_type="faiss",
            collection_name="test_workflow"
        )
        rag.add_curriculum_content(sample_curriculum_documents)

        # 2. Initialize sync manager
        sync = OfflineSyncManager(
            sync_queue_path=str(temp_dir / "sync")
        )
        sync.set_online_status(False)  # Offline mode

        # 3. Student asks questions (offline)
        questions = [
            "What is photosynthesis?",
            "Explain Newton's first law",
            "How to solve quadratic equations?"
        ]

        for question in questions:
            result = rag.answer_question(
                question=question,
                top_k=3
            )

            # Verify retrieval worked
            assert result["num_sources"] > 0
            assert result["retrieval_time_ms"] < 500

            # Queue answer for sync
            sync.add_to_queue(
                record_type="practice_answer",
                data={
                    "question": question,
                    "sources_used": result["num_sources"]
                }
            )

        # 4. Verify sync queue
        status = sync.get_sync_status()
        assert status["total_pending"] == len(questions)

        # 5. Go online and sync
        sync.set_online_status(True)
        sync_result = await sync.sync()

        assert sync_result["synced_count"] == len(questions)
        assert sync_result["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_offline_to_online_transition(self, temp_dir, sample_curriculum_documents):
        """Test smooth transition from offline to online"""
        # Start in offline mode
        capability_manager = OfflineCapabilityManager()
        capability_manager.network_detector.is_online = False

        # Verify offline capabilities
        caps = capability_manager.get_capabilities()
        assert caps["mode"] == "offline"
        assert caps["available_features"]["ask_questions"] == True

        # Initialize RAG
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.add_curriculum_content(sample_curriculum_documents)

        # Use offline features
        result = rag.answer_question("What is photosynthesis?")
        assert result["num_sources"] > 0

        # Simulate going online
        capability_manager.network_detector.is_online = True
        capability_manager.offline_mode_active = False

        # Verify online capabilities
        caps = capability_manager.get_capabilities()
        assert caps["mode"] == "online"
        assert caps["available_features"]["teacher_features"] == True


@pytest.mark.integration
class TestRAGWithSync:
    """Test RAG pipeline integrated with sync"""

    @pytest.mark.asyncio
    async def test_rag_answers_are_synced(self, temp_dir, sample_curriculum_documents):
        """Test that RAG answers are properly queued for sync"""
        # Setup
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.add_curriculum_content(sample_curriculum_documents)

        sync = OfflineSyncManager(sync_queue_path=str(temp_dir / "sync"))

        # Ask question
        result = rag.answer_question("What is Newton's law?", subject="Physics")

        # Queue answer with metadata
        sync.add_to_queue(
            record_type="rag_answer",
            data={
                "question": result["question"],
                "num_sources": result["num_sources"],
                "retrieval_time_ms": result["retrieval_time_ms"],
                "filters": result["filters_applied"]
            }
        )

        # Verify queued
        assert len(sync.sync_queue) == 1
        queued_data = sync.sync_queue[0].data
        assert queued_data["num_sources"] > 0
        assert "retrieval_time_ms" in queued_data


@pytest.mark.integration
class TestMultipleComponents:
    """Test multiple components working together"""

    @pytest.mark.asyncio
    async def test_full_system_integration(self, temp_dir, sample_curriculum_documents, sample_sync_records):
        """Test full system with all components"""
        # 1. Network detection
        capability_manager = OfflineCapabilityManager()

        # 2. RAG system
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.add_curriculum_content(sample_curriculum_documents)

        # 3. Sync manager
        sync = OfflineSyncManager(sync_queue_path=str(temp_dir / "sync"))

        # Scenario: Student uses system offline
        capability_manager.network_detector.is_online = False
        sync.set_online_status(False)

        # Check we're in offline mode
        assert capability_manager.is_offline_mode() == True

        # Student asks questions
        q1_result = rag.answer_question("What is photosynthesis?")
        sync.add_to_queue("answer", {"question": "photosynthesis"})

        q2_result = rag.answer_question("Explain Newton's law")
        sync.add_to_queue("answer", {"question": "newton"})

        # Verify offline operations worked
        assert q1_result["num_sources"] > 0
        assert q2_result["num_sources"] > 0
        assert len(sync.sync_queue) == 2

        # Connection restored
        capability_manager.network_detector.is_online = True
        sync.set_online_status(True)

        # Sync happens
        sync_result = await sync.sync()
        assert sync_result["synced_count"] == 2


@pytest.mark.integration
class TestEndToEndPerformance:
    """End-to-end performance tests"""

    @pytest.mark.performance
    def test_complete_question_answer_cycle(self, test_vector_store, performance_timer):
        """Test complete Q&A cycle performance"""
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.vector_store = test_vector_store

        performance_timer.start()

        # Complete cycle: retrieve + build prompt
        result = rag.answer_question(
            question="What is the quadratic formula?",
            subject="Mathematics",
            top_k=3
        )

        performance_timer.stop()

        # Total time should be reasonable
        assert performance_timer.elapsed_ms < 1000  # 1 second
        assert result["retrieval_time_ms"] < 500  # Retrieval < 500ms

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_operations(self, temp_dir, sample_curriculum_documents):
        """Test system under concurrent load"""
        # Setup
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.add_curriculum_content(sample_curriculum_documents)

        # Run multiple queries concurrently
        questions = [
            "What is photosynthesis?",
            "Explain Newton's law",
            "Quadratic formula?",
            "What is momentum?",
        ]

        async def ask_question(question):
            return rag.answer_question(question, top_k=2)

        # Execute concurrently
        results = await asyncio.gather(*[ask_question(q) for q in questions])

        # All should succeed
        assert len(results) == len(questions)
        for result in results:
            assert result["num_sources"] > 0
            assert result["retrieval_time_ms"] < 1000


@pytest.mark.integration
def test_data_flow_integrity(temp_dir, sample_curriculum_documents):
    """Test data integrity through the pipeline"""
    # Add documents to RAG
    rag = OfflineRAGPipeline(vector_store_type="faiss")
    rag.add_curriculum_content(sample_curriculum_documents)

    # Retrieve and verify metadata is preserved
    result = rag.answer_question("photosynthesis", top_k=1)

    retrieved_doc = result["context_documents"][0]

    # Find original document
    original_doc = next(
        (doc for doc in sample_curriculum_documents
         if "photosynthesis" in doc["text"].lower()),
        None
    )

    assert original_doc is not None

    # Verify metadata preserved
    assert retrieved_doc["metadata"]["subject"] == original_doc["metadata"]["subject"]
    assert retrieved_doc["metadata"]["topic"] == original_doc["metadata"]["topic"]
