# Eve Environment Hardware Notes

## Summary

| Component    | Status |
|--------------|--------|
| GPU          | ❌ |
| Audio        | ❌ |
| STT          | ❌ |
| TTS          | ✅ |
| LLM          | ✅ |

## Detailed Logs

### GPU Validation
```text
--- GPU Environment Validation ---
❌ NVIDIA GPU not detected (nvidia-smi not found or failed)
❌ CUDA Toolkit (nvcc) not found in PATH
❌ pynvml module not installed

Summary: No compatible NVIDIA GPU found. Will fallback to CPU or Cloud APIs.
```

### Audio Validation
```text
--- Audio Environment Validation ---
❌ sounddevice module not installed
```

### STT Validation
```text
--- STT Environment Validation ---
❌ faster-whisper module not installed
```

### TTS Validation
```text
--- TTS Environment Validation ---
✅ HTTP client available for Cloud TTS.
⚠️ kokoro module not found (optional for cloud).
```

### LLM Validation
```text
--- LLM Environment Validation ---
❌ Ollama not running or not reachable at localhost:11434
⚠️ OPENAI_API_KEY not set (required for OpenAI LLM).
```
