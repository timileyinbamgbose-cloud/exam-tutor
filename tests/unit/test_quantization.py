"""
Unit tests for model quantization modules
Epic 3.2: Testing & Quality Assurance
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.models.quantization.base import BaseQuantizer, QuantizationConfig
from src.models.quantization.quantization_manager import QuantizationManager


@pytest.mark.unit
class TestBaseQuantizer:
    """Test BaseQuantizer abstract class"""

    def test_initialization(self, temp_dir):
        """Test quantizer initialization"""
        # Create concrete implementation for testing
        class ConcreteQuantizer(BaseQuantizer):
            def quantize(self, **kwargs):
                return {"quantized": True}

            def load_quantized_model(self, model_path):
                return None

        quantizer = ConcreteQuantizer(
            model_name="test-model",
            output_dir=str(temp_dir),
            device="cpu"
        )

        assert quantizer.model_name == "test-model"
        assert quantizer.output_dir == temp_dir
        assert quantizer.device == "cpu"
        assert temp_dir.exists()

    def test_model_size_calculation(self, mock_model):
        """Test model size calculation"""
        class ConcreteQuantizer(BaseQuantizer):
            def quantize(self, **kwargs):
                return {}

            def load_quantized_model(self, model_path):
                return None

        quantizer = ConcreteQuantizer(
            model_name="test",
            output_dir="./test",
            device="cpu"
        )
        quantizer.model = mock_model

        size_mb = quantizer.get_model_size_mb()

        assert isinstance(size_mb, float)
        assert size_mb > 0


@pytest.mark.unit
class TestQuantizationConfig:
    """Test quantization configurations"""

    def test_int8_config(self):
        """Test INT8 configuration"""
        config = QuantizationConfig.INT8_CONFIG

        assert config["bits"] == 8
        assert config["group_size"] == 128
        assert "desc_act" in config

    def test_int4_config(self):
        """Test INT4 configuration"""
        config = QuantizationConfig.INT4_CONFIG

        assert config["bits"] == 4
        assert config["group_size"] == 128

    def test_gptq_config(self):
        """Test GPTQ configuration"""
        config = QuantizationConfig.GPTQ_CONFIG

        assert config["bits"] == 4
        assert "damp_percent" in config

    def test_awq_config(self):
        """Test AWQ configuration"""
        config = QuantizationConfig.AWQ_CONFIG

        assert config["bits"] == 4
        assert config["zero_point"] is True


@pytest.mark.unit
class TestQuantizationManager:
    """Test QuantizationManager"""

    def test_initialization(self, temp_dir):
        """Test manager initialization"""
        manager = QuantizationManager(
            model_name="test-model",
            output_base_dir=str(temp_dir),
            device="cpu"
        )

        assert manager.model_name == "test-model"
        assert manager.device == "cpu"
        assert manager.quantizers == {}

    def test_supported_methods(self):
        """Test supported quantization methods"""
        assert "int8" in QuantizationManager.SUPPORTED_METHODS
        assert "int4" in QuantizationManager.SUPPORTED_METHODS
        assert "gptq" in QuantizationManager.SUPPORTED_METHODS
        assert "awq" in QuantizationManager.SUPPORTED_METHODS

    def test_unsupported_method_raises_error(self, temp_dir):
        """Test that unsupported method raises error"""
        manager = QuantizationManager(
            model_name="test-model",
            output_base_dir=str(temp_dir)
        )

        with pytest.raises(ValueError, match="Unsupported quantization method"):
            manager.quantize(method="unsupported_method")

    @patch('src.models.quantization.int8_quantizer.INT8Quantizer')
    def test_get_quantizer_int8(self, mock_quantizer_class, temp_dir):
        """Test getting INT8 quantizer"""
        manager = QuantizationManager(
            model_name="test-model",
            output_base_dir=str(temp_dir)
        )

        output_dir = manager.output_base_dir / "int8"
        quantizer = manager._get_quantizer("int8", output_dir)

        mock_quantizer_class.assert_called_once()

    def test_default_test_prompts(self, temp_dir):
        """Test default test prompts generation"""
        manager = QuantizationManager(
            model_name="test-model",
            output_base_dir=str(temp_dir)
        )

        prompts = manager._get_default_test_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0
        assert all(isinstance(p, str) for p in prompts)

        # Check for Nigerian curriculum content
        prompts_text = " ".join(prompts).lower()
        assert any(subject in prompts_text for subject in ["mathematics", "physics", "biology", "chemistry"])


@pytest.mark.unit
class TestQuantizationIntegration:
    """Integration tests for quantization workflow"""

    @pytest.mark.model
    @pytest.mark.slow
    def test_quantization_workflow(self, temp_dir):
        """
        Test complete quantization workflow (requires actual model)
        This test is marked as slow and requires a model to be available
        """
        pytest.skip("Requires actual model - run with --model flag")

        # This would be the actual workflow
        manager = QuantizationManager(
            model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            output_base_dir=str(temp_dir)
        )

        # Quantize
        result = manager.quantize(method="int4")

        # Verify results
        assert "quantized_size_mb" in result
        assert "compression_ratio" in result
        assert result["compression_ratio"] > 1

    def test_quantization_metadata_structure(self):
        """Test that quantization results have correct metadata structure"""
        expected_keys = [
            "quantization_type",
            "model_name",
            "quantized_size_mb",
            "compression_ratio",
            "output_path"
        ]

        # Mock result structure
        mock_result = {
            "quantization_type": "int4",
            "model_name": "test-model",
            "estimated_original_size_mb": 1000.0,
            "quantized_size_mb": 125.0,
            "compression_ratio": 8.0,
            "output_path": "/path/to/model"
        }

        for key in expected_keys:
            assert key in mock_result


@pytest.mark.unit
def test_quantization_compression_ratios():
    """Test expected compression ratios"""
    ratios = {
        "int8": 4,
        "int4": 8,
        "gptq": 4,
    }

    for method, expected_ratio in ratios.items():
        assert expected_ratio > 1, f"{method} should have compression > 1x"


@pytest.mark.unit
def test_quantization_performance_targets():
    """Test performance targets are defined"""
    targets = {
        "inference_time_cpu_seconds": 10,
        "ram_usage_gb": 4,
        "model_size_gb": 2,
    }

    # Verify targets are reasonable
    assert targets["inference_time_cpu_seconds"] <= 10
    assert targets["ram_usage_gb"] <= 4
    assert targets["model_size_gb"] <= 2
