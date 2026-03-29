import io
import os
import shutil
import tempfile
import numpy
from PIL import Image
from playwright.sync_api import sync_playwright
from imageio import get_writer
from ytml.animagic.html_preprocesor import HtmlPreprocessor
from ytml.animagic.video_processor import VideoProcessor
from ytml.utils.ffmpeg_wizard import FFMpegWizard, _q
from ytml.utils.logger import logger
from ytml.utils.config import Config


def _png_to_array(png_bytes):
    return numpy.array(Image.open(io.BytesIO(png_bytes)))


class Animagic:
    def __init__(self, config: Config, output_dir="tmp/renders"):
        self.output_dir = output_dir
        self.config = config
        os.makedirs(self.output_dir, exist_ok=True)
        self.preprocessor = HtmlPreprocessor(config=self.config)

    def _setup_page(self, browser_or_context, html_content):
        """
        Shared helper to initialise a browser page with HTML content.
        Waits for networkidle so CDN scripts (Mermaid, Prism) are loaded.

        Accepts either a Browser or a BrowserContext.
        """
        page = browser_or_context.new_page()
        page.set_viewport_size(
            {"width": self.config.VIDEO_WIDTH, "height": self.config.VIDEO_HEIGHT}
        )
        page.set_content(html_content, wait_until="networkidle")

        if "<mermaid" in html_content:
            page.wait_for_function(
                "document.querySelectorAll('.mermaid svg').length > 0",
                timeout=10000,
            )

        if "<code" in html_content:
            page.wait_for_function("window.Prism !== undefined", timeout=10000)
            page.wait_for_timeout(200)

        return page

    # ── Static frame rendering (unchanged — single screenshot) ───────────

    def render_frame(self, browser, html_content):
        """
        Render a single static frame and return a numpy array.
        """
        page = self._setup_page(browser, html_content)
        png_bytes = page.screenshot()
        page.close()
        return _png_to_array(png_bytes)

    # ── Animated frame rendering via Playwright video recording ──────────

    def _render_animated_segment_via_recording(self, browser, html_content, video_file, frame_rate, duration):
        """
        Capture an animated HTML segment using Playwright's built-in video
        recording instead of per-frame screenshots.

        Chrome records the page natively in its compositor thread — zero
        per-frame IPC overhead.  The resulting webm is converted to mp4 via
        FFmpeg in a single fast pass.

        Typical speedup: 2-3× for a 5 s segment at 30 fps (screenshot
        overhead of ~10 s is eliminated; only the real-time animation
        duration + a sub-second FFmpeg transcode remains).
        """
        rec_dir = tempfile.mkdtemp(prefix="ytml_rec_")

        try:
            # Create a recording context on the shared browser
            context = browser.new_context(
                viewport={
                    "width": self.config.VIDEO_WIDTH,
                    "height": self.config.VIDEO_HEIGHT,
                },
                record_video_dir=rec_dir,
                record_video_size={
                    "width": self.config.VIDEO_WIDTH,
                    "height": self.config.VIDEO_HEIGHT,
                },
            )

            page = context.new_page()
            page.set_content(html_content, wait_until="networkidle")

            # Wait for CDN scripts the same way _setup_page does
            if "<mermaid" in html_content:
                page.wait_for_function(
                    "document.querySelectorAll('.mermaid svg').length > 0",
                    timeout=10000,
                )
            if "<code" in html_content:
                page.wait_for_function("window.Prism !== undefined", timeout=10000)
                page.wait_for_timeout(200)
                # Adjust duration for code-block typewriter animations
                spans_count = page.evaluate(
                    "document.querySelectorAll('.token').length")
                calculated_duration = (
                    spans_count * self.config.ANIMATION_DELAY) / 1000
                if duration < calculated_duration:
                    duration = calculated_duration

            logger.debug(
                f"[Animagic] Recording {duration:.2f}s animation "
                f"({self.config.VIDEO_WIDTH}×{self.config.VIDEO_HEIGHT})"
            )

            # Let the animation play in real time — Chrome records natively
            page.wait_for_timeout(duration * 1000)

            # Grab the path *before* closing the context
            webm_path = page.video.path()
            context.close()          # flushes the video file to disk

            # Convert webm → mp4 at the target frame rate
            FFMpegWizard.run_command(
                f"ffmpeg -y -i {_q(webm_path)} "
                f"-r {frame_rate} -c:v libx264 -preset fast -crf 18 "
                f"{_q(video_file)}"
            )
        finally:
            shutil.rmtree(rec_dir, ignore_errors=True)

    # ── Fallback: screenshot loop (for edge cases / debugging) ───────────

    def _render_animated_frames_to_writer(self, browser, html_content, writer, frame_rate, duration):
        """
        Legacy screenshot-per-frame capture.  Kept as a fallback — the
        default path now uses ``_render_animated_segment_via_recording``.
        """
        page = self._setup_page(browser, html_content)

        if "<code" in html_content:
            spans_count = page.evaluate(
                "document.querySelectorAll('.token').length")
            calculated_duration = (
                spans_count * self.config.ANIMATION_DELAY) / 1000
            if duration < calculated_duration:
                duration = calculated_duration

        frame_count = int(duration * frame_rate)
        interval = duration / frame_count

        for _ in range(frame_count):
            png_bytes = page.screenshot()
            writer.append_data(_png_to_array(png_bytes))
            page.wait_for_timeout(interval * 1000)

        page.close()

    # ── Main entry point ─────────────────────────────────────────────────

    def process_frames(self, parsed_json):
        """
        Render frames for each segment directly into mp4 files.

        A single Playwright browser is launched once and shared across all
        segments.  Animated ``<frame>`` segments use native video recording
        (no per-frame screenshots).  ``<video>`` overlay segments use the
        shared browser for transparent-PNG capture at a configurable
        ``OVERLAY_FRAME_RATE`` (default 10 fps).
        """
        segment_videos = []
        segments = parsed_json.get("segments", [])

        # We always need a browser — HTML frames use recording, overlays
        # use screenshot capture.  Only skip for empty projects.
        needs_browser = len(segments) > 0

        with sync_playwright() as p:
            browser = p.chromium.launch() if needs_browser else None
            try:
                for segment_idx, segment in enumerate(segments):
                    logger.info(f"Processing segment {segment_idx + 1}...")
                    video_file = os.path.join(
                        self.output_dir, f"segment_{segment_idx + 1}.mp4")

                    # ── <video> segments → VideoProcessor ────────────
                    if segment.get("video_source"):
                        processor = VideoProcessor(self.preprocessor)
                        processor.process(
                            segment, video_file, self.config,
                            browser=browser,
                        )
                        segment_videos.append(video_file)
                        continue

                    # ── <frame> segments ─────────────────────────────
                    frame_rate = int(segment['frame_rate'] or self.config.FRAME_RATE)
                    has_animation = not segment['static']

                    if has_animation:
                        for frame in segment.get("frames", []):
                            html_content = self.preprocessor.preprocess(
                                frame, segment.get("styles", ""), include_animations=True)
                            self._render_animated_segment_via_recording(
                                browser, html_content, video_file,
                                frame_rate, segment['duration'],
                            )
                    else:
                        frame_arrays = []
                        for frame in segment.get("frames", []):
                            html_content = self.preprocessor.preprocess(
                                frame, segment.get("styles", ""), include_animations=False)
                            frame_arrays.append(self.render_frame(browser, html_content))
                        VideoComposer(frame_rate).create_video(frame_arrays, video_file)

                    segment_videos.append(video_file)
            finally:
                if browser:
                    browser.close()

        return segment_videos


class VideoComposer:
    def __init__(self, frame_rate):
        self.frame_rate = frame_rate

    def create_video(self, frames, output_file):
        """
        Combine numpy frame arrays into a video file.
        frames: list of numpy arrays (H x W x C).
        """
        writer = get_writer(output_file, fps=self.frame_rate)
        for frame in frames:
            writer.append_data(frame)
        writer.close()
        logger.info(f"Video saved to {output_file}")
