#!/usr/bin/env python3
"""每小時行情快照：產生 live.json，給「Dami 加密日報」網站使用。
 
用法：python3 live_fetch.py [輸出路徑，預設 live.json]
資料來源（皆為公開 API，失敗的欄位填 null，不會整個中斷）：
- Binance 現貨（data-api.binance.vision）：BTC 4H K 線、BTC／ETH 24h 行情
- alternative.me：恐懼貪婪指數
- OKX 公開 API：BTC／ETH 永續資金費率、BTC 未平倉量、BTC 多空帳戶比
- deriv（合約數據，BTC／ETH／SOL）：OKX＋Deribit＋Hyperliquid 未平倉量合計（非全市場）、
  OKX 24h OI 變化、OKX 近 24h 強平金額、OKX 主動買賣量
"""
import json, sys, time, urllib.request, datetime
from fetch.storage import validate, write
 
UA = {"User-Agent": "dami-crypto-daily/1.0"}
TPE = datetime.timezone(datetime.timedelta(hours=8))
 
def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)
 
def safe(fn, errors, name):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - record and continue
        errors.append(f"{name}: {e}")
        return None
 
def closed(rows, now):
    return [row for row in rows if int(row[6]) <= now]

def candles():
    k = get("https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=4h&limit=151")
    now = int(time.time() * 1000)
    k = closed(k, now)
    if not k:
        raise ValueError('沒有已收盤 K 線')
    return {"tf": "4h", "src": "Binance BTCUSDT 現貨（data-api.binance.vision）", "lastOpen": False,
            "t": [x[0] for x in k], "o": [float(x[1]) for x in k], "h": [float(x[2]) for x in k],
            "l": [float(x[3]) for x in k], "c": [float(x[4]) for x in k], "v": [round(float(x[5]), 1) for x in k]}
 
def prices():
    d = get('https://data-api.binance.vision/api/v3/ticker/24hr?symbols=%5B%22BTCUSDT%22,%22ETHUSDT%22%5D')
    out = []
    for x in d:
        out.append({"asOf": datetime.datetime.fromtimestamp(int(x["closeTime"])/1000,TPE).isoformat(), "src":"Binance 現貨 24h", "delay":"交易所快照，傳輸延遲未知", "sym": x["symbol"].replace("USDT", ""), "price": float(x["lastPrice"]),
                    "chg24h": round(float(x["priceChangePercent"]), 2), "high": float(x["highPrice"]),
                    "low": float(x["lowPrice"]), "quoteVol": round(float(x["quoteVolume"]) / 1e6, 1)})
    if not out:
        raise ValueError("無行情")
    return sorted(out, key=lambda p: p["sym"] != "BTC")
 
def fear_greed():
    d = get("https://api.alternative.me/fng/?limit=2")["data"]
    lab = {"Extreme Fear": "極度恐懼", "Fear": "恐懼", "Neutral": "中性", "Greed": "貪婪", "Extreme Greed": "極度貪婪"}
    day = datetime.datetime.fromtimestamp(int(d[0]["timestamp"]), datetime.timezone.utc).strftime("%Y-%m-%d")
    return {"value": int(d[0]["value"]), "prev": int(d[1]["value"]), "label": lab.get(d[0]["value_classification"], d[0]["value_classification"]), "date": day, "src": "alternative.me"}
 
def funding():
    f = lambda inst: round(float(get(f"https://www.okx.com/api/v5/public/funding-rate?instId={inst}")["data"][0]["fundingRate"]) * 100, 4)
    return {"btc": f("BTC-USDT-SWAP"), "eth": f("ETH-USDT-SWAP"), "src": "OKX 永續（每 8 小時）"}
 
def oi():
    d = get("https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP")["data"][0]
    return {"btcUsdBn": round(float(d["oiUsd"]) / 1e9, 3), "src": "OKX BTC-USDT 永續"}
 
def long_short():
    d = get("https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=1H")["data"][0]
    r = float(d[1])
    return {"btc": round(r / (1 + r) * 100, 1), "ratio": r, "src": "OKX 帳戶多空比（1 小時）"}
 
# ---------- 合約數據（多所 OI、OKX 清算、OKX 主動買賣量） ----------
COINS = ["BTC", "ETH", "SOL"]
H_MS = 3600_000
 
def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={**UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)
 
def parse_okx_oi_hist(rows):
    """rubik open-interest-volume（新到舊，[ts, oiUsd, volUsd]）→ (最新 OI 十億美元, 24h 變化 %)"""
    now = float(rows[0][1])
    chg = round((now / float(rows[24][1]) - 1) * 100, 2) if len(rows) > 24 and float(rows[24][1]) else None
    return round(now / 1e9, 3), chg
 
def parse_deribit(result):
    """Deribit 反向期貨（含永續）open_interest 單位是美元"""
    if not result:
        raise ValueError("Deribit 無資料")
    return round(sum(float(x["open_interest"]) for x in result) / 1e9, 3)
 
def parse_hl(meta, ctx, coins):
    out = {}
    for u, c in zip(meta["universe"], ctx):
        if u["name"] in coins:
            out[u["name"]] = round(float(c["openInterest"]) * float(c["markPx"]) / 1e9, 3)
    return out
 
def combine_oi(per, coins):
    out = {"missing": [ex for ex, v in per.items() if v is None]}
    for coin in coins:
        row = {ex: v[coin] for ex, v in per.items() if v and coin in v}
        if row:
            row["total"] = round(sum(row.values()), 3)
        out[coin] = row
    return out
 
