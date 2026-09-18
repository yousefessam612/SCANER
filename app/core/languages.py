"""تحليل النص العربي/اللاتيني: الاتجاه، السكربت السائد، إصلاح العربي المعكوس.

جوهر إصلاح «ةغللا → اللغة»:
- ملفات PDF العربية كثيرًا ما تخزّن النص بأشكال العرض (U+FB50–U+FEFF) وبترتيب بصري معكوس.
- الطبقة النصية من OCR العربي (Tesseract) تُرجع كلمات معكوسة الحروف وترتيبها من اليسار لليمين.
الحل حتمي 100% بلا أي ذكاء اصطناعي:
  1) NFKC يفكّ أشكال العرض إلى حروف أساس.
  2) نعكس قائمة كلمات السطر كاملة (الترتيب البصري → المنطقي).
  3) نعكس حروف كل كلمة عربية، مع إعادة عكس الجُزر اللاتينية/الرقمية داخلها.
  4) المقاطع اللاتينية المتصلة نعيد ترتيبها داخليًا لتبقى بترتيبها الصحيح.
"""
from __future__ import annotations

import re
import unicodedata

AR_RANGES = (("\u0600", "\u06FF"), ("\u0750", "\u077F"), ("\u08A0", "\u08FF"), ("\uFB50", "\uFDFF"), ("\uFE70", "\uFEFF"))
LATIN_RE = re.compile(r"[A-Za-z]")
DIGIT_RE = re.compile(r"[0-9\u0660-\u0669\u06F0-\u06F9]")

# محارف اتجاه ثنائي لا تظهر في النص النهائي
BIDI_CTRL_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]")

# لغات تستخدم حروفًا عربية-فارسية إضافية (تظهر عند تعطّل خرائط الترميز)
FOREIGN_ARABIC = set(
    "\u063b\u063c\u063d\u063e\u063f"  # حروف عربية غير مستخدمة تظهر عند تعطُّل الخرائط
    "\u0679\u0686\u0688\u0691\u0698\u06a9\u06af\u06be\u06c1\u06cc\u06d2\u06d5"  # فارسية/أردوية
)


def is_arabic_char(c: str) -> bool:
    return any(lo <= c <= hi for lo, hi in AR_RANGES)


def has_arabic_char(s: str) -> bool:
    """هل السلسلة تحوي محرفًا عربيًا واحدًا على الأقل (للحكم على الاتجاه)."""
    return any(is_arabic_char(c) for c in s)


def strip_bidi_controls(s: str) -> str:
    return BIDI_CTRL_RE.sub("", s)


def script_stats(text: str) -> dict:
    st = {"ar": 0, "latin": 0, "digit": 0, "space": 0, "other": 0}
    for c in text:
        if is_arabic_char(c):
            st["ar"] += 1
        elif LATIN_RE.match(c):
            st["latin"] += 1
        elif DIGIT_RE.match(c):
            st["digit"] += 1
        elif c.isspace():
            st["space"] += 1
        else:
            st["other"] += 1
    return st


def dominant_script(text: str) -> str:
    st = script_stats(text)
    if st["ar"] == 0 and st["latin"] == 0:
        return "none"
    return "ar" if st["ar"] >= st["latin"] else "latin"


def has_arabic(s: str) -> bool:
    return any(is_arabic_char(c) for c in s)


def _is_latin_token(tok: str) -> bool:
    return bool(LATIN_RE.search(tok)) and not has_arabic(tok)


def _fix_mixed_token(tok: str) -> str:
    """كلمة بصريّة → منطقية: عكس + NFKC لفكّ أشكال العرض + تنظيف الليغاتورات
    + إعادة عكس الجُزر اللاتينية/الرقمية.

    مثال: '123ع' → 'ع321' → 'ع123'، و'ﺓﻝﻱﻡﺝ' → 'ﺝﻡﻱﻝﺓ' → NFKC → 'جميلة'.
    """
    rev = tok[::-1]
    rev = unicodedata.normalize("NFKC", rev)
    rev = _clean_ligature_artifacts(rev)
    return re.sub(r"[0-9A-Za-z\u0660-\u0669\u06F0-\u06F9]+", lambda m: m.group(0)[::-1], rev)


