import os

from ytml.animagic.html_preprocesor import HtmlPreprocessor
from ytml.utils.ffmpeg_wizard import FFMpegWizard
from ytml.utils.logger import logger
from ytml.utils.config import Config


class VideoProcessor:
    """
    Handles rendering of segments that use the <video> tag.

    Pipeline:
      1. Trim source video to clip_start..clip_end  (FFmpeg stream copy)
      2. Adjust playback speed                       (FFmpeg re-encode)
      2.5 Normalize resolution to VIDEO_WIDTH×VIDEO_HEIGHT
      3. If overlay HTML present:
           a. Render overlay as transparent PNG frame sequence (Playwright)
           b. Composite frame sequence onto video    (FFmpeg overlay filter)
    """

    def __init__(self, preprocessor: HtmlPreprocessor):
        self.preprocessor = preprocessor

    def process(self, segment, output_path, config: Config, browser=None):
        """
        Produce a video file at *output_path* from the segment's video_source.

        *browser* is an optional already-open Playwright Browser instance.
        When provided the overlay renderer reuses it instead of launching a
        new ``sync_playwright()`` context (which would fail inside a thread
        pool because Playwright's sync API can't nest in an asyncio loop).
        """
        vs = segment["video_source"]
        src = vs["src"]
        clip_start = vs["clip_start"]
        clip_end = vs.get("clip_end")
        speed = vs["speed"]
        overlay_html = vs.get("overlay_html", "").strip()
        frame_rate = int(segment.get("frame_rate") or config.FRAME_RATE)

        logger.debug(
            f"[VideoProcessor] segment video_source:\n"
            f"  src         = {src}\n"
            f"  clip_start  = {clip_start}s\n"
            f"  clip_end    = {clip_end}s  (None = full video)\n"
            f"  speed       = {speed}x\n"
            f"  frame_rate  = {frame_rate} fps\n"
            f"  overlay_html present = {bool(overlay_html)} "
            f"({len(overlay_html)} chars)\n"
            f"  output      = {output_path}\n"
            f"  overlay render size = {config.VIDEO_WIDTH}×{config.VIDEO_HEIGHT}px"
        )

        if not os.path.exists(src):
            raise FileNotFoundError(
                f"[VideoProcessor] Source video not found: {src!r}. "
                f"Make sure the path is relative to your project directory."
            )

        src_duration = FFMpegWizard.get_video_duration(src)
        logger.debug(f"[VideoProcessor] Source video duration = {src_duration:.3f}s")

        work_dir = os.path.dirname(output_path)
        base = os.path.splitext(os.path.basename(output_path))[0]

        # ── Step 1: trim ──────────────────────────────────────────────────
        if clip_end is None:
            clip_end = src_duration
            logger.debug(f"[VideoProcessor] No end specified — using full source duration: {clip_end:.3f}s")

        if clip_end > src_duration:
            logger.warning(
                f"[VideoProcessor] clip end ({clip_end}s) exceeds source duration "
                f"({src_duration:.3f}s) — clamping to source length. "
                f"The output will be {(src_duration - clip_start):.3f}s, not {(clip_end - clip_start):.3f}s."
            )
            clip_end = src_duration

        needs_trim = clip_start > 0 or clip_end < src_duration
        if needs_trim:
            trimmed = os.path.join(work_dir, f"{base}_trimmed.mp4")
            logger.info(f"[VideoProcessor] Trimming [{clip_start}s → {clip_end}s] from {src}")
            FFMpegWizard.trim_video(src, clip_start, clip_end, trimmed)
            trimmed_dur = FFMpegWizard.get_video_duration(trimmed)
            logger.debug(f"[VideoProcessor] Trimmed video duration = {trimmed_dur:.3f}s")
        else:
            trimmed = src
            logger.debug("[VideoProcessor] No trim needed (full video selected)")

        # ── Step 2: speed ─────────────────────────────────────────────────
        if speed != 1.0:
            sped = os.path.join(work_dir, f"{base}_sped.mp4")
            has_audio = FFMpegWizard.has_audio_stream(trimmed)
            logger.info(
                f"[VideoProcessor] Adjusting speed ×{speed} "
                f"(source has audio: {has_audio})"
            )
            FFMpegWizard.change_speed(trimmed, speed, sped)
            sped_dur = FFMpegWizard.get_video_duration(sped)
            logger.debug(f"[VideoProcessor] Speed-adjusted video duration = {sped_dur:.3f}s")
        else:
            sped = trimmed
            logger.debug("[VideoProcessor] No speed change (speed=1.0)")

        # ── Step 2.5: normalize resolution ────────────────────────────────
        src_w, src_h = FFMpegWizard.get_video_dimensions(sped)
        target_w, target_h = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
        if src_w != target_w or src_h != target_h:
            normalized = os.path.join(work_dir, f"{base}_norm.mp4")
            logger.info(
                f"[VideoProcessor] Normalizing {src_w}×{src_h} → "
                f"{target_w}×{target_h} (letterbox/pillarbox)"
            )
            FFMpegWizard.normalize_video_size(sped, target_w, target_h, normalized)
            norm_dur = FFMpegWizard.get_video_duration(normalized)
            logger.debug(f"[VideoProcessor] Normalized video duration = {norm_dur:.3f}s")
            sped = normalized
        else:
            logger.debug(
                f"[VideoProcessor] Video already at target size "
                f"{target_w}×{target_h} — skipping normalization"
            )

        # ── Step 3: overlay ───────────────────────────────────────────────
        if overlay_html:
            duration = segment.get("duration") or FFMpegWizard.get_video_duration(sped)
            frames_dir = os.path.join(work_dir, f"{base}_overlay_frames")
            os.makedirs(frames_dir, exist_ok=True)

            # Use OVERLAY_FRAME_RATE (default 10 fps) — overlays are just
            # text/captions appearing and don't need the full video fps.
            # This typically cuts frame count by 3× (e.g. 600 → 200 for 20s).
            overlay_fps = int(getattr(config, "OVERLAY_FRAME_RATE", 10))
            total_frames = int(duration * overlay_fps)
            logger.info(
                f"[VideoProcessor] Rendering overlay: {duration:.2f}s × {overlay_fps}fps "
                f"= {total_frames} frames  (size: {config.VIDEO_WIDTH}×{config.VIDEO_HEIGHT}px)"
            )
            self._render_overlay_frames(
                overlay_html, duration, overlay_fps, config, frames_dir,
                segment.get("styles") or "",
                browser=browser,
            )
            actual_frames = len([f for f in os.listdir(frames_dir) if f.endswith(".png")])
            logger.debug(f"[VideoProcessor] Overlay frames written: {actual_frames}")
            logger.info("[VideoProcessor] Compositing overlay onto video")
            FFMpegWizard.overlay_frames_on_video(sped, frames_dir, overlay_fps, output_path)
        else:
            logger.debug("[VideoProcessor] No overlay HTML — copying processed video as-is")
            FFMpegWizard.copy_video_as_is(sped, output_path)

        final_dur = FFMpegWizard.get_video_duration(output_path)
        logger.info(f"[VideoProcessor] Done — {output_path}  ({final_dur:.3f}s)")

    def _render_overlay_frames(self, html_content, duration, fps, config, out_dir, styles="", browser=None):
        """
        Render overlay HTML as a transparent PNG sequence using Playwright.

        If *browser* is provided it is reused (shared with Animagic's
        ``process_frames``). Otherwise a fresh Playwright context is
        launched — this path is only taken when ``VideoProcessor`` is used
        standalone outside of ``Animagic``.

        Frames are named 0001.png, 0002.png, … matching FFmpeg's image2
        demuxer.
        """
        html = self.preprocessor.preprocess_overlay(html_content, styles)
        frame_count = int(duration * fps)
        interval_ms = (duration / frame_count) * 1000 if frame_count > 0 else 0

        logger.debug(
            f"[VideoProcessor._render_overlay_frames] "
            f"frame_count={frame_count}  interval={interval_ms:.1f}ms  "
            f"viewport={config.VIDEO_WIDTH}×{config.VIDEO_HEIGHT}"
        )

        # Use provided browser or launch a temporary one
        if browser is not None:
            self._capture_overlay_frames(browser, html, frame_count, interval_ms, config, out_dir)
        else:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                tmp_browser = p.chromium.launch()
                self._capture_overlay_frames(tmp_browser, html, frame_count, interval_ms, config, out_dir)
                tmp_browser.close()

    def _capture_overlay_frames(self, browser, html, frame_count, interval_ms, config, out_dir):
        """Capture *frame_count* transparent PNG screenshots into *out_dir*."""
        page = browser.new_page()
        page.set_viewport_size(
            {"width": config.VIDEO_WIDTH, "height": config.VIDEO_HEIGHT}
        )
        page.set_content(html, wait_until="networkidle")

        for i in range(frame_count):
            png_bytes = page.screenshot(omit_background=True)
            frame_path = os.path.join(out_dir, f"{i + 1:04d}.png")
            with open(frame_path, "wb") as f:
                f.write(png_bytes)
            if interval_ms > 0:
                page.wait_for_timeout(interval_ms)

        page.close()
