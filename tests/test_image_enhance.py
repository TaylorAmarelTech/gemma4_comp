"""Tests for scripts/image_enhance.py -- deterministic pre-OCR image enhancement.

Offline: every input is synthesized with numpy/cv2 (no fixtures, no network). cv2 +
numpy ship in the recovery venv; the whole module is skipped if cv2 is absent.
"""
from __future__ import annotations

import base64
import importlib.util
import sys
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ie = _load("image_enhance", _ROOT / "scripts" / "image_enhance.py")


# --- synthetic builders ----------------------------------------------------

def _checkerboard(h: int, w: int, sq: int = 20) -> "np.ndarray":
    """Sharp, high-contrast, axis-aligned image (passes blur/contrast/skew gates)."""
    board = (((np.indices((h, w)).sum(0) // sq) % 2) * 255).astype(np.uint8)
    return cv2.cvtColor(board, cv2.COLOR_GRAY2BGR)


def _text_lines(h: int = 400, w: int = 400) -> "np.ndarray":
    img = np.full((h, w, 3), 255, np.uint8)
    for y in range(40, h - 40, 40):
        cv2.rectangle(img, (60, y), (w - 60, y + 12), (0, 0, 0), -1)
    return img


def _rotate(img, deg):
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    return cv2.warpAffine(img, m, (w, h), borderValue=(255, 255, 255))


# --- measurement -----------------------------------------------------------

def test_blur_score_higher_for_sharp_than_blurred():
    sharp = _checkerboard(200, 200)
    blurred = cv2.GaussianBlur(sharp, (0, 0), 4)
    assert ie.blur_score(sharp) > ie.blur_score(blurred) > 0


def test_quality_report_has_flags():
    rep = ie.quality_report(_checkerboard(1200, 1200))
    for k in ("blur", "skew_deg", "is_blurry", "is_skewed", "is_low_res", "is_low_contrast"):
        assert k in rep


# --- operations ------------------------------------------------------------

def test_sharpen_increases_sharpness():
    blurred = cv2.GaussianBlur(_checkerboard(200, 200), (0, 0), 3)
    assert ie.blur_score(ie.sharpen(blurred)) > ie.blur_score(blurred)


def test_upscale_grows_then_caps():
    img = _checkerboard(200, 300)
    big = ie.upscale(img, scale=2.0)
    assert big.shape[:2] == (400, 600)
    capped = ie.upscale(img, scale=100.0, max_dim=1000)         # 300*100 would be 30000
    assert max(capped.shape[:2]) <= 1000


def test_clahe_increases_low_contrast():
    flat = np.full((200, 200, 3), 120, np.uint8)
    flat[:, 100:] = 135                                          # std ~7.5 -> low contrast
    assert float(cv2.cvtColor(ie.clahe_contrast(flat), cv2.COLOR_BGR2GRAY).std()) > float(
        cv2.cvtColor(flat, cv2.COLOR_BGR2GRAY).std())


def test_deskew_reduces_skew_magnitude():
    skewed = _rotate(_text_lines(), 8)
    before = abs(ie.estimate_skew(skewed))
    after = abs(ie.estimate_skew(ie.deskew(skewed)))
    assert before > 3.0 and after < before                      # genuinely skewed, then corrected


def test_crop_returns_clamped_subregion():
    img = _checkerboard(100, 100)
    assert ie.crop(img, (10, 20, 30, 40)).shape[:2] == (40, 30)
    assert ie.crop(img, (90, 90, 50, 50)).shape[:2] == (10, 10)  # clamped to bounds


# --- immutability ----------------------------------------------------------

@pytest.mark.parametrize("op", ["sharpen", "denoise", "clahe_contrast", "deskew"])
def test_ops_do_not_mutate_input(op):
    img = _rotate(_text_lines(), 6)
    original = img.copy()
    getattr(ie, op)(img)
    assert np.array_equal(img, original)


# --- quality-gated orchestration -------------------------------------------

def test_clean_large_image_needs_no_ops():
    out, ops = ie.enhance_for_ocr(_checkerboard(1200, 1200))
    assert ops == [] and out.shape == (1200, 1200, 3)


def test_small_image_is_upscaled():
    out, ops = ie.enhance_for_ocr(_checkerboard(300, 400), target_min_dim=1000)
    assert any("upscale" in o for o in ops)
    assert min(out.shape[:2]) >= 1000


# --- base64 boundary -------------------------------------------------------

def test_enhance_b64_roundtrips_and_reports_ops():
    img = _checkerboard(300, 400)
    b64 = base64.b64encode(ie.encode(img)).decode("ascii")
    out_b64, ops = ie.enhance_b64(b64, target_min_dim=1000)
    assert any("upscale" in o for o in ops)
    assert ie.decode(out_b64) is not None                       # valid PNG back


def test_enhance_b64_clean_image_returns_unchanged():
    b64 = base64.b64encode(ie.encode(_checkerboard(1200, 1200))).decode("ascii")
    out_b64, ops = ie.enhance_b64(b64)
    assert ops == [] and out_b64 == b64                         # untouched, same bytes


def test_enhance_b64_bad_input_is_safe_noop():
    out_b64, ops = ie.enhance_b64("not-valid-base64-image!!")
    assert ops == ["decode-failed:no-op"] and out_b64 == "not-valid-base64-image!!"
