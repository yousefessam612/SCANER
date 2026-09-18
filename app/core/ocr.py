"""تغليف Tesseract عبر tesserocr: كلمات+أسطر بإحداثياتها، سلّم محاولات مُقيَّم.

ملاحظة أساسية (مثبتة اختبارًا): Tesseract يُخرج كلمات الأسطر العربية معكوسة الحروف
وبترتيب بصري (يسار→يمين). إعادة البناء تتم في languages.reorder_visual_to_logical.
"""
from __future__ import annotations

import threading

from .preprocess import binarize, blur
from .languages import reorder_visual_to_logical

try:
    import tesserocr
    from tesserocr import PSM, RIL, PyTessBaseAPI, iterate_level
    _TESSEROCR = True
except Exception:  # pragma: no cover - البيئة بلا tesserocr
    _TESSEROCR = False


def ocr_available() -> bool:
    return _TESSEROCR


class OCRError(RuntimeError):
    pass


_PSM = {
    "block": getattr(PSM, "SINGLE_BLOCK", None) if _TESSEROCR else None,   # 6
    "column": getattr(PSM, "SINGLE_COLUMN", None) if _TESSEROCR else None,  # 4
}
_LOCK = threading.Lock()


class OCREngine:
    """محرك OCR بقالب واحد لكل (tessdata, lang) — آمن للاستخدام من خيط واحد."""

    def __init__(self, tessdata: str, lang: str = "ara+eng"):
        if not _TESSEROCR:
            raise OCRError("tesserocr غير مثبّت: pip install tesserocr")
        self.tessdata = tessdata
        self.lang = lang
        self._api: dict[str, PyTessBaseAPI] = {}

    def _get_api(self, psm_key: str):
        api = self._api.get(psm_key)
        if api is None:
            api = PyTessBaseAPI(path=self.tessdata, lang=self.lang, psm=_PSM[psm_key])
            self._api[psm_key] = api
        return api

    def close(self):
        for api in self._api.values():
            try:
                api.End()
            except Exception:
                pass
        self._api.clear()

    def recognize(self, img, psm_key: str = "block") -> dict:
        """يعيد كلمات/أسطر بإحداثيات بكسل الصورة + ثقة + نص السطور بالترتيب المنطقي."""
        with _LOCK:
            api = self._get_api(psm_key)
            api.SetImage(img)
            api.Recognize()
            it = api.GetIterator()
            words: list[dict] = []
            lines_geo: list[tuple[float, float, float, float]] = []
            if it is not None:
                # صناديق الأسطر أولًا (المكرر يُستهلك بعد المرور عليه مرة واحدة)
                try:
                    for ln in iterate_level(it, RIL.TEXTLINE):
                        lines_geo.append(tuple(ln.BoundingBox(RIL.TEXTLINE)))
                except Exception:
                    lines_geo = []
                it2 = api.GetIterator()
                if it2 is not None:
                    for w in iterate_level(it2, RIL.WORD):
                        try:
                            txt = w.GetUTF8Text(RIL.WORD)
                        except Exception:
                            continue
                        if not txt or not txt.strip():
                            continue
                        try:
                            conf = float(w.Confidence(RIL.WORD))
                        except Exception:
                            conf = 0.0
                        x0, y0, x1, y1 = w.BoundingBox(RIL.WORD)
                        words.append({"text": txt.strip(), "bbox": [x0, y0, x1, y1], "conf": round(conf, 1)})
            if not words:
                return {"words": [], "lines": [], "mean_conf": 0.0}
            return {"words": words, "lines": self._assemble_lines(words, lines_geo),
                    "mean_conf": round(sum(w["conf"] for w in words) / len(words), 1)}

    @staticmethod
    def _assemble_lines(words: list[dict], lines_geo) -> list[dict]:
        """تجميع الكلمات في أسطر: صناديق أسطر Tesseract أولًا، وإلا تجميع هندسي."""
        lines: list[dict] = []
        used = [False] * len(words)
        for (lx0, ly0, lx1, ly1) in lines_geo:
            inside = [w for i, w in enumerate(words)
                      if not used[i] and ly0 - 4 <= (w["bbox"][1] + w["bbox"][3]) / 2 <= ly1 + 4]
            if inside:
                for w in inside:
                    used[words.index(w)] = True
                lines.append(_make_line(inside, [lx0, ly0, lx1, ly1]))
        for i, w in enumerate(words):
            if not used[i]:
                lines.append(_make_line([w], w["bbox"]))
        lines.sort(key=lambda l: l["bbox"][1])
        return lines

    def line_logical_text(self, line: dict) -> str:
        """نص السطر بالترتيب المنطقي (إصلاح الانعكاس العربي)."""
        ws = sorted(line["words"], key=lambda w: w["bbox"][0])  # بصري يسار→يمين
        logical = reorder_visual_to_logical([w["text"] for w in ws])
        return " ".join(logical)


