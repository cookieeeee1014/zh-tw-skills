<div align="center">

# zh-tw-skills

**繁體中文的 Agent Skills**

繁中的語感、用詞、標點跟在簡中裡長出來的東西不一樣，直接轉換會留下痕跡。

[![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen?style=flat-square)](#設計原則)
[![Tests](https://img.shields.io/badge/tests-31%20passed-success?style=flat-square)](#)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](#授權)
[![繁中](https://img.shields.io/badge/%E7%B9%81%E4%B8%AD-Traditional%20Chinese-red?style=flat-square)](#)

</div>

---

## 一眼看懂

```bash
$ python scripts/check.py 你的文章.txt

=== 體檢 ===
  句長節奏        0.349  平滑（AI 傾向）
  抽象詞/千字     6.2
  高級同義詞/千字 4.1

=== 判定 ===
  大陸用詞   A 級 1（一票否決）、B 級 1、官方對照 2
  大陸構詞   4
  AI 腔      11

  ⚠ 地區用詞必須先清，其餘先不要動。
```

先量，再談。同一主題，兩種寫法的實測：

| 文本 | 句長節奏 | 抽象詞/千字 | AI 腔 | 判定 |
| --- | --- | --- | --- | --- |
| AI 寫的 | **0.349** | 6.2 | 11 處 | 平滑（AI 傾向） |
| 手寫的 | **0.820** | 0.0 | 0 處 | 有摩擦（像人寫的） |

差 **2.35 倍**。這個門檻寫在測試裡，改壞了會紅。

---

## 為什麼是繁體

英文世界早就證明這個需求是真的：

| 專案 | Stars | 做什麼 |
| --- | --- | --- |
| [`blader/humanizer`](https://github.com/blader/humanizer) | **62,940** | 英文去 AI 腔（本專案的靈感來源） |
| [`JimLiu/baoyu-skills`](https://github.com/JimLiu/baoyu-skills) | 27,111 | 中文 skills |
| [`vinvcn/mattpocock-skills-zh-CN`](https://github.com/vinvcn/mattpocock-skills-zh-CN) | 5,442 | 簡中本地化 |
| `ammosu/awesome-claude-skills-zh-TW` | 30 | 繁中清單 |
| `maggie00214/awesome-claude-skills-zh-tw` | 4 | 繁中清單 |
| `ddmanyes/agent-skills-toolkit-zh-tw` | 2 | 繁中工具包 |
| **`zh-tw-skills`（本專案）** | **0** | ← **你正在這裡** |

簡中做到了 5,442 星。繁中目前加起來不到 40 星，而且全是清單，沒有能跑的東西。

---

## 它抓什麼

真實輸出，不是示意圖：

```
輸入：
他撰寫了一份報告，運用新方法，嘗試解決問題。
這個設計扮演著關鍵的角色，具有重要的意義。

輸出：
  1:2   [高級同義詞] 「撰寫」 → 考慮用「寫」
  1:10  [高級同義詞] 「運用」 → 考慮用「用」
  1:16  [高級同義詞] 「嘗試」 → 考慮用「試」
  1:27  [迂迴說法]   「扮演著關鍵的角色」 → 直接用「是」
  1:36  [迂迴說法]   「具有重要的意義」 → 直接說「是…」

  AI 腔 5 處
```

對照組：

```
輸入：
他寫了一份報告，用新方法，試著解決問題。這個設計就是關鍵。這很重要。

輸出：
  AI 腔 0 處
```

---

## 三個可量測的信號

| 信號 | 怎麼算 | AI | 人 |
| --- | --- | --- | --- |
| **句長節奏** | 句長標準差 ÷ 平均句長 | < 0.35 | > 0.5 |
| **抽象詞密度** | 賦能／閉環／落地 ÷ 千字 | 高 | 低 |
| **高級同義詞密度** | 撰寫／運用／具備 ÷ 千字 | 高 | 低 |

斷言要長這樣：這篇節奏 0.31、抽象詞 8.4/千字、AI 腔 14 處。

---

## 繁簡判定：四層

| 層 | 內容 | 例子 | OpenCC 能處理 | AI 常犯 |
| --- | --- | --- | --- | --- |
| L0 | 字形 | 汉→漢 | ✅ | 很少 |
| **L1** | **術語命名** | **信息→資訊** | **❌** | **極常犯** |
| L2 | 構詞法 | 進行討論→討論 | ❌ | 常犯 |
| L3 | 語用語體 | 公文腔、稱謂 | ❌ | 常見 |

**主戰場在 L1。** OpenCC 把「信息」轉成繁體，結果還是「信息」——字形 100% 正確，用詞 100% 是大陸的。任何繁簡轉換工具都救不了這層，模型也不會自我察覺，因為它不覺得那是錯字。

### 詞表有官方依據

內建**教育部《國語辭典簡編本》附錄「兩岸常用詞語對照表」** 620 條，展開成 864 條可用映射：

```
公尺 ← 米          網際網路 ← 互聯網
埠 ← 端口          OK繃 ← 創可貼
點滴 ← 吊瓶        拘提 ← 拘傳
```

官方表收的是**生活與通用詞彙**。AI 寫繁體時最容易錯的**IT 術語**（`內存`、`默認`、`加載`、`源代碼`）反而不在裡面——那是人工詞表補的。兩者互補，不是重複。

---

## 安裝

```bash
# Claude Code
cp -r skills/zh-tw-humanizer ~/.claude/skills/

# DeepSeek Harness
cp -r skills/zh-tw-humanizer ~/.dsh/skills/
```

零依賴，只用 Python 標準函式庫。不裝套件、不連網。

```bash
python skills/zh-tw-humanizer/scripts/check.py 你的檔案.txt
python skills/zh-tw-humanizer/scripts/check.py --json 你的檔案.txt
cat 你的檔案.txt | python skills/zh-tw-humanizer/scripts/check.py --stdin
```

---

## 專案結構

```
zh-tw-skills/
├── skills/zh-tw-humanizer/
│   ├── SKILL.md                 判定體系（證據強度、人的寫作標誌、無效指標）
│   ├── PROMPT.md                可執行的提示詞 + 指標→動作翻譯表
│   └── scripts/check.py         檢查器（14.4 KB，零依賴）
├── tools/
│   ├── fetch_moe.py             重抓教育部官方詞表
│   └── moe_cross_strait.json    620 條官方對照（65 KB）
└── tests/
    ├── test_check.py            22 個測試
    ├── sample_ai.txt            AI 腔範例
    └── sample_human.txt         人寫範例
```

---

## 幾個容易搞錯的地方

「質量」在物理語境是對的。「用戶」在 B2B 產品裡也算合理。香港讀者寫「質素」更不算錯——這類詞改了反而糟。

「首先」「其次」在技術文件和操作步驟裡是正常結構。很多人以為刪掉就自然了，其實是把文章刪壞。

風險最高的是單字。教育部表收了「公尺←米」，那指的是長度；但米飯、玉米、稻米的「米」一改就荒謬。所以單字只提示，由人自己看上下文。

判斷法只有一句：這個詞是為了講精確，還是為了填篇幅？

還有件事我原本搞反了。維基把「或許」「通常」「非常」列為**人**寫作的標誌，不是 AI 的；同時說文法完美、正式學術腔、沒引用來源都不是可靠指標。這些已經照著改進 `SKILL.md`。

還有一個坑是這個工具自己的。它原本分不出「使用一個詞」和「討論一個詞」，所以這份 README 講「信息→資訊」時會被自己判定成錯字。現在引號、反引號、引用塊、`→` 對照行都豁免了，誤報從 7 處降到 0。

但表格裡的詞表（上面那行 `賦能／閉環／落地 ÷ 千字`）還是會被抓。要做到零誤報需要語意理解，純字串比對做不到。用的人要知道這個邊界。

---

## 參考資料

- 維基百科 [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)（WikiProject AI Cleanup 維護）
- [`blader/humanizer`](https://github.com/blader/humanizer)（62,940★）—— 六大類 25 模式、證據強度分級、用戶樣本優先原則
- [教育部《國語辭典簡編本》2021 附錄](https://dict.concised.moe.edu.tw/appendix.jsp?ID=54)（中華民國教育部公開資料）
- Cheng et al. 2025, [Ability of AI detection tools and humans to accurately identify AI-generated content](https://doi.org/10.1186/s41077-025-00396-6)

## 授權

MIT（程式碼）。詞表資料版權屬中華民國教育部。
