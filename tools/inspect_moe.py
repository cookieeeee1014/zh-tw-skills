import json
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "tools" / "moe_cross_strait.json"
d = json.loads(p.read_text(encoding="utf-8"))
e = d["entries"]

print("total", d["count"])
print()
print("=== 抽樣 ===")
for i in (0, 50, 120, 250, 400, 550, 615):
    if i < len(e):
        r = e[i]
        print(f"  {r['tw']:<14} <- {'／'.join(r['cn'])}")

mine_a = ["信息", "軟件", "硬件", "網絡", "內存", "默認", "加載", "屏幕",
          "打印", "源代碼", "服務器", "賬號", "視頻", "筆記本電腦",
          "移動端", "在線", "運營", "項目", "反饋"]
mine_b = ["數據", "用戶", "質量", "優化", "支持", "文件", "連接"]

cn_index = {}
for r in e:
    for c in r["cn"]:
        cn_index.setdefault(c, []).append(r["tw"])

print()
print("=== 我的 A 級詞 vs 官方表 ===")
hit_a = 0
for w in mine_a:
    if w in cn_index:
        hit_a += 1
        print(f"  OK   {w:<10} -> {'／'.join(cn_index[w])}")
    else:
        print(f"  MISS {w:<10} 官方表無此條")

print()
print("=== 我的 B 級詞 vs 官方表 ===")
hit_b = 0
for w in mine_b:
    if w in cn_index:
        hit_b += 1
        print(f"  OK   {w:<10} -> {'／'.join(cn_index[w])}")
    else:
        print(f"  MISS {w:<10} 官方表無此條")

print()
print(f"A 級命中 {hit_a}/{len(mine_a)}，B 級命中 {hit_b}/{len(mine_b)}")
