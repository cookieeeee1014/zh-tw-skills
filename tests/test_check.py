"""zh-tw-humanizer 檢查器行為測試。"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "zh-tw-humanizer" / "scripts" / "check.py"
HERE = Path(__file__).resolve().parent
SAMPLE_AI = HERE / "sample_ai.txt"
SAMPLE_HUMAN = HERE / "sample_human.txt"

sys.path.insert(0, str(SCRIPT.parent))
from check import MOE, metrics, rhythm, scan  # noqa: E402


# ── 官方對照表（教育部）─────────────────────────────────────

def test_moe_table_is_loaded():
    assert len(MOE) > 500, f"官方對照表只載入 {len(MOE)} 條"


def test_moe_maps_life_vocabulary():
    """這些是官方表獨有的生活詞，我原本的 IT 詞表沒有。"""
    assert MOE.get("互聯網") == "網際網路"
    assert MOE.get("創可貼") == "OK繃"
    assert MOE.get("吊瓶") == "點滴"


def test_moe_skips_same_form_terms():
    """兩岸同形的詞不能列入，否則會把正確用法判成錯。"""
    assert "鐵粉" not in MOE


def test_single_char_moe_terms_are_downgraded():
    """單字歧義（「米」可能是長度也可能是米飯）不能一票否決。"""
    findings = scan("我吃了米飯，配玉米濃湯。")
    kinds = {f["kind"] for f in findings}
    assert "單字待確認" in kinds
    assert "官方對照" not in kinds, "單字不該被當成確定錯誤"


def test_multi_char_moe_terms_are_blocking():
    findings = scan("互聯網上買的創可貼。")
    kinds = {f["kind"] for f in findings}
    assert "官方對照" in kinds
    assert "單字待確認" not in kinds


# ── L1：地區用詞 ─────────────────────────────────────────────

def test_a_level_vocabulary_is_flagged():
    findings = scan("這份信息要傳到服務器，賬號在內存裡。")
    a_words = {f["found"] for f in findings if f["kind"].startswith("A 級")}
    assert a_words == {"信息", "服務器", "賬號", "內存"}


def test_a_level_suggests_correct_taiwan_terms():
    findings = scan("信息")
    assert findings[0]["suggest"] == "資訊"


def test_b_level_is_flagged_but_separate():
    """B 級要跟 A 級分開，因為 B 級有合法語境。"""
    findings = scan("這個數據的質量很好。")
    kinds = {f["kind"] for f in findings}
    assert "B 級用詞" in kinds
    assert not any(k.startswith("A 級") for k in kinds)


def test_correct_taiwan_text_has_no_vocab_hits():
    findings = scan("這份資訊要傳到伺服器，帳號在記憶體裡。")
    assert findings == []


# ── L2：大陸構詞法 ───────────────────────────────────────────

def test_grammar_patterns():
    findings = scan("我們進行討論，並作出決定，對於團隊而言很重要。")
    groups = [f["group"] for f in findings]
    assert groups.count("大陸構詞") == 3


# ── AI 腔 ──────────────────────────────────────────────────

def test_template_phrases():
    findings = scan("總而言之，希望以上內容對你有幫助。")
    kinds = [f["kind"] for f in findings if f["group"] == "AI 腔"]
    assert kinds.count("空洞收尾") == 2


def test_multiline_three_part():
    findings = scan("首先，我們要看資料。\n其次，我們要分析。\n最後得出結論。")
    assert any("三段式" in f["kind"] for f in findings)


def test_abstract_nouns():
    findings = scan("這個方案可以賦能團隊，形成閉環。")
    found = {f["found"] for f in findings}
    assert {"賦能", "閉環"} <= found


# ── 否定平行（維基：單獨出現就是強信號）────────────────────

def test_negative_parallelism():
    findings = scan("這不是工具的問題，是流程的問題。")
    kinds = [f["kind"] for f in findings]
    assert "否定平行" in kinds


def test_negative_parallelism_not_only():
    findings = scan("這個做法不只省時間，更是省成本。")
    kinds = [f["kind"] for f in findings]
    assert "否定平行" in kinds


def test_negative_parallelism_rather_than():
    findings = scan("與其說這是技術問題，不如說是溝通問題。")
    kinds = [f["kind"] for f in findings]
    assert "否定平行" in kinds


# ── 豁免：討論而非使用 ────────────────────────────────────

def test_quoted_term_is_not_flagged():
    """引號是「提到」的信號，不是「使用」。"""
    findings = scan("OpenCC 把「信息」轉成繁體，結果還是「信息」。")
    assert findings == [], f"引號內的詞不該判錯：{findings}"


def test_backtick_term_is_not_flagged():
    findings = scan("把 `信息` 改成 `資訊` 就好。")
    assert findings == [], f"反引號內的詞不該判錯：{findings}"


def test_mapping_line_is_skipped():
    """規則對照行是在講規則，不是在使用。"""
    findings = scan("信息→資訊、軟件→軟體、網絡→網路")
    assert findings == [], f"對照行不該判錯：{findings}"


def test_blockquote_is_skipped():
    """引用別人的話不代表作者這樣寫。"""
    findings = scan("> 這份信息需要優化，質量很重要。")
    assert findings == [], f"引用塊不該判錯：{findings}"


def test_code_fence_is_skipped():
    findings = scan("```\n這份信息需要優化\n```\n")
    assert findings == [], f"程式碼區塊不該判錯：{findings}"


def test_real_usage_still_flagged():
    """豁免不能把真問題也豁免掉。"""
    findings = scan("這份信息需要優化，質量很重要。")
    a_words = {f["found"] for f in findings if f["kind"].startswith("A 級")}
    assert "信息" in a_words, "沒在引號裡的實際用詞仍要抓"


# ── 節奏指標（核心）─────────────────────────────────────────

def test_rhythm_separates_ai_from_human():
    """關鍵指標：AI 平滑，人寫有摩擦。"""
    ai_r, _ = rhythm(SAMPLE_AI.read_text(encoding="utf-8"))
    human_r, _ = rhythm(SAMPLE_HUMAN.read_text(encoding="utf-8"))
    assert ai_r is not None and human_r is not None
    assert ai_r < 0.35, f"AI 文本節奏應平滑，實測 {ai_r}"
    assert human_r > 0.5, f"人寫文本應有摩擦，實測 {human_r}"
    assert human_r > ai_r * 2, f"差距應超過兩倍：{human_r} vs {ai_r}"


def test_rhythm_needs_enough_sentences():
    r, n = rhythm("只有一句。")
    assert r is None and n < 3


def test_uniform_sentences_score_low():
    """句長一致 → 低分。"""
    text = "這是一個測試句子。這是一個測試句子。這是一個測試句子。這是一個測試句子。"
    r, _ = rhythm(text)
    assert r < 0.1


def test_varied_sentences_score_high():
    """長短交錯 → 高分。"""
    text = "短。這是中等長度的一個句子。這是一個非常非常非常長的句子用來測試節奏變化。又短。"
    r, _ = rhythm(text)
    assert r > 0.5


# ── 完整體檢 ───────────────────────────────────────────────

def test_metrics_on_ai_sample():
    m = metrics(SAMPLE_AI.read_text(encoding="utf-8"))
    assert m["rhythm_verdict"] == "平滑（AI 傾向）"
    assert m["abstract_per_kilo"] > 0


def test_metrics_on_human_sample():
    m = metrics(SAMPLE_HUMAN.read_text(encoding="utf-8"))
    assert m["rhythm_verdict"] == "有摩擦（像人寫的）"
    assert m["abstract_per_kilo"] == 0.0


def test_clean_text_has_zero_findings():
    """關鍵：正確的台灣繁體中文不能誤報。"""
    text = SAMPLE_HUMAN.read_text(encoding="utf-8")
    assert scan(text) == [], f"誤報了：{scan(text)}"


# ── CLI ────────────────────────────────────────────────────

def test_cli_json_output():
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", str(SAMPLE_AI)],
        capture_output=True, text=True, encoding="utf-8",
    )
    data = json.loads(out.stdout)
    assert data["summary"]["region_a"] >= 1
    assert data["metrics"]["rhythm"] < 0.35
    assert out.returncode == 1


def test_cli_clean_returns_zero():
    fd, path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(SAMPLE_HUMAN.read_text(encoding="utf-8"))
        out = subprocess.run(
            [sys.executable, str(SCRIPT), path],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert out.returncode == 0, out.stdout
        assert "A 級 0" in out.stdout
    finally:
        os.unlink(path)
