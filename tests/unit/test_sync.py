"""
Unit tests for Offline/Online Sync
Epic 3.2: Testing & Quality Assurance
"""
import pytest
import asyncio
from datetime import datetime
from pathlib import Path

from src.offline.sync.sync_manager import (
    SyncRecord,
    OfflineSyncManager,
    SyncStatus
)


@pytest.mark.unit
class TestSyncRecord:
    """Test SyncRecord class"""

    def test_initialization(self):
        """Test sync record initialization"""
        timestamp = datetime.utcnow()
        record = SyncRecord(
            record_id="test_001",
            record_type="practice_answer",
            data={"answer": "x=5"},
            timestamp=timestamp
        )

        assert record.record_id == "test_001"
        assert record.record_type == "practice_answer"
        assert record.data == {"answer": "x=5"}
        assert record.timestamp == timestamp
        assert record.status == "pending"
        assert record.retry_count == 0

    def test_to_dict(self):
        """Test conversion to dictionary"""
        timestamp = datetime.utcnow()
        record = SyncRecord(
            record_id="test_001",
            record_type="quiz_score",
            data={"score": 85},
            timestamp=timestamp
        )

        result = record.to_dict()

        assert isinstance(result, dict)
        assert result["record_id"] == "test_001"
        assert result["record_type"] == "quiz_score"
        assert result["data"] == {"score": 85}
        assert result["status"] == "pending"

    def test_from_dict(self):
        """Test creation from dictionary"""
        data = {
            "record_id": "test_002",
            "record_type": "topic_progress",
            "data": {"progress": 75},
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending",
            "retry_count": 0,
            "last_retry": None
        }

        record = SyncRecord.from_dict(data)

        assert record.record_id == "test_002"
        assert record.record_type == "topic_progress"
        assert record.status == "pending"


