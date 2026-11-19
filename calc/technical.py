from statistics import mean, pstdev
from datetime import datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, TPE).isoformat(timespec="seconds")


def ema(values, period):
    alpha = 2 / (period + 1)
    result = []
    for value in values:
        result.append(value if not result else alpha * value + (1 - alpha) * result[-1])
    return result


def indicators(values):
    upper, mid, lower, rsi = [], [], [], []
    gain = loss = 0
    for i, value in enumerate(values):
        window = values[max(0, i - 19) : i + 1]
        center = mean(window)
        width = 2 * pstdev(window)
        for series, point in [
            (upper, center + width),
            (mid, center),
            (lower, center - width),
        ]:
            series.append(point if len(window) == 20 else None)
        change = value - values[i - 1] if i else 0
        up, down = max(change, 0), max(-change, 0)
        if i <= 14:
            gain += up / 14
            loss += down / 14
        else:
            gain = (13 * gain + up) / 14
            loss = (13 * loss + down) / 14
        rsi.append(
            None if i < 14 else 100 * gain / (gain + loss) if gain + loss else 50
        )
    return dict(
        ema20=ema(values, 20),
        ema50=ema(values, 50),
        bbUpper=upper,
        bbMid=mid,
        bbLower=lower,
        rsi14=rsi,
    )


def structure(c):
    if len({len(c[k]) for k in "tohlcv"}) != 1:
        raise ValueError("K 線時間與價量筆數不符")
    if len(c["t"]) < 90 or any(b - a != 14400000 for a, b in zip(c["t"], c["t"][1:])):
        raise ValueError("4H K 線不足或不連續")
    ind = indicators(c["c"])
    phases = []
    for start in range(len(c["t"]) - 90, len(c["t"]), 18):
        end = start + 17
        phases.append(
            {
                "from": iso(c["t"][start]),
                "to": iso(c["t"][end] + 14400000),
                "low": min(c["l"][start : end + 1]),
                "high": max(c["h"][start : end + 1]),
                "volume": mean(c["v"][start : end + 1]),
                "close": c["c"][end],
                **{k: v[end] for k, v in ind.items() if k != "rsi14"},
            }
        )
    close, e20, e50 = c["c"][-1], ind["ema20"][-1], ind["ema50"][-1]
    for sign, label in [(1, "多頭趨勢"), (-1, "空頭趨勢")]:
        if sign * close > sign * e20 > sign * e50 and all(
            sign * a[k] < sign * b[k]
            for a, b in zip(phases, phases[1:])
            for k in ("low", "high")
        ):
            return label, ind, phases
    return "盤整", ind, phases
