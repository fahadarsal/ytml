import os
import re
from ytml.utils.config import Config


class HtmlPreprocessor:
    def __init__(self, config: Config, asset_dir="assets"):
        self.asset_dir = asset_dir
        self.config = config

    def _read_file_with_replacements(self, filepath, replacements=None):
        """Read a file and replace placeholders."""
        with open(filepath, "r") as file:
            content = file.read()
        if replacements:
            for key, value in replacements.items():
                content = content.replace(key, value)
        return content

    def _get_head_tag(self, styles=None, include_css=True, include_js=True, include_animations=True):
        """Dynamically generates the <head> tag with selected CSS & JS files."""
        try:
            replacements = {"VIDEO_WIDTH": str(self.config.VIDEO_WIDTH), "VIDEO_HEIGHT": str(
                self.config.VIDEO_HEIGHT), "MERMAID_THEME": self.config.MERMAID_THEME, 'CODE_ANIMATION_DELAY': str(self.config.ANIMATION_DELAY)}
            # Process selected CSS files
            css_tags = []
            if (not self.config.HTML_ASSETS):
                return f"""
                    <head>
                        {styles or ""}
                    </head>"""
            if include_css:
                for css_file in self.config.HTML_ASSETS["css"]:
                    css_path = os.path.join(self.asset_dir, css_file)
                    css_content = self._read_file_with_replacements(
                        css_path, replacements)
                    css_tags.append(f"<style>{css_content}</style>")
            # Process selected JS files
            js_tags = []
            if include_js:
                for js_file in self.config.HTML_ASSETS["js"]:
                    js_path = os.path.join(self.asset_dir, js_file)
                    js_content = self._read_file_with_replacements(
                        js_path, replacements)
                    js_tags.append(f"{js_content}")
            if include_animations:
                for js_file in self.config.HTML_ASSETS["animations"]:
                    js_path = os.path.join(self.asset_dir, js_file)
                    js_content = self._read_file_with_replacements(
                        js_path, replacements)
                    js_tags.append(f"{js_content}")

            head_tag = f"""
            <head >
                {''.join(css_tags)}
                {styles or ""}
                {''.join(js_tags)}
            </head >
            """
            return head_tag
        except Exception as e:
            raise RuntimeError(f"Failed to generate head tag: {e}")

    def preprocess(self, html_content, styles=None, include_css=True, include_js=True, include_animations=False):
        """Preprocess HTML content."""
        try:
            head_tag = self._get_head_tag(
                styles, include_css, include_js, include_animations)
            # Handle Mermaid tags
            if "<mermaid>" in html_content:
                html_content = html_content.replace(
                    "<mermaid>", "<div class='mermaid'>").replace("</mermaid>", "</div>")

            # Complete HTML template
            html_template = f"""
            <html >
            {head_tag}
            <body >
                <div style = "width:90%; height:90%; font-size:24px;" > {html_content} < /div >
            </body >
            </html >
            """
            html_template = html_template.replace(
                "../", "http://localhost:8000/")
            return html_template
        except Exception as e:
            raise RuntimeError(f"Failed to preprocess HTML: {e}")

    def preview(self, parsed_json):
        htmlBody = ""
        head_tag = ""
        for segment_idx, segment in enumerate(parsed_json.get("segments", [])):
            head_tag = self._get_head_tag(segment.get(
                "styles", ""), include_animations=not segment['static'])
            for frame_idx, frame in enumerate(segment.get("frames", [])):
                html_content = frame
                if "<mermaid>" in html_content:
                    # Extract Mermaid content and wrap in the required div
                    html_content = html_content.replace(
                        "<mermaid>", "<div class='mermaid'>").replace("</mermaid>", "</div>")
                htmlBody += html_content
        # Self closing object tags.
        htmlBody = re.sub(
            # Capture `<object` + any attributes (non-greedy) + `/>`
            r'<object([^>]*)/>',
            r'<object\1></object>',
            htmlBody)

        return f"""
        <html >
        {head_tag}
        <body >
            <div style = "width:90%; height:90%;font-size:24px;" > {htmlBody} </divß>
        </body >
        </html >
        """
