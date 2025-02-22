from abc import ABC, abstractmethod


class VocalForgeBase(ABC):
    @abstractmethod
    def generate_voiceover(self, text: str, output_file: str) -> str:
        """
        Generate a voiceover for the given text and save it to an audio file.
        """
        pass

    @abstractmethod
    def process_voiceovers(self, parsed_json: dict, output_dir: str = "voiceovers") -> list:
        """
        Process all voiceovers from the parsed JSON and generate audio files.
        """
        pass
