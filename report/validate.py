import argparse
import subprocess
import sys
from datetime import datetime
import re
from pathlib import Path
from calc.risk import scenario
from calc.technical import structure
from fetch.storage import ROOT, validate, write
from report.build import read, COMMON, STOCKS, INDICES
from report.render import render


def prepare(r):
    m = r["metrics"]
    missing = [k for k in COMMON if not r["sections"].get(k, "").strip()]
    if missing or not all(v.strip() for v in r["sections"].values()):
        raise ValueError("仍有待寫欄位：" + str(missing))
    if r.get("marketAsOf") and not r["title"].endswith("（時點重建）"):
        age = (
            datetime.fromisoformat(r["updatedAt"])
            - datetime.fromisoformat(r["marketAsOf"])
        ).total_seconds()
        if (age > 7200 or age < -300) and m["stance"] not in ("觀望", "減碼"):
            raise ValueError("資料過期，不能依舊快照進場")
    if not m["action"] or not m["stance"]:
        raise ValueError("缺動作或立場")
    if bool(m["correction"]) != r["headline"].startswith("【修正】"):
        raise ValueError("修正標記不一致")
    if m.get("candles"):
        if m["candles"]["lastOpen"] or m["trend"] != structure(m["candles"])[0]:
            raise ValueError("趨勢與已收盤 K 線不符")
    if (
        m["trend"] in ("多頭趨勢", "空頭趨勢")
        and not m["scenarios"]
        and not m.get("skipReason")
    ):
        raise ValueError("順勢候選缺漏，須記錄風報比或不交易條件")
    if (m.get("breakoutAlt") or {}).get("triggered") and not (
        m.get("globalOiConfirmed") and m.get("globalOiSource")
    ):
        raise ValueError("全市場 OI 未證實，不能觸發突破候選")
    if r["date"] != r["sortKey"][:10] or r["sortKey"][-1] != (
        "1" if r["kind"] == "morning" else "2"
    ):
        raise ValueError("日期或報告時段不一致")
    if not r["headline"].removeprefix("【修正】").startswith(m["trend"] or "資料不足"):
        raise ValueError("標題需先說明趨勢")
    if m["qqqSwitch"] is None and not any(
        q["field"] == "qqqSwitch" and q["status"] != "ok" for q in m["dataQuality"]
    ):
        raise ValueError("QQQ 開關缺值須說明")
    if any(
        not m.get("readings", {}).get(key)
        for key in ("kpis", "kline", "ladder", "trends", "macro", "stocks", "yields")
    ):
        raise ValueError("缺圖表閱讀說明")
    if not {"QQQ"} <= set(p["sym"] for p in m["stockPlans"]):
        raise ValueError("美股計畫須包含 QQQ")
    if not set(STOCKS) <= set(p["sym"] for p in m["stocks"]) or not set(INDICES) <= set(
        p["sym"] for p in m["indices"]
    ):
        raise ValueError("追蹤清單不完整")
    if not re.search(r"https?://", r["sections"]["來源"]):
        raise ValueError("缺公開來源連結")
    if m.get("correction") and not all(
        m["correction"].get(k) for k in ("previous", "newData", "revised")
    ):
        raise ValueError("前次修正缺項")
    if m["trend"] in ("多頭趨勢", "空頭趨勢"):
        expected = "long" if m["trend"] == "多頭趨勢" else "short"
        matches = [s for s in m["scenarios"] if s["side"] == expected]
        if not matches and not m.get("skipReason"):
            raise ValueError("缺順勢候選")
        for s in m["scenarios"]:
            if s["side"] != expected and (
                not s.get("counterTrend") or not s["halfSize"]
            ):
                raise ValueError("逆勢須標示且半倉")
    if any(
        q["status"] == "stale" and q["field"] in ("prices", "candles", "live")
        for q in m["dataQuality"]
    ) and m["stance"] not in ("觀望", "減碼"):
        raise ValueError("行情過期，不能給新進場候選")
    for s in m["scenarios"]:
        if s.get("counterTrend") and not s["halfSize"]:
            raise ValueError("逆勢須半倉")
        if not s["halfSize"] and not (
            m.get("globalOiConfirmed") and m.get("globalOiSource")
        ):
            raise ValueError("完整部位須有全市場 OI 依據")
        s.update(
            scenario(s["side"], s["entry"], s["stop"], s["t1"], s["t2"], s["halfSize"])
        )
    if m.get("breakoutAlt"):
        alt = m["breakoutAlt"]
        if alt.get("entry") is not None:
            calc = scenario(
                alt["side"], alt["entry"], alt["stop"], alt["t1"], alt["t2"]
            )
            alt.update(rr1=calc["rr1"], rr2=calc["rr2"])
    if (
        m["trend"] in ("多頭趨勢", "空頭趨勢")
        and m["stance"] == "觀望"
        and not m.get("skipReason")
    ):
        raise ValueError("順勢觀望須說明風報比或不交易條件")
    output = {k: v for k, v in r.items() if k != "sections"}
    output["markdown"] = render(r)
    validate("report", output)
    return output


def check():
    for p in (ROOT / "reports").glob("*.json"):
        if p.stem == "index":
            continue
        d = read(p)
        validate("report", d)
        if d["markdown"] != p.with_suffix(".md").read_text("utf-8"):
            raise ValueError(str(p) + " 與正文不符")
    catalog = read(ROOT / "reports/index.json")
    validate("index", catalog)
    for row in catalog["reports"]:
        doc = read(ROOT / row["path"])
        if (
            row["sortKey"] != doc["sortKey"]
            or row["id"] != doc["date"] + "-" + doc["kind"]
        ):
            raise ValueError("索引與報告不符")
    keys = [row["sortKey"] for row in catalog["reports"]]
    if keys != sorted(set(keys), reverse=True):
        raise ValueError("索引順序或唯一性錯誤")
    validate("live", read(ROOT / "data/live.json"))


def main():
    a = argparse.ArgumentParser()
    a.add_argument("draft", nargs="?")
    a.add_argument("--publish", action="store_true")
    a.add_argument("--all", action="store_true")
    args = a.parse_args()
    if args.all:
        check()
        print("OK 已核對報告與行情")
        return
    if args.draft:
        path = Path(args.draft)
    else:
        path = max((ROOT / ".drafts").glob("*-*.json"), key=lambda p: p.stat().st_mtime)
    d = prepare(read(path))
    if args.publish:
        dest = ROOT / "reports" / (d["date"] + "-" + d["kind"] + ".md")
        if dest.exists() and dest.read_text("utf-8") != d["markdown"]:
            raise ValueError("已有不同正文，保留人工版本")
        dest.write_text(d["markdown"], "utf-8")
        d["markdown"] = dest.read_text("utf-8")
        write(dest.with_suffix(".json"), d)
        subprocess.run([sys.executable, str(ROOT / "tools/build.py")], check=True)
    print("OK " + d["title"])


if __name__ == "__main__":
    main()
