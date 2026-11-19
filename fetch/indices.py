"""美股指數收盤資料，使用 FRED 發布的日資料。"""

import csv
from datetime import date, timedelta
import io
from urllib.request import urlopen
from fetch.storage import ROOT, write

SERIES = {"SPX": "SP500", "NDX": "NASDAQ100", "DJI": "DJIA", "VIX": "VIXCLS"}


def collect(end):
    start = end - timedelta(days=12)
    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?cosd={start}&coed={end}&id="
        + ",".join(SERIES.values())
    )
    with urlopen(url, timeout=25) as response:
        rows = list(csv.DictReader(io.StringIO(response.read().decode("utf-8-sig"))))
    results = []
    for sym, key in SERIES.items():
        values = [
            (r["observation_date"], float(r[key]))
            for r in rows
            if r.get(key) not in (None, "", ".") and r["observation_date"] <= str(end)
        ]
        if len(values) < 2:
            continue
        (prev_date, prev), (day, close) = values[-2:]
        results.append(
            dict(
                sym=sym,
                close=close,
                chg=round(100 * (close / prev - 1), 3),
                asOf=day,
                prevDate=prev_date,
                src="https://fred.stlouisfed.org/series/" + key,
                delay="美東日收盤，FRED 延後發布",
            )
        )
    if not results:
        raise ValueError("FRED 無可用收盤")
    return results


if __name__ == "__main__":
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo

    ny = datetime.now(timezone.utc).astimezone(ZoneInfo("America/New_York"))
    end = ny.date() if ny.hour >= 16 else ny.date() - timedelta(days=1)
    write(ROOT / "data/indices.json", collect(end))
