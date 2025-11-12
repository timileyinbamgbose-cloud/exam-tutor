"""
Performance and Load Testing
Epic 3.2: Testing & Quality Assurance

Target: 1000+ concurrent users
"""
import pytest
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.offline.rag.rag_pipeline import OfflineRAGPipeline


@pytest.mark.performance
class TestRAGPerformance:
    """Performance tests for RAG system"""

    def test_single_query_latency(self, test_vector_store):
        """Test single query latency"""
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.vector_store = test_vector_store

        latencies = []

        # Run 100 queries
        for i in range(100):
            start = time.time()
            rag.answer_question("test question", top_k=5)
            latency = (time.time() - start) * 1000
            latencies.append(latency)

        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

        print(f"\nRAG Latency Statistics:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  P99: {p99_latency:.2f}ms")

        # Targets
        assert avg_latency < 500, f"Average latency {avg_latency}ms > 500ms target"
        assert p95_latency < 1000, f"P95 latency {p95_latency}ms > 1000ms target"

    def test_throughput(self, test_vector_store):
        """Test system throughput (queries per second)"""
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.vector_store = test_vector_store

        num_queries = 100
        start_time = time.time()

        for i in range(num_queries):
            rag.answer_question(f"test question {i}", top_k=3)

        elapsed_time = time.time() - start_time
        qps = num_queries / elapsed_time

        print(f"\nThroughput: {qps:.2f} queries/second")

        # Should handle at least 10 queries per second
        assert qps >= 10, f"Throughput {qps} QPS < 10 QPS minimum"

    @pytest.mark.slow
    def test_concurrent_load(self, test_vector_store):
        """Test system under concurrent load"""
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.vector_store = test_vector_store

        num_workers = 50  # Concurrent users
        queries_per_worker = 10

        def worker_task(worker_id):
            results = []
            for i in range(queries_per_worker):
                start = time.time()
                result = rag.answer_question(
                    f"Question {worker_id}-{i}",
                    top_k=3
                )
                latency = (time.time() - start) * 1000
                results.append({
                    "success": result["num_sources"] > 0,
                    "latency_ms": latency
                })
            return results

        # Execute concurrent load
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(worker_task, i)
                for i in range(num_workers)
            ]

            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())

        elapsed_time = time.time() - start_time
        total_queries = num_workers * queries_per_worker

        # Calculate metrics
        success_count = sum(1 for r in all_results if r["success"])
        success_rate = (success_count / total_queries) * 100
        avg_latency = sum(r["latency_ms"] for r in all_results) / len(all_results)
        qps = total_queries / elapsed_time

        print(f"\nConcurrent Load Test Results:")
        print(f"  Workers: {num_workers}")
        print(f"  Total Queries: {total_queries}")
        print(f"  Success Rate: {success_rate:.2f}%")
        print(f"  Average Latency: {avg_latency:.2f}ms")
        print(f"  Throughput: {qps:.2f} QPS")

        # Targets
        assert success_rate >= 99, f"Success rate {success_rate}% < 99%"
        assert avg_latency < 2000, f"Avg latency under load {avg_latency}ms > 2s"


@pytest.mark.performance
class TestMemoryUsage:
    """Test memory usage under load"""

    def test_memory_growth(self, test_vector_store):
        """Test memory doesn't grow unbounded"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.vector_store = test_vector_store

        # Run many queries
        for i in range(1000):
            rag.answer_question(f"test {i}", top_k=5)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        print(f"\nMemory Usage:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Growth: {memory_growth:.2f} MB")

        # Memory growth should be reasonable
        assert memory_growth < 500, f"Memory grew by {memory_growth}MB"


@pytest.mark.performance
@pytest.mark.slow
class TestStressTest:
    """Stress testing"""

    def test_sustained_load(self, test_vector_store):
        """Test system under sustained load"""
        rag = OfflineRAGPipeline(vector_store_type="faiss")
        rag.vector_store = test_vector_store

        duration_seconds = 60  # 1 minute
        target_qps = 10

        start_time = time.time()
        query_count = 0
        errors = 0

        while time.time() - start_time < duration_seconds:
            try:
                result = rag.answer_question("test query", top_k=3)
                if result["num_sources"] == 0:
                    errors += 1
                query_count += 1

                # Control query rate
                time.sleep(1 / target_qps)

            except Exception as e:
                errors += 1

        elapsed_time = time.time() - start_time
        actual_qps = query_count / elapsed_time
        error_rate = (errors / query_count) * 100 if query_count > 0 else 100

        print(f"\nSustained Load Test ({duration_seconds}s):")
        print(f"  Total Queries: {query_count}")
        print(f"  Actual QPS: {actual_qps:.2f}")
        print(f"  Error Rate: {error_rate:.2f}%")

        assert error_rate < 1, f"Error rate {error_rate}% > 1%"


@pytest.mark.performance
class TestScalabilityTest:
    """Test system scalability"""

    def test_document_scaling(self, temp_dir):
        """Test performance with increasing document count"""
        from src.offline.rag.vector_store import create_vector_store

        document_counts = [100, 500, 1000]
        results = []

        for count in document_counts:
            # Create vector store
            store = create_vector_store(
                store_type="faiss",
                persist_directory=str(temp_dir / f"scale_{count}")
            )

            # Add documents
            docs = [
                {
                    "text": f"Test document number {i} with some content",
                    "metadata": {"id": i}
                }
                for i in range(count)
            ]

            add_start = time.time()
            store.add_documents(docs)
            add_time = time.time() - add_start

            # Test search
            search_times = []
            for _ in range(10):
                search_start = time.time()
                store.search("test query", top_k=5)
                search_times.append((time.time() - search_start) * 1000)

            avg_search_time = sum(search_times) / len(search_times)

            results.append({
                "doc_count": count,
                "add_time_s": add_time,
                "avg_search_ms": avg_search_time
            })

        print(f"\nScalability Test Results:")
        for result in results:
            print(f"  {result['doc_count']} docs: "
                  f"add={result['add_time_s']:.2f}s, "
                  f"search={result['avg_search_ms']:.2f}ms")

        # Search time shouldn't grow too much
        assert results[-1]["avg_search_ms"] < 1000  # < 1s even with 1000 docs
