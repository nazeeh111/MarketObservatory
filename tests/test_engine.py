import math
import unittest

from market_observatory.engine import ValidationError, analyze, parse_csv

META = {
    "title": "Known prices",
    "source": "test fixture",
    "as_of": "2024-01-03",
    "price_basis": "adjusted",
}
CSV = "date,symbol,close\n2024-01-01,A,100\n2024-01-02,A,110\n2024-01-03,A,99\n2024-01-01,B,100\n2024-01-02,B,90\n2024-01-03,B,99\n"


class EngineTests(unittest.TestCase):
    def test_known_asset_metrics(self):
        r = analyze(parse_csv(CSV, META))
        a = r["assets"][0]
        self.assertAlmostEqual(a["total_return"], -0.01)
        self.assertAlmostEqual(a["max_drawdown"], -0.1)
        self.assertAlmostEqual(a["annualized_volatility"], math.sqrt(0.02) * math.sqrt(252))
        self.assertAlmostEqual(r["correlation"][0][1], -1)
        self.assertAlmostEqual(r["portfolio"]["total_return"], 0)

    def test_buy_hold_differs_from_rebalanced(self):
        data = parse_csv(CSV, META)
        a = analyze(data, mode="buy_hold")
        b = analyze(data, mode="rebalance")
        self.assertAlmostEqual(a["portfolio"]["total_return"], -0.01)
        self.assertAlmostEqual(b["portfolio"]["total_return"], 0)

    def test_weights_and_value(self):
        r = analyze(parse_csv(CSV, META), weights={"A": 1, "B": 0}, initial_value=200)
        self.assertAlmostEqual(r["series"]["portfolio_value"][-1], 198)

    def test_alignment_has_no_fill(self):
        csv = CSV + "2024-01-04,A,200\n"
        r = analyze(parse_csv(csv, {**META, "as_of": "2024-01-04"}))
        self.assertEqual(r["coverage"][0]["excluded"], 1)
        self.assertEqual(r["dates"], ["2024-01-01", "2024-01-02", "2024-01-03"])

    def test_hash_order_invariant(self):
        lines = CSV.splitlines()
        a = parse_csv(CSV, META)
        b = parse_csv("\n".join([lines[0]] + list(reversed(lines[1:]))), META)
        self.assertEqual(a["data_sha256"], b["data_sha256"])
        self.assertNotEqual(a["source_sha256"], b["source_sha256"])

    def test_constant_correlation_is_undefined(self):
        r = analyze(parse_csv(CSV.replace("110", "100").replace(",A,99", ",A,100"), META))
        self.assertIsNone(r["correlation"][0][0])

    def test_reject_bad_rows(self):
        for value in ["nan", "inf", "-1", "0", "1e300", "", "x"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_csv(CSV.replace(",A,110", ",A," + value), META)

    def test_reject_dates_duplicates_schema(self):
        for value in [
            CSV + "2024-01-01,A,100\n",
            CSV.replace("2024-01-01", "2024-02-30"),
            CSV.replace("close", "price"),
            CSV.replace("date,symbol,close", "date,symbol,close,extra"),
            CSV.replace(",A,", ",=A,"),
        ]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_csv(value, META)

    def test_missing_intersection(self):
        with self.assertRaises(ValidationError):
            analyze(
                parse_csv(
                    CSV.replace("2024-01-03,B", "2024-01-04,B"),
                    {**META, "as_of": "2024-01-04"},
                )
            )

    def test_invalid_settings(self):
        data = parse_csv(CSV, META)
        for kwargs in [
            {"weights": {"A": -1, "B": 2}},
            {"weights": {"A": 0, "B": 0}},
            {"periods_per_year": 0},
            {"initial_value": float("inf")},
            {"mode": "magic"},
            {"mode": []},
            {"mode": {}},
            {"symbols": ["A", "A"]},
            {"symbols": ["NO"]},
            {"weights": {"A": 1}},
            {"periods_per_year": True},
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                analyze(data, **kwargs)

    def test_asof_cannot_precede_data(self):
        with self.assertRaises(ValidationError):
            parse_csv(CSV, {**META, "as_of": "2023-12-31"})

    def test_max_assets_bound(self):
        csv = "date,symbol,close\n" + "".join(f"2024-01-01,A{i},1\n" for i in range(17))
        with self.assertRaises(ValidationError):
            parse_csv(csv, META)

    def test_all_outputs_json_finite(self):
        import json

        json.dumps(analyze(parse_csv(CSV, META)), allow_nan=False)


if __name__ == "__main__":
    unittest.main()


class AdditionalMathTests(unittest.TestCase):
    def test_frequency_only_changes_volatility(self):
        d = parse_csv(CSV, META)
        a = analyze(d, periods_per_year=1)
        b = analyze(d, periods_per_year=252)
        self.assertAlmostEqual(
            b["assets"][0]["annualized_volatility"] / a["assets"][0]["annualized_volatility"],
            math.sqrt(252),
        )
        self.assertEqual(a["series"], b["series"])

    def test_weight_scaling_invariant(self):
        d = parse_csv(CSV, META)
        a = analyze(d, weights={"A": 2, "B": 3})
        b = analyze(d, weights={"A": 20, "B": 30})
        self.assertEqual(a["series"], b["series"])

    def test_selection_removes_other_asset_alignment(self):
        d = parse_csv(CSV + "2024-01-04,A,111\n", {**META, "as_of": "2024-01-04"})
        r = analyze(d, symbols=["A"])
        self.assertEqual(len(r["dates"]), 4)

    def test_buy_hold_terminal_drift(self):
        d = parse_csv(CSV.replace(",A,99", ",A,121").replace(",B,99", ",B,81"), META)
        r = analyze(d, mode="buy_hold")
        self.assertAlmostEqual(r["portfolio"]["terminal_weights"]["A"], 121 / 202)
        self.assertAlmostEqual(sum(r["portfolio"]["terminal_weights"].values()), 1)

    def test_cagr_calendar_days(self):
        text = "date,symbol,close\n2024-01-01,A,100\n2024-06-01,A,110\n2025-01-01,A,121\n"
        r = analyze(parse_csv(text, {**META, "as_of": "2025-01-01"}))
        self.assertAlmostEqual(r["assets"][0]["cagr"], 1.21 ** (365.25 / 366) - 1)

    def test_extreme_cagr_is_null(self):
        text = CSV.replace(",A,100", ",A,0.000000001").replace(",A,99", ",A,1000000000000")
        r = analyze(parse_csv(text, META), symbols=["A"], mode="buy_hold")
        self.assertIsNone(r["assets"][0]["cagr"])

    def test_timestamp_not_silently_truncated(self):
        with self.assertRaises(ValidationError):
            parse_csv(CSV.replace("2024-01-01", "2024-01-01T00:00:00Z"), META)

    def test_empty_and_oversized_input(self):
        from unittest.mock import patch

        with self.assertRaises(ValidationError):
            parse_csv("date,symbol,close\n", META)
        with (
            patch("market_observatory.engine.MAX_BYTES", 10),
            self.assertRaises(ValidationError),
        ):
            parse_csv(CSV, META)
        with (
            patch("market_observatory.engine.MAX_ROWS", 2),
            self.assertRaises(ValidationError),
        ):
            parse_csv(CSV, META)


class ReviewRegressionTests(unittest.TestCase):
    def test_single_asset_rebalancing_preserves_extreme_positive_ratios(self):
        for first in [10_000_000, 1_000_000_000_000]:
            with self.subTest(first=first):
                text = (
                    "date,symbol,close\n"
                    f"2024-01-01,A,{first}\n"
                    "2024-01-02,A,0.000000001\n"
                    f"2024-01-03,A,{first}\n"
                )
                dataset = parse_csv(text, META)
                rebalanced = analyze(dataset, mode="rebalance")
                held = analyze(dataset, mode="buy_hold")
                for actual, expected in zip(
                    rebalanced["series"]["portfolio_growth"],
                    held["series"]["portfolio_growth"],
                ):
                    self.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=0))
                self.assertAlmostEqual(rebalanced["portfolio"]["total_return"], 0)
