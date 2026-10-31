#!/usr/bin/env python3
"""繁體中文 AI 腔調與大陸用詞檢查器。

兩個獨立的評分：
  1. 地區用詞（A/B 級，A 級一票否決）
  2. AI 腔（節奏、抽象詞、模糊限定、模板句）

只用標準函式庫。

用法：
    python check.py 檔案.txt
    python check.py --stdin
    python check.py --json 檔案.txt
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ── 官方對照表：教育部《國語辭典簡編本》兩岸常用詞語對照表 ──────────
_MOE_PATH = Path(__file__).resolve().parents[3] / "tools" / "moe_cross_strait.json"


def load_moe():
    """回傳 {大陸詞: 臺灣詞}。

    只收兩邊說法不同的詞——同形的（如「鐵粉」兩岸都說）不列入，
    否則會把正確的臺灣用法判成錯誤。
    """
    if not _MOE_PATH.exists():
        return {}
    data = json.loads(_MOE_PATH.read_text(encoding="utf-8"))
    mapping = {}
    for entry in data.get("entries", []):
        tw = entry.get("tw", "").strip()
        if not tw:
            continue
        for cn in entry.get("cn", []):
            cn = cn.strip()
            if cn and cn != tw:
                mapping.setdefault(cn, tw)
    return mapping


MOE = load_moe()
# 長詞優先，避免「點滴」先吃掉「點滴瓶」這類情況
MOE_SORTED = sorted(MOE, key=len, reverse=True)

# ── L1：大陸用詞 ────────────────────────────────────────────────
# A 級：台灣與香港都不這樣說，一票否決
VOCAB_A = {
    "信息": "資訊",
    "軟件": "軟體",
    "硬件": "硬體",
    "網絡": "網路",
    "內存": "記憶體",
    "默認": "預設",
    "加載": "載入",
    "屏幕": "螢幕",
    "打印": "列印",
    "源代碼": "原始碼",
    "服務器": "伺服器",
    "賬號": "帳號",
    "視頻": "影片",
    "筆記本電腦": "筆記型電腦",
    "移動端": "行動裝置",
    "在線": "線上",
    "運營": "營運",
    "項目": "專案",
    "反饋": "回饋",
    "服務端": "伺服器端",
}

# B 級：多數情況該改，特定領域可保留
VOCAB_B = {
    "數據": "資料",
    "用戶": "使用者",
    "質量": "品質",
    "優化": "最佳化",
    "支持": "支援",
    "文件": "檔案",
    "連接": "連線",
    "公衆號": "公眾號",
    "公眾號": "公眾號",
}

# ── L2：大陸構詞法 ──────────────────────────────────────────────
GRAMMAR_PATTERNS = [
    (r"進行[討分研調論析究查][究]?", "「進行」+動詞，直接用動詞"),
    (r"作出(決定|判斷|回應|說明|選擇)", "「作出」+名詞，直接用動詞"),
    (r"對於[^。，,]{1,12}而言", "英文直譯，改「對…來說」"),
    (r"在[^。，,]{1,12}方面(上|來説)", "英文直譯，改「…的部分」"),
    (r"通過[^。，,]{1,15}來", "「通過…來」，改「用…」"),
    (r"一個(重要|關鍵|核心|主要)的", "「一個」冗餘"),
]

# ── AI 腔：模板句 ──────────────────────────────────────────────
TEMPLATE_ONE_LINE = [
    (r"總而言之|綜上所述|總體而言|整體而言", "空洞收尾", "整句刪除優先"),
    (r"希望(以上|這些)(內容|資訊)對(你|您)(有幫助|有所幫助)", "空洞收尾", "整句刪除優先"),
    (r"在這個.{0,12}(時代|社會|環境)", "假深刻開場", "直接講事實"),
    (r"隨著.{0,20}的(發展|進步|普及)", "假深刻開場", "直接講事實"),
    (r"你是否(曾經|有過)", "反問開頭", "改陳述句"),
    (r"不僅(僅)?[^。]{0,30}(而且|更是)", "遞進強迫症", "只留一層"),
    (r"作為(一個|一名)?\s*(AI|人工智能|語言模型)", "假謙虛", "刪"),
    (r"我(理解|明白)(你|您)的(需求|意思)", "假謙虛", "直接給答案"),
    (r"讓我(們)?(一起)?(來)?(看看|探索|了解)", "過度熱情", "講要做什麼"),
    (r"研究表明|根據統計|事實證明", "無出處權威", "給來源或刪"),
    (r"毫無疑問|毋庸置疑|不言而喻", "過度確定", "拿掉"),
    (r"這是(一個)?(非常)?(好|不錯)的(問題|問題)", "討好開場", "刪"),
    (r"值得(一提|注意)的是", "填充語", "通常可整句刪"),
    (r"需要(指出|強調)的是", "填充語", "通常可整句刪"),
    (r"眾所周知", "預設讀者無知", "刪"),
]

TEMPLATE_MULTILINE = [
    (r"首先[，,][\s\S]{0,300}?其次", "三段式（首先…其次）"),
    (r"第一個?方面[\s\S]{0,300}?第二個?方面", "三段式分點"),
    (r"一方面[，,][\s\S]{0,300}?另一方面", "對偶式對比"),
]

# ── AI 腔：抽象詞 ──────────────────────────────────────────────
ABSTRACT_WORDS = [
    "賦能", "抓手", "閉環", "落地", "生態", "矩陣", "體系", "機制",
    "維度", "場景", "賽道", "頂層設計", "方法論", "組合拳", "顆粒度",
]

# ── AI 腔：迴避簡單動詞（維基「Signs of human writing」的反面）──────
# 人類比 AI 更常寫「寫」「用」「試」「死」，AI 換成高級同義詞
STIFF_SYNONYMS = {
    "撰寫": "寫",
    "著述": "寫",
    "運用": "用",
    "採用": "用",
    "使用": "用",
    "設法": "試",
    "嘗試": "試",
    "逝世": "過世",
    "辭世": "過世",
    "具備": "有",
    "擁有": "有",
    "予以": "給",
    "進行了解": "了解",
    "從事": "做",
    "達成": "做到",
    "建構": "建立",
    "形塑": "形成",
    "驅動": "帶動",
}

# 迴避「是」的迂迴說法（英文 avoidance of copulatives 的中文對應）
COPULATIVE_AVOIDANCE = [
    (r"扮演[^。，,]{0,8}的?角色", "直接用「是」或說出做什麼"),
    (r"具有[^。，,]{0,12}的?(性質|特點|特徵|意義)", "直接說「是…」"),
    (r"起到[^。，,]{0,8}的?作用", "直接說做什麼"),
    (r"作為[^。，,]{0,10}的?存在", "直接說「是」"),
]

# ── 以下兩組「不是」AI 標誌，僅供參考，不列入判定 ──────────────
# 維基「Ineffective indicators」與「Signs of human writing」都指出：
# 單獨的過渡詞、模糊限定詞是人類也常用的寫法，不是可靠破綻。
HEDGES_NOT_A_TELL = ["可能", "或許", "也許", "通常", "往往", "大致"]
CONNECTIVES_NOT_A_TELL = ["因此", "然而", "此外", "同時", "並且", "從而"]


def split_sentences(text):
    parts = re.split(r"[。！？；!?;\n]", text)
    return [p.strip() for p in parts if p.strip()]


def rhythm(text):
    """句長標準差 ÷ 平均句長。數值越低越平滑（越像 AI）。"""
    sents = split_sentences(text)
    lengths = [len(s) for s in sents]
    if len(lengths) < 3:
        return None, len(lengths)
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return None, len(lengths)
    var = sum((x - mean) ** 2 for x in lengths) / len(lengths)
    return (var ** 0.5) / mean, len(lengths)


def per_kilo(text, words):
    total = 0
    for w in words:
        total += text.count(w)
    return total / max(len(text), 1) * 1000


def scan(text):
    findings = []
    lines = text.splitlines()

    for pattern, kind in TEMPLATE_MULTILINE:
        for m in re.finditer(pattern, text):
            lineno = text.count("\n", 0, m.start()) + 1
            findings.append({
                "line": lineno, "column": 1, "group": "AI 腔", "kind": kind,
                "found": m.group(0).splitlines()[0][:40], "suggest": "整句刪除優先",
            })

    for lineno, line in enumerate(lines, 1):
        for table, level in ((VOCAB_A, "A"), (VOCAB_B, "B")):
            for bad, good in table.items():
                start = 0
                while (idx := line.find(bad, start)) != -1:
                    findings.append({
                        "line": lineno, "column": idx + 1, "group": f"大陸用詞 {level} 級",
                        "kind": f"{level} 級用詞", "found": bad, "suggest": good,
                    })
                    start = idx + len(bad)

        for pattern, kind, sug in TEMPLATE_ONE_LINE:
            for m in re.finditer(pattern, line):
                findings.append({
                    "line": lineno, "column": m.start() + 1, "group": "AI 腔",
                    "kind": kind, "found": m.group(0), "suggest": sug,
                })

        for pattern, kind in GRAMMAR_PATTERNS:
            for m in re.finditer(pattern, line):
                findings.append({
                    "line": lineno, "column": m.start() + 1, "group": "大陸構詞",
                    "kind": kind, "found": m.group(0), "suggest": "見 SKILL.md L2",
                })

        for w in ABSTRACT_WORDS:
            start = 0
            while (idx := line.find(w, start)) != -1:
                findings.append({
                    "line": lineno, "column": idx + 1, "group": "AI 腔",
                    "kind": "抽象名詞", "found": w, "suggest": "換成具體動詞或事實",
                })
                start = idx + len(w)

        # 迴避簡單動詞（維基：人類更常用 wrote/used/tried/died 這類樸素詞）
        for stiff, plain in STIFF_SYNONYMS.items():
            start = 0
            while (idx := line.find(stiff, start)) != -1:
                findings.append({
                    "line": lineno, "column": idx + 1, "group": "AI 腔",
                    "kind": "高級同義詞", "found": stiff,
                    "suggest": f"考慮用「{plain}」",
                })
                start = idx + len(stiff)

        # 迴避「是」（英文 avoidance of copulatives 的中文對應）
        for pattern, sug in COPULATIVE_AVOIDANCE:
            for m in re.finditer(pattern, line):
                findings.append({
                    "line": lineno, "column": m.start() + 1, "group": "AI 腔",
                    "kind": "迂迴說法", "found": m.group(0), "suggest": sug,
                })

        # 教育部官方對照表（跳過已由 A/B 級表處理的詞，避免重複回報）
        for cn in MOE_SORTED:
            if cn in VOCAB_A or cn in VOCAB_B:
                continue
            start = 0
            while (idx := line.find(cn, start)) != -1:
                if len(cn) == 1:
                    # 單字歧義太重（「米」可能是長度也可能是米飯），只提示不判定
                    findings.append({
                        "line": lineno, "column": idx + 1,
                        "group": "大陸用詞（單字，需人工判斷）",
                        "kind": "單字待確認",
                        "found": cn,
                        "suggest": f"若指 {MOE[cn]} 才改；若是其他意思（如米飯）則不動",
                    })
                else:
                    findings.append({
                        "line": lineno, "column": idx + 1, "group": "大陸用詞（官方對照）",
                        "kind": "官方對照", "found": cn, "suggest": MOE[cn],
                    })
                start = idx + len(cn)

    findings.sort(key=lambda f: (f["line"], f["column"]))
    return findings


def metrics(text):
    r, n = rhythm(text)
    return {
        "char_count": len(text),
        "sentence_count": n,
        "rhythm": None if r is None else round(r, 3),
        "rhythm_verdict": (
            "樣本太少" if r is None
            else "平滑（AI 傾向）" if r < 0.35
            else "正常" if r < 0.5
            else "有摩擦（像人寫的）"
        ),
        "abstract_per_kilo": round(per_kilo(text, ABSTRACT_WORDS), 1),
        "stiff_per_kilo": round(per_kilo(text, list(STIFF_SYNONYMS)), 1),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="繁體中文 AI 腔調檢查器")
    p.add_argument("path", nargs="?", help="要檢查的檔案")
    p.add_argument("--stdin", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--quiet", action="store_true", help="只印體檢報告，不列逐項")
    args = p.parse_args(argv)

    if args.stdin or not args.path:
        text = sys.stdin.read()
    else:
        with open(args.path, encoding="utf-8") as f:
            text = f.read()

    findings = scan(text)
    m = metrics(text)

    a_count = sum(1 for f in findings if f["kind"].startswith("A 級"))
    b_count = sum(1 for f in findings if f["kind"].startswith("B 級"))
    moe_count = sum(1 for f in findings if f["kind"] == "官方對照")
    single_count = sum(1 for f in findings if f["kind"] == "單字待確認")
    gram = sum(1 for f in findings if f["group"] == "大陸構詞")
    ai_count = sum(1 for f in findings if f["group"] == "AI 腔")

    blocking = a_count + moe_count

    if args.json:
        print(json.dumps({
            "metrics": m,
            "summary": {
                "total": len(findings),
                "region_a": a_count, "region_b": b_count,
                "region_moe": moe_count, "region_single": single_count,
                "grammar": gram, "ai_tone": ai_count,
                "moe_table_size": len(MOE),
            },
            "findings": findings,
        }, ensure_ascii=False, indent=2))
        return 1 if (blocking or ai_count > 3) else 0

    # 體檢報告
    print("=== 體檢 ===")
    print(f"  字數            {m['char_count']}")
    print(f"  句長節奏        {m['rhythm']}  {m['rhythm_verdict']}")
    print(f"  抽象詞/千字     {m['abstract_per_kilo']}")
    print(f"  高級同義詞/千字 {m['stiff_per_kilo']}")
    print()
    print("=== 判定 ===")
    print(f"  大陸用詞   A 級 {a_count}（一票否決）、B 級 {b_count}、官方對照 {moe_count}")
    if single_count:
        print(f"  單字待確認 {single_count}（歧義多，不列入否決，自行看上下文）")
    print(f"  大陸構詞   {gram}")
    print(f"  AI 腔      {ai_count}")
    print(f"  （官方對照表載入 {len(MOE)} 條）")

    if blocking:
        print("\n  ⚠ 地區用詞必須先清，其餘先不要動。")

    if not args.quiet and findings:
        print("\n=== 逐項 ===")
        for f in findings:
            print(f"  {f['line']}:{f['column']}  [{f['kind']}] 「{f['found']}」 → {f['suggest']}")

    return 1 if (blocking or ai_count > 3) else 0


if __name__ == "__main__":
    sys.exit(main())
