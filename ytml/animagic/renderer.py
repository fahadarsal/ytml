import os
import logging
from playwright.sync_api import sync_playwright
from imageio import get_writer, imread
import re
from ytml.animagic.html_preprocesor import HtmlPreprocessor
from ytml.utils.config import Config


class Animagic:
    def __init__(self, config: Config, output_dir="tmp/renders"):
        """
        Initialize Animagic with default output directory and frame rate.
        """
        self.output_dir = output_dir
        self.config = config
        os.makedirs(self.output_dir, exist_ok=True)

        # Configure logging
        self.logger = logging.getLogger("Animagic")
        self.preprocessor = HtmlPreprocessor(config=self.config)
        logging.basicConfig(level=logging.INFO)

    def _setup_page(self, browser, html_content):
        """
        A shared method to initialize the browser page with given HTML content.
        """
        page = browser.new_page()
        page.set_viewport_size(
            {"width": self.config.VIDEO_WIDTH, "height": self.config.VIDEO_HEIGHT}
        )
        page.set_content(html_content)
        if "<mermaid" in html_content:
            page.wait_for_function(
                "window.mermaid && window.mermaid.init", timeout=5000)
        return page

    def render_frame(self, html_content, output_file):
        """
        Render a single frame of HTML content to an image.
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = self._setup_page(browser, html_content)
                page.screenshot(path=output_file)
                browser.close()
            self.logger.info(f"Rendered frame saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to render frame: {e}")

    def render_animation(self, html_content, segment_id, frame_rate, duration=2):
        """
        Render an animated HTML/CSS as a sequence of images.
        """
        frame_dir = os.path.join(
            self.output_dir, f"segment_{segment_id}_frames")
        os.makedirs(frame_dir, exist_ok=True)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = self._setup_page(browser, html_content)

                # Extend duration if there's code content
                if "<code" in html_content:
                    spans_count = page.evaluate(
                        "document.querySelectorAll('.token').length")
                    calculated_duration = (
                        spans_count * self.config.ANIMATION_DELAY) / 1000
                    if duration < calculated_duration:
                        duration = calculated_duration
                frame_count = int(duration * frame_rate)
                interval = duration / frame_count

                for i in range(frame_count):
                    frame_path = os.path.join(frame_dir, f"frame_{i:03d}.png")
                    page.screenshot(path=frame_path)
                    page.wait_for_timeout(interval * 1000)
                browser.close()
            self.logger.info(f"Animation frames saved to {frame_dir}")
        except Exception as e:
            self.logger.error(f"Failed to render animation: {e}")

        return frame_dir

    def process_frames(self, parsed_json):
        """
        Render frames and animations for each segment in the parsed JSON.
        """
        segment_videos = []
        for segment_idx, segment in enumerate(parsed_json.get("segments", [])):
            self.logger.info(f"Processing segment {segment_idx + 1}...")
            frame_files = []
            for frame_idx, frame in enumerate(segment.get("frames", [])):
                hasAnimation = segment['static'] == False
                html_content = self.preprocessor.preprocess(
                    frame, segment.get("styles", ""), include_animations=hasAnimation)
                # Check if the frame has animation or is static
                if hasAnimation:
                    frame_dir = self.render_animation(
                        html_content=html_content,
                        segment_id=f"{segment_idx + 1}_frame{frame_idx + 1}",
                        frame_rate=int(
                            segment['frame_rate'] or self.config.FRAME_RATE),
                        duration=segment['duration']
                    )
                    frame_files += sorted(
                        [os.path.join(frame_dir, img) for img in os.listdir(
                            frame_dir) if img.endswith(".png")]
                    )
                else:
                    # Static frame
                    output_file = os.path.join(
                        self.output_dir, f"segment{segment_idx + 1}_frame{frame_idx + 1}.png")
                    self.render_frame(html_content, output_file)
                    frame_files.append(output_file)

            # Combine frames into a video
            video_file = os.path.join(
                self.output_dir, f"segment_{segment_idx + 1}.mp4")
            VideoComposer(self.config.FRAME_RATE).create_video(
                frame_files, video_file)
            segment_videos.append(video_file)

        return segment_videos


class VideoComposer:
    def __init__(self, frame_rate):
        self.frame_rate = frame_rate
        self.logger = logging.getLogger("VideoComposer")
        logging.basicConfig(level=logging.INFO)

    def create_video(self, images, output_file):
        """
        Combine images into a video file using FFmpeg.
        """
        try:
            writer = get_writer(output_file, fps=self.frame_rate)
            for image in images:
                writer.append_data(imread(image))
            writer.close()
            self.logger.info(f"Video saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to create video: {e}")
