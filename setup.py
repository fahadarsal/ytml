from setuptools import setup, find_packages

setup(
    name="ytml",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "ytml=ytml.cli:main",  # This makes `ytml` a command
        ],
    },
    install_requires=[
        "fastapi",
        "uvicorn",
        "websockets",
        "boto3",
        "gtts",
        "pydub",  # Used for audio processing
        "moviepy",  # Used for video processing
        "imageio",  # Required for image/video handling
        "imageio-ffmpeg",  # Supports video encoding/decoding
        "playwright",  # Needed for rendering animations
        "numpy",  # If used in image/video processing
        "requests",  # Required for API requests (e.g., ElevenLabs)
        "python-dotenv",  # If you're using `.env` files for config
        "beautifulsoup4",  # If used for HTML parsing
        "lxml",  # If parsing XML or HTML
        "tqdm",  # If you're showing progress bars
        "pyttsx3",  # If using local TTS
        "starlette",  # Dependency of FastAPI,
        "colorama"
    ],
    python_requires=">=3.7",
)
