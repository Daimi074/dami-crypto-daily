import unittest
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from calc.technical import indicators, structure
from calc.risk import scenario
from fetch.news import freshness
from fetch.live import closed, LiqAcc, parse_okx_oi_hist, parse_taker, parse_hl, safe
from fetch.treasury import shape


class Indicators(unittest.TestCase):
    def test_indicators(self):
        for period in (20, 50):
            values = [100] * 55 + [110]
            self.assertAlmostEqual(
                indicators(values)["ema" + str(period)][-1],
                100 + 20 / (period + 1),
                places=8,
            )
        d = indicators(list(range(1, 91)))
        self.assertAlmostEqual(d["bbUpper"][19], 22.0325625947, places=7)
        self.assertAlmostEqual(d["bbLower"][19], -1.0325625947, places=7)
        self.assertEqual(d["rsi14"][-1], 100)
        self.assertEqual(indicators([10, 11, 10] * 5)["rsi14"][14], 50)

    def test_closed(self):
        self.assertEqual(closed([[0] * 6 + [10], [0] * 6 + [11]], 10), [[0] * 6 + [10]])

    def test_trends(self):
        for sign, label in [(1, "多頭趨勢"), (-1, "空頭趨勢"), (0, "盤整")]:
            x = [200 + i * sign for i in range(120)]
            c = dict(
                c=x,
                o=x,
                h=[p + 1 for p in x],
                l=[p - 1 for p in x],
                v=[1] * 120,
                t=[i * 14400000 for i in range(120)],
            )
            self.assertEqual(structure(c)[0], label)
            if sign == -1:
                c["l"][-18:] = [102] * 18
                self.assertEqual(structure(c)[0], "盤整")

    def test_position(self):
        s = scenario("short", 64200, 65100, 62100, 60000)
        for k, v in [("pnlStop", -14.0), ("pnlT1", 32.7), ("pnlT2", 65.4)]:
            self.assertEqual(round(s[k], 1), v)
        self.assertEqual(round(s["rr1"], 2), 2.33)
        self.assertEqual(round(s["rr2"], 2), 4.67)
        with self.assertRaises(ValueError):
            scenario("long", 100, 94, 105, 110)

    def test_curves(self):
        for a, b, label in [
            (3, -8, "熊平"),
            (1, 4, "熊陡"),
            (-4, -1, "牛陡"),
            (-1, -4, "牛平"),
        ]:
            self.assertEqual(shape(a, b), label)

    def test_derivatives(self):
        acc = LiqAcc(100, 2)
        self.assertFalse(
            acc.add(
                [
                    dict(ts=t, side=s, sz=1, bkPx=p)
                    for t, s, p in [
                        (105, "sell", 10),
                        (100, "buy", 12),
                        (99, "sell", 15),
                    ]
                ]
            )
        )
        self.assertEqual((acc.long_usd, acc.short_usd), (20, 24))
        self.assertEqual(
            parse_okx_oi_hist(
                [[24 * 3600000, 2e9]]
                + [[i * 3600000, 1e9] for i in reversed(range(24))]
            ),
            (2, 100),
        )
        self.assertEqual(
            parse_hl(
                {"universe": [{"name": "BTC"}]},
                [{"openInterest": 100, "markPx": 10000}],
                ["BTC"],
            ),
            {"BTC": 0.001},
        )
        self.assertEqual(parse_taker([[0, 2e6, 4e6]])["ratio"], 2)

    def test_news(self):
        now = datetime.now(timezone.utc)
        self.assertEqual(freshness(now - timedelta(hours=25), now), "來源過期，未採用")
        self.assertEqual(freshness(now - timedelta(hours=24), now), "可採用")

    def test_failure_preserves_file(self):
        from fetch import live

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live.json"
            path.write_text("previous")
            with patch.object(
                live, "get", side_effect=OSError("offline")
            ), patch.object(live, "post", side_effect=OSError("offline")), patch(
                "sys.argv", ["live", str(path)]
            ):
                with self.assertRaises(SystemExit):
                    live.main()
            self.assertEqual(path.read_text(), "previous")
        errors = []
        self.assertIsNone(safe(lambda: 1 / 0, errors, "funding"))
        self.assertIn("funding", errors[0])
