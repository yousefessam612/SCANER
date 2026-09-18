"""بانِي طبقة النص المخفية القابلة للبحث في PDF العربي — مبنيًا يدويًا لا عبر Tesseract.

لماذا يدويًا؟ مخرَج PDF من Tesseract يرسم الكلمات العربية بمصفوفة معكوسة فتُستخرج
معكوسة (ةغللا بدل اللغة) في أغلب العارضات. نبنيها نحن:
- خط Type0 بترميز Identity-H وToUnicode CMap بحيث CID = Unicode → الاستخراج منطقي.
- كل كلمة تُكتب محارفها **بالعكس البصري** (تتقدم محارف PDF يسارًا→يمينًا دائمًا)
  فيقع أول حرف منطقي أقصى اليمين ويقرأه المستخرج منطقيًا صحيحًا.
- Tz يضبط تقدّم الكلمة ليطابق صندوقها → مستطيلات البحث تضبط على الكلمة المرئية.
- فراغ صريح في منتصف الفجوة بين كل كلمتين متجاورتين (يدعم أرقامًا ولاتينيًا).
- نص مخفي بوضع الرسم 3 Tr: الصفحة الأصلية تبقى كما هي.
"""
from __future__ import annotations

import io

import pymupdf

from .languages import _fix_mixed_token, has_arabic


