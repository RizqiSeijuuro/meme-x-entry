#!/usr/bin/env python3
"""
build_meme.py -- gta6-meme-x-01 entry meme generator.

Downloads make.fun's ghost mascot press asset and composes a 1080x1080
Vice-City-sunset-style GTA6 meme around it, with bold outlined caption
text pitching make.fun and carrying the play code.

Usage:
    curl -sS -o ghost.png https://make.fun/press/mark-1024.png
    python3 build_meme.py
"""

import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
GHOST_PATH = ROOT / "ghost.png"
OUT_PATH = ROOT / "meme.png"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

W = H = 1080

PLAY_CODE = "makefun-binder-balloon-hiker"
HANDLE = "@makefunai"

TOP_LINE = "13 YEARS. ONE 150GB PRELOAD. ZERO SICK DAYS LEFT TO FAKE."
MID_LINE = "MY AI AGENT ALREADY CASHED OUT A GTA6 BOUNTY ON MAKE.FUN"
BOTTOM_LINE = f"{PLAY_CODE}  ·  {HANDLE}"


def ensure_ghost_png():
    """Download make.fun's ghost mascot press asset if not already present."""
    if GHOST_PATH.exists() and GHOST_PATH.stat().st_size > 0:
        return
    subprocess.run(
        ["curl", "-sS", "-o", str(GHOST_PATH), "https://make.fun/press/mark-1024.png"],
        check=True,
        cwd=ROOT,
    )


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))


def build_sky(draw):
    """Orange top -> magenta mid -> purple bottom vertical gradient."""
    orange = (255, 140, 40)
    magenta = (210, 50, 130)
    purple = (55, 25, 95)
    horizon = int(H * 0.62)
    for y in range(horizon):
        t = y / horizon
        if t < 0.5:
            color = lerp_color(orange, magenta, t / 0.5)
        else:
            color = lerp_color(magenta, purple, (t - 0.5) / 0.5)
        draw.line([(0, y), (W, y)], fill=color)
    # ground band below horizon, deep purple/near-black for the skyline to sit on
    for y in range(horizon, H):
        t = (y - horizon) / (H - horizon)
        color = lerp_color(purple, (18, 10, 30), t)
        draw.line([(0, y), (W, y)], fill=color)
    return horizon


