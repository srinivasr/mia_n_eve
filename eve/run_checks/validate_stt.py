#!/usr/bin/env python3
"""
STT Validation Script for mia_n_eve runtime.
Checks faster-whisper availability.
"""
import sys
import time

def check_whisper():
    try:
        from faster_whisper import WhisperModel
        print("✅ faster-whisper module loaded.")
        
        print("Loading tiny model (CPU) for quick validation...")
        start_time = time.time()
        # Use compute_type="int8" for wide compatibility on CPU
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        load_time = time.time() - start_time
        
        print(f"✅ Model loaded successfully in {load_time:.2f} seconds.")
        return True
    except ImportError:
        print("❌ faster-whisper module not installed")
        return False
    except Exception as e:
        print(f"❌ Whisper validation failed: {e}")
        return False

def main():
    print("--- STT Environment Validation ---")
    ok = check_whisper()
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
