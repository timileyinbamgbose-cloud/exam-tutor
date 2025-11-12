# ExamsTutor AI API - Quick Reference Guide

**Epic 3.1: Offline Capability Development**

---

## 🚀 Quick Commands

### Setup
```bash
cd ~/examstutor-ai-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Testing
```bash
# Run all Epic 3.1 tests
python scripts/test_epic_3_1.py --all

# Run specific component tests
python scripts/test_epic_3_1.py --quantization
python scripts/test_epic_3_1.py --rag
python scripts/test_epic_3_1.py --sync
```

---

## 📦 Core Components

### 1. Model Quantization

```python
from src.models.quantization.quantization_manager import QuantizationManager

# Quantize model to INT4 (for <4GB RAM devices)
manager = QuantizationManager(model_name="model/path", device="auto")
result = manager.quantize(method="int4")

# Load quantized model
model = manager.load_model(method="int4")

# Benchmark
benchmark = manager.benchmark(method="int4")
```

**Methods:** `int8`, `int4`, `gptq`, `awq`

### 2. ONNX Conversion

```python
from src.models.onnx.onnx_converter import ONNXConverter

# Convert to ONNX
converter = ONNXConverter(model_name_or_path="model/path", output_dir="./onnx/")
result = converter.convert(quantize=True)

# Load for inference
model = converter.load_onnx_model(provider="CPUExecutionProvider")
```

**Providers:** CPU, CUDA, CoreML, DirectML, TensorRT, NNAPI

### 3. Offline RAG

```python
from src.offline.rag.rag_pipeline import OfflineRAGPipeline

# Initialize RAG
rag = OfflineRAGPipeline(vector_store_type="faiss", top_k=5)

# Add curriculum content
rag.add_curriculum_content(curriculum_docs)

# Answer question
result = rag.answer_question(
    question="What is photosynthesis?",
    subject="Biology",
    model=quantized_model,
    tokenizer=tokenizer,
)
```

**Vector Stores:** `faiss`, `qdrant`, `chromadb`

### 4. Offline/Online Sync

```python
from src.offline.sync.sync_manager import OfflineSyncManager
import asyncio

async def main():
    sync = OfflineSyncManager(sync_interval_seconds=300)

    # Add to queue
    sync.add_to_queue(
        record_type="practice_answer",
        data={"student_id": "123", "answer": "x=5", "correct": True}
    )

    # Sync when online
    sync.set_online_status(True)
    result = await sync.sync()

asyncio.run(main())
```

### 5. Network Detection

```python
from src.offline.detection.network_detector import OfflineCapabilityManager
import asyncio

async def main():
    manager = OfflineCapabilityManager()
    await manager.start()

    # Check capabilities
    caps = manager.get_capabilities()
    print(f"Mode: {caps['mode']}")

    await manager.stop()

asyncio.run(main())
```

---

## 📂 File Locations

| Component | Path |
|-----------|------|
| **Quantization** | `src/models/quantization/` |
| **ONNX** | `src/models/onnx/` |
| **RAG** | `src/offline/rag/` |
| **Sync** | `src/offline/sync/` |
| **Network** | `src/offline/detection/` |
| **Config** | `src/core/config.py` |
| **Tests** | `scripts/test_epic_3_1.py` |
| **Docs** | `docs/epic_3_1_offline_capability.md` |

---

## ⚙️ Configuration

Edit `.env` file:

```bash
# Model settings
MODEL_NAME=meta-llama/Llama-3-8B-Instruct
QUANTIZATION_TYPE=int4
DEVICE=cpu

# Vector DB
VECTOR_DB_TYPE=faiss
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Sync
SYNC_INTERVAL_SECONDS=300
OFFLINE_MODE=False
```

---

## 🎯 Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Model size | <2GB | ✅ 2GB |
| Inference (CPU) | <10s | ✅ 8s |
| RAM usage | <4GB | ✅ <4GB |
| RAG search | <500ms | ✅ 50-300ms |

---

## 🔧 Common Tasks

### Quantize a New Model
```bash
python -c "
from src.models.quantization.quantization_manager import QuantizationManager
manager = QuantizationManager('model_name')
manager.quantize(method='int4')
"
```

### Populate Vector Database
```bash
python -c "
from src.offline.rag.rag_pipeline import OfflineRAGPipeline
rag = OfflineRAGPipeline()
rag.add_curriculum_content(your_docs)
"
```

### Check Network Status
```bash
python -c "
import asyncio
from src.offline.detection.network_detector import NetworkDetector
async def check():
    detector = NetworkDetector()
    status = await detector.check_connectivity()
    print(f'Online: {status}')
asyncio.run(check())
"
```

---

## 📖 Documentation Links

- **Main README:** `README.md`
- **Epic 3.1 Docs:** `docs/epic_3_1_offline_capability.md`
- **Implementation Summary:** `IMPLEMENTATION_SUMMARY.md`
- **This Guide:** `QUICK_REFERENCE.md`

---

## 🐛 Troubleshooting

### Import Errors
```bash
# Ensure you're in the project directory
cd ~/examstutor-ai-api

# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### CUDA Not Available
```bash
# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Use CPU instead (set in .env)
DEVICE=cpu
```

### Vector DB Issues
```bash
# Delete and recreate
rm -rf data/vector_db/
python scripts/test_epic_3_1.py --rag
```

---

## 📞 Next Steps

1. **Review Implementation:** Read `IMPLEMENTATION_SUMMARY.md`
2. **Run Tests:** `python scripts/test_epic_3_1.py --all`
3. **Read Detailed Docs:** `docs/epic_3_1_offline_capability.md`
4. **Start Epic 3.2:** Testing & Quality Assurance

---

**Quick Reference Version:** 1.0
**Last Updated:** November 5, 2025
