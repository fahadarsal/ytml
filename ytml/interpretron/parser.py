import re
import unicodedata
import xml.etree.ElementTree as ET
import json
from ytml.utils.utils import parse_boolean, parse_duration


class YTMLParser:
    def __init__(self, ytml_file):
        self.ytml_file = ytml_file
        self.templates = {}
        self.global_styles = ""

    def clean_text(self, text):
        """
        Cleans and normalizes the input text by:
        - Stripping leading and trailing whitespace
        - Replacing multiple spaces and newlines with a single space
        - Normalizing Unicode characters to ASCII equivalents
        """
        # Normalize Unicode characters
        normalized_text = unicodedata.normalize('NFKC', text)
        # Remove extra spaces and newlines
        cleaned_text = re.sub(r'\s+', ' ', normalized_text.strip())
        return cleaned_text

    def _preprocess_file(self, file_path):
        """
        Preprocess the YTML file to wrap content inside <code> tags in <![CDATA[ ... ]]>
        """
        with open(file_path, "r") as file:
            content = file.read()

        # Wrap <frame> content in <![CDATA[ ... ]]>
        content = re.sub(
            r"(<frame[^>]*>)(.*?)(</frame>)",
            lambda match: f"{match.group(1)}<![CDATA[{match.group(2)}]]>{match.group(3)}",
            content,
            flags=re.DOTALL
        )
        return content

    def parse(self):
        """
        Parse the YTML file and return structured JSON.
        """
        try:
            # Preprocess the file to handle <code> content
            preprocessed_content = self._preprocess_file(self.ytml_file)
            root = ET.fromstring(preprocessed_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid YTML format: {e}")

        if root.tag != "ytml":
            raise ValueError("Invalid root element. Expected <ytml>.")

        # Extract templates
        self._extract_templates(root)

        # Extract styles
        style_tags = root.find("style")
        self.global_styles = (
            ET.tostring(style_tags, encoding="unicode").strip(
            ) if style_tags is not None else None
        )
        # Parse composites
        composites = []
        for composite in root.findall("composite"):
            # Check conditional logic
            composites.append(self._parse_composite(composite))

        # Extract global-music tag
        global_music_tag = root.find("global-music")
        global_music = []
        if (global_music_tag != None):

            global_music.append(
                {
                    "src": global_music_tag.get('src'),
                    "start": parse_duration(global_music_tag.get('start')),
                    "end": parse_duration(global_music_tag.get('end')),
                    "loop": global_music_tag.get("loop") == "true",
                }
            )
        return {"segments": composites, "global_music": global_music}

    def _extract_templates(self, root):
        """
        Extract and store reusable templates.
        """
        for template in root.findall("template"):
            template_id = template.get("id")
            if not template_id:
                raise ValueError("Template missing required 'id' attribute.")
            if template_id in self.templates:
                raise ValueError(f"Duplicate template ID found: {template_id}")
            self.templates[template_id] = template

    def _parse_composite(self, composite):
        """
        Parse a single composite, handling <code> tags as raw text.
        """
        parsed_composite = {
            "frames": [],
            "styles": self.global_styles,
            "voiceovers": [],
            "music": [],
            "transitions": [],
            "duration": '',
            "static": False
        }
        current_time = 0.0

        # Parse frames
        for frame in composite.findall("frame"):
            frame_data = frame.text.strip() if frame.text else ""
            parsed_composite["frames"].append(frame_data)
            parsed_composite['duration'] = parse_duration(
                frame.get('duration') or '2s')
            parsed_composite['frame_rate'] = frame.get('frame_rate')
            parsed_composite["static"] = parse_boolean(frame.get("static"))

        # Expand <use> tags with templates
        for use in composite.findall("use"):
            template_id = use.get("template")
            if not template_id or template_id not in self.templates:
                raise ValueError(
                    f"Referenced template '{template_id}' not found.")
            template_content = ET.tostring(
                self.templates[template_id], encoding="unicode").strip()
            parsed_composite["frames"].append(template_content)

        # Parse voiceovers
        for voice in composite.findall("voice"):
            start = self._resolve_timing(voice.get("start"), current_time)
            end = self._resolve_timing(voice.get("end"), start)
            current_time = max(current_time, end)
            parsed_composite["voiceovers"].append({
                "text": self.clean_text(voice.text),
                "start": start,
                "end": end
            })

        # Parse music
        for music in composite.findall("music"):
            start = self._resolve_timing(music.get("start"), current_time)
            end = self._resolve_timing(music.get("end"), start)
            current_time = max(current_time, end)
            parsed_composite["music"].append({
                "src": music.get("src"),
                "start": start,
                "end": end,
                "loop": music.get("loop") == "true",
            })

        # Parse transitions
        for transition in composite.findall("transition"):
            tType = transition.get("type")
            duration = self._resolve_timing(transition.get("duration"), "1s")
            parsed_composite["transitions"].append({
                "type": tType,
                "duration": f"{duration}s",
            })

        return parsed_composite

    def _resolve_timing(self, timing, current_time):
        """
        Resolve timing values:
        - Absolute values (e.g., "5s") remain unchanged.
        - Relative values (e.g., "+2s") are added to the current time.
        """
        if timing is None:
            return current_time
        if timing.startswith("+"):
            return current_time + float(parse_duration(timing[1:]))
        return float(parse_duration(timing))


# CLI for testing
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python parser.py <ytml_file>")
        sys.exit(1)

    parser = YTMLParser(sys.argv[1])
    try:
        result = parser.parse()
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
