"""خيط العمل: يغلّف محرك التحويل ويبث تقدمه كإشارات Qt آمنة للخيوط."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from ..core.engine import convert_pdf


class ConvertWorker(QThread):
    progress = Signal(int, int, str)      # (منجز, إجمالي, حالة الصفحة)
    page_note = Signal(str)               # ملاحظة صفحة للسجل فقط
    finished_ok = Signal(dict)            # ملخص {outputs, pages, ...}
    was_cancelled = Signal()
    failed = Signal(str)

    def __init__(self, pdf_path: str, *, lang: str, quality: str, formats: list[str],
                 out_dir: str, trust_text_layer: bool, page_breaks: bool,
                 ocr_max_attempts: int = 4, project=None, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.opts = dict(lang=lang, quality=quality, formats=formats, out_dir=out_dir,
                         trust_text_layer=trust_text_layer, page_breaks=page_breaks,
                         ocr_max_attempts=ocr_max_attempts, project=project)
        self._cancel = False
        self._pause = threading.Event()

    def run(self):
        try:
            summary = convert_pdf(
                self.pdf_path,
                lang=self.opts["lang"], quality=self.opts["quality"],
                formats=self.opts["formats"], out_dir=self.opts["out_dir"],
                project=self.opts["project"],
                on_progress=self._on_progress,
                should_cancel=lambda: self._cancel,
                pause_event=self._pause,
                trust_text_layer=self.opts["trust_text_layer"],
                ocr_max_attempts=self.opts["ocr_max_attempts"],
                page_breaks=self.opts["page_breaks"])
        except Exception as e:  # noqa: BLE001 — أي خطأ يصل للمستخدم بنص واضح
            self.failed.emit(str(e))
            return
        status = summary.get("status")
        if status == "cancelled":
            self.was_cancelled.emit()
        elif status == "done":
            self.finished_ok.emit(summary)
        else:
            self.failed.emit(str(summary))

    def _on_progress(self, done: int, total: int, pr: dict):
        st = pr.get("status", "?")
        label = {"ok": "نجحت", "suspect": "تحتاج مراجعة", "fail": "فشلت"}.get(st, st)
        src = "نص" if pr.get("source") == "text" else "تعرف ضوئي"
        self.progress.emit(done, total, label)
        self.page_note.emit(f"صفحة {done}/{total} — {label} ({src})")

    # ------- تحكم -------
    def cancel(self):
        self._cancel = True
        self._pause.clear()

    def pause(self):
        self._pause.set()

    def resume_work(self):
        self._pause.clear()

    @property
    def is_paused(self) -> bool:
        return self._pause.is_set()
