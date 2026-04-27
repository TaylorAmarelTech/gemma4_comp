"""Redact evidence assets (images + video keyframes) for safe demo use.

INPUT:  evidence_raw/      (gitignored, contains raw downloads with PII)
OUTPUT: packages/duecare-llm-server/src/duecare/server/static/evidence/
        (committed, contains heavily-redacted versions safe to ship)

Implementation uses pure ffmpeg (no PIL/opencv dependency, both broken
on this Python 3.14 install). ffmpeg's `boxblur` + `scale` + `drawtext`
filters handle the entire redaction pipeline:
  - boxblur=20:2     -- aggressive blur (radius 20, 2 power passes)
  - scale=480:-2     -- downscale to 480px wide, keep aspect, even height
  - drawtext         -- 'REDACTED' watermark across center

For videos: extract N keyframes via -ss / -frames:v 1 then redact each.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "evidence_raw"
DST = (REPO_ROOT / "packages" / "duecare-llm-server" / "src"
       / "duecare" / "server" / "static" / "evidence")

BLUR = 20
TARGET_W = 480
JPG_Q = 5            # ffmpeg JPG quality (lower = better, 1-31)
WATERMARK = "REDACTED -- schematic only -- Duecare evidence"
VIDEO_FRAMES_PER_CLIP = 6
MAKE_VIDEO_STRIP = (
    os.environ.get("MAKE_VIDEO_STRIP", "0").lower() in ("1", "true", "yes"))


def _ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args],
                            capture_output=True, text=True)


def _ffprobe_duration(path: Path) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except Exception:
        return 30.0


def _find_font() -> str:
    """Locate a usable font file for ffmpeg drawtext (Windows-friendly)."""
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            # ffmpeg's drawtext on Windows requires forward slashes
            # AND a literal escape of the colon in 'C:/...'
            return c.replace("\\", "/").replace(":", "\\:")
    return ""


_FONT = _find_font()


# Build the ffmpeg vf filter chain that does our redaction
def _redact_filter() -> str:
    # 1. Downscale, 2. boxblur (radius x power), 3. drawtext watermark
    text_args = (
        f"text='{WATERMARK}'"
        f":fontcolor=#992222"
        f":box=1:boxcolor=#ffffffdd:boxborderw=8"
        f":fontsize=14"
        f":x=(w-text_w)/2"
        f":y=h-text_h-20"
    )
    if _FONT:
        text_args += f":fontfile='{_FONT}'"
    return (f"scale={TARGET_W}:-2,"
              f"boxblur={BLUR}:2,"
              f"drawtext={text_args}")


def redact_image(src_path: Path, dst_path: Path) -> dict:
    """Redact a single image. Returns metadata."""
    # ffmpeg flags: -q:v 5 = high quality; lower quality -> larger blurry blob
    proc = _ffmpeg([
        "-i", str(src_path),
        "-vf", _redact_filter(),
        "-q:v", str(JPG_Q),
        str(dst_path),
    ])
    if proc.returncode != 0 or not dst_path.exists():
        raise RuntimeError(f"ffmpeg redact failed for {src_path.name}: "
                           f"{proc.stderr[:300]}")
    return {"out_bytes": dst_path.stat().st_size}


def redact_video_keyframes(src_path: Path, dst_dir: Path,
                              slug: str,
                              n_frames: int = VIDEO_FRAMES_PER_CLIP
                              ) -> list[dict]:
    """Extract N keyframes from a video and redact each. Optionally
    also encode a redacted MP4."""
    duration = _ffprobe_duration(src_path)
    interval = max(1.0, duration / (n_frames + 1))
    out: list[dict] = []
    for i in range(n_frames):
        ts = interval * (i + 1)
        out_path = dst_dir / f"{slug}_frame_{i:02d}.jpg"
        proc = _ffmpeg([
            "-ss", f"{ts:.1f}", "-i", str(src_path),
            "-frames:v", "1",
            "-vf", _redact_filter(),
            "-q:v", str(JPG_Q),
            str(out_path),
        ])
        if proc.returncode == 0 and out_path.exists():
            out.append({
                "seq": i, "filename": out_path.name,
                "out_bytes": out_path.stat().st_size,
                "ts_seconds": round(ts, 1),
            })
    if MAKE_VIDEO_STRIP:
        out_mp4 = dst_dir / f"{slug}_redacted.mp4"
        proc = _ffmpeg([
            "-i", str(src_path),
            "-vf", f"scale={TARGET_W}:-2,boxblur={BLUR}:2",
            "-c:v", "libx264", "-crf", "32",
            "-an",                       # drop audio
            "-r", "10",                   # 10 fps
            "-preset", "fast",
            str(out_mp4),
        ])
        if proc.returncode == 0 and out_mp4.exists():
            out.append({
                "seq": -1, "filename": out_mp4.name,
                "is_video": True,
                "out_bytes": out_mp4.stat().st_size,
            })
    return out


# Asset specs
IMGUR_SPECS = [
    ("imgur_01_Qt7PomG.png", "imgur_01_bank_hongkong_wanted",
     "Bank Hongkong page -- 'WANTED' poster template (English)",
     "doxxing",
     "Predatory lender FB page publicly shaming an OFW with passport "
     "photos + full name. Pattern documented since Feb 2021. Heavily "
     "blurred to schematic-only level."),
    ("imgur_02_JKHZx9B.png", "imgur_02_bank_hongkong_wanted_v2",
     "Bank Hongkong -- second 'WANTED' post variant",
     "doxxing",
     "Same template; second post visible. User had begun manual "
     "redaction (black bars over passport thumbnails) but full name "
     "remained in body text. Re-redacted defensively here."),
    ("imgur_03_vQXz42N.png", "imgur_03_facebook_wanted_thumbnail",
     "Facebook user 'Nicole Cruz' reposting the 'WANTED' template",
     "doxxing",
     "Cropped Facebook post (Feb 24, 2021) -- same lender-shaming "
     "wording amplified by an individual user. Documents the "
     "viral-spread pattern."),
    ("imgur_04_LGRoIvq.png", "imgur_04_yoursun_caretaker_wanted",
     "Yoursun Caretaker -- 'asap pay ur overdues' shaming",
     "doxxing",
     "Two stacked posts (Apr 2024) targeting HK-based Filipina "
     "domestic helpers with passport photos + 'pay overdues' "
     "demands. Eyes-only redaction in original was insufficient -- "
     "fully blurred here."),
]

VIDEO_SPECS = [
    ("video_01_20210225_141513.mp4", "video_01_bank_hongkong_scroll",
     "Bank Hongkong page -- scroll-through screen recording",
     "doxxing",
     "~94 MB screen recording (Feb 25, 2021) scrolling through the "
     "'Bank Hongkong' Facebook page. Captures multiple 'WANTED' posts "
     "with different OFW victims. 6 evenly-spaced keyframes extracted, "
     "each heavily blurred."),
    ("video_02_20210225_152144.mp4", "video_02_indonesian_doxxing",
     "Indonesian-language doxxing post -- 'Melly Wong' page",
     "doxxing",
     "~108 MB recording showing the same template in Bahasa Indonesia: "
     "'SIAPA YANG TAHU ORANG INI' (whoever knows this person) with "
     "full name + KTP number + village location. Documents the cross-"
     "language pattern."),
    ("video_03_20210303_114223.mp4", "video_03_wang_tzu_wanted",
     "Wang Tzu page -- second predator profile",
     "doxxing",
     "~33 MB recording of the same 'WANTED' template on a different "
     "page (Wang Tzu, Mar 3 2021). Targets another named OFW. Confirms "
     "the template is industrialised across multiple coordinated actors."),
    ("video_04_20210407_213026.mp4", "video_04_followup_post",
     "Apr 2021 follow-up shaming post",
     "doxxing",
     "~25 MB recording (Apr 7 2021). Continued documentation of the "
     "pattern persisting over weeks."),
    ("video_05_20210607_181413.mp4", "video_05_summer_2021_post",
     "Jun 2021 -- long-term campaign continuation",
     "doxxing",
     "~16 MB recording (Jun 7 2021). 4-month timeline confirms this "
     "is not a one-off but an ongoing harassment campaign."),
]


def main() -> int:
    if not SRC.is_dir():
        print(f"NO source dir: {SRC}")
        return 1
    DST.mkdir(parents=True, exist_ok=True)

    items: list[dict] = []
    print(f"== IMAGES ==")
    for src_name, slug, title, category, caption in IMGUR_SPECS:
        src = SRC / src_name
        if not src.exists():
            print(f"  MISSING {src_name}, skipping")
            continue
        dst = DST / f"{slug}.jpg"
        try:
            meta = redact_image(src, dst)
            print(f"  OK{src_name} -> {dst.name}  ({meta['out_bytes']//1024} KB)")
            items.append({
                "id": slug, "kind": "image", "filename": dst.name,
                "title": title, "caption": caption, "category": category,
                "redaction_status": "REDACTED (boxblur=20, "
                                      "downscale=480w, watermarked)",
                "source_note": "Public Facebook page screenshot, "
                                  "Imgur public album.",
            })
        except Exception as e:
            print(f"  X{src_name} FAILED: {e}")

    # ---- Auto-discover Drive FB lender screenshots -----------------------
    print(f"\n== DRIVE FB LENDER SCREENSHOTS ==")
    drive_fb = sorted(SRC.glob("drive_fb_*.png"))
    for src in drive_fb:
        # Slugify the filename: drive_fb_PRIME_CREDIT_POST.png ->
        #                        drive_fb_prime_credit_post
        slug = (src.stem.lower()
                  .replace(" ", "_").replace("-", "_"))
        # Friendly display name: PRIME CREDIT POST -> "Prime Credit"
        lender = (src.stem.replace("drive_fb_", "")
                            .replace("_POST", "")
                            .replace("_DONE", "")
                            .replace("_", " ").title())
        dst = DST / f"{slug}.jpg"
        try:
            meta = redact_image(src, dst)
            print(f"  OK{src.name} -> {dst.name}  "
                  f"({meta['out_bytes']//1024} KB)")
            items.append({
                "id": slug,
                "kind": "image",
                "filename": dst.name,
                "title": f"Predatory lender FB post -- {lender}",
                "caption": "Tagalog-language predatory-lender shaming "
                              f"post (Migrasia investigation evidence). "
                              f"Lender: {lender}. Same template as Bank "
                              f"Hongkong / Yoursun Caretaker -- WANTED-"
                              f"poster framing + passport-photo collateral "
                              f"+ public-shaming demands.",
                "category": "predatory_lending",
                "redaction_status": "REDACTED (boxblur=20, downscale=480w, "
                                      "watermarked)",
                "source_note": "Field-collected public-record evidence "
                                  "of predatory-lender activity targeting "
                                  "migrant workers (~2020-2021).",
            })
        except Exception as e:
            print(f"  X{src.name} FAILED: {e}")

    print(f"\n== VIDEO KEYFRAMES ==")
    for src_name, slug, title, category, caption in VIDEO_SPECS:
        src = SRC / src_name
        if not src.exists():
            print(f"  MISSING {src_name}, skipping")
            continue
        print(f"  processing {src_name} ({src.stat().st_size//1024//1024} MB)")
        try:
            frames = redact_video_keyframes(src, DST, slug)
            print(f"    extracted + redacted {len(frames)} frame(s)")
            for fm in frames:
                if fm.get("is_video"):
                    items.append({
                        "id": f"{slug}_video", "kind": "video",
                        "filename": fm["filename"],
                        "title": title + " (redacted MP4)",
                        "caption": caption, "category": category,
                        "redaction_status": "REDACTED (boxblur=20, 240p, "
                                              "no audio, 10fps)",
                        "source_note": "Original screen recording from "
                                          "Taylor's NGO casework "
                                          "(Feb-Jun 2021).",
                    })
                else:
                    items.append({
                        "id": f"{slug}_f{fm['seq']:02d}", "kind": "image",
                        "filename": fm["filename"],
                        "title": f"{title} -- t={fm['ts_seconds']}s",
                        "caption": caption, "category": category,
                        "redaction_status": "REDACTED (boxblur=20, "
                                              "downscale=480w, watermarked)",
                        "source_note": f"Keyframe @ "
                                          f"{fm['ts_seconds']}s of original "
                                          f"recording.",
                    })
        except Exception as e:
            print(f"  X{src_name} FAILED: {e}")

    # Add the research-document summary as a 'doc' entry (already
    # written by hand at static/evidence/research_document_summary.md).
    summary_path = DST / "research_document_summary.md"
    if summary_path.exists():
        items.append({
            "id": "research_document_facebook_case",
            "kind": "doc",
            "filename": "research_document_summary.md",
            "title": "Facebook trafficking-facilitation case "
                       "-- legal research binder framework",
            "caption": "Sanitised summary of a 37,553-char legal research "
                          "document outlining offences (insufficient content "
                          "regulation, facilitating trafficking + money "
                          "laundering, fraud/non-disclosure to shareholders) "
                          "and the HK PDPO Cap. 486 + Money Lenders "
                          "Cap. 163 framework for prosecution. Real victim "
                          "names + agency identifiers redacted.",
            "category": "other",
            "redaction_status": "REDACTED (hand-summarized; victim names + "
                                  "specific agency identifiers removed; "
                                  "framework-only)",
            "source_note": "Original research document by an NGO casework "
                              "team (~2024).",
        })

    manifest = {
        "_comment": "Auto-generated by scripts/redact_evidence.py. "
                       "Every asset is REDACTED. See "
                       ".claude/rules/10_safety_gate.md.",
        "items": items,
        "_schema": {
            "id": "unique slug",
            "kind": "image | video | doc",
            "filename": "filename inside static/evidence/",
            "title": "short headline",
            "caption": "1-2 sentence description",
            "category": "doxxing | passport_collateral | "
                          "recruitment_fraud | kafala | predatory_lending "
                          "| other",
            "redaction_status": "must start with REDACTED",
            "source_note": "where the original came from",
        },
    }
    (DST / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    total_kb = sum(p.stat().st_size
                    for p in DST.iterdir() if p.is_file()) // 1024
    print(f"\n  OK{len(items)} manifest entries  ·  total output: {total_kb} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
