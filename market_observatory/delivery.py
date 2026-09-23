"""Bundled demo and portable reports."""

import csv
import html
import io
import json
import os
import tempfile
from importlib.resources import files
from pathlib import Path

from .engine import parse_csv


def demo_dataset():
    root = files("market_observatory").joinpath("data")
    return parse_csv(
        root.joinpath("demo.csv").read_bytes().decode("utf-8"),
        json.loads(root.joinpath("demo.json").read_text(encoding="utf-8")),
    )


def csv_report(result):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    symbols = result["settings"]["symbols"]
    writer.writerow(
        ["date", "portfolio_value", "portfolio_growth", "portfolio_drawdown"]
        + [f"{s}_{kind}" for s in symbols for kind in ["close", "return", "growth", "drawdown"]]
    )
    for i, day in enumerate(result["dates"]):
        row = [day] + [
            result["series"][key][i]
            for key in ["portfolio_value", "portfolio_growth", "portfolio_drawdown"]
        ]
        for symbol in symbols:
            row.extend(
                result["series"][key][symbol][i]
                for key in ["prices", "returns", "growth", "drawdown"]
            )
        writer.writerow(row)
    return output.getvalue()


def html_report(result):
    def escape(value):
        return html.escape(str(value), quote=True)

    def percent(value):
        return "Undefined" if value is None else f"{value:.2%}"

    rows = "".join(
        "<tr><th>"
        + escape(row["symbol"])
        + "</th>"
        + "".join(
            "<td>" + percent(row[k]) + "</td>"
            for k in ["total_return", "cagr", "annualized_volatility", "max_drawdown"]
        )
        + "</tr>"
        for row in [{"symbol": "Portfolio", **result["portfolio"]}] + result["assets"]
    )
    meta = "".join(
        f"<dt>{escape(k.replace('_', ' ').title())}</dt><dd>{escape(v)}</dd>"
        for k, v in result["metadata"].items()
    )
    warnings = "".join("<li>" + escape(w) + "</li>" for w in result["warnings"])
    details = escape(
        json.dumps(
            {
                "settings": result["settings"],
                "provenance": result["provenance"],
                "coverage": result["coverage"],
                "engine_version": result["engine_version"],
            },
            indent=2,
            allow_nan=False,
        )
    )
    points = result["series"]["portfolio_growth"]
    # Report plot is bounded for large imports while full series remains in JSON/CSV.
    stride = max(1, (len(points) - 1) // 800)
    indices = sorted(set(range(0, len(points), stride)) | {len(points) - 1})
    low, high = min(points), max(points)
    spread = high - low or 1
    path = " ".join(
        f"{'M' if j == 0 else 'L'}{40 + 720 * i / (len(points) - 1):.2f},{200 - 160 * (points[i] - low) / spread:.2f}"
        for j, i in enumerate(indices)
    )
    title = escape(result["metadata"]["title"])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} | MarketObservatory</title><style>body{{font:16px/1.6 system-ui,sans-serif;color:#182536;background:#f5f7fb;max-width:1000px;margin:40px auto;padding:0 24px}}h1{{font-size:36px}}small{{color:#526071}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{text-align:right;padding:12px;border-bottom:1px solid #d9e0eb}}th:first-child{{text-align:left}}dt{{font-weight:bold}}dd{{margin:0 0 12px;overflow-wrap:anywhere}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#e8edf5;padding:16px}}svg{{width:100%;background:white;border:1px solid #d9e0eb}}@media print{{body{{margin:0}}}}</style><body><small>MARKETOBSERVATORY · PORTFOLIO ANALYSIS</small><h1>{title}</h1><p>{result["dates"][0]} to {result["dates"][-1]} · {len(points)} aligned observations · {escape(result["settings"]["mode"])}</p><h2>Portfolio growth</h2><svg viewBox="0 0 800 240" role="img" aria-label="Historical portfolio growth"><path d="{path}" fill="none" stroke="#146579" stroke-width="3"/><text x="40" y="225">Start: 1.000</text><text x="620" y="225">End: {points[-1]:.3f}</text></svg><h2>Historical metrics</h2><table><thead><tr><th>Series</th><th>Return</th><th>CAGR</th><th>Annualized volatility</th><th>Max drawdown</th></tr></thead><tbody>{rows}</tbody></table><h2>Dataset provenance</h2><dl>{meta}</dl><h2>Interpretation limits</h2><ul>{warnings}</ul><h2>Reproduction record</h2><pre>{details}</pre><p>The report contains the source details, assumptions, aligned observations, and calculated results.</p></body></html>'''


def write_report(result, path, format, force=False):
    render = {
        "json": lambda r: json.dumps(r, indent=2, allow_nan=False) + "\n",
        "csv": csv_report,
        "html": html_report,
    }
    if format not in render:
        raise ValueError("Report format must be json, csv, or html.")
    # Finish rendering and writing before publishing the destination. A failed
    # render/write must never truncate an earlier report, even with --force.
    content = render[format](result)
    destination = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if force:
            os.replace(temporary, destination)
        else:
            # A same-directory hard link publishes atomically and refuses an
            # existing destination, including a competing writer's report.
            os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
