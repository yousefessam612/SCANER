@echo off
rem ============================================================
rem  اقرأ / Iqra — خط إنتاج بناء ويندوز الكامل
rem  المتطلبات (مرة واحدة):
rem    1) Python 3.11/3.12 (64-bit) من python.org
rem    2) Inno Setup 6 من jrsoftware.org (اختياري — للمثبت)
rem  الاستخدام:  انقر build_windows.bat  أو شغّله من موجه الأوامر
rem  النواتج:
rem    dist\Iqra\Iqra.exe                 (التطبيق)
rem    dist\IqraCLI.exe                   (سطر الأوامر)
rem    installer_output\Iqra-Setup-*.exe  (المثبت إن وُجد Inno Setup)
rem ============================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo [1/5] تجهيز البيئة وتثبيت الاعتماديات...
if not exist ".venv\Scripts\python.exe" python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install PyMuPDF Pillow numpy python-docx psutil pytest tesserocr PySide6-Essentials pyinstaller
if errorlevel 1 goto :fail

echo [2/5] الفحص الذاتي (OCR حقيقي + كل الكُتّاب + بحث عربي)...
.venv\Scripts\python -m app selftest
if errorlevel 1 goto :fail

echo [3/5] الاختبارات المؤتمتة...
set QT_QPA_PLATFORM=offscreen
.venv\Scripts\python -m pytest tests -q
if errorlevel 1 goto :fail

echo [4/5] التجميع بـ PyInstaller (Iqra + IqraCLI)...
.venv\Scripts\python -m PyInstaller iqra.spec --noconfirm
if errorlevel 1 goto :fail

echo [5/5] بناء المثبت بـ Inno Setup...
where iscc >nul 2>nul
if %errorlevel%==0 (
    iscc installer.iss
    if errorlevel 1 goto :fail
    echo ✓ المثبت: installer_output\Iqra-Setup-1.1.0.exe
) else (
    echo (تخطي المثبت: Inno Setup غير مثبت — الملفات التنفيذية جاهزة في dist\)
)

echo.
echo ✓ اكتمل البناء بنجاح:
echo    dist\Iqra\Iqra.exe
echo    dist\IqraCLI.exe
pause
exit /b 0

:fail
echo.
echo [خطأ] فشل البناء — راجع رسالة الخطأ أعلاه
pause
exit /b 1
