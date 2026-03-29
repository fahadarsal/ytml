import os
import shlex
import subprocess

from ytml.utils.logger import logger


def _q(path):
    """Shell-quote a file path to prevent injection."""
    return shlex.quote(str(path))


class FFMpegWizard:
    @staticmethod
    def run_command(command):
        """
        Execute an FFmpeg/FFprobe command using subprocess.

        Raises RuntimeError with the captured stderr on failure so that
        callers get a human-readable message instead of a bare CalledProcessError.
        """
        os.makedirs("tmp", exist_ok=True)
        with open("tmp/ffmpeg_log.txt", "a") as log_file:
            log_file.write(f"\n$ {command}\n")
            result = subprocess.run(
                command, shell=True,
                stdout=log_file, stderr=subprocess.PIPE,
            )
            stderr_text = result.stderr.decode(errors="replace") if result.stderr else ""
            log_file.write(stderr_text)

            if result.returncode != 0:
                # Keep last 15 lines of stderr for the error message
                tail = "\n".join(stderr_text.strip().splitlines()[-15:])
                raise RuntimeError(
                    f"FFmpeg command failed (exit {result.returncode}):\n"
                    f"  Command: {command}\n"
                    f"  Stderr:\n{tail}"
                )

    # ── Probe helpers ────────────────────────────────────────────────────

    @staticmethod
    def get_video_duration(video_file):
        """Get the duration of a video file using FFprobe."""
        command = (
            f"ffprobe -i {_q(video_file)} -show_entries format=duration "
            f"-v quiet -of csv=p=0"
        )
        result = subprocess.run(
            command, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        raw = result.stdout.decode().strip()
        if not raw:
            raise RuntimeError(
                f"Could not determine duration of {video_file!r}. "
                f"Is this a valid video file?"
            )
        return float(raw)

    @staticmethod
    def get_video_dimensions(video_file):
        """Return (width, height) of the first video stream."""
        command = (
            f"ffprobe -v error -select_streams v:0 "
            f"-show_entries stream=width,height "
            f"-of csv=s=x:p=0 {_q(video_file)}"
        )
        result = subprocess.run(
            command, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        raw = result.stdout.decode().strip()
        if not raw or "x" not in raw:
            raise RuntimeError(
                f"Could not determine dimensions of {video_file!r}. "
                f"ffprobe returned: {raw!r}"
            )
        w, h = raw.split("x")
        return int(w), int(h)

    @staticmethod
    def has_audio_stream(src):
        """Return True if the video file contains at least one audio stream."""
        command = (
            f"ffprobe -i {_q(src)} -show_streams -select_streams a "
            f"-loglevel error -of csv=p=0"
        )
        result = subprocess.run(
            command, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return bool(result.stdout.decode().strip())

    # ── Video operations ─────────────────────────────────────────────────

    @staticmethod
    def extend_video(video_file, extra_duration, output_file):
        """Extend video duration by padding with the last frame."""
        command = (
            f"ffmpeg -i {_q(video_file)} "
            f'-vf "tpad=stop_mode=clone:stop_duration={float(extra_duration)}" '
            f"-c:v libx264 {_q(output_file)}"
        )
        FFMpegWizard.run_command(command)

    @staticmethod
    def trim_video(src, start, end, output):
        """Trim a video to [start, end] seconds (stream copy — fast)."""
        duration = float(end) - float(start)
        command = (
            f"ffmpeg -y -ss {float(start)} -i {_q(src)} "
            f"-t {duration} -c copy {_q(output)}"
        )
        FFMpegWizard.run_command(command)

    @staticmethod
    def change_speed(src, speed, output):
        """
        Change video playback speed.

        speed > 1 = faster, speed < 1 = slower.
        atempo is clamped to [0.5, 2.0] per FFmpeg limitation; values outside
        that range are handled by chaining multiple atempo filters.
        """
        pts = 1.0 / speed

        if FFMpegWizard.has_audio_stream(src):
            remaining = speed
            atempo_chain = []
            while remaining > 2.0:
                atempo_chain.append("atempo=2.0")
                remaining /= 2.0
            while remaining < 0.5:
                atempo_chain.append("atempo=0.5")
                remaining /= 0.5
            atempo_chain.append(f"atempo={remaining:.4f}")
            atempo_filter = ",".join(atempo_chain)
            command = (
                f"ffmpeg -y -i {_q(src)} "
                f'-vf "setpts={pts:.6f}*PTS" '
                f'-af "{atempo_filter}" '
                f"-c:v libx264 -c:a aac {_q(output)}"
            )
        else:
            command = (
                f"ffmpeg -y -i {_q(src)} "
                f'-vf "setpts={pts:.6f}*PTS" '
                f"-an -c:v libx264 {_q(output)}"
            )
        FFMpegWizard.run_command(command)

    @staticmethod
    def normalize_video_size(src, width, height, output):
        """
        Scale video to exactly width×height using letterbox/pillarbox padding.
        Aspect ratio is preserved; black bars fill gaps.
        """
        w, h = int(width), int(height)
        command = (
            f"ffmpeg -y -i {_q(src)} "
            f'-vf "scale={w}:{h}:force_original_aspect_ratio=decrease,'
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black\" "
            f"-c:v libx264 -crf 18 -preset fast -c:a copy {_q(output)}"
        )
        FFMpegWizard.run_command(command)

    @staticmethod
    def copy_video_as_is(video_file, output_file):
        """Copy video without re-encoding."""
        command = f"ffmpeg -i {_q(video_file)} -c copy {_q(output_file)}"
        FFMpegWizard.run_command(command)

    # ── Audio / video merge ──────────────────────────────────────────────

    @staticmethod
    def merge_audio_video(video_file, audio_files, filter_complex, output_file):
        """Merge audio files with a video using a filter complex."""
        audio_inputs = " ".join([f"-i {_q(audio)}" for audio in audio_files])
        command = (
            f"ffmpeg -i {_q(video_file)} {audio_inputs} "
            f'-filter_complex "{filter_complex}" '
            f'-map 0:v -map "[final_audio]" -c:v copy -c:a aac '
            f"-shortest {_q(output_file)}"
        )
        FFMpegWizard.run_command(command)

    @staticmethod
    def merge_audio_with_ducking(video_file, audio_file, mixed_audio_file):
        """Mix global audio with the video's existing audio with ducking."""
        command = (
            f"ffmpeg -i {_q(video_file)} -i {_q(audio_file)} "
            f"-c:v copy -map 0:v:0 -map 1:a:0 -shortest "
            f"{_q(mixed_audio_file)} -y"
        )
        FFMpegWizard.run_command(command)

    @staticmethod
    def merge_audio_with_timing(video_file, audio_files, timing_metadata, output_file):
        """Merge audio files with a video, applying timing metadata."""
        filter_script = ""
        audio_inputs = []
        for idx, audio_file in enumerate(audio_files):
            start_time = int(timing_metadata[idx]["start"] * 1000)
            filter_script += f"[{idx + 1}:a]adelay={start_time}|{start_time}[a{idx + 1}];"
            audio_inputs.append(f"-i {_q(audio_file)}")
        filter_script += (
            f"{''.join([f'[a{i + 1}]' for i in range(len(audio_files))])}"
            f"amix=inputs={len(audio_files)}[final_audio]"
        )
        command = (
            f"ffmpeg -i {_q(video_file)} {' '.join(audio_inputs)} "
            f'-filter_complex "{filter_script}" '
            f'-map 0:v -map "[final_audio]" -c:v copy -c:a aac '
            f"-shortest {_q(output_file)}"
        )
        FFMpegWizard.run_command(command)

    # ── Transitions ──────────────────────────────────────────────────────

    @staticmethod
    def add_transition(video1, video2, transition_type, duration, output_file):
        """Add a transition between two video files."""
        # Sanitise transition_type — only allow known safe values
        allowed = {"fade", "wipeleft", "wiperight", "wipeup", "wipedown",
                    "slideleft", "slideright", "slideup", "slidedown",
                    "circlecrop", "rectcrop", "distance", "fadeblack",
                    "fadewhite", "radial", "smoothleft", "smoothright",
                    "smoothup", "smoothdown", "dissolve"}
        if transition_type not in allowed:
            raise ValueError(
                f"Unknown transition type {transition_type!r}. "
                f"Allowed: {', '.join(sorted(allowed))}"
            )
        command = (
            f"ffmpeg -i {_q(video1)} -i {_q(video2)} "
            f'-filter_complex "[0:v][1:v]xfade=transition={transition_type}:'
            f'duration={float(duration)}:offset=0[outv]" '
            f'-map "[outv]" -map 0:a? -c:v libx264 -preset fast -crf 23 '
            f"-c:a aac -b:a 128k {_q(output_file)}"
        )
        FFMpegWizard.run_command(command)

    # ── Concatenation ────────────────────────────────────────────────────

    @staticmethod
    def concatenate_videos(video_files, output_file):
        """Normalize audio and concatenate multiple videos into one."""
        temp_dir = "tmp"
        os.makedirs(temp_dir, exist_ok=True)
        normalized_files = []

        try:
            for idx, video_file in enumerate(video_files):
                normalized_file = os.path.join(temp_dir, f"normalized_{idx}.mp4")
                command = (
                    f"ffmpeg -i {_q(video_file)} "
                    f"-ac 1 -ar 44100 -b:a 128k -c:v copy {_q(normalized_file)}"
                )
                FFMpegWizard.run_command(command)
                normalized_files.append(normalized_file)

            concat_file = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_file, "w") as f:
                for nf in normalized_files:
                    # Use absolute paths so FFmpeg doesn't resolve them
                    # relative to the concat file's directory.
                    abs_nf = os.path.abspath(nf)
                    safe = abs_nf.replace("'", "'\\''")
                    f.write(f"file '{safe}'\n")

            command = (
                f"ffmpeg -y -f concat -safe 0 -i {_q(concat_file)} "
                f"-c copy {_q(output_file)}"
            )
            FFMpegWizard.run_command(command)
        finally:
            for nf in normalized_files:
                if os.path.exists(nf):
                    os.remove(nf)
            concat_path = os.path.join(temp_dir, "concat_list.txt")
            if os.path.exists(concat_path):
                os.remove(concat_path)

    # ── Overlay ──────────────────────────────────────────────────────────

    @staticmethod
    def overlay_frames_on_video(video, frames_dir, fps, output):
        """
        Composite a transparent PNG frame sequence over a video.
        frames_dir must contain files named 0001.png, 0002.png, etc.
        """
        command = (
            f"ffmpeg -y -i {_q(video)} "
            f"-framerate {int(fps)} -i {_q(frames_dir)}/%04d.png "
            f'-filter_complex "[0:v][1:v]overlay=0:0:shortest=1" '
            f"-c:v libx264 -c:a copy {_q(output)}"
        )
        FFMpegWizard.run_command(command)
