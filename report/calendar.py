"""NYSE 公布的完整休市日；超出公告期間須另行核對。"""

from datetime import timedelta

SOURCE = "https://www.nyse.com/trade/hours-calendars"
HOLIDAYS = {
    2026: "01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25",
    2027: "01-01 01-18 02-15 03-26 05-31 06-18 07-05 09-06 11-25 12-24",
    2028: "01-17 02-21 04-14 05-29 06-19 07-04 09-04 11-23 12-25",
}


def is_closed(day):
    if day.weekday() >= 5:
        return True
    if day.year not in HOLIDAYS:
        return None
    return day.strftime("%m-%d") in HOLIDAYS[day.year].split()


def section(day, kind):
    if is_closed(day) is None:
        return "交易日曆待核對與事件預告"
    if is_closed(day) or (kind == "morning" and is_closed(day - timedelta(days=1))):
        return (
            "上週美股回顧與本週事件、財報預告"
            if kind == "morning"
            else "下週或下次開盤前的準備方案"
        )
    return (
        "前一交易日收盤、TSM ADR 與昨晚 BTC"
        if kind == "morning"
        else "盤前與自早報以來變化、日間 BTC"
    )