def normalize_word(tok: str) -> str:
    """كلمة منطقية الترتيب لكنها قد تحمل أشكال عرض/ليغاتورات → NFKC فقط بلا عكس."""
    if not has_arabic(tok):
        return tok
    norm = unicodedata.normalize("NFKC", tok)
    return _clean_ligature_artifacts(norm)


def fix_word_to_logical(tok: str) -> str:
    """تحويل كلمة واحدة بصريّة (من OCR عربي) إلى منطقية.

    - كلمة عربية: عكس الحروف + NFKC لفكّ أشكال العرض + تنظيف الليغاتورات.
    - لاتينية/رقمية: تبقى كما هي (التطبيق مرتين = بلا أثر).
    مثال: 'ةملكو321' → 'وكلمة123'، و'ﺓﻝﻱﻡﺝ' → 'جميلة'، و'English' → 'English'.
    """
    return _fix_mixed_token(tok)


def order_logical_by_position(words: list[str]) -> list[str]:
    """ترتيب كلمات **منطقية أصلاً** (من طبقة نص سليمة) بحسب مواقعها البصرية.

    السطر العربي: أول كلمة منطقية هي أقصى اليمين → نعكس قائمة اليسار→يمين
    ثم نعيد المقاطع اللاتينية المتصلة إلى ترتيبها الداخلي.
    """
    if not words:
        return words
    joined = " ".join(words)
    if dominant_script(joined) != "ar":
        return list(words)
    out = list(reversed(words))
    i = 0
    while i < len(out):
        if _is_latin_token(out[i]):
            j = i
            while j + 1 < len(out) and _is_latin_token(out[j + 1]):
                j += 1
            if j > i:
                out[i:j + 1] = out[i:j + 1][::-1]
            i = j + 1
        else:
            i += 1
    return out


def reorder_visual_to_logical(words: list[str]) -> list[str]:
    """إعادة بناء ترتيب القراءة لسطر من كلماته بترتيبها البصري (يسار→يمين).

    - سطر عربي: عكس قائمة الكلمات + عكس حروف كل كلمة عربية.
    - المقاطع اللاتينية المتصلة تُعكس قائمةً لتصبح بترتيبها الصحيح.
    - سطر لاتيني خالص: يُعاد كما هو.
    """
    if not words:
        return words
    joined = unicodedata.normalize("NFKC", " ".join(words))
    if dominant_script(joined) != "ar":
        return list(words)
    out = [fix_word_to_logical(w) if has_arabic(w) else w for w in reversed(words)]
    # إعادة ترتيب المقاطع اللاتينية المتصلة (كلمة أو أكثر متتالية)
    i = 0
    while i < len(out):
        if _is_latin_token(out[i]):
            j = i
            while j + 1 < len(out) and _is_latin_token(out[j + 1]):
                j += 1
            if j > i:
                out[i:j + 1] = out[i:j + 1][::-1]
            i = j + 1
        else:
            i += 1
    return out


# أشكال العرض الشائعة التي يفكّها NFKC تلقائيًا — لا حاجة لجدول يدوي.
def _clean_ligature_artifacts(text: str) -> str:
    """بقايا حروف ليغاتور بلا Unicode عربي (مثل U+01C4/U+01C1 من خطوط مجمّعة) تُستبدل بـ«لل»
    لأن أشهر الليغاتورات في العربية هي لام-لام (الله/اللہ)."""
    if not has_arabic(text):
        return text
    out_chars = []
    for c in text:
        o = ord(c)
        if 0x00C0 <= o <= 0x024F and c not in "æœÆŒ":
            # حرف لاتيني موسّع داخل نص عربي: بقايا ليغاتور
            out_chars.append("لل")
        else:
            out_chars.append(c)
    return "".join(out_chars)


def fix_visual_arabic(text: str) -> str:
    """إصلاح سطر عربي مخزّن بأشكال العرض وبترتيب بصري (أشهر عطب في ملفات PDF العربية).

    لكل سطر: NFKC ← تنظيف الليغاتورات ← عكس الترتيب البصري حسب السكربت السائد.
    الأسطر اللاتينية الخالصة تُترك كما هي.
    """
    fixed_lines = []
    for line in text.splitlines():
        norm = unicodedata.normalize("NFKC", line)
        norm = _clean_ligature_artifacts(norm)
        norm = strip_bidi_controls(norm)
        if not has_arabic(norm):
            fixed_lines.append(norm)
            continue
        if looks_reversed_arabic(norm):
            # مخزّن بترتيب بصري معكوس فعلاً → إعادة بناء كاملة
            words = [w for w in norm.split(" ") if w != ""]
            fixed_lines.append(" ".join(reorder_visual_to_logical(words)))
        else:
            # منطقي الترتيب (مستخرجات حديثة تُعيد ترتيب القراءة) → كما هو
            fixed_lines.append(norm)
    return "\n".join(fixed_lines)


