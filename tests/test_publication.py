import contextlib
import io
from pathlib import Path
from unittest import TestCase
from jsonschema import ValidationError
from report.build import read, ROOT, build
from report.migrate import parsed_metrics
from report.validate import check, prepare
from fetch.storage import validate
from datetime import datetime
from calc.technical import TPE


class Publishing(TestCase):
    def test_weekend_holiday(self):
        from datetime import date
        from report.calendar import section

        self.assertIn("準備方案", section(date(2026, 11, 26), "evening"))
        self.assertIn("上週", section(date(2026, 11, 23), "morning"))
        self.assertIn("盤前", section(date(2026, 11, 19), "evening"))

    def test_public_files(self):
        check()

    def test_required_numeric_type(self):
        item = read(ROOT / "reports/2026-11-19-evening.json")
        item["metrics"]["prices"][0]["price"] = "63,000"
        with self.assertRaises(ValidationError):
            validate("report", item)

    def test_incomplete_editorial_draft(self):
        r = build("evening", read(ROOT / "data/live.json"), None, datetime.now(TPE))
        with self.assertRaisesRegex(ValueError, "待寫"):
            prepare(r)

    def test_migration(self):
        d = parsed_metrics(
            "趨勢方向：空頭趨勢。今晚動作：等反彈再空。QQQ 風險開關：關。"
        )
        self.assertEqual(
            (d["trend"], d["stance"], d["qqqSwitch"]), ("空頭趨勢", "偏空", "關")
        )
        self.assertIsNone(parsed_metrics("趨勢未知")["trend"])

    def test_source_failure_isolated(self):
        from fetch import live
        from unittest.mock import patch
        from tempfile import TemporaryDirectory

        snapshot = read(ROOT / "data/live.json")
        with TemporaryDirectory() as tmp:
            dest = Path(tmp) / "live.json"
            with patch("sys.argv", ["live", str(dest)]), patch.object(
                live, "prices", return_value=snapshot["prices"]
            ), patch.object(live, "get", side_effect=OSError("offline")), patch.object(
                live, "post", side_effect=OSError("offline")
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    live.main()
            item = read(dest)
            for field in ("funding", "longShort", "candles", "oi", "fearGreed"):
                self.assertIsNone(item[field])
            self.assertEqual(item["prices"], snapshot["prices"])
            self.assertTrue(item["errors"])
