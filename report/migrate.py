import re
from pathlib import Path
from report.build import ROOT
from fetch.storage import validate, write


def parsed_metrics(md):
    def labeled(label, choices):
        hit = re.search(label + r"[：:\s*]*(" + choices + r")", md)
        return hit[1] if hit else None

    trend = labeled("趨勢方向", "多頭趨勢|空頭趨勢|盤整")
    action = labeled(
        "(?:今日動作|今晚動作|今日主建議|今晚主建議)",
        "等回測再多|等反彈再空|偏多候選|偏空候選|觀望|減碼風險",
    )
    stance = (
        (
            "偏多"
            if "多" in action
            else "偏空" if "空" in action else "減碼" if "減碼" in action else "觀望"
        )
        if action
        else None
    )
    switch = labeled("QQQ 風險開關", "開|關")
    return dict(
        trend=trend,
        stance=stance,
        action=action,
        qqqSwitch=switch,
        dataQuality=[
            dict(field=k, status="missing", note="歷史原文未解析此欄。")
            for k in (
                "prices",
                "candles",
                "etf",
                "oi",
                "funding",
                "yields",
                "scenarios",
            )
        ]
        + [
            dict(field=k, status="missing", note="歷史正文無明確標示。")
            for k, v in (("trend", trend), ("action", action), ("qqqSwitch", switch))
            if v is None
        ],
    )


def main():
    for src in sorted((ROOT / "import/daily").glob("*.md")):
        match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(-evening)?", src.stem)
        if not match:
            continue
        date = match[1]
        kind = "evening" if match[2] else "morning"
        dest = ROOT / "reports" / (date + "-" + kind + ".md")
        md = src.read_text("utf-8-sig")
        if dest.exists() and dest.read_text("utf-8") != md:
            raise ValueError("版本衝突：" + dest.name)
        if dest.with_suffix(".json").exists():
            continue
        title = md.splitlines()[0].lstrip("# ")
        stamp = re.search(
            r"(?:產出時間|更新時間) *[：:]? *(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+08:00)",
            md,
        )
        from datetime import datetime
        from calc.technical import TPE

        headline = next(
            (
                s.strip()
                for s in md.splitlines()[1:]
                if s.strip() and not s.startswith("#")
            ),
            title,
        )
        r = dict(
            date=date,
            kind=kind,
            title=title,
            headline=headline,
            markdown=md,
            updatedAt=stamp[1] if stamp else datetime.now(TPE).isoformat(),
            sortKey=date + ("-2" if match[2] else "-1"),
            metrics=parsed_metrics(md),
        )
        validate("report", r)
        dest.write_text(md, "utf-8")
        r["markdown"] = dest.read_text("utf-8")
        write(dest.with_suffix(".json"), r)
    from tools.build import main as rebuild

    rebuild()


if __name__ == "__main__":
    main()
