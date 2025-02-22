import os
import requests
from dotenv import load_dotenv
from ytml.vocalforge.base_vocal_forge import VocalForgeBase

load_dotenv()  # Reads .env file and loads environment variables

# Default fallback if environment variable is missing:
DEFAULT_ELEVEN_LABS_API_KEY = "key"

ELEVEN_LABS_API_KEY = os.getenv(
    "ELEVEN_LABS_API_KEY", DEFAULT_ELEVEN_LABS_API_KEY)
ELEVEN_LABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"


class ElevenLabsVocalForge(VocalForgeBase):
    def __init__(self, voice_id, api_key=None):
        """
        If api_key is provided, use it. Otherwise, read from environment or the default.
        """
        self.api_key = api_key if api_key else ELEVEN_LABS_API_KEY

        if(self.api_key=='key'):
           raise Exception(
            "Invalid Eleven Labs API key. Please set the 'ELEVEN_LABS_API_KEY' environment variable to use Eleven Labs, "
            "or use the '--use-gtts' flag to fall back to Google Text-to-Speech.")

        self.voice_id = voice_id

    def generate_voiceover(self, text, output_file):
        """
        Generate voiceover for the given text and save it to an audio file.
        """
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
        }
        response = requests.post(
            f"{ELEVEN_LABS_URL}/{self.voice_id}", json=payload, headers=headers)

        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            return output_file
        else:
            raise Exception(f"Error generating voice: {response.text}")

    def process_voiceovers(self, parsed_json, output_dir="tmp/xi_voiceovers/1"):
        """
        Process all voiceovers from the parsed JSON.
        """
        os.makedirs(output_dir, exist_ok=True)
        audio_metadata = []

        for segment_idx, segment in enumerate(parsed_json.get("segments", [])):
            for voice_idx, voice in enumerate(segment.get("voiceovers", [])):
                text = voice["text"]
                start = voice["start"]
                end = voice["end"]
                output_file = os.path.join(
                    output_dir, f"segment{segment_idx+1}_voice{voice_idx+1}.mp3")

                self.generate_voiceover(text, output_file)

                audio_metadata.append({
                    "file": output_file,
                    "start": start,
                    "end": end
                })

        return audio_metadata


# Example Usage
if __name__ == "__main__":
    import json

    parsed_json = {
        "segments": [
            {
                "voiceovers": [
                    {"text": "Hello and welcome!", "start": "0.5s", "end": "4.0s"}
                ]
            }
        ]
    }

    # If you set ELEVEN_LABS_API_KEY in .env, it will be read automatically
    forge = ElevenLabsVocalForge()
    metadata = forge.process_voiceovers(parsed_json)
    print(json.dumps(metadata, indent=2))
