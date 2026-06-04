from __future__ import annotations

import base64
import io
import json
import sys
import threading
import time
from pathlib import Path

import numpy as np

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

try:
    import mss
    import mss.tools
    _MSS = True
except ImportError:
    _MSS = False

try:
    import PIL.Image
    _PIL = True
except ImportError:
    _PIL = False


from utils.logger import setup_logger
logger = setup_logger(__name__)


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE        = _base_dir()
_CONFIG_PATH = _BASE / "config" / "api_keys.json"


def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_config_key(key: str, value) -> None:
    try:
        cfg = _load_config()
        cfg[key] = value
        _CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    except Exception as e:
        logger.info(f"Could not save config key '{key}': {e}")


def _get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not found in env.")
    return key


def _get_os() -> str:
    return _load_config().get("os_system", "windows").lower()

_LIVE_MODEL         = "models/gemini-2.5-flash-native-audio-preview-12-2025"
_CHANNELS           = 1
_RECEIVE_SAMPLE_RATE = 24_000
_CHUNK_SIZE         = 1_024

_IMG_MAX_W = 640
_IMG_MAX_H = 360
_JPEG_Q    = 60

_SYSTEM_PROMPT = (
    "You are MIA, an advanced AI assistant. "
    "Analyze the provided image with precision and intelligence. "
    "Be concise and direct — maximum two sentences unless the user's question "
    "requires more detail. "
    "Address the user respectfully. "
    "Always call the appropriate tool; never simulate results."
)


def _compress(img_bytes: bytes, source_format: str = "PNG") -> tuple[bytes, str]:
    if not _PIL:
        return img_bytes, f"image/{source_format.lower()}"

    try:
        img = PIL.Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q, optimize=False)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        logger.exception("Operation failed")
        return img_bytes, f"image/{source_format.lower()}"

def _capture_screen() -> tuple[bytes, str]:
    import os
    if _get_os() == "linux" and os.environ.get("XDG_SESSION_TYPE") == "wayland":
        import subprocess
        try:
            result = subprocess.run(
                ["gdbus", "call", "--session", "--dest", "org.gnome.Shell.Screenshot", 
                 "--object-path", "/org/gnome/Shell/Screenshot", "--method", "org.gnome.Shell.Screenshot.Screenshot", 
                 "true", "false", "/tmp/mia_screenshot.png"],
                capture_output=True, text=True, check=True
            )
            import re
            match = re.search(r"'(.*?)'", result.stdout)
            if match:
                filepath = match.group(1)
                with open(filepath, "rb") as f:
                    img_bytes = f.read()
                try:
                    os.remove(filepath)
                except Exception:
                    pass
                return _compress(img_bytes, "PNG")
        except Exception:
            logger.exception("Operation failed")

    if not _MSS:
        raise RuntimeError("mss is not installed. Run: pip install mss")

    with mss.mss() as sct:
        monitors = sct.monitors          # [0] = all combined, [1..n] = real screens
        target   = monitors[1] if len(monitors) > 1 else monitors[0]
        shot     = sct.grab(target)
        png      = mss.tools.to_png(shot.rgb, shot.size)

    return _compress(png, "PNG")


def _cv2_backend() -> int:
    """Return the best OpenCV camera backend for the current OS."""
    if not _CV2:
        return 0
    os_name = _get_os()
    if os_name == "windows":
        return cv2.CAP_DSHOW    
    if os_name == "mac":
        return cv2.CAP_AVFOUNDATION  
    return cv2.CAP_ANY


def _probe_camera(index: int, backend: int, warmup: int = 5) -> bool:

    if not _CV2:
        return False
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        cap.release()
        return False
    for _ in range(warmup):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        return False
    return bool(np.mean(frame) > 8)


def _detect_camera_index() -> int:

    backend = _cv2_backend()
    logger.info("Auto-detecting camera...")
    for idx in range(6):
        if _probe_camera(idx, backend):
            logger.info(f"Camera found at index {idx}")
            _save_config_key("camera_index", idx)
            return idx
        logger.info(f"Camera index {idx}: no usable frame")

    logger.info("No camera found — defaulting to index 0")
    _save_config_key("camera_index", 0)
    return 0


