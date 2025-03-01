import sys
from setuptools.command.install import install
import subprocess
from setuptools import setup, find_packages
class PostInstallCommand(install):
    """Post-installation for Playwright browser"""
    def run(self):
        install.run(self)
        subprocess.run(["python", "-m", "ytml.post_install"], check=False)

# Conditionally add `audioop-lts` only for Python >3.10
install_requires = [
    "fastapi",
    "uvicorn",
    "websockets",
    "boto3",
    "gtts",
    "pydub",
    "moviepy",
    "imageio",
    "imageio-ffmpeg",
    "playwright",
    "numpy",
    "requests",
    "python-dotenv",
    "beautifulsoup4",
    "lxml",
    "tqdm",
    "pyttsx3",
    "starlette",
    "colorama",
    "audioop-lts;python_version>'3.11'",
]

setup(
    name="ytml-toolkit",
    version="0.2.0",
    packages=find_packages(include=["ytml", "ytml.*"]),
    entry_points={
        "console_scripts": [
            "ytml=ytml.cli:main",  # ✅ CLI command
        ],
    },
    install_requires=install_requires,  # ✅ Dynamic dependencies
    python_requires=">=3.7",
    cmdclass={"install": PostInstallCommand},  # ✅ Run post-install script
)
