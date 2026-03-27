import argparse
import logging
import os
import sys

# Ensure the local source package takes priority over any installed ytml-toolkit
# version in site-packages. This matters when running cli.py directly from the
# repo rather than from a freshly installed wheel.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from colorama import Fore, Style
except ImportError:
    class _NoColor:
        def __getattr__(self, _): return ""
    Fore = Style = _NoColor()

VERSION = "0.2.13"

HELLO_WORLD_TEMPLATE = """\
<ytml>
  <config>
    FRAME_RATE=30
    VIDEO_WIDTH=1920
    VIDEO_HEIGHT=1088
    ENABLE_AI_VOICE=False
  </config>

  <segment>
    <frame duration="4s">
      <div style="display:flex;justify-content:center;align-items:center;height:100vh;
                  background:linear-gradient(135deg,#1a1a2e,#16213e);font-family:'Segoe UI',sans-serif;">
        <div style="text-align:center;color:#fff;">
          <h1 style="font-size:3.5em;margin:0;animation:fadeIn 1.5s ease-in-out;">Hello, World!</h1>
          <p style="font-size:1.5em;margin-top:15px;color:#e2a428;animation:fadeIn 2.5s ease-in-out;">
            My first YTML video
          </p>
        </div>
      </div>
      <style>
        @keyframes fadeIn {
          0% { opacity:0; transform:translateY(20px); }
          100% { opacity:1; transform:translateY(0); }
        }
      </style>
    </frame>
    <voice start="0.5s" end="4s">Hello, and welcome! This is my first video made with YTML.</voice>
  </segment>

  <segment>
    <frame duration="5s">
      <div style="display:flex;justify-content:center;align-items:center;height:100vh;
                  background:#0f0f0f;font-family:'Segoe UI',sans-serif;">
        <div style="text-align:center;color:#fff;max-width:800px;padding:40px;">
          <h2 style="font-size:2.5em;color:#e2a428;">Why YTML?</h2>
          <ul style="font-size:1.3em;line-height:2;text-align:left;color:#ccc;">
            <li>Write videos like you write code</li>
            <li>AI voiceover built in</li>
            <li>Animations with pure CSS</li>
          </ul>
        </div>
      </div>
    </frame>
    <voice start="0.5s" end="5s">YTML lets you write videos the same way you write code. Fast, repeatable, and expressive.</voice>
  </segment>
</ytml>
"""


def check_elevenlabs_key():
    if not os.getenv("ELEVEN_LABS_API_KEY"):
        print(Fore.YELLOW + "[WARNING] ELEVEN_LABS_API_KEY is not set. "
              "Use --use-gtts or set the key for AI voiceovers." + Style.RESET_ALL)
        return False
    return True


def cmd_init(name):
    """Scaffold a new YTML project."""
    project_dir = name or "my-ytml-video"
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(os.path.join(project_dir, "assets"), exist_ok=True)

    with open(os.path.join(project_dir, "video.ytml"), "w") as f:
        f.write(HELLO_WORLD_TEMPLATE)
    with open(os.path.join(project_dir, ".env"), "w") as f:
        f.write("ELEVEN_LABS_API_KEY=your-api-key-here\n")

    print(Fore.GREEN +
          f"\n✅ Project created at ./{project_dir}/" + Style.RESET_ALL)
    print(f"   📄 video.ytml      — your YTML script")
    print(f"   📁 assets/         — put your images, audio and fonts here")
    print(f"   🔑 .env            — add your Eleven Labs key here\n")
    print(Fore.CYAN + "Next steps:" + Style.RESET_ALL)
    print(f"  cd {project_dir}")
    print(f"  ytml -i video.ytml -o output.mp4 --use-gtts\n")


