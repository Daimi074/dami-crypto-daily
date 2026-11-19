# Dami 加密日報 v2

[閱讀日報](https://daimi074.github.io/dami-crypto-daily/) · [判讀規則](docs/RULES.md)

每小時整理公開行情，早晚各製作一份 BTC、ETH 與美股研究報告。綠色代表上漲、紅色代表下跌。研究部位是固定假設，沒有交易功能。網站沿用既有 HTML 與 SVG 圖表，靜態檔可直接部署，走勢可用滑鼠或觸控讀值。Markdown 由隨站提供的 marked 解析，經 DOMPurify 清理。

## 第一次使用

在專案根目錄，以 Python 3.12 或更新版本執行以下命令。

```sh
python -m pip install -r requirements.txt
python -m fetch.live data/live.json
python -m fetch.treasury
python -m fetch.indices
python -m fetch.headlines
python -m report.build --kind morning
```

晚報把 morning 改為 evening。行情與 K 線同時取得失敗時會保留舊快照。殖利率採美國財政部日值，每個報告保留當次快照。首頁時間反映最近擷取時間，來源本身的交易日期另列。

## 製作與校對

1. 開啟 .drafts 裡的日期與時段 JSON。sections 是須查證與撰寫的各節，metrics 是網站用的數值。先核對行情與前報，再填寫行動、開關、資料品質、事件及來源。新聞檢查結果在 .drafts/news.json，時間不可核實的首頁不能當成當日證據。
2. 確認美東交易日與台北事件時間。休市時依規則改寫週回顧或下次開盤準備。指數、股票、類股、ETF 及重大事件依公開報價或正式公告核對。無法查證時列出原因。
3. 執行以下命令。publish 前會檢查草稿並重算情境。每份正式 JSON 的 markdown 取自同名正文。若同名正文已有不同人工內容，會保留並告知衝突。
4. 部署前核對差異，只提交預定公開的檔案。不要提交草稿、對話、帳戶資料或金鑰。

```sh
python -m report.validate .drafts/YYYY-MM-DD-morning.json --publish
python -m unittest discover -v
python -m report.validate --all
python -m http.server 8000
```

## 檔案與部署

- fetch 負責公開資料，calc 計算指標、趨勢與試算，report 組裝、驗證與遷移，schema 定義資料格式。
- reports 保存新版 Markdown、JSON 和 index.json。既有十份歷史報告沿用 data/reports，data/index.json 保持舊入口可讀。tools/build.py 從 src/page.html 更新首頁，現有 Markdown 是正文的依據。
- 歷史匯入放在 import/daily，確認資料可公開後執行 python -m report.migrate。缺少正式來源時不會補造歷史報告。標為「時點重建」的驗收報告採當時市場快照與事後可核實的已收盤資料，其更新時間為實際製作時間。
- GitHub Actions 的 live.yml 每小時第 7 分更新。drafts.yml 每日台北 07:55、20:52 產生數據草稿，留在當次執行的 editorial-draft 附件。GitHub 排程可能延遲。文字由另一個編輯排程查來源後填寫，單有 Actions 並不會自行產生查證過的新聞。
- GitHub 設定 Pages 的部署來源為 GitHub Actions。pages.yml 在 main 更新或行情流程成功後，測試並只發布 index.html、assets、reports、data。
- 調整版面請改 src/page.html 並執行 python tools/build.py。各圖提供按鈕或圖下解讀。快照超過兩小時顯示黃色提醒，超過六小時顯示紅色過期。操作建議另以報告截點為準。

