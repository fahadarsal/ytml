import os
from ytml.conductor.sound_smith import SoundSmith
from ytml.utils.ffmpeg_wizard import FFMpegWizard


class VidComposer:
    def __init__(self, output_file="final_output.mp4"):
        self.output_file = output_file
        self.soundSmith = SoundSmith()

    def process_segments(self, segments):
        """
        Process all segments to handle <pauses>, <music>, and transitions.
        """
        final_videos = []

        for idx, segment in enumerate(segments):
            video_file = segment["video_file"]

            # Handle music
            music_output = video_file.replace(".mp4", "_with_music")
            video_file = self.process_music(
                video_file, segment.get("music", []), music_output)
            final_videos.append(video_file)
        return final_videos

    def process_music(self, video_file, music_data, output_file):
        """
        Add background music to the video based on the provided music data.
        """
        if not music_data:
            return video_file

        music = music_data[0]  # Assuming one music track per segment
        music_src = music["src"]
        music_start = music["start"]
        music_end = music["end"]

        print(f"Adding music from {music_src} to {video_file}...")
        if os.path.isfile(music_src):
            audio_file = self.soundSmith.mix_audio_with_ducking(
                video_file, music_src, f'{output_file}.mp3', music_start, music_end)
            FFMpegWizard.merge_audio_with_ducking(
                video_file, audio_file, f'{output_file}.mp4')
            print(f"Music added to {video_file}, saved to {output_file}.mp4")
        else:
            print("Music file not found.")
            return video_file

        return output_file+".mp4"

    def concatenate_videos(self, video_files, global_music=None):
        """
        Concatenate all processed video segments into a single video.
        """

        FFMpegWizard.concatenate_videos(video_files, self.output_file)
        if global_music is not None and len(global_music) > 0:
            src = global_music[0]["src"]
            start = global_music[0]["start"]
            end = global_music[0]["end"]

            # Mix global music with the video audio
            mixed_audio_file = self.soundSmith.mix_audio_with_ducking(
                self.output_file, src, "tmp/temp_audio.mp3", start, end)
            final_output = self.output_file.replace(".mp4", "_with_music.mp4")
            # Merge the mixed audio back into the video
            FFMpegWizard.merge_audio_with_ducking(
                self.output_file, mixed_audio_file, final_output)
            # Update the output file name to include the merged audio
            self.output_file = final_output

        print(f"Final video saved to {self.output_file}")


if __name__ == "__main__":
    vid = VidComposer("test.mp4")
    vids = [
        "tmp/0868836c-ceb6-402f-83c2-fa448a2e92a9/mixed_segments/synchronized_segment_1_with_music.mp4",

        "tmp/0868836c-ceb6-402f-83c2-fa448a2e92a9/mixed_segments/synchronized_segment_2.mp4",

        "tmp/0868836c-ceb6-402f-83c2-fa448a2e92a9/mixed_segments/synchronized_segment_3.mp4",
        "tmp/0868836c-ceb6-402f-83c2-fa448a2e92a9/mixed_segments/synchronized_segment_4.mp4",
        "tmp/0868836c-ceb6-402f-83c2-fa448a2e92a9/mixed_segments/synchronized_segment_5.mp4"
    ]
    gM = [
        {
            "src": "videos/assets/sample.mp3",
            "start": "10s",
            "end": "20s",
        }
    ]
    vid.concatenate_videos(video_files=vids)