def _make_line(ws: list[dict], bbox) -> dict:
    ws_sorted = sorted(ws, key=lambda w: w["bbox"][0])
    logical = reorder_visual_to_logical([w["text"] for w in ws_sorted])
    return {"bbox": list(bbox), "words": ws_sorted,
            "text_logical": " ".join(logical),
            "mean_conf": round(sum(w["conf"] for w in ws) / max(len(ws), 1), 1)}


def _merge_missing_lines(base: dict, candidates: list[dict], base_bands,
                         base_dpi: int = 300) -> dict:
    """يتبنى أسطرًا من محاولات أخرى تغطي أشرطة حبر أسقطتها المحاولة المختارة.

    candidates: نتائج المحاولات الأخرى (كل واحدة بقائمة أسطر bbox+text).
    base_bands: أشرطة الحبر (y0,y1) ببكسل الصورة الأساسية.
    """
    import copy

    if not base.get("lines") or not base_bands:
        return base
    dpi = None
    merged = copy.deepcopy(base)
    for (by0, by1) in base_bands:
        band_mid = (by0 + by1) / 2.0
        covered = any(l["bbox"][1] - 8 <= band_mid <= l["bbox"][3] + 8 for l in merged["lines"])
        if covered:
            continue
        # ابحث عن سطر بديل يغطي هذا الشريط (بأعلى كلمات/ثقة)
        best_line, best_src = None, None
        for cand in candidates:
            for ln in cand.get("lines", []):
                if ln["bbox"][1] - 8 <= band_mid <= ln["bbox"][3] + 8:
                    key = (len(ln.get("words", [])), ln.get("mean_conf", 0))
                    if best_line is None or key > (len(best_line.get("words", [])), best_line.get("mean_conf", 0)):
                        best_line, best_src = ln, cand
        if best_line and len(best_line.get("words", [])) >= 2 and best_line.get("mean_conf", 0) >= 55:
            adopted = dict(best_line)
            adopted["words"] = [dict(w) for w in best_line.get("words", [])]
            merged["lines"].append(adopted)
            merged["words"].extend(
                {"text": w["text"], "bbox": w["bbox"], "conf": w.get("conf", best_line.get("mean_conf", 0))}
                for w in adopted["words"]
                if not any(abs(w["bbox"][0] - m["bbox"][0]) < 3 and abs(w["bbox"][1] - m["bbox"][1]) < 3
                           for m in merged["words"]))
            if best_src and best_src.get("mean_conf", 0) > merged.get("mean_conf", 0):
                pass  # نحافظ على ثقة الأساس؛ الأسطر المتبناة تحمل ثقتها الخاصة
    merged["lines"].sort(key=lambda l: l["bbox"][1])
    merged["words"].sort(key=lambda w: (w["bbox"][1], w["bbox"][0]))
    merged["merged_from_alternatives"] = True
    return merged


