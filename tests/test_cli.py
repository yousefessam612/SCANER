"""اختبارات واجهة سطر الأوامر: تشغيل حقيقي end-to-end."""
import subprocess
import sys

from conftest import make_arabic_pdf

PY = sys.executable


def run_cli(args, cwd=None):
    return subprocess.run([PY, "-m", "app"] + args, capture_output=True, text=True,
                          cwd=cwd or str(__import__("pathlib").Path(__file__).resolve().parent.parent),
                          timeout=300)


def test_convert_command(tmp_path):
    pdf = make_arabic_pdf(tmp_path / "doc.pdf", ["جملة عربية لاختبار سطر الأوامر مع رقم 25"])
    r = run_cli(["convert", str(pdf), "-f", "docx,txt", "-o", str(tmp_path / "out")])
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "out/doc.iqra_project/output/doc.docx").is_file()
    assert (tmp_path / "out/doc.iqra_project/output/doc.txt").is_file()


def test_selftest_command():
    r = run_cli(["selftest"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "سليم" in r.stdout


def test_resume_command(tmp_path):
    from app.core.engine import convert_pdf
    pdf = make_arabic_pdf(tmp_path / "res.pdf", ["صفحة أولى", "صفحة ثانية"])
    # أنشئ مشروعًا ملغيًا بعد صفحة واحدة
    calls = {"n": 0}

    def cancel_once():
        calls["n"] += 1
        return calls["n"] >= 2

    out = convert_pdf(str(pdf), lang="ara+eng", formats=["txt"], project=tmp_path / "p",
                      should_cancel=cancel_once)
    assert out["status"] == "cancelled"
    r = run_cli(["resume", str(tmp_path / "p"), "-f", "txt"])
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "p/output/res.txt").is_file()
