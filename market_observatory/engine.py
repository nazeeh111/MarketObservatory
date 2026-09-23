"""Validated datasets and transparent historical analytics. No network access."""

import csv
import hashlib
import io
import math
import re
import statistics
from datetime import date

from . import __version__

MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 100_000
MAX_SYMBOLS = 16


class ValidationError(ValueError):
    """An actionable error in a dataset or analysis setting."""


def number(value, label, minimum, maximum):
    if isinstance(value, bool):
        raise ValidationError(f"{label} must be a number, not a boolean.")
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError):
        raise ValidationError(f"{label} must be numeric.") from None
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValidationError(f"{label} must be finite and between {minimum:g} and {maximum:g}.")
    return result


def iso_date(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValidationError(f"{label} must use YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError(f"{label} is not a valid calendar date.") from None


def parse_csv(text, metadata):
    """Parse long-format CSV; return canonical series and provenance."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_BYTES:
        raise ValidationError("CSV must be UTF-8 text of at most 8 MiB.")
    if not isinstance(metadata, dict):
        raise ValidationError("Dataset metadata must be an object.")
    meta = {}
    for field, limit in [
        ("title", 120),
        ("source", 300),
        ("as_of", 10),
        ("price_basis", 30),
        ("notes", 2000),
    ]:
        value = metadata.get(field, "")
        if (
            not isinstance(value, str)
            or len(value) > limit
            or any(ord(c) < 32 and c not in "\n\t" for c in value)
        ):
            raise ValidationError(f"{field} must be text of at most {limit} characters.")
        meta[field] = value.strip()
    if not meta["title"] or not meta["source"]:
        raise ValidationError("A dataset title and source are required.")
    as_of = iso_date(meta["as_of"], "As-of date")
    if meta["price_basis"] not in {"adjusted", "unadjusted", "unknown", "synthetic"}:
        raise ValidationError("Price basis must be adjusted, unadjusted, unknown, or synthetic.")
    series = {}
    count = 0
    try:
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff"), newline=""), strict=True)
        if reader.fieldnames != ["date", "symbol", "close"]:
            raise ValidationError("CSV header must be exactly date,symbol,close in that order.")
        for line, row in enumerate(reader, 2):
            count += 1
            if count > MAX_ROWS:
                raise ValidationError("CSV exceeds 100,000 observations.")
            if set(row) != {"date", "symbol", "close"} or any(v is None for v in row.values()):
                raise ValidationError(f"Row {line}: exactly three fields are required.")
            day = row["date"].strip()
            observed = iso_date(day, f"Row {line} date")
            if observed > as_of:
                raise ValidationError(
                    f"Row {line}: observation date is later than the dataset as-of date."
                )
            symbol = row["symbol"].strip()
            if not re.fullmatch(r"[A-Z][A-Z0-9._-]{0,15}", symbol):
                raise ValidationError(
                    f"Row {line}: symbol must start with A-Z and contain at most 16 uppercase letters, digits, dots, underscores or hyphens."
                )
            price = number(row["close"], f"Row {line} close", 1e-9, 1e12)
            values = series.setdefault(symbol, {})
            if len(series) > MAX_SYMBOLS:
                raise ValidationError("CSV exceeds 16 assets.")
            if day in values:
                raise ValidationError(f"Row {line}: duplicate observation for {symbol} on {day}.")
            values[day] = price
    except csv.Error as error:
        raise ValidationError(f"Malformed CSV: {error}") from None
    if not series:
        raise ValidationError("CSV contains no observations.")
    canonical = "\n".join(
        f"{d},{s},{series[s][d]:.17g}" for s in sorted(series) for d in sorted(series[s])
    )
    return {
        "metadata": meta,
        "prices": series,
        "observations": count,
        "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "data_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }


def _returns(values):
    return [values[i] / values[i - 1] - 1 for i in range(1, len(values))]


def _drawdown(values):
    peak = values[0]
    result = []
    for value in values:
        peak = max(value, peak)
        result.append(value / peak - 1)
    return result


def _metrics(values, dates, periods):
    returns = _returns(values)
    days = (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days
    exponent = math.log(values[-1] / values[0]) * 365.25 / days
    # Very short, extreme samples can overflow annual extrapolation. Null is explicit.
    cagr = math.expm1(exponent) if exponent < 700 else None
    return {
        "total_return": values[-1] / values[0] - 1,
        "cagr": cagr,
        "annualized_volatility": statistics.stdev(returns) * math.sqrt(periods),
        "max_drawdown": min(_drawdown(values)),
        "best_period": max(returns),
        "worst_period": min(returns),
        "positive_period_fraction": sum(x > 0 for x in returns) / len(returns),
    }


def _correlation(left, right):
    lm, rm = statistics.mean(left), statistics.mean(right)
    ld = [x - lm for x in left]
    rd = [x - rm for x in right]
    denom = math.sqrt(math.fsum(x * x for x in ld) * math.fsum(y * y for y in rd))
    return (
        max(-1.0, min(1.0, math.fsum(x * y for x, y in zip(ld, rd)) / denom)) if denom > 0 else None
    )


def analyze(
    dataset,
    symbols=None,
    weights=None,
    mode="rebalance",
    periods_per_year=252,
    initial_value=10_000,
):
    """Compare assets on exact common dates. Weights are long-only and normalized."""
    prices = dataset["prices"]
    symbols = sorted(prices) if symbols is None else symbols
    if not isinstance(symbols, list) or not symbols or any(not isinstance(s, str) for s in symbols):
        raise ValidationError("Select at least one asset.")
    if (
        len(symbols) > 16
        or len(set(symbols)) != len(symbols)
        or any(s not in prices for s in symbols)
    ):
        raise ValidationError("Select 1–16 unique assets present in the dataset.")
    periods = number(periods_per_year, "Periods per year", 1, 366)
    initial = number(initial_value, "Starting value", 1e-6, 1e12)
    if not isinstance(mode, str) or mode not in {"rebalance", "buy_hold"}:
        raise ValidationError("Portfolio mode must be rebalance or buy_hold.")
    if weights is None:
        weights = dict.fromkeys(symbols, 1)
    if not isinstance(weights, dict) or set(weights) != set(symbols):
        raise ValidationError("Provide exactly one weight for each selected asset.")
    weights = {s: number(weights[s], f"{s} weight", 0, 1e9) for s in symbols}
    total = math.fsum(weights.values())
    if total <= 0:
        raise ValidationError("At least one weight must be positive.")
    weights = {s: w / total for s, w in weights.items()}
    common = set(prices[symbols[0]])
    for symbol in symbols[1:]:
        common.intersection_update(prices[symbol])
    dates = sorted(common)
    if len(dates) < 3:
        raise ValidationError(
            "At least three common dates are required. No missing prices are filled."
        )
    if len(dates) > 20_000:
        raise ValidationError("Analysis is limited to 20,000 common observations.")
    values = {s: [prices[s][d] for d in dates] for s in symbols}
    returns = {s: _returns(values[s]) for s in symbols}
    growth = {s: [p / values[s][0] for p in values[s]] for s in symbols}
    portfolio_growth = [1.0]
    if mode == "buy_hold":
        portfolio_growth = [
            math.fsum(weights[s] * growth[s][i] for s in symbols) for i in range(len(dates))
        ]
    else:
        for i in range(len(dates) - 1):
            # Compute gross ratios directly: (ratio - 1) + 1 loses tiny positive
            # ratios to cancellation and can invent gains after a large rebound.
            gross = math.fsum(weights[s] * (values[s][i + 1] / values[s][i]) for s in symbols)
            value = portfolio_growth[-1] * gross
            if not math.isfinite(value) or not 1e-100 <= value <= 1e100:
                raise ValidationError(
                    "Portfolio growth exceeds supported numeric range. Inspect prices for unit changes or data errors."
                )
            portfolio_growth.append(value)
    # Both modes report post-rebalance terminal allocation (buy-and-hold drifts).
    terminal_weights = (
        weights.copy()
        if mode == "rebalance"
        else {s: weights[s] * growth[s][-1] / portfolio_growth[-1] for s in symbols}
    )
    coverage = [
        {
            "symbol": s,
            "available": len(prices[s]),
            "retained": len(dates),
            "excluded": len(prices[s]) - len(dates),
        }
        for s in symbols
    ]
    gaps = [
        (date.fromisoformat(dates[i]) - date.fromisoformat(dates[i - 1])).days
        for i in range(1, len(dates))
    ]
    warnings = [
        "Historical price analysis only. No forecast, recommendation, fees, taxes or transaction costs.",
        "Returns use exact shared observation dates; gaps are not filled. Volatility annualization assumes equally spaced periods at the selected frequency.",
        "CAGR extrapolates using elapsed calendar days and is unstable over short samples.",
    ]
    if any(c["excluded"] for c in coverage):
        warnings.append("Some observations were excluded to align the selected assets.")
    if max(gaps) > 4:
        warnings.append(
            "Shared dates contain gaps longer than four calendar days. Check the frequency assumption before interpreting annualized volatility."
        )
    if dataset["metadata"]["price_basis"] == "unadjusted":
        warnings.append(
            "Unadjusted prices may contain splits and omit dividends. These are price returns, not total investment returns."
        )
    if dataset["metadata"]["price_basis"] == "synthetic":
        warnings.append(
            "This dataset is synthetic. Symbols and results do not describe real investments."
        )
    return {
        "schema_version": 1,
        "engine_version": __version__,
        "metadata": dataset["metadata"],
        "provenance": {k: dataset[k] for k in ["source_sha256", "data_sha256", "observations"]},
        "settings": {
            "symbols": symbols,
            "weights": weights,
            "mode": mode,
            "periods_per_year": periods,
            "initial_value": initial,
        },
        "dates": dates,
        "coverage": coverage,
        "max_calendar_gap_days": max(gaps),
        "assets": [{"symbol": s, **_metrics(values[s], dates, periods)} for s in symbols],
        "correlation": [[_correlation(returns[a], returns[b]) for b in symbols] for a in symbols],
        "portfolio": {
            **_metrics(portfolio_growth, dates, periods),
            "terminal_weights": terminal_weights,
        },
        "series": {
            "prices": values,
            "returns": {s: [None] + r for s, r in returns.items()},
            "growth": growth,
            "drawdown": {s: _drawdown(values[s]) for s in symbols},
            "portfolio_growth": portfolio_growth,
            "portfolio_value": [initial * x for x in portfolio_growth],
            "portfolio_drawdown": _drawdown(portfolio_growth),
        },
        "warnings": warnings,
    }