def _font_program() -> bytes | None:
    """خط عربي لغرض الـ tokenization الداخلي (لا يُرسم أبدًا — النص مخفي). يُبحث في مواضع معروفة."""
    import os
    from pathlib import Path
    candidates = []
    env = os.environ.get("IQRA_LAYER_FONT")
    if env:
        candidates.append(Path(env))
    root = Path(__file__).resolve().parent.parent.parent
    candidates += [
        root / "tests" / "fixtures" / "Amiri-Regular.ttf",
        root / "runtime" / "fonts" / "Amiri-Regular.ttf",
        Path("C:/Windows/Fonts/tahoma.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/kacst/KacstOne.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for c in candidates:
        try:
            if c.is_file():
                return c.read_bytes()
        except Exception:
            continue
    return None


class SearchablePDFBuilder:
    """يجمع صفحات أصلية (بايت-بايت) + طبقة نص مخفية منطقية قابلة للبحث."""

    def __init__(self):
        self.doc = pymupdf.open()
        self._font_xref: int | None = None
        self._tounicode_xref: int | None = None
        self._codes: set[int] = set()

    # ---------- font plumbing ----------
    def _ensure_font(self) -> int:
        if self._font_xref is not None:
            return self._font_xref
        doc = self.doc
        ffx = doc.get_new_xref()
        doc.update_object(ffx, "<< >>")
        prog = _font_program() or b""
        doc.update_stream(ffx, prog, compress=True)
        fd = doc.get_new_xref()
        doc.update_object(fd, (
            "<< /Type /FontDescriptor /FontName /IqraLayer /Flags 4 /FontBBox [0 -300 1400 1200] "
            "/ItalicAngle 0 /Ascent 1000 /Descent -300 /CapHeight 700 /StemV 80 "
            f"/FontFile2 {ffx} 0 R >>"))
        desc = doc.get_new_xref()
        doc.update_object(desc, (
            "<< /Type /Font /Subtype /CIDFontType2 /BaseFont /IqraLayer "
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
            f"/FontDescriptor {fd} 0 R /DW 1000 /CIDToGIDMap /Identity >>"))
        # ToUnicode: يُبنى كاملًا عند الحفظ من كل المحارف المستخدمة (حاسم لصحة الاستخراج والبحث)
        self._tounicode_xref = doc.get_new_xref()
        doc.update_object(self._tounicode_xref, "<< >>")
        fx = doc.get_new_xref()
        doc.update_object(fx, (
            "<< /Type /Font /Subtype /Type0 /BaseFont /IqraLayer /Encoding /Identity-H "
            f"/DescendantFonts [{desc} 0 R] /ToUnicode {self._tounicode_xref} 0 R >>"))
        self._font_xref = fx
        return fx

    def _write_tounicode(self):
        if self._tounicode_xref is None:
            return  # لا طبقات نص مضافة أصلًا
        doc = self.doc
        codes = sorted(set(self._codes) | {0x20})
        cmap = [
            "/CIDInit /ProcSet findresource begin",
            "12 dict begin",
            "begincmap",
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
            "/CMapName /Adobe-Identity-UCS def",
            "/CMapType 2 def",
            "1 begincodespacerange",
            "<0000> <FFFF>",
            "endcodespacerange",
        ]
        for i in range(0, len(codes), 100):
            chunk = codes[i:i + 100]
            cmap.append(f"{len(chunk)} beginbfchar")
            cmap += [f"<{cp:04X}> <{cp:04X}>" for cp in chunk]
            cmap.append("endbfchar")
        cmap += [
            "endcmap",
            "CMapName currentdict /CMap defineresource pop",
            "end",
            "end",
        ]
        doc.update_stream(self._tounicode_xref, "\n".join(cmap).encode(), compress=True)

    def _register_font_on_page(self, page: pymupdf.Page, font_xref: int):
        res = self.doc.xref_get_key(page.xref, "Resources")
        if res and res[0] == "xref":
            res_xref = int(res[1].split()[0])
            existing = self.doc.xref_get_key(res_xref, "Font")
            if existing and existing[0] == "dict":
                self.doc.xref_set_key(res_xref, "Font", existing[1][:-2] + f" /F0 {font_xref} 0 R >>")
            else:
                self.doc.xref_set_key(res_xref, "Font", f"<< /F0 {font_xref} 0 R >>")
        else:
            self.doc.xref_set_key(page.xref, "Resources/Font", f"<< /F0 {font_xref} 0 R >>")

    # ---------- page building ----------
    def add_page(self, page_width: float, page_height: float, words: list[dict],
                 background_pdf: pymupdf.Document | None = None, background_page: int | None = None,
                 layer: str = "none"):
        """إضافة صفحة: الأصل (حسب حالة طبقتها) + طبقة كلمات مخفية منطقية.

        - layer="trusted": الطبقة الأصلية سليمة → نسخ الصفحة كما هي بلا طبقة إضافية.
        - layer="none": بلا طبقة نص → نسخ الأصل + طبقتنا فوقه.
        - layer="broken": طبقة فاسدة → رسم الأصل صورةً (لا تُنسخ طبقته الفاسدة) + طبقتنا.

        - الكلمات المُدخلة **منطقية النص** (نهائي كما سيُستخرج)، والترتيب في السطر
          يُحدَّد هندسيًا: السطر العربي يُبث من أقصى اليمين ثم يسارًا.

        words: [{text: منطقي, bbox: [x0,y0,x1,y1] بإحداثيات نقاط PDF (أصل أعلى-يسار)}]
        """
        if layer == "trusted":
            self.doc.insert_pdf(background_pdf, from_page=background_page, to_page=background_page)
            return
        if layer == "broken":
            page = self.doc.new_page(width=page_width, height=page_height)
            pix = background_pdf[background_page].get_pixmap(dpi=150)
            page.insert_image(page.rect, stream=pix.tobytes("png"))
        else:
            self.doc.insert_pdf(background_pdf, from_page=background_page, to_page=background_page)
            page = self.doc[self.doc.page_count - 1]
        if not words:
            return
        # تجميع الأسطر هندسيًا ثم الكلمات داخل السطر بصريًا
        lines = self._cluster_lines(words)
        ops: list[str] = ["q", "3 Tr"]
        H = page_height
        for lwords in lines:
            visual = sorted(lwords, key=lambda w: w["bbox"][0])
            is_ar = any(has_arabic(w["text"]) for w in visual)
            logical_order = visual[::-1] if is_ar else visual
            for wi, w in enumerate(logical_order):
                x0, y0, x1, y1 = w["bbox"]
                yt, yb = H - y1, H - y0          # قلب الإحداثي الرأسي (أصل PDF أسفل-يسار)
                h = max(yb - yt, 1.0)
                size = h * 0.72
                baseline = yb - h * 0.22
                # العقد: نص الكلمة الداخل منطقي → نكتبه بالترتيب البصري (عكس مع الحفاظ
                # على الجُزر اللاتينية/الرقمية LTR) لأن المستخرجات تطبّق BiDi فتُعيد المنطقي،
                # والبحث في العارضات يعمل على السلسلة البصرية.
                if is_ar and has_arabic(w["text"]):
                    vis = _fix_mixed_token(w["text"])
                else:
                    vis = w["text"]
                vis = "".join(c for c in vis if 0 < ord(c) < 0xFFFF) or " "
                self._codes.update(ord(c) for c in vis)
                hexs = "".join(f"{ord(c):04X}" for c in vis)
                bw = max(x1 - x0, 1.0)
                tz = max(min((bw / (len(vis) * size)) * 100.0, 400.0), 5.0)
                ops.append(f"BT 1 0 0 1 {x0:.2f} {baseline:.2f} Tm /F0 {size:.2f} Tf {tz:.1f} Tz <{hexs}> Tj ET")
                if wi < len(logical_order) - 1:
                    b = logical_order[wi + 1]
                    mid = (max(x0, b["bbox"][0]) + min(x1, b["bbox"][2])) / 2.0
                    bytop = H - max(y1, b["bbox"][3])
                    bh = max(max(y1, b["bbox"][3]) - min(y0, b["bbox"][1]), 1.0)
                    ops.append(f"BT 1 0 0 1 {mid:.2f} {bytop + bh * 0.22:.2f} Tm /F0 {bh * 0.72:.2f} Tf <0020> Tj ET")
        ops.append("ET")
        stream = "\n".join(ops).encode()
        conts = page.get_contents()
        # نلحق ستريم الطبقة كعنصر جديد في مصفوفة /Contents — لا نلمس ستريمات الأصل
        # (تعديل الموجود يفسد صفحات متعددة الستريعات)
        ncx = self.doc.get_new_xref()
        self.doc.update_object(ncx, "<< >>")
        self.doc.update_stream(ncx, stream, compress=True)
        if conts:
            arr = " ".join(f"{c} 0 R" for c in conts) + f" {ncx} 0 R"
            self.doc.xref_set_key(page.xref, "Contents", f"[{arr}]")
        else:
            self.doc.xref_set_key(page.xref, "Contents", f"{ncx} 0 R")
        self._register_font_on_page(page, self._ensure_font())

    @staticmethod
    def _cluster_lines(words: list[dict]) -> list[list[dict]]:
        ws = sorted(words, key=lambda w: (w["bbox"][1], w["bbox"][0]))
        lines: list[list[dict]] = []
        for w in ws:
            yc = (w["bbox"][1] + w["bbox"][3]) / 2
            h = w["bbox"][3] - w["bbox"][1]
            placed = False
            for ln in lines:
                lyc = (ln[0]["bbox"][1] + ln[0]["bbox"][3]) / 2
                if abs(yc - lyc) <= max(3.0, 0.6 * h):
                    ln.append(w)
                    placed = True
                    break
            if not placed:
                lines.append([w])
        return lines

    def save(self, path: str):
        self._write_tounicode()
        self.doc.save(path, garbage=3, deflate=True)

    def tobytes(self) -> bytes:
        self._write_tounicode()
        return self.doc.tobytes(garbage=3, deflate=True)
