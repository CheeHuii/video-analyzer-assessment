# backend/attachments_store.py
import os
import uuid
from pathlib import Path

ATTACH_DIR = Path("data/attachments")
ATTACH_DIR.mkdir(parents=True, exist_ok=True)

def save_attachment_bytes(filename: str, content_bytes: bytes) -> str:
    # create unique name to avoid collisions
    ext = Path(filename).suffix or ".bin"
    uid = uuid.uuid4().hex
    target = ATTACH_DIR / f"{uid}{ext}"
    with open(target, "wb") as f:
        f.write(content_bytes)
    # return POSIX path string
    return str(target)
