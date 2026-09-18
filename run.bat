@echo off
rem ============================================================
rem  اقرأ / Iqra — تشغيل سريع على ويندوز
rem  الاستخدام:
rem     run.bat selftest
rem     run.bat convert كتاب.pdf -f docx,pdf -o المخرجات
rem     run.bat resume "كتاب.iqra_project"
rem     run.bat batch مجلد_الكتب
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"

rem أول تشغيل: تجهيز البيئة تلقائيًا (يتطلب Python 3.11 أو 3.12 64-bit)
if not exist ".venv\Scripts\python.exe" (
    echo أول تشغيل: جارٍ تجهيز البيئة وتثبيت الاعتماديات...
    python -m venv .venv
    if errorlevel 1 (
        echo [خطأ] Python غير مثبت — نزّل Python 3.11/3.12 من python.org
        pause
        exit /b 1
    )
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [خطأ] فشل تثبيت الاعتماديات — راجع رسالة الخطأ أعلاه
        pause
        exit /b 1
    )
    echo.
    echo ✓ البيئة جاهزة — فحص ذاتي:
    .venv\Scripts\python -m app selftest
    echo.
)

if "%1"=="" (
    rem بدون معاملات: الواجهة الرسومية
    if exist ".venv\Scripts\pythonw.exe" (
        start "" ".venv\Scripts\pythonw.exe" -m app
    ) else (
        .venv\Scripts\python -m app
    )
    goto :eof
)
.venv\Scripts\python -m app %*
