from report.build import FIXED

def number(x):
    return f"{x:,.2f}" if isinstance(x,(float,int)) else "未取得"

def table(head, rows):
    return "\n".join(["| "+" | ".join(head)+" |","|"+"---|"*len(head)]+["| "+" | ".join(map(str,row))+" |" for row in rows])

def render(r):
    m=r["metrics"]
    out=["# "+r["title"],"產出 "+r["updatedAt"]+"；行情截點 "+r["marketAsOf"]+"（台北）。交易所為公開快照，傳輸延遲未知。"]
    cor=m["correction"]
    out.append("⚠ 前次判讀修正\n\n"+" → ".join(cor[k] for k in ("previous","newData","revised")) if cor else "不需前次判讀修正")
    out.extend(["## 一句話結論",r["headline"],"趨勢方向："+str(m["trend"] or "資料不足"),("今晚" if r["kind"]=="evening" else "今日")+"動作："+m["action"]+"。QQQ 風險開關："+str(m["qqqSwitch"] or "未取得"),"## 行情快照",
        table(["標的","價格","24h %","低／高","來源與時間"],[(p["sym"],number(p["price"]),number(p["chg24h"]),number(p["low"])+"／"+number(p["high"]),p["src"]+" "+p["asOf"]) for p in m["prices"]]),
        "恐懼貪婪："+str(m["fearGreed"] if m["fearGreed"] is not None else "未取得")+"（alternative.me，日資料）。"])
    if m.get("indicators"):
        ind=m["indicators"]
        out.append("自行計算，最後收盤／EMA20／EMA50："+ "／".join(number(x) for x in [m["candles"]["c"][-1],ind["ema20"][-1],ind["ema50"][-1]])+"。")
        out.append(table(["4H 分段（台北）","低／高","均量 BTC","期末 EMA20／50","布林下／上","事件依據"],[(p["from"]+" 至 "+p["to"],number(p["low"])+"／"+number(p["high"]),number(p["volume"]),number(p["ema20"])+"／"+number(p["ema50"]),number(p["bbLower"])+"／"+number(p["bbUpper"]),p["why"]) for p in m["klineStory"]["phases"]]))
    y=m.get("yields")
    if y:
        out.append("美國財政部，美東 "+y["asOf"]+"。2Y／10Y "+number(y["y2"][-1])+"%／"+number(y["y10"][-1])+"%，利差 "+number(y["spread"])+" bp。"+ " ".join(label+"短端／長端／利差變化 "+"／".join(number(y[key][k]) for k in ("shortBp","longBp","spreadBp"))+" bp（"+y[key]["shape"]+"）。" for key,label in [("daily","一日"),("monthly","約一月")]))
    for key,value in r["sections"].items(): out.extend(["## "+key,value])
    out.append("## 情境試算")
    out.append(table(["方向","成立條件","名目 USDT","進場／停損","T1／T2","風報比","損益 SL／T1／T2","粗估強平","失效"],[(s["name"],s["trigger"],1000 if s["halfSize"] else 2000,number(s["entry"])+"／"+number(s["stop"]),number(s["t1"])+"／"+number(s["t2"]),number(s["rr1"])+"／"+number(s["rr2"]),"／".join(number(s[k]) for k in ("pnlStop","pnlT1","pnlT2")),number(s["liqPrice"]),s["invalid"]) for s in m["scenarios"]]+[("盤整","區間內不交易","—","—","—","—","—","—","離開區間後重判")]))
    out.extend(["不交易條件："+"；".join(m["noTrade"])+"。","20 倍約 5% 反向波動就可能強平。試算假設維持保證金率 0.5%，未計手續費、資金費、滑價及交易所實際強平規則。",*FIXED])
    return "\n\n".join(out)+"\n"