@pytest.mark.unit
class TestOfflineSyncManager:
    """Test OfflineSyncManager"""

    def test_initialization(self, temp_dir):
        """Test sync manager initialization"""
        sync = OfflineSyncManager(
            sync_queue_path=str(temp_dir / "sync_queue"),
            sync_interval_seconds=60,
            max_retries=3,
            batch_size=50
        )

        assert sync.sync_interval == 60
        assert sync.max_retries == 3
        assert sync.batch_size == 50
        assert len(sync.sync_queue) == 0
        assert sync.is_online == False

    def test_add_to_queue(self, temp_dir):
        """Test adding records to sync queue"""
        sync = OfflineSyncManager(
            sync_queue_path=str(temp_dir / "sync_queue")
        )

        record_id = sync.add_to_queue(
            record_type="practice_answer",
            data={"student_id": "123", "answer": "correct"}
        )

        assert len(sync.sync_queue) == 1
        assert record_id is not None
        assert sync.sync_queue[0].record_id == record_id
        assert sync.sync_queue[0].status == "pending"

    def test_add_multiple_records(self, temp_dir, sample_sync_records):
        """Test adding multiple records"""
        sync = OfflineSyncManager(
            sync_queue_path=str(temp_dir / "sync_queue")
        )

        for record in sample_sync_records:
            sync.add_to_queue(
                record_type=record["record_type"],
                data=record["data"]
            )

        assert len(sync.sync_queue) == len(sample_sync_records)

    @pytest.mark.asyncio
    async def test_sync_when_offline(self, temp_dir):
        """Test sync skips when offline"""
        sync = OfflineSyncManager(
            sync_queue_path=str(temp_dir / "sync_queue")
        )
        sync.set_online_status(False)

        sync.add_to_queue("test", {"data": "test"})

        result = await sync.sync()

        assert result["status"] == "skipped"
        assert result["reason"] == "offline"
        assert result["pending_count"] == 1

    @pytest.mark.asyncio
    async def test_sync_when_online(self, temp_dir):
        """Test sync when online"""
        sync = OfflineSyncManager(
            sync_queue_path=str(temp_dir / "sync_queue")
        )

        # Add records
        sync.add_to_queue("test1", {"data": "test1"})
        sync.add_to_queue("test2", {"data": "test2"})

        # Go online and sync
        sync.set_online_status(True)
        result = await sync.sync()

        assert result["status"] == "completed"
        assert result["synced_count"] == 2
        assert result["failed_count"] == 0
        assert result["pending_count"] == 0

    def test_get_sync_status(self, temp_dir):
        """Test getting sync status"""
        sync = OfflineSyncManager(
            sync_queue_path=str(temp_dir / "sync_queue")
        )

        sync.add_to_queue("test", {"data": "test"})

        status = sync.get_sync_status()

        assert status["is_online"] == False
        assert status["total_pending"] == 1
        assert "status_breakdown" in status

    def test_queue_persistence(self, temp_dir):
        """Test sync queue persists to disk"""
        queue_path = temp_dir / "sync_queue"

        # Create manager and add records
        sync1 = OfflineSyncManager(sync_queue_path=str(queue_path))
        sync1.add_to_queue("test", {"data": "test"})

        # Create new manager with same path
        sync2 = OfflineSyncManager(sync_queue_path=str(queue_path))

        # Should load existing queue
        assert len(sync2.sync_queue) == 1

    def test_online_status_change(self, temp_dir):
        """Test online status change detection"""
        sync = OfflineSyncManager(
            sync_queue_path=str(temp_dir / "sync_queue")
        )

        assert sync.is_online == False

        sync.set_online_status(True)
        assert sync.is_online == True

        sync.set_online_status(False)
        assert sync.is_online == False

    @pytest.mark.asyncio
    async def test_max_retries(self, temp_dir):
        """Test max retries behavior"""
        sync = OfflineSyncManager(
            sync_queue_path=str(temp_dir / "sync_queue"),
            max_retries=2
        )

        # Add record
        record_id = sync.add_to_queue("test", {"data": "test"})

        # Simulate failed syncs
        sync.set_online_status(True)
        for i in range(3):  # More than max_retries
            await sync.sync()

        # Record should be marked as failed
        failed_records = [r for r in sync.sync_queue if r.status == "failed"]
        assert len(failed_records) > 0


@pytest.mark.unit
class TestSyncPerformance:
    """Performance tests for sync manager"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_batch_sync_performance(self, temp_dir, performance_timer):
        """Test batch sync performance"""
        sync = OfflineSyncManager(
            sync_queue_path=str(temp_dir / "sync_queue"),
            batch_size=100
        )

        # Add many records
        for i in range(100):
            sync.add_to_queue(f"test_{i}", {"id": i})

        sync.set_online_status(True)

        performance_timer.start()
        await sync.sync()
        performance_timer.stop()

        # Should complete in reasonable time
        assert performance_timer.elapsed_ms < 5000  # 5 seconds for 100 records

    @pytest.mark.asyncio
    async def test_background_sync_start_stop(self, temp_dir):
        """Test background sync can start and stop"""
        sync = OfflineSyncManager(
            sync_queue_path=str(temp_dir / "sync_queue"),
            sync_interval_seconds=1
        )

        # Start background sync
        await sync.start_background_sync()
        assert sync.sync_task is not None
        assert not sync.sync_task.done()

        # Wait a bit
        await asyncio.sleep(0.5)

        # Stop background sync
        await sync.stop_background_sync()
        assert sync.sync_task.done() or sync.sync_task.cancelled()


@pytest.mark.unit
def test_sync_record_types():
    """Test different sync record types"""
    record_types = [
        "practice_answer",
        "topic_progress",
        "quiz_score",
        "session_data",
        "settings"
    ]

    for record_type in record_types:
        record = SyncRecord(
            record_id=f"test_{record_type}",
            record_type=record_type,
            data={"test": "data"},
            timestamp=datetime.utcnow()
        )

        assert record.record_type == record_type
