#!/usr/bin/env python3
"""Deterministic image enhancement before OCR / Gemma-4 vision extraction.

Ported (technique only) from the OpenSearch-VL tool environment
(``shawn0728/OpenSearch-VL``, Apache-2.0): its multimodal agent recovers from
imperfect visual inputs with ``crop`` / ``perspective_correct`` /
``super_resolution`` / ``sharpen`` tools *before* reading them. We implement the
same enhance-before-extract idea with the OpenCV that camelot already pulls in --
no model download, no new heavy dependency, pure deterministic computer vision.

The pipeline is QUALITY-GATED: :func:`quality_report` measures blur (variance of
the Laplacian), resolution, contrast, and skew, and :func:`enhance_for_ocr`
applies only the ops a given image actually needs -- so a clean screenshot is left
essentially untouched while a blurry, skewed, low-res document photo is deskewed,
denoised, sharpened, contrast-stretched, and upscaled.

It slots in right before ``scripts.llm_scrape.vision_extract`` (which takes a
base64 PNG): ``b64, ops = enhance_b64(screenshot_b64)``.

Contracts:
- every op returns a NEW array and never mutates its input (immutability rule);
- ``cv2`` / ``numpy`` are imported lazily; if ``cv2`` is unavailable each op is a
  logged no-op so callers always get a usable image back (never an exception);
- nothing here is model-backed -- it is reproducible and runs on CPU.
"""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path
from typing import Any

# Quality thresholds (named, not magic). Tuned for screen/document captures.
_BLUR_MIN = 120.0          # variance-of-Laplacian below this => blurry
_SKEW_MIN_DEG = 1.5        # |skew| above this => worth deskewing
_LOWRES_MIN_DIM = 1000     # min(h, w) below this => upscale toward target
_LOWCONTRAST_STD = 45.0    # gray std below this => contrast-stretch
_UPSCALE_MAX_DIM = 4000    # never upscale beyond this (memory / API limits)


def _cv():
    """Return (cv2, numpy) or (None, None) if OpenCV is unavailable."""
    try:
        import cv2
        import numpy as np
        return cv2, np
    except Exception:  # noqa: BLE001 - absence degrades to no-op, never fatal
        return None, None


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def blur_score(img: Any) -> float:
    """Variance of the Laplacian -- higher is sharper (0.0 if cv2 missing)."""
    cv2, np = _cv()
    if cv2 is None:
        return 0.0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def estimate_skew(img: Any) -> float:
    """Estimate document skew in degrees in [-45, 45] (0.0 if cv2 missing)."""
    cv2, np = _cv()
    if cv2 is None:
        return 0.0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    # foreground = dark text on light page; invert so text is non-zero
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = cv2.findNonZero(thr)
    if coords is None or len(coords) < 20:
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle += 90
    elif angle > 45:
        angle -= 90
    return float(angle)


def quality_report(img: Any) -> dict:
    """Blur / skew / resolution / contrast plus boolean 'needs' flags."""
    cv2, np = _cv()
    if cv2 is None:
        return {"available": False}
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    h, w = img.shape[:2]
    blur = blur_score(img)
    skew = estimate_skew(img)
    contrast = float(gray.std())
    return {
        "available": True,
        "height": int(h), "width": int(w),
        "blur": round(blur, 1), "skew_deg": round(skew, 2),
        "contrast": round(contrast, 1),
        "is_blurry": blur < _BLUR_MIN,
        "is_skewed": abs(skew) > _SKEW_MIN_DEG,
        "is_low_res": min(h, w) < _LOWRES_MIN_DIM,
        "is_low_contrast": contrast < _LOWCONTRAST_STD,
    }


# ---------------------------------------------------------------------------
# Operations (each returns a new array)
# ---------------------------------------------------------------------------

def deskew(img: Any, *, max_angle: float = 15.0) -> Any:
    """Rotate the image to remove skew (no-op if skew is tiny or too large)."""
    cv2, np = _cv()
    if cv2 is None:
        return img
    angle = estimate_skew(img)
    if abs(angle) < _SKEW_MIN_DEG or abs(angle) > max_angle:
        return img
    h, w = img.shape[:2]
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, rot, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def sharpen(img: Any, *, amount: float = 1.0, radius: int = 3) -> Any:
    """Unsharp mask: img + amount*(img - blur(img))."""
    cv2, np = _cv()
    if cv2 is None:
        return img
    blurred = cv2.GaussianBlur(img, (0, 0), radius)
    return cv2.addWeighted(img, 1 + amount, blurred, -amount, 0)


def denoise(img: Any) -> Any:
    """Edge-preserving denoise (bilateral filter)."""
    cv2, np = _cv()
    if cv2 is None:
        return img
    return cv2.bilateralFilter(img, 5, 50, 50)


def clahe_contrast(img: Any) -> Any:
    """Contrast-limited adaptive histogram equalization on luminance."""
    cv2, np = _cv()
    if cv2 is None:
        return img
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    if img.ndim == 2:
        return clahe.apply(img)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def upscale(img: Any, *, scale: float = 2.0, max_dim: int = _UPSCALE_MAX_DIM) -> Any:
    """Lanczos upscale, capped so the long edge never exceeds ``max_dim``."""
    cv2, np = _cv()
    if cv2 is None or scale <= 1.0:
        return img
    h, w = img.shape[:2]
    scale = min(scale, max_dim / max(h, w)) if max(h, w) * scale > max_dim else scale
    if scale <= 1.0:
        return img
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LANCZOS4)


