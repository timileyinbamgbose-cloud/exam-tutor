"""
Network Detection and Offline Fallback Logic
Epic 3.1: Automatic detection and graceful degradation

Features:
- Real-time network status monitoring
- Automatic fallback to offline mode
- Connection quality assessment
- Bandwidth-aware sync
"""
from typing import Optional, Dict, Any, Callable
import asyncio
import socket
import httpx
from datetime import datetime
from src.core.logger import get_logger

logger = get_logger(__name__)


class NetworkDetector:
    """
    Detect network connectivity and manage offline/online transitions

    Use cases:
    - Detect when device goes offline
    - Automatically switch to offline mode
    - Resume sync when connection restored
    - Assess connection quality for adaptive behavior
    """

    def __init__(
        self,
        check_interval_seconds: int = 30,
        timeout_seconds: int = 5,
        connectivity_check_urls: Optional[list[str]] = None,
    ):
        self.check_interval = check_interval_seconds
        self.timeout = timeout_seconds

        # URLs to check for connectivity (Nigerian and global)
        self.connectivity_check_urls = connectivity_check_urls or [
            "https://www.google.com",
            "https://www.cloudflare.com",
            "https://1.1.1.1",  # Cloudflare DNS
        ]

        self.is_online = False
        self.last_check: Optional[datetime] = None
        self.connection_quality: Optional[str] = None  # "excellent", "good", "poor", "offline"
        self.monitoring_task: Optional[asyncio.Task] = None

        # Callbacks for status changes
        self.on_online_callbacks: list[Callable] = []
        self.on_offline_callbacks: list[Callable] = []

        logger.info("NetworkDetector initialized")

    async def check_connectivity(self) -> bool:
        """
        Check network connectivity

        Returns:
            True if online, False if offline
        """
        self.last_check = datetime.utcnow()

        # Method 1: DNS resolution test (fastest)
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            logger.debug("DNS connectivity check: PASS")
        except OSError:
            logger.warning("DNS connectivity check: FAIL")
            return False

        # Method 2: HTTP request test (more reliable)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for url in self.connectivity_check_urls:
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.debug(f"HTTP connectivity check ({url}): PASS")
                        return True
                except Exception as e:
                    logger.debug(f"HTTP connectivity check ({url}): FAIL - {e}")
                    continue

        logger.warning("All connectivity checks failed")
        return False

    async def assess_connection_quality(self) -> str:
        """
        Assess connection quality based on latency

        Returns:
            "excellent", "good", "poor", or "offline"
        """
        if not self.is_online:
            return "offline"

        try:
            import time
            start_time = time.time()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                await client.get(self.connectivity_check_urls[0])

            latency_ms = (time.time() - start_time) * 1000

            if latency_ms < 100:
                quality = "excellent"
            elif latency_ms < 300:
                quality = "good"
            else:
                quality = "poor"

            logger.info(f"Connection quality: {quality} (latency: {latency_ms:.0f}ms)")
            return quality

        except Exception as e:
            logger.error(f"Failed to assess connection quality: {e}")
            return "poor"

    async def update_status(self) -> Dict[str, Any]:
        """
        Update network status and trigger callbacks if status changed

        Returns:
            Status information
        """
        previous_status = self.is_online
        current_status = await self.check_connectivity()

        self.is_online = current_status

        # Status changed
        if previous_status != current_status:
            if current_status:
                logger.info("🟢 NETWORK STATUS: ONLINE")
                await self._trigger_callbacks(self.on_online_callbacks)
            else:
                logger.warning("🔴 NETWORK STATUS: OFFLINE")
                await self._trigger_callbacks(self.on_offline_callbacks)

        # Assess quality if online
        if current_status:
            self.connection_quality = await self.assess_connection_quality()
        else:
            self.connection_quality = "offline"

        return {
            "is_online": self.is_online,
            "connection_quality": self.connection_quality,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "status_changed": previous_status != current_status,
        }

    async def start_monitoring(self) -> None:
        """Start continuous network monitoring"""
        if self.monitoring_task and not self.monitoring_task.done():
            logger.warning("Network monitoring already running")
            return

        logger.info(f"Starting network monitoring (interval: {self.check_interval}s)")

        async def monitoring_loop():
            while True:
                try:
                    await self.update_status()
                except Exception as e:
                    logger.error(f"Network monitoring error: {e}")

                await asyncio.sleep(self.check_interval)

        self.monitoring_task = asyncio.create_task(monitoring_loop())
        logger.info("✓ Network monitoring started")

        # Initial check
        await self.update_status()

    async def stop_monitoring(self) -> None:
        """Stop network monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

            logger.info("✓ Network monitoring stopped")

    def on_online(self, callback: Callable) -> None:
        """Register callback for when connection is restored"""
        self.on_online_callbacks.append(callback)
        logger.info(f"Registered on_online callback: {callback.__name__}")

    def on_offline(self, callback: Callable) -> None:
        """Register callback for when connection is lost"""
        self.on_offline_callbacks.append(callback)
        logger.info(f"Registered on_offline callback: {callback.__name__}")

    async def _trigger_callbacks(self, callbacks: list[Callable]) -> None:
        """Trigger all callbacks in list"""
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Callback error ({callback.__name__}): {e}")

    def should_use_offline_mode(self) -> bool:
        """
        Determine if offline mode should be used

        Returns:
            True if offline mode should be used
        """
        if not self.is_online:
            return True

        # Use offline mode if connection is poor
        if self.connection_quality == "poor":
            logger.info("Using offline mode due to poor connection quality")
            return True

        return False

    def get_status(self) -> Dict[str, Any]:
        """Get current network status"""
        return {
            "is_online": self.is_online,
            "connection_quality": self.connection_quality,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "monitoring_active": (
                self.monitoring_task is not None and not self.monitoring_task.done()
            ),
        }


class OfflineCapabilityManager:
    """
    Manage offline capability and graceful degradation

    Features:
    - Automatic mode switching
    - Resource management for offline mode
    - User notifications
    """

    def __init__(self, network_detector: Optional[NetworkDetector] = None):
        self.network_detector = network_detector or NetworkDetector()
        self.offline_mode_active = False

        # Register network callbacks
        self.network_detector.on_online(self._on_connection_restored)
        self.network_detector.on_offline(self._on_connection_lost)

        logger.info("OfflineCapabilityManager initialized")

    async def _on_connection_restored(self) -> None:
        """Handle connection restoration"""
        logger.info("🟢 Connection restored - switching to online mode")
        self.offline_mode_active = False

        # Trigger sync (would call sync_manager.sync())
        logger.info("Triggering sync of offline data...")

    async def _on_connection_lost(self) -> None:
        """Handle connection loss"""
        logger.warning("🔴 Connection lost - switching to offline mode")
        self.offline_mode_active = True

        # Notify user
        logger.info("User notification: App is now in offline mode")

    def is_offline_mode(self) -> bool:
        """Check if currently in offline mode"""
        return self.offline_mode_active or not self.network_detector.is_online

    async def start(self) -> None:
        """Start offline capability management"""
        logger.info("Starting offline capability manager")
        await self.network_detector.start_monitoring()

    async def stop(self) -> None:
        """Stop offline capability management"""
        logger.info("Stopping offline capability manager")
        await self.network_detector.stop_monitoring()

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get available capabilities based on current mode

        Returns:
            Dict of available features
        """
        network_status = self.network_detector.get_status()

        if self.is_offline_mode():
            return {
                "mode": "offline",
                "network_status": network_status,
                "available_features": {
                    "ask_questions": True,  # Using offline RAG
                    "practice_questions": True,  # Using local DB
                    "learning_plans": True,  # Using local data
                    "progress_tracking": True,  # Syncs when online
                    "teacher_features": False,  # Requires server
                    "live_leaderboard": False,  # Requires server
                    "model_updates": False,  # Requires server
                },
                "limitations": [
                    "Cannot access latest content updates",
                    "Progress will sync when connection restored",
                    "Teacher features unavailable",
                ],
            }
        else:
            return {
                "mode": "online",
                "network_status": network_status,
                "available_features": {
                    "ask_questions": True,
                    "practice_questions": True,
                    "learning_plans": True,
                    "progress_tracking": True,
                    "teacher_features": True,
                    "live_leaderboard": True,
                    "model_updates": True,
                },
                "limitations": [],
            }


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Create offline capability manager
        capability_manager = OfflineCapabilityManager()

        # Start monitoring
        await capability_manager.start()

        # Check capabilities
        capabilities = capability_manager.get_capabilities()
        print(f"\nCurrent capabilities:")
        print(f"Mode: {capabilities['mode']}")
        print(f"Network: {capabilities['network_status']}")
        print(f"\nAvailable features:")
        for feature, available in capabilities['available_features'].items():
            status = "✓" if available else "✗"
            print(f"  {status} {feature}")

        if capabilities['limitations']:
            print(f"\nLimitations:")
            for limitation in capabilities['limitations']:
                print(f"  - {limitation}")

        # Monitor for 60 seconds
        print(f"\nMonitoring network for 60 seconds...")
        await asyncio.sleep(60)

        # Stop
        await capability_manager.stop()
        print("\n✓ Monitoring stopped")

    asyncio.run(main())
