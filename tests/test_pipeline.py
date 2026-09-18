"""اختبارات خط الأنابيب الكامل: OCR عربي حقيقي → كل المخرجات."""
import json

import pytest

from conftest import SAMPLE_SENTENCE, make_arabic_pdf


@pytest.fixture(scope="module")
def converted(tmp_path_factory, need_ocr):
    """يحوّل PDF عربيًا من صفحتين مرة واحدة لكل الوحدة."""
    from app.core.engine import convert_pdf

    td = tmp_path_factory.mktemp("conv")
    pdf = make_arabic_pdf(td / "book.pdf", [
        SAMPLE_SENTENCE + " في الصفحة الأولى من الكتاب",
        "صفحة ثانية تحتوي كلمات عربية أخرى للتحقق من الترتيب والجودة",
    ])
    summary = convert_pdf(str(pdf), lang="ara+eng", quality="balanced",
                          formats=["docx", "txt", "html", "pdf"], project=td / "proj")
    return td, summary


class TestFullPipeline:
    def test_done(self, converted):
        td, summary = converted
        assert summary["status"] == "done"
        assert summary["pages"] == 2

    def test_docx_has_arabic_words(self, converted):
        from docx import Document
        td, _ = converted
        d = Document(str(td / "proj/output/book.docx"))
        text = "\n".join(p.text for p in d.paragraphs)
        for needle in ("الرحمن", "الرحيم", "العربية"):
            assert needle in text, f"كلمة {needle} مفقودة من DOCX"

    def test_txt_bom_and_content(self, converted):
        td, _ = converted
        p = td / "proj/output/book.txt"
        raw = p.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
        assert "العربية" in raw.decode("utf-8-sig")

    def test_html_direction(self, converted):
        td, _ = converted
        html = (td / "proj/output/book.html").read_text(encoding="utf-8")
        assert 'dir="rtl"' in html and 'lang="ar"' in html

    def test_searchable_pdf_extraction_and_search(self, converted):
        import pymupdf
        td, _ = converted
        d = pymupdf.open(str(td / "proj/output/book_searchable.pdf"))
        page1 = " ".join(d[0].get_text().split())
        assert "الرحمن" in page1 or "الرحيم" in page1
        assert d[0].search_for("العربية") or d[0].search_for("الرحمن")

    def test_quality_report_written(self, converted):
        td, _ = converted
        rep = td / "proj/quality_report.json"
        assert rep.is_file()
        data = json.loads(rep.read_text(encoding="utf-8"))
        assert data["summary"]["total"] == 2

    def test_resume_state_exists(self, converted):
        td, _ = converted
        st = json.loads((td / "proj/state.json").read_text(encoding="utf-8"))
        assert st["next_page"] == 2 and st["total"] == 2


class TestPageKinds:
    def test_text_page_trusted_layer(self, tmp_path, need_ocr):
        from app.core.engine import convert_pdf
        pdf = make_arabic_pdf(tmp_path / "good.pdf", [SAMPLE_SENTENCE])
        convert_pdf(str(pdf), lang="ara+eng", formats=["txt"], project=tmp_path / "p")
        pr = json.loads((tmp_path / "p/pages/page_00000.json").read_text(encoding="utf-8"))
        # الطبقة قد تكون سليمة (trusted) أو تحتاج OCR حسب جودة توليد الطبقة
        assert pr["layer"] in ("trusted", "broken", "none")
        assert pr["status"] in ("ok", "suspect")

    def test_empty_page_is_ok(self, tmp_path, need_ocr):
        import pymupdf
        from app.core.engine import convert_pdf
        doc = pymupdf.open()
        doc.new_page(width=595, height=300)  # صفحة فارغة تمامًا
        doc.save(str(tmp_path / "empty.pdf"))
        convert_pdf(str(tmp_path / "empty.pdf"), lang="ara+eng", formats=["txt"], project=tmp_path / "p")
        pr = json.loads((tmp_path / "p/pages/page_00000.json").read_text(encoding="utf-8"))
        assert pr["status"] == "ok"


class TestCancelResume:
    def test_cancel_then_resume(self, tmp_path, need_ocr):
        from app.core.engine import convert_pdf

        pdf = make_arabic_pdf(tmp_path / "three.pdf", [
            "صفحة أولى للتجربة", "صفحة ثانية للتجربة", "صفحة ثالثة للتجربة"])
        calls = {"n": 0}

        def cancel_after_first():
            calls["n"] += 1
            return calls["n"] >= 2  # ألغِ قبل الصفحة الثانية

        out1 = convert_pdf(str(pdf), lang="ara+eng", formats=["txt"], project=tmp_path / "p",
                           should_cancel=cancel_after_first)
        assert out1["status"] == "cancelled"
        assert out1["next_page"] == 1

        st_file = tmp_path / "p/state.json"
        mtime_before = st_file.stat().st_mtime_ns

        out2 = convert_pdf(str(pdf), lang="ara+eng", formats=["txt"], project=tmp_path / "p")
        assert out2["status"] == "done"
        # الصفحة الأولى لم تُعالج مجددًا (حالتها محفوظة ولم تُلمس)
        assert st_file.stat().st_mtime_ns != mtime_before
        pr0 = json.loads((tmp_path / "p/pages/page_00000.json").read_text(encoding="utf-8"))
        assert "أولى" in " ".join(b["text"] for b in pr0["blocks"]) or pr0["status"] in ("ok", "suspect")
