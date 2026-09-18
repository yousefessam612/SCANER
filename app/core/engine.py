"""المنتج/خط الأنابيب: معالجة صفحة-بصفحة بذاكرة محدودة، إلغاء/استئناف، عزل أعطال.

- صفحة PDF الوحيدة الحية في الذاكرة في أي لحظة (كتاب 1000 صفحة = نفس الذاكرة).
- الحالة تُحفظ ذرّيًا (tmp + os.replace) بعد كل صفحة → كهرباء مقطوعة = خسارة صفحة واحدة.
- فشل صفحة لا يوقف الكتاب: يُسجّل في تقرير الجودة ويُتابع.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pymupdf

from . import pdfutil
from .jobstate import JobState, project_dir_for
from .ocr import OCREngine, ocr_available, run_ladder
from .pagequality import measure_page
from .pdfutil import page_check, page_size_pts, render_page
from .textclean import build_blocks, clean_text
from .languages import (broken_layer_reasons, fix_visual_arabic, fix_word_to_logical,
                        has_presentation_forms, looks_reversed_arabic, normalize_word,
                        order_logical_by_position)
import unicodedata

_QUALITY_DPI = {"fast": 200, "balanced": 300, "high": 400}


def _settings_fp(lang: str, quality: str, trust: bool) -> str:
    return f"{lang}|{quality}|{int(trust)}"


def process_page(doc: pymupdf.Document, i: int, engine: OCREngine | None, quality: str,
                 trust_text_layer: bool, ocr_max_attempts: int) -> dict:
    """معالجة صفحة واحدة مستقلة → صف نتيجة موحد (كلمات بإحداثيات نقاط + كتل + حكم)."""
    w_pt, h_pt = page_size_pts(doc, i)
    kind, reason = page_check(doc, i)
    page_result = {
        "page": i, "width": w_pt, "height": h_pt,
        "source": "text", "status": "ok", "reasons": [], "attempts": [], "conf": None,
        "layer": "trusted",  # trusted: طبقة سليمة | none: بلا طبقة | broken: طبقة فاسدة
    }
    words: list[dict] = []
    lines: list[dict] = []

    if kind == "text" and trust_text_layer:
        raw = doc[i].get_text("text")
        fixed = fix_visual_arabic(clean_text(raw))
        # إعادة فحص بعد الإصلاح: إن بقيت مسببات عطب نعالج بالصورة
        residual = broken_layer_reasons(fixed)
        if residual:
            kind, reason = "image", "broken_layer_residual:" + "+".join(residual)
            page_result["layer"] = "broken"
            page_result["reasons"].append("fixed_then_ocr:" + "+".join(residual))
        else:
            # المستخرج (MuPDF) يُعيد المحارف بترتيب القراءة؛ نطبّع كل كلمة (NFKC
            # لفكّ أشكال العرض) ونؤجل حكم ترتيب الحروف/الكلمات إلى مستوى السطر.
            words = pdfutil.page_words(doc, i)
            for wd in words:
                txt = wd["text"].replace("\n", " ").strip()
                wd["text"] = normalize_word(txt) or txt
            lines = _lines_from_words(words)
            page_result["conf"] = 100.0
    else:
        page_result["layer"] = "none" if reason in ("no_text_layer", "too_few_words") else "broken"
        if reason:
            page_result["reasons"].append(reason)

    if kind != "text" or not words:
        if engine is None:
            page_result.update(status="fail", source="ocr",
                               reasons=(page_result["reasons"] or ["ocr_unavailable"]))
            page_result["blocks"] = []
            page_result["words"] = []
            return page_result
        dpi = _QUALITY_DPI.get(quality, 300)
        img = render_page(doc, i, dpi)
        metrics = measure_page(img)
        metrics["dpi"] = dpi
        metrics["w_pt"], metrics["h_pt"] = w_pt, h_pt

        def render(d: int):
            return render_page(doc, i, d)

        ladder = run_ladder(engine, render, img, metrics, max_attempts=ocr_max_attempts)
        res, assessment, attempts = ladder["result"], ladder["assessment"], ladder["attempts"]
        scale = 72.0 / dpi
        # كلمات OCR بصريّة → نُخزّنها منطقية (عقد موحد لكل المستهلكين وطبقة PDF)
        words = [{"text": fix_word_to_logical(w["text"]),
                  "bbox": [round(c * scale, 2) for c in w["bbox"]], "conf": w["conf"]}
                 for w in res["words"]]
        lines = [{"bbox": [round(c * scale, 2) for c in ln["bbox"]],
                  "text": ln["text_logical"], "words": ln["words"]}
                 for ln in res["lines"]]
        page_result.update(
            source="ocr",
            status=assessment["status"],
            reasons=page_result["reasons"] + assessment.get("reasons", []),
            attempts=attempts,
            conf=res["mean_conf"],
        )

    # نص السطور المنطقي → كتل دلالية
    text_lines = []
    for ln in lines:
        txt = ln.get("text") or ln.get("text_logical") or ""
        txt = clean_text(txt)
        if txt:
            text_lines.append({"text": txt, "page": i, "y0": ln["bbox"][1], "y1": ln["bbox"][3]})
    page_result["blocks"] = build_blocks(text_lines)
    page_result["words"] = words
    page_result["n_lines"] = len(text_lines)
    return page_result


def _lines_from_words(words: list[dict], raw_words: list | None = None) -> list[dict]:
    """تجميع كلمات الطبقة النصية في أسطر هندسيًا مع حكم الانعكاس على مستوى السطر.

    لكل سطر: نرشّح القراءة الطبيعية (أقصى اليمين أولًا بعد التطبيع)؛ فإن بقي
    السطر يبدو معكوسًا إحصائيًا طبقنا إعادة البناء البصرية الكاملة (عكس الكلمات
    + عكس حروف كل كلمة) كما في طبقات Tesseract/Adobe المعكوسة.
    """
    if not words:
        return []
    if raw_words is None:
        raw_words = []
    ws = sorted(words, key=lambda w: (w["bbox"][1], w["bbox"][0]))
    lines: list[list[dict]] = []
    for w in ws:
        yc = (w["bbox"][1] + w["bbox"][3]) / 2
        for ln in lines:
            lyc = (ln[0]["bbox"][1] + ln[0]["bbox"][3]) / 2
            if abs(yc - lyc) <= 3.0:
                ln.append(w)
                break
        else:
            lines.append([w])
    out = []
    for ln in lines:
        ln.sort(key=lambda w: w["bbox"][0])  # بصري يسار→يمين
        texts_asc = [w["text"] for w in ln]
        norm_desc = list(reversed(texts_asc))  # القراءة الطبيعية: أقصى اليمين أولًا
        from .languages import looks_reversed_arabic, reorder_visual_to_logical
        if looks_reversed_arabic(" ".join(norm_desc)):
            logical_txt = " ".join(reorder_visual_to_logical(texts_asc))
        else:
            logical_txt = " ".join(norm_desc)
        y0 = min(w["bbox"][1] for w in ln)
        y1 = max(w["bbox"][3] for w in ln)
        x0 = min(w["bbox"][0] for w in ln)
        x1 = max(w["bbox"][2] for w in ln)
        out.append({"bbox": [x0, y0, x1, y1], "words": ln,
                    "text": logical_txt})
    out.sort(key=lambda l: l["bbox"][1])
    return out


def convert_pdf(pdf_path, *, lang: str = "ara+eng", quality: str = "balanced",
                formats: list[str] | None = None,
                out_dir=None, project: Path | None = None,
                on_progress=None, should_cancel=None, pause_event=None,
                trust_text_layer: bool = True, ocr_max_attempts: int = 4,
                page_breaks: bool = False) -> dict:
    """تحويل PDF كامل: معالجة الصفحات (مع استئناف) ثم التصدير. يعيد ملخصًا."""
    from ..exporting import export_outputs

    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(str(pdf_path))
    pdir = Path(project) if project else project_dir_for(pdf_path, out_dir)
    pdir.mkdir(parents=True, exist_ok=True)
    state = JobState(pdir)

    doc = pymupdf.open(pdf_path)
    total = doc.page_count
    st = state.init(str(pdf_path), total, _settings_fp(lang, quality, trust_text_layer))

    need_ocr = st["next_page"] < total  # قد لا نحتاج OCR إن كانت كل النصوص موثوقة
    engine = None
    if need_ocr and ocr_available():
        from ..paths import tessdata_dir
        td = tessdata_dir()
        if td:
            try:
                engine = OCREngine(str(td), lang=lang)
            except Exception as e:
                engine = None
                (pdir / "engine_error.txt").write_text(str(e), encoding="utf-8")

    cancelled_at = None
    for i in range(st["next_page"], total):
        # إيقاف مؤقت: ننتظر حتى يُستأنف أو يُلغى (فحص كل 0.2 ثانية)
        while pause_event is not None and pause_event.is_set():
            if should_cancel and should_cancel():
                break
            time.sleep(0.2)
        if should_cancel and should_cancel():
            cancelled_at = i
            break
        t0 = time.time()
        try:
            pr = process_page(doc, i, engine, quality, trust_text_layer, ocr_max_attempts)
        except Exception as e:  # عزل الأعطال: صفحة تالفة لا تُسقط الكتاب
            pr = {"page": i, "status": "fail", "source": "error", "reasons": [f"exception:{e}"],
                  "attempts": [], "conf": None, "blocks": [], "words": [],
                  "width": 595, "height": 842, "layer": "none"}
        pr["seconds"] = round(time.time() - t0, 2)
        state.save_page(i, pr, st)
        if on_progress:
            on_progress(i + 1, total, pr)
    doc.close()
    if engine:
        engine.close()

    if cancelled_at is not None:
        return {"status": "cancelled", "next_page": st["next_page"], "project": str(pdir)}

    pages = []
    for i in range(total):
        pr = state.load_page(i)
        if pr:
            pages.append(pr)
    summary = export_outputs(pdf_path, pdir, pages, formats=formats or ["docx"],
                             lang=lang, page_breaks=page_breaks)
    return {"status": "done", "pages": len(pages), "project": str(pdir), **summary}
