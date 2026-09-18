"""النافذة الرئيسية — RTL بالكامل، أقسام واضحة، تشغيل كامل بلوحة المفاتيح،
ومتوافقة مع قارئ الشاشة (تسميات Accessible + إعلانات UIA Alert)."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

from .. import strings as S
from ..config import load
from ..core.engine import convert_pdf  # noqa: F401 (تُستخدم عبر worker)
from ..core.jobstate import project_dir_for
from ..scanner import wia
from .announcements import Announcer
from .settings_dialog import SettingsDialog
from .worker import ConvertWorker

_PAGE_NOTE_EVERY = 1  # سجل كل صفحة؛ الإعلان الصوتي كل 10 صفحات


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load()
        self.worker: ConvertWorker | None = None
        self.last_summary: dict | None = None
        self.scanned_images: list[str] = []

        self.setWindowTitle(S.t("app", self.cfg.get("ui_lang", "ar")))
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(760, 640)
        self.setStyleSheet("QWidget { font-size: 11pt; }")

        root = QWidget()
        self.setCentralWidget(root)
        col = QVBoxLayout(root)

        # ===== المستند المصدر =====
        src = QGroupBox("المستند المصدر")
        src.setAccessibleName("قسم المستند المصدر")
        gl = QGridLayout(src)
        self.file_edit = QLineEdit()
        self.file_edit.setAccessibleName("مسار ملف PDF")
        self.file_edit.setPlaceholderText("اختر ملف PDF…")
        browse = QPushButton("فتح PDF…")
        browse.setAccessibleDescription("اختيار ملف PDF للتحويل — اختصار كنترول حرف O")
        browse.clicked.connect(self.select_pdf)
        gl.addWidget(self.file_edit, 0, 0)
        gl.addWidget(browse, 0, 1)
        col.addWidget(src)

        # ===== خيارات التحويل =====
        opts = QGroupBox("خيارات التحويل")
        opts.setAccessibleName("قسم خيارات التحويل")
        og = QGridLayout(opts)
        self.lang_combo = QComboBox()
        for label, val in (("عربية + إنجليزية", "ara+eng"), ("عربية فقط", "ara"), ("إنجليزية فقط", "eng")):
            self.lang_combo.addItem(label, val)
        self.lang_combo.setCurrentIndex(max(self.lang_combo.findData(self.cfg.get("lang", "ara+eng")), 0))
        self.lang_combo.setAccessibleName("لغة التعرف")
        og.addWidget(QLabel("اللغة:"), 0, 0)
        og.addWidget(self.lang_combo, 0, 1)

        self.quality_combo = QComboBox()
        for label, val in (("سريع", "fast"), ("متوازن — موصى به", "balanced"), ("دقة عالية", "high")):
            self.quality_combo.addItem(label, val)
        self.quality_combo.setCurrentIndex(max(self.quality_combo.findData(self.cfg.get("quality", "balanced")), 0))
        self.quality_combo.setAccessibleName("جودة التحويل")
        og.addWidget(QLabel("الجودة:"), 0, 2)
        og.addWidget(self.quality_combo, 0, 3)

        self.fmt = {}
        for i, (f, label) in enumerate((("docx", "وورد"), ("txt", "نص"), ("html", "HTML"), ("pdf", "PDF قابل للبحث"))):
            cb = QCheckBox(label)
            cb.setChecked(f in self.cfg.get("formats", ["docx"]))
            cb.setAccessibleName(f"صيغة {label}")
            self.fmt[f] = cb
            og.addWidget(cb, 1, i)

        self.out_edit = QLineEdit(self.cfg.get("out_dir", ""))
        self.out_edit.setAccessibleName("مجلد المخرجات")
        self.out_edit.setPlaceholderText("افتراضي: بجوار الملف")
        out_btn = QPushButton("استعراض…")
        out_btn.clicked.connect(self._browse_out)
        og.addWidget(QLabel("المخرجات:"), 2, 0)
        og.addWidget(self.out_edit, 2, 1)
        og.addWidget(out_btn, 2, 2)

        settings_btn = QPushButton("الإعدادات…")
        settings_btn.clicked.connect(self.open_settings)
        og.addWidget(settings_btn, 2, 3)
        col.addWidget(opts)

        # ===== التنفيذ =====
        run = QGroupBox("التنفيذ")
        run.setAccessibleName("قسم التنفيذ")
        rg = QGridLayout(run)
        self.button_start = QPushButton("ابدأ التحويل")
        self.button_start.setAccessibleDescription("بدء التحويل — كنترول إنتر")
        self.button_start.clicked.connect(self.start)
        self.button_pause = QPushButton("إيقاف مؤقت")
        self.button_pause.setEnabled(False)
        self.button_pause.clicked.connect(self.toggle_pause)
        self.button_cancel = QPushButton("إلغاء")
        self.button_cancel.setEnabled(False)
        self.button_cancel.clicked.connect(self.cancel)
        self.button_output = QPushButton("فتح مجلد المخرجات")
        self.button_output.setEnabled(False)
        self.button_output.clicked.connect(self.open_output)
        rg.addWidget(self.button_start, 0, 0)
        rg.addWidget(self.button_pause, 0, 1)
        rg.addWidget(self.button_cancel, 0, 2)
        rg.addWidget(self.button_output, 0, 3)

        scan_row_i = 1
        if wia.available():
            self.button_scan = QPushButton("مسح صفحة من الماسح")
            self.button_scan.clicked.connect(self.scan_page)
            self.button_build_scan = QPushButton("أنشئ PDF من الممسوح")
            self.button_build_scan.setEnabled(False)
            self.button_build_scan.clicked.connect(self.build_scanned_pdf)
            self.scan_label = QLabel("لا صفحات ممسوحة")
            rg.addWidget(self.button_scan, scan_row_i, 0)
            rg.addWidget(self.button_build_scan, scan_row_i, 1)
            rg.addWidget(self.scan_label, scan_row_i, 2, 1, 2)
        col.addWidget(run)

        # ===== التقدم =====
        prog = QGroupBox("التقدم")
        prog.setAccessibleName("قسم التقدم")
        pg = QGridLayout(prog)
        self.progress = QProgressBar()
        self.progress.setAccessibleName("شريط التقدم")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.page_label = QLabel("—")
        pg.addWidget(self.progress, 0, 0)
        pg.addWidget(self.page_label, 0, 1)
        col.addWidget(prog)

        # ===== الحالة + السجل =====
        self.status_label = QLabel("جاهز")
        self.status_label.setAccessibleName("الحالة")
        col.addWidget(self.status_label)
        self.announcer = Announcer(self.status_label, QPlainTextEdit())
        self.announcer.log.setReadOnly(True)
        self.announcer.log.setAccessibleName("سجل الأحداث")
        col.addWidget(self.announcer.log, 1)

        # ===== اختصارات =====
        self._shortcut("Ctrl+O", self.select_pdf)
        self._shortcut("Ctrl+Return", self.start)
        self._shortcut("Ctrl+P", self.toggle_pause)
        self._shortcut("Ctrl+Alt+C", self.cancel)
        self._shortcut("Ctrl+,", self.open_settings)

        self.announcer.announce("اقرأ جاهز. افتح ملف PDF ثم اضغط كنترول إنتر لبدء التحويل.")

    # ---------- أدوات ----------
    def _shortcut(self, seq: str, cb):
        sc = QShortcut(QKeySequence(seq), self)
        sc.activated.connect(cb)

    def select_pdf(self):
        d = self.out_edit.text() or ""
        path, _ = QFileDialog.getOpenFileName(self, "فتح PDF", d, "ملفات PDF (*.pdf)")
        if path:
            self.file_edit.setText(path)
            self.announcer.announce(f"تم اختيار {Path(path).name}")

    def _browse_out(self):
        d = QFileDialog.getExistingDirectory(self, "مجلد المخرجات", self.out_edit.text() or "")
        if d:
            self.out_edit.setText(d)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.cfg = load()
            dlg.apply_to_ui(self)
            self.announcer.announce("حُفظت الإعدادات")

    def open_output(self):
        if self.last_summary:
            outputs = self.last_summary.get("outputs", {})
            if outputs:
                QDesktopServices.openUrl(Path(list(outputs.values())[0]).parent)

    # ---------- التنفيذ ----------
    def _maybe_resume(self, pdf: str, out_dir: str) -> tuple[Path | None, bool]:
        """يعيد (project_dir, is_fresh_restart). يسأل عن الاستئناف إن وُجد مشروع غير مكتمل."""
        pdir = project_dir_for(pdf, out_dir or None)
        stf = pdir / "state.json"
        if not stf.is_file():
            return pdir, False
        try:
            st = json.loads(stf.read_text(encoding="utf-8"))
        except Exception:
            return pdir, False
        if st.get("next_page", 0) >= st.get("total", 0) > 0:
            return pdir, False  # مكتمل — سيُصدَّر من جديد بسرعة
        box = QMessageBox(self)
        box.setLayoutDirection(Qt.RightToLeft)
        box.setWindowTitle("مشروع غير مكتمل")
        box.setText(f"يوجد مشروع سابق توقف عند الصفحة {st.get('next_page', 0) + 1} من {st.get('total')}.")
        resume_btn = box.addButton("استئناف من نفس النقطة", QMessageBox.YesRole)
        fresh_btn = box.addButton("بدء من جديد", QMessageBox.NoRole)
        cancel_btn = box.addButton("إلغاء", QMessageBox.RejectRole)
        box.setDefaultButton(resume_btn)
        box.exec()
        clicked = box.clickedButton()
        if clicked is cancel_btn:
            return None, False
        if clicked is fresh_btn:
            shutil.rmtree(pdir, ignore_errors=True)
            return pdir, False
        return pdir, True

    def start(self):
        if self.worker is not None:
            return
        pdf = self.file_edit.text().strip()
        if not pdf or not Path(pdf).is_file():
            self.announcer.announce(S.t("missing_pdf"))
            return
        formats = [f for f, cb in self.fmt.items() if cb.isChecked()] or ["docx"]
        out_dir = self.out_edit.text().strip()
        picked = self._maybe_resume(pdf, out_dir)
        if picked is None:
            return
        project, _resume = picked

        self.worker = ConvertWorker(
            pdf, lang=self.lang_combo.currentData(), quality=self.quality_combo.currentData(),
            formats=formats, out_dir=out_dir, trust_text_layer=self.cfg.get("trust_text_layer", True),
            page_breaks=self.cfg.get("page_breaks", False),
            ocr_max_attempts=int(self.cfg.get("ocr_max_attempts", 4)),
            project=project)
        self.worker.progress.connect(self.on_progress)
        self.worker.page_note.connect(lambda s: self.announcer.log_line(s))
        self.worker.finished_ok.connect(self.on_done)
        self.worker.was_cancelled.connect(self.on_cancelled)
        self.worker.failed.connect(self.on_failed)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.button_start.setEnabled(False)
        self.button_pause.setEnabled(True)
        self.button_pause.setText("إيقاف مؤقت")
        self.button_cancel.setEnabled(True)
        self.button_output.setEnabled(False)
        self.announcer.announce(S.t("converting"))
        self.worker.start()

    def on_progress(self, done: int, total: int, status: str):
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(done)
        self.page_label.setText(S.t("page_of", done=done, total=total) + f" — {status}")
        if done % 10 == 0 or done == total:
            self.announcer.announce(f"اكتملت {done} من {total} صفحة", log_only=False)

    def on_done(self, summary: dict):
        self.last_summary = summary
        self._reset_buttons()
        self.button_output.setEnabled(True)
        n = len(summary.get("outputs", {}))
        self.announcer.announce(f"{S.t('done')} — {n} ملفات في مجلد المخرجات. كنترول إنتر لبدء تحويل آخر.")
        report = summary.get("project")
        if report:
            self.announcer.log_line(f"تقرير الجودة: {Path(report) / 'quality_report.txt'}")

    def on_cancelled(self):
        self._reset_buttons()
        self.announcer.announce(S.t("cancelled"))

    def on_failed(self, err: str):
        self._reset_buttons()
        self.announcer.announce(f"فشل التحويل: {err[:200]}")

    def _reset_buttons(self):
        self.button_start.setEnabled(True)
        self.button_pause.setEnabled(False)
        self.button_pause.setText("إيقاف مؤقت")
        self.button_cancel.setEnabled(False)
        self.worker = None

    def toggle_pause(self):
        if self.worker is None:
            return
        if self.worker.is_paused:
            self.worker.resume_work()
            self.button_pause.setText("إيقاف مؤقت")
            self.announcer.announce("استؤنف التحويل")
        else:
            self.worker.pause()
            self.button_pause.setText("استئناف")
            self.announcer.announce("أوقف التحويل مؤقتًا — استئناف بالإيقاف/الاستئناف مجددًا")

    def cancel(self):
        if self.worker is not None:
            self.announcer.announce("جارٍ الإلغاء…")
            self.worker.cancel()

    # ---------- الماسح ----------
    def scan_page(self):
        try:
            devices = wia.list_scanners()
        except Exception as e:
            self.announcer.announce(f"لا ماسح متاح: {e}")
            return
        device_id = devices[0]["id"] if devices else None
        if not devices:
            self.announcer.announce("لا يوجد ماسح ضوئي مثبت")
            return
        tmp = tempfile.mktemp(suffix=".png")
        try:
            path = wia.scan_page(tmp, device_id=device_id, dpi=300, wizard=True)
            self.scanned_images.append(path)
            self.scan_label.setText(f"ممسوح: {len(self.scanned_images)} صفحة")
            self.button_build_scan.setEnabled(True)
            self.announcer.announce(f"مسحت صفحة. لديك {len(self.scanned_images)} صفحات ممسوحة.")
        except Exception as e:
            self.announcer.announce(f"فشل المسح: {e}")

    def build_scanned_pdf(self):
        if not self.scanned_images:
            return
        out_dir = self.out_edit.text().strip() or str(Path.home() / "Documents")
        out_pdf = str(Path(out_dir) / "ممسوح.pdf")
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        try:
            wia.images_to_pdf(self.scanned_images, out_pdf)
            self.file_edit.setText(out_pdf)
            self.announcer.announce(f"أُنشئ {out_pdf} — جاهز للتحويل")
        except Exception as e:
            self.announcer.announce(f"فشل بناء PDF: {e}")

    # ---------- إغلاق ----------
    def closeEvent(self, ev):
        if self.worker is not None and self.worker.isRunning():
            box = QMessageBox(self)
            box.setLayoutDirection(Qt.RightToLeft)
            box.setWindowTitle("تحويل جارٍ")
            box.setText("التحويل جارٍ. الإلغاء يحفظ التقدم ويمكن استئنافه لاحقًا. إلغاء والخروج؟")
            yes = box.addButton("إلغاء التحويل والخروج", QMessageBox.YesRole)
            box.addButton("متابعة التحويل", QMessageBox.NoRole)
            box.exec()
            if box.clickedButton() is yes:
                self.worker.cancel()
                self.worker.wait(5000)
                ev.accept()
            else:
                ev.ignore()
                return
        super().closeEvent(ev)


def run_app() -> int:
    app = QApplication.instance() or QApplication()
    app.setApplicationName("اقرأ")
    app.setLayoutDirection(Qt.RightToLeft)
    w = MainWindow()
    w.show()
    # فتح ملف مُمرر في سطر الأوامر (سحب وإفلات على الاختصار)
    args = [a for a in QApplication.arguments()[1:] if a.lower().endswith(".pdf")]
    if args:
        w.file_edit.setText(args[0])
    return app.exec()
