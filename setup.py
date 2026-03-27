import sys
import subprocess
from setuptools import setup, find_packages
from setuptools.command.install import install


class PostInstallCommand(install):
    """Install Playwright browser after package install."""

    def run(self):
        install.run(self)
        subprocess.run(["python", "-m", "ytml.post_install"], check=False)


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

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ytml-toolkit",
    version="0.4.0",
    author="Fahad Arsal",
    author_email="",
    description="Turn .ytml scripts into production-ready videos — code-driven video automation.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://ytml.mergeconflict.tech/",
    project_urls={
        "Documentation": "https://ytml.mergeconflict.tech/docs/intro",
        "Source": "https://github.com/fahadarsal/ytml",
        "Bug Tracker": "https://github.com/fahadarsal/ytml/issues",
    },
    packages=find_packages(include=["ytml", "ytml.*"]),
    package_data={"ytml": ["assets/**/*", "assets/*"]},
    entry_points={
        "console_scripts": [
            "ytml=ytml.cli:main",
        ],
    },
    install_requires=install_requires,
    python_requires=">=3.8",
    cmdclass={"install": PostInstallCommand},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords="video automation youtube markup language tts voiceover animation ffmpeg playwright",
)
