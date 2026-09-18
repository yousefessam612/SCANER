# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: builds Iqra (windowed GUI) + IqraCLI (console).
# The tesseract runtime + tessdata ship beside the exe via the installer,
# NOT inside it (keeps the exe small and OCR data upgradable).

import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = [
    "PySide6.QtSvg",  # high-DPI icon rendering
] + collect_submodules("docx") + collect_submodules("psutil")

a = Analysis(
    ["entry.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas", "IPython"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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

# --- console CLI build (same code, console subsystem)
exe_cli = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="IqraCLI",
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon="assets/icon.ico",
    version="version_info.txt",
)

coll_cli = COLLECT(
    exe_cli,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="IqraCLI",
)
