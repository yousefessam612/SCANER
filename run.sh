#!/usr/bin/env bash
# ============================================================
#  اقرأ / Iqra — تشغيل سريع على لينكس/ماك
#  الاستخدام:
#     ./run.sh selftest
#     ./run.sh convert كتاب.pdf -f docx,pdf -o المخرجات
# ============================================================
set -e
cd "$(dirname "$0")"

# أول تشغيل: تجهيز البيئة تلقائيًا
if [ ! -x ".venv/bin/python" ]; then
    echo "أول تشغيل: جارٍ تجهيز البيئة وتثبيت الاعتماديات..."
    python3 -m venv .venv
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt
    echo "✓ البيئة جاهزة — فحص ذاتي:"
    .venv/bin/python -m app selftest
    echo
fi

if [ $# -eq 0 ]; then
    echo "الاستخدام: ./run.sh convert كتاب.pdf -f docx,pdf -o المخرجات"
    exit 0
fi

exec .venv/bin/python -m app "$@"
