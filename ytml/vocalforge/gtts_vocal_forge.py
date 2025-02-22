import os
from gtts import gTTS

from ytml.vocalforge.base_vocal_forge import VocalForgeBase


class gTTSVocalForge(VocalForgeBase):

    def generate_voiceover(self, text, output_file):
        tts = gTTS(text)
        tts.save(output_file)
        return output_file

    def process_voiceovers(self, parsed_json: dict, output_dir: str = "tmp/gtts_voiceovers") -> list:
        """
        Generate gtts voiceovers for all text in the parsed JSON.
        """
        os.makedirs(output_dir, exist_ok=True)
        audio_metadata = []

        for segment_idx, segment in enumerate(parsed_json.get("segments", [])):
            for voice_idx, voice in enumerate(segment.get("voiceovers", [])):
                text = voice["text"]
                output_file = os.path.join(
                    output_dir, f"segment{segment_idx+1}_voice{voice_idx+1}.mp3")
                self.generate_voiceover(text, output_file)
                audio_metadata.append({
                    "file": output_file,
                    "start": voice["start"],
                    "end": voice["end"],
                })

        return audio_metadata
