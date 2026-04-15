"""Generate the Kaggle Media Gallery cover image for the DueCare submission.

1200 x 675 PNG, consistent with the demo's dark theme.
Design goals:
- Title "DueCare" dominant and legible at thumbnail size
- Subtitle explains the project in one line
- Four headline stats as the visual bed
- "Privacy is non-negotiable" — the rules-matching tagline
- No migrant-worker imagery; safe for global audience
- Readable at 150x84 thumbnail
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "media"
OUTPUT_PATH = OUTPUT_DIR / "cover_1200x675.png"

W, H = 1200, 675
BG = (15, 17, 23)           # --bg  #0f1117
SURFACE = (26, 29, 39)      # --surface #1a1d27
BORDER = (42, 45, 58)       # --border  #2a2d3a
PRIMARY = (79, 140, 255)    # --primary #4f8cff
DANGER = (255, 79, 79)      # --danger  #ff4f4f
SUCCESS = (79, 255, 140)    # --success #4fff8c
TEXT = (228, 230, 237)      # --text    #e4e6ed
TEXT_DIM = (143, 147, 162)  # --text-dim #8f93a2


def _try_fonts(candidates: list[tuple[str, int]]) -> ImageFont.ImageFont:
    """Return the first loadable font, falling back to the default."""
    for name, size in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rounded_rect(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int],
                   radius: int, fill: tuple[int, int, int], outline=None) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def build() -> Path:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # --- background geometry: a subtle grid of dots, plus a left-side shield wedge
    for x in range(0, W, 40):
        for y in range(0, H, 40):
            draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(24, 27, 36))

    # Subtle colored accent bar on the left edge (identity strip)
    draw.rectangle((0, 0, 12, H), fill=PRIMARY)

    # --- typography
    title_font = _try_fonts([
        ("seguisb.ttf", 140),       # Segoe UI Semibold (Windows)
        ("Helvetica-Bold.ttf", 140),
        ("Arial.ttf", 140),
    ])
    subtitle_font = _try_fonts([
        ("seguisb.ttf", 34),
        ("Helvetica.ttf", 34),
        ("Arial.ttf", 34),
    ])
    stat_font = _try_fonts([
        ("seguisb.ttf", 30),
        ("Helvetica-Bold.ttf", 30),
        ("Arial.ttf", 30),
    ])
    stat_label_font = _try_fonts([
        ("segoeui.ttf", 18),
        ("Helvetica.ttf", 18),
        ("Arial.ttf", 18),
    ])
    tag_font = _try_fonts([
        ("seguisbi.ttf", 28),       # Semibold italic
        ("Helvetica-BoldOblique.ttf", 28),
        ("Arial.ttf", 28),
    ])

    # --- title block (left-aligned, top-third)
    title_x = 70
    title_y = 90
    draw.text((title_x, title_y), "DueCare", font=title_font, fill=TEXT)

    # Inline accent under the title
    draw.rectangle((title_x, title_y + 165, title_x + 160, title_y + 173), fill=PRIMARY)

    subtitle_y = title_y + 200
    draw.text((title_x, subtitle_y),
              "An agentic safety harness for on-device LLMs",
              font=subtitle_font, fill=TEXT_DIM)
    draw.text((title_x, subtitle_y + 40),
              "Built for frontline NGOs, regulators, and labor ministries",
              font=subtitle_font, fill=TEXT_DIM)

    # --- four stat tiles (bottom-left)
    stats = [
        ("74,567", "trafficking prompts", PRIMARY),
        ("12", "autonomous agents", PRIMARY),
        ("8", "PyPI packages", PRIMARY),
        ("$0", "per evaluation", SUCCESS),
    ]
    tile_w, tile_h = 245, 105
    tile_gap = 20
    tile_y = 430
    for idx, (big, small, accent) in enumerate(stats):
        tx = title_x + idx * (tile_w + tile_gap)
        _rounded_rect(draw, (tx, tile_y, tx + tile_w, tile_y + tile_h),
                      radius=10, fill=SURFACE, outline=BORDER)
        draw.text((tx + 16, tile_y + 14), big, font=stat_font, fill=accent)
        draw.text((tx + 16, tile_y + 58), small, font=stat_label_font, fill=TEXT_DIM)

    # --- Tagline (bottom, italic, dim)
    tag_y = H - 80
    draw.text((title_x, tag_y),
              "\u201CPrivacy is non-negotiable.\u201D",
              font=tag_font, fill=TEXT)
    draw.text((title_x, tag_y + 35),
              "Gemma 4 Good Hackathon \u2022 github.com/TaylorAmarelTech/gemma4_comp",
              font=stat_label_font, fill=TEXT_DIM)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT_PATH, "PNG", optimize=True)
    return OUTPUT_PATH


if __name__ == "__main__":
    out = build()
    print(f"Wrote cover image: {out}")
    print(f"Size: {out.stat().st_size / 1024:.1f} KB")
