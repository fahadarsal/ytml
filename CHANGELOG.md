# Changelog

All notable changes to **ytml-toolkit** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [0.4.0] — 2026-03-28

### Added

**`<video>` Tag — embed, edit, and overlay videos from YTML**
- Trim source videos to a precise time range (`start` / `end` attributes).
- Adjust playback speed with `speed="0.5x"`, `1x`, `2x`, etc.
- Overlay arbitrary HTML/CSS on top of the video — captions, commentary cards,
  labels, stats, emoji floods, or any DOM element.
- Overlay frames are rendered at `VIDEO_WIDTH x VIDEO_HEIGHT` via Playwright
  as transparent PNGs and composited with FFmpeg.
- CSS `@keyframes` and `animation-delay` work for timed caption visibility.
- Automatic video size normalisation — source videos are scaled and
  letterboxed / pillarboxed to match the configured output resolution before
  processing, preventing dimension-mismatch artefacts during concatenation.

**Parser**
- `<video>` inner HTML is CDATA-wrapped during preprocessing so that overlay
  markup (`<div>`, `<style>`, etc.) survives the XML parser.
- `overlay_html` and `video_source` fields added to the parsed segment dict.

**FFmpeg utilities**
- `FFMpegWizard.get_video_dimensions()` — returns `(width, height)` of a video.
- `FFMpegWizard.normalize_video_size()` — scales and pads a video to an exact
  resolution with aspect-ratio-preserving letterbox/pillarbox.

**Documentation**
- New Docusaurus page: [The `<video>` Tag](/docs/video) — full reference with
  examples for captions, overlays, slow-motion, and commentary cards.
- `tags.md` updated with `<video>` row.
- `future.md` updated — `<video>` marked as shipped.

**Samples**
- `friends-breakdown.ytml` — full Friends episode commentary showcasing video
  overlays: timed captions, animated commentary cards, rejection stamps,
  character labels, slow-motion replay, and stat-bar outro.
- `video-reaction.ytml` — short, focused sample demonstrating the `<video>` tag
  with caption overlay, commentary card, and slow-motion replay.

---

## [0.3.0] — 2026-03-27

### Added

**CLI**
- `ytml init [name]` — scaffolds a new project directory with `video.ytml`, `assets/`, and `.env` in one command.
- `--preview` no longer requires heavy dependencies (Playwright, gTTS, requests). It now uses only stdlib-safe imports, so the preview path works even in minimal environments.
- `sys.path` priority fix — running `cli.py` from source now loads the local package rather than any stale installed version in site-packages.
- `colorama` is now an optional dependency with a silent no-op fallback; the CLI no longer crashes on machines where it is not installed.

**Rendering**
- Full-screen output — videos and previews now fill 100 % of the frame. The wrapper `<div>` was incorrectly constrained to `width: 90%; height: 90%` and the `<body>` had default browser margin; both are fixed.
- Auto CDN injection — `HtmlPreprocessor` detects `<mermaid>` and `<code>` in frame content and automatically injects the correct CDN scripts (Mermaid 10, Prism 1.29). No manual `HTML_ASSETS` configuration is needed for standard use.
- Animated Mermaid diagrams — Mermaid slides no longer require `static="true"`. The renderer waits for the SVG to fully render and then captures animation frames, so CSS entrance animations play in the final video. Mermaid SVGs now fill the slide via `width: 100% !important`.

**Animations** (available in samples and custom YTML)
- `blurIn` — title entrance with blur + slight scale, more cinematic than a plain fade.
- `slideInLeft` / `slideInRight` — alternating horizontal pull-in for list and grid items.
- `codeSlideIn` — code block rises in with a coloured ambient glow matching the slide's accent.
- `diagramReveal` — Mermaid container scales up from 0.88 with an upward drift.
- `titleDrop` — diagram slide title drops in from above.

**Samples** — 8 production-quality example scripts added to `package/samples/`:
| File | Topic | Highlights |
|---|---|---|
| `hello-world.ytml` | Minimal intro | Starter template |
| `code-tutorial.ytml` | Async/await | Code blocks + Mermaid sequence |
| `data-explainer.ytml` | Data pipelines | Animated stat bars + Mermaid flow |
| `product-launch.ytml` | Release announcement | `<global-music>`, card grid |
| `git-workflow.ytml` | Git branching | Code + Mermaid git graph, `<music>` |
| `youtube-channel-intro.ytml` | Channel trailer | Intro sting + background loop |
| `rag-explainer.ytml` | RAG / AI | Full pipeline, 3 code slides |
| `typescript-generics.ytml` | TypeScript | 5 code slides + type-flow diagram |

**Claude AI skill**
- `.claude/commands/ytml.md` — a Claude Code slash-command (`/ytml`) that teaches Claude the complete YTML spec. Claude can generate, save, and describe any YTML video from a plain-English description.

**Pipeline UX**
- Step-by-step progress display with elapsed time for each of the 5 pipeline stages.

---

### Fixed

| # | Bug | File |
|---|---|---|
| 1 | HTML comments (`<!-- -->`) in `.ytml` files crashed the XML parser with `not well-formed` | `interpretron/parser.py` |
| 2 | `<segment>` tag was silently ignored — only the legacy `<composite>` alias was recognised | `interpretron/parser.py` |
| 3 | ~10 % white border on all sides of every video frame and preview | `animagic/html_preprocesor.py` |
| 4 | `preview.html` had an empty `<head>` — Mermaid diagrams and syntax highlighting did not render | `animagic/html_preprocesor.py` |
| 5 | Typewriter animation showed nothing — CSS hid all `pre code span` including Prism's outer token wrappers; revealing an inner span had no effect because the parent remained `opacity: 0` | `assets/js/typewriter_effect.js` |
| 6 | `ytml --resume <uuid>` threw `TypeError` (missing required `config` positional argument) | `conductor/conductor.py` |
| 7 | CLI raised `FileNotFoundError` when `get_config_from_file()` was called before the `-i` argument was validated | `cli.py` |
| 8 | `assets/` directory was listed in `.gitignore`, causing `typewriter_effect.js`, `prism.js`, and `mermaid_init.js` to be excluded from the repository | `.gitignore` |

---

### Changed

- `HtmlPreprocessor._get_head_tag()` now accepts `html_content` as its first parameter so CDN tags are computed from actual frame content rather than a config list.
- `Conductor` step banners replaced with a cleaner `[SKIP]` / step N of 5 format with timing.
- Heavy voice-forge imports (`gTTSVocalForge`, `ElevenLabsVocalForge`) moved out of `conductor.py` — they are injected by `cli.py`, not imported internally.
- `Animagic.render_animation` and `render_frame` share a single `_setup_page()` helper that handles `networkidle` waiting, Mermaid SVG readiness, and Prism autoloader completion.

---

### Repo / tooling

- Removed stale venvs (`newenv/` — Python 3.14, incomplete), duplicate build artifacts (`ytml.egg-info/`, `setup copy.py`), and generated test outputs (`*.mp4`, `preview.html`, `tmp/`).
- `my-ytml-video/` test project now has its own Python 3.12 venv (`venv/`) for testing the deployed package independently of the dev environment.
- `.gitignore` consolidated: `__pycache__/`, `*.mp4`, `preview.html`, `tmp/` now covered globally; stray `assets/` exclusion removed.

---

## [0.2.13] — 2025-03

_Previous release — see git history._

---

[0.3.0]: https://github.com/your-org/ytml-toolkit/compare/v0.2.13...v0.3.0
[0.2.13]: https://github.com/your-org/ytml-toolkit/releases/tag/v0.2.13