def _get_camera_index() -> int:
    cfg = _load_config()
    if "camera_index" in cfg:
        return int(cfg["camera_index"])
    return _detect_camera_index()


def _capture_camera() -> tuple[bytes, str]:
    if not _CV2:
        raise RuntimeError("OpenCV (cv2) is not installed. Run: pip install opencv-python")

    index   = _get_camera_index()
    backend = _cv2_backend()
    cap     = cv2.VideoCapture(index, backend)

    if not cap.isOpened():
        raise RuntimeError(f"Camera index {index} could not be opened.")

    for _ in range(10):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError("Camera returned no frame.")

    if _PIL:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(rgb)
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q)
        return buf.getvalue(), "image/jpeg"

    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_Q])
    return buf.tobytes(), "image/jpeg"

class _VisionSession:
    def __init__(self):
        self._player = None

    def start(self, player=None, timeout: float = 25.0) -> None:
        if player is not None:
            self._player = player

    def analyze(self, image_bytes: bytes, mime_type: str, user_text: str) -> None:
        def run():
            import ollama
            from memory.config_manager import get_ollama_url, get_ollama_model
            
            client = ollama.Client(host=get_ollama_url())
            
            b64 = base64.b64encode(image_bytes).decode("ascii")
            
            prompt = _SYSTEM_PROMPT + "\n\nUser: " + user_text
            
            try:
                response = client.chat(
                    model=get_ollama_model(),
                    messages=[{
                        "role": "user",
                        "content": prompt,
                        "images": [b64]
                    }]
                )
                text = response.get("message", {}).get("content", "").strip()
                if text and self._player:
                    self._player.write_log(f"MIA: {text}")
                    logger.info(text)
            except Exception:
                logger.exception("An error occurred")
                
        threading.Thread(target=run, daemon=True).start()

_session      = _VisionSession()
_session_lock = threading.Lock()
_session_up   = False


def _ensure_session(player=None) -> None:
    global _session_up
    with _session_lock:
        if not _session_up:
            _session.start(player=player)
            _session_up = True
        elif player is not None:
            _session._player = player


def screen_process(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> bool:

    params    = parameters or {}
    user_text = (params.get("text") or params.get("user_text") or "").strip()
    angle     = params.get("angle", "screen").lower().strip()

    if not user_text:
        logger.info("No question provided — aborting")
        return False

    logger.info(f"angle={angle!r}  question='{user_text[:80]}'")

    try:
        _ensure_session(player=player)
    except Exception as e:
        logger.info(f"Could not start session: {e}")
        return False

    try:
        if angle == "camera":
            image_bytes, mime_type = _capture_camera()
            logger.info(f"Camera: {len(image_bytes):,} bytes")
        else:
            image_bytes, mime_type = _capture_screen()
            logger.info(f"Screen: {len(image_bytes):,} bytes")
    except Exception:
        logger.exception("An error occurred")
        return False

    _session.analyze(image_bytes, mime_type, user_text)
    return True


def warmup_session(player=None) -> None:
    try:
        _ensure_session(player=player)
    except Exception:
        logger.exception("Operation failed")

if __name__ == "__main__":
    logger.info("screen_processor.py")
    logger.info("=" * 52)
    mode = input("angle — screen / camera (default: screen): ").strip().lower() or "screen"
    q    = input("Question (Enter = default): ").strip() or "What do you see? Be brief."

    t0 = time.perf_counter()
    warmup_session()
    logger.info(f"Session ready in {time.perf_counter()-t0:.2f}s\n")

    t1 = time.perf_counter()
    ok = screen_process({"angle": mode, "text": q})
    logger.info(f"Queued in {time.perf_counter()-t1:.3f}s — waiting for audio...")
    time.sleep(10)
    logger.info("Done." if ok else "Failed.")