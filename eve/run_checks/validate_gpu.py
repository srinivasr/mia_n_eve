#!/usr/bin/env python3
"""
GPU Validation Script for mia_n_eve runtime.
Checks for NVIDIA GPU, CUDA availability, NVML bindings, and VRAM.
"""
import subprocess
import sys

def check_nvidia_smi():
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'], 
                                capture_output=True, text=True, check=True)
        print("✅ NVIDIA GPU Detected:")
        for line in result.stdout.strip().split('\n'):
            print(f"   - {line}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ NVIDIA GPU not detected (nvidia-smi not found or failed)")
        return False

def check_nvcc():
    try:
        result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True, check=True)
        # Extract version
        version_line = [line for line in result.stdout.split('\n') if 'release' in line]
        if version_line:
            print(f"✅ CUDA Toolkit Detected: {version_line[0].strip()}")
        else:
            print("✅ CUDA Toolkit Detected (version unknown)")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ CUDA Toolkit (nvcc) not found in PATH")
        return False

def check_pynvml():
    try:
        import pynvml
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        print(f"✅ NVML bindings (pynvml) available. Found {device_count} device(s).")
        pynvml.nvmlShutdown()
        return True
    except ImportError:
        print("❌ pynvml module not installed")
        return False
    except pynvml.NVMLError as e:
        print(f"❌ NVML init failed: {e}")
        return False

def main():
    print("--- GPU Environment Validation ---")
    smi_ok = check_nvidia_smi()
    nvcc_ok = check_nvcc()
    pynvml_ok = check_pynvml()
    
    if smi_ok:
        print("\nSummary: GPU hardware found. System is capable of local acceleration.")
        if not nvcc_ok:
            print("Warning: CUDA toolkit missing. Some source-built ML packages might fail.")
    else:
        print("\nSummary: No compatible NVIDIA GPU found. Will fallback to CPU or Cloud APIs.")
        
    return 0 if smi_ok else 1

if __name__ == "__main__":
    sys.exit(main())
