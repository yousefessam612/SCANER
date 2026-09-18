# تراخيص المكونات / Licenses

اقرأ مجاني ومفتوح المصدر ويوزَّع بموجب **AGPL-3.0** (النص الكامل في ملف LICENSE).
Iqra is free and open-source software under **AGPL-3.0**.

كل الاعتماديات مجانية ومفتوحة ومناسبة لإعادة التوزيع. لا يوجد مكوّن تجاري مدفوع، ولا خدمة سحابية، ولا مفتاح API.

## التطبيق نفسه / Application

| المكوّن | الترخيص | الاستخدام |
|---|---|---|
| Iqra (app/) | AGPL-3.0 | كل كود التطبيق |

## مكتبات Python الموزَّعة داخل المثبت

| المكوّن | الترخيص | ملاحظات التوزيع |
|---|---|---|
| Python 3.14 (مدمج في الملف التنفيذي) | PSF License | مدمج عبر PyInstaller — لا حاجة لتثبيته |
| PySide6 6.11 | LGPL-3.0 | ربط ديناميكي؛ LGPL متوافق مع التوزيع |
| PyMuPDF 1.28 | AGPL-3.0 | نفس رخصة تطبيقنا — متوافق |
| MuPDF (داخل PyMuPDF) | AGPL-3.0 | كذلك |
| Pillow 11 | MIT-CMU | مفتوح |
| NumPy 2.x | BSD-3-Clause | مفتوح |
| python-docx 1.1 | MIT | مفتوح |
| psutil 7 | BSD-3-Clause | مفتوح |
| tesserocr 5.x | MIT | ربط Python بمكتبة Tesseract 5.5.1 المدمجة |

## مكونات OCR الموزَّعة (مُضمَّنة في المثبت)

| المكوّن | الترخيص | ملاحظات |
|---|---|---|
| Tesseract 5.4 (tesseract.exe + DLLs) | Apache-2.0 | بناء UB-Mannheim (tesseract-ocr.github.io) |
| Leptonica 1.84 (داخل البناء) | BSD-2-Clause | مدمج في بناء Tesseract |
| tessdata_best: ara, eng, osd | Apache-2.0 | من github.com/tesseract-ocr/tessdata_best |
| tessdata_fast: ara, eng, osd | Apache-2.0 | من github.com/tesseract-ocr/tessdata_fast |

ملاحظة: بيانات اللغة العربية `ara.traineddata` مبنية من عمل مجتمعي وتوزَّع بموجب Apache-2.0 — قانونية لإعادة التوزيع داخل المثبت.

## أدوات البناء (لا توزَّع للمستخدم النهائي)

| الأداة | الترخيص |
|---|---|
| PyInstaller 6.x | GPL-2.0 مع استثناء (يُسمح بترخيص الناتج مستقلًا) |
| Inno Setup 6.7 | Inno Setup License (استخدام مجاني) |
| pytest | MIT |

## الخطوط / Fonts

التطبيق لا يوزّع خطوطًا؛ يستخدم خطوط النظام (Segoe UI / Arial / Tahoma) المرخّصة مع Windows نفسه.

## إفصاح / Disclosure

- **لا ذكاء اصطناعي** في أي جزء من المعالجة — كل المنطق حتمي (قواعد Unicode/هندسة/إحصاء بسيط).
- **لا خدمات سحابية، لا تتبع، لا تلمتري، لا حسابات.**
- عند إعادة توزيع التطبيق يجب الالتزام بشروط AGPL-3.0 (توفير المصدر).
