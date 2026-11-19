import csv
import io
from datetime import date, datetime
from urllib.request import urlopen
from fetch.storage import write

LABELS = ["1 Mo","3 Mo","6 Mo","1 Yr","2 Yr","3 Yr","5 Yr","7 Yr","10 Yr","20 Yr","30 Yr"]
SRC = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/"

def year_rows(year):
    url = f"{SRC}{year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv"
    with urlopen(url,timeout=25) as r:
        rows = csv.DictReader(io.StringIO(r.read().decode("utf-8-sig")))
        return [(datetime.strptime(row["Date"],"%m/%d/%Y").date(),[float(row[k]) if row.get(k) not in ("","N/A",None) else None for k in LABELS]) for row in rows]

def shape(short,long):
    if short==long: return "平行移動" if short else "持平"
    if short>long: return "熊平" if short>0 else "牛平"
    return "牛陡" if short<0 else "熊陡"

def collect(asof=None):
    asof = asof or date.today()
    rows = year_rows(asof.year)
    if sum(d<=asof for d,_ in rows)<90:
        rows += year_rows(asof.year-1)
    rows = sorted((d,v) for d,v in rows if d<=asof and v[4] is not None and v[8] is not None)[-90:]
    if len(rows)<22: raise ValueError("有效交易日不足")
    day,now = rows[-1]
    def change(n):
        prev=rows[-1-n][1]
        s,l = round((now[4]-prev[4])*100,3), round((now[8]-prev[8])*100,3)
        return dict(shortBp=s,longBp=l,spreadBp=round(l-s,3),shape=shape(s,l))
    return dict(src=SRC,asOf=day.isoformat(),delay="美東官方日值",dates=[str(d) for d,_ in rows],
                **{k:[v[i] for _,v in rows] for k,i in [("y3m",1),("y2",4),("y10",8),("y30",10)]},
                spread=round((now[8]-now[4])*100,3),daily=change(1),monthly=change(21),
                curve=dict(labels=["1M","3M","6M","1Y","2Y","3Y","5Y","7Y","10Y","20Y","30Y"],now=now,ago=rows[-22][1],agoDate=str(rows[-22][0])))

if __name__=="__main__":
    write("data/yields.json",collect())

