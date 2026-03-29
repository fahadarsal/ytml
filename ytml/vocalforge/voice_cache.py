"""
Voiceover cache — avoids redundant TTS API calls by caching audio files
keyed on (provider, voice_id, text).

Cache layout
────────────
  {cache_dir}/
  ├── index.json          ← lookup table: hash → metadata
  ├── a1b2c3d4e5f6.mp3
  ├── f6e5d4c3b2a1.mp3
  └── …

index.json schema:
  {
    "<sha256_hex>": {
      "file": "a1b2c3d4e5f6.mp3",
      "provider": "elevenlabs",
      "voice_id": "CwhRBWXzGAHq8TQ4Fs17",
      "text": "Hello, welcome to …",
      "created": "2026-03-28T14:30:00"
    }
  }
"""

import hashlib
import json
import os
import shutil
import threading
from datetime import datetime, timezone

from ytml.utils.logger import logger

DEFAULT_CACHE_DIR = "tmp/voice_cache"


class VoiceCache:
    """Thread-safe, file-system-backed voiceover cache."""

    def __init__(self, cache_dir=None, enabled=True):
        self.enabled = enabled
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._index_path = os.path.join(self.cache_dir, "index.json")
        self._lock = threading.Lock()

        if self.enabled:
            os.makedirs(self.cache_dir, exist_ok=True)

    # ── public API ────────────────────────────────────────────────────────

    def lookup(self, provider, voice_id, text):
        """
        Return the cached file path if a matching voiceover exists, else None.
        """
        if not self.enabled:
            return None

        key = self._cache_key(provider, voice_id, text)
        index = self._read_index()
        entry = index.get(key)

        if entry is None:
            return None

        cached_file = os.path.join(self.cache_dir, entry["file"])
        if not os.path.exists(cached_file):
            # Stale entry — file was deleted
            logger.debug(f"[VoiceCache] Stale entry for key {key[:12]}… — file missing")
            return None

        logger.info(
            f"[VoiceCache] HIT  {key[:12]}…  "
            f"({provider}/{voice_id}) \"{self._preview(text)}\""
        )
        return cached_file

    def store(self, provider, voice_id, text, source_file):
        """
        Copy *source_file* into the cache and record it in the index.
        Returns the path to the cached copy.
        """
        if not self.enabled:
            return source_file

        key = self._cache_key(provider, voice_id, text)
        ext = os.path.splitext(source_file)[1] or ".mp3"
        cached_name = f"{key[:16]}{ext}"
        cached_path = os.path.join(self.cache_dir, cached_name)

        # Copy the generated file into cache
        shutil.copy2(source_file, cached_path)

        entry = {
            "file": cached_name,
            "provider": provider,
            "voice_id": voice_id,
            "text": text,
            "created": datetime.now(timezone.utc).isoformat(),
        }

        self._write_entry(key, entry)

        logger.info(
            f"[VoiceCache] STORE {key[:12]}…  "
            f"({provider}/{voice_id}) \"{self._preview(text)}\""
        )
        return cached_path

    def stats(self):
        """Return a dict with cache statistics."""
        index = self._read_index()
        total = len(index)
        valid = sum(
            1 for e in index.values()
            if os.path.exists(os.path.join(self.cache_dir, e["file"]))
        )
        return {"total_entries": total, "valid_files": valid, "cache_dir": self.cache_dir}

    # ── internals ─────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(provider, voice_id, text):
        """Deterministic hash for a (provider, voice_id, text) triple."""
        raw = f"{provider}:{voice_id}:{text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _read_index(self):
        with self._lock:
            if not os.path.exists(self._index_path):
                return {}
            try:
                with open(self._index_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}

    def _write_entry(self, key, entry):
        with self._lock:
            index = {}
            if os.path.exists(self._index_path):
                try:
                    with open(self._index_path, "r") as f:
                        index = json.load(f)
                except (json.JSONDecodeError, OSError):
                    index = {}
            index[key] = entry
            with open(self._index_path, "w") as f:
                json.dump(index, f, indent=2)

    @staticmethod
    def _preview(text, max_len=50):
        """Truncated text for log messages."""
        return text[:max_len] + "…" if len(text) > max_len else text
