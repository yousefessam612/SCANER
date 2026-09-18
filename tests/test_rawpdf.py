"""اختبارات PDF القابل للبحث: طبقة نص عربية مخفية مبنية يدويًا — استخراج منطقي وبحث يعمل."""
import pymupdf

from app.core.rawpdf import SearchablePDFBuilder

WORDS = [
    {"text": "بسم", "bbox": [526.08, 70.56, 552.96, 84.0]},
    {"text": "الله", "bbox": [497.28, 64.56, 517.68, 78.0]},
    {"text": "الرحمن", "bbox": [441.60, 64.56, 488.88, 83.28]},
    {"text": "الرحيم", "bbox": [383.28, 64.56, 433.20, 84.0]},
    {"text": "رقم", "bbox": [400.0, 95.0, 425.0, 111.0]},
    {"text": "1442", "bbox": [360.0, 95.0, 392.0, 111.0]},
]


def _build(tmp_path, layer="none"):
    b = SearchablePDFBuilder()
    src = pymupdf.open()
    src.new_page(width=595, height=300)
    b.add_page(595, 300, WORDS, background_pdf=src, background_page=0, layer=layer)
    out = tmp_path / "searchable.pdf"
    b.save(str(out))
    return out


def test_logical_extraction(tmp_path):
    out = _build(tmp_path)
    d = pymupdf.open(str(out))
    txt = " ".join(d[0].get_text().split())
    assert "بسم الله الرحمن الرحيم" in txt
    assert "ةغللا" not in txt  # لا انعكاس
    assert "1442" in txt       # الأرقام سليمة


def test_search_works(tmp_path):
    out = _build(tmp_path)
    d = pymupdf.open(str(out))
    hits = d[0].search_for("الرحمن")
    assert hits, "البحث العربي يجب أن يعمل"
    # المستطيل داخل حدود الصفحة وبمنطقة النص العلوية
    r = hits[0]
    assert 0 <= r.x0 <= 595 and 0 <= r.y0 <= 300


def test_trusted_layer_copies_without_overlay(tmp_path):
    out = _build(tmp_path, layer="trusted")
    d = pymupdf.open(str(out))
    assert "بسم" not in d[0].get_text()  # لا طبقة مضافة فوق الطبقة السليمة


def test_number_search(tmp_path):
    out = _build(tmp_path)
    d = pymupdf.open(str(out))
    assert d[0].search_for("1442")


def test_empty_words_page_ok(tmp_path):
    b = SearchablePDFBuilder()
    src = pymupdf.open()
    src.new_page(width=595, height=300)
    b.add_page(595, 300, [], background_pdf=src, background_page=0, layer="none")
    out = tmp_path / "empty.pdf"
    b.save(str(out))
    assert pymupdf.open(str(out)).page_count == 1
