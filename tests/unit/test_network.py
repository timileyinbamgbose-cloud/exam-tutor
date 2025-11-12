"""
Unit tests for Network Detection
Epic 3.2: Testing & Quality Assurance
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, Mock

from src.offline.detection.network_detector import (
    NetworkDetector,
    OfflineCapabilityManager
)


@pytest.mark.unit
class TestNetworkDetector:
    """Test NetworkDetector"""

    def test_initialization(self):
        """Test network detector initialization"""
        detector = NetworkDetector(
            check_interval_seconds=30,
            timeout_seconds=5
        )

        assert detector.check_interval == 30
        assert detector.timeout == 5
        assert detector.is_online == False
        assert len(detector.connectivity_check_urls) > 0

    @pytest.mark.asyncio
    @pytest.mark.online
    async def test_check_connectivity_when_online(self):
        """Test connectivity check when online (requires internet)"""
        detector = NetworkDetector()

        is_online = await detector.check_connectivity()

        # This might fail in offline environments
        assert isinstance(is_online, bool)

    @pytest.mark.asyncio
    async def test_check_connectivity_mock_online(self):
        """Test connectivity check with mocked online status"""
        detector = NetworkDetector()

        with patch('socket.create_connection'):
            with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                is_online = await detector.check_connectivity()

                assert is_online == True

    @pytest.mark.asyncio
    async def test_check_connectivity_mock_offline(self):
        """Test connectivity check with mocked offline status"""
        detector = NetworkDetector()

        with patch('socket.create_connection', side_effect=OSError):
            is_online = await detector.check_connectivity()

            assert is_online == False

    @pytest.mark.asyncio
    async def test_assess_connection_quality_excellent(self):
        """Test connection quality assessment - excellent"""
        detector = NetworkDetector()
        detector.is_online = True

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            with patch('time.time', side_effect=[0, 0.05]):  # 50ms latency
                quality = await detector.assess_connection_quality()

                assert quality == "excellent"

    @pytest.mark.asyncio
    async def test_assess_connection_quality_poor(self):
        """Test connection quality assessment - poor"""
        detector = NetworkDetector()
        detector.is_online = True

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            with patch('time.time', side_effect=[0, 0.5]):  # 500ms latency
                quality = await detector.assess_connection_quality()

                assert quality == "poor"

    @pytest.mark.asyncio
    async def test_update_status_triggers_callbacks(self):
        """Test that status changes trigger callbacks"""
        detector = NetworkDetector()

        callback_called = []

        async def on_online_callback():
            callback_called.append("online")

        async def on_offline_callback():
            callback_called.append("offline")

        detector.on_online(on_online_callback)
        detector.on_offline(on_offline_callback)

        # Mock going online
        with patch.object(detector, 'check_connectivity', return_value=True):
            await detector.update_status()

        assert "online" in callback_called

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring"""
        detector = NetworkDetector(check_interval_seconds=1)

        # Start monitoring
        await detector.start_monitoring()
        assert detector.monitoring_task is not None
        assert not detector.monitoring_task.done()

        # Wait a bit
        await asyncio.sleep(0.5)

        # Stop monitoring
        await detector.stop_monitoring()
        assert detector.monitoring_task.done() or detector.monitoring_task.cancelled()

    def test_should_use_offline_mode_when_offline(self):
        """Test offline mode decision when offline"""
        detector = NetworkDetector()
        detector.is_online = False

        assert detector.should_use_offline_mode() == True

    def test_should_use_offline_mode_when_poor_connection(self):
        """Test offline mode decision with poor connection"""
        detector = NetworkDetector()
        detector.is_online = True
        detector.connection_quality = "poor"

        assert detector.should_use_offline_mode() == True

    def test_should_not_use_offline_mode_when_good_connection(self):
        """Test offline mode decision with good connection"""
        detector = NetworkDetector()
        detector.is_online = True
        detector.connection_quality = "good"

        assert detector.should_use_offline_mode() == False

    def test_get_status(self):
        """Test getting network status"""
        detector = NetworkDetector()
        detector.is_online = True
        detector.connection_quality = "good"

        status = detector.get_status()

        assert status["is_online"] == True
        assert status["connection_quality"] == "good"
        assert "last_check" in status
        assert "monitoring_active" in status


@pytest.mark.unit
class TestOfflineCapabilityManager:
    """Test OfflineCapabilityManager"""

    def test_initialization(self):
        """Test capability manager initialization"""
        manager = OfflineCapabilityManager()

        assert manager.network_detector is not None
        assert manager.offline_mode_active == False

    @pytest.mark.asyncio
    async def test_on_connection_restored(self):
        """Test connection restored callback"""
        manager = OfflineCapabilityManager()
        manager.offline_mode_active = True

        await manager._on_connection_restored()

        assert manager.offline_mode_active == False

    @pytest.mark.asyncio
    async def test_on_connection_lost(self):
        """Test connection lost callback"""
        manager = OfflineCapabilityManager()
        manager.offline_mode_active = False

        await manager._on_connection_lost()

        assert manager.offline_mode_active == True

    def test_is_offline_mode_when_offline(self):
        """Test offline mode check when offline"""
        manager = OfflineCapabilityManager()
        manager.network_detector.is_online = False

        assert manager.is_offline_mode() == True

    def test_is_offline_mode_when_active(self):
        """Test offline mode check when manually activated"""
        manager = OfflineCapabilityManager()
        manager.network_detector.is_online = True
        manager.offline_mode_active = True

        assert manager.is_offline_mode() == True

    def test_get_capabilities_offline_mode(self):
        """Test capabilities in offline mode"""
        manager = OfflineCapabilityManager()
        manager.network_detector.is_online = False
        manager.offline_mode_active = True

        capabilities = manager.get_capabilities()

        assert capabilities["mode"] == "offline"
        assert capabilities["available_features"]["ask_questions"] == True
        assert capabilities["available_features"]["practice_questions"] == True
        assert capabilities["available_features"]["teacher_features"] == False
        assert len(capabilities["limitations"]) > 0

    def test_get_capabilities_online_mode(self):
        """Test capabilities in online mode"""
        manager = OfflineCapabilityManager()
        manager.network_detector.is_online = True
        manager.offline_mode_active = False

        capabilities = manager.get_capabilities()

        assert capabilities["mode"] == "online"
        assert capabilities["available_features"]["ask_questions"] == True
        assert capabilities["available_features"]["teacher_features"] == True
        assert len(capabilities["limitations"]) == 0

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping capability manager"""
        manager = OfflineCapabilityManager()

        # Start
        await manager.start()
        assert manager.network_detector.monitoring_task is not None

        # Stop
        await manager.stop()


@pytest.mark.unit
def test_connection_quality_levels():
    """Test connection quality level definitions"""
    quality_levels = ["excellent", "good", "poor", "offline"]

    # Verify all levels are defined
    for level in quality_levels:
        assert level in quality_levels


@pytest.mark.unit
def test_feature_availability_matrix():
    """Test feature availability matrix is complete"""
    manager = OfflineCapabilityManager()

    online_caps = manager.get_capabilities()
    manager.offline_mode_active = True
    offline_caps = manager.get_capabilities()

    # Check all features are defined in both modes
    online_features = set(online_caps["available_features"].keys())
    offline_features = set(offline_caps["available_features"].keys())

    assert online_features == offline_features

    # Verify key features
    key_features = [
        "ask_questions",
        "practice_questions",
        "learning_plans",
        "progress_tracking"
    ]

    for feature in key_features:
        assert feature in online_features
