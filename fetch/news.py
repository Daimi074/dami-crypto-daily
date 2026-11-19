from datetime import datetime, timezone


def freshness(latest, now=None):
    if latest is None:
        return "無法讀取"
    now = now or datetime.now(timezone.utc)
    hours = (now - latest).total_seconds() / 3600
    if hours < 0:
        return "時間異常，未採用"
    return "來源過期，未採用" if hours > 24 else "可採用"