def run_ladder(engine: OCREngine, render, base_img, metrics, max_attempts: int = 4) -> dict:
    """سلّم محاولات حتمي مرتب من الأرخص/الأرجح + دمج الأسطر المفقودة من محاولات أخرى.

    render(dpi) → PIL.Image أعيد رسمها من الـPDF (تُستخدم لمحاولة الدقة الأعلى).
    """
    from .pagequality import assess_ocr, count_ink_bands

    attempts: list[dict] = []
    results: list[dict] = []  # كل نتائج المحاولات (للدمج لاحقًا)
    best: dict | None = None
    best_bands = count_ink_bands(base_img)

    def consider(res: dict, tag: str) -> dict | None:
        # تطبيع فوري: كل المحاولات تُحوَّل إلى إحداثيات صورة الأساس (dpi0)
        if tag == "rerender_400dpi" and dpi0 != 400:
            k = dpi0 / 400.0
            for w in res["words"]:
                w["bbox"] = [c * k for c in w["bbox"]]
            for ln in res["lines"]:
                ln["bbox"] = [c * k for c in ln["bbox"]]
                for w in ln.get("words", []):
                    w["bbox"] = [c * k for c in w["bbox"]]
        a = {"attempt": tag,
             **assess_ocr(res["words"], res["mean_conf"], metrics,
                          n_lines=len(res["lines"]), n_bands=len(best_bands))}
        attempts.append(a)
        res = dict(res)
        res["dpi"] = dpi0
        results.append(res)
        if a["status"] == "ok":
            return a
        if best is None or a["score"] > best["score"]:
            return a
        return best

    current = base_img
    dpi0 = metrics.get("dpi", 300)
    steps = [("block", current), ("blur", blur(current, 1.5)), ("column", current)]
    if dpi0 < 380:
        try:
            steps.append(("rerender_400dpi", render(400)))
        except Exception:
            pass
    steps.append(("binarize", binarize(current)))

    chosen = None
    for tag, img in steps[: max(1, max_attempts)]:
        try:
            res = engine.recognize(img, psm_key="block" if not tag.startswith(("column",)) else "column")
        except Exception as e:  # صفحة تعطّل OCR لا تُسقط الكتاب
            attempts.append({"attempt": tag, "status": "fail", "reasons": [f"error:{e}"], "score": 0})
            continue
        prev_score = best["score"] if best else float("-inf")
        best = consider(res, tag)
        # الأساس = أفضل محاولة فعلًا (بالأعلى درجة)، لا آخر محاولة
        if best["score"] > prev_score or chosen is None:
            chosen = res
        if best["status"] == "ok" and "missing_lines" not in best.get("reasons", []):
            break
    if chosen is None:
        chosen = {"words": [], "lines": [], "mean_conf": 0.0}
        return {"result": chosen, "attempts": attempts,
                "assessment": best or {"status": "fail", "reasons": ["no_attempt"], "score": 0}}

    # دمج الأسطر المفقودة: أشرطة حبر بلا سطر في الأساس تُتبنى من أفضل بديل
    final = _merge_missing_lines(chosen, results, best_bands, base_dpi=dpi0)
    assessment = best or {"status": "fail", "reasons": ["no_attempt"], "score": 0}
    if final is not chosen:
        # أعد التقييم بعد الدمج: إن اكتملت التغطية ارفع الحكم
        recheck = assess_ocr(final["words"], final["mean_conf"], metrics,
                             n_lines=len(final["lines"]), n_bands=len(best_bands))
        reasons = [r for r in recheck["reasons"] if r != "missing_lines"]
        if "missing_lines" in assessment.get("reasons", []) and not reasons:
            assessment = dict(assessment)
            assessment["reasons"] = reasons
            if not reasons:
                assessment["status"] = "ok"
                assessment["score"] = round(assessment.get("score", 0) + 10, 1)
                assessment["merged"] = True
    return {"result": final, "attempts": attempts, "assessment": assessment}
