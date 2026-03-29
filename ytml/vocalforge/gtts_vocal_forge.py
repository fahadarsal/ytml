import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from gtts import gTTS

from ytml.vocalforge.base_vocal_forge import VocalForgeBase
from ytml.vocalforge.voice_cache import VoiceCache
from ytml.utils.logger import logger

PROVIDER_NAME = "gtts"
VOICE_ID = "default"


class gTTSVocalForge(VocalForgeBase):

    def __init__(self, cache=None):
        self.cache = cache or VoiceCache(enabled=False)

    def generate_voiceover(self, text, output_file):
        # ── Check cache first ──────────────────────────────────────────────
        cached = self.cache.lookup(PROVIDER_NAME, VOICE_ID, text)
        if cached:
            shutil.copy2(cached, output_file)
            return output_file

        # ── Generate via gTTS ──────────────────────────────────────────────
        tts = gTTS(text)
        tts.save(output_file)

        # Store in cache for future reuse
        self.cache.store(PROVIDER_NAME, VOICE_ID, text, output_file)
        return output_file

    def process_voiceovers(self, parsed_json: dict, output_dir: str = "tmp/gtts_voiceovers") -> list:
        """
        Generate gTTS voiceovers for all segments in parallel.
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
            f"[gTTS] Generating {len(jobs)} voiceover(s)"
            + (f" — cache: {cache_stats['valid_files']} entries" if cache_stats else "")
        )

        results = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
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
