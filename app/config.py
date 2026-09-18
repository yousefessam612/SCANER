"""إعدادات التطبيق — ملف JSON في مجلد بيانات المستخدم، لا يفشل التحميل أبدًا."""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS = {
    "lang": "ara+eng",        # ara | eng | ara+eng
    "quality": "balanced",    # fast | balanced | high  (DPI 200/300/400)
    "formats": ["docx"],      # docx,txt,html,pdf
    "out_dir": "",
    "trust_text_layer": True,   # الثقة بطبقة نص PDF بعد الفحص
    "ocr_max_attempts": 4,
    "page_breaks": False,       # فاصل صفحة بين صفحات PDF في DOCX
    "keep_debug": False,
    "ui_lang": "ar",
}

_QUALITY_DPI = {"fast": 200, "balanced": 300, "high": 400}


def settings_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "Iqra" / "settings.json"
    return Path.home() / ".config" / "Iqra" / "settings.json"


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for k in DEFAULTS:
                if k in data:
                    cfg[k] = data[k]
    except Exception:
        pass
    return cfg


def save(cfg: dict) -> None:
    p = settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def dpi_for(quality: str) -> int:
    return _QUALITY_DPI.get(quality, 300)
