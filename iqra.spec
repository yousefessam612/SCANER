# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: يبني Iqra (واجهة رسومية onedir) + IqraCLI (سطر أوامر onefile).
# بيانات OCR + خط Amiri (لازم لطبقة البحث في rawpdf) تُضمَّن داخل الحزمة.
# البناء:  pyinstaller iqra.spec --noconfirm   (على ويندوز 64-bit)
# ثم المثبت:  ISCC.exe installer.iss

import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = [
    "PySide6.QtSvg",
    "tesserocr",
] + collect_submodules("docx") + collect_submodules("psutil")

a = Analysis(
    ["entry.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("runtime/tessdata", "runtime/tessdata"),   # بيانات OCR العربية/الإنجليزية
        ("runtime/fonts", "runtime/fonts"),          # خط Amiri لطبقة النص القابلة للبحث
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    excludes=["tkinter", "matplotlib", "scipy", "pandas", "IPython", "notebook", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- التطبيق الرئيسي (واجهة رسومية، onedir) ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Iqra",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon="assets/icon.ico",
    version="version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="Iqra",
)

# --- أداة سطر الأوامر (ملف تنفيذي واحد) ---
exe_cli = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="IqraCLI",
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon="assets/icon.ico",
    version="version_info.txt",
)
