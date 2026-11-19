import re
from pathlib import Path
from report.build import ROOT
from fetch.storage import validate,write

def main():
    for src in sorted((ROOT/"import/daily").glob("*.md")):
        match=re.fullmatch(r"(\d{4}-\d{2}-\d{2})(-evening)?",src.stem)
        if not match: continue
        date=match[1]
        kind="evening" if match[2] else "morning"
        dest=ROOT/"reports"/(date+"-"+kind+".md")
        md=src.read_text("utf-8-sig")
        if dest.exists() and dest.read_text("utf-8")!=md: raise ValueError("版本衝突："+dest.name)
        if dest.with_suffix(".json").exists(): continue
        title=md.splitlines()[0].lstrip("# ")
        stamp=re.search(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+08:00",md)
        from datetime import datetime
        from calc.technical import TPE
        headline=next((s.strip() for s in md.splitlines()[1:] if s.strip() and not s.startswith("#")),title)
        r=dict(date=date,kind=kind,title=title,headline=headline,markdown=md,updatedAt=stamp[0] if stamp else datetime.now(TPE).isoformat(),
            sortKey=date+("-2" if match[2] else "-1"),metrics=dict(trend=None,stance=None,action=None,qqqSwitch=None,
            dataQuality=[dict(field="legacy",status="partial",note="歷史原文；無法核實的數值留空。無明確更新時間時標記轉檔時間。")]))
        validate("report",r)
        dest.write_text(md,"utf-8")
        r["markdown"]=dest.read_text("utf-8")
        write(dest.with_suffix(".json"),r)
    from tools.build import main as rebuild
    rebuild()

if __name__=="__main__": main()

