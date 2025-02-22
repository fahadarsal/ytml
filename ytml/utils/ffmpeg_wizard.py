import subprocess
import os


class FFMpegWizard:
    @staticmethod
    def run_command(command):
        """
        Execute an FFmpeg command using subprocess.
        """
        subprocess.run(command, shell=True, check=True)

    @staticmethod
    def get_video_duration(video_file):
        """
        Get the duration of a video file using FFprobe.
        """
        command = f"ffprobe -i {video_file} -show_entries format=duration -v quiet -of csv='p=0'"
        result = subprocess.run(command, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return float(result.stdout.decode().strip())

    @staticmethod
    def extend_video(video_file, extra_duration, output_file):
        """
        Extend video duration by padding with the last frame.
        """
        command = f"""
        ffmpeg -i {video_file} -vf "tpad=stop_mode=clone:stop_duration={extra_duration}" -c:v libx264 {output_file}
        """
        FFMpegWizard.run_command(command)

    @staticmethod
    def merge_audio_video(video_file, audio_files, filter_complex, output_file):
        """
        Merge audio files with a video using a filter complex.
        """
        audio_inputs = " ".join([f"-i {audio}" for audio in audio_files])
        command = f"""
        ffmpeg -i {video_file} {audio_inputs} -filter_complex "{filter_complex}" -map 0:v -map "[final_audio]" -c:v copy -c:a aac -shortest {output_file}
        """
        FFMpegWizard.run_command(command)

    @staticmethod
    def add_transition(video1, video2, transition_type, duration, output_file):
        """
        Add a transition between two video files.
        """
        command = f"""
        ffmpeg -i {video1} -i {video2} -filter_complex "[0:v][1:v]xfade=transition={transition_type}:duration={duration}:offset=0[outv]" -map "[outv]" -map 0:a? -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k {output_file}
        """
        FFMpegWizard.run_command(command)

    @staticmethod
    def concatenate_videos(video_files, output_file):
        """
        Normalize and concatenate multiple videos into one.
        """
        import os

        # Directory for temporary normalized files
        temp_dir = "tmp"
        os.makedirs(temp_dir, exist_ok=True)
        normalized_files = []

        try:
            # Step 1: Normalize all input files
            for idx, video_file in enumerate(video_files):
                normalized_file = os.path.join(
                    temp_dir, f"normalized_{idx}.mp4")
                command = (
                    f"ffmpeg -i {video_file} -ac 1 -ar 44100 -b:a 128k -c:v copy {normalized_file}"
                )
                FFMpegWizard.run_command(command)
                normalized_files.append(normalized_file)

            # Step 2: Create concat list
            print(normalized_files)
            concat_file = "concat_list.txt"
            with open(concat_file, "w") as f:
                for normalized_file in normalized_files:
                    f.write(f"file '{normalized_file}'\n")

            # Step 3: Concatenate normalized files
            command = f"ffmpeg -f concat -safe 0 -i {concat_file} -c copy {output_file}"
            FFMpegWizard.run_command(command)

        finally:
            # Step 4: Clean up temporary files
            for file in normalized_files:
                os.remove(file)
            if os.path.exists(concat_file):
                os.remove(concat_file)

    @staticmethod
    def merge_audio_with_ducking(video_file, audio_file, mixed_audio_file):
        """
        Mix global audio with the video's existing audio with ducking.
        """
        command = f"ffmpeg -i {video_file} -i {audio_file} -c:v copy -map 0:v:0 -map 1:a:0 -shortest {mixed_audio_file}"
        FFMpegWizard.run_command(command)

    @staticmethod
    def merge_audio_with_timing(video_file, audio_files, timing_metadata, output_file):
        """
        Merge audio files with a video, applying timing metadata.
        """
        # Construct filter_complex script
        filter_script = ""
        audio_inputs = []
        for idx, audio_file in enumerate(audio_files):
            start_time = int((timing_metadata[idx]["start"]) * 1000)
            filter_script += f"[{idx + 1}:a]adelay={start_time}|{start_time}[a{idx + 1}];"
            audio_inputs.append(f"-i {audio_file}")
        filter_script += f"{''.join([f'[a{i + 1}]' for i in range(len(audio_files))])}amix=inputs={len(audio_files)}[final_audio]"

        # Debugging: Print filter script
        print("Generated FFmpeg filter_complex script:")
        print(filter_script)

        # Run the FFmpeg command
        command = f"""
        ffmpeg -i {video_file} {" ".join(audio_inputs)} -filter_complex "{filter_script}" -map 0:v -map "[final_audio]" -c:v copy -c:a aac -shortest {output_file}
        """
        FFMpegWizard.run_command(command)

    @staticmethod
    def copy_video_as_is(video_file, output_file):
        """
        Copy video without modifications.
        """
        command = f"ffmpeg -i {video_file} -c copy {output_file}"
        FFMpegWizard.run_command(command)
