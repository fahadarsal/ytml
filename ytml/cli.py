import argparse
import os
import sys
from ytml.vocalforge.xi_labs_vocal_forge import ElevenLabsVocalForge
from ytml.vocalforge.gtts_vocal_forge import gTTSVocalForge
from ytml.conductor.conductor import Conductor
from ytml.utils.config import get_config_from_file
from tqdm import tqdm  
from colorama import Fore, Style 

VERSION = "0.1.0" 

def check_elevenlabs_key():
    """Check if ELEVEN_LABS_API_KEY is set, warn if missing."""
    if not os.getenv("ELEVEN_LABS_API_KEY"):
        print(Fore.YELLOW + "[WARNING] ELEVEN_LABS_API_KEY is not set. "
              "Use --use-gtts or define the API key for Eleven Labs." + Style.RESET_ALL)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="YTML CLI - Video Generation Compiler")
    parser.add_argument("-i", "--input", help="Path to the YTML input file.")
    parser.add_argument("-o", "--output", default="output_video.mp4", help="Output video file.")
    parser.add_argument("--use-gtts", action="store_true", help="Use gTTS VocalForge instead of Eleven Labs.")
    parser.add_argument("--skip", nargs="*", choices=["parse", "voiceover", "render", "sync", "compose"], help="Steps to skip.")
    parser.add_argument("--resume", help="Resume a job using the provided UUID.")
    parser.add_argument("--job", help="Job ID of voiceovers to mix. Requires --skip voiceover.")
    parser.add_argument("--preview", action="store_true", help="Preview HTML only.")
    parser.add_argument("--version", action="store_true", help="Show CLI version.")

    args = parser.parse_args()

    # ✅ Handle version and help
    if args.version:
        print(Fore.CYAN + f"YTML CLI Version: {VERSION}" + Style.RESET_ALL)
        sys.exit(0)

    # ✅ Check if Eleven Labs API Key is missing
    if not args.use_gtts:
        if not check_elevenlabs_key():
            return

    config = get_config_from_file(args.input)

    if args.preview:
        conductor = Conductor(None, args.output, config)
        conductor.previewHTML(args.input)
        return

    if args.resume:
        job_dir = f"tmp/{args.resume}"
        if not os.path.exists(job_dir):
            print(Fore.RED + f"[ERROR] No job found with UUID {args.resume}." + Style.RESET_ALL)
            return

        print(Fore.BLUE + f"[INFO] Resuming job with UUID {args.resume}..." + Style.RESET_ALL)
        conductor = Conductor(None, args.output, job_id=args.resume)
        status = conductor.get_job_status()

        skip_steps = [stage for stage in ["parse", "voiceover", "render", "sync"] if status.get(f"{stage}.json")]
        conductor.run_workflow(f"{job_dir}/parsed.json", skip_steps)
        return

    if not os.path.exists(args.input):
        print(Fore.RED + f"[ERROR] Input file '{args.input}' not found." + Style.RESET_ALL)
        return
    vocal_forge = gTTSVocalForge() if args.use_gtts or config.ENABLE_AI_VOICE == False else ElevenLabsVocalForge(config.AI_VOICE_ID)
    conductor = Conductor(vocal_forge, args.output, config=config)
    conductor.run_workflow(args.input, skip_steps=args.skip or [], job=args.job)


if __name__ == "__main__":
    main()
