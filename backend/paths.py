import os
from pathlib import Path

IS_HF = bool(os.environ.get("SPACE_ID"))

if IS_HF:
    DATA_ROOT = Path("/data")
else:
    DATA_ROOT = Path(__file__).parent

DB_PATH = DATA_ROOT / "wardrobe.db"
UPLOAD_DIR = DATA_ROOT / "uploads"
CONFIG_FILE = DATA_ROOT / "llm_config.json"
