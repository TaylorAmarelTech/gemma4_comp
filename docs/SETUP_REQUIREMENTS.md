# DueCare Setup requirements`r`nClear setup instructions for running DueCare notebooks and applications across different environments.

## 🖥️ Kaggle Notebooks (Recommended for Demo)

### Required Setup (in Kaggle interface):
1. **Accelerator**: Set to **GPU T4 x2** (recommended) or equivalent (T4/P100/A100/V100)
2. **Internet**: Set to **ON** (required for GitHub package installation)
3. **Persistence**: Optional (notebooks are fully self-contained)

### No Manual Steps Required:
- ✅ No dataset linking
- ✅ No "Add Data" requirements`r`n- ✅ No manual package installation
- ✅ Self-installing from GitHub

### Click "Run All" - Everything Else is Automatic!

---

## 🏠 Local Development Environment

### System Requirements:
- **Python**: 3.11+ (3.12+ recommended)
- **GPU**: CUDA-capable with 8GB+ VRAM (16GB+ for larger models)
- **RAM**: 16GB+ system memory (32GB+ recommended)
- **Storage**: 20GB+ free space for models and dependencies
- **Internet**: Required for initial package and model downloads

### Initial Setup:

#### 1. Install PyTorch (CUDA):
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### 2. Verify GPU:
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU count: {torch.cuda.device_count()}")
print(f"GPU name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No GPU'}")
```

#### 3. Run Notebook:
- DueCare packages auto-install from GitHub
- Models download automatically from HF Hub or Kaggle Models

### Supported GPU Configurations:
| GPU | VRAM | Recommended Models |
|-----|------|-------------------|
| RTX 4090 | 24GB | Gemma 4 E4B (full precision) |
| RTX 4080 | 16GB | Gemma 4 E4B (4-bit quantized) |
| RTX 4070 | 12GB | Gemma 4 E2B (full precision) |
| RTX 3080 | 10GB | Gemma 4 E2B (4-bit quantized) |
| T4 x2 | 16GB | Gemma 4 E4B (4-bit quantized) |
| T4 | 16GB | Gemma 4 E2B (4-bit quantized) |

---

## ☁️ Cloud Platforms

### Google Colab:
1. **Runtime**: Change runtime type → Hardware accelerator → **GPU**
2. **Runtime Type**: T4/V100/A100 (if available)
3. **Run**: Upload notebook and run - auto-detects Colab environment

### AWS SageMaker / Azure / GCP:
1. **Instance**: GPU-enabled instance (ml.g4dn.xlarge or equivalent)
2. **Environment**: JupyterLab or notebook environment
3. **Setup**: Run notebook - auto-detects cloud environment

---

## 📋 Package Dependencies (Auto-Installed)

### Core Dependencies:
- `torch` (PyTorch - deep learning framework)
- `transformers` (Hugging Face model adapters)
- `accelerate` (distributed training support)
- `bitsandbytes` (quantization for memory efficiency)

### Web Interface Dependencies:
- `fastapi` (web framework)
- `uvicorn` (ASGI server)
- `pydantic` (data validation)
- `jinja2` (template engine)

### Optional Dependencies (install on demand):
- `unsloth` (fine-tuning framework)
- `llama-cpp-python` (CPU/quantized inference)
- `openai` (OpenAI API integration)
- `anthropic` (Claude API integration)

---

## 🔧 Troubleshooting

### Common Issues:

#### "CUDA out of memory"
- **Solution**: Use smaller model (E2B instead of E4B) or enable 4-bit quantization
- **Check**: `nvidia-smi` to see current VRAM usage

#### "No module named 'torch'"
- **Solution**: Install PyTorch with CUDA support (see Local Setup above)
- **Check**: Run `pip install torch --index-url https://download.pytorch.org/whl/cu121`

#### "Could not find a version that satisfies the requirement"
- **Solution**: Update pip: `pip install --upgrade pip`
- **Check**: Python version with `python --version` (must be 3.11+)

#### "HTTP 403 Forbidden" during model download
- **Solution**: Set HF_TOKEN for private models or use public model variants
- **Check**: Model availability on Hugging Face Hub

#### Installation fails on GitHub packages
- **Fallback**: The notebook automatically tries multiple installation tiers
- **Manual**: Use `pip install git+https://github.com/TaylorAmarelTech/gemma4_comp.git@main#subdirectory=packages/duecare-llm-core`

### Getting Help:
1. **Check logs**: Installation logs show detailed error messages
2. **GPU info**: Run `nvidia-smi` to check GPU status
3. **Python environment**: Verify Python 3.11+ and pip version
4. **Internet**: Ensure connection for package/model downloads

---

## 🎯 Quick Start Verification

After setup, verify everything works:

```python
# Test 1: Check GPU
import torch
assert torch.cuda.is_available(), "CUDA not available"
print(f"✅ GPU: {torch.cuda.get_device_name(0)}")

# Test 2: Install DueCare (automatic in notebooks)
# Test 3: Load model and run demo prompt

print("🎉 Setup complete! Ready to run DueCare.")
```

---

## 📊 Performance Expectations

| Environment | Model | Expected Speed | Memory Usage |
|-------------|--------|----------------|--------------|
| Kaggle T4x2 | E4B 4-bit | 2-3 tok/sec | 14GB VRAM |
| Kaggle T4x2 | E2B full | 5-8 tok/sec | 10GB VRAM |
| Local RTX 4090 | E4B full | 15-25 tok/sec | 20GB VRAM |
| Local RTX 4070 | E2B 4-bit | 8-12 tok/sec | 8GB VRAM |
| Colab T4 | E2B 4-bit | 4-6 tok/sec | 12GB VRAM |

*Performance varies based on prompt length and complexity.*