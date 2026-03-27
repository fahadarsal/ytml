import os
import re
from ytml.utils.config import Config

# CDN bundles — loaded only when the frame actually needs them.
# Playwright fetches these at render time via headless Chromium.
_MERMAID_SCRIPT = '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>'
_PRISM_CSS = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css"/>'
_PRISM_JS = '<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>'
_PRISM_AUTOLOADER = '<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>'


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

    def _cdn_tags(self, html_content):
        """
        Return CDN <script>/<link> tags required by the frame content.
        Mermaid and Prism are only injected when the frame actually uses them,
        keeping unrelated slides lean.
        """
        tags = []
        if "<mermaid" in html_content:
            tags.append(_MERMAID_SCRIPT)
            tags.append(
                f'<script>document.addEventListener("DOMContentLoaded",function(){{'
                f'mermaid.initialize({{startOnLoad:true,theme:"{self.config.MERMAID_THEME}"}})}})</script>'
            )
        if "<code" in html_content:
            tags.append(_PRISM_CSS)
            tags.append(_PRISM_JS)
            tags.append(_PRISM_AUTOLOADER)
        return "\n".join(tags)

    def _get_head_tag(self, html_content="", styles=None, include_css=True, include_js=True, include_animations=True):
        """Dynamically generates the <head> tag."""
        try:
            replacements = {
                "VIDEO_WIDTH": str(self.config.VIDEO_WIDTH),
                "VIDEO_HEIGHT": str(self.config.VIDEO_HEIGHT),
                "MERMAID_THEME": self.config.MERMAID_THEME,
                "CODE_ANIMATION_DELAY": str(self.config.ANIMATION_DELAY),
            }
            css_tags = []
            js_tags = []

            if self.config.HTML_ASSETS:
                if include_css:
                    for css_file in self.config.HTML_ASSETS.get("css", []):
                        css_path = os.path.join(self.asset_dir, css_file)
                        css_content = self._read_file_with_replacements(
                            css_path, replacements)
                        css_tags.append(f"<style>{css_content}</style>")
                if include_js:
                    for js_file in self.config.HTML_ASSETS.get("js", []):
                        js_path = os.path.join(self.asset_dir, js_file)
                        js_content = self._read_file_with_replacements(
                            js_path, replacements)
                        js_tags.append(js_content)
                if include_animations:
                    for js_file in self.config.HTML_ASSETS.get("animations", []):
                        js_path = os.path.join(self.asset_dir, js_file)
                        js_content = self._read_file_with_replacements(
                            js_path, replacements)
                        js_tags.append(js_content)

            cdn = self._cdn_tags(html_content)

            return f"""<head>
{''.join(css_tags)}
{styles or ""}
{cdn}
{''.join(js_tags)}
</head>"""
        except Exception as e:
            raise RuntimeError(f"Failed to generate head tag: {e}")

    def preprocess(self, html_content, styles=None, include_css=True, include_js=True, include_animations=False):
        """Preprocess HTML content."""
        try:
            head_tag = self._get_head_tag(
                html_content, styles, include_css, include_js, include_animations)

            if "<mermaid>" in html_content:
                html_content = html_content.replace(
                    "<mermaid>", "<div class='mermaid'>").replace("</mermaid>", "</div>")

            html_template = f"""<html>
{head_tag}
<body style="margin:0;padding:0;">
    <div style="width:100%; height:100%;">{html_content}</div>
</body>
</html>"""
            html_template = html_template.replace(
                "../", "http://localhost:8000/")
            return html_template
        except Exception as e:
            raise RuntimeError(f"Failed to preprocess HTML: {e}")

    def preview(self, parsed_json):
        html_body = ""
        head_tag = ""
        combined_content = ""
        for segment in parsed_json.get("segments", []):
            for frame in segment.get("frames", []):
                combined_content += frame

        head_tag = self._get_head_tag(
            combined_content,
            parsed_json.get("segments", [{}])[0].get(
                "styles", "") if parsed_json.get("segments") else "",
            include_animations=True,
        )

        for segment in parsed_json.get("segments", []):
            for frame in segment.get("frames", []):
                html_content = frame
                if "<mermaid>" in html_content:
                    html_content = html_content.replace(
                        "<mermaid>", "<div class='mermaid'>").replace("</mermaid>", "</div>")
                html_body += html_content

        html_body = re.sub(r'<object([^>]*)/>',
                           r'<object\1></object>', html_body)

        return f"""<html>
{head_tag}
<body style="margin:0;padding:0;">
    <div style="width:100%; height:100%;">{html_body}</div>
</body>
</html>"""
