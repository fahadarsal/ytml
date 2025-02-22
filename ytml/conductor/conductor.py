import os
import json
import argparse
from ytml.interpretron.parser import YTMLParser
from ytml.vocalforge.gtts_vocal_forge import gTTSVocalForge
from ytml.vocalforge.base_vocal_forge import VocalForgeBase
from ytml.vocalforge.xi_labs_vocal_forge import ElevenLabsVocalForge
from ytml.animagic.renderer import Animagic, HtmlPreprocessor
from ytml.timesync.synchronizer import TimeSyncAlchemist
from ytml.conductor.vid_composer import VidComposer
from ytml.conductor.local_server import start_local_server
from ytml.utils.config import get_config_from_file, Config
import uuid


class Conductor:
    def __init__(self, vocal_forge: VocalForgeBase, output_file: str, config: Config, job_id=None):
        self.vocal_forge = vocal_forge
        self.vidcomposer = VidComposer(output_file)
        self.job_id = job_id or str(uuid.uuid4())
        self.job_dir = f"tmp/{self.job_id}"
        self.config = config

    def previewHTML(self, ytml_file):
        parser = YTMLParser(ytml_file)
        parsed_json = parser.parse()
        self.preproc = HtmlPreprocessor(self.config)
        html = self.preproc.preview(parsed_json)
        with open(f"preview.html", "w") as f:
            f.write(html)

    def run_workflow(self, ytml_file, skip_steps, job=None):
        
        """
        Main workflow for orchestrating the video generation process.
        """
        local_server = start_local_server()
        print(f"Starting workflow with Job ID: {self.job_id}...")
        os.makedirs(self.job_dir, exist_ok=True)

        # Step 1: Parse YTML
        if "parse" not in skip_steps:
            print("Parsing YTML...")
            parser = YTMLParser(ytml_file)
            parsed_json = parser.parse()
            with open(f"{self.job_dir}/parsed.json", "w") as f:
                json.dump(parsed_json, f, indent=2)
            print("Parsed JSON saved.")
        else:
            print("Skipping YTML parsing...")
            with open(f"{self.job_dir}/parsed.json", "r") as f:
                parsed_json = json.load(f)

        # Step 2: Generate Voiceovers
        if "voiceover" not in skip_steps:
            print("Generating voiceovers...")
            voice_metadata = self.vocal_forge.process_voiceovers(
                parsed_json, output_dir=f"{self.job_dir}/voiceovers")
            with open(f"{self.job_dir}/voice_metadata.json", "w") as f:
                json.dump(voice_metadata, f, indent=2)
            print("Voiceover metadata saved.")
        else:
            print("Skipping voiceover generation...")
            voice_metadata = []
            if (job):
                with open(f"tmp/{job}/voice_metadata.json", "r") as f:
                    voice_metadata = json.load(f)

        # Step 3: Render Animations
        if "render" not in skip_steps:
            print("Rendering video segments...")
            self.animagic = Animagic(
                output_dir=f"{self.job_dir}/renders", config=self.config)
            segment_videos = self.animagic.process_frames(parsed_json)
            with open(f"{self.job_dir}/segment_videos.json", "w") as f:
                json.dump(segment_videos, f, indent=2)
            print("Segment videos saved.")
        else:
            print("Skipping video rendering...")
            with open(f"{self.job_dir}/segment_videos.json", "r") as f:
                segment_videos = json.load(f)

        # Step 4: Synchronize Audio and Video
        if "sync" not in skip_steps:
            print("Synchronizing audio and video...")
            segment_data = self.prepare_segment_data(
                parsed_json, segment_videos, voice_metadata)
            self.alchemist = TimeSyncAlchemist(
                f"{self.job_dir}/mixed_segments")
            synchronized_videos = self.alchemist.process_segments(segment_data)
            with open(f"{self.job_dir}/synchronized_videos.json", "w") as f:
                json.dump(synchronized_videos, f, indent=2)
            print("Synchronized videos saved.")
        else:
            print("Skipping synchronization...")
            with open(f"{self.job_dir}/synchronized_videos.json", "r") as f:
                synchronized_videos = json.load(f)

        # Step 5: Combine Metadata with Video Paths
        print("Combining metadata with synchronized video files...")
        combined_segments = self.combine_video_metadata(
            synchronized_videos, parsed_json)
        print("Combined segments:", combined_segments)

        # Step 6: Process Tags and Compose Final Video
        if "compose" not in skip_steps:
            print("Processing tags and composing final video...")
            processed_segments = self.vidcomposer.process_segments(
                combined_segments)
            self.vidcomposer.concatenate_videos(
                processed_segments, parsed_json["global_music"])
            print("Final video composed.")
        else:
            print("Skipping final video composition...")
        if local_server:
            local_server.shutdown()
        print("Workflow completed!")

    def combine_video_metadata(self, synchronized_files, parsed_json):
        """
        Combine synchronized video file paths with their corresponding metadata.
        """
        combined_segments = []
        for idx, video_file in enumerate(synchronized_files):
            segment_metadata = parsed_json["segments"][idx]
            combined_segments.append({
                "video_file": video_file,
                "pauses": segment_metadata.get("pauses", []),
                "music": segment_metadata.get("music", []),
                "transitions": segment_metadata.get("transitions", [])
            })
        return combined_segments

    def prepare_segment_data(self, parsed_json, segment_videos, voice_metadata):
        """
        Prepare data for TimeSync Alchemist.
        """
        segment_data = []
        for idx, segment in enumerate(parsed_json["segments"]):
            audio_files = [voice["file"]
                           for voice in voice_metadata if f"segment{idx+1}_" in voice["file"]]
            timing_metadata = [
                {"start": voice["start"], "end": voice["end"]}
                for voice in voice_metadata
                if f"segment{idx+1}_" in voice["file"]
            ]
            segment_data.append({
                "video_file": segment_videos[idx],
                "audio_files": audio_files,
                "timing_metadata": timing_metadata
            })
        return segment_data

    def get_job_status(self):
        """Check the current status of the job."""
        stages = ["parsed.json", "voice_metadata.json",
                  "segment_videos.json", "synchronized_videos.json"]
        status = {}
        for stage in stages:
            status[stage] = os.path.exists(f"{self.job_dir}/{stage}")
        return status
