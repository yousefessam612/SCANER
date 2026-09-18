"""اختبارات تحليل اللغة وإصلاح العربية المعكوسة — سريعة حتمية بلا OCR."""
from app.core.languages import (
    broken_layer_reasons,
    fix_word_to_logical,
    fix_visual_arabic,
    looks_reversed_arabic,
    order_logical_by_position,
    reorder_visual_to_logical,
    script_stats,
    strip_bidi_controls,
    dominant_script,
)


class TestFixVisualArabic:
    def test_reversed_word(self):
        assert fix_visual_arabic("ةغللا") == "اللغة"

    def test_presentation_forms_reversed(self):
        # مثال مُثبت من التوثيق: أشكال عرض + ترتيب بصري
        assert fix_visual_arabic("ﻡﻱﺡﺭﻝﺍ ﻥﻡﺡﺭﻝﺍ") == "الرحمن الرحيم"

    def test_reversed_sentence(self):
        out = fix_visual_arabic("ةغللا ةيبرعلا اذه")
        assert "العربية" in out and "اللغة" in out

    def test_latin_line_untouched(self):
        assert fix_visual_arabic("Hello world 123") == "Hello world 123"

    def test_ligature_artifacts(self):
        # بقايا ليغاتور (الله) من خطوط مجمّعة
        out = fix_visual_arabic("ﺍǄǁﻪ")
        assert "لل" in out or "الله" in out

    def test_bidi_controls_stripped(self):
        assert strip_bidi_controls("بس\u200fم") == "بسم"


class TestReorder:
    def test_pure_arabic_line(self):
        # بصري يسار→يمين: [ةجمدم][2] — المنطقي: [2][مدمجة]
        assert reorder_visual_to_logical(["ةجمدم", "2"]) == ["2", "مدمجة"]

    def test_basmala(self):
        # البصري يسار→يمين (كما يعطي TSV): أقصى اليسار أولًا
        visual = ["ميحرلا", "نمحرلا", "هللا", "مسب"]
        assert reorder_visual_to_logical(visual) == ["بسم", "الله", "الرحمن", "الرحيم"]

    def test_latin_run_keeps_order(self):
        # «استخدم Google Docs الآن» بصريًا L→R: [نآلا][Google][Docs][مدختسا]
        visual = ["نآلا", "Google", "Docs", "مدختسا"]
        assert reorder_visual_to_logical(visual) == ["استخدم", "Google", "Docs", "الآن"]

    def test_latin_line_asis(self):
        assert reorder_visual_to_logical(["Hello", "world"]) == ["Hello", "world"]

    def test_mixed_token_digits(self):
        # كلمة تحوي عربيًا وأرقامًا: البصري '123ع' → المنطقي 'ع123'
        assert fix_word_to_logical("123ع") == "ع123"

    def test_fix_word_pure_arabic(self):
        assert fix_word_to_logical("ةملكو") == "وكلمة"

    def test_fix_word_latin_identity(self):
        assert fix_word_to_logical("English") == "English"

    def test_order_logical_by_position(self):
        # كلمات منطقية مرتبة بصريًا يسار→يمين
        assert order_logical_by_position(["الآن", "Google", "Docs", "استخدم"]) == [
            "استخدم", "Google", "Docs", "الآن"]


class TestDetectors:
    def test_reversed_heuristic_true(self):
        assert looks_reversed_arabic("ةغللا ةيبرعلا اذه ينهذ ميظنت")

    def test_reversed_heuristic_false(self):
        assert not looks_reversed_arabic("هذا نص عربي سليم باللغة العربية للتجربة")

    def test_broken_layer_foreign(self):
        text = "نص عربي طويل نسبيًا " + "ﮊﮍﮎ " * 10
        assert "foreign_letters" in broken_layer_reasons(text)

    def test_broken_layer_latin_intrusion(self):
        text = "بسم DŽǁه الرحمن الرحيم هذا اختبار للغة DŽǁغة العربية في سطر طويل للتقييم"
        assert "latin_intrusion" in broken_layer_reasons(text)

    def test_clean_text_no_reasons(self):
        assert broken_layer_reasons("هذا نص عربي سليم تمامًا بلا أي مشاكل في الطبقة النصية") == []

    def test_machine_layer(self):
        text = "12.3456\t91.518349\t78.1234\t" * 12 + "نص"
        assert any(r.startswith("layer_") for r in broken_layer_reasons(text))

    def test_script_stats(self):
        st = script_stats("مرحبا Hello 123")
        assert st["ar"] == 5 and st["latin"] == 5

    def test_dominant(self):
        assert dominant_script("مرحبا بالعربية") == "ar"
        assert dominant_script("hello there") == "latin"
