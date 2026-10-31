#!/usr/bin/env python3
"""抓取教育部《國語辭典簡編本》附錄「兩岸常用詞語對照表」。

來源：https://dict.concised.moe.edu.tw/appendix.jsp?ID=54
輸出：data/moe_cross_strait.json

資料為中華民國教育部公開資料。
"""

import json
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://dict.concised.moe.edu.tw/appendix.jsp?ID=54&page={}"
OUT = Path(__file__).resolve().parent / "moe_cross_strait.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch(page):
    req = urllib.request.Request(BASE.format(page), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def clean(s):
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("\u3000", " ").strip()


def parse(html):
    tstart = html.find("<table")
    tend = html.find("</table>", tstart)
    if tstart < 0 or tend < 0:
        return []
    table = html[tstart:tend]
    rows = re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", table)

    out = []
    for row in rows:
        m_tw = re.search(r"(?s)<td class=val[^>]*>(.*?)</td>", row)
        m_cn = re.search(r"(?s)<td class='?sub'?[^>]*>(.*?)</td>", row)
        if not (m_tw and m_cn):
            continue
        tw = clean(m_tw.group(1))
        cn_raw = clean(m_cn.group(1))
        if not tw or not cn_raw:
            continue
        cn = [x.strip() for x in re.split(r"[／/]", cn_raw) if x.strip()]
        out.append({"tw": tw, "cn": cn})
    return out


def main():
    all_rows = []
    seen = set()
    for page in range(1, 8):
        html = fetch(page)
        rows = parse(html)
        added = 0
        for r in rows:
            key = (r["tw"], tuple(r["cn"]))
            if key in seen:
                continue
            seen.add(key)
            all_rows.append(r)
            added += 1
        print(f"  page {page}: {len(rows)} parsed, {added} new")
        time.sleep(1.0)  # 對來源站台客氣一點

    all_rows.sort(key=lambda r: r["tw"])
    OUT.write_text(
        json.dumps({
            "source": "教育部《國語辭典簡編本》2021 附錄：兩岸常用詞語對照表",
            "url": "https://dict.concised.moe.edu.tw/appendix.jsp?ID=54",
            "count": len(all_rows),
            "entries": all_rows,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n總計 {len(all_rows)} 條 -> {OUT}")
    print(f"檔案大小 {OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
