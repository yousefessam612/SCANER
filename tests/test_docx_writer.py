"""اختبارات كاتب DOCX: خصائص RTL الحقيقية في XML + النص والترتيب."""
import zipfile

from app.core.languages import fix_word_to_logical
from app.writers.docx_writer import DocxWriter


def _xml_of(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def test_rtl_paragraph_and_run(tmp_path):
    w = DocxWriter(str(tmp_path / "out.docx"))
    w.add_block({"type": "paragraph", "text": "هذا نص عربي طويل للتجربة", "page": 0})
    w.add_block({"type": "heading", "text": "عنوان رئيسي", "page": 0})
    w.save()
    xml = _xml_of(tmp_path / "out.docx")
    assert "<w:bidi/>" in xml or "<w:bidi " in xml
    assert "<w:rtl/>" in xml or "<w:rtl " in xml


def test_ltr_paragraph_not_forced_rtl(tmp_path):
    w = DocxWriter(str(tmp_path / "out.docx"))
    w.add_block({"type": "paragraph", "text": "Plain English paragraph here", "page": 0})
    w.save()
    xml = _xml_of(tmp_path / "out.docx")
    # فقرة لاتينية خالصة: لا bidi
    assert "<w:bidi/>" not in xml


def test_text_preserved_in_order(tmp_path):
    blocks = [
        {"type": "paragraph", "text": "الأولى", "page": 0},
        {"type": "paragraph", "text": "الثانية", "page": 0},
        {"type": "list_item", "text": "عنصر قائمة", "page": 0},
    ]
    w = DocxWriter(str(tmp_path / "out.docx"))
    w.add_blocks(blocks)
    w.save()
    from docx import Document
    d = Document(str(tmp_path / "out.docx"))
    texts = [p.text for p in d.paragraphs if p.text.strip()]
    assert texts == ["الأولى", "الثانية", "• عنصر قائمة"]


def test_page_breaks_option(tmp_path):
    w = DocxWriter(str(tmp_path / "out.docx"), page_breaks_between_pages=True)
    w.add_block({"type": "paragraph", "text": "صفحة أولى", "page": 0})
    w.add_block({"type": "paragraph", "text": "صفحة ثانية", "page": 1})
    w.save()
    xml = _xml_of(tmp_path / "out.docx")
    assert "w:br" in xml


def test_fix_word_consistency():
    # عقد موحد: الكلمة المخزنة منطقية
    assert fix_word_to_logical("ةجمدم") == "مدمجة"
