#!/usr/bin/env python3
"""
Audio Validation Script for mia_n_eve runtime.
Checks for audio input and output devices.
"""
import sys

def check_sounddevice():
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        default_in = sd.default.device[0]
        default_out = sd.default.device[1]
        
        print("✅ Sounddevice module loaded.")
        print(f"Total audio devices found: {len(devices)}")
        
        if default_in is not None:
            in_device = devices[default_in]
            print(f"✅ Default Input: {in_device['name']} (Channels: {in_device['max_input_channels']})")
        else:
            print("❌ No default input device found.")
            
        if default_out is not None:
            out_device = devices[default_out]
            print(f"✅ Default Output: {out_device['name']} (Channels: {out_device['max_output_channels']})")
        else:
            print("❌ No default output device found.")
            
        return default_in is not None and default_out is not None
    except ImportError:
        print("❌ sounddevice module not installed")
        return False
    except Exception as e:
        print(f"❌ Audio device query failed: {e}")
        return False

def main():
    print("--- Audio Environment Validation ---")
    ok = check_sounddevice()
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
