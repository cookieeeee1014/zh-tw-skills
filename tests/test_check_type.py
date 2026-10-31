"""zh-tw-typography 檢查器行為測試。"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills" / "zh-tw-typography" / "scripts" / "check_type.py"
)

sys.path.insert(0, str(SCRIPT.parent))
from check_type import scan  # noqa: E402

GOOD = """這是正確的句子，用全形標點。
我們走了很遠……然後停下來——真的很累。
他說「沒問題」，我信了。
用 Python 寫的程式（中文括號也對）。
"""

BAD = """這是錯的,用了半形逗號.
我們走了很遠...然後停下來--真的很累.
他說"沒問題",我信了.
"""


def kinds(findings):
    return {f["kind"] for f in findings}


def test_halfwidth_comma_in_chinese():
    findings = scan("今天很好,明天也是。")
    assert "半形逗號" in kinds(findings)


def test_halfwidth_period_in_chinese():
    findings = scan("這是句子.")
    assert "半形句號" in kinds(findings)


def test_ellipsis():
    findings = scan("我還沒想好...再等等。")
    assert "省略號" in kinds(findings)
    hit = [f for f in findings if f["kind"] == "省略號"][0]
    assert hit["suggest"] == "……"


def test_dash():
    findings = scan("他走了--沒有回頭。")
    assert "破折號" in kinds(findings)


def test_straight_quotes():
    findings = scan('他說"沒問題"，我信了。')
    assert "直引號" in kinds(findings)


def test_halfwidth_parens_around_chinese():
    findings = scan("這件事(很重要)要知道。")
    assert "半形括號包中文" in kinds(findings)


def test_good_text_is_clean():
    """正確的台灣排版不能誤報。"""
    findings = scan(GOOD)
    errors = [f for f in findings if f["level"] == "錯誤"]
    assert errors == [], f"誤報了：{errors}"


def test_bad_sample_hits_multiple():
    findings = scan(BAD)
    got = kinds(findings)
    assert {"半形逗號", "省略號", "破折號", "直引號"} <= got


def test_code_fence_is_skipped():
    findings = scan("```\n這是錯的,半形逗號.\n```\n")
    assert findings == [], f"程式碼區塊不該檢查：{findings}"


def test_url_is_skipped():
    """URL 裡的點和問號不是標點錯誤。"""
    findings = scan("參考 https://example.com/a?b=1 這裡。")
    assert findings == [], f"URL 不該誤判：{findings}"


def test_inline_code_is_skipped():
    findings = scan("執行 `a,b.c` 就好。")
    assert findings == [], f"行內程式碼不該誤判：{findings}"


def test_html_attribute_quotes_are_skipped():
    """HTML 屬性的引號不是中文引號。"""
    findings = scan('<div align="center">\n內容\n</div>\n')
    assert findings == [], f"HTML 標籤不該誤判：{findings}"


def test_english_text_not_flagged():
    """英文句子裡的半形標點是正確的。"""
    findings = scan("This is fine, and so is this.\n")
    errors = [f for f in findings if f["level"] == "錯誤"]
    assert errors == [], f"英文段落誤報：{errors}"


def test_cli_json():
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(BAD)
        out = subprocess.run(
            [sys.executable, str(SCRIPT), "--json", path],
            capture_output=True, text=True, encoding="utf-8",
        )
        data = json.loads(out.stdout)
        assert data["errors"] >= 3
        assert out.returncode == 1
    finally:
        os.unlink(path)


def test_cli_clean_returns_zero():
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(GOOD)
        out = subprocess.run(
            [sys.executable, str(SCRIPT), path],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert out.returncode == 0, out.stdout
    finally:
        os.unlink(path)
