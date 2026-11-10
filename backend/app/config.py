import os
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(os.getenv("DATA_DIR", "./data"))
DATA.mkdir(parents=True, exist_ok=True)

if os.getenv("OFFLINE_MODELS", "0") == "1":      # NFR-7: no outbound model-hub calls
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

def _secret(name, gen):
    if os.getenv(name.upper()):
        return os.environ[name.upper()]
    p = DATA / f".{name}"
    if not p.exists():
        p.write_text(gen()); p.chmod(0o600)
    return p.read_text().strip()

def _is_private(url):
    h = urlparse(url).hostname or ""
    return (h in {"localhost", "127.0.0.1", "::1", "ollama"} or h.startswith(("10.", "192.168."))
            or any(h.startswith(f"172.{i}.") for i in range(16, 32)))

class Settings:
    EMBED_MODEL = os.getenv("EMBED_MODEL", "pritamdeka/S-PubMedBert-MS-MARCO")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b-instruct")
    CHROMA_PATH = str(DATA / "chroma")
    DB_PATH = str(DATA / "app.db")
    META_PATH = DATA / "index_meta.json"
    CORS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    TOP_K = int(os.getenv("TOP_K", 3))
    MAX_DIST = float(os.getenv("MAX_DIST", 0.55))            # cosine distance cut-off
    GROUND_THRESHOLD = float(os.getenv("GROUND_THRESHOLD", 0.45))  # calibrate on labelled data
    MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", 5))
    MAX_PAGES = int(os.getenv("MAX_PAGES", 40))
    WORKERS = int(os.getenv("GEN_WORKERS", 4))
    TARGET_SECONDS = 30            # NFR-2
    RETRIEVAL_BUDGET_MS = 1000     # NFR-1
    SUS_TARGET = 68                # NFR-8
    SECRET_KEY = _secret("secret_key", lambda: os.urandom(32).hex())
    FERNET_KEY = _secret("fernet_key", lambda: __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode())

settings = Settings()
if not _is_private(settings.OLLAMA_URL) and os.getenv("ALLOW_REMOTE_LLM") != "1":
    raise RuntimeError("NFR-7: OLLAMA_URL must point to a local/private host")
