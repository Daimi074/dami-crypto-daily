"""從公開行情建立編輯用草稿。已存在的草稿保留人工編輯。"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from report.calendar import section
from calc.technical import TPE, iso, structure
from fetch.storage import ROOT, write

STOCKS = "QQQ SPCX NVDA TSLA TSM AMD MSFT GOOG GOOGL GLW".split()
INDICES = "SPX NDX DJI SOX RUT VIX ES NQ".split()
COMMON = [
    "主線事件與來源核對",
    "跨市場因果鏈",
    "類股輪動與加密相關股",
    "ETF、交易所流向與穩定幣",
    "財報與今晚事件",
    "QQQ 風險開關",
    "K 線走勢解讀",
    "前次驗證點與候選回顧",
    "接下來如何驗證與失效條件",
    "BTC 三情境與突破條件",
    "美股觀察與計畫",
    "來源",
]
READINGS = dict(
    kpis="先對照資料時間。只有部分交易所的未平倉量，不能代表全市場資金流向。",
    kline="每根 K 線代表四小時。先看收盤相對兩條均線的位置，再看五段高低點有沒有同方向移動。",
    ladder="先找進場、停損和第一目標。風報比低於 1.5 時跳過順勢候選。",
    trends="每個點代表一份報告。比較不同報告時，先看兩份的資料時間。",
    macro="美元與殖利率可協助判讀資金成本，單獨一項變動不足以確認因果。",
    stocks="先看 QQQ，再看個股的常規盤與延長盤，兩者的成交量不同。",
    yields="以美東官方日值比較。長短利差等於十年期減兩年期，百分點乘 100 換算成基點。",
)
NO_TRADE = [
    "盤整區內",
    "觸發 K 量低於近 90 根均量",
    "每 8h 資金費率高於 +0.03% 不追多、低於 −0.03% 不追空",
    "重大數據或 ETF 數字公布前後一小時",
    "美股開盤首小時",
    "FOMC 事件前後兩小時",
]
FIXED = [
    "順勢候選是依均線與價格結構的規則式訊號，未經回測驗證，訊號變多代表假訊號也會變多。",
    "沒有使用者最新持倉資料，以上不假設已有倉位、不沿用舊倉推算。",
    "以上為候選訊號，需自行判斷並手動下單；不是投資建議，不保證走勢或報酬。",
]


def read(path):
    return json.loads(Path(path).read_text("utf-8-sig"))


def build(kind, live, yields, now):
    date = now.date().isoformat()
    title = ("加密日報 " if kind == "morning" else "加密＋美股晚報 ") + date
    m = dict(
        prices=live["prices"] or [],
        candles=live["candles"],
        trend=None,
        stance=None,
        action=None,
        qqqSwitch=None,
        correction=None,
        fearGreed=(live.get("fearGreed") or {}).get("value"),
        funding=live.get("funding"),
        longShort=live.get("longShort"),
        yields=yields,
        etf=None,
        scenarios=[],
        breakoutAlt=None,
        checks=[],
        stockPlans=[],
        causal=[],
        events=[],
        readings=READINGS,
        noTrade=NO_TRADE,
        dataQuality=[],
        sectors={"strong": [], "weak": []},
        stocks=[{"sym": s} for s in STOCKS],
        indices=[{"sym": s} for s in INDICES],
        cryptoStocks=[{"sym": s} for s in ("COIN", "MSTR", "IBIT")],
        earnings={"last": [], "upcoming": []},
    )
    for p in m["prices"]:
        p["range24h"] = [p["low"], p["high"]]
    d = live.get("deriv") or {}
    m["oi"] = {
        "btc": ((d.get("oi") or {}).get("BTC") or {}).get("total"),
        "scope": "部分交易所",
        "src": d.get("oiSrc"),
        "chg24h": None,
    }
    m["liquidations24h"] = None
    liq = (d.get("liq") or {}).get("BTC")
    if liq:
        m["liquidations24h"] = dict(
            long=liq["longM"],
            short=liq["shortM"],
            total=round(liq["longM"] + liq["shortM"], 2),
            scope="僅 OKX",
            capped=liq["capped"],
        )
    m["deriv"] = d
    c = m["candles"]
    if c and not c["lastOpen"]:
        m["trend"], m["indicators"], phases = structure(c)
        m["klineStory"] = {
            "summary": "",
            "phases": [
                dict(p, label=f"第{i}段", why="原因不明")
                for i, p in enumerate(phases, 1)
            ],
        }
        m["levels"] = {
            "support": [p["low"] for p in phases if p["low"] < c["c"][-1]],
            "resistance": [p["high"] for p in phases if p["high"] > c["c"][-1]],
        }
    m["macro"] = (
        {}
        if not yields
        else dict(
            us10y=yields["y10"][-1],
            us2y=yields["y2"][-1],
            spread=yields["spread"],
            curveShape=yields["monthly"]["shape"],
        )
    )
    for field, note in [
        ("oi", "全市場 OI 未取得；分所數字不可支持追單。"),
        ("etf", "待核對前一交易日"),
        ("stocks", "待核對盤別、交易日、均線及延遲"),
        ("qqqSwitch", "待核對 VIX、均線及高低點"),
    ]:
        m["dataQuality"].append(
            dict(
                field=field,
                status=(
                    "partial"
                    if field == "oi" and m["oi"]["btc"] is not None
                    else "missing"
                ),
                note=note,
            )
        )
    for source_issue in live.get("dataQuality", []):
        if source_issue.get("status") == "stale":
            m["dataQuality"].append(
                dict(
                    source_issue,
                    field=(
                        "prices"
                        if source_issue["field"] in ("BTC", "ETH")
                        else source_issue["field"]
                    ),
                )
            )
    for field in [
        "prices",
        "candles",
        "fearGreed",
        "funding",
        "longShort",
        "yields",
        "liquidations24h",
    ]:
        if not m.get(field):
            m["dataQuality"].append(
                dict(field=field, status="missing", note="來源未取得")
            )
    age = (now - datetime.fromisoformat(live["updatedAt"])).total_seconds()
    if age > 7200 or age < 0:
        m["dataQuality"].append(
            dict(field="live", status="stale", note="行情與截稿時間不符")
        )
    if (ROOT / "data/indices.json").exists():
        index_rows = {
            x["sym"]: x for x in read(ROOT / "data/indices.json") if x["asOf"] <= date
        }
        m["indices"] = [index_rows.get(sym, {"sym": sym}) for sym in INDICES]
        m["dataQuality"].append(
            dict(
                field="indices",
                status="partial",
                note="有值的指數標示美東日值，其餘待編輯核對。",
            )
        )
    if yields and (now.date() - datetime.fromisoformat(yields["asOf"]).date()).days > 4:
        m["dataQuality"].append(
            dict(
                field="yields",
                status="stale",
                note="官方日值超過四個日曆日，請核對休市日或來源延遲。",
            )
        )
    sections = COMMON[:-1] + [section(now.date(), kind)] + COMMON[-1:]
    return dict(
        date=date,
        kind=kind,
        title=title,
        sortKey=date + ("-1" if kind == "morning" else "-2"),
        headline="",
        updatedAt=now.isoformat(timespec="seconds"),
        marketAsOf=live["updatedAt"],
        metrics=m,
        sections=dict.fromkeys(sections, ""),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["morning", "evening"], required=True)
    parser.add_argument("--live", default=ROOT / "data/live.json")
    parser.add_argument("--yields", default=ROOT / "data/yields.json")
    args = parser.parse_args()
    r = build(
        args.kind,
        read(args.live),
        read(args.yields) if Path(args.yields).exists() else None,
        datetime.now(TPE),
    )
    path = ROOT / ".drafts" / (r["date"] + "-" + args.kind + ".json")
    if not path.exists():
        write(path, r)
    elif (ROOT / "reports" / path.name).exists():
        print("已有同名正式報告，保留版本")
    elif (
        datetime.now(TPE) - datetime.fromisoformat(read(path)["marketAsOf"])
    ).total_seconds() > 7200:
        print("草稿行情超過兩小時。請重新核對來源並更新草稿中的快照，再發布。")
    print(path)
    print(
        "待寫欄位：" + "、".join(k for k, v in read(path)["sections"].items() if not v)
    )


if __name__ == "__main__":
    main()
