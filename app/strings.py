"""جدول النصوص ثنائي اللغة (عربي أولًا)."""
from __future__ import annotations

STRINGS = {
    "ar": {
        "app": "اقرأ — محوّل المستندات",
        "converting": "جارٍ التحويل",
        "page_of": "صفحة {i} من {n}",
        "done": "اكتمل التحويل",
        "out_files": "الملفات الناتجة",
        "cancelled": "أُلغي التحويل — استأنف لاحقًا من نفس النقطة",
        "resume_ask": "يوجد مشروع سابق غير مكتمل. استئناف؟",
        "resuming": "استئناف من الصفحة {i}",
        "failed_page": "تعذرت معالجة الصفحة {i} وسُجّلت في التقرير",
        "missing_tess": "بيانات OCR العربية غير موجودة. ضع ara.traineddata في مجلد runtime/tessdata",
        "missing_pdf": "الملف غير موجود أو ليس PDF",
        "selftest_ok": "الاختبار الذاتي: سليم ✓",
        "selftest_fail": "الاختبار الذاتي: فشل ✗ — {why}",
        "quality_report": "تقرير الجودة",
        "suspects": "صفحات تحتاج مراجعة",
        "no_text": "لا يوجد نص في هذا الملف (صور فقط) — سيُستخرج بالتعرف الضوئي",
    },
    "en": {
        "app": "Iqra — Document Converter",
        "converting": "Converting",
        "page_of": "Page {i} of {n}",
        "done": "Conversion complete",
        "out_files": "Output files",
        "cancelled": "Conversion cancelled — resume later from the same point",
        "resume_ask": "An unfinished project exists. Resume?",
        "resuming": "Resuming from page {i}",
        "failed_page": "Page {i} failed and was logged in the report",
        "missing_tess": "Arabic OCR data missing. Put ara.traineddata in runtime/tessdata",
        "missing_pdf": "File missing or not a PDF",
        "selftest_ok": "Self-test: OK",
        "selftest_fail": "Self-test: FAILED — {why}",
        "quality_report": "Quality report",
        "suspects": "Pages needing review",
        "no_text": "No text layer (image-only) — OCR will be used",
    },
}


def t(key: str, lang: str = "ar", **kw) -> str:
    s = STRINGS.get(lang, STRINGS["ar"])
    txt = s.get(key) or STRINGS["en"].get(key) or key
    try:
        return txt.format(**kw)
    except Exception:
        return txt
