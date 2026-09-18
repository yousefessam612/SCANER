"""نقطة الدخول: الواجهة الرسومية افتراضيًا، أو سطر الأوامر عبر convert/resume/batch/scan/selftest."""
from __future__ import annotations

import sys


def _run_gui() -> int:
    try:
        from PySide6.QtWidgets import QApplication  # noqa: F401
    except ImportError:
        print("الواجهة الرسومية تحتاج PySide6 — ثبّتها بالأمر:")
        print("    pip install PySide6")
        print("أو استخدم سطر الأوامر:  python -m app convert كتاب.pdf -f docx,pdf")
        return 2
    from .gui.main_window import run_app
    try:
        return run_app()
    except RuntimeError as e:
        if "display" in str(e).lower() or "qpa" in str(e).lower():
            print("لا توجد شاشة متاحة لهذه الجلسة (بيئة بلا واجهة رسومية).")
            print("استخدم سطر الأوامر:  python -m app convert كتاب.pdf -f docx,pdf")
            return 3
        raise


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "gui":
        args = args[1:]
        return _run_gui()
    if args and args[0] in {"convert", "resume", "batch", "selftest", "scan"}:
        from .cli import main as cli_main
        return cli_main(args)
    return _run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
