#!/usr/bin/env python3
"""重建 GitHub Pages 用的檔案。

讀 data/reports/*.json（每份報告一個檔），產生：
- data/index.json：報告清單與趨勢圖需要的精簡數據
- reports/<id>.md：每份報告的 Markdown 全文
- index.html：把 src/page.html 包成完整網頁
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIGHT = ("trend","action","stance", "qqqSwitch", "prices", "fearGreed", "etf")

def main():
    entries = []
    sources = {p.stem:p for p in (ROOT/"data/reports").glob("*.json")}
    sources.update({p.stem:p for p in (ROOT/"reports").glob("*.json") if p.stem!="index"})
    for f in sources.values():
        d = json.loads(f.read_text(encoding="utf-8"))
        rid = f.stem
        m = d.get("metrics") or {}
        entries.append({
            "id": rid, "path": f.relative_to(ROOT).as_posix(), "date": d.get("date"), "kind": d.get("kind"),
            "sortKey": d.get("sortKey"), "title": d.get("title"),
            "headline": d.get("headline"), "updatedAt": d.get("updatedAt"),
            "metrics": {k: m[k] for k in LIGHT if k in m},
        })
        md=ROOT/"reports"/(rid+".md")
        if md.exists() and md.read_text("utf-8")!=d.get("markdown"):
            d["markdown"]=md.read_text("utf-8")
            f.write_text(json.dumps(d,ensure_ascii=False),"utf-8")
    entries.sort(key=lambda e: e.get("sortKey") or "", reverse=True)
    (ROOT / "data" / "index.json").write_text(
        json.dumps({"reports": entries}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (ROOT/"reports/index.json").write_bytes((ROOT/"data/index.json").read_bytes())
    page = (ROOT / "src" / "page.html").read_text(encoding="utf-8")
    (ROOT / "index.html").write_text(
        '<!doctype html>\n<html lang="zh-Hant"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '</head><body>\n' + page + '\n</body></html>\n', encoding="utf-8")
    print(f"{len(entries)} reports")

if __name__ == "__main__":
    main()
