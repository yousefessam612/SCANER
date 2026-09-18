#!/usr/bin/env bash
# يعيد بناء مكتبات الـstub من رموز مكتبات Qt المثبتة في البيئة
set -e
QTLIB="${1:-.venv/lib/python3.11/site-packages/PySide6/Qt/lib}"
OUT="$(dirname "$0")"
nm -D --undefined-only "$QTLIB"/libQt6*.so.6 "$QTLIB"/../plugins/platforms/libqoffscreen.so 2>/dev/null \
  | awk '{print $NF}' | sort -u > /tmp/undef.txt
gen() { local re="$1" lib="$2"
  grep -E "^$re" /tmp/undef.txt | sort -u > /tmp/sv.txt
  sed 's/@.*//' /tmp/sv.txt | sort -u > /tmp/all.txt
  grep -o '@[^ ]*' /tmp/sv.txt | sed 's/@//' | sort -u > /tmp/vers.txt || true
  { echo "/* stub $lib */"; while read -r s; do echo "void $s(void) {}"; done < /tmp/all.txt; } > /tmp/$lib.c
  EXTRA=""
  if [ -s /tmp/vers.txt ]; then
    { while read -r v; do
        echo "$v {"; echo "  global:"
        grep "@$v\$" /tmp/sv.txt | sed "s/@.*//;s/^/    /;s/$/;" | sort -u
        echo "};"
      done < /tmp/vers.txt; } > /tmp/$lib.map
    EXTRA="-Wl,--version-script=/tmp/$lib.map"
  fi
  gcc -shared -fPIC -o "$OUT/$lib" /tmp/$lib.c $EXTRA
  echo "✓ $lib"
}
gen '^(gl|glX|GL)' libGL.so.1
gen '^egl' libEGL.so.1
gen '^xkb' libxkbcommon.so.0
gen '^dbus' libdbus-1.so.3
