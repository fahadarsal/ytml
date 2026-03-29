import os
import shutil
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from ytml.vocalforge.base_vocal_forge import VocalForgeBase
from ytml.vocalforge.voice_cache import VoiceCache
from ytml.utils.logger import logger

load_dotenv()

DEFAULT_ELEVEN_LABS_API_KEY = "key"

ELEVEN_LABS_API_KEY = os.getenv(
    "ELEVEN_LABS_API_KEY", DEFAULT_ELEVEN_LABS_API_KEY)
ELEVEN_LABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# ElevenLabs concurrent request limits by plan:
#   Free/Starter = 2,  Creator = 3,  Pro = 5,  Scale = 10
# Default to 2 (safest). Override with ELEVEN_LABS_MAX_CONCURRENT env var.
DEFAULT_MAX_CONCURRENT = 2
MAX_RETRIES = 5
INITIAL_BACKOFF_SECS = 1.0

PROVIDER_NAME = "elevenlabs"


class ElevenLabsVocalForge(VocalForgeBase):
    def __init__(self, voice_id, api_key=None, max_concurrent=None, cache=None):
        self.api_key = api_key if api_key else ELEVEN_LABS_API_KEY

        if self.api_key == 'key':
            raise ValueError(
                "Invalid Eleven Labs API key. Please set the 'ELEVEN_LABS_API_KEY' "
                "environment variable, or use --use-gtts to fall back to Google TTS.")

        self.voice_id = voice_id
        self.max_concurrent = max_concurrent or int(
            os.getenv("ELEVEN_LABS_MAX_CONCURRENT", DEFAULT_MAX_CONCURRENT)
        )
        self.cache = cache or VoiceCache(enabled=False)

    def generate_voiceover(self, text, output_file):
        """
        Generate a single voiceover via the Eleven Labs API.

        Retries automatically on 429 (rate limit) with exponential backoff.
        Other errors are raised immediately.
        """
        # ── Check cache first ──────────────────────────────────────────────
        cached = self.cache.lookup(PROVIDER_NAME, self.voice_id, text)
        if cached:
            shutil.copy2(cached, output_file)
            return output_file

        # ── Call API ───────────────────────────────────────────────────────
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        backoff = INITIAL_BACKOFF_SECS

        for attempt in range(1, MAX_RETRIES + 1):
            response = requests.post(
                f"{ELEVEN_LABS_URL}/{self.voice_id}",
                json={"text": text},
                headers=headers,
            )

            if response.status_code == 200:
                with open(output_file, "wb") as f:
                    f.write(response.content)
                # Store in cache for future reuse
                self.cache.store(PROVIDER_NAME, self.voice_id, text, output_file)
                return output_file

            # ── Rate limited — back off and retry ────────────────────────
            if response.status_code == 429:
                # Prefer the server's Retry-After header if provided
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else backoff

                logger.warning(
                    f"[ElevenLabs] 429 rate-limited (attempt {attempt}/{MAX_RETRIES}) "
                    f"— waiting {wait:.1f}s before retry  "
                    f"[file: {os.path.basename(output_file)}]"
                )
                time.sleep(wait)
                backoff = min(backoff * 2, 30)  # exponential, capped at 30s
                continue

            # ── Any other error — fail immediately ───────────────────────
            self._raise_api_error(response)

        # All retries exhausted on 429
        raise RuntimeError(
            f"[ElevenLabs] Rate limit exceeded after {MAX_RETRIES} retries for "
            f"{os.path.basename(output_file)}. Your plan allows "
            f"{self.max_concurrent} concurrent requests. Either reduce "
            f"the number of voice segments or upgrade your ElevenLabs plan."
        )

    def process_voiceovers(self, parsed_json, output_dir="tmp/xi_voiceovers/1"):
        """
        Generate all voiceovers in parallel using a thread pool.

        Concurrency is capped to self.max_concurrent (default 2) to stay
        within ElevenLabs' per-plan rate limit. Each worker retries
        automatically on 429s with exponential backoff.
        """
        os.makedirs(output_dir, exist_ok=True)

        # Collect all jobs with their original (segment, voice) index for ordering
        jobs = {}
        for segment_idx, segment in enumerate(parsed_json.get("segments", [])):
            for voice_idx, voice in enumerate(segment.get("voiceovers", [])):
                key = (segment_idx, voice_idx)
                output_file = os.path.join(
                    output_dir, f"segment{segment_idx+1}_voice{voice_idx+1}.mp3")
                jobs[key] = (voice["text"], output_file, voice["start"], voice["end"])

        if not jobs:
            return []

        cache_stats = self.cache.stats() if self.cache.enabled else None
        logger.info(
            f"[ElevenLabs] Generating {len(jobs)} voiceover(s) "
            f"(max {self.max_concurrent} concurrent)"
            + (f" — cache: {cache_stats['valid_files']} entries" if cache_stats else " — cache disabled")
        )

        results = {}
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            future_to_key = {
                executor.submit(self.generate_voiceover, text, output_file): (key, output_file, start, end)
                for key, (text, output_file, start, end) in jobs.items()
            }
            for future in as_completed(future_to_key):
                key, output_file, start, end = future_to_key[future]
                future.result()  # raise any exception that occurred
                results[key] = {"file": output_file, "start": start, "end": end}

        # Return in original document order
        return [results[k] for k in sorted(results)]

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _raise_api_error(response):
        """Extract ElevenLabs error detail and raise RuntimeError."""
        try:
            detail = response.json().get("detail", {})
            if isinstance(detail, dict):
                msg = detail.get("message", response.text)
            else:
                msg = detail
        except Exception:
            msg = response.text
        raise RuntimeError(
            f"Eleven Labs API error {response.status_code}: {msg}")