def crop(img: Any, box: tuple[int, int, int, int]) -> Any:
    """Crop ``(x, y, w, h)``, clamped to the image bounds."""
    cv2, np = _cv()
    if cv2 is None:
        return img
    x, y, w, h = box
    H, W = img.shape[:2]
    x, y = max(0, x), max(0, y)
    return img[y:min(H, y + h), x:min(W, x + w)].copy()


def perspective_correct(img: Any, *, min_area_frac: float = 0.25) -> Any:
    """Flatten a photographed page to top-down if a confident quad is found."""
    cv2, np = _cv()
    if cv2 is None:
        return img
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 60, 180)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    H, W = img.shape[:2]
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        if cv2.contourArea(c) < min_area_frac * H * W:
            break
        quad = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(quad) == 4:
            return _warp_quad(cv2, np, img, quad.reshape(4, 2).astype("float32"))
    return img


def _warp_quad(cv2, np, img: Any, pts: Any) -> Any:
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1)
    tl, br, tr, bl = pts[np.argmin(s)], pts[np.argmax(s)], pts[np.argmin(d)], pts[np.argmax(d)]
    wA, wB = np.linalg.norm(br - bl), np.linalg.norm(tr - tl)
    hA, hB = np.linalg.norm(tr - br), np.linalg.norm(tl - bl)
    w, h = int(max(wA, wB)), int(max(hA, hB))
    if w < 10 or h < 10:
        return img
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype="float32")
    m = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl], dtype="float32"), dst)
    return cv2.warpPerspective(img, m, (w, h))


# ---------------------------------------------------------------------------
# Orchestrated, quality-gated pipeline
# ---------------------------------------------------------------------------

def enhance_for_ocr(img: Any, *, target_min_dim: int = _LOWRES_MIN_DIM) -> tuple[Any, list[str]]:
    """Apply only the enhancements the image needs; return (image, ops_applied)."""
    cv2, np = _cv()
    if cv2 is None:
        return img, ["cv2-unavailable:no-op"]
    rep = quality_report(img)
    ops: list[str] = []
    out = img
    if rep["is_skewed"]:
        out = deskew(out)
        ops.append(f"deskew({rep['skew_deg']:+.1f}deg)")
    if rep["is_blurry"]:
        out = sharpen(denoise(out))
        ops.append(f"denoise+sharpen(blur={rep['blur']:.0f})")
    if rep["is_low_contrast"]:
        out = clahe_contrast(out)
        ops.append(f"clahe(contrast={rep['contrast']:.0f})")
    if rep["is_low_res"]:
        scale = max(1.0, target_min_dim / max(1, min(out.shape[:2])))
        if scale > 1.0:
            before = out.shape[:2]
            out = upscale(out, scale=scale)
            ops.append(f"upscale({before[1]}x{before[0]}->{out.shape[1]}x{out.shape[0]})")
    return out, ops


# ---------------------------------------------------------------------------
# bytes / base64 bridges (the vision_extract boundary)
# ---------------------------------------------------------------------------

def decode(data: bytes | str) -> Any:
    """PNG/JPEG bytes or a base64 string -> BGR array.

    Returns ``None`` if cv2 is missing or the input is not a decodable image
    (malformed base64, non-image bytes) -- callers treat ``None`` as a no-op.
    """
    cv2, np = _cv()
    if cv2 is None:
        return None
    try:
        if isinstance(data, str):
            data = base64.b64decode(data, validate=False)
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    except Exception:  # noqa: BLE001 - bad input degrades to no-op, never fatal
        return None


def encode(img: Any, *, fmt: str = ".png") -> bytes:
    """BGR array -> encoded image bytes (empty if cv2 missing)."""
    cv2, np = _cv()
    if cv2 is None:
        return b""
    ok, buf = cv2.imencode(fmt, img)
    return buf.tobytes() if ok else b""


def enhance_b64(image_b64: str, *, target_min_dim: int = _LOWRES_MIN_DIM) -> tuple[str, list[str]]:
    """Decode a base64 PNG, quality-gate enhance, re-encode base64.

    Returns ``(original_b64, ['decode-failed'])`` unchanged if anything goes wrong,
    so wiring it before ``vision_extract`` can never break the extraction path.
    """
    img = decode(image_b64)
    if img is None:
        return image_b64, ["decode-failed:no-op"]
    out, ops = enhance_for_ocr(img, target_min_dim=target_min_dim)
    if not ops:
        return image_b64, []
    enc = encode(out, fmt=".png")
    return (base64.b64encode(enc).decode("ascii"), ops) if enc else (image_b64, ["encode-failed:no-op"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="input image path")
    ap.add_argument("output", nargs="?", help="output path (omit with --report)")
    ap.add_argument("--report", action="store_true", help="print quality only, don't write")
    ap.add_argument("--target-min-dim", type=int, default=_LOWRES_MIN_DIM)
    args = ap.parse_args(argv)

    cv2, np = _cv()
    if cv2 is None:
        print("OpenCV unavailable (pip install opencv-python-headless)", file=sys.stderr)
        return 2
    img = cv2.imread(args.input)
    if img is None:
        ap.error(f"could not read image: {args.input}")
    print("before:", quality_report(img), file=sys.stderr)
    if args.report:
        return 0
    out, ops = enhance_for_ocr(img, target_min_dim=args.target_min_dim)
    print("ops:", ops or ["(none needed)"], file=sys.stderr)
    print("after: ", quality_report(out), file=sys.stderr)
    dst = args.output or str(Path(args.input).with_suffix(".enhanced.png"))
    cv2.imwrite(dst, out)
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
