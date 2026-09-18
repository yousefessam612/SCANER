"""تجمع أدوات الاختبار: توليد PDF عربي حقيقي بخط Amiri + OCR جاهز."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.paths import missing_langs, tessdata_dir  # noqa: E402

FONT = ROOT / "tests" / "fixtures" / "Amiri-Regular.ttf"


def make_arabic_pdf(path: Path, pages: list[str], width: float = 595, height: float = 400) -> Path:
    """يبني PDF حقيقيًا بنص عربي مُشكَّل (فقرات RTL)."""
    import pymupdf

    doc = pymupdf.open()
    for content in pages:
        page = doc.new_page(width=width, height=height)
        html = f'<p dir="rtl" style="font-size:18px;">{content}</p>'
        page.insert_htmlbox(pymupdf.Rect(40, 40, width - 40, height - 40), html)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture(scope="session")
def need_ocr():
    """يضمن توفر tesserocr وبيانات ara/eng قبل اختبارات OCR."""
    pytest.importorskip("tesserocr")
    td = tessdata_dir()
    if not td:
        pytest.skip("tessdata غير متوفر")
    miss = missing_langs(["ara", "eng"])
    if miss:
        pytest.skip(f"بيانات لغة ناقصة: {miss}")
    return str(td)


SAMPLE_SENTENCE = "بسم الله الرحمن الرحيم هذا اختبار للغة العربية مع أرقام 1442"
