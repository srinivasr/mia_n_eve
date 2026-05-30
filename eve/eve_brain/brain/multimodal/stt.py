import base64
import numpy as np
import scipy.signal
from faster_whisper import WhisperModel

# keep the model in memory globally — loading it is very slow
MODEL_SIZE = "base.en"
print(f"loading faster-whisper model '{MODEL_SIZE}'...")
try:
    model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")
    print("model loaded (cuda).")
except Exception as e:
    print(f"cuda not available ({e}), falling back to cpu...")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    print("model loaded (cpu).")


def process_audio_base64(b64_data: str, sample_rate: int) -> str:
    """Decode base64 f32le audio, resample to 16kHz, transcribe with whisper."""
    try:
        raw_bytes = base64.b64decode(b64_data)
        audio = np.frombuffer(raw_bytes, dtype=np.float32)

        target_sr = 16000
        if sample_rate != target_sr:
            num_samples = int(len(audio) * float(target_sr) / sample_rate)
            audio = scipy.signal.resample(audio, num_samples)

        # no VAD filter here — the rust frontend already handles that
        segments, info = model.transcribe(audio, beam_size=1, language="en")

        text = " ".join([segment.text for segment in segments])
        return text.strip()
    except Exception as e:
        print(f"error processing audio: {e}")
        return ""
