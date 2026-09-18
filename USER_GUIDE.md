# دليل الاستخدام / User Guide

اقرأ — محوّل PDF إلى DOCX/TXT/HTML/PDF قابل للبحث، بعربية احترافية، ويعمل دون اتصال بالإنترنت تمامًا.

## البدء السريع

```bash
# 1) جهّز البيئة (مرة واحدة)
pip install -r requirements.txt
# 2) بيانات OCR العربية: ara.traineddata وeng.traineddata داخل runtime/tessdata/
#    (التنزيل: github.com/tesseract-ocr/tessdata_best → ara.traineddata
#             github.com/tesseract-ocr/tessdata_fast → eng.traineddata)
# 3) فحص ذاتي سريع
python -m app selftest
# 4) حوّل أول ملف
python -m app convert كتاب.pdf -f docx,txt,pdf -o المخرجات
```

ستجد النواتج في `المخرجات/كتاب.iqra_project/output/`:
- `كتاب.docx` — وورد عربي RTL جاهز للتحرير وقارئ الشاشة
- `كتاب.txt` — نص UTF-8 مع BOM
- `كتاب_searchable.pdf` — نسخة قابلة للبحث بالعربية
- وفي جذر المشروع: `quality_report.txt` — الصفحات التي تحتاج مراجعة

## سطر الأوامر الكامل

```
python -m app convert ملف.pdf [خيارات]
  -l ara|eng|ara+eng      لغة التعرف (افتراضي ara+eng)
  -q fast|balanced|high   السرعة مقابل الدقة (DPI 200/300/400)
  -f docx,txt,html,pdf    صيغ المخرجات (افتراضي docx)
  -o مجلد                 مجلد المخرجات
  --page-breaks           فاصل صفحة بين صفحات PDF في الوورد
  --no-trust-text-layer   أجبر OCR حتى لو في الصفحة طبقة نص

python -m app resume "كتاب.iqra_project"    # استئناف
python -m app batch مجلد/                   # كل ملفات PDF في مجلد
python -m app selftest                      # فحص ذاتي شامل
```

## نصائح للعربية

- **الافتراضي ara+eng هو الأفضل** للوثائق المختلطة (نموذج best للعربية تلقائيًا).
- الملفات العربية «سيئة الصنع» (نصها يظهر سليمًا لكن نسخه يخرج `ةغللا`) يُصلحها اقرأ تلقائيًا — لا تحتاج أي إعداد.
- إن كانت الصفحات ممسوحة ضوئيًا رديئًا جرّب `-q high`.
- `--page-breaks` مفيد للكتب: فاصل صفحة في الوورد بين كل صفحتين.

## استكشاف سريع

| المشكلة | الحل |
|---|---|
| «بيانات OCR العربية غير موجودة» | ضع `ara.traineddata` في `runtime/tessdata/` |
| تحويل يتوقف في منتصف الكتاب | `python -m app resume "الكتاب.iqra_project"` — يكمل من نفس الصفحة |
| صفحات مشبوهة في التقرير | راجعها يدويًا أو أعد التحويل بـ `-q high` |
| الوورد يظهر إنجليزيًا يسارًا | هذا طبيعي للفقرات الإنجليزية؛ الفقرات العربية RTL تلقائيًا |
