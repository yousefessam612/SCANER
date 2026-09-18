"""تقرير الجودة الحتمي — يُكتب في مجلد المشروع ولا يدخل مستندات المستخدم أبدًا."""
from __future__ import annotations

import json
import time


def write_report(project_dir, pdf_name: str, pages: list[dict], extra: dict | None = None):
    """pages: [{page, status, source, conf, words, attempts:[{attempt,status,reasons}], reason}]"""
    project_dir.mkdir(parents=True, exist_ok=True)
    ok = sum(1 for p in pages if p.get("status") == "ok")
    suspect = [p for p in pages if p.get("status") == "suspect"]
    failed = [p for p in pages if p.get("status") == "fail"]

    report = {
        "pdf": pdf_name,
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {"ok": ok, "suspect": len(suspect), "failed": len(failed), "total": len(pages)},
        "pages": pages,
        **(extra or {}),
    }
    (project_dir / "quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"تقرير الجودة — {pdf_name}",
        f"التاريخ: {report['generated']}",
        f"الإجمالي: {len(pages)} صفحة — سليمة: {ok} — تحتاج مراجعة: {len(suspect)} — فاشلة: {len(failed)}",
        "",
    ]
    if suspect:
        lines.append("## صفحات تحتاج مراجعة يدوية")
        for p in suspect:
            lines.append(f"- صفحة {p['page'] + 1}: {', '.join(p.get('reasons', []))} (ثقة {p.get('conf', 0)}%)")
        lines.append("")
    if failed:
        lines.append("## صفحات فاشلة")
        for p in failed:
            lines.append(f"- صفحة {p['page'] + 1}: {', '.join(p.get('reasons', ['فشل غير معروف']))}")
        lines.append("")
    if not suspect and not failed:
        lines.append("كل الصفحات سليمة. ✓")
    (project_dir / "quality_report.txt").write_text("\n".join(lines), encoding="utf-8-sig")
    return report