def main():
    parser = argparse.ArgumentParser(
        description="YTML CLI — turn .ytml scripts into videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  ytml init my-video                           scaffold a new project
  ytml -i video.ytml -o out.mp4 --use-gtts    generate video (free TTS)
  ytml -i video.ytml -o out.mp4               generate video (Eleven Labs AI)
  ytml -i video.ytml --preview                preview HTML structure
  ytml --resume <uuid>                         resume a stopped job
        """
    )
    parser.add_argument("command", nargs="?", help="Subcommand: init")
    parser.add_argument("init_name", nargs="?", help="Project name for `init`")
    parser.add_argument("-i", "--input", help="Path to the YTML input file.")
    parser.add_argument(
        "-o", "--output", default="output_video.mp4", help="Output video file.")
    parser.add_argument("--use-gtts", action="store_true",
                        help="Use gTTS instead of Eleven Labs (free, no API key needed).")
    parser.add_argument("--skip", nargs="*", choices=[
                        "parse", "voiceover", "render", "sync", "compose"], help="Steps to skip.")
    parser.add_argument(
        "--resume", help="Resume a job using the provided UUID.")
    parser.add_argument(
        "--job", help="Job ID of voiceovers to reuse. Requires --skip voiceover.")
    parser.add_argument("--preview", action="store_true",
                        help="Preview HTML only (no video generated).")
    parser.add_argument("--version", action="store_true",
                        help="Show CLI version.")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable detailed logging.")

    args = parser.parse_args()

    # ── Commands that need zero heavy dependencies ─────────────────────────────

    if args.version:
        print(Fore.CYAN + f"YTML CLI v{VERSION}" + Style.RESET_ALL)
        sys.exit(0)

    if args.command == "init":
        cmd_init(args.init_name)
        return

    # ── Require an input file for everything below ─────────────────────────────
    if args.resume is None and not args.input:
        print(
            Fore.RED + "[ERROR] No input file provided. Use -i <file.ytml>" + Style.RESET_ALL)
        print(Fore.YELLOW + "Tip: run `ytml init my-video` to scaffold a starter project." + Style.RESET_ALL)
        parser.print_help()
        return

    if args.input and not os.path.exists(args.input):
        print(
            Fore.RED + f"[ERROR] Input file '{args.input}' not found." + Style.RESET_ALL)
        return

    # ── Preview — only needs the parser + preprocessor (no heavy deps) ─────────
    if args.preview:
        from ytml.utils.config import get_config_from_file
        from ytml.interpretron.parser import YTMLParser
        from ytml.animagic.html_preprocesor import HtmlPreprocessor

        config = get_config_from_file(args.input)
        parsed = YTMLParser(args.input).parse()
        html = HtmlPreprocessor(config).preview(parsed)
        with open("preview.html", "w") as f:
            f.write(html)
        print(Fore.GREEN + "✅ Preview written to preview.html now" + Style.RESET_ALL)
        return

    # ── Full pipeline — needs all dependencies ─────────────────────────────────
    from ytml.utils.logger import logger
    from ytml.utils.config import Config, get_config_from_file
    from ytml.conductor.conductor import Conductor

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    # Resume a stopped job
    if args.resume:
        job_dir = f"tmp/{args.resume}"
        if not os.path.exists(job_dir):
            print(
                Fore.RED + f"[ERROR] No job found with UUID {args.resume}." + Style.RESET_ALL)
            return
        print(Fore.BLUE +
              f"[INFO] Resuming job {args.resume}..." + Style.RESET_ALL)
        conductor = Conductor(
            None, args.output, config=Config(), job_id=args.resume)
        status = conductor.get_job_status()
        skip_steps = [stage for stage in ["parse", "voiceover",
                                          "render", "sync"] if status.get(f"{stage}.json")]
        conductor.run_workflow(f"{job_dir}/parsed.json", skip_steps)
        return

    config = get_config_from_file(args.input)

    from ytml.vocalforge.gtts_vocal_forge import gTTSVocalForge
    from ytml.vocalforge.xi_labs_vocal_forge import ElevenLabsVocalForge

    if not args.use_gtts and config.ENABLE_AI_VOICE:
        if not check_elevenlabs_key():
            print(
                Fore.YELLOW + "Falling back to gTTS. Use --use-gtts to suppress this message." + Style.RESET_ALL)
            args.use_gtts = True

    vocal_forge = gTTSVocalForge(
    ) if args.use_gtts or not config.ENABLE_AI_VOICE else ElevenLabsVocalForge(config.AI_VOICE_ID)
    conductor = Conductor(vocal_forge, args.output, config=config)
    conductor.run_workflow(
        args.input, skip_steps=args.skip or [], job=args.job)


if __name__ == "__main__":
    main()
