from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
