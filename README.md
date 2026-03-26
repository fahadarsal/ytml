# YTML — YouTube Markup Language

> **Turn a `.ytml` script into a production-ready video with one command.**

YTML is a code-first video automation toolkit. Write video slides in HTML, add `<voice>` tags for AI narration, sprinkle in CSS animations — then let the CLI do the rest.

```sh
pip install ytml-toolkit
ytml init my-video
cd my-video
ytml -i video.ytml -o output.mp4 --use-gtts
```

---

## Why YTML?

| Without YTML | With YTML |
|---|---|
| Open a timeline editor | Write a `.ytml` text file |
| Drag clips, tweak keyframes | CSS animations just work |
| Record or manually sync audio | `<voice>` tag → auto-generated narration |
| Export, wait, re-export | One CLI command |
| Can't version-control a project file | Plain text — git diff it |

---

## Quick Start

### 1. Install

```sh
pip install ytml-toolkit
playwright install chromium   # headless browser for rendering
```

> **Need Eleven Labs AI voices?** Set your key:
> ```sh
> export ELEVEN_LABS_API_KEY="your-key"
> ```
> No key? Use `--use-gtts` for free Google TTS.

### 2. Scaffold a project

```sh
ytml init my-video
cd my-video
```

This creates:
```
my-video/
├── video.ytml   # starter script — edit this
├── assets/      # put images, audio, fonts here
└── .env         # add ELEVEN_LABS_API_KEY here
```

### 3. Write your script

```html
<ytml>
  <config>
    FRAME_RATE=30
    VIDEO_WIDTH=1920
    VIDEO_HEIGHT=1088
    ENABLE_AI_VOICE=False
  </config>

  <segment>
    <frame duration="4s">
      <div style="display:flex; justify-content:center; align-items:center;
                  height:100vh; background:#1a1a2e; font-family:'Segoe UI',sans-serif;">
        <h1 style="color:#fff; font-size:4em; animation:fadeIn 1.5s ease-out;">
          Hello, World!
        </h1>
      </div>
      <style>
        @keyframes fadeIn {
          from { opacity:0; transform:translateY(30px); }
          to   { opacity:1; transform:translateY(0); }
        }
      </style>
    </frame>
    <voice start="0.5s" end="4s">Hello and welcome! This was generated with YTML.</voice>
  </segment>
</ytml>
```

### 4. Render

```sh
ytml -i video.ytml -o output.mp4 --use-gtts
```

---

## CLI Reference

```
ytml init [name]            scaffold a new project
ytml -i <file> -o <out>     render a video
  --use-gtts                free Google TTS (no API key needed)
  --skip <steps>            skip: parse voiceover render sync compose
  --resume <uuid>           continue an interrupted job
  --job <uuid>              reuse voiceovers from another job
  --preview                 export HTML preview only
  --verbose                 show detailed logs
  --version                 show version
```

---

## YTML Tag Reference

| Tag | What it does |
|---|---|
| `<segment>` | One video segment (a logical scene) |
| `<frame duration="Xs">` | HTML/CSS slide displayed for X seconds |
| `<voice start="Xs" end="Xs">` | Narration text spoken over the segment |
| `<music src="..." start="Xs" end="Xs">` | Background audio |
| `<pause duration="Xs">` | Silent pause between segments |
| `<transition type="fade" duration="Xs">` | Fade/transition between segments |
| `<template id="...">` | Define a reusable component |
| `<use template="...">` | Inject a template |
| `<mermaid>` | Render a Mermaid.js diagram |
| `<code>` | Syntax-highlighted code block |
| `<global-music src="...">` | Music that plays across the whole video |
| `<config>` | Override default settings |

### Config Options

```
FRAME_RATE=30              frames per second
VIDEO_WIDTH=1920           output width
VIDEO_HEIGHT=1088          output height
BITRATE=5000k              video bitrate
ENABLE_AI_VOICE=True       use Eleven Labs (requires API key)
AI_VOICE_ID=...            Eleven Labs voice ID
LOG_LEVEL=INFO             DEBUG | INFO | WARNING | ERROR
```

---

## Sample Scripts

| File | Description |
|---|---|
| [`hello-world.ytml`](samples/hello-world.ytml) | Minimal 3-slide intro video |
| [`code-tutorial.ytml`](samples/code-tutorial.ytml) | Tech tutorial with code blocks and Mermaid diagram |
| [`data-explainer.ytml`](samples/data-explainer.ytml) | Animated stats and pipeline diagram |

---

## Example — Mermaid Diagram Slide

```html
<segment>
  <frame duration="6s" static="true">
    <div style="height:100vh; background:#0f0f23; display:flex;
                flex-direction:column; align-items:center; justify-content:center;
                font-family:'Segoe UI',sans-serif; padding:40px;">
      <h2 style="color:#89b4fa; font-size:2em; margin-bottom:24px;">System Architecture</h2>
      <mermaid>
        graph LR
          Client --> API
          API --> Auth
          API --> DB[(Database)]
      </mermaid>
    </div>
  </frame>
  <voice start="0.5s" end="6s">
    Requests flow through the API gateway, which delegates to auth and the database.
  </voice>
</segment>
```

---

## Example — Reusable Branding Template

```html
<ytml>
  <template id="lower-third">
    <div style="position:absolute; bottom:0; width:100%; padding:12px 40px;
                background:rgba(0,0,0,0.7); display:flex; align-items:center; gap:16px;">
      <span style="color:#e2a428; font-weight:700;">MY CHANNEL</span>
      <span style="color:#666;">|</span>
      <span style="color:#aaa; font-size:0.9em;">Subscribe for more</span>
    </div>
  </template>

  <segment>
    <frame duration="5s">
      <div style="position:relative; height:100vh; background:#111;
                  display:flex; align-items:center; justify-content:center;">
        <h1 style="color:#fff; font-size:3em;">My Video Title</h1>
        <use template="lower-third" />
      </div>
    </frame>
    <voice start="0.5s" end="5s">Welcome to this video.</voice>
  </segment>
</ytml>
```

---

## How the Pipeline Works

```
.ytml file
   │
   ▼ 1. Parse        YTMLParser extracts segments, frames, voice & music metadata
   ▼ 2. Voiceover    Eleven Labs or gTTS generates .mp3 files for every <voice> tag
   ▼ 3. Render       Playwright screenshots each HTML frame → image sequence → .mp4
   ▼ 4. Sync         FFmpeg merges voiceover audio at exact timestamps
   ▼ 5. Compose      Segments concatenated; background music mixed with ducking
   │
   ▼ output.mp4
```

Each step saves its state to `tmp/<job-id>/`. Use `--skip` or `--resume` to rerun from any step without redoing expensive work.

---

## Links

- **Docs:** https://ytml.mergeconflict.tech/docs/intro
- **Templates:** https://ytml.mergeconflict.tech/templates
- **GitHub:** https://github.com/fahadarsal/ytml
- **PyPI:** https://pypi.org/project/ytml-toolkit/

---

## License

MIT
