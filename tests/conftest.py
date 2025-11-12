"""
Pytest configuration and shared fixtures
Epic 3.2: Testing & Quality Assurance
"""
import pytest
import sys
from pathlib import Path
import tempfile
import shutil
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import Settings


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Test configuration settings"""
    return Settings(
        environment="testing",
        debug=True,
        log_level="DEBUG",
        model_path="./tests/fixtures/models/",
        vector_db_path="./tests/fixtures/vector_db/",
        offline_mode=True,
    )


@pytest.fixture(scope="function")
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_curriculum_documents() -> List[Dict[str, Any]]:
    """Sample curriculum documents for testing"""
    return [
        {
            "text": "Photosynthesis is the process by which green plants use sunlight to synthesize nutrients from carbon dioxide and water. The equation is: 6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂",
            "metadata": {
                "subject": "Biology",
                "topic": "Plant Physiology",
                "subtopic": "Photosynthesis",
                "class": "SS2",
                "difficulty": "medium",
            }
        },
        {
            "text": "Newton's first law of motion states that an object at rest stays at rest and an object in motion continues in motion with constant velocity unless acted upon by an external force. This is also called the law of inertia.",
            "metadata": {
                "subject": "Physics",
                "topic": "Mechanics",
                "subtopic": "Newton's Laws",
                "class": "SS1",
                "difficulty": "easy",
            }
        },
        {
            "text": "A quadratic equation is a second-degree polynomial equation in the form ax² + bx + c = 0, where a ≠ 0. The quadratic formula is: x = (-b ± √(b² - 4ac)) / (2a)",
            "metadata": {
                "subject": "Mathematics",
                "topic": "Algebra",
                "subtopic": "Quadratic Equations",
                "class": "SS2",
                "difficulty": "medium",
            }
        },
        {
            "text": "The periodic table organizes elements by atomic number and chemical properties. Elements in the same group have similar properties. The first 20 elements include hydrogen, helium, lithium, beryllium, boron, carbon, nitrogen, oxygen, fluorine, neon, sodium, magnesium, aluminum, silicon, phosphorus, sulfur, chlorine, argon, potassium, and calcium.",
            "metadata": {
                "subject": "Chemistry",
                "topic": "Periodic Table",
                "subtopic": "Elements",
                "class": "SS1",
                "difficulty": "easy",
            }
        },
    ]


@pytest.fixture
def sample_test_prompts() -> List[str]:
    """Sample test prompts for model evaluation"""
    return [
        "Solve the equation: 2x + 5 = 15",
        "What is photosynthesis?",
        "State Newton's first law of motion.",
        "Calculate the area of a circle with radius 7cm.",
        "What is the atomic number of carbon?",
    ]


@pytest.fixture
def sample_waec_questions() -> List[Dict[str, Any]]:
    """Sample WAEC-style questions for accuracy testing"""
    return [
        {
            "question": "If 2x + 3 = 11, find the value of x.",
            "options": ["A. 3", "B. 4", "C. 5", "D. 6"],
            "correct_answer": "B",
            "subject": "Mathematics",
            "topic": "Linear Equations",
            "difficulty": "easy",
        },
        {
            "question": "Which of the following is NOT a function of the cell membrane?",
            "options": [
                "A. Controls what enters and leaves the cell",
                "B. Provides structural support",
                "C. Photosynthesis",
                "D. Cell recognition"
            ],
            "correct_answer": "C",
            "subject": "Biology",
            "topic": "Cell Biology",
            "difficulty": "medium",
        },
        {
            "question": "The SI unit of force is:",
            "options": ["A. Joule", "B. Newton", "C. Watt", "D. Pascal"],
            "correct_answer": "B",
            "subject": "Physics",
            "topic": "Units and Measurements",
            "difficulty": "easy",
        },
    ]


@pytest.fixture
def sample_sync_records() -> List[Dict[str, Any]]:
    """Sample sync records for testing"""
    return [
        {
            "record_type": "practice_answer",
            "data": {
                "student_id": "test_student_001",
                "question_id": "math_q_001",
                "answer": "x = 4",
                "correct": True,
                "time_spent_seconds": 45,
            }
        },
        {
            "record_type": "topic_progress",
            "data": {
                "student_id": "test_student_001",
                "subject": "Mathematics",
                "topic": "Algebra",
                "progress_percent": 75,
            }
        },
        {
            "record_type": "quiz_score",
            "data": {
                "student_id": "test_student_001",
                "quiz_id": "quiz_001",
                "score": 85,
                "total": 100,
                "time_taken_seconds": 600,
            }
        },
    ]


# ============================================================================
# Mock Model Fixtures
# ============================================================================

@pytest.fixture
def mock_tokenizer():
    """Mock tokenizer for testing without loading actual models"""
    class MockTokenizer:
        def __init__(self):
            self.eos_token_id = 2
            self.pad_token_id = 0

        def __call__(self, text, return_tensors=None, **kwargs):
            import torch
            # Return mock tensors
            return {
                "input_ids": torch.tensor([[1, 2, 3, 4, 5]]),
                "attention_mask": torch.tensor([[1, 1, 1, 1, 1]]),
            }

        def decode(self, token_ids, skip_special_tokens=False):
            return "Mock generated response for testing"

        def save_pretrained(self, path):
            pass

    return MockTokenizer()


@pytest.fixture
def mock_model():
    """Mock model for testing without loading actual models"""
    class MockModel:
        def __init__(self):
            self.device = "cpu"
            self.config = type('Config', (), {"hidden_size": 768})()

        def generate(self, **kwargs):
            import torch
            # Return mock output
            return torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]])

        def parameters(self):
            import torch
            # Mock parameter for size calculation
            return [torch.randn(100, 100)]

        def buffers(self):
            return []

        def save_pretrained(self, path):
            pass

        def eval(self):
            return self

    return MockModel()


# ============================================================================
# Vector Store Fixtures
# ============================================================================

@pytest.fixture
def test_vector_store(temp_dir, sample_curriculum_documents):
    """Create test vector store with sample data"""
    from src.offline.rag.vector_store import create_vector_store

    vector_store = create_vector_store(
        store_type="faiss",
        collection_name="test_collection",
        persist_directory=str(temp_dir),
    )

    # Add sample documents
    vector_store.add_documents(sample_curriculum_documents)

    yield vector_store

    # Cleanup
    try:
        vector_store.delete_collection()
    except:
        pass


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def performance_timer():
    """Timer for performance testing"""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return None

    return Timer()


# ============================================================================
# Test Result Collectors
# ============================================================================

@pytest.fixture
def test_results_collector():
    """Collect test results for reporting"""
    class ResultsCollector:
        def __init__(self):
            self.results = []

        def add(self, test_name: str, passed: bool, duration_ms: float, **metadata):
            self.results.append({
                "test_name": test_name,
                "passed": passed,
                "duration_ms": duration_ms,
                **metadata
            })

        def summary(self):
            total = len(self.results)
            passed = sum(1 for r in self.results if r["passed"])
            failed = total - passed
            avg_duration = sum(r["duration_ms"] for r in self.results) / total if total > 0 else 0

            return {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": (passed / total * 100) if total > 0 else 0,
                "avg_duration_ms": avg_duration,
            }

    return ResultsCollector()


# ============================================================================
# Cleanup Hooks
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_artifacts():
    """Cleanup test artifacts after all tests"""
    yield

    # Cleanup test directories
    test_dirs = [
        "./tests/fixtures/",
        "./data/test_sync_queue/",
        "./htmlcov/",
    ]

    for dir_path in test_dirs:
        if Path(dir_path).exists():
            shutil.rmtree(dir_path, ignore_errors=True)
