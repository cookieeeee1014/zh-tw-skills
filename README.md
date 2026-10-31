<div align="center">

# zh-tw-skills

**繁體中文的 Agent Skills**

判斷一段繁體中文是台灣／香港人寫的，還是機器寫的。

[![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen?style=flat-square)](#零依賴)
[![Tests](https://img.shields.io/badge/tests-31%20passed-success?style=flat-square)](#)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](#授權)

</div>

---

繁簡轉換工具（OpenCC 之類）把「汉」變成「漢」，但它把「信息」轉成繁體之後還是「信息」——字形全對，用詞全是大陸的。這個工具補的就是這一層，外加量化「AI 腔」。

## 它抓什麼

真實輸出：

```
$ python skills/zh-tw-humanizer/scripts/check.py 你的文章.txt

=== 體檢 ===
  句長節奏        0.349  平滑（AI 傾向）
  抽象詞/千字     6.2
  高級同義詞/千字 4.1

=== 判定 ===
  大陸用詞   A 級 1（一票否決）、B 級 1、官方對照 2
  大陸構詞   4
  AI 腔      11

=== 逐項 ===
  1:15  [A 級用詞]  「信息」 → 資訊
  3:18  [抽象名詞]  「賦能」 → 換成具體動詞或事實
  5:3   [否定平行]  「不是…是」 → 直接講肯定的那半
```

支援 `--json`、`--stdin`、`--quiet`。

## 三個可量測的信號

同一主題，兩種寫法的實測：

| | 句長節奏 | 抽象詞/千字 | AI 腔 |
| --- | --- | --- | --- |
| AI 寫的 | **0.349** | 6.2 | 11 處 |
| 手寫的 | **0.820** | 0.0 | 0 處 |

句長節奏 = 句長標準差 ÷ 平均句長。數值越低越平滑。差 2.35 倍，門檻寫在測試裡。

另外兩個：抽象詞密度（賦能／閉環／落地 ÷ 千字）、高級同義詞密度（撰寫／運用／具備 ÷ 千字）。

## 安裝

```bash
# Claude Code
cp -r skills/zh-tw-humanizer ~/.claude/skills/

# DeepSeek Harness
cp -r skills/zh-tw-humanizer ~/.dsh/skills/
```

零依賴，只用 Python 標準函式庫。不裝套件、不連網。

```bash
python skills/zh-tw-humanizer/scripts/check.py 檔案.txt
python skills/zh-tw-humanizer/scripts/check.py --json 檔案.txt
cat 檔案.txt | python skills/zh-tw-humanizer/scripts/check.py --stdin
```

也可以當普通 Python 用：

```python
import sys; sys.path.insert(0, "skills/zh-tw-humanizer/scripts")
from check import scan, metrics
```

## 判定分四層

| 層 | 內容 | 例子 | OpenCC 能處理 | AI 常犯 |
| --- | --- | --- | --- | --- |
| L0 | 字形 | 汉→漢 | ✅ | 很少 |
| **L1** | **術語命名** | **信息→資訊** | **❌** | **極常犯** |
| L2 | 構詞法 | 進行討論→討論 | ❌ | 常犯 |
| L3 | 語用語體 | 公文腔、稱謂 | ❌ | 常見 |

L1 是重點。工具內建**教育部《國語辭典簡編本》附錄「兩岸常用詞語對照表」** 620 條，展開成 864 條映射：

```
公尺 ← 米          網際網路 ← 互聯網
埠 ← 端口          OK繃 ← 創可貼
點滴 ← 吊瓶        拘提 ← 拘傳
```

官方表收生活與通用詞彙，AI 寫繁體最容易錯的 IT 術語（`內存`、`默認`、`加載`、`源代碼`）不在裡面，由人工詞表補。兩者互補。

詞表可自行重抓：`python tools/fetch_moe.py`

## 邊界

**會誤報的地方。** 單字詞歧義太大——教育部表收了「公尺←米」指的是長度，但米飯、玉米、稻米的「米」一改就荒謬。所以單字只提示，不影響 exit code。

表格裡的詞表行（`賦能／閉環／落地`）也會被抓，因為工具分不出「列舉一個詞」和「使用一個詞」。引號、反引號、引用塊、程式碼區塊都已豁免，但這一類做不到。

**不該改的地方。** 技術文件和操作步驟裡的「首先」「其次」是正常結構；物理語境的「質量」是對的；B2B 產品的「用戶」可接受；香港讀者寫「質素」也不算錯。

判斷法只有一句：這個詞是為了講精確，還是為了填篇幅？

**不是 AI 標誌的東西。** 文法完美、正式學術腔、沒引用來源，這些在維基百科的 `ineffective indicators` 裡。而「或許」「通常」「非常」是**人**寫作的標誌。2025 年的研究顯示，人靠感覺判斷 AI 文的準確率不比隨機猜好，所以這裡的門檻全部由測試釘住。

## 專案結構

```
skills/zh-tw-humanizer/
├── SKILL.md              判定體系
├── PROMPT.md             可執行提示詞 + 指標→動作翻譯表
└── scripts/check.py      檢查器（零依賴）
tools/
├── fetch_moe.py          重抓教育部官方詞表
└── moe_cross_strait.json 620 條官方對照
tests/                    31 個測試
```

## 參考

- [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)（WikiProject AI Cleanup）
- [blader/humanizer](https://github.com/blader/humanizer)（MIT）—— 分類架構與證據強度原則
- [教育部《國語辭典簡編本》2021 附錄](https://dict.concised.moe.edu.tw/appendix.jsp?ID=54)

## 授權

MIT（程式碼）。詞表資料版權屬中華民國教育部，詳見 `NOTICE.md`。
