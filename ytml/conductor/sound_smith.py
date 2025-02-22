from pydub import AudioSegment


class SoundSmith:
    def mix_audio_with_ducking(self, video_audio_path, music_path, output_path, start_time, end_time, ducking_level=-10):
        """
        Mix background music into a video audio between specific timestamps with ducking.

        :param video_audio_path: Path to the original audio (extracted from video).
        :param music_path: Path to the background music file.
        :param output_path: Path to save the final mixed audio.
        :param start_time: Start time in milliseconds to mix background music.
        :param end_time: End time in milliseconds to mix background music.
        :param ducking_level: Level (in dB) to reduce the volume of the original audio during mixing.
        """
        # Load the original audio and background music
        original_audio = AudioSegment.from_file(video_audio_path)
        background_music = AudioSegment.from_file(music_path).set_channels(1)

        # Trim background music to match the duration of the overlay section
        background_music_segment = background_music[:end_time *
                                                    1000 - start_time*1000].apply_gain(ducking_level)

        # Overlay the background music onto the ducked portion
        mixed_segment = original_audio[start_time *
                                       1000:end_time*1000].overlay(background_music_segment)


        # Replace the original segment with the mixed segment
        final_audio = (
            original_audio[:start_time*1000] +  # Audio before the overlay
            mixed_segment +               # Mixed segment
            original_audio[end_time*1000:]     # Audio after the overlay
        )

        # Save the final mixed audio
        final_audio.export(output_path, format="mp3")
        print(f"Final audio saved to {output_path}")
        return output_path
