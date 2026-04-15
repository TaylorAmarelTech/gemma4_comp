"""Generate the browser extension icon set — 16, 32, 48, 128 px PNG.

Minimalist "DC" glyph in the DueCare brand color on a rounded dark tile,
sized for MV3 extension manifests.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent.parent / "deployment" / "browser_extension" / "icons"
SIZES = [16, 32, 48, 128]

BG = (15, 17, 23)           # --bg
PRIMARY = (79, 140, 255)    # --primary
TEXT = (228, 230, 237)      # --text


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("seguisb.ttf", "Helvetica-Bold.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_icon(size: int) -> Path:
    # Render at 4x for supersampling, then downscale to target.
    scale = 4
    full = size * scale
    img = Image.new("RGBA", (full, full), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded-square background
    draw.rounded_rectangle((0, 0, full - 1, full - 1),
                           radius=int(full * 0.2), fill=BG)

    # Accent stripe on the left (brand identity)
    stripe_w = max(2, int(full * 0.06))
    draw.rectangle((int(full * 0.12), int(full * 0.14),
                    int(full * 0.12) + stripe_w, int(full * 0.86)),
                   fill=PRIMARY)

    # "DC" glyph — sized to fit
    glyph = "DC"
    fsize = int(full * 0.55)
    font = _font(fsize)
    # Measure
    bbox = draw.textbbox((0, 0), glyph, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (full - tw) // 2 + int(full * 0.05)
    ty = (full - th) // 2 - bbox[1]
    draw.text((tx, ty), glyph, font=font, fill=TEXT)

    img = img.resize((size, size), Image.LANCZOS)
    out = OUT_DIR / f"icon{size}.png"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out


if __name__ == "__main__":
    for s in SIZES:
        p = build_icon(s)
        print(f"Wrote {p} ({p.stat().st_size} B)")
