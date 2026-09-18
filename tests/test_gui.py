"""اختبارات الواجهة الرسومية — تعمل offscreen (تُتخطى إن لم تتوفر PySide6)."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from conftest import make_arabic_pdf  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setLayoutDirection(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.RightToLeft)
    yield app


def test_main_window_builds_rtl(qapp):
    from app.gui.main_window import MainWindow
    w = MainWindow()
    assert "اقرأ" in w.windowTitle()
    assert w.button_start.text() == "ابدأ التحويل"
    assert w.lang_combo.currentData() in ("ara+eng", "ara", "eng")
    w.announcer.announce("تجربة إعلان")
    assert "تجربة إعلان" in w.announcer.log.toPlainText()
    assert w.status_label.text() == "تجربة إعلان"
    w.close()


def test_gui_worker_full_conversion(qapp, tmp_path, need_ocr):
    """تحويل حقيقي عبر خيط الواجهة: PDF عربي → TXT على القرص."""
    from app.gui.worker import ConvertWorker

    pdf = make_arabic_pdf(tmp_path / "gui.pdf", ["جملة عربية لاختبار الواجهة الرسومية مع رقم 33"])
    result: dict = {}
    loop = QEventLoop()
    w = ConvertWorker(str(pdf), lang="ara+eng", quality="balanced", formats=["txt"],
                      out_dir=str(tmp_path / "o"), trust_text_layer=True, page_breaks=False)
    w.finished_ok.connect(lambda s: (result.update(s), loop.quit()))
    w.was_cancelled.connect(lambda: (result.update({"status": "cancelled"}), loop.quit()))
    w.failed.connect(lambda e: (result.update({"status": "error", "err": e}), loop.quit()))
    QTimer.singleShot(240_000, loop.quit)
    w.start()
    loop.exec()
    w.wait(10_000)
    assert result.get("status") == "done", result
    out = tmp_path / "o" / "gui.iqra_project" / "output" / "gui.txt"
    assert out.is_file()


def test_settings_dialog_roundtrip(qapp, tmp_path, monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg, "settings_path", lambda: tmp_path / "settings.json")

    from app.gui.settings_dialog import SettingsDialog
    d = SettingsDialog()
    d.lang.setCurrentIndex(d.lang.findData("eng"))
    d.quality.setCurrentIndex(d.quality.findData("high"))
    d.attempts.setValue(6)
    d.save_settings()
    saved = cfg.load()
    assert saved["lang"] == "eng" and saved["quality"] == "high" and saved["ocr_max_attempts"] == 6


def test_resume_prompt_logic(qapp, tmp_path, need_ocr):
    """مشروع مكتمل → لا سؤال استئناف؛ غير مكتمل → توجد حالة محفوظة."""
    import json

    from app.core.engine import convert_pdf
    from app.gui.main_window import MainWindow
    pdf = make_arabic_pdf(tmp_path / "r.pdf", ["صفحة للاستئناف"])
    pdir = tmp_path / "r.iqra_project"  # نفس تسمية project_dir_for
    convert_pdf(str(pdf), lang="ara+eng", formats=["txt"], project=pdir)
    st = json.loads((pdir / "state.json").read_text(encoding="utf-8"))
    assert st["next_page"] == st["total"]  # مكتمل
    w = MainWindow()
    got, fresh = w._maybe_resume(str(pdf), str(tmp_path))
    assert got == pdir and fresh is False  # بلا سؤال لمشروع مكتمل
    w.close()
