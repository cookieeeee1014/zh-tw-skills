#!/usr/bin/env python3
"""繁體中文標點與排版檢查。

只管可以機械判定的錯：半形標點混進中文、省略號與破折號寫法、引號格式、
中英文之間的空白。不改檔案，只報位置。

只用標準函式庫。

用法：
    python check_type.py 檔案.txt
    python check_type.py --stdin < 檔案.txt
    python check_type.py --json --strict 檔案.txt
"""

import argparse
import json
import re
import sys

CJK = r"\u4e00-\u9fff"


def cn(ch):
    return re.match(f"[{CJK}]", ch) is not None


# 確定錯誤：(名稱, regex, 建議)
CERTAIN = [
    ("半形逗號", re.compile(rf"([{CJK}])\s*,"), "，"),
    ("半形句號", re.compile(rf"([{CJK}])\s*\.(?![0-9a-zA-Z.])"), "。"),
    ("半形冒號", re.compile(rf"([{CJK}])\s*:"), "："),
    ("半形分號", re.compile(rf"([{CJK}])\s*;"), "；"),
    ("半形問號", re.compile(rf"([{CJK}])\s*\?"), "？"),
    ("半形驚嘆號", re.compile(rf"([{CJK}])\s*!"), "！"),
    ("省略號", re.compile(r"\.\.\.+"), "……"),
    ("省略號（句點堆疊）", re.compile(r"。。+"), "……"),
    ("破折號", re.compile(r"(?<!-)--(?!-)"), "——"),
    ("直引號", re.compile(r'"[^"\n]{1,60}"'), "「…」"),
]

# 建議級
SUGGEST = [
    ("半形括號包中文", re.compile(rf"\([{CJK}][^()\n]{{0,20}}\)"), "（）"),
    ("刪節號後多餘句號", re.compile(r"……\s*。"), "刪掉句號"),
]

# 中英文之間缺空格（只提示，不判定為錯）
LATIN_CJK = re.compile(rf"([{CJK}])([A-Za-z0-9])|([A-Za-z0-9])([{CJK}])")

SKIP_LINE = re.compile(r"^\s*(```|~~~|>|#{1,6}\s)")
URLISH = re.compile(r"https?://\S+")


def scan(text, strict=False):
    findings = []
    lines = text.splitlines()
    in_fence = False

    for lineno, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        # 移除 URL、行內程式碼與 HTML 標籤，避免誤判
        line = URLISH.sub(lambda m: " " * len(m.group(0)), raw)
        line = re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), line)
        line = re.sub(r"<[^>\n]{1,200}>", lambda m: " " * len(m.group(0)), line)

        for name, pattern, sug in CERTAIN:
            for m in pattern.finditer(line):
                findings.append({
                    "line": lineno, "column": m.start() + 1, "level": "錯誤",
                    "kind": name, "found": m.group(0)[:30], "suggest": sug,
                })

        for name, pattern, sug in SUGGEST:
            for m in pattern.finditer(line):
                findings.append({
                    "line": lineno, "column": m.start() + 1, "level": "建議",
                    "kind": name, "found": m.group(0)[:30], "suggest": sug,
                })

        if strict:
            for m in LATIN_CJK.finditer(line):
                findings.append({
                    "line": lineno, "column": m.start() + 1, "level": "建議",
                    "kind": "中英文間缺空格", "found": m.group(0),
                    "suggest": f"{m.group(1) or m.group(3)} {m.group(2) or m.group(4)}",
                })

    findings.sort(key=lambda f: (f["line"], f["column"]))
    return findings


def main(argv=None):
    p = argparse.ArgumentParser(description="繁體中文標點與排版檢查")
    p.add_argument("path", nargs="?", help="要檢查的檔案")
    p.add_argument("--stdin", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true", help="連建議級的空白問題也列入")
    args = p.parse_args(argv)

    if args.stdin or not args.path:
        text = sys.stdin.read()
    else:
        with open(args.path, encoding="utf-8") as f:
            text = f.read()

    findings = scan(text, strict=args.strict)
    errors = [f for f in findings if f["level"] == "錯誤"]
    suggests = [f for f in findings if f["level"] == "建議"]

    if args.json:
        print(json.dumps({
            "total": len(findings),
            "errors": len(errors),
            "suggestions": len(suggests),
            "findings": findings,
        }, ensure_ascii=False, indent=2))
        return 1 if errors else 0

    if not findings:
        print("標點與排版沒有問題。")
        return 0

    for f in findings:
        print(f"  {f['line']}:{f['column']}  [{f['kind']}] 「{f['found']}」 → {f['suggest']}")

    print()
    print(f"確定錯誤 {len(errors)} 處，建議 {len(suggests)} 處。")
    if errors:
        print("錯誤那幾條改了沒有爭議；建議那幾條看語境。")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
