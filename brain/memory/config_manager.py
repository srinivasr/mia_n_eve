import os
import sys
import httpx
from pathlib import Path
from dotenv import load_dotenv

from utils.logger import setup_logger
logger = setup_logger(__name__)


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR    = get_base_dir()
# The .env is stored at the root of the mia_n_eve project
ENV_FILE = BASE_DIR.parent / ".env"

# Load the .env file automatically
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)

def ensure_config_dir() -> None:
    pass

def config_exists() -> bool:
    return ENV_FILE.exists()

def get_ollama_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

def get_ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

def is_configured() -> bool:
    url = get_ollama_url()
    try:
        response = httpx.get(f"{url}/api/tags", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False