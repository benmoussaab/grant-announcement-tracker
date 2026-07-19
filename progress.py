"""
progress.py
Tracks which image URLs have already been processed, and which monthly
date-range chunks have been fully completed — so an interrupted backfill
(quota exhaustion, crash, manual stop) can resume safely without
re-processing already-handled data.
"""

import json
from config import PROGRESS_FILE


def load_progress():
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("failed_downloads", [])
            return data
    except FileNotFoundError:
        return {"processed_image_urls": [], "completed_chunks": [], "failed_downloads": []}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False)
