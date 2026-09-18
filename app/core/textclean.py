"""تنظيف النص الحتمي وبناء الكتل (عناوين/فقرات/قوائم).

منطق العناوين بنيوي لا طولي فقط: العنوان يبدأ كتلة جديدة (فجوة قبله) ويكون قصيرًا
بلا نهاية جملة، مع إشارة بنية: ارتفاع سطر أكبر من السائد أو فجوة أكبر بعده.
"""
from __future__ import annotations

import re

from .languages import strip_bidi_controls

_WS_RE = re.compile(r"[ \t\u00a0\u2000-\u200a]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")


def clean_text(s: str) -> str:
    s = strip_bidi_controls(s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(_WS_RE.sub(" ", ln).strip() for ln in s.split("\n"))
    s = _MULTI_NL_RE.sub("\n\n", s)
    s = re.sub(r" +([،.؛:!؟])", r"\1", s)
    return s.strip()


def is_likely_heading(line: str, next_line: str = "") -> bool:
    """شروط العنوان النصية (تُستخدم مع الشروط البنيوية في build_blocks)."""
    ln = line.strip()
    if not ln or len(ln) > 80:
        return False
    if ln.endswith((".", "،", "؛", ":", "!", "؟")) and not ln.endswith("..."):
        return False
    if re.match(r"^[-–—•*●▪◦]\s+\S", ln):
        return False
    if re.match(r"^\d{1,3}[.)]\s+\S", ln):
        return False
    if next_line.strip() == "":
        return False  # سطر معزول بلا ما يليه: فقرة قصيرة أصلح من عنوان مخمَّن
    return len(ln) < 60


def is_list_item(line: str) -> bool:
    ln = line.strip()
    if re.match(r"^[-–—•*●▪◦]\s+\S", ln):
        return True
    if re.match(r"^\d{1,3}[.)]\s+\S", ln):
        return True
    if re.match(r"^[أ-ي]\)\s+\S", ln):
        return True
    return False


def strip_list_marker(line: str) -> str:
    return re.sub(r"^[-–—•*●▪◦]\s+|^\d{1,3}[.)]\s+|^[أ-ي]\)\s+", "", line.strip())


def _median(values: list[float], default: float) -> float:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return default
    return max(vals[len(vals) // 2], 0.001)


def build_blocks(lines: list[dict]) -> list[dict]:
    """كتل دلالية من سطور الصفحة: {type, text, page}.

    - القائمة: سطر يبدأ بعلامة قائمة.
    - العنوان: يبدأ كتلة جديدة (أول الصفحة أو فجوة قبله) + شروط نصية
      + إشارة بنية (ارتفاع أكبر من السائد أو فجوة أكبر بعده من إيقاع الأسطر).
    - الفقرة: تُدمج الأسطر المتلاصقة.
    """
    blocks: list[dict] = []
    para: list[str] = []
    para_page = 0
    prev_y1 = None
    prev_y0 = None

    median_h = _median([ln["y1"] - ln["y0"] for ln in lines if ln.get("y1") is not None], 14.0)
    spacings = [lines[i + 1]["y0"] - lines[i]["y0"] for i in range(len(lines) - 1)
                if lines[i].get("y0") is not None and lines[i + 1].get("y0") is not None
                and 0 < lines[i + 1]["y0"] - lines[i]["y0"] < 3 * median_h]
    median_space = _median(spacings, median_h * 1.3)

    def flush():
        nonlocal para
        if para:
            blocks.append({"type": "paragraph", "text": " ".join(para).strip(), "page": para_page})
            para = []

    for idx, ln in enumerate(lines):
        txt = ln["text"].strip()
        if not txt:
            continue
        page = ln.get("page", 0)
        y0, y1 = ln.get("y0"), ln.get("y1")
        next_ln = lines[idx + 1] if idx + 1 < len(lines) else None
        next_txt = next_ln["text"] if next_ln else ""
        h = (y1 - y0) if (y0 is not None and y1 is not None) else median_h
        gap_after = (next_ln["y0"] - y0) if (next_ln and next_ln.get("y0") is not None and y0 is not None) else None
        big_gap_above = prev_y1 is not None and y0 is not None and (y0 - prev_y1) > 1.7 * median_h
        page_changed = para and page != para_page

        if is_list_item(txt):
            flush()
            blocks.append({"type": "list_item", "text": strip_list_marker(txt), "page": page})
        elif para and not big_gap_above and not page_changed:
            para.append(txt)
        else:
            # بداية كتلة جديدة: هل هي عنوان؟
            structural = (h > median_h * 1.18) or (gap_after is not None and gap_after > median_space * 1.45)
            if structural and is_likely_heading(txt, next_txt):
                flush()
                blocks.append({"type": "heading", "text": txt, "page": page})
                para_page = page
                prev_y1, prev_y0 = y1, y0
                continue
            flush()
            para = [txt]
            para_page = page
        if y1 is not None:
            prev_y1 = y1
        if y0 is not None:
            prev_y0 = y0
    flush()
    return blocks
