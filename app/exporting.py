"""منسّق التصدير: يبني DOCX/TXT/HTML/PDF قابل للبحث + تقرير الجودة من نتائج الصفحات."""
from __future__ import annotations

from pathlib import Path

from .core.rawpdf import SearchablePDFBuilder
from .writers.docx_writer import DocxWriter
from .writers.html_writer import HtmlWriter
from .writers.report_writer import write_report
from .writers.txt_writer import TxtWriter

_FORMATS = ("docx", "txt", "html", "pdf")


def export_outputs(pdf_path, project_dir, pages: list[dict], *, formats=("docx",),
                   lang: str = "ara+eng", page_breaks: bool = False) -> dict:
    project_dir = Path(project_dir)
    out_dir = project_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(pdf_path).stem
    produced: dict[str, str] = {}

    # كتل موحدة عبر الصفحات بترتيبها
    blocks = []
    for pr in sorted(pages, key=lambda p: p["page"]):
        for b in pr.get("blocks", []):
            b2 = dict(b)
            b2["page"] = pr["page"]
            blocks.append(b2)

    formats = [f for f in formats if f in _FORMATS]
    if "docx" in formats:
        w = DocxWriter(str(out_dir / f"{stem}.docx"), page_breaks_between_pages=page_breaks)
        w.add_blocks(blocks)
        w.save()
        produced["docx"] = str(out_dir / f"{stem}.docx")
    if "txt" in formats:
        w = TxtWriter(str(out_dir / f"{stem}.txt"), page_markers=page_breaks)
        w.add_blocks(blocks)
        w.save()
        produced["txt"] = str(out_dir / f"{stem}.txt")
    if "html" in formats:
        w = HtmlWriter(str(out_dir / f"{stem}.html"), title=stem)
        w.add_blocks(blocks)
        w.save()
        produced["html"] = str(out_dir / f"{stem}.html")
    if "pdf" in formats:
        builder = SearchablePDFBuilder()
        src = None
        try:
            import pymupdf
            src = pymupdf.open(Path(pdf_path))
            for pr in sorted(pages, key=lambda p: p["page"]):
                i = pr["page"]
                words = pr.get("words", [])
                # حدود الأمان: كلمات خارج الصفحة تُهمل
                W, H = pr.get("width", 595), pr.get("height", 842)
                clean = [wd for wd in words
                         if 0 <= wd["bbox"][0] <= W + 2 and 0 <= wd["bbox"][1] <= H + 2]
                builder.add_page(W, H, clean, background_pdf=src, background_page=i,
                                 layer=pr.get("layer", "none"))
        finally:
            if src:
                src.close()
        out_pdf = out_dir / f"{stem}_searchable.pdf"
        builder.save(str(out_pdf))
        produced["pdf"] = str(out_pdf)

    # تقرير الجودة — دائمًا، في مجلد المشروع (لا يدخل مخرجات المستخدم)
    report_pages = [{
        "page": pr["page"], "status": pr.get("status"), "source": pr.get("source"),
        "conf": pr.get("conf"), "words": len(pr.get("words", [])),
        "reasons": pr.get("reasons", []), "attempts": pr.get("attempts", []),
    } for pr in pages]
    write_report(project_dir, Path(pdf_path).name, report_pages)
    produced["report"] = str(project_dir / "quality_report.txt")
    return {"outputs": produced}
