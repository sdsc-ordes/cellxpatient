from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
FRONTEND_DIR = ROOT / "frontend" / "dist"
DATA_URL = "/data"
HOST = "127.0.0.1"
DEFAULT_PORT = 8008
