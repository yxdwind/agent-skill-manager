# -*- coding: utf-8 -*-
"""Render docs/social-preview.png (1280x640) for agent-skill-manager."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640
DARK = (13, 17, 23)
GRAD_TOP = (24, 32, 46)
ACCENT = (139, 92, 246)      # violet 8b5cf6
ACCENT2 = (52, 211, 153)     # emerald 34d399
WHITE = (240, 246, 252)
GREY = (139, 148, 158)

img = Image.new("RGB", (W, H), DARK)
d = ImageDraw.Draw(img)

# --- vertical gradient background (banded, 4px steps) ---
for y in range(0, H, 4):
    t = y / H
    r = int(GRAD_TOP[0] + (DARK[0] - GRAD_TOP[0]) * t)
    g = int(GRAD_TOP[1] + (DARK[1] - GRAD_TOP[1]) * t)
    b = int(GRAD_TOP[2] + (DARK[2] - GRAD_TOP[2]) * t)
    d.rectangle([0, y, W, y + 4], fill=(r, g, b))

# --- faint diagonal grid for texture ---
for i in range(-H, W, 80):
    d.line([(i, 0), (i + H, H)], fill=(22, 29, 41), width=1)
    d.line([(i + H, 0), (i, H)], fill=(22, 29, 41), width=1)

_font_cache = {}


def mono(size, bold=True):
    key = f"{'b' if bold else 'r'}{size}"
    if key not in _font_cache:
        name = "consolab.ttf" if bold else "consola.ttf"
        try:
            _font_cache[key] = ImageFont.truetype(rf"C:\Windows\Fonts\{name}", size)
        except OSError:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


def zh(size, bold=False):
    key = f"zh{'b' if bold else 'r'}{size}"
    if key not in _font_cache:
        name = "msyhbd.ttc" if bold else "msyh.ttc"
        try:
            _font_cache[key] = ImageFont.truetype(rf"C:\Windows\Fonts\{name}", size)
        except OSError:
            _font_cache[key] = mono(size)
    return _font_cache[key]


# --- logo framed as app icon (top-left) ---
logo = Image.open(r"D:\pythonproject\agent-skill-manager\docs\logo.png").convert("RGBA")
logo.thumbnail((128, 128), Image.LANCZOS)
d.rounded_rectangle([72, 66, 232, 226], radius=28, fill=(255, 255, 255),
                    outline=(48, 54, 61), width=2)
img.paste(logo, (88, 82), logo)

# --- title ---
d.text((80, 262), "Agent Skill Manager", font=mono(62), fill=WHITE)

# --- tagline (CJK) ---
d.text((84, 356), "\u4e00\u6b21\u5f00\u53d1\uff0c\u5341\u4e94\u7aef\u540c\u6b65", font=zh(34, bold=True), fill=ACCENT2)
d.text((84, 412), "Cross-platform skill sync for", font=mono(25, bold=False), fill=GREY)
d.text((84, 448), "15 Chinese AI agent products", font=mono(25, bold=False), fill=GREY)

# --- badges row ---
badges = [
    ("15 products", ACCENT),
    ("Zero deps", ACCENT2),
    ("Python 3.10+", (59, 130, 246)),
    ("MIT", GREY),
]
x, y, bh, bw = 84, 512, 44, 210
for label, color in badges:
    d.rounded_rectangle([x, y, x + bw, y + bh], radius=10, fill=(21, 28, 40), outline=color, width=2)
    tw = d.textlength(label, font=mono(21))
    d.text((x + (bw - tw) / 2, y + 10), label, font=mono(21), fill=WHITE)
    x += bw + 18

# --- right side: terminal window mock ---
tx, ty, tw_, th = 790, 120, 410, 360
d.rounded_rectangle([tx, ty, tx + tw_, ty + th], radius=14, fill=(9, 12, 18),
                    outline=(48, 54, 61), width=2)
for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
    d.ellipse([tx + 20 + i * 24, ty + 16, tx + 32 + i * 24, ty + 28], fill=c)
d.text((tx + 20, ty + 48), "$ askill sync", font=mono(23, bold=False), fill=ACCENT2)
rows = ["autoclaw", "kimi", "minimax", "trae", "codebuddy", "dumate (zip)", "... +9 more"]
ly = ty + 96
for name in rows:
    if name.startswith("..."):
        d.text((tx + 46, ly), name, font=mono(21, bold=False), fill=GREY)
    else:
        d.ellipse([tx + 22, ly + 8, tx + 34, ly + 20], fill=ACCENT2)  # status dot, no glyph risk
        d.text((tx + 46, ly), name, font=mono(21, bold=False), fill=WHITE)
    ly += 34
d.text((tx + 20, ly + 6), "15/15 synced", font=mono(21), fill=ACCENT2)

# --- repo url under terminal, fills bottom-right void (right-aligned to terminal edge) ---
_url = "github.com/yxdwind/agent-skill-manager"
_urlw = d.textlength(_url, font=mono(20, bold=False))
d.text((tx + tw_ - _urlw, ty + th + 28), _url, font=mono(20, bold=False), fill=(125, 137, 150))

img.save(r"D:\pythonproject\agent-skill-manager\docs\social-preview.png", optimize=True)
print("saved social-preview.png")
