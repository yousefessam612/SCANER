"""تصنيف صفحات PDF: نص حقيقي موثوق أم صورة/طبقة تالفة تحتاج OCR."""
from __future__ import annotations

import pymupdf

from .languages import broken_layer_reasons, has_arabic_char


def char_storage_directions(doc: pymupdf.Document, page_no: int) -> list[dict]:
    """لكل span عربي: هل محارفه المستخرجة بترتيب القراءة (rtl) أم معكوسة (ltr)؟

    القياس هندسي قطعي: أول محرف في سلسلة الاستخراج، إن رُسم في **النصف الأيمن**
    من صندوق الـspan فالسلسلة تتبع القراءة العربية (rtl=منطقية)؛ وإن في **النصف
    الأيسر** فهي مخزّنة بترتيب بصري معكوس (ltr) وتحتاج عكسًا.
    """
    out = []
    raw = doc[page_no].get_text("rawdict")
    for b in raw.get("blocks", []):
        for l in b.get("lines", []):
            for sp in l.get("spans", []):
                chars = sp.get("chars", [])
                sb = sp.get("bbox")
                if not chars or not sb or len(chars) < 2:
                    continue
                arabic_first = None
                for c in chars:
                    ch = c.get("c", "")
                    if has_arabic_char(ch):
                        arabic_first = c
                        break
                if arabic_first is None:
                    continue
                mid_x = (sb[0] + sb[2]) / 2.0
                fx = arabic_first.get("origin", (0, 0))[0]
                # اتجاه التخزين: rtl = منطقي، ltr = بصري معكوس
                direction = "rtl" if fx >= mid_x else "ltr"
                out.append({"bbox": list(sb), "direction": direction,
                            "n_chars": len(chars)})
    return out


def word_direction(words_raw: tuple, span_dirs: list[dict]) -> str | None:
    """حكم كلمة باعتماد الـspan الحاوي لها، أو None إن لم يوجد حاكم هندسي."""
    x0, y0, x1, y1 = words_raw[0], words_raw[1], words_raw[2], words_raw[3]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    best = None
    for sp in span_dirs:
        b = sp["bbox"]
        if b[0] - 1 <= cx <= b[2] + 1 and b[1] - 1 <= cy <= b[3] + 1:
            if best is None or sp["n_chars"] > best["n_chars"]:
                best = sp
    return best["direction"] if best else None


def page_words(doc: pymupdf.Document, page_no: int) -> list[dict]:
    """كلمات الطبقة النصية بإحداثيات النقاط (72dpi)."""
    page = doc[page_no]
    words = []
    for x0, y0, x1, y1, txt, *_ in page.get_text("words"):
        if txt.strip():
            words.append({"text": txt, "bbox": [x0, y0, x1, y1]})
    return words


def page_check(doc: pymupdf.Document, page_no: int) -> tuple[str, str | None]:
    """يعيد (kind, reason): kind نص/صورة، reason سبب عدم الثقة بالطبقة إن وجد."""
    page = doc[page_no]
    txt = page.get_text("text")
    words = [w for w in txt.split() if w.strip()]
    if len(words) < 3:
        return ("image", "no_text_layer" if not words else "too_few_words")
    # الحكم على الطبقة **بعد** محاولة إصلاحها (أشكال العرض + الانعكاس البصري شائعان في الملفات العربية)
    from .languages import fix_visual_arabic
    from .textclean import clean_text
    repaired = fix_visual_arabic(clean_text(txt))
    reasons = broken_layer_reasons(repaired)
    if reasons:
        return ("image", "broken_layer:" + "+".join(reasons))
    return ("text", None)


def render_page(doc: pymupdf.Document, page_no: int, dpi: int):
    pix = doc[page_no].get_pixmap(dpi=dpi)
    from .preprocess import decode_image
    return decode_image(pix.tobytes("png"))


def page_size_pts(doc: pymupdf.Document, page_no: int) -> tuple[float, float]:
    r = doc[page_no].rect
    return (r.width, r.height)
