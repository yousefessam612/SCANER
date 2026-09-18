"""معالجة الصور قبل OCR: رمادي/تباين/ضباب/عتبة — كلها حتمية وسريعة."""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def to_gray(img: Image.Image) -> Image.Image:
    return img.convert("L") if img.mode != "L" else img


def autocontrast(img: Image.Image) -> Image.Image:
    return ImageOps.autocontrast(to_gray(img), cutoff=1)


def blur(img: Image.Image, radius: float = 1.5) -> Image.Image:
    """ضباب خفيف: يُغلق فجوات الحروف المضادة للتعرّف (أنقذ صفحات كاملة اختبارًا)."""
    return to_gray(img).filter(ImageFilter.GaussianBlur(radius))


def binarize(img: Image.Image, threshold: int | None = None) -> Image.Image:
    g = to_gray(img)
    if threshold is None:
        threshold = otsu_threshold(g)
    return g.point(lambda p: 0 if p < threshold else 255)


def otsu_threshold(img: Image.Image) -> int:
    a = np.asarray(to_gray(img), dtype=np.uint8)
    hist, _ = np.histogram(a, bins=256, range=(0, 256))
    total = a.size
    sum_all = np.dot(np.arange(256), hist)
    sum_b = 0.0
    w_b = 0.0
    best_t, best_var = 127, -1.0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > best_var:
            best_var, best_t = var, t
    return int(best_t)


def decode_image(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


def encode_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
