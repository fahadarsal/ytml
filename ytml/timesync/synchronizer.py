import subprocess
import os
from ytml.utils.ffmpeg_wizard import FFMpegWizard


class TimeSyncAlchemist:
    def __init__(self, output_dir="tmp/final_videos"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def calculate_audio_duration(self, timing_metadata):
        """
        Calculate the total duration of audio based on timing metadata.
        Considers multiple voice tags in a segment.
        """
        max_duration = 0
        for entry in timing_metadata:
            start = entry["start"]
            end = entry["end"]
            max_duration = max(max_duration, start + end)
        return max_duration

    def get_video_duration(self, video_file):
        """
        Get the duration of a video file using FFprobe.
        """
        return FFMpegWizard.get_video_duration(video_file)

    def extend_video(self, video_file, extra_duration, output_file):
        """
        Extend video duration by padding with the last frame.
        """
        FFMpegWizard.extend_video(video_file, extra_duration, output_file)

    def merge_audio_video(self, segment, output_file):
        """
        Synchronize and merge audio with video based on timing metadata.
        """
        video_file = segment["video_file"]
        audio_files = segment["audio_files"]
        timing_metadata = segment["timing_metadata"]

        if not audio_files:
            print(f"No audio files for {video_file}. Copying video as-is.")
            FFMpegWizard.copy_video_as_is(video_file, output_file)
            return

        # Calculate durations
        video_duration = self.get_video_duration(video_file)
        audio_duration = self.calculate_audio_duration(timing_metadata)
        max_audio_file_duration = max(
            [self.get_video_duration(x) for x in audio_files])
        audio_duration = max(audio_duration, max_audio_file_duration) + 1

        # Handle mismatched durations
        if video_duration < audio_duration:
            print(
                f"Extending video duration from {video_duration}s to {audio_duration}s...")
            extended_video = video_file.replace(".mp4", "_extended.mp4")
            FFMpegWizard.extend_video(
                video_file, audio_duration - video_duration, extended_video)
            video_file = extended_video

        print(f"Merging audio and video for {video_file}...")
        FFMpegWizard.merge_audio_with_timing(
            video_file, audio_files, timing_metadata, output_file)
        print(f"Output saved to {output_file}")

    def process_segments(self, segment_data):
        """
        Process all segments and produce synchronized video files.
        """
        final_videos = []

        for segment in segment_data:
            video_file = segment["video_file"]
            audio_files = segment["audio_files"]
            timing_metadata = segment["timing_metadata"]
            output_file = os.path.join(
                self.output_dir, f"synchronized_{os.path.basename(video_file)}")
            self.merge_audio_video(segment, output_file)
            final_videos.append(output_file)

        return final_videos
