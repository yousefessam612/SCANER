"""واجهة سطر الأوامر — عربية أولًا.

أمثلة:
  python -m app convert book.pdf -f docx,txt,pdf -o المخرجات
  python -m app resume "book.iqra_project"
  python -m app selftest
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import DEFAULTS, dpi_for, load
from .strings import t


def _add_common(p, out_default=""):
    p.add_argument("-l", "--lang", default=None, help="ara | eng | ara+eng (الافتراضي ara+eng)")
    p.add_argument("-q", "--quality", choices=["fast", "balanced", "high"], default=None,
                   help="السرعة مقابل الدقة (DPI 200/300/400)")
    p.add_argument("-f", "--formats", default=None, help="قائمة مفصولة بفواصل: docx,txt,html,pdf")
    p.add_argument("-o", "--out", default=out_default, help="مجلد المخرجات")
    p.add_argument("--trust-text-layer", dest="trust_text_layer", action="store_true", default=None)
    p.add_argument("--no-trust-text-layer", dest="trust_text_layer", action="store_false")
    p.add_argument("--page-breaks", action="store_true", help="فاصل صفحة بين صفحات PDF في DOCX")
    p.add_argument("--lang-ui", choices=["ar", "en"], default="ar")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="iqra", description="اقرأ — محوّل PDF عربي يعمل دون اتصال")
    sub = ap.add_subparsers(dest="cmd", required=True)

    cv = sub.add_parser("convert", help="تحويل ملف PDF")
    cv.add_argument("pdf")
    _add_common(cv)

    rs = sub.add_parser("resume", help="استئناف مشروع غير مكتمل")
    rs.add_argument("project")
    _add_common(rs)

    bt = sub.add_parser("batch", help="تحويل كل ملفات PDF في مجلد")
    bt.add_argument("folder")
    _add_common(bt)

    st = sub.add_parser("selftest", help="فحص ذاتي: OCR + الكُتّاب + البحث العربي")
    _add_common(st)

    return ap


def _check_tess(lang: str) -> bool:
    from .paths import missing_langs, tessdata_dir
    if not tessdata_dir():
        print(t("missing_tess"))
        return False
    miss = missing_langs([lang])
    if miss:
        print(t("missing_tess") + f" ({', '.join(miss)})")
        return False
    return True


def cmd_convert(args) -> int:
    from .core.engine import convert_pdf
    from .core.ocr import ocr_available
    cfg = load()
    lang = args.lang or cfg["lang"]
    quality = args.quality or cfg["quality"]
    formats = [f.strip().lower() for f in args.formats.split(",")] if args.formats else cfg["formats"]
    trust = cfg["trust_text_layer"] if args.trust_text_layer is None else args.trust_text_layer

    if not Path(args.pdf).is_file():
        print(t("missing_pdf", args.lang_ui))
        return 2
    if not _check_tess(lang):
        return 2

    def progress(i, n, pr):
        msg = t("page_of", args.lang_ui, i=i, n=n)
        status = pr.get("status", "?")
        src = pr.get("source", "?")
        print(f"{msg} — {status} ({src})")

    summary = convert_pdf(
        args.pdf, lang=lang, quality=quality, formats=formats, out_dir=args.out,
        on_progress=progress, trust_text_layer=trust,
        ocr_max_attempts=DEFAULTS["ocr_max_attempts"], page_breaks=args.page_breaks)
    if summary["status"] == "cancelled":
        print(t("cancelled", args.lang_ui))
        return 130
    print(t("done", args.lang_ui))
    for k, v in summary.get("outputs", {}).items():
        print(f"  {k}: {v}")
    return 0


def cmd_resume(args) -> int:
    from .core.engine import convert_pdf
    pdir = Path(args.project)
    if not pdir.is_dir():
        print(t("missing_pdf", args.lang_ui))
        return 2
    st_file = pdir / "state.json"
    import json
    st = json.loads(st_file.read_text(encoding="utf-8"))
    pdf = st["pdf"]
    cfg = load()
    lang = args.lang or cfg["lang"]
    if not _check_tess(lang):
        return 2
    print(t("resuming", args.lang_ui, i=st["next_page"] + 1))
    summary = convert_pdf(pdf, lang=lang, quality=args.quality or cfg["quality"],
                          formats=args.formats.split(",") if args.formats else cfg["formats"],
                          out_dir=args.out or None, project=pdir)
    if summary["status"] == "cancelled":
        print(t("cancelled", args.lang_ui))
        return 130
    print(t("done", args.lang_ui))
    for k, v in summary.get("outputs", {}).items():
        print(f"  {k}: {v}")
    return 0


def cmd_batch(args) -> int:
    folder = Path(args.folder)
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        print(t("missing_pdf", args.lang_ui))
        return 2
    rc = 0
    for pdf in pdfs:
        print(f"=== {pdf.name} ===")
        args.pdf = str(pdf)
        r = cmd_convert(args)
        if r != 0:
            rc = r
    return rc


def cmd_selftest(args) -> int:
    """فحص ذاتي حقيقي: يولّد صفحة عربية، يقرؤها OCR، يبني DOCX وPDF قابلًا للبحث، ويبحث فيهما."""
    ok = True
    why = []
    try:
        from .selftest import run_selftest
        ok, why = run_selftest()
    except Exception as e:
        ok, why = False, [f"exception: {e}"]
    if ok:
        print(t("selftest_ok", args.lang_ui))
        return 0
    print(t("selftest_fail", args.lang_ui, why="؛ ".join(why)))
    return 1


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return {"convert": cmd_convert, "resume": cmd_resume, "batch": cmd_batch, "selftest": cmd_selftest}[args.cmd](args)
