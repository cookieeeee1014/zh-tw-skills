# 資料來源與授權

本專案分兩部分，授權範圍不同。

## 程式碼

`skills/`、`tools/*.py`、`tests/` 底下的所有程式碼：**MIT**，見 `LICENSE`。

## 詞表資料

`tools/moe_cross_strait.json` 衍生自：

> 教育部《國語辭典簡編本》2021 附錄「兩岸常用詞語對照表」
> 中華民國教育部
> https://dict.concised.moe.edu.tw/appendix.jsp?ID=54

該資料由中華民國教育部公開，版權屬教育部。本專案依其原始條款使用，MIT 授權不涵蓋此檔案。若要用於商業用途，請自行確認教育部的授權條款。

重新取得資料的方式見 `tools/fetch_moe.py`。

## 規則來源

`skills/zh-tw-humanizer/SKILL.md` 與 `PROMPT.md` 中的寫作模式，主要整理自：

- 維基百科 [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)，由 WikiProject AI Cleanup 維護，採用 CC BY-SA 4.0。
- [`blader/humanizer`](https://github.com/blader/humanizer)（MIT）的分類架構與證據強度原則。

本專案對上述內容做了繁體中文的重新歸納與實作，並加入了量化指標與繁簡判定，這兩部分是原專案沒有的。
