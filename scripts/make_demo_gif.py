# -*- coding: utf-8 -*-
"""Render docs/demo.gif — a terminal-animation demo for askill (README hero).

Pure Pillow, no external deps. ASCII-only glyphs (Consolas-safe):
no checkmarks/arrows to avoid tofu, after the social-preview lesson.
"""
import io

from PIL import Image, ImageDraw, ImageFont

W, H = 800, 460
FPS_MS = 100  # 10 fps
BG = (13, 17, 23)
TERM = (9, 12, 18)
BORDER = (48, 54, 61)
WHITE = (230, 237, 243)
GREEN = (52, 211, 153)
VIOLET = (139, 92, 246)
GREY = (139, 148, 158)
YELLOW = (255, 189, 46)

_cache = {}


def mono(size, bold=False):
    key = f"{'b' if bold else 'r'}{size}"
    if key not in _cache:
        name = "consolab.ttf" if bold else "consola.ttf"
        try:
            _cache[key] = ImageFont.truetype(rf"C:\Windows\Fonts\{name}", size)
        except OSError:
            _cache[key] = ImageFont.load_default()
    return _cache[key]


F_CMD = mono(19)
F_OUT = mono(17)
F_TITLE = mono(15)

LH = 27  # line height
PAD = 26
TOP = 62  # first text baseline area below title bar


def new_frame():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 6, W - 6, H - 6], radius=12, fill=TERM, outline=BORDER, width=2)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([26 + i * 24, 22, 38 + i * 24, 34], fill=c)
    t = "askill — agent skill manager"
    tw = d.textlength(t, font=F_TITLE)
    d.text(((W - tw) / 2, 20), t, font=F_TITLE, fill=GREY)
    return im, d


def render_scene(lines, cursor=None, cursor_on=True):
    """lines: list of (text, color, bold). cursor: (row, col) block cursor."""
    im, d = new_frame()
    y = TOP
    for i, (text, color, bold) in enumerate(lines):
        font = mono(19, bold) if bold else mono(17)
        d.text((PAD, y), text, font=font, fill=color)
        if cursor and cursor[0] == i and cursor_on:
            cx = PAD + d.textlength(text, font=font)
            d.rectangle([cx + 2, y + 1, cx + 12, y + 21], fill=WHITE)
        y += LH
    return im


PROMPT_COLOR = GREEN
CMD_COLOR = WHITE
OUT = (WHITE, False)


def scene_frames(cmd, outputs, hold=16, type_speed=1, out_speed=2):
    """Typewriter the command, then reveal output lines, then hold."""
    frames = []
    # typing phase
    for n in range(0, len(cmd) + 1, type_speed):
        frames.append(render_scene([("$ " + cmd[:n], PROMPT_COLOR, True)], cursor=(0, 0)))
    # output reveal
    for n in range(1, len(outputs) + 1):
        lines = [("$ " + cmd, PROMPT_COLOR, True)] + outputs[:n]
        frames.append(render_scene(lines, cursor=(len(outputs[:n]), 0)))
    # hold with blinking cursor
    for k in range(hold):
        lines = [("$ " + cmd, PROMPT_COLOR, True)] + outputs
        frames.append(render_scene(lines, cursor=(len(outputs), 0), cursor_on=(k % 6) < 4))
    return frames


# ---- Scene 1: askill status -------------------------------------------------
s1_out = [
    ("Central repo: ~/.agents/skills  (4 skills)", GREY, False),
    ("", WHITE, False),
    ("  skill             products   grade", WHITE, True),
    ("  pdf               15/15      A  safe", WHITE, False),
    ("  data-analysis     15/15      A  safe", WHITE, False),
    ("  code-review       14/15      B  safe", WHITE, False),
    ("  english-memory    15/15      A  safe", WHITE, False),
]
f1 = scene_frames("askill status", s1_out, hold=18)

# ---- Scene 2: askill sync pdf ------------------------------------------------
s2_out = [
    ("  autoclaw      linked", WHITE, False),
    ("  kimi          linked", WHITE, False),
    ("  minimax       native", WHITE, False),
    ("  trae-cn       linked", WHITE, False),
    ("  codebuddy     linked", WHITE, False),
    ("  qwenwork      linked", WHITE, False),
    ("  ... +9 more products", GREY, False),
    ("  pdf -> synced to 15/15 products", GREEN, True),
]
f2 = scene_frames("askill sync pdf", s2_out, hold=18)

# ---- Scene 3: install with auto audit ---------------------------------------
s3_out = [
    ("  downloading anthropics/skills ...", GREY, False),
    ("  installed pdf -> ~/.agents/skills/pdf", WHITE, False),
    ("", WHITE, False),
    ("  [check] spec: pass", YELLOW, False),
    ("  [check] security: 98/100 (A, safe)", GREEN, False),
    ("  [check] frontmatter: 15 products ok", GREEN, False),
    ("", WHITE, False),
    ("  run `askill sync pdf` to distribute", GREY, False),
]
f3 = scene_frames("askill install anthropics/skills@pdf", s3_out, hold=22)

# ---- separators: brief blank terminal ---------------------------------------
sep = [render_scene([("$ ", PROMPT_COLOR, True)], cursor=(0, 0)) for _ in range(4)]

all_frames = f1 + sep + f2 + sep + f3

# ---- save GIF ----------------------------------------------------------------
buf = io.BytesIO()
all_frames[0].save(
    buf,
    format="GIF",
    save_all=True,
    append_images=all_frames[1:],
    duration=FPS_MS,
    loop=0,
    optimize=True,
)
data = buf.getvalue()
out = r"D:\pythonproject\agent-skill-manager\docs\demo.gif"
with open(out, "wb") as f:
    f.write(data)
print(f"frames={len(all_frames)} duration={len(all_frames) * FPS_MS / 1000:.1f}s size={len(data) / 1024:.0f}KB")
