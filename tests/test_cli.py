import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from test_engine import CSV, META

from market_observatory.__main__ import main


class CliTests(unittest.TestCase):
    def test_import_and_export_all_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "prices.csv").write_text(CSV)
            (root / "source.json").write_text(json.dumps(META))
            for format in ["json", "html", "csv"]:
                path = root / f"report.{format}"
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main(
                        [
                            "report",
                            "--csv",
                            str(root / "prices.csv"),
                            "--metadata",
                            str(root / "source.json"),
                            "--format",
                            format,
                            "--output",
                            str(path),
                        ]
                    )
                self.assertEqual(code, 0)
                self.assertGreater(path.stat().st_size, 100)
            result = json.loads((root / "report.json").read_text())
            self.assertAlmostEqual(result["portfolio"]["total_return"], 0)

    def test_missing_metadata_and_invalid_weights(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            for extra in [
                ["--csv", "missing.csv"],
                ["--weights", "A=1,A=2"],
                ["--weights", "invalid"],
            ]:
                self.assertEqual(
                    main(["report", "--output", str(Path(tmp) / "report.html")] + extra),
                    2,
                )

    def test_source_hash_is_original_bytes_for_newlines_and_bom(self):
        import hashlib

        expected_canonical = None
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = root / "source.json"
            metadata.write_text(json.dumps(META), encoding="utf-8")
            for index, (newline, bom) in enumerate(
                (newline, bom) for newline in ["\n", "\r\n", "\r"] for bom in ["", "\ufeff"]
            ):
                with self.subTest(newline=repr(newline), bom=bool(bom)):
                    raw = (bom + CSV.replace("\n", newline)).encode("utf-8")
                    source = root / f"source-{index}.csv"
                    source.write_bytes(raw)
                    report = root / f"report-{index}.json"
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = main(
                            [
                                "report",
                                "--csv",
                                str(source),
                                "--metadata",
                                str(metadata),
                                "--format",
                                "json",
                                "--output",
                                str(report),
                            ]
                        )
                    self.assertEqual(code, 0)
                    result = json.loads(report.read_text(encoding="utf-8"))
                    self.assertEqual(
                        result["provenance"]["source_sha256"], hashlib.sha256(raw).hexdigest()
                    )
                    canonical = result["provenance"]["data_sha256"]
                    if expected_canonical is None:
                        expected_canonical = canonical
                    self.assertEqual(canonical, expected_canonical)
