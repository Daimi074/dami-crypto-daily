import argparse
import subprocess
import sys
from math import isclose
from pathlib import Path
from calc.risk import scenario
from calc.technical import structure
from fetch.storage import ROOT, validate, write
from report.build import read, COMMON
from report.render import render

def prepare(r):
    m=r["metrics"]
    missing=[k for k in COMMON if not r["sections"].get(k,"").strip()]
    if missing or not all(v.strip() for v in r["sections"].values()):
        raise ValueError("仍有待寫欄位："+str(missing))
    if not m["action"] or not m["stance"]: raise ValueError("缺動作或立場")
    if bool(m["correction"])!=r["headline"].startswith("【修正】"): raise ValueError("修正標記不一致")
    if m.get("candles"):
        if m["candles"]["lastOpen"] or m["trend"]!=structure(m["candles"])[0]: raise ValueError("趨勢與已收盤 K 線不符")
    if m["trend"] in ("多頭趨勢","空頭趨勢") and not m["scenarios"] and not m.get("skipReason"):
        raise ValueError("順勢候選缺漏，須記錄風報比或不交易條件")
    if (m.get("breakoutAlt") or {}).get("triggered") and not (m.get("globalOiConfirmed") and m.get("globalOiSource")):
        raise ValueError("全市場 OI 未證實，不能觸發突破候選")
    for s in m["scenarios"]:
        if s.get("counterTrend") and not s["halfSize"]: raise ValueError("逆勢須半倉")
        s.update(scenario(s["side"],s["entry"],s["stop"],s["t1"],s["t2"],s["halfSize"]))
    output={k:v for k,v in r.items() if k!="sections"}
    output["markdown"]=render(r)
    validate("report",output)
    return output

def check():
    for p in (ROOT/"reports").glob("*.json"):
        if p.stem=="index": continue
        d=read(p)
        validate("report",d)
        if d["markdown"]!=p.with_suffix(".md").read_text("utf-8"): raise ValueError(str(p)+" 與正文不符")
    validate("live",read(ROOT/"data/live.json"))

def main():
    a=argparse.ArgumentParser()
    a.add_argument("draft",nargs="?")
    a.add_argument("--publish",action="store_true")
    a.add_argument("--all",action="store_true")
    args=a.parse_args()
    if args.all: check(); print("OK 已核對報告與行情"); return
    if args.draft: path=Path(args.draft)
    else: path=max((ROOT/".drafts").glob("*-*.json"),key=lambda p:p.stat().st_mtime)
    d=prepare(read(path))
    if args.publish:
        dest=ROOT/"reports"/(d["date"]+"-"+d["kind"]+".md")
        if dest.exists() and dest.read_text("utf-8")!=d["markdown"]: raise ValueError("已有不同正文，保留人工版本")
        dest.write_text(d["markdown"],"utf-8")
        d["markdown"]=dest.read_text("utf-8")
        write(dest.with_suffix(".json"),d)
        subprocess.run([sys.executable,str(ROOT/"tools/build.py")],check=True)
    print("OK "+d["title"])

if __name__=="__main__": main()

