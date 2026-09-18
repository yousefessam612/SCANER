"""الاختبار الذاتي: خط أنابيب حقيقي مصغّر (OCR عربي → DOCX → PDF قابل للبحث ← بحث عربي)."""
from __future__ import annotations

import tempfile
from pathlib import Path


def _make_arabic_pdf(path: Path) -> None:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=300)
    html = ('<p dir="rtl" style="font-size:20px;">'
            "بسم الله الرحمن الرحيم، هذا اختبار ذاتي لمحول اقرأ باللغة العربية مع رقم 1442."
            "</p>")
    page.insert_htmlbox(pymupdf.Rect(40, 40, 555, 200), html)
    doc.save(str(path))
    doc.close()


def run_selftest() -> tuple[bool, list[str]]:
    """يعيد (نجاح, أسباب الفشل). يفشل بصوت عالٍ إذا انكسر أي جزء من خط الأنابيب."""
    from .core.engine import convert_pdf
    from .core.languages import fix_visual_arabic
    from .paths import missing_langs, tessdata_dir

    why: list[str] = []
    if not tessdata_dir():
        return False, ["tessdata غير موجود"]
    if missing_langs(["ara", "eng"]):
        return False, ["بيانات ara/eng غير مكتملة"]
    try:
        import tesserocr  # noqa: F401
    except Exception:
        return False, ["tesserocr غير مثبت"]

    # 1) إصلاح الانعكاس
    fixed = fix_visual_arabic("ةغللا")
    if fixed != "اللغة":
        why.append(f"fix_visual_arabic: '{fixed}'")

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        pdf = tdp / "selftest.pdf"
        _make_arabic_pdf(pdf)
        out = convert_pdf(str(pdf), lang="ara+eng", quality="balanced",
                          formats=["docx", "txt", "html", "pdf"], project=tdp / "proj")
        if out.get("status") != "done":
            why.append(f"convert: {out}")
            return False, why
        odir = tdp / "proj" / "output"
        docx_p = odir / "selftest.docx"
        spdf_p = odir / "selftest_searchable.pdf"
        for f in (docx_p, spdf_p, odir / "selftest.txt", odir / "selftest.html"):
            if not f.is_file():
                why.append(f"missing output: {f.name}")

        # 2) DOCX يحوي كلمة عربية صحيحة
        if docx_p.is_file():
            from docx import Document
            d = Document(str(docx_p))
            text = "\n".join(p.text for p in d.paragraphs)
            for needle in ("الرحمن", "الرحيم", "العربية"):
                if needle not in text:
                    why.append(f"docx missing '{needle}'")

        # 3) PDF قابل للبحث: استخراج منطقي + بحث يعمل
        if spdf_p.is_file():
            import pymupdf
            sd = pymupdf.open(str(spdf_p))
            txt = sd[0].get_text()
            if "الرحيم" not in txt:
                why.append("searchable pdf extraction broken")
            if not sd[0].search_for("الرحيم"):
                why.append("search_for failed")

    return (not why), why
