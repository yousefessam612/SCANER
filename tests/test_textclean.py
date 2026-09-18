"""اختبارات التنظيف وبناء الكتل."""
from app.core.textclean import build_blocks, clean_text, is_list_item, is_likely_heading


def test_clean_strips_controls_and_spaces():
    s = "  بسم\u200f  الله\u200b  \n\n\n\nالرحمن  "
    out = clean_text(s)
    assert "\u200f" not in out and "\u200b" not in out
    assert "\n\n\n" not in out
    assert out == "بسم الله\n\nالرحمن"


def test_list_items():
    assert is_list_item("• نقطة أولى")
    assert is_list_item("1. رقمية")
    assert is_list_item("- شرطة")
    assert not is_list_item("نص عادي طويل ليس بقائمة")


def test_heading_heuristics():
    assert is_likely_heading("الفصل الأول", "نص الفقرة التالية طويل")
    assert not is_likely_heading("هذه جملة طويلة نسبيًا تنتهي بنقطة.", "تابت")
    assert not is_likely_heading("• عنصر قائمة")


def test_build_blocks_paragraph_merge():
    lines = [
        {"text": "هذه بداية الفقرة الأولى وتحتوي", "page": 0, "y0": 100, "y1": 114},
        {"text": "على كلمات متتابعة في نفس السطر المنطقي", "page": 0, "y0": 116, "y1": 130},
        {"text": "وتصل ببعضها فقرة واحدة", "page": 0, "y0": 132, "y1": 146},
        {"text": "هذه فقرة جديدة بعد فجوة كبيرة", "page": 0, "y0": 220, "y1": 234},
    ]
    blocks = build_blocks(lines)
    types = [b["type"] for b in blocks]
    assert types == ["paragraph", "paragraph"]
    assert "وتصل ببعضها فقرة واحدة" in blocks[0]["text"]


def test_build_blocks_list_grouping():
    lines = [
        {"text": "• الأولى", "page": 0, "y0": 100, "y1": 114},
        {"text": "• الثانية", "page": 0, "y0": 116, "y1": 130},
    ]
    blocks = build_blocks(lines)
    assert all(b["type"] == "list_item" for b in blocks)
    assert blocks[0]["text"] == "الأولى"
