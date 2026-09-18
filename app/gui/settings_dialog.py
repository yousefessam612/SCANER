"""حوار الإعدادات: يقرأ ويكتب ملف الإعدادات عبر app.config."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLineEdit, QPushButton, QSpinBox, QVBoxLayout,
)

from ..config import DEFAULTS, load, save


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("الإعدادات — اقرأ")
        self.setLayoutDirection(self.parent().layoutDirection() if self.parent() else __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.RightToLeft)
        cfg = load()

        form = QFormLayout(self)

        self.ui_lang = QComboBox()
        self.ui_lang.addItem("العربية", "ar")
        self.ui_lang.addItem("English", "en")
        self.ui_lang.setCurrentIndex(max(self.ui_lang.findData(cfg.get("ui_lang", "ar")), 0))
        form.addRow("لغة الواجهة:", self.ui_lang)

        self.lang = QComboBox()
        for label, val in (("عربية + إنجليزية (موصى به)", "ara+eng"), ("عربية فقط", "ara"), ("إنجليزية فقط", "eng")):
            self.lang.addItem(label, val)
        self.lang.setCurrentIndex(max(self.lang.findData(cfg.get("lang", "ara+eng")), 0))
        form.addRow("لغة التعرف:", self.lang)

        self.quality = QComboBox()
        for label, val in (("سريع (200)", "fast"), ("متوازن (300) — موصى به", "balanced"), ("دقة عالية (400)", "high")):
            self.quality.addItem(label, val)
        self.quality.setCurrentIndex(max(self.quality.findData(cfg.get("quality", "balanced")), 0))
        form.addRow("الجودة:", self.quality)

        grp = QGroupBox("صيغ المخرجات")
        lay = QHBoxLayout(grp)
        self.format_boxes: dict[str, QCheckBox] = {}
        for f, label in (("docx", "وورد"), ("txt", "نص"), ("html", "HTML"), ("pdf", "PDF قابل للبحث")):
            cb = QCheckBox(label)
            cb.setChecked(f in cfg.get("formats", ["docx"]))
            self.format_boxes[f] = cb
            lay.addWidget(cb)
        form.addRow(grp)

        self.trust = QCheckBox("ثق بطبقة النص في PDF (إلغاؤها يفرض OCR دائمًا)")
        self.trust.setChecked(bool(cfg.get("trust_text_layer", True)))
        form.addRow(self.trust)

        self.page_breaks = QCheckBox("فاصل صفحة بين صفحات PDF في الوورد")
        self.page_breaks.setChecked(bool(cfg.get("page_breaks", False)))
        form.addRow(self.page_breaks)

        self.attempts = QSpinBox()
        self.attempts.setRange(1, 8)
        self.attempts.setValue(int(cfg.get("ocr_max_attempts", DEFAULTS["ocr_max_attempts"])))
        form.addRow("أقصى محاولات OCR للصفحة:", self.attempts)

        row = QHBoxLayout()
        self.out_dir = QLineEdit(cfg.get("out_dir", ""))
        browse = QPushButton("استعراض…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.out_dir)
        row.addWidget(browse)
        form.addRow("مجلد المخرجات الافتراضي:", row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _browse(self):
        from PySide6.QtWidgets import QFileDialog
        d = QFileDialog.getExistingDirectory(self, "مجلد المخرجات", self.out_dir.text() or "")
        if d:
            self.out_dir.setText(d)

    def _save_and_close(self):
        self.save_settings()
        self.accept()

    def save_settings(self):
        cfg = load()
        cfg.update({
            "ui_lang": self.ui_lang.currentData(),
            "lang": self.lang.currentData(),
            "quality": self.quality.currentData(),
            "formats": [f for f, cb in self.format_boxes.items() if cb.isChecked()] or ["docx"],
            "trust_text_layer": self.trust.isChecked(),
            "page_breaks": self.page_breaks.isChecked(),
            "ocr_max_attempts": self.attempts.value(),
            "out_dir": self.out_dir.text().strip(),
        })
        save(cfg)

    def apply_to_ui(self, w):
        """يطبق الإعدادات المحفوظة على عناصر النافذة الرئيسية (يُستدعى بعد OK)."""
        from PySide6.QtCore import Qt
        w.lang_combo.setCurrentIndex(max(w.lang_combo.findData(load()["lang"]), 0))
        w.quality_combo.setCurrentIndex(max(w.quality_combo.findData(load()["quality"]), 0))
