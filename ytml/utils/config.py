from dataclasses import dataclass
from dataclasses import replace
import json
import re
# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
#     from dataclasses import dataclass
# else:
#     from pydantic.dataclasses import dataclass


@dataclass
class Config:
    # Basic Configuration
    FRAME_RATE: int = 30  # Frames per second
    # TODO: Implement Default Music
    DEFAULT_TRANSITION_MUSIC: str = "uplifting-beat.mp3"  # Default transition sound
    ANIMATION_SPEED: str = "1s"  # Default animation duration
    IMAGE_DURATION: str = "5s"  # Default display time for images
    ANIMATION_DELAY = 50
    MERMAID_THEME = 'dark'

    # Video Output Settings
    VIDEO_HEIGHT: str = 1080  # Video resolution (width x height)
    VIDEO_WIDTH: str = 1920
    OUTPUT_FORMAT: str = "mp4"  # Format for the exported video
    BITRATE: str = "5000k"  # Video bitrate (affects quality and file size)
    AUDIO_SAMPLE_RATE: int = 44100  # Audio sample rate in Hz

    # Transition and Animation Defaults
    DEFAULT_TRANSITION_EFFECT: str = "fade"  # Default transition effect

    # AI and Automation
    ENABLE_AI_VOICE: bool = True  # Whether to use AI-generated voiceovers
    AI_VOICE_ID: str = "yDUXXKsu0jF5vdJnWAPU"  # Style for AI-generated voices
    # Enable AI-generated visuals (e.g., imagine tag)
    ENABLE_AI_GENERATION: bool = False
    AI_IMAGE_STYLE: str = "3D"  # Style for AI-generated images or videos

    # Debugging and Development
    DEBUG_MODE: bool = False  # Enable debug logs
    LOG_LEVEL: str = "INFO"  # Log level (DEBUG, INFO, WARN, ERROR)

    # Experimental Features
    EXPERIMENTAL_DYNAMIC_SPEED: bool = False  # Dynamic animation speed adjustment
    EXPERIMENTAL_VOICE_CLONING: bool = False  # Voice cloning for custom narrations

    HTML_ASSETS = {
        "css": [
            "css/merge_conflict_styles.css",
        ],
        "js": [
            "js/mermaid_init.js",
            "js/prism.js",
        ],
        "animations": [
            "js/typewriter_effect.js",
        ]
    }


def get_config_from_file(file_path: str, default_config=Config()):
    """
    Manually reads the <config> section from a YTML file and updates the default config.

    Args:
        file_path (str): Path to the YTML file.
        default_config (Config): The default Config dataclass instance.

    Returns:
        Config: Updated Config dataclass instance.
    """
    with open(file_path, "r") as file:
        content = file.read()

    # Extract <config> tag manually
    match = re.search(r"<config>(.*?)</config>", content, re.DOTALL)
    if not match:
        return default_config

    config_content = match.group(1).strip()
    updates = {}

    # Parse key-value pairs in the <config> content
    for line in config_content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):  # Skip empty lines and comments
            continue

        # Parse key-value pairs
        if "=" in line:
            key, value = [item.strip() for item in line.split("=", 1)]
            if hasattr(default_config, key):
                current_value = getattr(default_config, key)
                if key == "HTML_ASSETS":
                    try:
                        # Convert single quotes to double for JSON parsing
                        value = json.loads(value.replace("'", '"'))
                    except json.JSONDecodeError:
                        raise ValueError(
                            f"Invalid JSON format for {key}: {value}")
                if isinstance(current_value, bool):
                    value = value.lower() in ("true", "1", "yes")
                elif isinstance(current_value, int):
                    value = int(value)
                elif isinstance(current_value, float):
                    value = float(value)
                updates[key] = value

    # Update the default config with parsed values
    print(updates)
    # ✅ Apply updates manually instead of using `replace()`
    for key, value in updates.items():
        setattr(default_config, key, value)
    # updated_config = replace(default_config, **updates)
    # return updated_config
    # return default_config.__class__(**{**default_config.__dict__, **updates})
    return default_config
