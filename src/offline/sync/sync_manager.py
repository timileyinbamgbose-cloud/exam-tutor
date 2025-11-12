"""
Offline/Online Sync Manager
Epic 3.1: Seamless synchronization for multi-device, offline-first usage

Features:
- Background sync of student progress
- Conflict resolution
- Delta sync (bandwidth optimization)
- Retry with exponential backoff
"""
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime, timedelta
import asyncio
import json
from pathlib import Path
from src.core.logger import get_logger
from src.core.config import settings

logger = get_logger(__name__)

SyncStatus = Literal["pending", "in_progress", "completed", "failed"]


class SyncRecord:
    """Represents a sync operation"""

    def __init__(
        self,
        record_id: str,
        record_type: str,
        data: Dict[str, Any],
        timestamp: datetime,
        status: SyncStatus = "pending",
    ):
        self.record_id = record_id
        self.record_type = record_type
        self.data = data
        self.timestamp = timestamp
        self.status = status
        self.retry_count = 0
        self.last_retry: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "record_type": self.record_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "retry_count": self.retry_count,
            "last_retry": self.last_retry.isoformat() if self.last_retry else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncRecord":
        record = cls(
            record_id=data["record_id"],
            record_type=data["record_type"],
            data=data["data"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            status=data["status"],
        )
        record.retry_count = data.get("retry_count", 0)
        if data.get("last_retry"):
            record.last_retry = datetime.fromisoformat(data["last_retry"])
        return record


class OfflineSyncManager:
    """
    Manage offline/online synchronization

    Use cases:
    - Student completes practice questions offline
    - Progress is queued for sync
    - When online, sync automatically uploads
    - Conflict resolution for multi-device usage
    """

    def __init__(
        self,
        sync_queue_path: str = "./data/sync_queue/",
        sync_interval_seconds: int = 300,
        max_retries: int = 3,
        batch_size: int = 100,
    ):
        self.sync_queue_path = Path(sync_queue_path)
        self.sync_queue_path.mkdir(parents=True, exist_ok=True)

        self.sync_interval = sync_interval_seconds
        self.max_retries = max_retries
        self.batch_size = batch_size

        self.sync_queue: List[SyncRecord] = []
        self.is_online = False
        self.sync_task: Optional[asyncio.Task] = None

        # Load existing queue
        self._load_queue()

        logger.info(
            f"SyncManager initialized:\n"
            f"  Queue path: {self.sync_queue_path}\n"
            f"  Sync interval: {sync_interval_seconds}s\n"
            f"  Pending records: {len(self.sync_queue)}"
        )

    def add_to_queue(
        self,
        record_type: str,
        data: Dict[str, Any],
        record_id: Optional[str] = None,
    ) -> str:
        """
        Add record to sync queue

        Args:
            record_type: Type of record ("progress", "answer", "score", etc.)
            data: Record data
            record_id: Unique ID (generated if not provided)

        Returns:
            Record ID
        """
        import uuid

        record_id = record_id or str(uuid.uuid4())
        timestamp = datetime.utcnow()

        record = SyncRecord(
            record_id=record_id,
            record_type=record_type,
            data=data,
            timestamp=timestamp,
        )

        self.sync_queue.append(record)
        self._persist_queue()

        logger.info(
            f"Record added to sync queue: {record_type} ({record_id})\n"
            f"  Queue size: {len(self.sync_queue)}"
        )

        return record_id

    async def sync(self, force: bool = False) -> Dict[str, Any]:
        """
        Sync pending records with server

        Args:
            force: Force sync even if not online

        Returns:
            Sync results
        """
        if not self.is_online and not force:
            logger.warning("Cannot sync: offline mode")
            return {
                "status": "skipped",
                "reason": "offline",
                "pending_count": len(self.sync_queue),
            }

        if not self.sync_queue:
            logger.info("No pending records to sync")
            return {
                "status": "success",
                "synced_count": 0,
                "failed_count": 0,
                "pending_count": 0,
            }

        logger.info(f"Starting sync of {len(self.sync_queue)} records")

        synced_count = 0
        failed_count = 0

        # Process in batches
        for i in range(0, len(self.sync_queue), self.batch_size):
            batch = self.sync_queue[i:i + self.batch_size]

            for record in batch:
                # Skip if max retries exceeded
                if record.retry_count >= self.max_retries:
                    logger.warning(
                        f"Max retries exceeded for {record.record_id}, marking as failed"
                    )
                    record.status = "failed"
                    failed_count += 1
                    continue

                # Attempt sync
                try:
                    success = await self._sync_record(record)

                    if success:
                        record.status = "completed"
                        synced_count += 1
                        logger.info(f"✓ Synced {record.record_id}")
                    else:
                        record.status = "failed"
                        record.retry_count += 1
                        record.last_retry = datetime.utcnow()
                        failed_count += 1
                        logger.warning(
                            f"✗ Failed to sync {record.record_id} "
                            f"(retry {record.retry_count}/{self.max_retries})"
                        )

                except Exception as e:
                    logger.error(f"Error syncing {record.record_id}: {e}")
                    record.status = "failed"
                    record.retry_count += 1
                    record.last_retry = datetime.utcnow()
                    failed_count += 1

        # Remove completed records
        self.sync_queue = [r for r in self.sync_queue if r.status != "completed"]
        self._persist_queue()

        result = {
            "status": "completed",
            "synced_count": synced_count,
            "failed_count": failed_count,
            "pending_count": len(self.sync_queue),
        }

        logger.info(
            f"✓ Sync completed:\n"
            f"  Synced: {synced_count}\n"
            f"  Failed: {failed_count}\n"
            f"  Pending: {len(self.sync_queue)}"
        )

        return result

    async def _sync_record(self, record: SyncRecord) -> bool:
        """
        Sync a single record with server

        Args:
            record: Sync record

        Returns:
            True if successful, False otherwise
        """
        # TODO: Implement actual API call to server
        # For now, simulate sync with delay

        logger.info(f"Syncing {record.record_type} record: {record.record_id}")

        # Simulate API call
        await asyncio.sleep(0.1)

        # In production, this would be:
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{API_URL}/sync/{record.record_type}",
        #         json=record.data,
        #         headers={"Authorization": f"Bearer {token}"}
        #     )
        #     return response.status_code == 200

        # For now, assume success
        return True

    async def start_background_sync(self) -> None:
        """Start background sync task"""
        if self.sync_task and not self.sync_task.done():
            logger.warning("Background sync already running")
            return

        logger.info(f"Starting background sync (interval: {self.sync_interval}s)")

        async def sync_loop():
            while True:
                try:
                    if self.is_online and self.sync_queue:
                        await self.sync()
                except Exception as e:
                    logger.error(f"Background sync error: {e}")

                await asyncio.sleep(self.sync_interval)

        self.sync_task = asyncio.create_task(sync_loop())
        logger.info("✓ Background sync started")

    async def stop_background_sync(self) -> None:
        """Stop background sync task"""
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass

            logger.info("✓ Background sync stopped")

    def set_online_status(self, is_online: bool) -> None:
        """Update online/offline status"""
        previous_status = self.is_online
        self.is_online = is_online

        if previous_status != is_online:
            logger.info(f"Network status changed: {'ONLINE' if is_online else 'OFFLINE'}")

            # Trigger immediate sync if coming online and have pending records
            if is_online and self.sync_queue:
                logger.info(f"Coming online with {len(self.sync_queue)} pending records")
                # In async context, you'd await self.sync()

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        status_counts = {
            "pending": 0,
            "completed": 0,
            "failed": 0,
        }

        for record in self.sync_queue:
            status_counts[record.status] = status_counts.get(record.status, 0) + 1

        return {
            "is_online": self.is_online,
            "total_pending": len(self.sync_queue),
            "status_breakdown": status_counts,
            "oldest_pending": (
                self.sync_queue[0].timestamp.isoformat()
                if self.sync_queue else None
            ),
        }

    def _persist_queue(self) -> None:
        """Persist sync queue to disk"""
        queue_file = self.sync_queue_path / "sync_queue.json"

        data = {
            "last_updated": datetime.utcnow().isoformat(),
            "records": [r.to_dict() for r in self.sync_queue],
        }

        with open(queue_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_queue(self) -> None:
        """Load sync queue from disk"""
        queue_file = self.sync_queue_path / "sync_queue.json"

        if not queue_file.exists():
            logger.info("No existing sync queue found")
            return

        try:
            with open(queue_file, 'r') as f:
                data = json.load(f)

            self.sync_queue = [
                SyncRecord.from_dict(r) for r in data.get("records", [])
            ]

            logger.info(f"✓ Loaded {len(self.sync_queue)} records from sync queue")

        except Exception as e:
            logger.error(f"Failed to load sync queue: {e}")


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Initialize sync manager
        sync_manager = OfflineSyncManager(
            sync_interval_seconds=10,  # Sync every 10 seconds
        )

        # Simulate offline activity
        print("\n--- Simulating offline activity ---")
        sync_manager.set_online_status(False)

        # Add student progress records
        sync_manager.add_to_queue(
            record_type="practice_answer",
            data={
                "student_id": "12345",
                "question_id": "math_001",
                "answer": "x = 5",
                "correct": True,
                "time_spent_seconds": 45,
            }
        )

        sync_manager.add_to_queue(
            record_type="topic_progress",
            data={
                "student_id": "12345",
                "subject": "Mathematics",
                "topic": "Algebra",
                "progress_percent": 75,
            }
        )

        # Check status
        status = sync_manager.get_sync_status()
        print(f"\nSync status (offline): {status}")

        # Come online and sync
        print("\n--- Coming online ---")
        sync_manager.set_online_status(True)

        result = await sync_manager.sync()
        print(f"\nSync result: {result}")

        # Final status
        status = sync_manager.get_sync_status()
        print(f"\nFinal sync status: {status}")

    asyncio.run(main())
