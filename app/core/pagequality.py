"""قياس جودة الصفحة وتقييم نتيجة OCR — كل الفحوص حتمية."""
from __future__ import annotations

import numpy as np
from PIL import Image


def measure_page(img: Image.Image) -> dict:
    g = np.asarray(img.convert("L"), dtype=np.uint8)
    dark = g < 160
    ink = float(dark.mean())
    bright = float(g.mean())
    contrast = float(g.std())
    noise = float(np.abs(g.astype(np.int16) - int(np.median(g))).mean())
    return {
        "width": img.width,
        "height": img.height,
        "brightness": round(bright, 1),
        "contrast": round(contrast, 1),
        "ink_ratio": round(ink, 5),
        "noise": round(noise, 1),
    }


def count_ink_bands(img: Image.Image, min_height_px: int = 8) -> list[tuple[int, int]]:
    """يعدّ أشرطة النص (أسطر) من موج الصفوف الداكنة — لكشف الأسطر التي أسقطها OCR."""
    g = np.asarray(img.convert("L"), dtype=np.uint8)
    dark = g < 160
    row_ratio = dark.mean(axis=1)
    rows = row_ratio > 0.003
    bands: list[tuple[int, int]] = []
    start = None
    gap = 0
    for i, v in enumerate(rows):
        if v:
            if start is None:
                start = i
            gap = 0
        else:
            if start is not None:
                gap += 1
                if gap > 6:  # فجوة بين الأسطر
                    if i - gap - start + 1 >= min_height_px:
                        bands.append((start, i - gap))
                    start = None
                    gap = 0
    if start is not None and len(rows) - start >= min_height_px:
        bands.append((start, len(rows) - 1))
    return bands


def assess_ocr(words: list[dict], mean_conf: float, page_metrics: dict,
               n_lines: int | None = None, n_bands: int | None = None) -> dict:
    """حكم على جودة OCR: ok / suspect / fail + أسباب + درجة للمقارنة بين المحاولات."""
    reasons: list[str] = []
    ink = page_metrics.get("ink_ratio", 0.0)

    if not words:
        if ink < 0.002:
            return {"status": "ok", "reasons": ["empty_page"], "score": 50.0}
        reasons.append("no_words_with_ink")
        return {"status": "suspect", "reasons": reasons, "score": 10.0}

    texts = [w["text"] for w in words]
    if mean_conf < 35:
        reasons.append("low_confidence")

    weak = sum(1 for w in words if w.get("conf", 0) < 55)
    if weak / len(words) > 0.5:
        reasons.append("many_weak_words")

    # سطر مكرر 5 مرات فأكثر = عطب مسح
    from collections import Counter
    c = Counter(" ".join(t.split()) for t in texts if len(t) > 8)
    if c and c.most_common(1)[0][1] >= 5:
        reasons.append("repeated_lines")

    # رموز بلا كلمات
    import re
    wordish = [t for t in texts if re.search(r"[\w\u0600-\u06FF]", t)]
    if len(wordish) < len(texts) * 0.5:
        reasons.append("symbols_not_words")

    if ink > 0.004 and len(words) < 3:
        reasons.append("few_words_for_ink")

    # كثافة الكلمات مقابل الحبر: حبر نصّي كثير مع كلمات قليلة = OCR أسقط أسطرًا
    # (مع استثناء النصوص العرضية الضخمة التي كلماتها قليلة بطبيعتها)
    W = page_metrics.get("width", 0)
    H = page_metrics.get("height", 0)
    if W and H and ink > 0.0025:
        ink_px = ink * W * H
        expected = ink_px / 1000.0
        hs = [w["bbox"][3] - w["bbox"][1] for w in words if len(w.get("bbox", [])) == 4]
        median_h = sorted(hs)[len(hs) // 2] if hs else 0
        display_text = median_h > 0.06 * H
        if not display_text and len(words) < 0.25 * expected:
            reasons.append("sparse_for_ink")

    # أسطر مفقودة: أشرطة حبر نصية أكثر بكثير من أسطر OCR = سقوط أسطر كاملة
    if n_bands is not None and n_lines is not None and n_bands >= 3 and n_lines < 0.75 * n_bands:
        reasons.append("missing_lines")

    status = "ok" if not reasons else ("suspect" if mean_conf >= 20 or len(words) > 5 else "fail")
    score = mean_conf + min(len(words), 200) * 0.1 - 25 * len(reasons)
    return {"status": status, "reasons": reasons, "score": round(score, 1)}
