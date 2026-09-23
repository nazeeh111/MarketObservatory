import json
import tempfile
import unittest
from pathlib import Path

from test_engine import CSV, META

from market_observatory.delivery import (
    csv_report,
    demo_dataset,
    html_report,
    write_report,
)
from market_observatory.engine import analyze, parse_csv


class DeliveryTests(unittest.TestCase):
    def test_demo_is_labeled_and_complete(self):
        data = demo_dataset()
        self.assertEqual(data["metadata"]["price_basis"], "synthetic")
        r = analyze(data)
        self.assertEqual(len(r["assets"]), 4)
        self.assertEqual(len(r["dates"]), 300)

    def test_exports_escape_untrusted_metadata(self):
        data = parse_csv(CSV, {**META, "title": "<script>alert(1)</script>"})
        r = analyze(data)
        self.assertIn("&lt;script&gt;", html_report(r))
        self.assertNotIn("<script>alert", html_report(r))
        self.assertEqual(len(csv_report(r).splitlines()), 4)

    def test_write_refuses_overwrite(self):
        r = analyze(parse_csv(CSV, META))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            write_report(r, path, "json")
            self.assertEqual(json.loads(path.read_text())["schema_version"], 1)
            with self.assertRaises(FileExistsError):
                write_report(r, path, "json")