# أشكال العرض: دليل قاطع على تخزين بصري (تُفكّها NFKC إلى حروف أساس)
def has_presentation_forms(text: str) -> bool:
    return any("\uFB50" <= c <= "\uFDFF" or "\uFE70" <= c <= "\uFEFF" for c in text)


def looks_reversed_arabic(text: str) -> bool:
    """كشف السطور العربية المعكوسة: كلمات تنتهي بـ«لا» وقلائل تبدأ بـ«ال».

    في نص عربي سليم «ال» التعريف تبدأ بها نسبة كبيرة من الكلمات، وتنتهي بـ«لا»
    نسبة ضئيلة. في النص المعكوس تنعكس النسب تمامًا.
    """
    text = unicodedata.normalize("NFKC", text)
    words = [w.strip("،.؛:!؟()[]{}\"'«»") for w in text.split()]
    words = [w for w in words if has_arabic(w) and len(w) >= 3]
    if len(words) == 1:
        w = words[0]
        # كلمة مفردة منقّحة: «ةغللا» معكوسة، «اللغة» سليمة
        return len(w) >= 5 and w.endswith("لا") and not w.startswith("ال")
    if len(words) < 2:
        return False
    al_start = sum(1 for w in words if w.startswith("ال"))
    la_end = sum(1 for w in words if w.endswith("لا"))
    if al_start > 0:
        return False
    if len(words) >= 4:
        return la_end / len(words) > 0.20
    return la_end / len(words) > 0.35  # أسطر قصيرة: شرط أكثر صرامة


def broken_layer_reasons(text: str) -> list[str]:
    """فحوص حتمية لطبقة نص عربية تالفة (تُعالج بالرسم + OCR بدل الثقة بها)."""
    reasons: list[str] = []
    # أشكال العرض تُفكّ أولًا حتى تُقاس الحروف الأجنبية الحقيقية
    text = unicodedata.normalize("NFKC", text)
    st = script_stats(text)
    letters = st["ar"] + st["latin"]

    # 5) طبقة «آلية»: مخرَج OCR خام مدفون (أرقام هندسة/ثقة) — فحص مستقل عن الحروف
    toks = text.split()
    if len(toks) >= 30:
        decimal_re = re.compile(r"^[0-9]+\.[0-9]+$")
        numeric = sum(1 for w in toks if DIGIT_RE.fullmatch(w) or decimal_re.fullmatch(w))
        tabs = text.count("\t")
        prose = sum(1 for w in toks if has_arabic(w) or LATIN_RE.search(w)) / len(toks)
        if tabs >= 5 and prose < 0.6:
            reasons.append("layer_tab_delimited")
        if numeric / len(toks) > 0.75 and prose < 0.3:
            reasons.append("layer_machine_numbers")

    if letters < 20:
        return reasons

    # 1) حروف عربية أجنبية/فارسية تدل على خريطة ترميز معطوبة
    foreign = sum(1 for c in text if c in FOREIGN_ARABIC)
    if foreign / letters > 0.03:
        reasons.append("foreign_letters")

    # 2) حروف لاتينية محشورة داخل كلمات عربية (بقايا ليغاتور/خرائط معطوبة)
    intrusions = 0
    for tok in text.split():
        if has_arabic(tok) and LATIN_RE.search(tok):
            t2 = strip_bidi_controls(tok)
            if LATIN_RE.search(t2):
                intrusions += 1
    if letters and intrusions / max(len(text.split()), 1) > 0.03:
        reasons.append("latin_intrusion")

    # 3) فيض العلامات: تشكيل أكثر من الحروف (طبقات OCR رديئة)
    marks = sum(1 for c in text if "\u064b" <= c <= "\u065f" or c == "\u0670")
    if marks / letters > 1.35:
        reasons.append("mark_flood")

    # 4) ترتيب معكوس إحصائيًا
    if looks_reversed_arabic(text):
        reasons.append("reversed_order")

    return reasons
