from math import isfinite

def scenario(side, entry, stop, t1, t2, half=True, mmr=0.005):
    if side not in ("long","short") or not all(isfinite(x) and x>0 for x in (entry,stop,t1,t2)) or not 0<=mmr<0.05:
        raise ValueError("情境輸入無效")
    sign = 1 if side=="long" else -1
    risk = sign*(entry-stop)
    gain1,gain2 = sign*(t1-entry),sign*(t2-entry)
    liquidation = entry*(1-sign*(1/20-mmr))
    if not (0<risk<sign*(entry-liquidation) and 0<gain1<gain2):
        raise ValueError("停損、強平或目標順序不成立")
    nominal = 1000 if half else 2000
    return dict(side=side,entry=entry,stop=stop,t1=t1,t2=t2,halfSize=half,rr1=gain1/risk,rr2=gain2/risk,
                pnlStop=-nominal*risk/entry,pnlT1=nominal*gain1/entry,pnlT2=nominal*gain2/entry,liqPrice=liquidation)

