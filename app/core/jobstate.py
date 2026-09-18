"""حالة المشروع: حفظ ذرّي بعد كل صفحة → استئناف حتمي بلا فقد عمل."""
from __future__ import annotations

import json
import os
from pathlib import Path


def project_dir_for(pdf_path, out_dir=None) -> Path:
    pdf = Path(pdf_path)
    base = Path(out_dir) if out_dir else pdf.parent
    return base / (pdf.stem + ".iqra_project")


class JobState:
    def __init__(self, pdir: Path):
        self.pdir = Path(pdir)
        self.pages_dir = self.pdir / "pages"
        self.state_file = self.pdir / "state.json"

    def load(self) -> dict:
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def init(self, pdf_path: str, total: int, settings_fp: str) -> dict:
        st = self.load()
        if not st or st.get("settings_fp") != settings_fp or st.get("pdf") != str(pdf_path):
            st = {"pdf": str(pdf_path), "total": total, "next_page": 0, "settings_fp": settings_fp}
        else:
            st["total"] = total
        self._save(st)
        return st

    def ensure_dirs(self):
        self.pages_dir.mkdir(parents=True, exist_ok=True)

    def page_path(self, i: int) -> Path:
        return self.pages_dir / f"page_{i:05d}.json"

    def save_page(self, i: int, data: dict, state: dict):
        self.ensure_dirs()
        tmp = self.page_path(i).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.page_path(i))
        state["next_page"] = i + 1
        self._save(state)

    def _save(self, state: dict):
        self.ensure_dirs()
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.state_file)

    def load_page(self, i: int) -> dict | None:
        try:
            return json.loads(self.page_path(i).read_text(encoding="utf-8"))
        except Exception:
            return None
