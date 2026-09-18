"""تحديد مسارات Tesseract وtessdata (مضمَّن في runtime/ أو نظامي).

الترتيب:
1) runtime/tessdata بجوار الحزمة (توزيع المثبت) أو بجوار الملف التنفيذي.
2) متغير البيئة IQRA_TESSDATA.
3) مسارات تثبيت Tesseract النظامية (Windows/Linux).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _app_root() -> Path:
    """جذر المشروع: الأب المباشر لحزمة app، أو مجلد الملف التنفيذي بعد التجميع."""
    if getattr(sys, "frozen", False):  # PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundled_tessdata() -> Path | None:
    for cand in (_app_root() / "runtime" / "tessdata", _app_root() / "tessdata"):
        if cand.is_dir() and any(cand.glob("*.traineddata")):
            return cand
    return None


def system_tessdata() -> Path | None:
    env = os.environ.get("IQRA_TESSDATA")
    if env and Path(env).is_dir():
        return Path(env)
    candidates: list[Path] = []
    if os.name == "nt":
        for base in (os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
                     os.environ.get("LOCALAPPDATA", ""), os.environ.get("PROGRAMFILES", r"C:\Program Files")):
            if base:
                candidates.append(Path(base) / "Tesseract-OCR" / "tessdata")
    else:
        candidates += [Path("/usr/share/tesseract-ocr/5/tessdata"),
                       Path("/usr/share/tesseract-ocr/4.00/tessdata"),
                       Path("/usr/local/share/tessdata"),
                       Path("/usr/share/tessdata")]
    for cand in candidates:
        if cand.is_dir() and any(cand.glob("*.traineddata")):
            return cand
    return None


def tessdata_dir() -> Path | None:
    """مجلد بيانات OCR العامل: المضمَّن أولًا ثم النظامي."""
    return bundled_tessdata() or system_tessdata()


def available_langs() -> list[str]:
    d = tessdata_dir()
    if not d:
        return []
    return sorted(p.stem for p in d.glob("*.traineddata"))


def missing_langs(required: list[str]) -> list[str]:
    have = set(available_langs())
    miss: list[str] = []
    for req in required:
        for part in req.split("+"):
            if part and part not in have:
                miss.append(part)
    return sorted(set(miss))
