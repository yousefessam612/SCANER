# مكتبات Qt الوهمية للتشغيل بلا شاشة (بيئات CI فقط)

بيئات لينكس المصغّرة (حاويات اختبار) تفتقد `libGL/libEGL/libxkbcommon/libdbus`.
هذه مكتبات قِيَم فارغة (stub) تسمح بتحميل PySide6 في وضع `QT_QPA_PLATFORM=offscreen`
لأغراض الاختبار فقط — لا تُستخدم في الإنتاج ولا في حزم التوزيع.

الاستخدام:
```bash
LD_LIBRARY_PATH=$PWD/tools/headless-qt-stubs QT_QPA_PLATFORM=offscreen python -m pytest tests
```

البناء الأصلي (إن أردت إعادة توليدها): سكربت `tools/headless-qt-stubs/build_stubs.sh`.