def build_sun(img, draw, horizon):
    """Big sun straddling the horizon with horizontal sunset bands."""
    cx, cy, r = W // 2, horizon - 40, 230
    sun_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(sun_layer)
    sdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 221, 120, 255))
    # inner warmer core
    r2 = int(r * 0.7)
    sdraw.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(255, 190, 90, 255))
    # horizontal sunset bands cut across the lower half of the sun (vice-city stripes)
    band_colors = [
        (255, 120, 60, 255),
        (235, 70, 110, 255),
        (190, 40, 120, 255),
        (140, 30, 120, 255),
        (90, 20, 100, 255),
    ]
    band_h = 14
    gap = 12
    y = cy - 10
    bi = 0
    while y < cy + r:
        bdraw_color = band_colors[bi % len(band_colors)]
        sdraw.rectangle([cx - r, y, cx + r, y + band_h], fill=bdraw_color)
        y += band_h + gap
        bi += 1
    mask = Image.new("L", (W, H), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    img.paste(sun_layer, (0, 0), Image.composite(sun_layer, Image.new("RGBA", (W, H), (0, 0, 0, 0)), mask))
    return cx, cy, r


def build_skyline(draw, horizon):
    """Stylized building silhouette along the bottom with lit windows."""
    import random
    random.seed(42)
    x = 0
    base_color = (20, 10, 35)
    buildings = []
    while x < W:
        bw = random.randint(60, 140)
        bh = random.randint(120, 340)
        buildings.append((x, bw, bh))
        x += bw + random.randint(-6, 4)

    for (bx, bw, bh) in buildings:
        top = H - bh
        draw.rectangle([bx, top, bx + bw, H], fill=base_color)
        # lit windows
        win_w, win_h = 10, 14
        pad = 8
        wx = bx + pad
        while wx + win_w < bx + bw - pad:
            wy = top + pad + 20
            while wy + win_h < H - pad:
                if random.random() < 0.35:
                    lit = random.choice([
                        (255, 220, 120), (255, 180, 90), (255, 240, 180),
                    ])
                    draw.rectangle([wx, wy, wx + win_w, wy + win_h], fill=lit)
                wy += win_h + 10
            wx += win_w + 10
    # a few taller antenna/spire accents
    for (bx, bw, bh) in buildings[::5]:
        top = H - bh
        cx = bx + bw // 2
        draw.line([(cx, top), (cx, top - 40)], fill=base_color, width=4)


def paste_ghost_with_glow(img):
    """Paste the make.fun ghost mascot lower-middle with a soft white glow."""
    ghost = Image.open(GHOST_PATH).convert("RGBA")
    g_size = 460
    ghost = ghost.resize((g_size, g_size), Image.LANCZOS)

    gx = (W - g_size) // 2
    gy = H - g_size - 70

    # glow: blurred white silhouette of the ghost's alpha, oversized, behind it
    glow_scale = 1.35
    glow_size = int(g_size * glow_scale)
    alpha = ghost.split()[-1]
    alpha_big = alpha.resize((glow_size, glow_size), Image.LANCZOS)
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    white_shape = Image.new("RGBA", (glow_size, glow_size), (255, 255, 255, 0))
    white_shape.putalpha(alpha_big)
    # boost opacity for a strong glow core
    r, g, b, a = white_shape.split()
    a = a.point(lambda p: min(255, int(p * 1.6)))
    white_shape = Image.merge("RGBA", (r, g, b, a))
    blurred = white_shape.filter(ImageFilter.GaussianBlur(28))
    glx = (W - glow_size) // 2
    gly = gy - (glow_size - g_size) // 2
    glow_layer.paste(blurred, (glx, gly), blurred)
    img.alpha_composite(glow_layer)

    # second tighter, brighter glow pass for punch close to the mascot edge
    tight_scale = 1.1
    tight_size = int(g_size * tight_scale)
    alpha_tight = alpha.resize((tight_size, tight_size), Image.LANCZOS)
    tight_shape = Image.new("RGBA", (tight_size, tight_size), (255, 255, 255, 0))
    tight_shape.putalpha(alpha_tight)
    tight_blur = tight_shape.filter(ImageFilter.GaussianBlur(10))
    tlx = (W - tight_size) // 2
    tly = gy - (tight_size - g_size) // 2
    tight_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tight_layer.paste(tight_blur, (tlx, tly), tight_blur)
    img.alpha_composite(tight_layer)

    img.alpha_composite(ghost, (gx, gy))


def fit_font(draw, text, max_width, start_size, min_size, font_path=FONT_PATH):
    """Shrink font size until textlength(text) <= max_width."""
    size = start_size
    while size > min_size:
        font = ImageFont.truetype(font_path, size)
        if draw.textlength(text, font=font) <= max_width:
            return font, size
        size -= 2
    return ImageFont.truetype(font_path, min_size), min_size


def wrap_to_width(draw, text, font, max_width):
    """Greedy word-wrap so every produced line fits max_width at this font."""
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_outlined_text_block(draw, lines, font, center_x, top_y, line_gap,
                              fill=(255, 255, 255, 255), outline=(10, 10, 10, 255),
                              outline_w=4):
    y = top_y
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lh = bbox[3] - bbox[1]
        line_heights.append(lh)
    for i, line in enumerate(lines):
        w = draw.textlength(line, font=font)
        x = center_x - w / 2
        # outline via offset passes
        for dx in range(-outline_w, outline_w + 1):
            for dy in range(-outline_w, outline_w + 1):
                if dx == 0 and dy == 0:
                    continue
                if dx * dx + dy * dy > outline_w * outline_w + 1:
                    continue
                draw.text((x + dx, y + dy), line, font=font, fill=outline)
        draw.text((x, y), line, font=font, fill=fill)
        y += line_heights[i] + line_gap
    return y


def main():
    ensure_ghost_png()

    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    bg_draw = ImageDraw.Draw(img)
    horizon = build_sky(bg_draw)
    build_sun(img, bg_draw, horizon)
    build_skyline(bg_draw, horizon)

    paste_ghost_with_glow(img)

    draw = ImageDraw.Draw(img)
    margin = 48
    max_text_width = W - 2 * margin  # 984px safety margin for all captions

    # --- Top joke line: GTA6-specific, may wrap to 2 lines ---
    top_font, _ = fit_font(draw, TOP_LINE, max_text_width, start_size=64, min_size=34)
    top_lines = wrap_to_width(draw, TOP_LINE, top_font, max_text_width)
    # re-verify every wrapped line actually fits; shrink further if not
    while any(draw.textlength(l, font=top_font) > max_text_width for l in top_lines):
        size = top_font.size - 2
        top_font = ImageFont.truetype(FONT_PATH, size)
        top_lines = wrap_to_width(draw, TOP_LINE, top_font, max_text_width)

    y = draw_outlined_text_block(
        draw, top_lines, top_font, center_x=W / 2, top_y=40, line_gap=8,
        fill=(255, 250, 230, 255), outline=(25, 10, 35, 255), outline_w=5,
    )

    # --- Middle pitch line, placed above the mascot's glow area ---
    mid_font, _ = fit_font(draw, MID_LINE, max_text_width, start_size=46, min_size=26)
    mid_lines = wrap_to_width(draw, MID_LINE, mid_font, max_text_width)
    while any(draw.textlength(l, font=mid_font) > max_text_width for l in mid_lines):
        size = mid_font.size - 2
        mid_font = ImageFont.truetype(FONT_PATH, size)
        mid_lines = wrap_to_width(draw, MID_LINE, mid_font, max_text_width)

    mid_top = y + 14
    draw_outlined_text_block(
        draw, mid_lines, mid_font, center_x=W / 2, top_y=mid_top, line_gap=6,
        fill=(255, 255, 255, 255), outline=(20, 10, 40, 255), outline_w=4,
    )

    # --- Bottom small line: play code + handle, single line near the bottom edge ---
    bottom_font, _ = fit_font(draw, BOTTOM_LINE, max_text_width, start_size=30, min_size=16)
    bottom_w = draw.textlength(BOTTOM_LINE, font=bottom_font)
    assert bottom_w <= max_text_width, "bottom line overflow"
    bottom_y = H - 44 - (draw.textbbox((0, 0), BOTTOM_LINE, font=bottom_font)[3])
    draw_outlined_text_block(
        draw, [BOTTOM_LINE], bottom_font, center_x=W / 2, top_y=bottom_y, line_gap=0,
        fill=(255, 230, 160, 255), outline=(10, 5, 20, 255), outline_w=3,
    )

    # Final safety check: nothing exceeds canvas width
    for lines, font in ((top_lines, top_font), (mid_lines, mid_font), ([BOTTOM_LINE], bottom_font)):
        for line in lines:
            lw = draw.textlength(line, font=font)
            if lw > max_text_width:
                print(f"WARNING: line overflow: {line!r} width={lw}", file=sys.stderr)

    img.convert("RGB").save(OUT_PATH, "PNG")
    print(f"Wrote {OUT_PATH} ({W}x{H})")


if __name__ == "__main__":
    main()
