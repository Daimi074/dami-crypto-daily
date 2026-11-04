# Dami 加密日報

每天兩份的加密貨幣與美股研究報告，以及閱讀報告用的圖表網站。

- 早報（台北 07:55）：加密市場、K 線走勢解讀、美債殖利率、建議操作
- 晚報＋美股（台北 20:52）：加上美股追蹤標的與跨市場因果鏈

## 結構

| 路徑 | 內容 |
|---|---|
| `index.html` | 網站（由 `tools/build.py` 產生，不要直接改） |
| `src/page.html` | 網站原始碼 |
| `data/reports/<日期>-morning.json`、`-evening.json` | 每份報告的完整數據 |
| `data/index.json` | 報告清單（由 `tools/build.py` 產生） |
| `reports/*.md` | 每份報告的 Markdown 全文（由 `tools/build.py` 產生） |

## 新增一份報告

1. 把報告 JSON 放進 `data/reports/`
2. 執行 `python3 tools/build.py`
3. commit 並 push

## 資料來源

報告內每個數字都標有來源與時間。K 線來自 Binance 公開行情，美債殖利率來自美國財政部 Daily Treasury Par Yield Curve。

## 免責

報告中的建議操作是候選訊號，需自行判斷並手動下單；不是投資建議，不保證走勢或報酬。
