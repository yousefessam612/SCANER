"""إعلانات قارئ الشاشة — ثلاثة مسارات كي لا يضيع الإعلان أبدًا:

1) UIA Alert عبر QAccessible (يقرأه NVDA/JAWS/الراوي فورًا)
2) ملصق الحالة المرئي (للمكفوفين جزئيًا والمستخدمين الآخرين)
3) السجل النصي (مرجع دائم يمكن تصفحه)
"""
from __future__ import annotations

from PySide6.QtGui import QAccessible, QAccessibleEvent
from PySide6.QtWidgets import QLabel, QPlainTextEdit


class Announcer:
    def __init__(self, status_label: QLabel, log: QPlainTextEdit):
        self.status = status_label
        self.log = log

    def announce(self, text: str, log_only: bool = False):
        text = str(text)
        self.log.appendPlainText(text)
        if not log_only:
            self.status.setText(text)
            # UIA Alert: أهم مسار لقارئ الشاشة
            try:
                ev = QAccessibleEvent(self.status, QAccessible.Event.Alert)
                QAccessible.updateAccessibility(ev)
            except Exception:
                pass  # الإعلان لا يُسقط التطبيق أبدًا

    def log_line(self, text: str):
        """سطر سجل صامت (لا يُعلن صوتيًا) — لتفاصيل كل صفحة."""
        self.log.appendPlainText(text)