class LiqAcc:
    """累加 OKX 強平明細；side=sell 是多單被強平，side=buy 是空單被強平"""
    def __init__(self, cut_ms, ct_val):
        self.cut, self.ct = cut_ms, ct_val
        self.long_usd = self.short_usd = 0.0
        self.n, self.oldest = 0, None
 
    def add(self, details):
        for x in details:
            ts = int(x["ts"])
            if ts < self.cut:
                return False
            usd = float(x["sz"]) * self.ct * float(x["bkPx"])
            if x["side"] == "sell":
                self.long_usd += usd
            elif x["side"] != "buy":
                raise ValueError("強平方向不明")
            else:
                self.short_usd += usd
            self.n += 1
            self.oldest = ts if self.oldest is None else min(self.oldest, ts)
        return True
 
def parse_taker(rows, hours=24):
    """rubik taker-volume（新到舊，[ts, sellVol, buyVol]，美元）→ 近 hours 小時合計"""
    if not rows:
        raise ValueError("無成交量資料")
    r = rows[:hours]
    sell, buy = sum(float(x[1]) for x in r), sum(float(x[2]) for x in r)
    return {"buyM": round(buy / 1e6, 4), "sellM": round(sell / 1e6, 4), "ratio": round(buy / sell, 3) if sell else None, "hours": len(r)}
 
def okx_liq(coin, now_ms, max_pages=80):
    ct = float(get(f"https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId={coin}-USDT-SWAP")["data"][0]["ctVal"])
    acc, after, pages, capped = LiqAcc(now_ms - 24 * H_MS, ct), None, 0, False
    while True:
        d = get(f"https://www.okx.com/api/v5/public/liquidation-orders?instType=SWAP&uly={coin}-USDT&state=filled&limit=100" + (f"&after={after}" if after else ""))["data"]
        det = d[0]["details"] if d else []
        pages += 1
        if not det or not acc.add(det):
            break
        if pages >= max_pages:
            capped = True
            break
        cursor = det[-1]["ts"]
        if after is not None and int(cursor) >= int(after):
            raise ValueError("強平分頁未前進")
        after = cursor
        time.sleep(0.12)
    hours = round((now_ms - acc.oldest) / H_MS, 1) if acc.oldest else 0
    return {"longM": round(acc.long_usd / 1e6, 2), "shortM": round(acc.short_usd / 1e6, 2), "n": acc.n, "hours": min(hours, 24.0), "capped": capped}
 
def deriv(errors):
    now_ms = int(time.time() * 1000)
    okx_oi, chg = {}, {}
    for c in COINS:
        r = safe(lambda: parse_okx_oi_hist(get(f"https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-volume?ccy={c}&period=1H")["data"]), errors, f"deriv.okxOi.{c}")
        if r:
            okx_oi[c], chg[c] = r
    deribit = {}
    for c in ["BTC", "ETH"]:
        r = safe(lambda: parse_deribit(get(f"https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={c}&kind=future")["result"]), errors, f"deriv.deribit.{c}")
        if r is not None:
            deribit[c] = r
    hl = safe(lambda: parse_hl(*post("https://api.hyperliquid.xyz/info", {"type": "metaAndAssetCtxs"}), COINS), errors, "deriv.hyperliquid")
    oi_all = combine_oi({"okx": okx_oi or None, "deribit": deribit or None, "hl": hl or None}, COINS)
    liq = {c: safe(lambda: okx_liq(c, now_ms), errors, f"deriv.liq.{c}") for c in COINS}
    taker = {c: safe(lambda: parse_taker(get(f"https://www.okx.com/api/v5/rubik/stat/taker-volume?ccy={c}&instType=CONTRACTS&period=1H")["data"]), errors, f"deriv.taker.{c}") for c in COINS}
    return {
        "asOf": datetime.datetime.now(TPE).isoformat(timespec="seconds"),
        "oi": oi_all,
        "oiSrc": "OKX 全部合約＋Deribit BTC/ETH 期貨（含永續）＋Hyperliquid 永續；不含 Binance、Bybit、CME，不代表全市場",
        "oiChg24h": chg,
        "oiChgSrc": "僅 OKX 全部合約（1 小時資料，與 24 小時前比較）",
        "liq": liq,
        "liqSrc": "僅 OKX USDT 永續強平單（OKX 只保留約 1 天），不代表全市場",
        "taker": taker,
        "takerSrc": "僅 OKX 合約主動買賣量，近 24 小時合計",
    }
 
def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "live.json"
    errors = []
    live = {
        "updatedAt": datetime.datetime.now(TPE).isoformat(timespec="seconds"),
        "prices": safe(prices, errors, "prices"),
        "candles": safe(candles, errors, "candles"),
        "fearGreed": safe(fear_greed, errors, "fearGreed"),
        "funding": safe(funding, errors, "funding"),
        "oi": safe(oi, errors, "oi"),
        "longShort": safe(long_short, errors, "longShort"),
        "deriv": safe(lambda: deriv(errors), errors, "deriv"),
        "errors": errors,
    }
    if not live["prices"] and not live["candles"]:
        raise SystemExit("行情與 K 線均失敗，保留舊檔：" + "；".join(errors))
    validate("live", live)
    write(out_path, live)
    btc = (live["prices"] or [{}])[0].get("price")
    print(f"OK {live['updatedAt']} BTC={btc} errors={len(errors)}")
    for e in errors:
        print("ERR", e)
 
if __name__ == "__main__":
    main()
 
