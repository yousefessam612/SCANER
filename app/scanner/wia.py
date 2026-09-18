"""الماسح الضوئي عبر WIA COM باستخدام PowerShell — بلا أي اعتمادات إضافية.

يعمل على ويندوز فقط (WIA غير موجود على الأنظمة الأخرى):
- تعداد الأجهزة المثبتة
- مسح صامت بجهاز محدد ودقة معينة
- مسح عبر معالج ويندوز (يدعم المغذاة ADF)
"""
from __future__ import annotations

import os
import subprocess


class ScannerError(RuntimeError):
    pass


def available() -> bool:
    """هل نحن على ويندوز (حيث WIA متوفر)؟"""
    return os.name == "nt"


def _ps(script: str, timeout: int = 180) -> str:
    if not available():
        raise ScannerError("الماسح الضوئي متوفر على ويندوز فقط")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired as e:
        raise ScannerError(f"انتهت مهلة الماسح ({timeout} ثانية)") from e
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "خطأ غير معروف").strip()
        raise ScannerError(f"فشل الماسح: {msg[:400]}")
    return r.stdout


def list_scanners() -> list[dict]:
    """الأجهزة المثبتة: [{id, name, type}]."""
    script = r"""
$ErrorActionPreference = 'Stop'
$dm = New-Object -ComObject WIA.DeviceManager
foreach ($d in $dm.DeviceInfos) {
  $name = ''
  foreach ($p in $d.Properties) { if ($p.Name -eq 'Name') { $name = $p.Value } }
  $t = ''
  foreach ($p in $d.Properties) { if ($p.Name -eq 'Type') { $t = $p.Value } }
  Write-Output ("{0}|{1}|{2}" -f $d.DeviceID, $t, $name)
}
"""
    out = []
    for line in _ps(script).splitlines():
        line = line.strip()
        if "|" in line:
            did, typ, name = (line.split("|", 2) + ["", ""])[:3]
            out.append({"id": did, "type": typ, "name": name or "ماسح ضوئي"})
    return out


def scan_page(out_path: str, device_id: str | None = None, dpi: int = 300,
              wizard: bool = False) -> str:
    """مسح صفحة واحدة إلى ملف صورة (PNG) ويعيد المسار.

    wizard=True يفتح معالج المسح في ويندوز (يسمح باختيار المغذاة/الأسطح).
    """
    out_path = os.path.abspath(out_path)
    ps_dev = ""
    if device_id and not wizard:
        ps_dev = f"$dev = $null; foreach ($d in $dm.DeviceInfos) {{ if ($d.DeviceID -eq '{device_id}') {{ $dev = $d.Connect() }} }}\nif (-not $dev) {{ throw 'الجهاز المحدد غير موجود' }}"
    else:
        ps_dev = "$dev = $dm.DeviceInfos.Item(1).Connect()"
    script = r"""
$ErrorActionPreference = 'Stop'
$dm = New-Object -ComObject WIA.DeviceManager
__DEV__
$item = $dev.Items.Item(1)
foreach ($p in $item.Properties) {
  if ($p.Name -eq 'Horizontal Resolution' -or $p.Name -eq 'Vertical Resolution') {
    try { $p.Value = __DPI__ } catch {}
  }
}
if (-not '__WIZARD__') {
  $img = $item.Transfer('{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}')
  $img.SaveFile('__OUT__')
  Write-Output '__OUT__'
} else {
  $dlg = New-Object -ComObject WIA.CommonDialog
  $img = $dlg.ShowAcquireImage()
  if ($img) { $img.SaveFile('__OUT__'); Write-Output '__OUT__' }
  else { throw 'أُلغي المسح' }
}
""".replace("__DEV__", ps_dev).replace("__DPI__", str(int(dpi))) \
       .replace("__WIZARD__", "1" if wizard else "0").replace("__OUT__", out_path.replace("'", "''"))
    res = _ps(script, timeout=300).strip()
    if not res or not os.path.isfile(out_path):
        raise ScannerError("لم يُنتج الماسح أي صورة")
    return out_path


def images_to_pdf(image_paths: list[str], out_pdf: str) -> str:
    """تجميع صور ممسوحة في PDF واحد (عبر PyMuPDF)."""
    import pymupdf

    doc = pymupdf.open()
    for p in image_paths:
        img = pymupdf.Pixmap(p)
        page = doc.new_page(width=img.width * 72.0 / 200.0, height=img.height * 72.0 / 200.0)
        page.insert_image(page.rect, filename=p)
        img = None
    doc.save(out_pdf)
    doc.close()
    return out_pdf
