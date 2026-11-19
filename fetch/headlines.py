"""查首頁可辨認的文章時間。被拒絕即停止。"""
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import re
from urllib.request import Request,urlopen
from fetch.news import freshness
from fetch.storage import ROOT,write

SITES={"CoinDesk":"https://www.coindesk.com/","The Block":"https://www.theblock.co/","動區":"https://www.blocktempo.com/","BlockBeats":"https://www.theblockbeats.info/","CryptoPanic":"https://cryptopanic.com/"}

class Times(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="time" and a.get("datetime"): self.values.append(a["datetime"])
        if a.get("itemprop")=="datePublished" and a.get("content"): self.values.append(a["content"])

def inspect(url,now):
    row=dict(src=url,checkedAt=now.isoformat(),asOf=None)
    try:
        with urlopen(Request(url,headers={"User-Agent":"Dami-Daily/2.0"}),timeout=12) as resp:
            body=resp.read(4_000_000).decode("utf-8","replace")
        parser=Times()
        parser.feed(body)
        stamps=[]
        for value in parser.values+re.findall(r'"datePublished"\s*:\s*"([^"]+)"',body):
            try: d=datetime.fromisoformat(value.replace("Z","+00:00"))
            except ValueError: continue
            if d.tzinfo: stamps.append(d)
        latest=max(stamps,default=None)
        row.update(asOf=latest.isoformat() if latest else None,status=freshness(latest,now) if latest else "文章時間未取得，未採用")
    except (ValueError,OSError) as exc:
        row.update(status="無法讀取",error=str(exc))
    return row

if __name__=="__main__":
    from concurrent.futures import ThreadPoolExecutor
    now=datetime.now(timezone.utc)
    with ThreadPoolExecutor(5) as pool:
        rows=list(pool.map(lambda url:inspect(url,now),SITES.values()))
    write(ROOT/".drafts/news.json",dict(zip(SITES,rows)))

